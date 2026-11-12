"""The site sets the default text size, not the size in force, and writes
no system-dark copy of its dark rules, which the build writes (the engine's
tests/test_themes.py).

--text-size is the reader's choice from the settings panel, set on <html>,
or else --text-size-default, which the panel calls 100% (the engine's
tests/test_css_tokens.py). A site sheet that set --text-size would change
the page's size while the panel still measured from the engine's default."""

import unittest

from tests._helpers import SITE_ROOT
from tests.test_css_tokens import text_size_overrides
from tests.test_themes import hand_copies


class SiteTokens(unittest.TestCase):
    def test_no_site_stylesheet_sets_the_size_in_force(self):
        self.assertEqual(text_size_overrides(SITE_ROOT), [])

    def test_no_site_stylesheet_copies_the_dark_theme_by_hand(self):
        found = {str(p.relative_to(SITE_ROOT)): hand_copies(p.read_text(encoding="utf-8"))
                 for p in sorted((SITE_ROOT / "static/css").rglob("*.css"))}
        self.assertEqual({k: v for k, v in found.items() if v}, {})


if __name__ == "__main__":
    unittest.main()
