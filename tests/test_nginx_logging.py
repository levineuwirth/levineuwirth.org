"""Real nginx logging rehearsal: RUN_NGINX_TESTS=1 python -m unittest discover
-s tests -p test_nginx_logging.py -v. Requires Docker and nginx:1.30 locally.
No public ports, production files, or external network are used.
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('RUN_NGINX_TESTS') == '1', 'explicit Docker rehearsal')
class NginxLogging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='nginx-logging-'))
        cls.addClassCleanup(shutil.rmtree, cls.tmp)
        # Docker writes as our uid, so cleanup never needs root.
        for name in ('conf.d', 'sites-enabled', 'snippets', 'logs', 'site', 'certs'):
            (cls.tmp / name).mkdir()
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(cls.tmp / 'certs/key.pem'),
                        '-out', str(cls.tmp / 'certs/cert.pem'), '-days', '1',
                        '-subj', '/CN=localhost'], check=True, capture_output=True)
        companions = ('access-log-format.conf', 'csp-report-format.conf',
                      'csp-report-zone.conf', 'anki-sync-zone.conf', 'popup-proxy-cache.conf')
        for name in companions:
            text = (ROOT / 'nginx' / name).read_text()
            text = text.replace('/var/cache/nginx/popup-proxy', '/tmp/popup-cache')
            (cls.tmp / 'conf.d' / name).write_text(text)
        snippets = ('security-headers.conf', 'security-framing.conf', 'csp-report.conf',
                    'static-assets.conf', 'popup-proxy.conf', 'archive.conf')
        for name in snippets:
            text = (ROOT / 'nginx' / name).read_text()
            # The stock image has gzip but not Arch's optional Brotli modules.
            text = re.sub(r'^brotli(?:_static)?\s+.*$', '', text, flags=re.M)
            text = text.replace('/var/log/nginx/', '/work/logs/')
            text = text.replace('/srv/http/levineuwirth.org', '/work/site')
            (cls.tmp / 'snippets' / name).write_text(text)
        for name in ('levineuwirth.conf', 'forgejo.conf', 'anki-sync.conf',
                     'couchdb-sync.conf', 'default-server.conf'):
            text = (ROOT / 'nginx' / name).read_text()
            text = text.replace('/var/log/nginx/', '/work/logs/')
            text = text.replace('/srv/http/levineuwirth.org', '/work/site')
            text = re.sub(r'(ssl_certificate\s+)[^;]+;', r'\1/work/certs/cert.pem;', text)
            text = re.sub(r'(ssl_certificate_key\s+)[^;]+;', r'\1/work/certs/key.pem;', text)
            text = re.sub(r'^\s*(?:include /etc/letsencrypt/|ssl_dhparam).*$', '', text, flags=re.M)
            text = re.sub(r'listen (\[::\]:)?80;', r'listen \g<1>8088;', text)
            text = re.sub(r'listen\s+(\[::\]:)?80 default_server;', r'listen \g<1>8088 default_server;', text)
            text = re.sub(r'listen\s+(\[::\]:)?443 ssl', r'listen \g<1>8443 ssl', text)
            # All proxied services get the same deterministic fixture backend.
            text = re.sub(r'127\.0\.0\.1:(3000|8080|5984)', '127.0.0.1:9090', text)
            (cls.tmp / 'sites-enabled' / name).write_text(text)
        config = (ROOT / 'nginx/nginx.conf').read_text()
        config = config.replace('include modules.d/*.conf;', '')
        config = config.replace('include      mime.types;', 'include /etc/nginx/mime.types;')
        config = config.replace('/etc/nginx/', '/work/').replace('include /work/mime.types;', 'include /etc/nginx/mime.types;')
        config = config.replace('/var/log/nginx/', '/work/logs/')
        config = 'pid /tmp/nginx.pid;\nerror_log /work/logs/error.log;\n' + config
        # A slow static fixture and an HTTP backend exercise both timings.
        config = config.replace('include /work/sites-enabled/*;', '''
        client_body_temp_path /tmp/client;
        proxy_temp_path /tmp/proxy;
        fastcgi_temp_path /tmp/fastcgi;
        uwsgi_temp_path /tmp/uwsgi;
        scgi_temp_path /tmp/scgi;
        include /work/sites-enabled/*;
        server {
            listen 9090;
            access_log off;
            location / { return 200 "backend\\n"; }
        }
        ''')
        (cls.tmp / 'nginx.conf').write_text(config)
        (cls.tmp / 'site/index.html').write_text('home\n')
        (cls.tmp / 'site/404.html').write_text('custom missing page\n')
        (cls.tmp / 'site/fast.css').write_text('body {}\n')
        (cls.tmp / 'site/fonts').mkdir()
        (cls.tmp / 'site/fonts/fast.woff2').write_text('font\n')
        site = cls.tmp / 'sites-enabled/levineuwirth.conf'
        text = site.read_text().replace('location / {', '''location = /slow.css {
            limit_rate 512;
            access_log /work/logs/site.access.json.log access_json if=$log_asset;
        }
        location / {''', 1)
        site.write_text(text)
        (cls.tmp / 'site/slow.css').write_bytes(b'x' * 1536)
        cls.container = 'nginx-logging-' + uuid.uuid4().hex[:12]
        cls.addClassCleanup(subprocess.run, ['docker', 'rm', '-f', cls.container],
                            capture_output=True)
        done = subprocess.run(['docker', 'run', '-d', '--pull=never', '--network', 'none',
                               '--name', cls.container, '--user', f'{os.getuid()}:{os.getgid()}',
                               '-v', f'{cls.tmp}:/work', '--entrypoint', 'nginx',
                               'nginx:1.30', '-p', '/work/', '-c', '/work/nginx.conf',
                               '-g', 'daemon off;'], text=True, capture_output=True)
        if done.returncode:
            raise RuntimeError(done.stderr)
        check = subprocess.run(['docker', 'exec', cls.container, 'nginx', '-t',
                                '-p', '/work/', '-c', '/work/nginx.conf'],
                               text=True, capture_output=True)
        if check.returncode:
            logs = subprocess.run(['docker', 'logs', cls.container], capture_output=True, text=True)
            raise RuntimeError(check.stderr + logs.stderr)

    def request(self, host, path='/', *, tls=True, method='GET', data=None, extra=()):
        cmd = ['docker', 'exec', self.container, 'curl', '-sk', '--resolve',
               f'{host}:{8443 if tls else 8088}:127.0.0.1', '-X', method,
               '-o', '/dev/null', '-w', '%{http_code}', *extra]
        if data is not None:
            cmd += ['--data-binary', data]
        cmd += [f'{"https" if tls else "http"}://{host}:{8443 if tls else 8088}{path}']
        r = subprocess.run(cmd, text=True, capture_output=True, timeout=15)
        if r.returncode not in (0, 52):
            self.fail(r.stderr)
        return r.stdout

    def records(self, file):
        # USR1 flushes buffered logs, just as rotation does.
        subprocess.run(['docker', 'kill', '--signal=USR1', self.container], check=True, capture_output=True)
        time.sleep(.15)
        path = self.tmp / 'logs' / file
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_separation_redaction_and_backend_timings(self):
        for host, name in [('levineuwirth.org', 'site'), ('git.levineuwirth.org', 'forgejo'),
                           ('anki.levineuwirth.org', 'anki-sync'), ('sync.levineuwirth.org', 'couchdb-sync')]:
            ua = 'test "quoted" \\ agent'
            self.assertEqual(self.request(host, '/?token=secret', extra=(
                '-A', ua, '-e', 'https://example.org/private?secret=value',
                '-H', 'Authorization: Bearer TOPSECRET', '-H', 'Cookie: secret=COOKIE')), '200')
            self.assertEqual(self.request(host, '/redirect?token=secret', tls=False), '301')
            rows = self.records(name + '.access.json.log')
            record = next(r for r in reversed(rows) if r['path'] == '/')
            self.assertEqual(record['host'], host)
            self.assertEqual(record['ua'], ua)
            self.assertEqual(record['referer_host'], 'example.org')
            self.assertEqual(record['status'], 200)
            self.assertIsInstance(record['request_time'], (int, float))
            self.assertRegex(record['request_id'], r'^[a-f0-9]{32}$')
            self.assertNotIn('secret', json.dumps(record).lower())
            self.assertNotIn('COOKIE', json.dumps(record))
            if name != 'site':
                self.assertEqual(record['upstream_status'], '200')
                self.assertGreaterEqual(float(record['upstream_response_time']), 0)
            self.assertTrue(any(r['scheme'] == 'http' and r['status'] == 301 for r in rows))

    def test_asset_filter_and_original_missing_path(self):
        self.assertEqual(self.request('levineuwirth.org', '/fast.css'), '200')
        self.assertEqual(self.request('levineuwirth.org', '/fonts/fast.woff2'), '200')
        self.assertEqual(self.request('levineuwirth.org', '/missing.css?secret=yes'), '404')
        self.assertEqual(self.request('levineuwirth.org', '/slow.css'), '200')
        rows = self.records('site.access.json.log')
        self.assertFalse(any(r['path'] in ('/fast.css', '/fonts/fast.woff2') for r in rows))
        missing = next(r for r in rows if r['path'] == '/missing.css')
        self.assertEqual(missing['status'], 404)
        slow = next(r for r in rows if r['path'] == '/slow.css')
        self.assertGreaterEqual(slow['request_time'], 1)

    def test_unmatched_host(self):
        self.request('unknown.invalid', tls=False)
        rows = self.records('unmatched.access.json.log')
        self.assertTrue(any(r['host'] == 'unknown.invalid' and r['status'] == 444 for r in rows))

    def test_csp_body_and_status_survive_internal_redirect(self):
        self.assertEqual(self.request('levineuwirth.org', '/csp-report'), '405')
        body = json.dumps({'csp-report': {'document-uri': 'https://levineuwirth.org/test'}})
        results = [self.request('levineuwirth.org', '/csp-report', method='POST', data=body)
                   for _ in range(35)]
        self.assertIn('204', results)
        self.assertIn('429', results)
        rows = self.records('csp-report.log')
        self.assertTrue(any(r['status'] == 405 and r['method'] == 'GET' for r in rows))
        self.assertTrue(any(r['status'] == 429 for r in rows))
        accepted = next(r for r in rows if r['status'] == 204)
        self.assertEqual(json.loads(accepted['report']), json.loads(body))
        self.assertEqual(accepted['method'], 'POST')


if __name__ == '__main__':
    unittest.main()
