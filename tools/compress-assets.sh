#!/usr/bin/env bash
# compress-assets.sh — Generate .gz (and .br, if brotli is installed) sidecars
# for compressible text assets in _site/.
#
# Pairs with nginx `gzip_static on` / `brotli_static on`: nginx serves the
# pre-compressed file when the client advertises a matching Accept-Encoding,
# so each build pays the compression cost once (at brotli -q 11) instead of
# the server paying it on every request.
#
# Only files >= MIN_SIZE bytes are compressed — below that, the compression
# framing overhead can exceed the savings. A sidecar is reused only when it
# is strictly newer than its source, so re-runs are cheap but a same-second
# rewrite is never mistaken for up to date.
#
# Three ways a sidecar can go stale, all handled here because nginx serves
# it in preference to the source whenever the client sends the matching
# Accept-Encoding — a stale sidecar is a *wrong response*, not a slow one:
#
#   1. The source shrank below MIN_SIZE. The old sidecar is not overwritten
#      (nothing is compressed), so it keeps decoding to the previous, larger
#      content. Deleted here.
#   2. The source was deleted. Its sidecars are orphans that nginx will
#      still happily serve. Swept here, but only when the stripped name has
#      one of the compressible extensions below, so an intentionally
#      published foo.tar.gz is never touched.
#   3. The compressor was interrupted or produced garbage. Every sidecar
#      this run writes is decompressed and `cmp`-ed against its source
#      before it is moved into place.
#
# Usage:
#   ./tools/compress-assets.sh              # compress _site/
#   ./tools/compress-assets.sh path/to/dir  # compress a specific directory
#
# MIN_SIZE is overridable (bytes); the directory argument is what tests use
# to run this against a scratch tree.

set -euo pipefail

SITE_DIR="${1:-_site}"
MIN_SIZE="${MIN_SIZE:-1024}"  # bytes

if [[ ! "$MIN_SIZE" =~ ^[0-9]+$ ]]; then
    echo "compress-assets: MIN_SIZE must be a positive integer (got '$MIN_SIZE')" >&2
    exit 1
fi

if [ ! -d "$SITE_DIR" ]; then
    echo "compress-assets: directory '$SITE_DIR' not found" >&2
    exit 1
fi

have_brotli=0
if command -v brotli >/dev/null 2>&1; then
    have_brotli=1
else
    echo "compress-assets: brotli not found — generating gzip only" >&2
    echo "                 (install: pacman -S brotli  /  apt install brotli)" >&2
fi

# Export for subshells invoked by xargs.
export MIN_SIZE
export have_brotli

compress_one() {
    local src="$1"
    local size
    size=$(stat -c '%s' "$src" 2>/dev/null || stat -f '%z' "$src")

    if [ "$size" -lt "$MIN_SIZE" ]; then
        # Below the threshold nothing is written — so any sidecar sitting
        # here is from a previous, larger version of this file and would
        # decode to content the source no longer has. Remove it.
        for stale in "$src.gz" "$src.br"; do
            if [ -f "$stale" ]; then
                echo "  drop  ${stale} (source below MIN_SIZE)" >&2
                rm -f "$stale"
            fi
        done
        rm -f "$src.gz.tmp" "$src.br.tmp"
        return
    fi

    # gzip sidecar — -9 max ratio, -n strips filename/mtime for reproducible output.
    # Reuse only a sidecar strictly newer than the source: `src -nt sidecar`
    # is false when the two share an mtime, which is exactly the case a
    # same-second rewrite produces.
    if [ ! -f "$src.gz" ] || [ ! "$src.gz" -nt "$src" ]; then
        gzip -9 -n -c "$src" > "$src.gz.tmp" || { rm -f "$src.gz.tmp"; return 1; }
        if ! gzip -dc "$src.gz.tmp" | cmp -s - "$src"; then
            rm -f "$src.gz.tmp"
            echo "compress-assets: gzip sidecar for $src did not round-trip" >&2
            return 1
        fi
        mv "$src.gz.tmp" "$src.gz"
    fi

    # brotli sidecar — -Z is the max quality (level 11); slow but cached.
    if [ "$have_brotli" = "1" ]; then
        if [ ! -f "$src.br" ] || [ ! "$src.br" -nt "$src" ]; then
            brotli -Z -f -o "$src.br.tmp" "$src" || { rm -f "$src.br.tmp"; return 1; }
            if ! brotli -dc "$src.br.tmp" | cmp -s - "$src"; then
                rm -f "$src.br.tmp"
                echo "compress-assets: brotli sidecar for $src did not round-trip" >&2
                return 1
            fi
            mv "$src.br.tmp" "$src.br"
        fi
    fi
}
export -f compress_one

# Extensions worth compressing. Images (png/jpg/webp) and PDFs are already
# compressed; fonts (woff2) are zstd/brotli internally — don't re-wrap.
# Kept in one place because the orphan sweep below has to agree with it
# exactly: a suffix this list does not claim must never be deleted.
COMPRESSIBLE_EXTS=(html css js mjs json svg xml txt wasm)

find_predicates=()
for ext in "${COMPRESSIBLE_EXTS[@]}"; do
    if [ "${#find_predicates[@]}" -gt 0 ]; then
        find_predicates+=(-o)
    fi
    find_predicates+=(-name "*.$ext")
done

# --- Sweep 1: orphaned and interrupted sidecars ----------------------------
#
# A source deleted since the last run leaves foo.html.gz behind, and nginx
# will still serve it to any client advertising gzip. Delete a sidecar only
# when its stripped name has a compressible extension, so a deliberately
# published archive (foo.tar.gz) survives.
orphans=0
while IFS= read -r -d '' sidecar; do
    src="${sidecar%.*}"
    [ -e "$src" ] && continue
    ext="${src##*.}"
    for known in "${COMPRESSIBLE_EXTS[@]}"; do
        if [ "$ext" = "$known" ]; then
            echo "  drop  $sidecar (source no longer exists)" >&2
            rm -f "$sidecar"
            orphans=$((orphans + 1))
            break
        fi
    done
done < <(find "$SITE_DIR" -type f \( -name '*.gz' -o -name '*.br' \) -print0)

# Debris from an interrupted earlier run. These are never served (nginx
# looks for exactly .gz/.br) but they do get rsynced to the VPS.
while IFS= read -r -d '' debris; do
    rm -f "$debris"
done < <(find "$SITE_DIR" -type f \( -name '*.gz.tmp' -o -name '*.br.tmp' \) -print0)

# --- Sweep 2: compress ------------------------------------------------------
if ! find "$SITE_DIR" -type f \( "${find_predicates[@]}" \) \
        -not -name '*.gz' \
        -not -name '*.br' \
        -print0 \
    | xargs -0 -P "$(nproc 2>/dev/null || echo 4)" -I {} bash -c 'compress_one "$@"' _ {}
then
    echo "compress-assets: one or more sidecars failed to verify — aborting" >&2
    exit 1
fi

echo "compress-assets: sidecars written under $SITE_DIR/ ($orphans orphan(s) removed)"
