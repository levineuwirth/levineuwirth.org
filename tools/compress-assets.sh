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
# framing overhead can exceed the savings. Sidecars are regenerated only
# when the source is newer than the existing sidecar, so re-runs are cheap.
#
# Usage:
#   ./tools/compress-assets.sh              # compress _site/
#   ./tools/compress-assets.sh path/to/dir  # compress a specific directory

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
        return
    fi

    # gzip sidecar — -9 max ratio, -n strips filename/mtime for reproducible output.
    if [ ! -f "$src.gz" ] || [ "$src" -nt "$src.gz" ]; then
        gzip -9 -n -c "$src" > "$src.gz.tmp" && mv "$src.gz.tmp" "$src.gz"
    fi

    # brotli sidecar — -Z is the max quality (level 11); slow but cached.
    if [ "$have_brotli" = "1" ]; then
        if [ ! -f "$src.br" ] || [ "$src" -nt "$src.br" ]; then
            brotli -Z -f -o "$src.br.tmp" "$src" && mv "$src.br.tmp" "$src.br"
        fi
    fi
}
export -f compress_one

# Extensions worth compressing. Images (png/jpg/webp) and PDFs are already
# compressed; fonts (woff2) are zstd/brotli internally — don't re-wrap.
find "$SITE_DIR" -type f \( \
        -name '*.html' -o \
        -name '*.css'  -o \
        -name '*.js'   -o \
        -name '*.mjs'  -o \
        -name '*.json' -o \
        -name '*.svg'  -o \
        -name '*.xml'  -o \
        -name '*.txt'  -o \
        -name '*.wasm' \
    \) \
    -not -name '*.gz' \
    -not -name '*.br' \
    -print0 \
    | xargs -0 -P "$(nproc 2>/dev/null || echo 4)" -I {} bash -c 'compress_one "$@"' _ {}

echo "compress-assets: sidecars written under $SITE_DIR/"
