"""tools/backup-pair.sh: the archive-and-checksum steps the four VPS backup
scripts share — finalizing a pair, retention over complete pairs only, and
the sweep of what a killed run leaves (cleanup pass, 2026-10-04)."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "tools" / "backup-pair.sh"


def bash(script: str, cwd: Path) -> subprocess.CompletedProcess:
    prelude = f'set -euo pipefail\nlog() {{ echo "log: $*"; }}\ndie() {{ echo "die: $*" >&2; exit 1; }}\n. "{LIB}"\n'
    return subprocess.run(["bash", "-c", prelude + script], cwd=cwd, capture_output=True, text=True, timeout=30)


@unittest.skipUnless(shutil.which("sha256sum"), "sha256sum not installed")
class BackupPairTests(unittest.TestCase):
    def setUp(self):
        self.dest = Path(tempfile.mkdtemp(prefix="backup-pair-"))
        self.addCleanup(shutil.rmtree, self.dest)

    def touch(self, *names):
        for n in names:
            (self.dest / n).write_text(n)

    def test_finalize_writes_a_verifiable_pair_and_announces_nothing(self):
        self.touch(".couchdb-T1.tar.gz.partial")
        done = bash(f'pair_finalize "{self.dest}/.couchdb-T1.tar.gz.partial" '
                    f'"{self.dest}/.couchdb-T1.tar.gz.sha256.partial" "{self.dest}/couchdb-T1.tar.gz"', self.dest)
        self.assertEqual(done.returncode, 0, done.stderr)
        # No LATEST or last-success yet: a script that verifies further
        # publishes only once its check passes.
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()),
                         ["couchdb-T1.tar.gz", "couchdb-T1.tar.gz.sha256"])
        check = subprocess.run(["sha256sum", "-c", "couchdb-T1.tar.gz.sha256"], cwd=self.dest, capture_output=True)
        self.assertEqual(check.returncode, 0)

    def test_publish_points_latest_and_stamps_success(self):
        self.touch("couchdb-T1.tar.gz")
        done = bash(f'pair_publish "{self.dest}/couchdb-T1.tar.gz"', self.dest)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((self.dest / "LATEST").resolve(), (self.dest / "couchdb-T1.tar.gz").resolve())
        self.assertTrue((self.dest / "last-success").read_text().strip())

    def test_lock_refuses_a_second_run(self):
        import fcntl
        with open(self.dest / ".backup.lock", "w") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            done = bash(f'pair_lock "{self.dest}"; echo got-it', self.dest)
        self.assertNotEqual(done.returncode, 0)
        self.assertNotIn("got-it", done.stdout)
        self.assertIn("another backup", done.stderr)
        free = bash(f'pair_lock "{self.dest}"; echo got-it', self.dest)
        self.assertIn("got-it", free.stdout)

    def test_prune_keeps_the_newest_complete_pairs_and_sweeps_debris(self):
        self.touch("anki-20261001.tar.gz", "anki-20261001.tar.gz.sha256",
                   "anki-20261002.tar.gz", "anki-20261002.tar.gz.sha256",
                   "anki-20261003.tar.gz", "anki-20261003.tar.gz.sha256",
                   "anki-20261004.tar.gz",                                  # incomplete: left alone
                   ".anki-20261005.tar.gz.partial", ".anki-20261005.sha256.partial",  # a killed run
                   "anki-20260930.tar.gz.sha256",                           # orphan checksum
                   "couchdb-20261001.tar.gz", ".couchdb-x.partial")         # another set: untouched
        done = bash(f'pair_prune "{self.dest}" anki 2', self.dest)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), [
            ".couchdb-x.partial",
            "anki-20261002.tar.gz", "anki-20261002.tar.gz.sha256",
            "anki-20261003.tar.gz", "anki-20261003.tar.gz.sha256",
            "anki-20261004.tar.gz",
            "couchdb-20261001.tar.gz"])
        self.assertIn("anki-20261004.tar.gz has no .sha256", done.stdout)

    def test_every_backup_script_sources_the_library(self):
        tools = LIB.parent
        for name in ("forgejo-backup.sh", "couchdb-backup.sh", "anki-sync-backup.sh", "vps-config-backup.sh"):
            src = (tools / name).read_text()
            with self.subTest(script=name):
                self.assertIn("backup-pair.sh", src)
                for fn in ("pair_lock", "pair_finalize", "pair_publish", "pair_prune"):
                    self.assertIn(fn, src)
                self.assertNotIn('mv "$TMP_SUM"', src, "a copy of the finalize steps is back")


if __name__ == "__main__":
    unittest.main()
