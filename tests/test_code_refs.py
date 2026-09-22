#!/usr/bin/env python3
"""Tests for tools/code-refs.py link discovery — no network.

Run with: ``python3 -m unittest tests.test_code_refs``.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "code_refs",
    Path(__file__).resolve().parent.parent / "tools" / "code-refs.py",
)
assert _SPEC and _SPEC.loader
code_refs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(code_refs)

SHA = "3508ef1d63d004686e85373f6100689ae94b922a"


def parse(url: str):
    m = code_refs.URL_RE.search(url)
    return code_refs.parse_link(m) if m else None


class ParseLink(unittest.TestCase):
    def test_pinned_blob(self):
        link = parse(f"https://github.com/o/r/blob/{SHA}/analysis/a.md#results")
        self.assertEqual(link["kind"], "blob")
        self.assertEqual(link["ref"], SHA)
        self.assertEqual(link["path"], "analysis/a.md")
        self.assertTrue(link["pinned"])
        # The fragment selects within the snapshot; it is not part of the key.
        self.assertEqual(link["url"], f"https://github.com/o/r/blob/{SHA}/analysis/a.md")

    def test_branch_tree_is_unpinned(self):
        link = parse("https://github.com/o/r/tree/weight-split-model")
        self.assertEqual((link["kind"], link["ref"], link["path"]), ("tree", "weight-split-model", ""))
        self.assertFalse(link["pinned"])

    def test_short_commit(self):
        link = parse("https://github.com/o/r/commit/f426f97")
        self.assertEqual((link["kind"], link["ref"]), ("commit", "f426f97"))
        self.assertTrue(link["pinned"])

    def test_commit_by_branch_rejected(self):
        self.assertIsNone(parse("https://github.com/o/r/commit/main"))

    def test_blob_without_path_rejected(self):
        self.assertIsNone(parse(f"https://github.com/o/r/blob/{SHA}"))

    def test_traversal_rejected(self):
        self.assertIsNone(parse(f"https://github.com/o/r/blob/{SHA}/a/../../x"))
        self.assertIsNone(parse(f"https://github.com/o/r/blob/{SHA}/a/%2e%2e/x"))

    def test_trailing_punctuation_stripped(self):
        link = parse(f"see https://github.com/o/r/tree/{SHA}/profiler.")
        self.assertEqual(link["path"], "profiler")

    def test_bare_repo_not_matched(self):
        self.assertIsNone(parse("https://github.com/o/r"))


class Discover(unittest.TestCase):
    def test_markdown_links_deduplicated(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.md").write_text(
                f"[x](https://github.com/o/r/blob/{SHA}/f.py#L3-L9) and "
                f"[y](https://github.com/o/r/blob/{SHA}/f.py#L20)\n"
            )
            links = code_refs.discover_links(Path(d))
        self.assertEqual(list(links), [f"https://github.com/o/r/blob/{SHA}/f.py"])


if __name__ == "__main__":
    unittest.main()
