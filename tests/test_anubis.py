"""Opt-in real nginx -> Anubis -> Forgejo rehearsal.

RUN_ANUBIS_TESTS=1 python -m unittest discover -s tests -p test_anubis.py -v
Requires local Docker images, PyYAML, and Playwright Chromium/Firefox.
Only a random loopback TLS port is published. All repos/users are temporary.
"""
import json
import gzip
import os
from pathlib import Path
import re
import secrets
import shutil
import ssl
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('RUN_ANUBIS_TESTS') == '1', 'explicit Anubis rehearsal')
class Anubis(unittest.TestCase):
    @classmethod
    def command(cls, args, **kw):
        return subprocess.run(args, check=True, capture_output=True, text=True, timeout=90, **kw)

    @classmethod
    def setUpClass(cls):
        import yaml
        cls.tmp = Path(tempfile.mkdtemp(prefix='anubis-rehearsal-'))
        cls.prefix = 'anubis-test-' + uuid.uuid4().hex[:10]
        cls.front = cls.prefix + '-nginx'
        cls.backend = cls.prefix + '-forgejo'
        cls.filter = cls.prefix + '-filter'
        cls.volume = cls.prefix + '-data'
        cls.addClassCleanup(cls.cleanup)
        for d in ('logs', 'state'):
            (cls.tmp / d).mkdir()
        (cls.tmp / 'signing.key').write_text(secrets.token_hex(32))
        (cls.tmp / 'signing.key').chmod(0o600)
        cls.command(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                 '-keyout', str(cls.tmp / 'key.pem'), '-out', str(cls.tmp / 'cert.pem'),
                 '-days', '1', '-subj', '/CN=localhost'])
        shutil.copy(ROOT / 'nginx/access-log-format.conf', cls.tmp)
        text = (ROOT / 'nginx/forgejo.conf').read_text()
        text = re.sub(r'(ssl_certificate\s+)[^;]+;', r'\1/work/cert.pem;', text)
        text = re.sub(r'(ssl_certificate_key\s+)[^;]+;', r'\1/work/key.pem;', text)
        text = re.sub(r'^\s*(?:include /etc/letsencrypt/|ssl_dhparam).*$', '', text, flags=re.M)
        text = text.replace('443 ssl', '8443 ssl').replace('listen 80;', 'listen 8088;').replace('[::]:80;', '[::]:8088;')
        text = text.replace('/var/log/nginx/', '/work/logs/')
        (cls.tmp / 'vhost.conf').write_text(text)
        (cls.tmp / 'nginx.conf').write_text('''pid /tmp/nginx.pid;
error_log /work/logs/error.log;
events {}
http {
    client_body_temp_path /tmp/client;
    proxy_temp_path /tmp/proxy;
    fastcgi_temp_path /tmp/fastcgi;
    uwsgi_temp_path /tmp/uwsgi;
    scgi_temp_path /tmp/scgi;
    include /work/access-log-format.conf;
    include /work/vhost.conf;
}
''')
        cls.command(['docker', 'run', '-d', '--pull=never', '--name', cls.front,
                 '--user', f'{os.getuid()}:{os.getgid()}', '-p', '127.0.0.1::8443',
                 '-v', f'{cls.tmp}:/work', '--entrypoint', 'nginx', 'nginx:1.30',
                 '-c', '/work/nginx.conf', '-g', 'daemon off;'])
        port = cls.command(['docker', 'port', cls.front, '8443']).stdout.strip().split(':')[-1]
        cls.base = f'https://localhost:{port}'
        cls.command(['docker', 'run', '-d', '--pull=never', '--name', cls.backend,
                 '--network', 'container:' + cls.front, '-v', cls.volume + ':/data',
                 '-e', 'FORGEJO__security__INSTALL_LOCK=true',
                 '-e', 'FORGEJO__server__ROOT_URL=' + cls.base + '/',
                 '-e', 'FORGEJO__server__DISABLE_SSH=true',
                 '-e', 'FORGEJO__service__DISABLE_REGISTRATION=true',
                 '-e', 'FORGEJO__server__LFS_START_SERVER=false',
                 '-e', 'FORGEJO__packages__ENABLED=false',
                 '-e', 'FORGEJO__security__REVERSE_PROXY_TRUSTED_PROXIES=*',
                 'codeberg.org/forgejo/forgejo:15.0.9'])
        for _ in range(60):
            ready = subprocess.run(['docker', 'exec', cls.front, 'curl', '-fsS',
                                    'http://127.0.0.1:3000/api/v1/version'], capture_output=True)
            if ready.returncode == 0:
                break
            time.sleep(.5)
        else:
            raise RuntimeError('Fixture Forgejo did not start')
        robots = ROOT / 'forgejo/robots.txt'
        if robots.exists():
            cls.command(['docker', 'exec', cls.backend, 'mkdir', '-p', '/data/gitea/public'])
            cls.command(['docker', 'cp', str(robots), cls.backend + ':/data/gitea/public/robots.txt'])
        cls.password = 'local-rehearsal-' + secrets.token_hex(12)
        cls.command(['docker', 'exec', '-u', 'git', cls.backend, 'gitea', 'admin', 'user', 'create',
                 '--username', 'tester', '--password', cls.password, '--email', 'test@example.invalid',
                 '--admin', '--must-change-password=false'])
        cls.token = cls.command(['docker', 'exec', '-u', 'git', cls.backend, 'gitea', 'admin', 'user',
                             'generate-access-token', '--username', 'tester', '--token-name', 'rehearsal',
                             '--scopes', 'all', '--raw']).stdout.strip().splitlines()[-1]
        compose = yaml.safe_load((ROOT / 'anubis/docker-compose.yml').read_text())['services']['anubis']
        cls.healthcheck = compose['healthcheck']['test'][1:]
        env = dict(compose['environment'])
        env.update(POLICY_FNAME='/work/policy.yaml', ED25519_PRIVATE_KEY_HEX_FILE='/work/signing.key',
                   REDIRECT_DOMAINS='localhost:' + port)
        # Production's persistent store, under our fixture mount.
        policy = (ROOT / 'anubis/policy.yaml').read_text().replace('/state/anubis.bdb', '/work/state/anubis.bdb')
        (cls.tmp / 'policy.yaml').write_text(policy)
        cmd = ['docker', 'run', '-d', '--pull=never', '--read-only', '--cap-drop=ALL',
               '--security-opt=no-new-privileges', '--name', cls.filter,
               '--user', f'{os.getuid()}:{os.getgid()}', '--network', 'container:' + cls.front,
               '-v', f'{cls.tmp}:/work']
        for k, v in env.items():
            cmd += ['-e', f'{k}={v}']
        cls.command(cmd + [compose['image']])
        for _ in range(30):
            ready = subprocess.run(['docker', 'exec', cls.filter, *cls.healthcheck], capture_output=True)
            if ready.returncode == 0:
                break
            time.sleep(.25)
        else:
            raise RuntimeError(cls.command(['docker', 'logs', cls.filter]).stderr)
        status, _, body = cls.request('/api/v1/user/repos', method='POST',
                                     data={'name': 'rehearsal', 'auto_init': True}, token=cls.token)
        if status != 201:
            raise RuntimeError(f'Repository fixture creation: {status}, {body[:200]}')

    @classmethod
    def cleanup(cls):
        for name in (cls.filter, cls.backend, cls.front):
            log = subprocess.run(['docker', 'logs', name], capture_output=True, text=True)
            (cls.tmp / (name + '.log')).write_text(log.stdout + log.stderr)
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
        subprocess.run(['docker', 'volume', 'rm', cls.volume], capture_output=True)
        if getattr(cls, 'derived_images', None):
            subprocess.run(['docker', 'image', 'rm', *cls.derived_images,
                            cls.filter + '-rollback:previous'], capture_output=True)
        # Keep the private scratch directory for screenshots and failure logs.
        print('\nAnubis rehearsal artifacts:', cls.tmp)

    @classmethod
    def request(cls, path, *, ua='curl-test', token=None, data=None, method='GET', headers=None):
        hdr = {'User-Agent': ua, 'Accept-Encoding': 'gzip', **(headers or {})}
        if token:
            hdr['Authorization'] = 'token ' + token
        body = None
        if data is not None:
            hdr['Content-Type'] = 'application/json'
            body = json.dumps(data).encode()
        req = urllib.request.Request(cls.base + path, data=body, headers=hdr, method=method)
        try:
            resp = urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=20)
        except urllib.error.HTTPError as err:
            resp = err
        raw = resp.read()
        if resp.headers.get('Content-Encoding') == 'gzip':
            raw = gzip.decompress(raw)
        return resp.status, resp.headers, raw.decode(errors='replace')

    def test_meta_denied_before_exceptions(self):
        for ua in ('meta-externalagent/1.1', 'META-EXTERNALFETCHER/1.0',
                   'facebookexternalhit/1.1', 'Facebot', 'facebookcatalog/1.0', 'FacebookBot', 'meta-webindexer/1.1'):
            for path in ('/tester/rehearsal', '/assets/test.css',
                         '/tester/rehearsal.git/info/refs?service=git-upload-pack', '/api/v1/user'):
                with self.subTest(ua=ua, path=path):
                    self.assertEqual(self.request(path, ua=ua, token=self.token)[0], 403)

    def test_unidentified_clients_and_spoofed_git_ua_are_challenged(self):
        for ua in ('', 'curl/8.0', 'git/2.50', 'Mozilla/5.0'):
            status, _, body = self.request('/tester/rehearsal', ua=ua)
            self.assertEqual(status, 403)
            self.assertIn('anubis', body.lower())
            self.assertIn('Making sure', body)

    def test_api_checks_credentials_and_feeds_work(self):
        for path in ('/api/v1/user', '/api/v1/repos/tester/rehearsal'):
            for scheme in ('token', 'Bearer'):
                with self.subTest(path=path, scheme=scheme):
                    self.assertEqual(self.request(path, headers={'Authorization': scheme + ' ' + self.token})[0], 200)
                    self.assertEqual(self.request(path, headers={'Authorization': scheme + ' invalid-token'})[0], 401)
                    self.assertEqual(self.request(path, ua='FacebookBot', headers={'Authorization': scheme + ' ' + self.token})[0], 403)
        self.assertEqual(self.request('/api/v1/user/repos?limit=100', token=self.token)[0], 200)
        status, headers, _ = self.request('/tester/rehearsal.atom')
        self.assertEqual(status, 200)
        self.assertIn('xml', headers.get('Content-Type', ''))

    def test_machine_requests_never_report_a_successful_challenge(self):
        for path in ('/api/v1/repos/tester/rehearsal', '/api/healthz',
                     '/tester/rehearsal/raw/branch/main/README.md',
                     '/tester/rehearsal/releases/download/v1/example.zip',
                     '/tester/rehearsal.git/info/lfs/objects/batch',
                     '/tester/rehearsal?go-get=1', '/api/packages/tester/generic/test'):
            with self.subTest(path=path):
                status, _, body = self.request(path)
                self.assertEqual(status, 403)
                self.assertIn('Making sure', body)

    def test_meta_can_read_robots_but_not_crawl(self):
        import urllib.robotparser
        for ua in ('meta-externalagent', 'FacebookBot', 'facebookexternalhit', 'curl-test'):
            status, _, body = self.request('/robots.txt', ua=ua)
            self.assertEqual(status, 200)
            parser = urllib.robotparser.RobotFileParser()
            parser.parse(body.splitlines())
            for bot in ('meta-externalagent', 'meta-externalfetcher', 'meta-webindexer',
                        'FacebookBot', 'Facebot', 'facebookcatalog', 'facebookexternalhit'):
                self.assertFalse(parser.can_fetch(bot, self.base + '/tester/rehearsal'))

    def test_search_crawlers_require_the_published_address(self):
        for ua, ip in (('Googlebot (+http://www.google.com/bot.html)', '66.249.66.1'),
                       ('bingbot (+http://www.bing.com/bingbot.htm)', '157.55.39.1')):
            # Public clients cannot impersonate the trusted nginx hop.
            self.assertEqual(self.request('/tester/rehearsal', ua=ua,
                             headers={'X-Real-IP': ip, 'X-Forwarded-For': ip})[0], 403)
            # Inside the isolated fixture only, simulate nginx's verified address.
            def probe(agent, address):
                return self.command(['docker', 'exec', self.front, 'curl', '--compressed', '-sS',
                    '-o', '/dev/null', '-w', '%{http_code}', '-H', 'Host: localhost',
                    '-H', 'X-Real-IP: ' + address, '-A', agent,
                    'http://127.0.0.1:8923/tester/rehearsal']).stdout
            self.assertEqual(probe(ua, ip), '200')
            self.assertEqual(probe(ua, '203.0.113.1'), '403')
            self.assertEqual(probe(ua + ' meta-externalagent', ip), '403')

    def test_git_clone_push_fetch(self):
        ask = self.tmp / 'askpass'
        ask.write_text('#!/bin/sh\nprintf "%s\\n" "$ANUBIS_TEST_TOKEN"\n')
        ask.chmod(0o700)
        env = dict(os.environ, GIT_SSL_NO_VERIFY='true', GIT_TERMINAL_PROMPT='0',
                   GIT_ASKPASS=str(ask), ANUBIS_TEST_TOKEN=self.token)
        clone = self.tmp / 'clone'
        url = self.base.replace('://', '://tester@') + '/tester/rehearsal.git'
        self.command(['git', '-c', 'credential.helper=', 'clone', url, str(clone)], env=env)
        with (clone / 'README.md').open('a') as f:
            f.write('\nAnubis push rehearsal.\n')
        self.command(['git', '-C', str(clone), 'add', 'README.md'])
        self.command(['git', '-C', str(clone), '-c', 'user.name=Rehearsal',
                  '-c', 'user.email=test@example.invalid', 'commit', '-m', 'Rehearsal'])
        self.command(['git', '-C', str(clone), '-c', 'credential.helper=', 'push'], env=env)
        self.command(['git', '-C', str(clone), '-c', 'credential.helper=', 'fetch'], env=env)

    def test_browsers_solve_login_and_keep_cookie_after_restart(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            for engine in ('chromium', 'firefox'):
                with self.subTest(browser=engine):
                    browser = getattr(pw, engine).launch()
                    try:
                        context = browser.new_context(ignore_https_errors=True)
                        page = context.new_page()
                        page.goto(self.base + '/user/login')
                        page.locator('input[name="user_name"]').wait_for(timeout=60000)
                        page.screenshot(path=str(self.tmp / (engine + '-login.png')))
                        page.locator('input[name="user_name"]').fill('tester')
                        page.locator('input[name="password"]').fill(self.password)
                        page.locator('form[action="/user/login"] button').click()
                        page.wait_for_url(lambda u: '/user/login' not in u, timeout=20000)
                        page.goto(self.base + '/tester/rehearsal')
                        page.get_by_text('README.md', exact=True).first.wait_for()
                        cookies = context.cookies()
                        self.assertTrue(any('anubis-auth' in c['name'] for c in cookies))
                        page.screenshot(path=str(self.tmp / (engine + '-repo.png')))
                        # Valid challenge cookies must not bypass the Meta deny.
                        denied = self.request('/tester/rehearsal', ua='meta-externalagent/1.1',
                                              headers={'Cookie': '; '.join(c['name'] + '=' + c['value'] for c in cookies)})
                        self.assertEqual(denied[0], 403)
                        self.command(['docker', 'restart', self.filter])
                        for _ in range(30):
                            healthy = subprocess.run(['docker', 'exec', self.filter, *self.healthcheck], capture_output=True)
                            if healthy.returncode == 0:
                                break
                            time.sleep(.2)
                        response = context.request.get(self.base + '/tester/rehearsal')
                        self.assertEqual(response.status, 200)
                        self.assertNotIn('Making sure', response.text())
                    except Exception:
                        page.screenshot(path=str(self.tmp / (engine + '-failure.png')))
                        (self.tmp / (engine + '-failure.html')).write_text(page.content())
                        raise
                    finally:
                        browser.close()

    def test_z_updater_replaces_and_rolls_back_real_containers(self):
        """Derived fixture images exercise replacement, then a startup failure.

        No release is downloaded: one image only adds a label, the other
        starts Anubis with an invalid policy path. Both use the real binary.
        """
        import importlib.util
        import yaml
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('anubis_update_real', ROOT / 'tools/anubis-update.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fixture = self
        service = yaml.safe_load((ROOT / 'anubis/docker-compose.yml').read_text())['services']['anubis']
        base = service['image']
        service.update(container_name=self.filter, network_mode='container:' + self.front,
                       user=f'{os.getuid()}:{os.getgid()}', volumes=[str(self.tmp) + ':/work'])
        service['environment'].update(POLICY_FNAME='/work/policy.yaml',
                ED25519_PRIVATE_KEY_HEX_FILE='/work/signing.key',
                REDIRECT_DOMAINS=self.base.removeprefix('https://'))
        (self.tmp / 'docker-compose.yml').write_text(json.dumps({'name': self.prefix,
                                                        'services': {'anubis': service}}))
        images = [self.prefix + ':v1.28.0', self.prefix + ':v1.29.0']
        type(self).derived_images = images
        for name, extra in zip(images, ('LABEL rehearsal=accepted',
                     'ENTRYPOINT ["/ko-app/anubis", "--policy-fname=/missing-policy"]')):
            self.command(['docker', 'build', '-q', '-t', name, '-'],
                         input='FROM ' + base + '\n' + extra + '\n')

        class Real(module.Updater):
            next_image = images[0]
            def request(self, port, path, *, ua='anubis-update', address='203.0.113.1', auth=None):
                cmd = ['docker', 'exec', fixture.front, 'curl', '--compressed', '--max-time', '5',
                       '-sS', '-w', '\n%{http_code}', '-H', 'Host: localhost',
                       '-H', 'X-Real-IP: ' + address, '-H', 'X-Forwarded-For: ' + address, '-A', ua]
                if auth:
                    cmd += ['-H', 'Authorization: ' + auth]
                try:
                    body, status = self.command(*cmd, f'http://127.0.0.1:{port}' + path).rsplit('\n', 1)
                except subprocess.CalledProcessError as error:
                    raise OSError('fixture listener is not ready') from error
                return int(status), body.encode(), {}
            def candidate(self, before):
                info = json.loads(self.command('docker', 'image', 'inspect', self.next_image))[0]
                return self.next_image, info['Id']
            def backup(self):
                pass  # Disposable fixture, never a production backup.

        with patch.dict(os.environ, DIR=str(self.tmp), UPDATE_STATE=str(self.tmp / 'update'),
                        PROBE_REPO='/tester/rehearsal', WAIT='3', STABLE='2', CHECK_EVERY='.2'):
            self.command(['docker', 'rm', '-f', self.filter])
            updater = Real()
            updater.compose('up', '-d', '--pull', 'never')
            updater.run()
            good = updater.inspect()['Image']
            self.assertIn('v1.28.0', updater.override.read_text())
            self.assertFalse(updater.hold.exists())
            updater.next_image = images[1]
            with self.assertRaises(OSError):
                updater.run()
            self.assertEqual(updater.inspect()['Image'], good)
            self.assertTrue(updater.hold.exists())
            self.assertFalse(updater.journal.exists())
            self.assertFalse(updater.attention.exists())
            updater.probe()


if __name__ == '__main__':
    unittest.main()
