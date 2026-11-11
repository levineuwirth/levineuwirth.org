"""The site's stylesheets are wholly in @layer site.

An unlayered sheet beats every layered rule, the engine's and the site's,
whatever its specificity (the engine's tests/test_css_layers.py). B1's first
pass left the Halloween season's so; this keeps every site stylesheet,
seasons and the pages' own included, in the site's layer."""

import unittest

from tests._helpers import SITE_ROOT
from tests.test_css_layers import unlayered


class SiteLayers(unittest.TestCase):
    def test_every_site_stylesheet_is_in_the_site_s_layer(self):
        self.assertEqual(unlayered(SITE_ROOT, "site"), [])


if __name__ == "__main__":
    unittest.main()
