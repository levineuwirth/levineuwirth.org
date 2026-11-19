"""This site's pages credit whoever wrote them, wherever the site says who did."""

import unittest
from xml.etree import ElementTree

import yaml
from bs4 import BeautifulSoup

from tests._helpers import SITE_ROOT

SITE = SITE_ROOT / "_site"
ATOM = "{http://www.w3.org/2005/Atom}"
POEMS = {"ozymandias": ("Percy Bysshe Shelley", "1818"), "sonnet-60": ("William Shakespeare", "1609")}


def front_matter(rel: str) -> dict:
    return yaml.safe_load((SITE_ROOT / rel).read_text(encoding="utf-8").split("---")[1])


def credited(url: str, author: str) -> dict[str, list[str]]:
    """Each poem's page with a poet: and each essay's with authors:, by its
    URL under `url`, with the names its feed entry gives: none when the
    site's `author` alone wrote it, which the feed's own author covers."""
    found = {}
    for path in sorted((SITE_ROOT / "content/poetry").glob("*.md")):
        if poet := front_matter(str(path.relative_to(SITE_ROOT))).get("poet"):
            found[f"{url}/poetry/{path.stem}.html"] = [poet]
    essays = [(path, f"{path.stem}.html") for path in (SITE_ROOT / "content/essays").glob("*.md")]
    essays += [(path, f"{path.parent.name}/") for path in (SITE_ROOT / "content/essays").glob("*/index.md")]
    for path, route in sorted(essays):
        if authors := front_matter(str(path.relative_to(SITE_ROOT))).get("authors"):
            names = [a.split("|")[0].strip() for a in authors]
            found[f"{url}/essays/{route}"] = [] if names == [author] else names
    return found


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
                self.assertEqual(front_matter(f"content/poetry/{slug}.md")["poet"], poet)
                page = BeautifulSoup((SITE / f"poetry/{slug}.html").read_text(encoding="utf-8"), "html.parser")
                names = page.select(".meta-authors .meta-author")
                self.assertEqual([n.get_text() for n in names], [poet])
                self.assertEqual(names[0]["data-cite-year"], year)

    def test_the_feed_credits_whoever_wrote_each_entry(self) -> None:
        # The feed holds only the newest entries, so which credited pieces
        # are in it changes as the site grows: each one that is names its
        # poet or its authors, and at least one is.
        present = {url: names for url, names in credited(self.url, self.author).items() if url in self.own}
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
