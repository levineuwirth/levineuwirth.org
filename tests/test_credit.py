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


@unittest.skipUnless((SITE / "feed.xml").exists(), "build the site first")
class CreditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        feed = ElementTree.parse(SITE / "feed.xml").getroot()
        cls.own = {entry.findtext(f"{ATOM}id"): [a.findtext(f"{ATOM}name") for a in entry.findall(f"{ATOM}author")]
                   for entry in feed.findall(f"{ATOM}entry")}
        cls.url = yaml.safe_load((SITE_ROOT / "site.yaml").read_text(encoding="utf-8"))["url"]

    def test_a_poem_names_its_poet_and_its_year(self) -> None:
        for slug, (poet, year) in POEMS.items():
            with self.subTest(poem=slug):
                self.assertEqual(front_matter(f"content/poetry/{slug}.md")["poet"], poet)
                page = BeautifulSoup((SITE / f"poetry/{slug}.html").read_text(encoding="utf-8"), "html.parser")
                names = page.select(".meta-authors .meta-author")
                self.assertEqual([n.get_text() for n in names], [poet])
                self.assertEqual(names[0]["data-cite-year"], year)

    def test_the_feed_credits_each_poem_s_poet(self) -> None:
        for slug, (poet, _) in POEMS.items():
            with self.subTest(poem=slug):
                self.assertEqual(self.own[f"{self.url}/poetry/{slug}.html"], [poet])

    def test_the_feed_credits_each_author_of_a_shared_piece(self) -> None:
        authors = front_matter("content/essays/beyond-comorbidity-indices/index.md")["authors"]
        self.assertEqual(self.own[f"{self.url}/essays/beyond-comorbidity-indices/"],
                         [a.split("|")[0].strip() for a in authors])

    def test_the_feed_leaves_the_site_s_author_alone_to_the_feed(self) -> None:
        author = yaml.safe_load((SITE_ROOT / "site.yaml").read_text(encoding="utf-8"))["author"]
        alone = [entry for entry, names in self.own.items() if names == [author]]
        self.assertEqual(alone, [])
        self.assertGreater(sum(1 for names in self.own.values() if not names), 0)


if __name__ == "__main__":
    unittest.main()
