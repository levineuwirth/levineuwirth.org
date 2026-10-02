#!/usr/bin/env python3
"""Every name the site refuses to publish is also ignored by git.

`make build` commits content/ wholesale and `make deploy` pushes it, so a
private file the build would never serve (build/Site.hs `neverPublish`,
tools/check-site.py PRIVATE_FILE_GLOBS) still reached the public mirror if
.gitignore missed it (audit D03). Both lists are read from their sources,
so a rule added to either without a matching ignore rule fails here.

Run with: ``python3 -m unittest tests.test_gitignore``.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = "content/essays/sample"


def _check_site():
    spec = importlib.util.spec_from_file_location("check_site", ROOT / "tools" / "check-site.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def never_publish() -> dict[str, list[str]]:
    """The suffixes, prefixes and exact names in build/Site.hs `neverPublish`."""
    src = (ROOT / "build" / "Site.hs").read_text(encoding="utf-8")
    lists = {}
    for name in ("suffixes", "prefixes", "exactNames"):
        m = re.search(rf"^\s*{name}\s*=\s*(.*?)\]", src, re.MULTILINE | re.DOTALL)
        assert m, f"neverPublish {name} not found in build/Site.hs"
        body = re.sub(r"--[^\n]*", "", m.group(1))
        lists[name] = re.findall(r'"([^"]*)"', body)
    return lists


def samples() -> list[tuple[str, str]]:
    """(rule, sample file name) for every rule."""
    np = never_publish()
    out = [(f"suffix {s}", "sample.md~" if s == "~" else f"sample{s}") for s in np["suffixes"]]
    out += [(f"prefix {p}", f"{p}sample") for p in np["prefixes"]]
    out += [(f"name {n}", n) for n in np["exactNames"]]
    out += [(f"check-site {g}", g.replace("*", "sample")) for g in _check_site().PRIVATE_FILE_GLOBS]
    return out


@unittest.skipUnless(shutil.which("git"), "git not on PATH")
class PrivateNamesAreIgnored(unittest.TestCase):
    def test_lists_were_read(self):
        np = never_publish()
        self.assertIn(".local.md", np["suffixes"])
        self.assertIn("credentials", np["prefixes"])
        self.assertIn(".netrc", np["exactNames"])

    def test_every_private_name_is_ignored(self):
        names = samples()
        paths = [f"{SAMPLE_DIR}/{name}" for _, name in names]
        # --no-index: judge the rules alone, as the content/ snapshot's
        # `git add` would, whether or not a file exists or is tracked.
        done = subprocess.run(
            ["git", "check-ignore", "--no-index", "--stdin"],
            cwd=ROOT, input="\n".join(paths) + "\n", capture_output=True, text=True,
        )
        ignored = set(done.stdout.split())
        missing = [f"{rule} ({name})" for (rule, name), path in zip(names, paths)
                   if path not in ignored]
        self.assertEqual(missing, [], "add a .gitignore rule for each")

    def test_ordinary_content_is_not_ignored(self):
        for name in ("index.md", "figure.svg", "data.csv", "notes.md"):
            done = subprocess.run(
                ["git", "check-ignore", "--no-index", "-q", f"{SAMPLE_DIR}/{name}"], cwd=ROOT
            )
            self.assertEqual(done.returncode, 1, f"{name} would be ignored")


if __name__ == "__main__":
    unittest.main()
