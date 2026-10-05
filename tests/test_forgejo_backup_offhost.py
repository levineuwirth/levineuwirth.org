"""forgejo-backup.sh's off-host copy: borg only. Its rsync and rclone paths
were never configured on the VPS (OFFHOST_TOOL=borg there) and were removed;
a setting naming either must be refused, not quietly sent to borg. The
function is run on its own, with borg and its library stubbed."""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._helpers import TOOLS, script_env, stub_bin

SOURCE = (TOOLS / "forgejo-backup.sh").read_text()
FUNCTION = re.search(r"^offhost_copy\(\) \{\n.*?^\}\n", SOURCE, re.M | re.S).group(0)


class OffhostCopy(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.bin = stub_bin(self.dir / "bin", ["borg"], "#!/bin/sh\nexit 0\n")
        self.lib = self.dir / "borg-offhost.sh"
        self.lib.write_text('borg_offhost_copy() { echo "COPIED $1 $(basename "$2") $BORG_REPO"; }\n')

    def run_copy(self, **env):
        script = ('die() { echo "DIE: $*"; exit 1; }\nlog() { :; }\n' + FUNCTION
                  + 'offhost_copy "$PWD/forgejo-1.tar.gz"\n')
        return subprocess.run(["bash", "-c", script], cwd=self.dir, capture_output=True, text=True,
                              env=script_env(self.bin, **{"OFFHOST_DEST": "ssh://box/./repo",
                                                          "BORG_OFFHOST_LIB": str(self.lib), **env}))

    def test_borg_copies(self):
        done = self.run_copy(OFFHOST_TOOL="borg")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(done.stdout.strip(), "COPIED forgejo forgejo-1.tar.gz ssh://box/./repo")

    def test_rsync_and_rclone_are_refused(self):
        for tool in ("rsync", "rclone"):
            with self.subTest(tool=tool):
                done = self.run_copy(OFFHOST_TOOL=tool)
                self.assertEqual(done.returncode, 1)
                self.assertIn("only borg is", done.stdout)
                self.assertNotIn("COPIED", done.stdout)

    def test_a_missing_library_is_named(self):
        done = self.run_copy(OFFHOST_TOOL="borg", BORG_OFFHOST_LIB=str(self.dir / "absent.sh"))
        self.assertEqual(done.returncode, 1)
        self.assertIn("absent.sh is missing", done.stdout)


if __name__ == "__main__":
    unittest.main()
