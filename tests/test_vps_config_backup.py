"""tools/vps-config-backup.sh: the host's own configuration, off-host (audit Y13).

The job runs against a scratch root (CONFIG_ROOT) with stub pacman, docker,
systemctl and ip, so what it archives — and what it must leave out — can be
checked without a VPS. With borg installed, the archive also goes through a
local repository and comes back through vps-offsite-verify.sh.
"""

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
SCRIPT = TOOLS / 'vps-config-backup.sh'

FILES = {
    'etc/nginx/nginx.conf': 'http {}\n',
    'etc/nginx/sites-available/levineuwirth.org': 'server {}\n',
    'etc/letsencrypt/live/levineuwirth.org/privkey.pem': 'KEY\n',
    'etc/default/anki-sync-backup': 'BORG_REPO=x\n',
    'etc/borg/passphrase': 'the repository passphrase\n',
    'root/couchdb-server/docker-compose.yml': 'services: {}\n',
    'root/couchdb-server/instance.ini': '[couchdb]\nuuid = u\n',
    'root/couchdb-server/couchdb-data/shards/db.couch': 'data\n',
    'root/couchdb-server/couchdb-data.pre-20261002T000000Z/shards/db.couch': 'old data\n',
    'root/anubis-server/docker-compose.yml': 'services: {}\n',
    'root/anubis-server/docker-compose.override.yml': '{"services": {}}\n',
    'root/anubis-server/policy.yaml': 'bots: []\n',
    'root/anubis-server/signing.key': 'SECRET SIGNING KEY\n',
    'root/anubis-server/state/anubis.bdb': 'ephemeral challenges\n',
    'root/forgejo-server/docker-compose.yml': 'services: {}\n',
    'root/forgejo-server/forgejo-data/gitea/gitea.db': 'db\n',
    'root/.ssh/config': 'Host storagebox\n',
    'root/.ssh/id_storagebox': 'PRIVATE KEY\n',
    'usr/local/bin/forgejo-backup.sh': '#!/bin/sh\n',
    'var/lib/couchdb-update/hold': 'sha256:abc\n',
    'var/lib/anubis-update/hold': '{"image_id": "sha256:abc"}\n',
    'var/lib/anubis-update/previous-state/anubis.bdb': 'cold rollback copy\n',
}

STUBS = {
    'pacman': 'echo nginx; echo borg',
    'docker': '''case "$1 $2" in
  "network ls") echo n1 ;;
  "network inspect") echo '[{"Name":"proxy-net","IPAM":{"Config":[{"Subnet":"172.18.0.0/16","Gateway":"172.18.0.1"}]}}]' ;;
  *) echo "docker $*" ;;
esac''',
    'systemctl': 'echo "systemctl $*"',
    'ip': 'echo "eth0 UP 178.104.77.249/32"',
}


