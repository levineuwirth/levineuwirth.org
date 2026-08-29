#!/usr/bin/env bash
# import-photo.sh — Author-facing import workflow for photography entries.
#
# Given a path to an original photograph and a target slug, this script:
#
#   1. Creates content/photography/<slug>/.
#   2. Resizes the original to ≤2400px on the long edge, JPEG quality 85,
#      sRGB. EXIF is preserved at this step so the extractor can read it.
#   3. Runs tools/extract-exif.py to produce the {photo}.exif.yaml sidecar.
#   4. Strips EXIF from the delivered JPEG (the sidecar now holds the
#      metadata; the file shipped to viewers carries no GPS, no serial
#      numbers, no Lightroom edit history).
#   5. Runs tools/extract-palette.py to produce the {photo}.palette.yaml
#      sidecar.
#   6. Scaffolds an index.md frontmatter stub ready for editing.
#
# Usage:
#   tools/import-photo.sh <original-path> <slug> [--title "Title"]
#                         [--series <series-slug>] [--tags a,b,c]
#
# Examples:
#   tools/import-photo.sh ~/Photos/IMG_4421.jpg reykjavik-rooftops
#   tools/import-photo.sh ~/Photos/IMG_4421.jpg reykjavik-rooftops --title "Reykjavík Rooftops"
#
# Requirements:
#   * ImageMagick (`magick`) for resize / strip / colorspace conversion
#   * uv + .venv (Pillow + colorthief + pyyaml) for sidecar extraction
#
# Originals are NEVER copied into the repo verbatim — only the resized
# delivery JPEG. Per PHOTOGRAPHY.md, originals live outside source
# control (your local archive, NAS, or backup).

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

if [ "$#" -lt 2 ]; then
    cat <<EOF >&2
Usage: $(basename "$0") <original-path> <slug> [--title "T"] [--series <s>] [--tags a,b]

Imports a photograph into content/photography/<slug>/, producing:
  photo.jpg                  resized, sRGB, EXIF-stripped (delivery copy)
  photo.jpg.exif.yaml        extracted EXIF metadata (sidecar)
  photo.jpg.palette.yaml     5-color palette (sidecar)
  index.md                   frontmatter stub ready for editing
EOF
    exit 1
fi

ORIGINAL="$1"
SLUG="$2"
shift 2

if [[ ! "$SLUG" =~ ^[a-z0-9-]+$ ]]; then
    echo "import-photo: invalid slug '$SLUG' (must be lowercase a-z, 0-9, hyphens only)" >&2
    exit 1
fi

TITLE=""
SERIES=""
EXTRA_TAGS=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --title)
            TITLE="$2"
            shift 2
            ;;
        --series)
            SERIES="$2"
            shift 2
            ;;
        --tags)
            EXTRA_TAGS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

if [ -n "$SERIES" ] && [[ ! "$SERIES" =~ ^[a-z0-9-]+$ ]]; then
    echo "import-photo: invalid series '$SERIES' (lowercase a-z, 0-9, hyphens)" >&2
    exit 1
fi

if [ ! -f "$ORIGINAL" ]; then
    echo "import-photo: original not found: $ORIGINAL" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Tool availability checks
# ---------------------------------------------------------------------------

if ! command -v exiftool >/dev/null 2>&1; then
    echo "import-photo: exiftool is required (it strips EXIF from the delivered file)." >&2
    echo "  Arch:   pacman -S perl-image-exiftool" >&2
    echo "  Debian: apt install libimage-exiftool-perl" >&2
    exit 1
fi

if ! command -v magick >/dev/null 2>&1; then
    echo "import-photo: ImageMagick ('magick') is required but not installed." >&2
    echo "  Arch:   pacman -S imagemagick" >&2
    echo "  Debian: apt install imagemagick" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -d "$REPO_ROOT/.venv" ]; then
    echo "import-photo: .venv not found at $REPO_ROOT/.venv" >&2
    echo "  Run: uv sync" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

# Two shapes, per PHOTOGRAPHY.md:
#
#   standalone   content/photography/<slug>/index.md  + photo.jpg
#   series child content/photography/<series>/<slug>.md + <slug>.jpg
#
# The build derives the image URL as /photography/<dir>/<photo>, where <dir>
# is the containing directory either way — so a series child keeps its image
# beside its markdown rather than in a subdirectory of its own. A directory
# becomes a series automatically once it holds sibling .md files next to
# index.md; nothing has to be declared.
if [ -n "$SERIES" ]; then
    ENTRY_DIR="$REPO_ROOT/content/photography/$SERIES"
    TARGET="$ENTRY_DIR/$SLUG.jpg"
    PHOTO_FIELD="$SLUG.jpg"
    INDEX_MD="$ENTRY_DIR/$SLUG.md"
    SERIES_LANDING="$ENTRY_DIR/index.md"
else
    ENTRY_DIR="$REPO_ROOT/content/photography/$SLUG"
    TARGET="$ENTRY_DIR/photo.jpg"
    PHOTO_FIELD="photo.jpg"
    INDEX_MD="$ENTRY_DIR/index.md"
    SERIES_LANDING=""
