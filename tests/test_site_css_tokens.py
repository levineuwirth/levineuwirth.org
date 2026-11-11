"""The site sets the default text size, not the size in force.

--text-size is the reader's choice from the settings panel, set on <html>,
or else --text-size-default, which the panel calls 100% (the engine's
tests/test_css_tokens.py). A site sheet that set --text-size would change
the page's size while the panel still measured from the engine's default."""

import unittest

from tests._helpers import SITE_ROOT
from tests.test_css_tokens import text_size_overrides


class SiteTokens(unittest.TestCase):
    def test_no_site_stylesheet_sets_the_size_in_force(self):
        self.assertEqual(text_size_overrides(SITE_ROOT), [])


if __name__ == "__main__":
    unittest.main()
