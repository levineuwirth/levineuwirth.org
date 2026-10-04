"""Each section's pages carry its default ornament (build/Sections.hs) unless
their front matter names another. memento-mori's one page is routed to
memento-mori.html, beside its directory, and uses the author's preferred
asterism. Reads the built site."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
DINGBAT_RE = re.compile(r'<body[^>]* data-dingbat="([^"]+)"')


def dingbat(page: str) -> str | None:
    m = DINGBAT_RE.search((SITE / page).read_text(encoding="utf-8"))
    return m.group(1) if m else None


@unittest.skipUnless((SITE / "memento-mori.html").is_file(), "no _site — run `make build`")
class SectionOrnaments(unittest.TestCase):
    def test_memento_mori(self) -> None:
        self.assertNotIn("dingbat:", (ROOT / "content/memento-mori/index.md").read_text(encoding="utf-8"))
        self.assertEqual(dingbat("memento-mori.html"), "asterism")

    def test_routed_sections(self) -> None:
        for page, want in (("essays/asymmetric-forgetting.html", "fleuron"),
                           ("poetry/index.html", "trefoil")):
            with self.subTest(page=page):
                self.assertEqual(dingbat(page), want)


if __name__ == "__main__":
    unittest.main()
