"""Every character the built site's maths draws is in the math face's subset.

tools/fonts.yaml cuts Latin Modern Math down to the characters the maths
used when it was cut, with the italic alphabets and the operator, arrow and
double-struck blocks around them. A formula that gains a character the subset
lacks is drawn from another face, and nothing else notices: this names it.
Add it to the family's `unicodes` and rerun engine/tools/subset-fonts.py.
"""

import html
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"


def declared() -> set[int]:
    """The subset's characters: the tool's shared set and the family's own."""
    config = yaml.safe_load((ROOT / "tools/fonts.yaml").read_text(encoding="utf-8"))
    spec = ",".join(filter(None, [config["unicodes"], config["families"]["latinmodernmath"].get("unicodes", "")]))
    found = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        lo, _, hi = part.removeprefix("U+").partition("-")
        found.update(range(int(lo, 16), int(hi or lo, 16) + 1))
    return found


@unittest.skipUnless(SITE.is_dir(), "no _site: run make build")
class MathFont(unittest.TestCase):
    def test_the_subset_covers_the_site_s_maths(self):
        have = declared()
        missing: dict[str, set[str]] = {}
        for page in SITE.rglob("*.html"):
            if "source" in page.relative_to(SITE).parts:
                continue
            text = page.read_text(encoding="utf-8", errors="ignore")
            for formula in re.findall(r"<math\b.*?</math>", text, re.S):
                drawn = re.sub(r"<annotation\b.*?</annotation>", "", formula, flags=re.S)
                for c in html.unescape(re.sub(r"<[^>]+>", "", drawn)):
                    # U+2061 is invisible: MathML spaces it, no glyph is drawn.
                    if not c.isspace() and c != "⁡" and ord(c) not in have:
                        missing.setdefault(f"U+{ord(c):04X} {c}", set()).add(str(page.relative_to(SITE)))
        self.assertEqual(missing, {}, "maths characters the math face's subset lacks (tools/fonts.yaml)")


if __name__ == "__main__":
    unittest.main()
