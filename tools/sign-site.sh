#!/usr/bin/env bash
# sign-site.sh — Detach-sign every HTML file in _site/ with the signing subkey.
#
# Requires the passphrase to be pre-cached via tools/preset-signing-passphrase.sh.
# Produces <file>.html.sig alongside each <file>.html.
#
# Usage (called by `make sign`):
#   ./tools/sign-site.sh [site-dir]
#
# SIGN_ONLY_CHANGED=1 skips any HTML whose signature already exists and is
# newer than it. Off by default, and useless on its own: tools/stamp-build-time.py
# rewrites every page's footer at the end of every build, so every file is
# newer than its signature by the time this runs. It pays only together with
# SKIP_STAMP=1 (see the `build` target). Coverage is unaffected either way —
# the post-sign manifest check below still requires a non-empty .sig for
# every .html before the script exits 0.

set -euo pipefail

GNUPGHOME="${GNUPGHOME:-$HOME/.gnupg-signing}"
SITE_DIR="${1:-_site}"
SIGNING_KEY="C9A42A6FAD444FBE566FD738531BDC1CC2707066"

if [ ! -d "$SITE_DIR" ]; then
    echo "Error: site directory '$SITE_DIR' not found. Run 'make build' first." >&2
    exit 1
fi

# Pre-flight: verify the signing key is available and the passphrase is cached
# by signing /dev/null. If this fails (e.g. passphrase not preset, key missing),
# abort before touching any .sig files.
echo "sign-site: pre-flight check..." >&2
if ! GNUPGHOME="$GNUPGHOME" gpg \
        --homedir "$GNUPGHOME" \
        --batch \
        --yes \
        --detach-sign \
        --armor \
        --local-user "$SIGNING_KEY" \
        --output /dev/null \
        /dev/null 2>/dev/null; then
    echo "" >&2
    echo "ERROR: GPG signing pre-flight failed." >&2
    echo "  The signing key passphrase is probably not cached." >&2
    echo "  Run: ./tools/preset-signing-passphrase.sh" >&2
    echo "  Then retry: make sign  (or  make deploy)" >&2
    exit 1
fi
echo "sign-site: pre-flight OK — signing $SITE_DIR..." >&2

# Sign sequentially through a single gpg-agent: parallel signing causes
# pinentry/IPC races where individual signs fail silently while xargs
# still exits 0. Atomic write via .tmp + mv avoids leaving a truncated
# .sig if the script is interrupted mid-write.
sign_one() {
    local html="$1"
    local sig="${html}.sig"
    local tmp="${sig}.tmp"
    if ! gpg --homedir "$GNUPGHOME" \
             --batch \
             --yes \
             --detach-sign \
             --armor \
             --local-user "$SIGNING_KEY" \
             --output "$tmp" \
             "$html"; then
        rm -f "$tmp"
        echo "sign-site: FAILED to sign $html" >&2
        return 1
    fi
    mv -f "$tmp" "$sig"
}

count=0
skipped=0
while IFS= read -r -d '' html; do
    if [ "${SIGN_ONLY_CHANGED:-0}" = "1" ] \
       && [ -s "${html}.sig" ] \
       && [ "${html}.sig" -nt "$html" ]; then
        skipped=$((skipped + 1))
        continue
    fi
    sign_one "$html"
    count=$((count + 1))
done < <(find "$SITE_DIR" -name "*.html" -print0)

# Post-sign manifest verification: every .html must have a non-empty
# matching .sig. This catches any per-file failure that slipped through
# (set -e bails on first failure inside the loop, but a manual --output
# write to a directory containing a stale .sig from a prior run could
# look "successful" otherwise).
missing=0
while IFS= read -r -d '' html; do
    if [ ! -s "${html}.sig" ]; then
        echo "sign-site: missing/empty signature for $html" >&2
        missing=$((missing + 1))
    fi
done < <(find "$SITE_DIR" -name "*.html" -print0)

if [ "$missing" -ne 0 ]; then
    echo "sign-site: $missing HTML files lack signatures — aborting" >&2
    exit 1
fi

if [ "$skipped" -gt 0 ]; then
    echo "Signed $count HTML files in $SITE_DIR ($skipped unchanged, reused)."
else
    echo "Signed $count HTML files in $SITE_DIR."
fi
