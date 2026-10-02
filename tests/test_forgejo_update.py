"""Updater failure recovery, with no real Docker or service operations."""

import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/forgejo-update.sh"
STUB = r'''#!/usr/bin/env python3
import os, sys, time
from pathlib import Path
root = Path(os.environ['STUB_ROOT'])
args = sys.argv[1:]
mode = os.environ['STUB_MODE']
applied = root / 'applied'
tag = root / 'tag'
if Path(sys.argv[0]).name == 'curl':
    v = '15.0.1' if applied.exists() else '15.0.0'
    if mode == 'rollback' and applied.exists():
        sys.exit(7)
    print('{"version":"' + v + '"}')
elif args[0] == 'inspect':
    print('sha256:old')
elif args[:2] == ['image', 'inspect']:
    print('sha256:new')
elif args[0] == 'run':
    print('forgejo version 15.0.1')
elif args[0] == 'tag':
    tag.write_text(args[1])
elif args[0] == 'compose':
    if tag.read_text() == 'sha256:old':
        applied.unlink(missing_ok=True)
    else:
        applied.touch()
        if mode == 'interrupt':
            time.sleep(60)
elif args[0] == 'exec' and 'sqlite3' in args:
    if mode == 'sqlite-error':
        print('database is locked', file=sys.stderr)
        sys.exit(1)
    print('ok')
'''


class ForgejoUpdateRecovery(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        for name in ("docker", "curl"):
            path = bin_dir / name
            path.write_text(STUB)
            path.chmod(0o755)
        (self.root / "docker-compose.yml").write_text("image: codeberg.org/forgejo/forgejo:15\n")
        self.hold = self.root / "hold"
        self.attention = self.root / "needs-operator"
        self.env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
                        STUB_ROOT=str(self.root), DIR=str(self.root), BACKUP="true",
                        HOLD=str(self.hold), ATTENTION=str(self.attention),
                        WAIT="1", PRUNE="0", PULL="0", EOL="2099-07-15")

    def run_update(self, mode):
        return subprocess.run(["bash", str(SCRIPT)], env=dict(self.env, STUB_MODE=mode),
                              capture_output=True, text=True, timeout=15)

    def test_failed_integrity_command_leaves_a_sticky_failure(self):
        result = self.run_update("sqlite-error")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.attention.exists(), result.stdout + result.stderr)
        self.assertIn("previous image sha256:old", self.attention.read_text())
        self.assertEqual(self.hold.read_text().strip(), "sha256:new")
        retry = self.run_update("success")
        self.assertNotEqual(retry.returncode, 0)
        self.assertIn("previous update needs the operator", retry.stdout)

    def test_interrupted_replacement_leaves_a_sticky_failure(self):
        with subprocess.Popen(["bash", str(SCRIPT)], env=dict(self.env, STUB_MODE="interrupt"),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              start_new_session=True) as process:
            try:
                deadline = time.monotonic() + 10
                while not (self.root / "applied").exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue((self.root / "applied").exists())
            finally:
                os.killpg(process.pid, signal.SIGTERM)
                process.communicate(timeout=5)
        self.assertTrue(self.attention.exists())
        self.assertEqual(self.hold.read_text().strip(), "sha256:new")

    def test_verified_success_clears_pending_markers(self):
        result = self.run_update("success")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.attention.exists())
        self.assertFalse(self.hold.exists())
        self.assertEqual((self.root / "tag").read_text(), "sha256:new")

    def test_verified_rollback_clears_attention_but_keeps_image_held(self):
        result = self.run_update("rollback")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.attention.exists(), result.stdout + result.stderr)
        self.assertEqual(self.hold.read_text().strip(), "sha256:new")
        self.assertEqual((self.root / "tag").read_text(), "sha256:old")


if __name__ == "__main__":
    unittest.main()
