#!/usr/bin/env python3
"""The site's tags keep the shape decided in November 2026.

Every top-level tag is a portal (site.yaml's `portals`): a tag that is not
one gets a page whose "see also" lists every portal, unrelated to it, and
an essay whose tags name no portal was left off the Library. Research is
the one mode among the portals and stays flat: its only subtag is
`research/preprint`, a status, and subjects go under their own portals
(`mathematics/graph-theory`, not `research/graph-theory`).

The plan and its reasons are in the apocrypha vault, Passus/Site tags and
portals (2026-11-24). Nothing in the build fails on either rule, so this
suite reads the front matter of every page under content/ that ships and
fails instead. What ships is the generator's to say (`site list-unpublished`,
engine tools/unpublished.py): a draft flag in any spelling it takes, and a
draft series' or essay directory's whole contents, are withheld.

Run with: ``make test`` (or ``python3 -m unittest tests.test_tags``).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests._helpers import SITE_ROOT, load_tool, requires_cabal

try:
    import yaml
except ImportError:  # pragma: no cover - `make validate` requires .venv
    yaml = None

CONTENT = SITE_ROOT / "content"
front_matter = load_tool("front_matter.py")
unpublished = load_tool("unpublished.py")

# Research's subtags: statuses of a piece of research, not subjects.
RESEARCH_SUBTAGS = {"research/preprint"}


def tagged_pages(content=CONTENT):
    """(path under content/, its tags as written) for every page with tags
    that ships: not under content/drafts/, and not withheld by a production
    build (Drafts.hs), as the generator itself reports."""
    boundary = unpublished.load_boundary(content)
    pages = []
    for path in sorted(content.rglob("*.md")):
        rel = path.relative_to(content)
        if rel.parts[0] in ("drafts", "tag-meta") or unpublished.withheld(path, boundary):
            continue
        meta = front_matter.load(path.read_text(encoding="utf-8"))
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        if tags:
            pages.append((rel.as_posix(), tags))
    return pages


@requires_cabal
@unittest.skipIf(yaml is None, "PyYAML is required (make validate uses .venv)")
class TagShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = yaml.safe_load((SITE_ROOT / "site.yaml").read_text(encoding="utf-8"))
        cls.portals = {p["tag"] for p in config["portals"]}
        cls.pages = tagged_pages()

    def test_there_are_tagged_pages(self):
        self.assertGreater(len(self.pages), 20)

    def test_every_top_level_tag_is_a_portal(self):
        stray = sorted({(rel, tag) for rel, tags in self.pages for tag in tags
                        if tag.split("/")[0] not in self.portals})
        self.assertEqual(stray, [], "tags whose top level is not a portal in site.yaml")

    def test_research_has_no_subjects_beneath_it(self):
        stray = sorted({(rel, tag) for rel, tags in self.pages for tag in tags
                        if tag.startswith("research/") and tag not in RESEARCH_SUBTAGS})
        self.assertEqual(stray, [], "subjects go under their own portal, not research/")


@requires_cabal
class ShippedPages(unittest.TestCase):
    def test_what_a_production_build_withholds_is_not_checked(self):
        with tempfile.TemporaryDirectory(prefix="tag-shape-") as tmp:
            content = Path(tmp)
            pages = {
                "essays/quoted.md": 'title: Q\ndraft: "1"\ntags: [nowhere]',
                "photography/series/index.md": "title: S\ndraft: true\ntags: [nowhere]",
                "photography/series/frame.md": "title: F\ntags: [nowhere]",
                "essays/shipped.md": "title: P\ntags: [somewhere]",
            }
            for rel, front in pages.items():
                (content / rel).parent.mkdir(parents=True, exist_ok=True)
                (content / rel).write_text(f"---\n{front}\n---\n\nBody.\n", encoding="utf-8")
            self.assertEqual(tagged_pages(content), [("essays/shipped.md", ["somewhere"])])


if __name__ == "__main__":
    unittest.main()
