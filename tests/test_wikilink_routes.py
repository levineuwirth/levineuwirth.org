"""Wikilinks resolve a bare slug without Hakyll's route table, so the slugs
that route to a directory index are listed by hand in
build/Filters/Wikilinks.hs. A slug missing there links to <slug>.html, which
404s. This keeps the list complete against the routes and portals in build/."""

import re
import unittest
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1] / "build"


def listed_slugs() -> set[str]:
    src = (BUILD / "Filters" / "Wikilinks.hs").read_text(encoding="utf-8")
    body = re.search(r"^directoryRouteSlugs =(.*?)\]", src, re.M | re.S).group(1)
    return set(re.findall(r'"([^"]+)"', re.sub(r"--[^\n]*", "", body)))


def directory_routes() -> set[str]:
    found = set()
    for hs in BUILD.rglob("*.hs"):
        found |= set(re.findall(r'"([a-z-]+)/index\.html"', hs.read_text(encoding="utf-8")))
    return found


def portal_tags() -> set[str]:
    src = (BUILD / "Site.hs").read_text(encoding="utf-8")
    body = re.search(r"^homePortals =(.*?)\n\s*\]", src, re.M | re.S).group(1)
    return {slug for _, slug in re.findall(r'\("([^"]+)",\s*"([^"]+)"\)', body)}


class DirectoryRouteSlugs(unittest.TestCase):
    def test_sources_were_read(self):
        self.assertIn("build", directory_routes())
        self.assertIn("research", portal_tags())

    def test_every_directory_route_and_portal_is_listed(self):
        missing = (directory_routes() | portal_tags()) - listed_slugs()
        self.assertEqual(missing, set(), "add these to directoryRouteSlugs in build/Filters/Wikilinks.hs")


if __name__ == "__main__":
    unittest.main()
