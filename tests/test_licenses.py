"""The compact footer links site licenses; detailed work notices stay published."""

import unittest

from tests._helpers import SITE_ROOT, engine_path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

SITE = SITE_ROOT / "_site"
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
        self.assertEqual(" ".join(footer.get_text().split()), "CC BY-NC-SA 4.0 · GPL-2.0-or-later · MM")

    def test_a_public_domain_poem_says_so_in_its_footer(self):
        for slug in ("sonnet-60", "ozymandias"):
            with self.subTest(poem=slug):
                footer = self.page(f"poetry/{slug}.html").select_one(".footer-license")
                self.assertIsNotNone(footer.find("a", href=PD, rel="license"))
                self.assertIsNone(footer.find("a", href=CC))
                self.assertEqual(" ".join(footer.get_text().split()), "Public domain · GPL-2.0-or-later · MM")

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
        self.assertIn("/licenses/GPL-2.0-or-later.txt", local)
        self.assertIn("/licenses/Ozymandias.txt", local)
        self.assertIn("/licenses/MIT-through-0ff8792.txt", local)
        self.assertIn("/licenses/CC-BY-NC-SA-4.0.txt", local)
        for path in local:
            with self.subTest(path=path):
                target = SITE / path.lstrip("/")
                if target.is_dir():
                    target /= "index.html"
                self.assertTrue(target.is_file())

    def test_the_site_and_the_engine_give_the_same_terms(self):
        # The grant and the permission for generated websites, then the FSF's
        # text; each notice differs only in what it says of itself.
        rule = "\n" + "-" * 72 + "\n\n"
        ours, engine = ((path).read_text(encoding="utf-8") for path in (SITE_ROOT / "LICENSE", engine_path("LICENSE")))
        self.assertEqual(ours.split(rule)[1], engine.split(rule)[1])

        def terms(notice: str) -> str:
            head = notice.split(rule)[0]
            return head[head.index("Copyright (C)"):head.index("Earlier versions")]

        self.assertEqual(terms(ours), terms(engine))
        self.assertIn("Copyright (C) 2026 Levi Neuwirth", terms(ours))

    def test_the_earlier_grant_stays_published_as_it_was(self):
        earlier = (SITE_ROOT / "static/licenses/MIT-through-0ff8792.txt").read_text(encoding="utf-8")
        self.assertTrue(earlier.startswith("Scope: this MIT licence applies"))
        self.assertIn("MIT License\n\nCopyright (c) 2026 Levi Neuwirth\n", earlier)
        self.assertIn("MIT-through-0ff8792.txt", (SITE_ROOT / "LICENSE").read_text(encoding="utf-8"))

    def test_distributed_notices_match_the_repository(self):
        pairs = [(SITE_ROOT / "LICENSE", SITE / "licenses/GPL-2.0-or-later.txt"),
                 (engine_path("LICENSE"), SITE / "licenses/Ozymandias.txt"),
                 (SITE_ROOT / "LICENSE-CONTENT", SITE / "licenses/CC-BY-NC-SA-4.0.txt")]
        # The engine's notices and the site's.
        for static in dict.fromkeys((engine_path("static"), SITE_ROOT / "static")):
            pairs += [(p, SITE / p.relative_to(static))
                      for p in (static / "licenses").glob("*.txt")]
        pairs += [(p, SITE / "fonts" / p.name)
                  for p in (SITE_ROOT / "static" / "fonts").glob("OFL-*.txt")]
        for source, published in pairs:
            with self.subTest(source=source.name):
                self.assertEqual(source.read_bytes(), published.read_bytes())
