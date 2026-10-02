"""CouchDB recovery decisions without touching Docker or a real database."""

import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/couchdb-update.sh"
STUB = r'''#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
root = Path(os.environ['STUB_ROOT'])
args = sys.argv[1:]
mode = os.environ['STUB_MODE']
tag = root / 'tag'
applied = root / 'applied'
name = Path(sys.argv[0]).name
if name == 'curl':
    if '--write-out' in args:
        print('503' if mode != 'unguarded' and (root / 'state/maintenance').exists() else '200')
        sys.exit(0)
    sys.stdin.read()
    path = args[-1].split(':5984')[-1]
    if mode == 'bad-count' and path == '/one':
        sys.exit(22)
    if path == '/':
        print(json.dumps({'version': '3.5.2' if applied.exists() else '3.4.2', 'uuid': 'identity'}))
    elif path == '/_up':
        print('{"status":"ok"}')
    elif path.endswith('/cors/origins'):
        print(json.dumps('app://obsidian.md,capacitor://localhost,http://localhost'))
    elif path.endswith('/chttpd_auth/secret'):
        print(json.dumps('wrong' if mode in ('bad-secret', 'rollback-stop-error') and applied.exists() else 'cookie-secret'))
    else:
        print(json.dumps({'doc_count': 0 if mode == 'data-loss' and applied.exists() else 321}))
elif name == 'cp':
    if mode == 'copy-failure':
        sys.exit(1)
    os.execv('/usr/bin/cp', ['cp', *args])
elif args[0] == 'inspect':
    print('sha256:new' if applied.exists() else 'sha256:old')
elif args[:2] == ['image', 'inspect']:
    if '.Id' in args[3]:
        print(tag.read_text())
    else:
        print('COUCHDB_VERSION=3.4.2' if args[-1] == 'sha256:old' else 'COUCHDB_VERSION=3.5.2.1')
elif args[0] == 'tag':
    tag.write_text(args[1])
elif args[:2] == ['compose', 'stop']:
    if mode == 'rollback-stop-error' and applied.exists():
        sys.exit(1)
    (root / 'stopped').touch()
elif args[:2] == ['compose', 'start']:
    (root / 'stopped').unlink(missing_ok=True)
elif args[:2] == ['compose', 'up']:
    if tag.read_text() == 'sha256:old':
        applied.unlink(missing_ok=True)
    else:
        applied.touch()
        if mode == 'interrupt':
            time.sleep(60)
'''


class CouchDBUpdateRecovery(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        for name in ('docker', 'curl', 'cp'):
            path = bin_dir / name
            path.write_text(STUB)
            path.chmod(0o755)
        (self.root / 'docker-compose.yml').write_text('image: couchdb:3\n')
        (self.root / 'server.env').write_text('COUCHDB_USER=admin\nCOUCHDB_PASSWORD=test-secret\n')
        (self.root / 'instance.ini').write_text('[couchdb]\nuuid = identity\n\n[chttpd_auth]\nsecret = cookie-secret\n')
        (self.root / 'local.ini').write_text('[cors]\norigins = app://obsidian.md,capacitor://localhost,http://localhost\n')
        (self.root / 'couchdb-data').mkdir()
        (self.root / 'couchdb-data/data').write_text('original documents')
        (self.root / 'tag').write_text('sha256:new')
        self.state = self.root / 'state'
        self.env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'],
                        STUB_ROOT=str(self.root), DIR=str(self.root), STATE=str(self.state),
                        BACKUP='true', DBS='one two', WAIT='1', PULL='0')

    def run_update(self, mode='success'):
        return subprocess.run(['bash', str(SCRIPT)], env=dict(self.env, STUB_MODE=mode),
                              capture_output=True, text=True, timeout=15)

    def test_interruption_leaves_recovery_details_and_blocks_retry(self):
        with subprocess.Popen(['bash', str(SCRIPT)], env=dict(self.env, STUB_MODE='interrupt'),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              start_new_session=True) as process:
            try:
                deadline = time.monotonic() + 10
                while not (self.root / 'applied').exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue((self.root / 'applied').exists())
            finally:
                os.killpg(process.pid, signal.SIGTERM)
                process.communicate(timeout=5)
        self.assertTrue((self.state / 'needs-operator').exists())
        self.assertIn('sha256:old', (self.state / 'needs-operator').read_text())
        self.assertTrue((self.state / 'maintenance').exists())
        self.assertNotEqual(self.run_update().returncode, 0)

    def test_count_failure_refuses_before_stopping(self):
        result = self.run_update('bad-count')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'stopped').exists(), result.stdout + result.stderr)
        self.assertFalse((self.state / 'maintenance').exists())

    def test_verified_success_clears_markers(self):
        result = self.run_update()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.state / 'needs-operator').exists())
        self.assertFalse((self.state / 'hold').exists())
        self.assertFalse((self.state / 'maintenance').exists())

    def test_missing_proxy_guard_refuses_before_stopping(self):
        result = self.run_update('unguarded')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'stopped').exists())
        self.assertFalse((self.state / 'maintenance').exists())

    def test_failed_cold_copy_resumes_verified_old_server(self):
        result = self.run_update('copy-failure')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'stopped').exists())
        self.assertFalse((self.state / 'maintenance').exists())
        self.assertFalse((self.state / 'needs-operator').exists())

    def test_failed_candidate_stop_never_moves_live_data(self):
        result = self.run_update('rollback-stop-error')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.state / 'needs-operator').exists())
        self.assertTrue((self.state / 'maintenance').exists())
        self.assertFalse(list(self.root.glob('couchdb-data.failed-*')))

    def test_data_loss_rolls_back_and_holds_image(self):
        self.check_rollback('data-loss')

    def test_changed_auth_secret_rolls_back_and_holds_image(self):
        self.check_rollback('bad-secret')

    def check_rollback(self, mode):
        result = self.run_update(mode)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.state / 'hold').read_text().strip(), 'sha256:new')
        self.assertEqual((self.root / 'tag').read_text(), 'sha256:old')
        self.assertEqual((self.root / 'couchdb-data/data').read_text(), 'original documents')
        self.assertFalse((self.state / 'needs-operator').exists())
        self.assertFalse((self.state / 'maintenance').exists())

    def test_empty_identity_refuses_before_stopping(self):
        (self.root / 'instance.ini').write_text('; incomplete file\n')
        result = self.run_update()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'stopped').exists())


if __name__ == '__main__':
    unittest.main()
