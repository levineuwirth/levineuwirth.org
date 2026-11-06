"""`make deploy`'s two transfers keep earlier versions of the first-party JS and
CSS on the server (engine/tools/asset-versions.py, which has its own tests of
which and for how long). The Makefile's recipes, as written, with real rsync
into a local directory; only ssh is a stand-in, which runs here what it is given.
"""

import datetime as dt
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FAKE_SSH = """#!/bin/sh
# ssh [-l user] host command...: what sshd would do with it, here.
if [ "$1" = -l ]; then shift 2; fi
shift
exec sh -c "$*"
"""


@unittest.skipUnless(shutil.which("rsync") and shutil.which("make"), "rsync and make are needed")
class DeployKeepsVersions(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="deploy-assets-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = self.root / "repo"
        (self.repo / "data").mkdir(parents=True)
        shutil.copy(ROOT / "Makefile", self.repo / "Makefile")
        (self.repo / "engine").symlink_to(ROOT / "engine")
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        (bin_dir / "ssh").write_text(FAKE_SSH)
        (bin_dir / "ssh").chmod(0o755)
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("DEPLOY_", "RSYNC_", "MAKE", "VPS_"))}
        self.env["PATH"] = f"{bin_dir}:{self.env['PATH']}"
        self.built = 1_000_000

    def build(self, version: str) -> None:
        site = self.repo / "_site"
        shutil.rmtree(site, ignore_errors=True)
        (site / f"assets/{version}/js").mkdir(parents=True)
        home = site / "index.html"
        home.write_text(f'<head><meta name="ozy:assets" content="/assets/{version}"></head>')
        # Builds a second apart, of the same size, would look unchanged to rsync.
        self.built += 100
        os.utime(home, (self.built, self.built))
        (site / f"assets/{version}/js/a.js").write_text(version)

    def seed(self, docroot: Path) -> None:
        """A live site as it was before versions."""
        for rel in ("index.html", "stale.txt", "js/old.js", "css/old.css"):
            (docroot / rel).parent.mkdir(parents=True, exist_ok=True)
            (docroot / rel).write_text("before")

    def make(self, target: str, docroot: Path, *variables: str) -> subprocess.CompletedProcess:
        done = subprocess.run(["make", "--no-print-directory", target, "VPS_USER=deployer", "VPS_HOST=vps.test",
                               f"VPS_PATH={docroot}", *variables],
                              cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done

    def age_the_ledger(self, days: int) -> None:
        """Every day in the ledger, so many days earlier."""
        path = self.repo / "data/deployed-assets.json"
        state = json.loads(path.read_text())
        earlier = lambda day: (dt.date.fromisoformat(day) - dt.timedelta(days=days)).isoformat()
        state["replaced"] = {v: earlier(d) for v, d in state["replaced"].items()}
        state["legacy"] = earlier(state["legacy"])
        path.write_text(json.dumps(state))

    def check_a_run_of_deploys(self, deploy, docroot: Path) -> None:
        self.build("aaa")
        deploy()
        self.assertEqual((docroot / "assets/aaa/js/a.js").read_text(), "aaa")
        self.assertFalse((docroot / "stale.txt").exists())
        self.assertEqual((docroot / "js/old.js").read_text(), "before")
        self.assertEqual((docroot / "css/old.css").read_text(), "before")
        self.build("bbb")
        deploy()
        self.assertEqual((docroot / "assets/aaa/js/a.js").read_text(), "aaa")
        self.assertEqual((docroot / "assets/bbb/js/a.js").read_text(), "bbb")
        self.assertIn('content="/assets/bbb"', (docroot / "index.html").read_text())
        self.assertEqual((docroot / "js/old.js").read_text(), "before")
        # Past their days.
        self.age_the_ledger(91)
        self.build("ccc")
        deploy()
        self.assertFalse((docroot / "assets/aaa").exists())
        self.assertFalse((docroot / "js").exists())
        self.assertFalse((docroot / "css").exists())
        self.assertEqual((docroot / "assets/bbb/js/a.js").read_text(), "bbb")
        self.assertEqual((docroot / "assets/ccc/js/a.js").read_text(), "ccc")

    def test_the_transfer_into_the_live_directory(self):
        docroot = self.root / "www/example/site"
        self.seed(docroot)
        self.check_a_run_of_deploys(lambda: self.make("deploy-rsync-inplace", docroot), docroot)

    def test_the_guard_counts_what_the_transfer_will_delete(self):
        docroot = self.root / "www/example/site"
        self.seed(docroot)
        self.build("aaa")
        done = self.make("deploy-rsync-inplace", docroot)
        self.assertIn("deletes 1 file(s)", done.stdout)

    def test_the_transfer_into_a_new_release(self):
        docroot = self.root / "www/example/site"
        releases = Path(f"{docroot}.releases")
        self.seed(releases / "initial")
        docroot.parent.mkdir(parents=True, exist_ok=True)
        docroot.symlink_to(releases / "initial")

        def deploy():
            # A release is named for its second.
            time.sleep(1.1)
            self.make("deploy-rsync-atomic", docroot, "ATOMIC_KEEP=2")

        self.check_a_run_of_deploys(deploy, docroot)
        self.assertTrue(docroot.is_symlink())
        self.assertEqual(sum(1 for _ in releases.iterdir()), 2)


if __name__ == "__main__":
    unittest.main()
