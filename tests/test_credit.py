"""This site's pages credit whoever wrote them, wherever the site says who did."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

import yaml
from bs4 import BeautifulSoup

from tests._helpers import SITE_ROOT, load_tool

SITE = SITE_ROOT / "_site"
ATOM = "{http://www.w3.org/2005/Atom}"
POEMS = {"ozymandias": ("Percy Bysshe Shelley", "1818"), "sonnet-60": ("William Shakespeare", "1609")}
front_matter = load_tool("front_matter.py")


def credited(content: Path, url: str, author: str) -> dict[str, list[str]]:
    """Expected entry-level authors for explicitly credited poems and essays."""
    found = {}
    for section in ("poetry", "essays"):
        directory = content / section
        for path in sorted([*directory.glob("*.md"), *directory.glob("*/*.md")]):
            if section == "poetry" and path.name == "index.md" and path.parent != directory:
                continue  # A poetry collection's landing page is separate from its poems.
            meta = front_matter.load(path.read_text(encoding="utf-8"))
            if section == "poetry":
                names = [meta["poet"].strip()] if meta.get("poet") else []
            else:
                names = [entry.partition("|")[0].strip() for entry in meta.get("authors") or []]
            if names:
                route = path.relative_to(content).with_suffix(".html").as_posix()
                if path.name == "index.md":
                    route = route.removesuffix("index.html")
                found[f"{url}/{route}"] = [] if names == [author] else names
    return found


class CreditSourceTests(unittest.TestCase):
    def test_collection_entries_and_inherited_poet_credit(self) -> None:
        with TemporaryDirectory() as tmp:
            content = Path(tmp)
            poems = content / "poetry/sequence"
            essays = content / "essays/series"
            poems.mkdir(parents=True)
            essays.mkdir(parents=True)
            (poems / "one.md").write_text('---\ntitle: "One --- Two"\npoet: Site Author\n---\n')
            (poems / "index.md").write_text("---\npoet: Collection Editor\n---\n")
            (essays / "one.md").write_text("---\nauthors: [Site Author, Guest]\n---\n")
            (essays / "index.md").write_text("---\nauthors: [Guest]\n---\n")
            self.assertEqual(credited(content, "https://example.org", "Site Author"), {
                "https://example.org/poetry/sequence/one.html": [],
                "https://example.org/essays/series/one.html": ["Site Author", "Guest"],
                "https://example.org/essays/series/": ["Guest"],
            })


@unittest.skipUnless((SITE / "feed.xml").exists(), "build the site first")
class CreditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        feed = ElementTree.parse(SITE / "feed.xml").getroot()
        cls.own = {entry.findtext(f"{ATOM}id"): [a.findtext(f"{ATOM}name") for a in entry.findall(f"{ATOM}author")]
                   for entry in feed.findall(f"{ATOM}entry")}
        config = yaml.safe_load((SITE_ROOT / "site.yaml").read_text(encoding="utf-8"))
        cls.url, cls.author = config["url"], config["author"]

    def test_a_poem_names_its_poet_and_its_year(self) -> None:
        for slug, (poet, year) in POEMS.items():
            with self.subTest(poem=slug):
                source = SITE_ROOT / f"content/poetry/{slug}.md"
                self.assertEqual(front_matter.load(source.read_text(encoding="utf-8"))["poet"], poet)
                page = BeautifulSoup((SITE / f"poetry/{slug}.html").read_text(encoding="utf-8"), "html.parser")
                names = page.select(".meta-authors .meta-author")
                self.assertEqual([n.get_text() for n in names], [poet])
                self.assertEqual(names[0]["data-cite-year"], year)

    def test_the_feed_credits_whoever_wrote_each_entry(self) -> None:
        # The feed holds only the newest entries, so which credited pieces
        # are in it changes as the site grows: each one that is names its
        # poet or its authors, and at least one is.
        expected = credited(SITE_ROOT / "content", self.url, self.author)
        present = {url: names for url, names in expected.items() if url in self.own}
        self.assertTrue(any(present.values()), "no poem or piece another wrote among the feed's entries")
        for url, names in present.items():
            with self.subTest(entry=url):
                self.assertEqual(self.own[url], names)

    def test_the_feed_leaves_the_site_s_author_alone_to_the_feed(self) -> None:
        alone = [entry for entry, names in self.own.items() if names == [self.author]]
        self.assertEqual(alone, [])
        self.assertGreater(sum(1 for names in self.own.values() if not names), 0)


if __name__ == "__main__":
    unittest.main()
