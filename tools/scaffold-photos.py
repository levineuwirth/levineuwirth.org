#!/usr/bin/env python3
"""
scaffold-photos.py — write every entry of a batch import in one process.

Called by tools/import-photos.sh, and by tools/import-photo.sh with a
one-row plan, with a tab-separated plan:

    md_path <TAB> target_jpg <TAB> slug <TAB> title

and reads SERIES, TAGS and LOCATION from the environment. It also writes the
series landing the first time a photograph is filed under a new series. A
batch takes one Python start rather than one per photograph; the single
importer used to write its own copy of all this, which had drifted (its
tags went unquoted).

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
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
import front_matter  # noqa: E402
import photo_sidecars  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
TODAY = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).date().isoformat()

def build_tags(extra: str) -> list[str]:
    tags = ["photography"]
    for raw in (extra or "").split(","):
        # All whitespace goes, not only the ends: a tag is a URL path.
        t = "".join(raw.split())
        if not t:
            continue
        # Anything not already hierarchical is filed beneath photography/,
        # matching import-photo.sh. A slash is the escape hatch.
        tags.append(t if ("/" in t or t == "photography") else f"photography/{t}")
    return list(dict.fromkeys(tags))


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
            front_matter.field("title", title or title_from_slug(slug)),
            f"date: {TODAY}",
            # No abstract: individual photographs don't carry one — the
            # caption is the title, and only the series landing has prose.
            front_matter.tags_field(tags),
            f"photo: {photo.name}",
        ]
        if series:
            body.append(front_matter.field("series", series))
        body.append(f"orientation: {orientation}")
        body += photo_sidecars.exif_front_matter(Path(str(photo) + ".exif.yaml"))
        if location:
            body.append(front_matter.field("location", location))
        body.append('# license: "CC BY-SA 4.0"   # uncomment + set; canonical URL auto-resolves')
        if not location:
            body.append('# location: ""              # human-readable, e.g. "Reykjavík, Iceland"')
        body += [
            "# The camera fields above were read from the file's EXIF at import and",
            "# written here because frontmatter is tracked and the sidecar is not. Edit",
            "# freely — these values are authoritative from now on.",
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
    if series:
        write_series_landing(REPO_ROOT / "content" / "photography" / series / "index.md", series)
    return 0


def write_series_landing(landing: Path, series: str) -> None:
    """A series needs a landing page: write one the first time a photograph
    is filed under a new series, and leave an existing one alone, so
    repeated imports only ever add frames."""
    if landing.exists():
        return
    landing.write_text("\n".join([
        "---",
        front_matter.field("title", title_from_slug(series)),
        f"date: {TODAY}",
        "abstract: >",
        "  TODO — what this series is, in a sentence or two.",
        "tags: [photography]",
        "---",
        "",
    ]) + "\n")
    landing.chmod(0o644)
    print(f"scaffold-photos: created series landing {landing}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
