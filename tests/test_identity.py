"""Identity allowances are individual, stale-sensitive and frozen in Git."""
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
import json

import yaml
from tests._helpers import ROOT, load_tool, requires_cabal, site_binary

checker = load_tool("check-identity.py")


def manifest(found):
    return {"bootstrap-parent": "initial", "initial-count": len(found),
            "entries": [dict(id=f"I{i}", **entry) for i, entry in enumerate(found)]}


class IdentityTests(unittest.TestCase):
    def test_each_occurrence_requires_its_own_exact_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "file.txt").write_text("Example Author / Example Author\n")
            found = checker.occurrences(root, ["file.txt"], ["Example Author"])
            self.assertEqual([e["column"] for e in found], [1, 18])
            allowances = manifest(found)
            self.assertEqual(checker.check_occurrences(found, allowances), [])
            allowances["entries"].pop()
            self.assertIn("unallowed", checker.check_occurrences(found, allowances)[0])
            allowances["entries"][0]["line"] += 1
            self.assertIn("stale", checker.check_occurrences(found, allowances)[0])

    def test_longest_match_and_case_variations_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "file.txt").write_text("AUTHOR@EXAMPLE.ORG example.org example")
            found = checker.occurrences(root, ["file.txt"], checker.denylist(
                {"host": "example.org", "email": "author@example.org"}, []))
            self.assertEqual([e["string"] for e in found],
                             ["AUTHOR@EXAMPLE.ORG", "example.org", "example"])

    def test_patterns_are_case_sensitive_and_longest_wins(self):
        # The site's namespace patterns have this shape; a neutral prefix keeps
        # the engine's own tests free of the namespace they guard against.
        patterns = [r"\bqz[A-Z]\w*", r"\bqz:[\w-]+", r"\bdata-qz-[\w-]+", r"--qz-[\w-]+"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "file.js").write_text(
                "window.qzNew = el.dataset.qzSeen; 'qz:ready'; [data-qz-idx]; --qz-gap\n"
                "for (const qz of lines) QZOther(qzlower, qz.length);\n"
                "qzFoo.example.org qzBar\n")
            found = checker.occurrences(root, ["file.js"], ["qzfoo.example.org"], patterns)
            self.assertEqual([(e["line"], e["string"]) for e in found],
                             [(1, "qzNew"), (1, "qzSeen"), (1, "qz:ready"), (1, "data-qz-idx"),
                              (1, "--qz-gap"), (3, "qzFoo.example.org"), (3, "qzBar")])
        for bad in ("qz[", "(qz)?"):
            with self.assertRaises(ValueError):
                checker.scanners([], [bad])

    def test_removal_and_relocation_allowed_but_no_replacement_or_growth(self):
        before = manifest([dict(file="a", line=1, column=1, string="Author"),
                           dict(file="b", line=2, column=1, string="Host")])
        after = copy.deepcopy(before)
        after["entries"].pop()
        after["entries"][0].update(file="engine/a", line=3)
        checker.check_transition(before, after)
        for mutation in (lambda x: x["entries"][0].update(id="new"),
                         lambda x: x["entries"][0].update(string="Different"),
                         lambda x: x.update(**{"initial-count": 3})):
            changed = copy.deepcopy(after)
            mutation(changed)
            with self.assertRaises(ValueError):
                checker.check_transition(before, changed)
        with self.assertRaises(ValueError):
            checker.check_transition(after, before)  # below initial cap is still growth

    def test_committing_an_added_allowance_does_not_approve_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root, text=True,
                                               stderr=subprocess.DEVNULL).strip()
            git("init", "-q")
            git("config", "user.email", "test@example.org")
            git("config", "user.name", "Test")
            git("commit", "--allow-empty", "-qm", "start")
            doc = manifest([dict(file="a", line=1, column=1, string="Author"),
                            dict(file="b", line=1, column=1, string="Host")])
            doc["bootstrap-parent"] = git("rev-parse", "HEAD")
            path = root / checker.ALLOWANCES
            path.parent.mkdir()
            def commit():
                path.write_text(yaml.safe_dump(doc))
                git("add", checker.ALLOWANCES)
                git("commit", "-qm", "allowances")
            checker.check_history(root, doc)
            commit()
            removed = doc["entries"].pop()
            commit()
            checker.check_history(root, doc)
            doc["entries"].append(removed)
            with self.assertRaisesRegex(ValueError, "new or changed"):
                checker.check_history(root, doc)
            commit()
            with self.assertRaisesRegex(ValueError, "new or changed"):
                checker.check_history(root, doc)

            # A shallow checkout of the bad commit must not let that commit
            # present itself as the initial population and approve itself.
            shallow = root / "shallow"
            git("clone", "--quiet", "--depth=1", root.as_uri(), str(shallow))
            with self.assertRaisesRegex(ValueError, "full Git history"):
                checker.check_history(shallow, doc)

    def test_inventory_gives_every_visible_file_an_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                subprocess.run(["git", "-c", "user.email=test@example.org", "-c", "user.name=Test",
                                *args], cwd=root, check=True, capture_output=True)
            git("init", "-q")
            for name in ("Makefile", "README.md", "content/a.md", "data/style.csl", "data/refs.bib",
                         "static/vendor/lib.js", "deleted.txt", checker.PATHS):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text("")
            (root / ".gitignore").write_text("_cache/\n")
            (root / checker.PATHS).write_text("# engine\nMakefile\ndata/style.csl\n")
            policy = {"fixed-strings": [], "fixed-patterns": [],
                      "site-files": [checker.PATHS, ".gitignore", "README.md", "content/", "data/"],
                      "vendored-files": ["static/vendor/", "tools/downloaded"]}
            # A tracked file deleted in the working copy no longer needs one.
            git("add", "deleted.txt")
            git("commit", "-qm", "start")
            (root / "deleted.txt").unlink()
            # data/style.csl is the engine's inside a site directory; vendored
            # files need not be present; ignored files need no owner.
            (root / "_cache").mkdir()
            (root / "_cache/build.o").write_text("")
            self.assertEqual(checker.inventory(root, policy), ["Makefile", "data/style.csl"])
            for name in ("NEW.md", "tests/new.py"):
                (root / name).write_text("")
                with self.assertRaisesRegex(ValueError, rf"unclassified=\['{name}'\]"):
                    checker.inventory(root, policy)
                (root / name).unlink()
            for extra, message in (("gone.txt", r"missing=\['gone.txt'\]"),
                                   ("empty/", r"missing=\['empty/'\]"),
                                   ("Makefile", r"conflicting=\['Makefile'\]")):
                broken = dict(policy, **{"site-files": policy["site-files"] + [extra]})
                with self.assertRaisesRegex(ValueError, message):
                    checker.inventory(root, broken)
            (root / checker.POLICY).write_text(yaml.safe_dump(dict(policy, extra=[])))
            with self.assertRaisesRegex(ValueError, "exactly"):
                checker.load_policy(root)

    @requires_cabal
    def test_engine_identity_allowances(self):
        config = json.loads(subprocess.check_output([str(site_binary()), "config"], cwd=ROOT, text=True))
        checker.check(ROOT, config)
