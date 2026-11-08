"""The engine's scripts once shared names under `ln`, the site's initials:
`lnUtils`, `ln:content-added`, `data-ln-idx` and the rest, renamed to `ozy` in
A9e. With no allowance left to go stale, the policy's patterns are what keeps
those names out of the engine, so they stay."""

import tempfile
import unittest
from pathlib import Path

from tests._helpers import SITE_ROOT, load_tool

checker = load_tool("check-identity.py")

# A line of each kind the scripts had, and the name in it the check finds.
OLD = (
    ("window.lnUtils.safeStorage", "lnUtils"),
    ("document.addEventListener('ln:content-added', f)", "ln:content-added"),
    ("container.dataset.lnEnhanced = '1'", "lnEnhanced"),
    ("err.lnKind = 'index'", "lnKind"),
    ('[data-ln-idx="3"]', "data-ln-idx"),
    ("color: var(--ln-accent)", "--ln-accent"),
)
NEW = "window.ozyUtils; 'ozy:content-added'; el.dataset.ozyEnhanced; [data-ozy-idx]; window.ozySite\n"


class LnNamespaceTests(unittest.TestCase):
    def found(self, text: str) -> list[str]:
        patterns = checker.load_policy(SITE_ROOT)["fixed-patterns"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "engine").mkdir()
            (root / "engine/a.js").write_text(text, encoding="utf-8")
            return [e["string"] for e in checker.occurrences(root, ["a.js"], [], patterns)]

    def test_the_old_names_are_still_identity(self):
        self.assertEqual(self.found("".join(line + "\n" for line, _ in OLD)), [name for _, name in OLD])

    def test_their_new_names_are_not(self):
        self.assertEqual(self.found(NEW), [])


if __name__ == "__main__":
    unittest.main()
