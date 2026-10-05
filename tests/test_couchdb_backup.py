"""Credential handling at the scratch Docker boundary."""

import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

from tests._helpers import script_env

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/couchdb-backup.sh'


class CouchDBBackupCredentials(unittest.TestCase):
    def test_scratch_password_is_in_environment_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'backup.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                info = tarfile.TarInfo('manifest')
                info.size = 0
                tar.addfile(info, io.BytesIO())
            archive.with_suffix('.gz.sha256').write_text(
                hashlib.sha256(archive.read_bytes()).hexdigest() + '  backup.tar.gz\n')
            docker = root / 'docker'
            docker.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
if sys.argv[1] == 'run':
    Path(os.environ['RECORD']).write_text(json.dumps({'args': sys.argv[1:], 'password': os.environ.get('COUCHDB_PASSWORD')}))
    sys.exit(1)  # Stop at this boundary; no database or real Docker is needed.
''')
            docker.chmod(0o755)
            record = root / 'record.json'
            env = script_env(root, RECORD=str(record), COUCHDB_IMAGE='test-image',
                       BACKUP_PAIR_LIB=str(SCRIPT.parent / 'backup-pair.sh'))
            result = subprocess.run(['bash', str(SCRIPT), '--verify', str(archive)],
                                    env=env, text=True, capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            data = json.loads(record.read_text())
            self.assertTrue(data['password'])
            self.assertNotIn(data['password'], ' '.join(data['args']))
            self.assertIn('COUCHDB_PASSWORD', data['args'])


if __name__ == '__main__':
    unittest.main()
