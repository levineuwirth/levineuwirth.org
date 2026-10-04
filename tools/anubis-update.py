#!/usr/bin/env python3
"""Apply stable Anubis 1.x releases, with a cold state copy and durable rollback.

No third-party Python dependencies. The image override is JSON (valid YAML),
so ordinary `docker compose up` also uses the last accepted digest.
"""
import fcntl
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

REGISTRY = 'ghcr.io/techarohq/anubis'
RELEASES = 'https://api.github.com/repos/TecharoHQ/anubis/releases/latest'


def log(message):
    print('anubis-update: ' + message, flush=True)


def atomic(path, value):
    tmp = path.with_suffix(path.suffix + '.new')
    with tmp.open('w') as stream:
        json.dump(value, stream)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def release_tag(data):
    tag = data.get('tag_name', '')
    if data.get('draft') or data.get('prerelease') or not re.fullmatch(r'v1\.\d+\.\d+', tag):
        raise RuntimeError('latest release is not a stable 1.x version; manual review required')
    return tag


def version(reference):
    match = re.search(r':v(\d+)\.(\d+)\.(\d+)(?:@|$)', reference)
    if not match:
        raise RuntimeError('image must name a version and digest: ' + reference)
    return tuple(map(int, match.groups()))


class Updater:
    def __init__(self):
        self.directory = Path(os.environ.get('DIR', '/root/anubis-server'))
        self.state = Path(os.environ.get('UPDATE_STATE', '/var/lib/anubis-update'))
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.override = self.directory / 'docker-compose.override.yml'
        self.journal = self.state / 'pending.json'
        self.hold = self.state / 'hold'
        self.attention = self.state / 'needs-operator'
        self.saved = self.state / 'previous-state'
        self.stable = int(os.environ.get('STABLE', '120'))
        self.interval = float(os.environ.get('CHECK_EVERY', '5'))
        self.wait = int(os.environ.get('WAIT', '60'))
        self.repo = os.environ.get('PROBE_REPO', '/neuwirth/levineuwirth.org')
        self.container = 'anubis'

    def command(self, *args, timeout=300):
        return subprocess.run(args, cwd=self.directory, capture_output=True, text=True,
                              check=True, timeout=timeout).stdout.strip()

    def compose(self, *args):
        return self.command('docker', 'compose', *args)

    def inspect(self):
        # Do not print an inspection's environment or mount secrets.
        return json.loads(self.command('docker', 'inspect', self.container))[0]

    def request(self, port, path, *, ua='anubis-update', address='203.0.113.1', auth=None):
        headers = {'Host': 'git.levineuwirth.org', 'User-Agent': ua,
                   'X-Real-IP': address, 'X-Forwarded-For': address, 'Accept-Encoding': 'gzip'}
        if auth:
            headers['Authorization'] = auth
        req = urllib.request.Request(f'http://127.0.0.1:{port}' + path, headers=headers)
        try:
            response = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(2_000_000)
            if response.headers.get('Content-Encoding') == 'gzip':
                body = gzip.decompress(body)
            return response.status, body, response.headers

    def probe(self):
        def check(path, status, contains=None, forbidden=None, **kw):
            got, body, _ = self.request(8923, path, **kw)
            if (got != status or (contains is not None and contains not in body)
                    or (forbidden is not None and forbidden in body)):
                raise RuntimeError(f'probe {path}: expected {status}, got {got} or wrong content')
        if self.request(9091, '/healthz')[0] != 200:
            raise RuntimeError('private health endpoint failed')
        check(self.repo, 403, b'Making sure')
        check(self.repo, 403, forbidden=b'Making sure', ua='meta-externalagent/1.1')
        check('/robots.txt', 200, b'User-agent: meta-externalagent', ua='FacebookBot')
        for scheme in ('token', 'Bearer'):
            check('/api/v1/user', 401, auth=scheme + ' anubis-update-invalid')
        check(self.repo + '.git/info/refs?service=git-upload-pack', 200, b'git-upload-pack')
        check(self.repo + '.atom', 200, b'<feed')
        for ua, ip in (('Googlebot (+http://www.google.com/bot.html)', '66.249.66.1'),
                       ('bingbot (+http://www.bing.com/bingbot.htm)', '157.55.39.1')):
            check(self.repo, 200, b'<html', ua=ua, address=ip)
            check(self.repo, 403, b'Making sure', ua=ua)
            check(self.repo, 403, forbidden=b'Making sure', ua=ua + ' meta-externalagent', address=ip)

    def healthy(self, image_id):
        deadline = time.monotonic() + self.wait
        while True:
            try:
                self.probe()
                break
            except (RuntimeError, OSError, urllib.error.URLError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(self.interval)
        def stamp():
            data = self.inspect()
            s = data['State']
            if data['Image'] != image_id or s['Status'] != 'running' or s['Restarting']:
                raise RuntimeError('container is not running the expected image steadily')
            return s['StartedAt'], data['RestartCount']
        first = stamp()
        deadline = time.monotonic() + self.stable
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(self.interval, remaining))
            if stamp() != first:
                raise RuntimeError('container restarted during the stability window')
        self.probe()

    def candidate(self, before):
        request = urllib.request.Request(RELEASES, headers={'User-Agent': 'levineuwirth-anubis-update',
                                                           'Accept': 'application/vnd.github+json'})
        with urllib.request.urlopen(request, timeout=30) as response:
            tag = release_tag(json.load(response))
        ref = REGISTRY + ':' + tag
        if version(ref) < version(before):
            raise RuntimeError('latest release is older than the installed version; refusing downgrade')
        self.command('docker', 'pull', ref, timeout=600)
        image = json.loads(self.command('docker', 'image', 'inspect', ref))[0]
        digests = [d for d in image['RepoDigests'] if d.startswith(REGISTRY + '@sha256:')]
        if len(digests) != 1 or not re.fullmatch(REGISTRY + r'@sha256:[0-9a-f]{64}', digests[0]):
            raise RuntimeError('could not resolve an unambiguous registry digest')
        return ref + '@' + digests[0].split('@')[1], image['Id']

    def select(self, reference):
        atomic(self.override, {'services': {'anubis': {'image': reference}}})

    def backup(self):
        self.command('systemctl', 'start', 'vps-config-backup.service', timeout=2400)

    def rollback(self, pending):
        log('restoring previous image and cold challenge state')
        self.compose('stop', 'anubis')
        self.select(pending['before'])
        if pending['state_saved']:
            # Keep the saved copy intact if recovery itself is interrupted.
            live = self.directory / 'state'
            if live.exists():
                shutil.rmtree(live)
            shutil.copytree(self.saved, live, copy_function=shutil.copy2)
            for item in (live, *live.rglob('*')):
                original = (self.saved / item.relative_to(live)).stat()
                os.chown(item, original.st_uid, original.st_gid)
        self.compose('up', '-d', '--no-deps', '--pull', 'never', 'anubis')
        self.healthy(pending['before_id'])
        self.journal.unlink()
        self.attention.unlink(missing_ok=True)
        log('rollback verified; failed image remains on hold')

    def recover(self, pending):
        try:
            self.rollback(pending)
        except Exception:
            atomic(self.attention, pending)
            raise

    def run(self):
        if self.attention.exists():
            raise RuntimeError('a rollback needs the operator; see ' + str(self.attention))
        if self.journal.exists():
            self.recover(json.loads(self.journal.read_text()))
            raise RuntimeError('recovered an interrupted update; review the journal before retrying')
        config = json.loads(self.compose('config', '--format', 'json'))['services']['anubis']
        self.container = config['container_name']
        before = config['image']
        version(before)
        running = self.inspect()['Image']
        configured = json.loads(self.command('docker', 'image', 'inspect', before))[0]['Id']
        if running != configured:
            raise RuntimeError('running image differs from Compose; reconcile before updating')
        self.healthy(running)
        candidate, image_id = self.candidate(before)
        if image_id == running:
            # Pulling and release discovery may take time; check again afterwards.
            self.healthy(running)
            log('unchanged, healthy: ' + before)
            return
        if self.hold.exists() and json.loads(self.hold.read_text())['image_id'] == image_id:
            raise RuntimeError('candidate failed previously and is on hold: ' + candidate)
        self.backup()
        self.command('docker', 'tag', running, self.container + '-rollback:previous')
        pending = {'before': before, 'before_id': running, 'candidate': candidate,
                   'image_id': image_id, 'state_saved': False}
        atomic(self.hold, pending)
        atomic(self.journal, pending)
        try:
            self.compose('stop', 'anubis')
            if self.saved.exists():
                shutil.rmtree(self.saved)
            self.command('cp', '-a', str(self.directory / 'state'), str(self.saved))
            pending['state_saved'] = True
            atomic(self.journal, pending)
            self.select(candidate)
            self.compose('up', '-d', '--no-deps', '--pull', 'never', 'anubis')
            self.healthy(image_id)
        except BaseException as error:
            log('replacement failed: ' + str(error))
            self.recover(pending)
            raise
        self.journal.unlink()
        self.hold.unlink(missing_ok=True)
        log('applied and stable: ' + candidate)


def main():
    os.umask(0o077)
    updater = Updater()
    with (updater.state / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        def interrupted(signum, frame):
            raise RuntimeError('interrupted by signal ' + str(signum))
        signal.signal(signal.SIGTERM, interrupted)
        updater.run()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        log(str(error))
        sys.exit(1)
