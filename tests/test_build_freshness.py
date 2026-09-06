#!/usr/bin/env python3
"""Tests for tools/build-freshness.sh — the clean-or-incremental decision.

Each test builds a throwaway Git repository in a temp directory with the
same shape the script expects (build/*.hs, the cabal files, content/,
data/, archive/), copies the script into it, and runs it there with
CLEAN_CMD pointing at a marker file instead of `cabal run site -- clean`.
The real checkout is never touched and no site is ever built.

The behaviour under test is B07: a route can disappear without any file
being deleted. Drop the only `tags: [x]` entry naming a tag and /x/ stays
in _site, where `rsync --delete` keeps it because it still exists locally.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "tools" / "build-freshness.sh"

PAGE = """---
title: An Essay
date: 2026-01-01
tags: [graph-theory, systems]
author: Levi Neuwirth
status: draft
---

Body text. A line here reading `status: shipped` inside prose must not be
mistaken for frontmatter.
"""


def have(binary: str) -> bool:
    return shutil.which(binary) is not None


@unittest.skipUnless(have("git") and have("bash"), "needs git and bash")
class BuildFreshnessTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="freshness-test-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        self._init_repo()

    # -- fixture -----------------------------------------------------------

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _init_repo(self) -> None:
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Freshness Test")

        # The inputs rules_hash() digests.
        self.write("build/Site.hs", "main = pure ()\n")
        self.write("levineuwirth.cabal", "name: site\n")
        self.write("cabal.project", "packages: .\n")
        self.write("cabal.project.freeze", "constraints: base\n")

        self.write("content/essays/one.md", PAGE)
        self.write("data/now.yaml", "status: current\ntags:\n  - now\n")
        self.write("archive/manifest.yaml", "entries: []\n")
        self.write("archive/old-piece/index.txt", "captured text\n")
        self.write("static/style.css", "body{}\n")

        tools = self.root / "tools"
        tools.mkdir(exist_ok=True)
        shutil.copy2(SCRIPT, tools / SCRIPT.name)

        self.git("add", "-A")
        self.git("commit", "-q", "-m", "initial")

        # Seed the state the script reads, as a successful build would.
        self.run_script("stamp")
        # A full rebuild is now on record, so the 7-day clock does not fire.
        (self.root / "data" / "last-full-rebuild.txt").write_text(
            str(int(__import__("time").time())), encoding="utf-8"
        )
        (self.root / "_cache").mkdir(exist_ok=True)

    def run_script(self, arg: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["CLEAN_CMD"] = f"touch {self.root}/CLEANED"
        env["STATE_DIR"] = "data"
        env["CACHE_DIR"] = "_cache"
        return subprocess.run(
            ["bash", str(self.root / "tools" / SCRIPT.name), arg],
            cwd=self.root,
            capture_output=True,
            text=True,
            env=env,
        )

    def cleaned(self) -> bool:
        return (self.root / "CLEANED").exists()

    def check(self) -> str:
        result = self.run_script("check")
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stderr

    # -- baseline ----------------------------------------------------------

    def test_unchanged_tree_builds_incrementally(self):
        self.assertIn("incremental build OK", self.check())
        self.assertFalse(self.cleaned())

    def test_prose_edit_does_not_force_a_clean(self):
        self.write(
            "content/essays/one.md",
            PAGE.replace("Body text.", "Body text, revised."),
        )
        self.assertIn("incremental build OK", self.check())
        self.assertFalse(self.cleaned())

    # -- B07: metadata removal through modification ------------------------

    def test_removing_a_tag_forces_a_clean(self):
        self.write(
            "content/essays/one.md",
            PAGE.replace("tags: [graph-theory, systems]", "tags: [systems]"),
        )
        out = self.check()
        self.assertIn("route metadata changed", out)
        self.assertIn("content/essays/one.md", out)
        self.assertTrue(self.cleaned())

    def test_editing_an_existing_tag_list_forces_a_clean(self):
        # Adding to an existing `tags:` line is still a *change* to a line
        # that previously existed, and the script cannot tell "added
        # proofs" from "renamed systems to proofs" without parsing YAML.
        # It cleans, which is the safe direction.
        self.write(
            "content/essays/one.md",
            PAGE.replace(
                "tags: [graph-theory, systems]",
                "tags: [graph-theory, systems, proofs]",
            ),
        )
        out = self.check()
        self.assertIn("route metadata changed", out)
        self.assertTrue(self.cleaned())

    def test_changing_status_forces_a_clean(self):
        self.write(
            "content/essays/one.md", PAGE.replace("status: draft", "status: stable")
        )
        self.assertIn("route metadata changed", self.check())
        self.assertTrue(self.cleaned())

    def test_removing_an_author_forces_a_clean(self):
        self.write(
            "content/essays/one.md", PAGE.replace("author: Levi Neuwirth\n", "")
        )
        self.assertIn("route metadata changed", self.check())
        self.assertTrue(self.cleaned())

    def test_block_sequence_tag_removal_is_seen(self):
        block = PAGE.replace(
            "tags: [graph-theory, systems]",
            "tags:\n  - graph-theory\n  - systems",
        )
        self.write("content/essays/one.md", block)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "block tags")
        self.run_script("stamp")
        self.write(
            "content/essays/one.md", block.replace("\n  - systems", "")
        )
        self.assertIn("route metadata changed", self.check())
        self.assertTrue(self.cleaned())

    def test_data_yaml_metadata_change_is_seen(self):
        self.write("data/now.yaml", "status: paused\ntags:\n  - now\n")
        self.assertIn("route metadata changed", self.check())
        self.assertTrue(self.cleaned())

    def test_body_text_resembling_frontmatter_is_ignored(self):
        # The document body mentions `status: shipped`; only the block
        # between the leading `---` markers is metadata.
        self.write(
            "content/essays/one.md",
            PAGE.replace("status: shipped", "status: archived"),
        )
        self.assertIn("incremental build OK", self.check())
        self.assertFalse(self.cleaned())

    def test_a_brand_new_page_does_not_force_a_clean(self):
        self.write("content/essays/two.md", PAGE)
        self.assertIn("incremental build OK", self.check())
        self.assertFalse(self.cleaned())

    def test_committed_metadata_change_since_last_build_is_seen(self):
        self.write(
            "content/essays/one.md",
            PAGE.replace("tags: [graph-theory, systems]", "tags: [systems]"),
        )
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "drop a tag")
        self.assertIn("route metadata changed", self.check())
        self.assertTrue(self.cleaned())

    # -- B07: the archive/ pathspec ----------------------------------------

    def test_archive_deletion_forces_a_clean(self):
        shutil.rmtree(self.root / "archive" / "old-piece")
        out = self.check()
        self.assertIn("uncommitted deletions", out)
        self.assertTrue(self.cleaned())

    def test_committed_archive_deletion_forces_a_clean(self):
        shutil.rmtree(self.root / "archive" / "old-piece")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "archive-gc")
        out = self.check()
        self.assertIn("deleted/renamed since last build", out)
        self.assertTrue(self.cleaned())

    # -- pre-existing triggers still work ----------------------------------

    def test_rules_change_forces_a_clean(self):
        self.write("build/Site.hs", "main = print 1\n")
        self.assertIn("build rules changed", self.check())
        self.assertTrue(self.cleaned())

    def test_content_deletion_forces_a_clean(self):
        os.unlink(self.root / "content" / "essays" / "one.md")
        self.assertIn("uncommitted deletions", self.check())
        self.assertTrue(self.cleaned())


if __name__ == "__main__":
    unittest.main()
