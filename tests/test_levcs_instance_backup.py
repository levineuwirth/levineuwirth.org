"""tools/levcs-instance-backup.sh: the LeVCS instance's repositories, nightly.

The job runs against a scratch root (LEVCS_ROOT) with stub systemctl,
levcs-backup and levcs-restore. The stub systemctl keeps the instance's
state in a file, so a test can see that the archive was taken with the
instance stopped and that it was started again however the run ended. The
other two stand in for LeVCS's deploy/levcs-backup and deploy/levcs-restore
by their contract: the first refuses a name that exists and archives the
root as <basename>/; the second installs an archive's root only into a
place that does not exist yet, and refuses an archive in which any
repository fails to verify (here, one holding a BROKEN file). With borg
installed, the archive also goes through a local repository and comes back
through vps-offsite-verify.sh.
"""

import fcntl
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import unittest

from tests._helpers import script_env, stub_bin

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
SCRIPT = TOOLS / 'levcs-instance-backup.sh'
SERVICE = 'levcs-instance.service'
REPO_ID = 'e1a2337a' + '0' * 56

STUBS = {
    'systemctl': '''echo "$*" >> "$CALLS"
case "$1" in
  is-active) cat "$STATE"; [ "$(cat "$STATE")" = active ] ;;
  stop) [ -z "${STOP_FAILS:-}" ] || exit 1; echo inactive > "$STATE" ;;
  start) [ -z "${START_FAILS:-}" ] || exit 1; echo active > "$STATE" ;;
  *) exit 1 ;;
esac''',
    'levcs-backup': '''set -eu
[ -z "${BACKUP_FAILS:-}" ] || { echo "levcs-backup: failed" >&2; exit 1; }
[ "$(cat "$STATE")" != active ] || { echo "levcs-backup: the instance is running" >&2; exit 1; }
[ ! -e "$1" ] || { echo "levcs-backup: $1 exists" >&2; exit 1; }
tar -C "$(dirname "$2")" -czf "$1" "$(basename "$2")"
echo "levcs-backup: $2 archived to $1"''',
    'levcs-restore': '''set -eu
root=${2%/}; name=$(basename "$root")
[ ! -e "$root" ] || { echo "levcs-restore: $root exists" >&2; exit 1; }
staging=$(mktemp -d "$(dirname "$root")/.$name.restore.XXXXXX")
tar -C "$staging" -xzf "$1"
[ -d "$staging/$name" ] || { echo "levcs-restore: holds no $name/ directory" >&2; exit 1; }
for bad in $(find "$staging/$name" -mindepth 2 -maxdepth 2 -name BROKEN); do
  echo "levcs-restore: $(basename "$(dirname "$bad")"): does not verify" >&2; exit 1
done
mv -T "$staging/$name" "$root"
rmdir "$staging"
echo "levcs-restore: $root restored from $1"''',
}


