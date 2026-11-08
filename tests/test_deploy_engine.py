"""The deploy answers for the engine as it does for the site.

Once the engine is a repository of its own, linked as engine, the site's
git status no longer sees it. The deploy then refuses an engine with
uncommitted changes, or off main; refuses a site built from another engine
commit, or from an uncommitted one (ENGINE_DEV=1); and pushes the engine's
main before the site's (the author, 2026-11-08). engine.mk's
engine-committed refuses a production build of an uncommitted engine, and
engine-published, for a site that doesn't push its engine, an engine HEAD
its origin lacks. Each case is a scratch site with a copy of the Makefile,
its engine a scratch repository with a bare origin."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SITE_ROOT, engine_path, script_env


def git(where: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.email=test@example.org", "-c", "user.name=Test",
                           "-c", "commit.gpgsign=false", *args], cwd=where,
                          check=True, capture_output=True, text=True).stdout.strip()


class DeployEngine(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="deploy-engine-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.origin = self.root / "origin.git"
        git(self.root, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.engine = self.root / "ozymandias"
        self.engine.mkdir()
        git(self.engine, "init", "-q", "-b", "main")
        shutil.copy2(engine_path("engine.mk"), self.engine / "engine.mk")
        (self.engine / "marker").write_text("one\n")
        git(self.engine, "add", "-A")
        git(self.engine, "commit", "-qm", "one")
        git(self.engine, "remote", "add", "origin", str(self.origin))
        git(self.engine, "push", "-q", "-u", "origin", "main")
        self.site = self.root / "site"
        self.site.mkdir()
        git(self.site, "init", "-q", "-b", "main")
        shutil.copy2(SITE_ROOT / "Makefile", self.site / "Makefile")
        (self.site / "engine").symlink_to("../ozymandias")

    def make(self, *targets: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run(["make", "--no-print-directory", "-C", str(self.site), *targets],
                              env=script_env(**env), capture_output=True, text=True, timeout=60)

    def commit(self, text: str) -> str:
        (self.engine / "marker").write_text(text)
        git(self.engine, "commit", "-qam", text.strip())
        return git(self.engine, "rev-parse", "HEAD")

    def record(self, *lines: str) -> None:
        (self.site / "data").mkdir(exist_ok=True)
        (self.site / "data/last-build-engine.txt").write_text("".join(f"{line}\n" for line in lines))

    def test_a_clean_engine_on_main_passes(self):
        done = self.make("deploy-engine-check")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("the engine is clean at", done.stdout)

    def test_an_engine_with_uncommitted_changes_is_refused(self):
        (self.engine / "marker").write_text("edited\n")
        (self.engine / "new.txt").write_text("")
        done = self.make("deploy-engine-check")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("the engine has uncommitted changes", done.stderr)
        self.assertIn("engine:  M marker", done.stderr)
        self.assertIn("engine: ?? new.txt", done.stderr)
        # Knowingly, and on the record that stays local.
        done = self.make("deploy-engine-check", ALLOW_DIRTY_DEPLOY="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("# engine HEAD:", (self.site / "data/last-deploy-dirty.txt").read_text())

    def test_an_engine_off_main_is_refused(self):
        git(self.engine, "checkout", "-q", "-b", "elsewhere")
        done = self.make("deploy-engine-check")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("the engine is on elsewhere, not main", done.stderr)
        git(self.engine, "checkout", "-q", "--detach")
        self.assertIn("on a detached HEAD", self.make("deploy-engine-check").stderr)

    def test_the_site_must_have_been_built_from_this_engine_commit(self):
        head = git(self.engine, "rev-parse", "HEAD")
        self.assertIn("no data/last-build-engine.txt", self.make("deploy-engine-built").stderr)
        self.record(head)
        self.assertEqual(self.make("deploy-engine-built").returncode, 0)
        self.commit("two\n")
        done = self.make("deploy-engine-built")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("is not the commit the site was built from", done.stderr)

    def test_a_site_built_from_an_uncommitted_engine_is_refused(self):
        self.record(git(self.engine, "rev-parse", "HEAD"), "dirty")
        done = self.make("deploy-engine-built")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("built from an engine with uncommitted changes", done.stderr)
        self.assertEqual(self.make("deploy-engine-built", ALLOW_DIRTY_DEPLOY="1").returncode, 0)

    def test_the_engine_s_main_is_pushed(self):
        head = self.commit("two\n")
        done = self.make("deploy-push-engine")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(git(self.origin, "rev-parse", "main"), head)

    def test_a_failed_engine_push_stops_the_deploy(self):
        self.commit("two\n")
        git(self.engine, "remote", "set-url", "origin", str(self.root / "nowhere.git"))
        done = self.make("deploy-push-engine")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("the engine's push failed", done.stderr)

    def test_a_site_that_doesn_t_push_its_engine_needs_it_published(self):
        self.assertEqual(self.make("engine-published").returncode, 0)
        self.commit("two\n")
        done = self.make("engine-published")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("is not on its origin's main", done.stderr)
        git(self.engine, "push", "-q", "origin", "main")
        self.assertEqual(self.make("engine-published").returncode, 0)

    def test_a_production_build_needs_a_committed_engine(self):
        self.assertEqual(self.make("engine-committed").returncode, 0)
        (self.engine / "marker").write_text("edited\n")
        done = self.make("engine-committed")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("the engine has uncommitted changes", done.stderr)
        self.assertEqual(self.make("engine-committed", ENGINE_DEV="1").returncode, 0)

    def test_an_engine_inside_the_site_is_the_site_s(self):
        # Before A10b: the site's own checks cover engine/, and its push
        # carries it; none of these has anything to do.
        (self.site / "engine").unlink()
        shutil.copytree(self.engine, self.site / "engine", ignore=shutil.ignore_patterns(".git"))
        (self.site / "engine/marker").write_text("edited\n")
        for target in ("deploy-engine-check", "deploy-push-engine", "engine-published"):
            with self.subTest(target=target):
                done = self.make(target)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(done.stdout, "")


if __name__ == "__main__":
    unittest.main()
