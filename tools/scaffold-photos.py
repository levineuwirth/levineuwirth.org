#!/usr/bin/env python3
"""
scaffold-photos.py — write every entry of a batch import in one process.

Called by tools/import-photos.sh with a tab-separated plan (the batch's
manifest is tab-separated already, so no field can hold a tab or newline):

    scaffold-photos.py PLAN     # md_path <TAB> target_jpg <TAB> slug <TAB> title

and by tools/import-photo.sh with the one entry as arguments, which carry a
title with a tab or a newline intact:

    scaffold-photos.py --entry MD_PATH TARGET_JPG SLUG TITLE

Both read SERIES, TAGS and LOCATION from the environment. It also writes
the series landing the first time a photograph is filed under a new series.
A batch takes one Python start rather than one per photograph; the single
importer used to write its own copy of all this, which had drifted (its
tags went unquoted).

    scaffold-photos.py --check

is the importers' namespace guard (see namespace_problems), run before
either copies a photograph: it judges the tags as they will be written.

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


def entry_tags(path: Path) -> list[str]:
    """The tags an existing entry's front matter gives it, as a list."""
    try:
        tags = front_matter.load(path.read_text(encoding="utf-8")).get("tags") or []
    except (OSError, UnicodeDecodeError, front_matter.yaml.YAMLError):
        return []
    if isinstance(tags, str):
        tags = tags.split(",")
    return [str(t).strip() for t in tags if str(t).strip()]


def namespace_problems(series: str, tags: list[str], photo_root: Path) -> list[str]:
    """Series and tags share one URL space: a series lives at
    /photography/<series>/ and a tag at /<tag>/, so photography/<x> claims
    /photography/<x>/ too. Two claims on one route fail the whole build
    with "multiple writes for route", which names the conflict but not the
    import that caused it, several hundred files after the fact; refused
    here instead, where the decision is still on the command line. Judges
    `tags` as they will be written (build_tags), not as typed."""
    problems = []
    for tag in tags:
        name = tag.removeprefix("photography/")
        if (name != tag and "/" not in name and name != series
                and (photo_root / name).is_dir()):
            problems.append(f"tag '{tag}' collides with the series '{name}': both would "
                            f"claim /photography/{name}/. Use another tag, or rename the series.")
    if series:
        claim = f"photography/{series}"
        for md in sorted(photo_root.rglob("*.md")):
            if claim in entry_tags(md):
                problems.append(f"series '{series}' collides with the tag '{claim}' on "
                                f"{md.relative_to(photo_root.parent.parent)}: both would claim "
                                f"/photography/{series}/.")
                break
    return problems


def main() -> int:
    series   = os.environ.get("SERIES", "")
    tags     = build_tags(os.environ.get("TAGS", ""))
    location = os.environ.get("LOCATION", "")
    args     = sys.argv[1:]

    if args == ["--check"]:
        problems = namespace_problems(series, tags, REPO_ROOT / "content" / "photography")
        for p in problems:
            print(f"scaffold-photos: {p}", file=sys.stderr)
        return 2 if problems else 0
    if len(args) == 5 and args[0] == "--entry":
        entries = [args[1:]]
    elif len(args) == 1:
        entries = [(line.split("\t") + ["", "", "", ""])[:4]
                   for line in Path(args[0]).read_text().splitlines() if line.strip()]
    else:
        print("usage: scaffold-photos.py PLAN | --entry MD TARGET SLUG TITLE | --check",
              file=sys.stderr)
        return 2

    written = 0
    for md_path, target, slug, title in entries:
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
