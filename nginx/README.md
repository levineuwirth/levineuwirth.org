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
