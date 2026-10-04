# Anubis for git.levineuwirth.org

Traffic flows through nginx (TLS and access logs), Anubis on
`127.0.0.1:8923`, then Forgejo on `127.0.0.1:3000`. Git over SSH on port
2222 and the Forgejo updater's localhost API checks keep their existing
paths. The website, Anki and CouchDB are outside this filter.

The image is pinned to Anubis 1.27.0 and its registry digest. This is a
separate Compose project, so Forgejo's unattended updater cannot replace it.
The container starts with Docker, uses at most 192 MB and half a CPU, and
has capped Docker logs. The only writable mount holds temporary challenge
state. Its metrics/health listener is private at `127.0.0.1:9091`.

## Policy

`policy.yaml` is evaluated in order:

1. Deny Meta's declared crawlers with HTTP 403, including ExternalAgent,
   ExternalFetcher, WebIndexer, FacebookBot, Facebot and link-preview agents.
   This happens before exceptions and before accepting a challenge cookie.
2. Allow Git smart-protocol discovery and transfer requests at their exact
   endpoints and methods. A `git/` user agent alone grants no exception.
3. Forward token-bearing `/api/v1/` requests to Forgejo, which validates the
   token. The regression check requires invalid tokens to receive 401 even
   on a public repository's metadata endpoint.
4. Allow read-only static resources, robots.txt, favicon and user/repository
   feeds. These exceptions still deny Meta.
5. Challenge everything else, including curl and clients with no user agent,
   with a difficulty-2 JavaScript proof of work.

Browsers need JavaScript and cookies for protected pages. A successful
challenge lasts up to seven days and is tied to the client address; a network
change can require another. The persistent signing key and challenge store
allow a container restart without forcing every reader through the challenge.
Unauthenticated API calls and raw-file URLs also encounter the challenge;
automations should use an authenticated API or Git. Git LFS and package
registries have no special exceptions; rehearse them before adding one.

User agents are spoofable. This refuses clients announcing themselves as
Meta and makes disguised web crawlers solve the challenge; it cannot prove
that a permitted Git client or browser is unaffiliated with Meta. Public
repositories remain cloneable through Git.

nginx overwrites forwarding headers before Anubis sees them. Host networking
keeps Forgejo's existing trusted Docker gateway unchanged. No public route
points directly to the Forgejo HTTP port. The existing archive-download
restriction remains in nginx.

## Installing

On the VPS, create the directory, persistent signing key and state before
starting the container. Root's shell is fish; these commands work there.

```sh
install -d -m 0700 /root/anubis-server
install -d -m 0700 -o 1000 -g 1000 /root/anubis-server/state
# Run only for a new instance: preserve the key on updates.
openssl rand -hex 32 > /root/anubis-server/signing.key
chown 1000:1000 /root/anubis-server/signing.key
chmod 0400 /root/anubis-server/signing.key
```

Copy `docker-compose.yml` and `policy.yaml` into that directory. Start and
verify the filter before changing nginx:

```sh
cd /root/anubis-server
docker compose pull
docker compose up -d
curl -fsS http://127.0.0.1:9091/healthz
docker inspect -f '{{.State.Health.Status}}' anubis
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: git.levineuwirth.org' -H 'X-Real-IP: 127.0.0.1' -A 'meta-externalagent/1.1' http://127.0.0.1:8923/neuwirth/levineuwirth.org
# Expect 403. A browser-like client should receive a challenge page.
```

Back up the live forge vhost, install `nginx/forgejo.conf`, then run
`nginx -t && systemctl reload nginx`. Check the public URL in Chromium and
Firefox, clone/fetch over HTTPS, and repeat the Meta request through HTTPS.
Check that `ss -ltn` shows 8923 and 9091 on loopback only. Install the updated
`tools/vps-config-backup.sh` at `/usr/local/bin/` with mode 0755; it includes
the compose file, policy and signing key and excludes `state/`. Run its
service and `--verify` once after installing. Its off-host copy is encrypted
in Borg like the other host configuration.

The healthcheck's `--metrics-bind=:9091` override applies only to the checker
process. Anubis 1.27.0's checker otherwise prepends `http://localhost` to the
server's full loopback address, producing an invalid URL. Do not widen the
server bind to work around it.

## Logs, updates and rollback

Use `curl --compressed` when probing a challenge page. Anubis 1.27.0 can
reject clients that omit gzip support with HTTP 500; that response is from
the filter, not Forgejo. Actual Git protocol requests bypass the challenge.

```sh
docker logs --since 1h --tail 100 anubis
curl -fsS http://127.0.0.1:9091/metrics
tail -F /var/log/nginx/forgejo.access.json.log | jq --unbuffered -c '{time,path,status,request_time,ua}'
```

Anubis's logs identify the rule and action. nginx's backend timing now
includes the filter; a denial's `upstream_status=403` comes from Anubis,
not Forgejo. Use the policy counters at `/metrics` to distinguish challenges,
denials and passes. Metrics reset on container restart. nginx access records
omit query strings; Anubis's own logs can contain full URLs. Both log sets
are restricted and rotated. `tools/vps-status` includes the container's
health status. Docker reports an unhealthy state but does not automatically
restart a process solely because its health check fails.

To update, review the release notes, change both the tag and digest in the
compose file, rerun the rehearsal below, and take a configuration backup.
Then copy the files, `docker compose pull && docker compose up -d`, and repeat
the public checks. There is deliberately no unattended Anubis upgrade timer.

For emergency rollback, restore the previous nginx forge vhost and run
`nginx -t && systemctl reload nginx` before stopping Anubis. For an intentional
permanent removal, change only its `proxy_pass` back to
`http://127.0.0.1:3000`, keeping the forwarded-header cleanup. This restores
direct web access and also removes the Meta denial. Leave Anubis's signing
key in the private backup rather than posting it to an issue or chat.

## Rehearsal

With Docker images for nginx 1.30, Forgejo 15.0.9 and the pinned Anubis image
available locally, and a Python environment with PyYAML and Playwright's
Chromium/Firefox installed:

```sh
RUN_ANUBIS_TESTS=1 python -m unittest discover -s tests -p test_anubis.py -v
RUN_NGINX_TESTS=1 python -m unittest discover -s tests -p test_nginx_logging.py -v
```

The fixture exposes only a random loopback TLS port and creates a temporary
Forgejo user and repository. It tests Meta denials (including with valid
credentials/cookies), challenges, API authentication, feeds, clone/push/fetch,
browser login and persistence across a restart. Test containers and the
Forgejo volume are removed; a private scratch directory retains screenshots
and logs for review. No production credentials or repositories are used.

Upstream references: [installation](https://github.com/TecharoHQ/anubis/blob/v1.27.0/docs/docs/admin/installation.mdx),
[policy expressions](https://github.com/TecharoHQ/anubis/blob/v1.27.0/docs/docs/admin/configuration/expressions.mdx),
[release](https://github.com/TecharoHQ/anubis/releases/tag/v1.27.0).
