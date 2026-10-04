"""The search page's filters against the generator's epistemic vocabularies.

`site epistemic-vocab` prints build/Marks.hs's lists. search-filters.js keeps
its own copy of the ordinal scales, and content/search.md numbers a button
for each value: a filter by button index matches a page only while all three
agree. The JS copy once lacked `local` and `low` (fixed 2026-10-04), so a
filter at or above either matched nothing it should have."""

import importlib.util
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEARCH_FILTERS_JS = REPO_ROOT / "static" / "js" / "search-filters.js"
SEARCH_MD = REPO_ROOT / "content" / "search.md"

_spec = importlib.util.spec_from_file_location("golden", Path(__file__).with_name("test_golden.py"))
_golden = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_golden)


def js_scales() -> dict[str, list[str]]:
    text = SEARCH_FILTERS_JS.read_text(encoding="utf-8")
    m = re.search(r"var SCALES = \{(.*?)\};", text, re.S)
    if not m:
        raise AssertionError("search-filters.js: no `var SCALES = {...};`")
    return {name: re.findall(r"'([^']*)'", values)
            for name, values in re.findall(r"(\w+):\s*\[([^\]]*)\]", m.group(1))}


def ordinal_buttons() -> dict[str, list[tuple[int, str]]]:
    text = SEARCH_MD.read_text(encoding="utf-8")
    buttons: dict[str, list[tuple[int, str]]] = {}
    for field, index, label in re.findall(
            r'<button class="[^"]*filter-ordinal-btn[^"]*" data-field="([^"]+)"'
            r' data-index="(\d+)">([^<]*)</button>', text):
        buttons.setdefault(field, []).append((int(index), label))
    return buttons


@unittest.skipUnless(shutil.which("cabal"), "cabal not on PATH")
class EpistemicVocabularyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run([str(_golden.site_binary()), "epistemic-vocab"],
                             capture_output=True, text=True, check=True)
        cls.vocab = json.loads(out.stdout)

    def test_search_scales_are_the_generators(self) -> None:
        scales = js_scales()
        self.assertEqual(sorted(scales), ["novelty", "practicality", "scope", "stability"])
        for field, values in scales.items():
            with self.subTest(field=field):
                self.assertEqual(values, self.vocab[field])

    def test_each_button_is_its_values_index(self) -> None:
        buttons = ordinal_buttons()
        self.assertEqual(sorted(buttons), sorted(js_scales()))
        for field, found in buttons.items():
            with self.subTest(field=field):
                self.assertEqual(found, list(enumerate(self.vocab[field])))

    def test_peer_status_default_is_listed(self) -> None:
        # Contexts.peerStatusField treats "unreviewed" as the default and
        # validates against the same list.
        self.assertEqual(self.vocab["peer-status"][0], "unreviewed")


if __name__ == "__main__":
    unittest.main()
