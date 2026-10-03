"""The .bib files under data/ (audit C07).

A page reads exactly one .bib: its own `bibliography:`, or bibliography.bib.
A paper's .bib is self-contained, so papers may share entries. The general
bibliography.bib must not repeat a paper's: /bibliography/ reads every file,
and a copy that has drifted (abadi2016's author list did) prints there
instead of the one the paper cites.
"""

import re
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
KEY = re.compile(r"^@\w+\s*\{\s*([^,\s]+)\s*,", re.M)


def keys(path: Path) -> list[str]:
    return KEY.findall(path.read_text(encoding="utf-8"))


class BibliographyTests(unittest.TestCase):
    def test_the_general_bibliography_repeats_no_papers_entry(self):
        general = set(keys(DATA / "bibliography.bib"))
        for bib in sorted(DATA.glob("*.bib")):
            if bib.name == "bibliography.bib":
                continue
            with self.subTest(bib=bib.name):
                self.assertEqual(sorted(general & set(keys(bib))), [])

    def test_no_file_defines_a_key_twice(self):
        for bib in sorted(DATA.glob("*.bib")):
            with self.subTest(bib=bib.name):
                ks = keys(bib)
                self.assertEqual(sorted({k for k in ks if ks.count(k) > 1}), [])


if __name__ == "__main__":
    unittest.main()
