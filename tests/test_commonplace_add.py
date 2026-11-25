#!/usr/bin/env python3
"""tools/commonplace-add.py: an entry is appended as WRITING.md sets it out
and reads back exactly as given; the book's own bytes are kept, line
endings included; a passage already there (punctuation aside, inside a word
too) is refused; adds at once all land; and nothing beside the book is
touched.

Run with: ``make test`` (or ``python3 -m unittest tests.test_commonplace_add``).
"""

from __future__ import annotations

import datetime
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tests._helpers import SITE_ROOT, load_tool

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

TOOL = SITE_ROOT / "tools" / "commonplace-add.py"
tool = load_tool("commonplace-add.py", site=True)

SONNET = """- text: |-
    Like as the waves make towards the pebbled shore,
    So do our minutes hasten to their end;
  attribution: William Shakespeare
  source: Sonnet 60
  tags: [time, mortality]
  date-added: 2026-03-17
"""


@unittest.skipIf(yaml is None, "PyYAML is required (the site's .venv has it)")
class CommonplaceAdd(unittest.TestCase):
    def setUp(self):
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.book = self.dir / "commonplace.yaml"
        self.book.write_text(SONNET, encoding="utf-8")

    def run_tool(self, *argv: str, stdin: str = "") -> str:
        out = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(out):
            tool.main(["--book", str(self.book), "--date", "2026-11-25", *argv])
        return out.getvalue()

    def last(self) -> dict:
        return yaml.safe_load(self.book.read_text(encoding="utf-8"))[-1]

    def test_an_entry_is_appended_and_reads_back(self):
        passage = "I am a sick man... I am a spiteful man.\nI am an unattractive man."
        self.run_tool("-a", "Fyodor Dostoevsky", "-s", "Notes from Underground: Part I",
                      "-t", "The Will, reason", "-c", "Where the essay begins.", stdin=passage)
        text = self.book.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(SONNET), "the book's own entries changed")
        self.assertEqual(len(yaml.safe_load(text)), 2)
        self.assertEqual(self.last(), {
            "text": passage, "attribution": "Fyodor Dostoevsky",
            "source": "Notes from Underground: Part I", "tags": ["the will", "reason"],
            "commentary": "Where the essay begins.", "date-added": datetime.date(2026, 11, 25)})

    def test_indented_verse_keeps_its_indentation(self):
        for verse in ("    Indented, both lines\n    alike.", "    Indented first,\nthen not."):
            with self.subTest(verse=verse):
                self.run_tool("-a", "Anon", stdin=verse)
                self.assertEqual(self.last()["text"], verse)

    def test_themes_and_names_stay_strings(self):
        self.run_tool("-a", "1984", "-s", "yes", "-t", "0x10, verse [early], no, # hash",
                      "-c", "a: colon", stdin="Some passage.")
        last = self.last()
        self.assertEqual(last["tags"], ["0x10", "verse [early]", "no", "# hash"])
        self.assertEqual((last["attribution"], last["source"], last["commentary"]), ("1984", "yes", "a: colon"))

    def test_a_passage_already_there_is_refused(self):
        for again in ("like as the waves make towards the pebbled shore,\nso do our minutes hasten to their end",
                      "Like as the waves make towards the pebbled shore — so do our minutes hasten to their end!"):
            with self.subTest(again=again), self.assertRaises(SystemExit):
                self.run_tool("-a", "Someone", stdin=again)
        self.assertEqual(self.book.read_text(encoding="utf-8"), SONNET)

    def test_punctuation_inside_a_word_does_not_make_another_passage(self):
        self.run_tool("-a", "Anon", stdin="Don't go.")
        before = self.book.read_bytes()
        for again in ("Dont go.", "Don’t go"):
            with self.subTest(again=again), self.assertRaises(SystemExit):
                self.run_tool("-a", "Anon", stdin=again)
        self.assertEqual(self.book.read_bytes(), before)

    def test_abbreviations_are_one_word_and_symbols_count(self):
        self.run_tool("-a", "Anon", stdin="The U.S. poet.")
        with self.assertRaises(SystemExit):
            self.run_tool("-a", "Anon", stdin="The US poet")
        self.run_tool("-a", "Anon", stdin="We have x < y.")
        self.run_tool("-a", "Anon", stdin="We have x > y.")   # another passage
        self.assertEqual(self.last()["text"], "We have x > y.")

    def test_a_paste_ending_in_blank_lines_is_taken(self):
        self.run_tool("-a", "Anon", stdin="\n  \nA pasted line.   \n   \n\n")
        self.assertEqual(self.last()["text"], "A pasted line.")

    def test_a_date_not_on_the_calendar_is_refused_before_anything(self):
        # Impossible, compact and week dates: fromisoformat takes the last two.
        for date in ("2026-02-30", "20261126", "2026-W48-4"):
            for argv in (["--dry-run"], []):
                stderr = io.StringIO()
                with self.subTest(date=date, argv=argv), mock.patch("sys.stderr", stderr), \
                        self.assertRaises(SystemExit) as err:
                    tool.main(["--book", str(self.book), "--date", date, "-a", "Anon", *argv])
                self.assertEqual(err.exception.code, 2)   # a usage error
                self.assertIn(f"--date: not a date of the calendar, as YYYY-MM-DD: {date}", stderr.getvalue())
        self.assertEqual(self.book.read_text(encoding="utf-8"), SONNET)

    def test_a_blank_attribution_is_refused(self):
        with mock.patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit) as err:
            self.run_tool("-a", "   ", stdin="A passage.")
        self.assertEqual(err.exception.code, 2)
        self.assertEqual(self.book.read_text(encoding="utf-8"), SONNET)

    def test_the_book_s_bytes_and_line_endings_are_kept(self):
        crlf = SONNET.replace("\n", "\r\n").encode("utf-8")
        self.book.write_bytes(crlf)
        self.run_tool("-a", "Anon", stdin="A line.\nAnother.")
        after = self.book.read_bytes()
        self.assertTrue(after.startswith(crlf))
        self.assertNotIn(b"\n", after.replace(b"\r\n", b""), "a bare LF in a CRLF book")
        self.assertEqual(self.last()["text"], "A line.\nAnother.")

    def test_nothing_beside_the_book_is_touched(self):
        backup = self.dir / "commonplace.yaml.bak"
        backup.write_text("mine", encoding="utf-8")
        self.run_tool("-a", "Anon", stdin="A passage.")
        self.assertEqual(backup.read_text(encoding="utf-8"), "mine")
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["commonplace.yaml", "commonplace.yaml.bak"])

    def test_a_dry_run_writes_nothing(self):
        out = self.run_tool("--dry-run", "-a", "Anon", stdin="A short line.")
        self.assertIn('- text: |2-\n    A short line.\n  attribution: "Anon"\n', out)
        self.assertEqual(self.book.read_text(encoding="utf-8"), SONNET)

    def test_an_entry_that_does_not_read_back_leaves_the_book(self):
        with mock.patch.object(tool, "entry", return_value="- text: [unclosed\n"):
            with self.assertRaises(SystemExit):
                self.run_tool("-a", "Anon", stdin="A new line.")
        self.assertEqual(self.book.read_text(encoding="utf-8"), SONNET)
        self.assertEqual([p.name for p in self.dir.iterdir()], ["commonplace.yaml"])

    def test_adds_at_once_all_land(self):
        runs = [subprocess.Popen([sys.executable, str(TOOL), "--book", str(self.book), "-a", "Anon"],
                                 stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                 text=True)
                for _ in range(8)]
        for n, run in enumerate(runs):
            run.stdin.write(f"Passage number {n}.")
            run.stdin.close()
        for run in runs:
            code = run.wait(timeout=60)
            err = run.stderr.read()
            run.stderr.close()
            self.assertEqual(code, 0, err)
        texts = [e["text"] for e in yaml.safe_load(self.book.read_text(encoding="utf-8"))]
        self.assertEqual(sorted(texts[1:]), sorted(f"Passage number {n}." for n in range(8)))


if __name__ == "__main__":
    unittest.main()
