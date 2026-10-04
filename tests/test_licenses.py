"""The compact footer links site licenses; detailed work notices stay published."""

import unittest
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
CC = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
PD = "https://creativecommons.org/publicdomain/mark/1.0/"


@unittest.skipUnless((SITE / "index.html").exists(), "build the site first")
class PublishedLicenseTests(unittest.TestCase):
    def page(self, route):
        return BeautifulSoup((SITE / route).read_text(), "html.parser")

    def test_public_domain_poems_are_not_relicensed(self):
        notices = self.page("licenses.html").find(id="public-domain-works").find_next_sibling("ul")
        for slug in ("sonnet-60", "ozymandias"):
            with self.subTest(poem=slug):
                link = notices.find("a", href=lambda s: s and s.endswith(f"/poetry/{slug}.html"))
                self.assertIsNotNone(link)
                self.assertIn("public domain", link.find_parent("li").get_text())

    def test_original_prose_keeps_its_license(self):
        footer = self.page("memento-mori.html").select_one(".footer-license")
        self.assertIsNotNone(footer.find("a", href=CC))
        self.assertEqual(" ".join(footer.get_text().split()), "CC BY-NC-SA 4.0 · MIT · MM")

    def test_dore_credit_applies_to_the_figure(self):
        img = self.page("memento-mori.html").find("img", src=lambda s: s and "canto31.jpg" in s)
        figure = img.find_parent("figure")
        self.assertIn("Gustave Doré", figure.get_text())
        self.assertIsNotNone(figure.find("a", href=PD))
        self.assertIsNone(figure.select_one('[aria-hidden="true"] a'))

    def test_archive_does_not_claim_the_source_work(self):
        notice = self.page("licenses.html").find(id="archived-material").find_next_sibling("p")
        self.assertIn("licenses do not apply to the preserved works", notice.get_text())

    def test_notices_and_license_texts_are_published(self):
        page = self.page("licenses.html")
        for text in ("VerInf", "monolith", "Bernstein", "Leaflet", "Spectral", "Fira", "Leland"):
            self.assertIn(text, page.get_text())
        links = [urlsplit(urljoin("https://levineuwirth.org/licenses.html", a["href"]))
                 for a in page.select("#markdownBody a[href]")]
        local = [u.path for u in links if u.netloc == "levineuwirth.org"]
        self.assertIn("/licenses/MIT.txt", local)
        self.assertIn("/licenses/CC-BY-NC-SA-4.0.txt", local)
        for path in local:
            with self.subTest(path=path):
                target = SITE / path.lstrip("/")
                if target.is_dir():
                    target /= "index.html"
                self.assertTrue(target.is_file())

    def test_distributed_notices_match_the_repository(self):
        pairs = [(ROOT / "LICENSE", SITE / "licenses/MIT.txt"),
                 (ROOT / "LICENSE-CONTENT", SITE / "licenses/CC-BY-NC-SA-4.0.txt")]
        pairs += [(p, SITE / p.relative_to(ROOT / "static"))
                  for p in (ROOT / "static" / "licenses").glob("*.txt")]
        pairs += [(p, SITE / "fonts" / p.name)
                  for p in (ROOT / "static" / "fonts").glob("OFL-*.txt")]
        for source, published in pairs:
            with self.subTest(source=source.name):
                self.assertEqual(source.read_bytes(), published.read_bytes())