class LevcsInstanceBackup(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='levcs-backup-'))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.root = self.tmp / 'var/lib/levcs'
        (self.root / REPO_ID / '.levcs').mkdir(parents=True)
        (self.root / REPO_ID / '.levcs/objects').write_text('objects\n')
        bin_ = self.tmp / 'bin'
        for name, body in STUBS.items():
            stub_bin(bin_, [name], '#!/bin/sh\n' + body + '\n')
        self.state = self.tmp / 'state'
        self.state.write_text('active\n')
        self.calls = self.tmp / 'calls'
        self.dest = self.tmp / 'dest'
        scratch = self.tmp / 'scratch'
        scratch.mkdir()
        self.env = script_env(bin_, LEVCS_ROOT=str(self.root), DEST=str(self.dest), TMPDIR=str(scratch),
                              STATE=str(self.state), CALLS=str(self.calls),
                              BACKUP_PAIR_LIB=str(TOOLS / 'backup-pair.sh'))

    def run_job(self, *args, env=None, **overrides):
        return subprocess.run(['bash', str(SCRIPT), *args], env=dict(env or self.env, **overrides),
                              text=True, capture_output=True, timeout=120)

    def archive(self):
        return Path(os.readlink(self.dest / 'LATEST'))

    def calls_made(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def instance(self):
        return self.state.read_text().strip()

    def leftovers(self):
        return sorted(p.name for p in self.dest.iterdir() if p.name.endswith('.partial')) \
            + sorted(p.name for p in (self.tmp / 'scratch').iterdir())

    def test_archives_with_the_instance_stopped_and_starts_it_again(self):
        done = self.run_job()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.calls_made(), [f'is-active {SERVICE}', f'stop {SERVICE}', f'start {SERVICE}'])
        self.assertEqual(self.instance(), 'active')
        self.assertRegex(self.archive().name, r'^levcs-\d{8}T\d{6}Z\.tar\.gz$')
        with tarfile.open(self.archive()) as tar:
            self.assertIn(f'levcs/{REPO_ID}/.levcs/objects', tar.getnames())
        check = subprocess.run(['sha256sum', '-c', self.archive().name + '.sha256'], cwd=self.dest,
                               capture_output=True)
        self.assertEqual(check.returncode, 0)
        self.assertTrue((self.dest / 'last-success').exists())
        self.assertIn('restores (1 repository, each verified', done.stdout)
        self.assertEqual(self.leftovers(), [])

    def test_a_failed_archive_publishes_nothing_and_the_instance_is_started_again(self):
        for failure in ('BACKUP_FAILS', 'STOP_FAILS'):
            with self.subTest(failure):
                self.calls.unlink(missing_ok=True)
                self.state.write_text('active\n')
                done = self.run_job(**{failure: '1'})
                self.assertNotEqual(done.returncode, 0)
                self.assertEqual(self.calls_made()[-1], f'start {SERVICE}')
                self.assertEqual(self.instance(), 'active')
                self.assertFalse((self.dest / 'LATEST').exists())
                self.assertFalse((self.dest / 'last-success').exists())
                self.assertEqual(self.leftovers(), [])

    def test_an_instance_that_does_not_start_again_fails_the_run(self):
        done = self.run_job(START_FAILS='1')
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('did NOT start again', done.stderr + done.stdout)
        self.assertFalse((self.dest / 'LATEST').exists())

    def test_an_instance_found_stopped_or_failed_is_archived_and_left_so(self):
        for state in ('inactive', 'failed'):
            with self.subTest(state):
                self.calls.unlink(missing_ok=True)
                self.state.write_text(state + '\n')
                done = self.run_job()
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(self.calls_made(), [f'is-active {SERVICE}'])
                self.assertEqual(self.instance(), state)
                self.assertIn(f'leaving it {state}', done.stdout)
                time.sleep(1.1)   # the next archive gets a new timestamped name

    def test_an_instance_in_any_other_state_is_stopped_first(self):
        # Waiting out its RestartSec, the instance reads "activating", and
        # would come up while the root is being read.
        self.state.write_text('activating\n')
        done = self.run_job()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.calls_made(), [f'is-active {SERVICE}', f'stop {SERVICE}', f'start {SERVICE}'])

    def test_an_archive_that_does_not_restore_is_not_published(self):
        self.assertEqual(self.run_job().returncode, 0)
        latest, stamp = self.archive(), (self.dest / 'last-success').read_text()
        time.sleep(1.1)
        (self.root / REPO_ID / 'BROKEN').write_text('')
        done = self.run_job()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('does not verify', done.stderr)
        self.assertEqual(self.archive(), latest)
        self.assertEqual((self.dest / 'last-success').read_text(), stamp)
        self.assertEqual(self.instance(), 'active')
        self.assertEqual(self.leftovers(), [])

    def test_a_second_run_into_the_same_dest_is_refused_and_harms_nothing(self):
        self.dest.mkdir(parents=True)
        partial = self.dest / '.levcs-20261031T000000Z.tar.gz.partial'
        partial.write_text('a running backup')
        with open(self.dest / '.backup.lock', 'w') as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            done = self.run_job()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('another backup', done.stderr)
        self.assertTrue(partial.exists(), "the refused run swept the other run's archive")
        self.assertEqual(self.calls_made(), [], 'the refused run touched the instance')

    def test_the_archive_and_its_directory_are_private(self):
        self.assertEqual(self.run_job().returncode, 0)
        self.assertEqual(stat.S_IMODE(self.dest.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.archive().stat().st_mode), 0o600)

    def test_verify_fails_a_damaged_archive_and_one_without_repositories(self):
        self.assertEqual(self.run_job().returncode, 0)
        done = self.run_job('--verify')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(str(self.archive()), done.stdout)
        empty = self.tmp / 'levcs-empty.tar.gz'
        (self.tmp / 'empty/levcs').mkdir(parents=True)
        with tarfile.open(empty, 'w:gz') as tar:
            tar.add(self.tmp / 'empty/levcs', arcname='levcs')
        subprocess.run(f'sha256sum {empty.name} > {empty.name}.sha256', shell=True, cwd=self.tmp, check=True)
        done = self.run_job('--verify', str(empty))
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('no repository', done.stderr)
        archive = self.archive()
        archive.write_bytes(archive.read_bytes()[:-100])
        done = self.run_job('--verify')
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('checksum mismatch', done.stderr)
        self.assertEqual(len(self.calls_made()), 3, '--verify touched the instance')
        self.assertEqual(self.leftovers(), [])

    @unittest.skipUnless(shutil.which('borg'), 'borg not installed')
    def test_off_host_copy_restores_through_the_monthly_verify(self):
        repo = self.tmp / 'repo'
        env = dict(self.env, BORG_REPO=str(repo), BORG_PASSPHRASE='test',
                   BORG_CACHE_DIR=str(self.tmp / 'borg-cache'),
                   BORG_SECURITY_DIR=str(self.tmp / 'borg-security'),
                   BORG_OFFHOST_LIB=str(TOOLS / 'borg-offhost.sh'),
                   BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK='yes')
        subprocess.run(['borg', 'init', '--encryption=repokey', str(repo)], env=env,
                       check=True, capture_output=True, timeout=60)
        done = self.run_job(env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.dest / 'last-offhost-success').exists())
        verify = subprocess.run(['bash', str(TOOLS / 'vps-offsite-verify.sh')],
                                env=dict(env, OFFSITE_PREFIXES='levcs', VERIFY_BIN_DIR=str(TOOLS)),
                                text=True, capture_output=True, timeout=300)
        self.assertEqual(verify.returncode, 0, verify.stderr)
        self.assertIn('restores (1 repository', verify.stdout)


if __name__ == '__main__':
    unittest.main()
