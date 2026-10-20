"""Real Git repositories exercise both directions and the dangerous boundary cases."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("reconcile", Path(__file__).resolve().parents[1] / "tools/forgejo-reconcile.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / "work"
        self.call("init", "-b", "main", str(self.work))
        self.call("config", "user.email", "test@example.invalid", cwd=self.work)
        self.call("config", "user.name", "Test", cwd=self.work)
        self.base = self.commit("base")
        self.gh, self.forge = self.root / "github.git", self.root / "forge.git"
        for remote in (self.gh, self.forge):
            self.call("clone", "--bare", str(self.work), str(remote))
        self.pair = {"id": "project", "github": {"url": str(self.gh)},
                     "forgejo": {"url": str(self.forge)},
                     "branches": [{"github": "main", "forgejo": "main"}]}
        self.config = {"repositories": [self.pair], "minimum_free_bytes": 0}

    def call(self, *args, cwd=None):
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def commit(self, text):
        (self.work / "content").write_text(text)
        self.call("add", ".", cwd=self.work)
        self.call("commit", "-m", text, cwd=self.work)
        return self.call("rev-parse", "HEAD", cwd=self.work)

    def push(self, remote, sha="HEAD"):
        self.call("push", str(remote), sha + ":refs/heads/main", cwd=self.work)

    def head(self, remote):
        return self.call("rev-parse", "refs/heads/main", cwd=remote)

    def run_sync(self, execute=True):
        return sync.run(self.config, self.root / "state", self.root / "cache", execute, allow_local=True)

    def assert_held(self, fragment):
        report = self.run_sync()
        self.assertEqual(report["held"], 1, report)
        self.assertIn(fragment, report["refs"][0]["reason"])

    def test_both_directions_and_dry_run(self):
        ahead = self.commit("github change")
        self.push(self.gh)
        dry = self.run_sync(False)
        self.assertEqual(dry["refs"][0]["status"], "would-update")
        self.assertEqual(self.head(self.forge), self.base)
        self.assertFalse((self.root / "state/agreements.json").exists())
        self.assertEqual(self.run_sync()["updated"], 1)
        self.assertEqual(self.head(self.forge), ahead)
        second = self.commit("forge change")
        self.push(self.forge)
        self.assertEqual(self.run_sync()["updated"], 1)
        self.assertEqual(self.head(self.gh), second)
        self.assertEqual(self.run_sync()["matched"], 1)

    def test_divergence_never_replaces_history(self):
        self.run_sync()
        github_tip = self.commit("github side")
        self.push(self.gh)
        self.call("reset", "--hard", self.base, cwd=self.work)
        forge_tip = self.commit("forge side")
        self.push(self.forge)
        self.assert_held("diverged")
        self.assertEqual(self.head(self.gh), github_tip)
        self.assertEqual(self.head(self.forge), forge_tip)

    def test_reset_on_one_or_both_hosts_is_not_undone(self):
        tip = self.commit("agreed change")
        self.push(self.gh)
        self.run_sync()
        self.call("update-ref", "refs/heads/main", self.base, cwd=self.forge)
        self.assert_held("history rewrite")
        self.assertEqual(self.head(self.forge), self.base)
        self.call("update-ref", "refs/heads/main", self.base, cwd=self.gh)
        self.assert_held("history rewrite")
        state = json.loads((self.root / "state/agreements.json").read_text())
        self.assertEqual(next(iter(state["refs"].values()))["sha"], tip)

    def test_deletion_and_initial_missing_branch_are_held(self):
        self.run_sync()
        self.call("update-ref", "-d", "refs/heads/main", cwd=self.forge)
        self.assert_held("missing")
        (self.root / "state/agreements.json").unlink()
        self.assert_held("missing")
        self.assertEqual(self.call("for-each-ref", "refs/heads", cwd=self.forge), "")

    def test_mapping_change_requires_review(self):
        self.run_sync()
        self.pair["direction"] = "github-to-forgejo"
        self.assert_held("mapping changed")

    def test_visibility_boundary_is_inbound_only(self):
        self.pair["direction"] = "github-to-forgejo"
        self.commit("published change")
        self.push(self.gh)
        self.assertEqual(self.run_sync()["updated"], 1)
        self.commit("private change")
        self.push(self.forge)
        self.assert_held("outbound publishing")

    def test_default_branch_names_can_differ(self):
        self.call("branch", "-m", "main", "master", cwd=self.forge)
        self.pair["branches"][0]["forgejo"] = "master"
        tip = self.commit("new main")
        self.push(self.gh)
        self.assertEqual(self.run_sync()["updated"], 1)
        self.assertEqual(self.call("rev-parse", "master", cwd=self.forge), tip)

    def test_one_failed_repository_does_not_block_other_pairs(self):
        broken = copy.deepcopy(self.pair)
        broken["id"] = "unreachable"
        broken["github"]["url"] = str(self.root / "nonexistent.git")
        broken["forgejo"]["url"] = str(self.root / "also-missing.git")
        self.config["repositories"].insert(0, broken)
        tip = self.commit("healthy change")
        self.push(self.gh)
        report = self.run_sync()
        self.assertEqual((report["held"], report["updated"]), (1, 1))
        self.assertEqual(self.head(self.forge), tip)
        self.assertFalse((self.root / "state/last-success.json").exists())

    def test_concurrent_destination_change_or_deletion_rejects_push(self):
        for mode in ("advance", "delete", "reset"):
            with self.subTest(mode=mode):
                self.setUp_case_for_race(mode)

    def setUp_case_for_race(self, mode):
        # Each subcase gets fresh repositories, but shares the test helpers.
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "destination.git"
            self.call("clone", "--bare", str(self.forge), str(dest))
            self.pair["forgejo"]["url"] = str(dest)
            self.call("reset", "--hard", self.head(self.gh), cwd=self.work)
            tip = self.commit("source " + mode)
            self.push(self.gh)
            expected = self.head(dest)
            real_git = sync.git
            fired = []

            def race(args, *pos, **kwargs):
                if args[0] == "push" and not fired:
                    fired.append(True)
                    if mode == "delete":
                        self.call("update-ref", "-d", "refs/heads/main", cwd=dest)
                    elif mode == "reset":
                        self.call("update-ref", "refs/heads/main", self.base, cwd=dest)
                    else:
                        self.call("reset", "--hard", expected, cwd=self.work)
                        concurrent = self.commit("concurrent target")
                        self.push(dest)
                        fired.append(concurrent)
                return real_git(args, *pos, **kwargs)

            # Use a separate state/cache per case to avoid mapping-change holds.
            # For reset, ensure the target starts above the root commit.
            if mode == "reset":
                self.push(dest, tip)
                self.commit("source after target")
                self.push(self.gh)
            with patch.object(sync, "git", side_effect=race):
                report = sync.run(self.config, Path(directory) / "state", Path(directory) / "cache", True, True)
            self.assertTrue(fired)
            self.assertEqual(report["held"], 1, report)
            if mode == "advance":
                self.assertEqual(self.head(dest), fired[1])
            elif mode == "reset":
                self.assertEqual(self.head(dest), self.base)
            else:
                self.assertEqual(self.call("for-each-ref", "refs/heads", cwd=dest), "")

    def test_disk_floor_and_secret_urls(self):
        self.config["minimum_free_bytes"] = 2**70
        self.assert_held("disk space")
        for url in ("https://token@github.com/a/b", "https://git:secret@github.com/a/b", "ext::anything"):
            self.pair["github"]["url"] = url
            with self.assertRaises(ValueError):
                self.run_sync()


if __name__ == "__main__":
    unittest.main()