fi

EXIF_SIDECAR="$TARGET.exif.yaml"
PALETTE_SIDECAR="$TARGET.palette.yaml"

# Refuse to clobber an existing entry. For a series the directory is expected
# to exist and be added to, so only the entry's own files are guarded.
if [ -e "$INDEX_MD" ] || [ -e "$TARGET" ]; then
    echo "import-photo: $INDEX_MD or $TARGET already exists. Refusing to overwrite." >&2
    echo "  Either choose a new slug or remove the existing entry first." >&2
    exit 1
fi
if [ -z "$SERIES" ] && [ -e "$ENTRY_DIR" ]; then
    echo "import-photo: $ENTRY_DIR already exists. Refusing to overwrite." >&2
    exit 1
fi

mkdir -p "$ENTRY_DIR"

# ---------------------------------------------------------------------------
# Step 1: resize + colorspace, EXIF preserved (so the extractor can read it)
# ---------------------------------------------------------------------------

echo "import-photo: resizing to ≤2400px JPEG q85 sRGB → $TARGET"
magick "$ORIGINAL" \
    -auto-orient \
    -resize '2400x2400>' \
    -colorspace sRGB \
    -quality 85 \
    "$TARGET" \
    || { echo "import-photo: magick resize failed for $ORIGINAL → $TARGET" >&2; exit 1; }
chmod 644 "$TARGET"

# ---------------------------------------------------------------------------
# Step 2: extract EXIF (reads from the resized file, which still has EXIF)
# ---------------------------------------------------------------------------

echo "import-photo: extracting EXIF sidecar..."
( cd "$REPO_ROOT" && .venv/bin/python tools/extract-exif.py "$TARGET" ) || true

if [ ! -f "$EXIF_SIDECAR" ]; then
    # Empty sidecar so the consuming Hakyll field has something to read
    # (an absent sidecar is also handled, but a present-but-empty file
    # signals "extraction was attempted" — useful for film scans where
    # there's intentionally no EXIF to find).
    echo '{}' > "$EXIF_SIDECAR"
fi

# ---------------------------------------------------------------------------
# Step 3: strip EXIF from the delivered JPEG (sidecar already has it)
# ---------------------------------------------------------------------------

echo "import-photo: stripping EXIF from delivered file..."
exiftool -q -all= --icc_profile:all -overwrite_original "$TARGET" \
    || {
        # The copy under content/ still carries full EXIF (GPS, serial
        # numbers); the Makefile's `git add content/` could auto-commit
        # and publish it. Remove it before bailing out.
        rm -f -- "$TARGET"
        echo "import-photo: exiftool -all= failed for $TARGET (EXIF NOT stripped); deleted the copied target so the EXIF-laden JPEG cannot be auto-committed" >&2
        exit 1
    }

# Stripping rewrites the JPEG, so the delivered file is now NEWER than the
# sidecar we just extracted from it. extract-exif.py treats
# `image mtime > sidecar mtime` as stale, so the very next `make build`
# would re-extract from the stripped file and overwrite real metadata with
# width/height alone — silently, because the build still succeeds. Making
# the sidecar the newer file closes that window.
touch "$EXIF_SIDECAR"

# ---------------------------------------------------------------------------
# Step 4: extract palette (does its own walk; idempotent on already-done photos)
# ---------------------------------------------------------------------------

echo "import-photo: extracting palette sidecar..."
( cd "$REPO_ROOT" && .venv/bin/python tools/extract-palette.py "$TARGET" ) || true

# ---------------------------------------------------------------------------
# Step 5: scaffold index.md
# ---------------------------------------------------------------------------

if [ -z "$TITLE" ]; then
    TITLE="$(echo "$SLUG" | tr '-' ' ' | awk '{
        for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2);
        print
    }')"
fi

TODAY="$(date -u +%Y-%m-%d)"

# Probe the resized file's pixel dimensions so we can suggest an
# orientation; the author can override in frontmatter.
DIMS="$(magick identify -format '%w %h' "$TARGET")"
WIDTH="${DIMS%% *}"
HEIGHT="${DIMS##* }"

if [ "$WIDTH" -gt "$HEIGHT" ]; then
    ORIENTATION="landscape"
elif [ "$HEIGHT" -gt "$WIDTH" ]; then
    ORIENTATION="portrait"
else
    ORIENTATION="square"
fi

# ---------------------------------------------------------------------------
# Carry the extracted metadata into the frontmatter.
#
# The sidecar is gitignored and is regenerated from the delivered JPEG —
# which this script has just stripped. So on any other machine, and on the
# VPS, regeneration yields width and height and nothing else: camera, lens,
# and exposure would never survive a clone. Frontmatter is tracked, is what
# PHOTOGRAPHY.md already calls the authoritative layer ("author-written
# values always win"), and is editable afterwards. It is the durable home.
#
# `geo` is deliberately NOT carried across. The sidecar holds coordinates at
# full precision on purpose, and Hakyll applies the geo-precision rounding at
# render time — that is the privacy gate. Writing coordinates into
# frontmatter would commit exact positions to a public repository and route
# around the gate entirely. Adding `geo:` stays a deliberate act by the
# author, at the precision the author chooses.
# ---------------------------------------------------------------------------

