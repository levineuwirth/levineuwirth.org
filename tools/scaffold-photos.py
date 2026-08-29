#!/usr/bin/env python3
"""
scaffold-photos.py — write every entry of a batch import in one process.

Called by tools/import-photos.sh with a tab-separated plan:

    md_path <TAB> target_jpg <TAB> slug <TAB> title

and reads SERIES, TAGS and LOCATION from the environment.

This exists because the single-file importer spent a Python interpreter
start per photograph just to turn one sidecar into one block of frontmatter.
At batch sizes that is most of the runtime and none of the work.

The frontmatter written here is the durable copy of the camera metadata: the
sidecars are gitignored and are regenerated from delivery files that have had
their EXIF stripped, so anything not written into frontmatter at import time
does not survive a clone. `geo` is deliberately never written — the sidecar
holds full-precision coordinates on purpose and Hakyll applies the
geo-precision gate at render, so putting coordinates in frontmatter would
commit exact positions to a public repository and route around it.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
TODAY = __import__("datetime").date.today().isoformat()

# Order matters: this is the order they appear in the file.
EXIF_KEYS_BASE = ["captured", "camera", "lens", "focal-length"]


def render(key: str, value) -> str:
    if isinstance(value, bool):
        return f"{key}: {'true' if value else 'false'}"
    if isinstance(value, (int, float)):
        return f"{key}: {value}"
    text = str(value)
    if key == "captured" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return f"{key}: {text}"
    return f'{key}: "{text}"'


def exif_lines(sidecar: Path) -> list[str]:
    if not sidecar.exists():
        return []
    try:
        data = yaml.safe_load(sidecar.read_text()) or {}
    except Exception:
        return []
    keys = list(EXIF_KEYS_BASE)
    # extract-exif composes `exposure` only when shutter, aperture and ISO are
    # all present; prefer it, and fall back to whichever parts were readable.
    keys += ["exposure"] if data.get("exposure") else ["shutter", "aperture", "iso"]
    return [render(k, data[k]) for k in keys if data.get(k) not in (None, "")]


def build_tags(extra: str) -> str:
    tags = ["photography"]
    for raw in (extra or "").split(","):
        t = raw.strip()
        if not t:
            continue
        # Anything not already hierarchical is filed beneath photography/,
        # matching import-photo.sh. A slash is the escape hatch.
        tags.append(t if ("/" in t or t == "photography") else f"photography/{t}")
    return ", ".join(dict.fromkeys(tags))


def title_from_slug(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.split("-"))


def main() -> int:
    if len(sys.argv) < 2:
        print("scaffold-photos: expected a plan file", file=sys.stderr)
        return 2

    series   = os.environ.get("SERIES", "")
    tags     = build_tags(os.environ.get("TAGS", ""))
    location = os.environ.get("LOCATION", "")

    written = 0
    for line in Path(sys.argv[1]).read_text().splitlines():
        if not line.strip():
            continue
        md_path, target, slug, title = (line.split("\t") + ["", "", "", ""])[:4]
        md = Path(md_path)
        photo = Path(target)

        with __import__("PIL.Image", fromlist=["Image"]).open(photo) as im:
            w, h = im.size
        orientation = "landscape" if w > h else ("portrait" if h > w else "square")

        body = [
            "---",
            render("title", title or title_from_slug(slug)),
            f"date: {TODAY}",
            # No abstract: individual photographs don't carry one — the
            # caption is the title, and only the series landing has prose.
            f"tags: [{tags}]",
            f"photo: {photo.name}",
        ]
        if series:
            body.append(f"series: {series}")
        body.append(f"orientation: {orientation}")
        body += exif_lines(Path(str(photo) + ".exif.yaml"))
        if location:
            body.append(render("location", location))
        body += [
            '# license: "CC BY-SA 4.0"   # uncomment + set; canonical URL auto-resolves',
            "# The camera fields above were read from EXIF at import and written",
            "# here because frontmatter is tracked and the sidecar is not.",
            "#",
            "# geo: [00.000, 00.000]     # add deliberately; pair with geo-precision",
            "# geo-precision: city       # exact | km | city | hidden  (default: city)",
            "---",
            "",
        ]
        md.write_text("\n".join(body) + "\n")
        md.chmod(0o644)
        written += 1

    print(f"scaffold-photos: {written} written", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
