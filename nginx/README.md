# nginx on the VPS

Everything nginx on the VPS reads is in this directory, except the stock
`mime.types` and certbot's `/etc/letsencrypt/options-ssl-nginx.conf` and
`ssl-dhparams.pem`. Nothing here is deployed by `make deploy`, which only
rsyncs `_site/`. A file takes effect when it is copied to its place and nginx
is reloaded.

| file | installed as | what |
|---|---|---|
| `nginx.conf` | `/etc/nginx/nginx.conf` | process settings, `server_tokens off`, the two includes |
| `default-server.conf` | `sites-available/`, linked in `sites-enabled/` | unknown hostnames: :80 closes, :443 refuses the handshake |
| `levineuwirth.conf` | the file `sites-enabled/levineuwirth.org` links to | the site, www → apex, :80 → https |
| `forgejo.conf` | `sites-available/forgejo.conf`, linked | git.levineuwirth.org |
| `anki-sync.conf` | `sites-available/anki-sync.conf`, linked | anki.levineuwirth.org |
| `couchdb-sync.conf` | `sites-available/couchdb-sync.conf`, linked | sync.levineuwirth.org |
| `security-headers.conf`, `security-framing.conf`, `csp-report.conf`, `static-assets.conf`, `popup-proxy.conf`, `archive.conf` | `/etc/nginx/snippets/` | included by `levineuwirth.conf` |
| `csp-report-format.conf`, `csp-report-zone.conf`, `popup-proxy-cache.conf`, `anki-sync-zone.conf` | `/etc/nginx/conf.d/` | `http { }` companions of the snippets; `nginx -t` fails without them |
| `access-log-format.conf` | `/etc/nginx/conf.d/` | JSON access format, original path without query, asset logging filter |
| `logrotate` | `/etc/logrotate.d/nginx` | daily rotation, 14 nonempty rotations, compression after one rotation |

The brotli modules are loaded by Arch's `/etc/nginx/modules.d/20-brotli.conf`
(`nginx-mod-brotli`), which `nginx.conf` includes.

On 2026-10-03 every snippet, `conf.d` file and the two sync vhosts were the
same on the VPS as here (`nginx -T`, compared byte for byte). The site's and
the forge's server blocks were not: the site lacked HTTP/2, the custom 404
and `$uri.html`; the forge's block sat inline in the stock `nginx.conf`,
without HTTP/2 or HSTS; and nothing claimed unknown hostnames (audit
X5/W03/W05/W06/Y13). `nginx.conf`, `default-server.conf`,
`levineuwirth.conf` and `forgejo.conf` replace them.

## Installing

Copy everything that changed to a staging directory on the VPS, take a
backup, install, and test before the reload. Root's shell there is fish;
these lines work in it.

```sh
# on the laptop
ssh vps mkdir -p /root/nginx-staging
scp nginx/*.conf vps:/root/nginx-staging/
```

```sh
# on the VPS
cp -a /etc/nginx /root/nginx-backup-$(date -u +%Y%m%dT%H%M%SZ)
cd /root/nginx-staging
install -m 0644 nginx.conf /etc/nginx/nginx.conf
readlink -f /etc/nginx/sites-enabled/levineuwirth.org     # the site's file: install over that
install -m 0644 levineuwirth.conf $(readlink -f /etc/nginx/sites-enabled/levineuwirth.org)
install -m 0644 forgejo.conf default-server.conf /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/forgejo.conf /etc/nginx/sites-available/default-server.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

`nginx.conf` no longer contains the forge's server block, so install
`forgejo.conf` in the same step: reloading with one and not the other takes
git.levineuwirth.org down. If `nginx -t` fails, nothing has been reloaded;
restore from the backup directory.

The snippets and `conf.d` files install the same way, to the paths in the
table, whenever they change.

## Checking

From anywhere:

```sh
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' https://levineuwirth.org/x-missing   # 404 and ~10 KB: the site's page
curl -s -o /dev/null -w '%{http_code}\n' https://levineuwirth.org/404.html                     # 404
curl -s -o /dev/null -w '%{http_code}\n' https://levineuwirth.org/about                        # 200
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' https://levineuwirth.org/essays/proof-broker   # 301 …/proof-broker/
curl -s --http2 -o /dev/null -w '%{http_version}\n' https://levineuwirth.org/ https://git.levineuwirth.org/   # 2, 2
curl -sI https://git.levineuwirth.org/ | grep -i 'strict-transport\|nosniff\|referrer\|^server'
curl -sI -H 'Host: unknown.invalid' http://178.104.77.249/            # empty reply (444)
curl -sk https://178.104.77.249/                                     # handshake refused (exit 35)
```

Then on the VPS, `certbot renew --dry-run`. The :80 servers redirect inside
`location /`, so a challenge location certbot adds is matched first.

## Access logs

Each completed request is a JSON object on one line. The service's HTTP
redirects and HTTPS requests use the same file, with `scheme` and `host`
distinguishing them. Files are under `/var/log/nginx/`:

| File | Traffic |
|---|---|
| `site.access.json.log` | apex and www; pages and popup proxies |
| `forgejo.access.json.log` | git.levineuwirth.org, including its assets and API |
| `anki-sync.access.json.log` | anki.levineuwirth.org |
| `couchdb-sync.access.json.log` | sync.levineuwirth.org |
| `unmatched.access.json.log` | fallback for requests outside the known vhosts |
| `csp-report.log` | CSP submissions, including rejected requests |

The website's asset locations record errors and requests taking at least
one second; successful assets below that threshold are omitted. Thus these
logs cannot measure the website's total bandwidth or asset request count.
The other service logs are unfiltered. A TLS handshake rejected before an
HTTP request does not produce an access record; check nginx's journal.

Fields include the client address, hostname and selected vhost, original
path, method, protocol, status, bytes sent (including headers), request
length, request ID, total duration, backend timings/status, proxy cache
status, response encoding, rate-limit outcome, referring host, and user
agent. Durations are in seconds. Backend fields are strings because a
request can have multiple attempts, or no backend at all. Total duration
includes client upload/download time: a long CouchDB changes feed or Git
transfer is not necessarily a slow backend. Cache status describes nginx's
proxy cache, not the visitor's browser cache. User-agent bot names are claims,
not verified identities.

Ordinary access records omit query strings, referring paths, cookies,
Authorization, and bodies. Paths, addresses and user agents still identify
activity, so files are mode 0640. CSP records deliberately retain the report
body and referring URL; they are untrusted and can contain sensitive URLs.
Their new `method` and `status` fields distinguish 204, 405, 413, and 429;
older records lack those fields. Existing `.report` parsing still works.

Writes are buffered for up to five seconds. On the VPS:

```sh
# Follow the forge. jq's --unbuffered matters when piping a live stream.
tail -F /var/log/nginx/forgejo.access.json.log | jq --unbuffered -c '{time,host,method,path,status,request_time,upstream_response_time}'