EXIF_FRONTMATTER="$( cd "$REPO_ROOT" && .venv/bin/python - "$EXIF_SIDECAR" <<'PY' 2>/dev/null || true
import re, sys, pathlib

try:
    import yaml
except ImportError:
    sys.exit(0)

path = pathlib.Path(sys.argv[1])
if not path.exists():
    sys.exit(0)

data = yaml.safe_load(path.read_text()) or {}

keys = ["captured", "camera", "lens", "focal-length"]
# extract-exif.py composes `exposure` only when shutter, aperture and ISO
# are all present. Prefer it when it exists; otherwise fall back to whichever
# components were readable. Emitting both would say the same thing twice.
keys += ["exposure"] if data.get("exposure") else ["shutter", "aperture", "iso"]

def render(key, value):
    if isinstance(value, bool):
        return f"{key}: {'true' if value else 'false'}"
    if isinstance(value, (int, float)):
        return f"{key}: {value}"
    text = str(value)
    if key == "captured" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return f"{key}: {text}"
    return f'{key}: "{text}"'

for key in keys:
    value = data.get(key)
    if value not in (None, ""):
        print(render(key, value))
PY
)"

GEO_PRESENT=""
if [ -f "$EXIF_SIDECAR" ] && grep -q '^geo:' "$EXIF_SIDECAR" 2>/dev/null; then
    GEO_PRESENT="yes"
fi

# Tags. `photography` is always present. Anything passed via --tags that is
# not already hierarchical is filed beneath it, so `--tags architecture,germany`
# becomes photography/architecture and photography/germany. A tag containing a
# slash is taken verbatim, which is the escape hatch for anything that should
# not live under photography/.
#
# These cut ACROSS series on purpose: the series says which trip a frame
# belongs to, the tags say what it is of, and the two indexes answer different
# questions. A frame can be in germany-2026 and still turn up under
# photography/architecture next to something shot years earlier.
TAGS="photography"
if [ -n "$EXTRA_TAGS" ]; then
    IFS=',' read -ra _raw <<< "$EXTRA_TAGS"
    for t in "${_raw[@]}"; do
        t="$(echo "$t" | tr -d '[:space:]')"
        [ -z "$t" ] && continue
        case "$t" in
            */*|photography) TAGS="$TAGS, $t" ;;
            *)               TAGS="$TAGS, photography/$t" ;;
        esac
    done
fi

SERIES_FIELD=""
if [ -n "$SERIES" ]; then
    SERIES_FIELD="series: $SERIES"
fi

cat > "$INDEX_MD" <<EOF
---
title: "$TITLE"
date: $TODAY
tags: [$TAGS]
photo: $PHOTO_FIELD
$SERIES_FIELD
orientation: $ORIENTATION
$EXIF_FRONTMATTER
# license: "CC BY-SA 4.0"   # uncomment + set; canonical URL auto-resolves
# location: ""              # human-readable, e.g. "Reykjavík, Iceland"
# The camera fields above were read from the file's EXIF at import and
# written here because frontmatter is tracked and the sidecar is not. Edit
# freely — these values are authoritative from now on.
#
# geo: [00.000, 00.000]     # add deliberately; pair with geo-precision
# geo-precision: city       # exact | km | city | hidden  (default: city)
---

EOF
chmod 644 "$INDEX_MD"

# A series needs a landing page. Create one the first time a photograph is
# filed under a new series slug; leave an existing landing untouched so
# repeated imports only ever add frames.
if [ -n "$SERIES_LANDING" ] && [ ! -f "$SERIES_LANDING" ]; then
    SERIES_TITLE="$(echo "$SERIES" | tr '-' ' ' | awk '{
        for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2);
        print
    }')"
    cat > "$SERIES_LANDING" <<EOF
---
title: "$SERIES_TITLE"
date: $TODAY
abstract: >
  TODO — what this series is, in a sentence or two.
tags: [photography]
---

EOF
    chmod 644 "$SERIES_LANDING"
    echo "import-photo: created series landing $SERIES_LANDING"
fi

echo
echo "import-photo: done."
echo "  Entry:   $INDEX_MD"
echo "  Photo:   $TARGET ($WIDTH × $HEIGHT, $ORIENTATION)"
echo "  Sidecars: $(basename "$EXIF_SIDECAR"), $(basename "$PALETTE_SIDECAR")"
echo
if [ -n "$GEO_PRESENT" ]; then
    echo
    echo "  NOTE: this photograph carries GPS coordinates in its EXIF."
    echo "  They are in the sidecar and were NOT written to frontmatter, and"
    echo "  the delivered JPEG has been stripped, so nothing is published yet."
    echo "  Add geo: + geo-precision: to $INDEX_MD only if you want it mapped."
fi

echo
echo "Next: edit $INDEX_MD to fill in title / abstract / tags, then 'make dev'."
