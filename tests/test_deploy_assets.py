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
import sys
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

# rsync, whose connection drops when told: the transfers after DROP_AFTER never
# happen. Neither a dry run nor the far end of a transfer counts as one.
FAKE_RSYNC = """#!/bin/sh
case "$1" in -an|--server) exec {real} "$@" ;; esac
count=$(( $(cat {count} 2>/dev/null || echo 0) + 1 ))
echo "$count" > {count}
if [ -n "$DROP_AFTER" ] && [ "$count" -gt "$DROP_AFTER" ]; then
  echo "rsync: connection unexpectedly closed" >&2
  exit 12
fi
exec {real} "$@"
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
        self.count = self.root / "transfers"
        (bin_dir / "rsync").write_text(FAKE_RSYNC.format(real=shutil.which("rsync"), count=self.count))
        (bin_dir / "rsync").chmod(0o755)
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("DEPLOY_", "RSYNC_", "MAKE", "VPS_"))}
        self.env["PATH"] = f"{bin_dir}:{self.env['PATH']}"
        for args in (("init", "-q"), ("add", "Makefile", "engine"), ("commit", "-qm", "fixture")):
            subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=test@example.org",
                            "-c", "commit.gpgsign=false", *args], cwd=self.repo,
                           check=True, capture_output=True)
        self.built = 1_000_000

    def build(self, version: str) -> None:
        provenance = self.repo / "engine/tools/build-provenance.py"
        subprocess.run([sys.executable, str(provenance), "begin"], cwd=self.repo,
                       check=True, capture_output=True)
        site = self.repo / "_site"
        shutil.rmtree(site, ignore_errors=True)
        (site / f"assets/{version}/js").mkdir(parents=True)
        home = site / "index.html"
        home.write_text(f'<head><meta name="ozy:assets" content="/assets/{version}"></head>')
        # Builds a second apart, of the same size, would look unchanged to rsync.
        self.built += 100
        os.utime(home, (self.built, self.built))
        (site / f"assets/{version}/js/a.js").write_text(version)
        subprocess.run([sys.executable, str(provenance), "stamp"], cwd=self.repo,
                       check=True, capture_output=True)

    def seed(self, docroot: Path) -> None:
        """A live site as it was before versions."""
        for rel in ("index.html", "stale.txt", "js/old.js", "css/old.css"):
            (docroot / rel).parent.mkdir(parents=True, exist_ok=True)
            (docroot / rel).write_text("before")

    def run_make(self, target: str, docroot: Path, *variables: str) -> subprocess.CompletedProcess:
        return subprocess.run(["make", "--no-print-directory", target, "VPS_USER=deployer", "VPS_HOST=vps.test",
                               f"VPS_PATH={docroot}", *variables],
                              cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=120)

    def make(self, target: str, docroot: Path, *variables: str) -> subprocess.CompletedProcess:
        done = self.run_make(target, docroot, *variables)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done

    def make_fails(self, target: str, docroot: Path, drop_after: int | None = None, *variables: str) -> None:
        """TARGET fails; with DROP_AFTER, because the connection drops after so
        many transfers."""
        self.count.unlink(missing_ok=True)
        if drop_after is not None:
            self.env["DROP_AFTER"] = str(drop_after)
            self.addCleanup(self.env.pop, "DROP_AFTER", None)
        done = self.run_make(target, docroot, *variables)
        self.env.pop("DROP_AFTER", None)
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)

    def ledger(self) -> dict:
        return json.loads((self.repo / "data/deployed-assets.json").read_text())

    def age_the_ledger(self, days: int) -> None:
        """Every day in the ledger, so many days earlier."""
        path = self.repo / "data/deployed-assets.json"
        state = json.loads(path.read_text())
        earlier = lambda day: (dt.date.fromisoformat(day) - dt.timedelta(days=days)).isoformat()
        state["replaced"] = {v: earlier(d) for v, d in state["replaced"].items()}
        state["legacy"] = earlier(state["legacy"]) if state["legacy"] else None
        path.write_text(json.dumps(state))

    def check_a_failed_deploy_costs_nothing(self, deploy, fail, docroot: Path) -> None:
        """A live; B fails; a long time later, C. A has been serving all along."""
        self.build("aaa")
        deploy()
        self.build("bbb")
        fail()
        self.assertEqual(self.ledger()["live"], "aaa")
        self.assertEqual(self.ledger()["replaced"], {})
        self.age_the_ledger(91)
        self.build("ccc")
        deploy()
        self.assertEqual((docroot / "assets/aaa/js/a.js").read_text(), "aaa")
        self.assertEqual((docroot / "assets/ccc/js/a.js").read_text(), "ccc")
        self.assertEqual(self.ledger()["live"], "ccc")
        self.assertEqual(sorted(self.ledger()["replaced"]), ["aaa", "bbb"])
        self.assertEqual(self.ledger()["attempted"], [])

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

    def names(self, docroot: Path) -> str:
        return (docroot / "index.html").read_text()

    def test_the_new_version_arrives_before_any_page_names_it(self):
        docroot = self.root / "www/example/site"
        self.seed(docroot)
        self.build("aaa")
        self.make("deploy-rsync-inplace", docroot)
        self.build("bbb")
        self.make_fails("deploy-rsync-inplace", docroot, 1)
        self.assertEqual((docroot / "assets/bbb/js/a.js").read_text(), "bbb")
        self.assertIn('content="/assets/aaa"', self.names(docroot))
        self.make("deploy-rsync-inplace", docroot)
        self.assertIn('content="/assets/bbb"', self.names(docroot))

    @unittest.skipIf(os.geteuid() == 0, "root can read an unreadable file")
    def test_an_asset_transfer_that_stops_partway_leaves_the_pages_alone(self):
        # Real rsync, failing on one file and carrying on with the rest. In one
        # pass, this is what puts a page on the server without its scripts.
        docroot = self.root / "www/example/site"
        self.seed(docroot)
        self.build("aaa")
        self.make("deploy-rsync-inplace", docroot)
        self.build("bbb")
        unreadable = self.repo / "_site/assets/bbb/js/a.js"
        unreadable.chmod(0)
        self.addCleanup(unreadable.chmod, 0o644)
        self.make_fails("deploy-rsync-inplace", docroot)
        self.assertFalse((docroot / "assets/bbb/js/a.js").exists())
        self.assertIn('content="/assets/aaa"', self.names(docroot))
        self.assertEqual(self.ledger()["live"], "aaa")

    @unittest.skipIf(os.geteuid() == 0, "root can read an unreadable file")
    def test_a_page_transfer_that_stops_partway_leaves_both_versions(self):
        # The home page arrives and another does not: pages of either.
        docroot = self.root / "www/example/site"
        self.seed(docroot)
        self.build("aaa")
        self.make("deploy-rsync-inplace", docroot)
        self.build("bbb")
        unreadable = self.repo / "_site/another.html"
        unreadable.write_text("bbb")
        unreadable.chmod(0)
        self.make_fails("deploy-rsync-inplace", docroot)
        self.assertIn('content="/assets/bbb"', self.names(docroot))
        self.assertFalse((docroot / "another.html").exists())
        for version in ("aaa", "bbb"):
            self.assertEqual((docroot / f"assets/{version}/js/a.js").read_text(), version)
        self.assertEqual(self.ledger(), {**self.ledger(), "live": "aaa", "attempted": ["bbb"]})
        self.build("ccc")
        self.make("deploy-rsync-inplace", docroot)
        for version in ("aaa", "bbb", "ccc"):
            self.assertEqual((docroot / f"assets/{version}/js/a.js").read_text(), version)

    def test_the_asset_transfer_removes_nothing(self):
        docroot = self.root / "www/example/site"
        self.seed(docroot)
        self.build("aaa")
        self.make_fails("deploy-rsync-inplace", docroot, 1)
        self.assertEqual((docroot / "stale.txt").read_text(), "before")
        self.assertEqual((docroot / "index.html").read_text(), "before")

    def test_a_deliberate_first_deploy_into_a_new_directory(self):
        docroot = self.root / "www/example/site"
        docroot.parent.mkdir(parents=True)
        self.build("aaa")
        self.make("deploy-rsync-inplace", docroot, "DEPLOY_NEW_DOCROOT=1")
        self.assertEqual((docroot / "assets/aaa/js/a.js").read_text(), "aaa")
        self.assertIn('content="/assets/aaa"', self.names(docroot))

    def test_a_deploy_the_guard_refuses_leaves_no_trace(self):
        docroot = self.root / "www/example/site"
        docroot.mkdir(parents=True)
        self.build("aaa")
        self.make_fails("deploy-rsync-inplace", docroot)
        self.assertEqual(list(docroot.iterdir()), [])
        self.assertFalse((self.repo / "data/deployed-assets.json").exists())

    def test_a_failed_transfer_into_the_live_directory_costs_nothing(self):
        docroot = self.root / "www/example/site"
        self.seed(docroot)
        self.check_a_failed_deploy_costs_nothing(lambda: self.make("deploy-rsync-inplace", docroot),
                                                 lambda: self.make_fails("deploy-rsync-inplace", docroot, 0),
                                                 docroot)

    def test_a_failed_first_deploy_starts_no_clock_on_the_legacy_paths(self):
        docroot = self.root / "www/example/site"
        self.seed(docroot)
        self.build("aaa")
        self.make_fails("deploy-rsync-inplace", docroot, 0)
        self.assertIsNone(self.ledger()["legacy"])
        self.assertIsNone(self.ledger()["live"])
        self.make("deploy-rsync-inplace", docroot)
        self.assertEqual(self.ledger()["legacy"], dt.date.today().isoformat())
        self.assertEqual((docroot / "js/old.js").read_text(), "before")

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

    def atomic_site(self) -> Path:
        docroot = self.root / "www/example/site"
        releases = Path(f"{docroot}.releases")
        self.seed(releases / "initial")
        docroot.parent.mkdir(parents=True, exist_ok=True)
        docroot.symlink_to(releases / "initial")
        return docroot

    def test_a_failed_transfer_into_a_new_release_costs_nothing(self):
        docroot = self.atomic_site()

        def deploy():
            time.sleep(1.1)
            self.make("deploy-rsync-atomic", docroot)

        def fail():
            time.sleep(1.1)
            self.make_fails("deploy-rsync-atomic", docroot, 0)

        self.check_a_failed_deploy_costs_nothing(deploy, fail, docroot)

    def test_a_release_that_never_goes_live_costs_nothing(self):
        docroot = self.atomic_site()

        def deploy():
            time.sleep(1.1)
            self.make("deploy-rsync-atomic", docroot)

        def fail():
            # All of it transfers, and then the flip is refused: mv will not
            # put a directory over the symlink.
            stuck = Path(f"{docroot}.new")
            stuck.mkdir()
            time.sleep(1.1)
            live = docroot.resolve()
            self.make_fails("deploy-rsync-atomic", docroot)
            self.assertEqual(docroot.resolve(), live)
            shutil.rmtree(stuck)

        self.check_a_failed_deploy_costs_nothing(deploy, fail, docroot)


if __name__ == "__main__":
    unittest.main()