class ConfigBackup(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='config-backup-'))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.root = self.tmp / 'root'
        for rel, text in FILES.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        bin_ = self.tmp / 'bin'
        bin_.mkdir()
        for name, body in STUBS.items():
            (bin_ / name).write_text('#!/bin/sh\n' + body + '\n')
            (bin_ / name).chmod(0o755)
        self.dest = self.tmp / 'dest'
        self.env = dict(os.environ, PATH=f'{bin_}{os.pathsep}{os.environ["PATH"]}',
                        CONFIG_ROOT=str(self.root), DEST=str(self.dest), TMPDIR=str(self.tmp),
                        BACKUP_PAIR_LIB=str(TOOLS / 'backup-pair.sh'))
        self.env.pop('BORG_REPO', None)

    def run_job(self, *args, env=None):
        return subprocess.run(['bash', str(SCRIPT), *args], env=env or self.env,
                              text=True, capture_output=True, timeout=120)

    def archive(self):
        return Path(os.readlink(self.dest / 'LATEST'))

    def test_archives_the_configuration_and_leaves_out_data_and_the_passphrase(self):
        done = self.run_job()
        self.assertEqual(done.returncode, 0, done.stderr)
        with tarfile.open(self.archive()) as tar:
            names = {n.lstrip('./') for n in tar.getnames()}
            networks = json.load(tar.extractfile('./inventory/docker-networks.json'))
        for kept in ('etc/nginx/nginx.conf', 'etc/letsencrypt/live/levineuwirth.org/privkey.pem',
                     'root/couchdb-server/instance.ini', 'root/forgejo-server/docker-compose.yml',
                     'root/anubis-server/policy.yaml', 'root/anubis-server/signing.key',
                     'root/anubis-server/docker-compose.override.yml',
                     'var/lib/anubis-update/hold', 'var/lib/anubis-update/previous-state/anubis.bdb',
                     'root/.ssh/config', 'usr/local/bin/forgejo-backup.sh', 'var/lib/couchdb-update/hold',
                     'inventory/packages.txt'):
            self.assertIn(kept, names)
        for left_out in ('etc/borg/passphrase', 'root/.ssh/id_storagebox',
                         'root/couchdb-server/couchdb-data/shards/db.couch',
                         'root/couchdb-server/couchdb-data.pre-20261002T000000Z/shards/db.couch',
                         'root/anubis-server/state/anubis.bdb',
                         'root/forgejo-server/forgejo-data/gitea/gitea.db'):
            self.assertNotIn(left_out, names)
        self.assertEqual(networks[0]['IPAM']['Config'][0]['Gateway'], '172.18.0.1')

    def test_the_archive_and_its_directory_are_private(self):
        self.assertEqual(self.run_job().returncode, 0)
        self.assertEqual(stat.S_IMODE(self.dest.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.archive().stat().st_mode), 0o600)

    def test_verify_fails_a_damaged_archive_and_one_holding_the_passphrase(self):
        self.assertEqual(self.run_job().returncode, 0)
        self.assertEqual(self.run_job('--verify').returncode, 0)
        # A complete archive that also holds the passphrase is refused.
        unpacked = self.tmp / 'unpacked'
        with tarfile.open(self.archive()) as tar:
            tar.extractall(unpacked, filter='data')
        (unpacked / 'etc/borg').mkdir()
        (unpacked / 'etc/borg/passphrase').write_text('secret\n')
        bad = self.tmp / 'config-bad.tar.gz'
        with tarfile.open(bad, 'w:gz') as tar:
            tar.add(unpacked, arcname='.')
        subprocess.run(f'sha256sum {bad.name} > {bad.name}.sha256', shell=True, cwd=self.tmp, check=True)
        done = self.run_job('--verify', str(bad))
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('etc/borg', done.stderr)
        archive = self.archive()
        archive.write_bytes(archive.read_bytes()[:-100])
        self.assertNotEqual(self.run_job('--verify').returncode, 0)

    @unittest.skipUnless(shutil.which('borg'), 'borg not installed')
    def test_off_host_copy_restores_through_the_monthly_verify(self):
        repo = self.tmp / 'repo'
        env = dict(self.env, BORG_REPO=str(repo), BORG_PASSPHRASE='test',
                   BORG_OFFHOST_LIB=str(TOOLS / 'borg-offhost.sh'),
                   BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK='yes')
        subprocess.run(['borg', 'init', '--encryption=repokey', str(repo)], env=env,
                       check=True, capture_output=True, timeout=60)
        done = self.run_job(env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.dest / 'last-offhost-success').exists())
        verify = subprocess.run(['bash', str(TOOLS / 'vps-offsite-verify.sh')],
                                env=dict(env, OFFSITE_PREFIXES='config', VERIFY_BIN_DIR=str(TOOLS)),
                                text=True, capture_output=True, timeout=300)
        self.assertEqual(verify.returncode, 0, verify.stderr)
        self.assertIn('restores', verify.stdout)


if __name__ == '__main__':
    unittest.main()