# Errors or requests taking at least one second in the current website log.
jq -c 'select(.status >= 400 or .request_time >= 1)' /var/log/nginx/site.access.json.log

# Most-requested forge paths, including retained rotations.
zcat -f /var/log/nginx/forgejo.access.json.log* | jq -r .path | sort | uniq -c | sort -nr | head -20

# User-agent claims. This includes crawlers, real browsers and spoofed strings.
jq -r .ua /var/log/nginx/forgejo.access.json.log | sort | uniq -c | sort -nr | head -20

# Backend errors, independently of the final status delivered by nginx.
jq -c 'select(.upstream_status | test("(^|[, :])[5][0-9][0-9]($|[, :])"))' /var/log/nginx/forgejo.access.json.log

# Collector rejections since the new fields were installed.
jq -c 'select((.status // 0) >= 400)' /var/log/nginx/csp-report.log
```

### Logging rollout and rotation

Install `access-log-format.conf` before reloading any vhost that names
`access_json`. Install the changed vhosts, `nginx.conf`, `static-assets.conf`,
`csp-report.conf` and `csp-report-format.conf` together. The logging-only
change does not require a site build or deploy. For each new JSON filename,
create it with `touch`, then `chown http:root` and `chmod 0640` before reload;
also restrict the existing CSP log to 0640. Do not truncate existing files.
Run `nginx -t` before the reload. The new filenames keep older combined-format
records separate; retain those old logs as historical evidence.

Back up `/etc/logrotate.d/nginx`, then install `nginx/logrotate` there with
mode 0644. `logrotate --debug /etc/logrotate.conf` checks the full setup
without changing logs or rotation state. The existing `logrotate.timer`
runs daily, with up to an hour's randomized delay. `daily` overrides the
system's weekly default for nginx only. Each file retains 14 nonempty
rotations, which can cover more than 14 days on quiet services. There is no
hard size cap between timer runs. The newest rotation stays uncompressed
until the following rotation (`delaycompress`), allowing nginx time to
reopen it after USR1. Older rotations are gzip-compressed. Rotation renames
files and reopens them; it does not use `copytruncate`.

```sh
systemctl list-timers logrotate.timer
journalctl -u logrotate.service --since yesterday
logrotate --debug /etc/logrotate.conf
```

Rehearse routing, JSON escaping, query removal, backend timings, slow/failed
assets, unmatched hosts and CSP acceptance/rejection locally:

```sh
RUN_NGINX_TESTS=1 python3 -m unittest discover -s tests -p test_nginx_logging.py -v
```

This uses a locally available `nginx:1.30` Docker image, opens no host ports,
and has no network access. It loads the real vhosts and snippets, replacing
certificate/root/backend paths with fixtures and omitting the stock image's
unavailable Brotli module. Production's `nginx -t` checks the installed modules.

## Anubis for Forgejo

The forge's HTTPS vhost proxies through Anubis on `127.0.0.1:8923`, then
Forgejo on `127.0.0.1:3000`. Meta's declared crawlers receive 403; web
browsing uses a short proof-of-work challenge. Git smart-protocol and
token-authenticated API requests have narrow exceptions. All forwarding
headers are overwritten at nginx. Other vhosts and Git over SSH are unchanged.

[anubis/README.md](../anubis/README.md) covers the pinned deployment, policy,
health check, logs, backups, updates, tests and rollback. nginx backend timings
now include Anubis, so use its policy counters to separate filter decisions
from requests actually forwarded to Forgejo.
