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
    if mode == 'unchanged-down' or (mode == 'unchanged-down-after-pull' and (root / 'pulled').exists()):
        sys.exit(7)
    v = '15.0.1' if applied.exists() else '15.0.0'
    if mode.startswith('rollback') and applied.exists():
        sys.exit(7)
    print('{"version":"' + v + '"}')
elif args[0] == 'inspect' and 'RestartCount' in args[2]:
    # The container's state. In crashloop modes the new image restarts on
    # every look; the old one (after a rollback) is normally steady.
    if ((mode.startswith('crashloop') and applied.exists())
            or mode in ('unchanged-crashloop', 'rollback-crashloop')):
        n = root / 'restarts'
        count = int(n.read_text()) + 1 if n.exists() else 1
        n.write_text(str(count))
        print(f'running false {count} 2026-10-04T05:00:{count:02d}Z')
    elif mode == 'stopped' and applied.exists():
        print('exited false 0 2026-10-04T05:00:00Z')
    else:
        print('running false 0 2026-10-04T05:00:00Z')
elif args[0] == 'inspect':
    print('sha256:old')
elif args[0] == 'pull':
    (root / 'pulled').touch()
elif args[0] == 'logs':
    if mode == 'crashloop-migrated' and applied.exists():
        print('2026/10/04 05:00:01 ...Migration[302]: add a column')
elif args[:2] == ['image', 'inspect']:
    print('sha256:old' if mode.startswith('unchanged') else 'sha256:new')
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
                        WAIT="1", STABLE="2", CHECK_EVERY="1",
                        PRUNE="0", PULL="0", EOL="2099-07-15")

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

    def test_a_release_that_answers_then_crash_loops_is_rolled_back(self):
        result = self.run_update("crashloop")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restarted or stopped", result.stdout)
        self.assertEqual(self.hold.read_text().strip(), "sha256:new")
        self.assertEqual((self.root / "tag").read_text(), "sha256:old")
        self.assertFalse(self.attention.exists(), result.stdout + result.stderr)

    def test_a_release_that_crash_loops_after_migrating_is_left_for_the_operator(self):
        result = self.run_update("crashloop-migrated")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NOT rolling back", result.stdout)
        self.assertTrue(self.attention.exists())
        self.assertEqual((self.root / "tag").read_text(), "sha256:new")

    def test_a_release_whose_container_stops_is_rolled_back(self):
        result = self.run_update("stopped")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not running steadily", result.stdout)
        self.assertEqual((self.root / "tag").read_text(), "sha256:old")

    def test_nothing_to_apply_still_fails_when_forgejo_is_not_answering(self):
        result = self.run_update("unchanged-down")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not answering", result.stdout)

    def test_nothing_to_apply_passes_when_forgejo_is_healthy(self):
        result = self.run_update("unchanged")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unchanged", result.stdout)

    def test_nothing_to_apply_rejects_a_loop_between_running_samples(self):
        result = self.run_update("unchanged-crashloop")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("restarted or stopped", result.stdout)
        self.assertFalse((self.root / "tag").exists())

    def test_nothing_to_apply_rechecks_the_api_after_pulling(self):
        self.env["PULL"] = "1"
        result = self.run_update("unchanged-down-after-pull")
        self.assertTrue((self.root / "pulled").exists())
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not answering", result.stdout)
        self.assertFalse((self.root / "tag").exists())

    def test_a_rollback_that_answers_then_crash_loops_keeps_attention(self):
        result = self.run_update("rollback-crashloop")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rollback did not come up and stay up", result.stdout)
        self.assertTrue(self.attention.exists(), result.stdout + result.stderr)
        self.assertEqual(self.hold.read_text().strip(), "sha256:new")
        self.assertEqual((self.root / "tag").read_text(), "sha256:old")

    def test_a_second_run_is_refused_while_one_holds_the_lock(self):
        import fcntl
        lock = self.hold.parent / "lock"
        with open(lock, "w") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_update("success")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("another update is running", result.stdout)
        self.assertFalse((self.root / "applied").exists(), "the refused run touched the forge")


if __name__ == "__main__":
    unittest.main()
