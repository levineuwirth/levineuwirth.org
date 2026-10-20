# Anubis for git.levineuwirth.org

Traffic flows through nginx (TLS and access logs), Anubis on
`127.0.0.1:8923`, then Forgejo on `127.0.0.1:3000`. Git over SSH on port
2222 and the Forgejo updater's localhost API checks keep their existing
paths. The website, Anki and CouchDB are outside this filter.

The bootstrap image is pinned to Anubis 1.27.0 and its registry digest.
The daily updater follows stable 1.x releases, resolving each to a digest
in `docker-compose.override.yml`; a new major requires manual review.
This is a separate Compose project, so Forgejo's updater cannot replace it.
The container starts with Docker, uses at most 192 MB and half a CPU, and
has capped Docker logs. The only writable mount holds temporary challenge
state. Its metrics/health listener is private at `127.0.0.1:9091`.

## Policy

`policy.yaml` is evaluated in order:

1. Allow GET/HEAD of exactly `/robots.txt`, including for Meta, so crawlers
   can read the prohibition. `forgejo/robots.txt` retains Forgejo's default
   exclusions and disallows all pages for Meta's seven declared crawlers.
2. Deny Meta's declared crawlers with HTTP 403, including ExternalAgent,
   ExternalFetcher, WebIndexer, FacebookBot, Facebot and link-preview agents.
   This happens before exceptions and before accepting a challenge cookie.
3. Allow Googlebot and Bingbot only when both their user agent and an IP
   range in Anubis's upstream list match. The broad `_allow-good` list is
   not imported. These ranges update with the Anubis image.
4. Allow Git smart-protocol discovery and transfer requests at their exact
   endpoints and methods. A `git/` user agent alone grants no exception.
5. Forward token-bearing `/api/v1/` requests to Forgejo, which validates the
   token. Tests cover both `token` and `Bearer`, requiring invalid credentials to receive 401 even
   on a public repository's metadata endpoint.
6. Allow read-only static resources, favicon and user/repository
   feeds. These exceptions still deny Meta.
7. Challenge everything else, including curl and clients with no user agent,
   with a difficulty-5 JavaScript proof of work and **HTTP 403**. Browsers
   solve and follow the challenge normally; tools see a failed HTTP request
   instead of successful HTML masquerading as a downloaded file.

Browsers need JavaScript and cookies for protected pages. A successful
challenge lasts up to seven days and is tied to the client address; a network
change can require another. The persistent signing key and challenge store
allow a container restart without forcing every reader through the challenge.

The difficulty was raised from 2 to 4 on 2026-10-14 at 20:14 UTC after a
distributed crawl was observed solving roughly one challenge per repository page. The
rule was renamed to `challenge-web-d4` to require a new pass: in Anubis
1.28.1, a rule's cookie identity includes its name and matching conditions,
but not its challenge difficulty. The change is a trial; compare successful
repository responses and bytes over matching UTC periods, and check visitor
solve times before increasing the difficulty further. Existing Git, API,
search-crawler and static-resource exceptions are retained.

`COOKIE_PREFIX=levineuwirth-d4-anubis` gave the difficulty-4 trial a fresh cookie
namespace (installed at 20:45 UTC): Firefox migration checks found that an
old auth cookie could survive replacement and cause a challenge loop. Both
the renamed rule and the fresh namespace are intentional. That namespace is
now superseded by the difficulty-5 trial described below.

The completed rollout passed old-cookie migration, repeat visits and the
login form in Chromium and Firefox, real HTTPS Git discovery/transfer,
the updater's protocol probes and a two-minute stability check. Aggregate
traffic tables and chart data are under `observations/2026-10-14/`;
the pre-change logs, metrics and configuration are retained privately on
the VPS under `/root/anubis-observations/20261014T201402Z/`.

On **2026-10-16 at 09:49:25 UTC**, the next trial raised `fast` difficulty from
4 to 5, renamed the challenge rule to `challenge-web-d5`, and moved to
`COOKIE_PREFIX=levineuwirth-d5-anubis`. Preserve this prefix across container
updates. The image and other policy rules are unchanged. This adds 16 times
the expected hashing work per challenge; it does not predict a corresponding
traffic reduction.

Both Chromium and Firefox passed migration from valid d4 cookies, five fresh
sessions each, repeat repository requests and the login form. Median worker
solve times in those five fresh desktop sessions were 1.237 s and 2.238 s;
the largest was 5.723 s. End-to-end page arrival includes additional network
and rendering time. These are controlled browser measurements, not trusted
timings from arbitrary access-log clients. HTTPS Git, updater protocol checks
and a two-minute container stability check passed.

Compare the next 48 hours through **2026-10-18 09:49 UTC**, keeping the partial
cutover hour separate. October 17 and 18 will provide the next two complete
UTC days at this setting if it is retained. There is no scheduled automatic
revert. Private pre-change counters, configuration, Docker events, current
forge log and cold challenge state are under
`/root/anubis-observations/difficulty-5-20261016T094922Z/`. Verification and
trial metadata are in `observations/2026-10-16/difficulty-5/`.

## Ongoing observations

`anubis-observe.timer` runs every five minutes, starting 2026-10-14 21:23 UTC.
The stdlib-only `tools/anubis-observe.py` saves Prometheus counters, container
identity/start time/health, hashed policy/Compose/nginx configurations and
available Anubis Docker events privately under `/root/anubis-observations/live/`.
Counter differences carry the actual interval and become null across process
resets. Docker events overlap by two seconds: deduplicate their original JSON
lines before analysis. Docker retention or container replacement can leave gaps;
client-reported challenge solve times are not trusted CPU measurements.

Active forge, website and CSP logs are copied once per UTC hour. Every run also
checks rotations, including the old mixed-host log, before nginx's normal
retention removes them. Each original log has one gzip archive that grows with
its source, identified by its first line; source names, byte counts, SHA-256 and
time bounds are recorded in `manifest.json`. Repeated snapshots and rotations
do not multiply request counts. Previous content must remain an identical prefix.
Archives are not automatically pruned. At less than 2 GiB free, collection fails
without deleting evidence; check the unit and disk use before it reaches that
floor. This is a local evidence archive, not an off-host backup.

Use independent copies for one-off snapshots too. Hard links to nginx rotations
can stop compression because [logrotate rejects multiply linked files by
default](https://github.com/logrotate/logrotate/blob/main/logrotate.8.in).
The original October 14 snapshot used hard links; on October 16 its 22 linked
files were replaced with independent copies, every SHA-256 preserved, and the
normal rotation service completed successfully. The ongoing gzip collector
already uses independent files. The repair record is in
`observations/2026-10-16/logrotate-repair.json`.

Hourly, `tools/anubis-traffic.py` recomputes the last 72 completed UTC hours into
`live/recent/`. `hourly.csv` groups by hour, historical policy interval,
user-agent cohort, repository, endpoint, method and response code, with bytes,
unique IP counts and summed request durations. `hourly-summary.csv` gives
repository totals by hour/cohort. Check-user-agent requests are excluded by
default. Missing rows are not certified zero hours, unique IP counts cannot be
summed across cells, and legacy body-only byte counts stay separate from modern
counts including headers. Raw evidence supports new groupings later.

Recompute a fixed window without changing collection:

```sh
/usr/local/bin/anubis-traffic.py --state /root/anubis-observations/live \
  --output /root/anubis-observations/live/history-20261014 \
  --since 2026-10-01T00:00:00Z --until 2026-10-14T00:00:00Z
systemctl status anubis-observe.timer anubis-observe.service
journalctl -u anubis-observe.service -n 20 --no-pager
```

Install both Python tools in `/usr/local/bin/` mode 0755, and both
`systemd/anubis-observe.*` units in `/etc/systemd/system/` mode 0644. Create
`/root/anubis-observations/` mode 0700, run `systemd-analyze verify` on the units,
then `systemctl daemon-reload` and `systemctl enable --now anubis-observe.timer`.
The first run captures retained logs, so it is larger than routine runs. Its
service limits CPU to 25% and memory to 512 MiB. It does not restart Anubis.

Raw records, addresses, full Docker URLs and configuration snapshots remain root
private. Only reviewed aggregates belong in this repository or the essay. See
[`observations/README.md`](observations/README.md) for the analysis conventions.

## Access behaviour

Unauthenticated API calls and raw-file URLs also encounter the challenge;
automations should use an authenticated API or Git, and `curl --fail` for
HTTP downloads (curl without that flag does not fail on HTTP errors).
Git LFS and package registries are disabled: neither had any stored objects
on 2026-10-04. Releases had no uploaded assets either, so no download
exception is currently needed. Rehearse exact endpoints before enabling
one of these workflows. Public `/api/healthz` remains challenged; monitoring
uses the private listeners.

User agents are spoofable. This refuses clients announcing themselves as
Meta and makes disguised web crawlers solve the challenge; it cannot prove
that a permitted Git client or browser is unaffiliated with Meta. Public
repositories remain cloneable through Git.

nginx overwrites forwarding headers before Anubis sees them. Host networking
keeps Forgejo's existing trusted Docker gateway unchanged. No public route
points directly to the Forgejo HTTP port. The existing archive-download
restriction remains in nginx.
Forgejo's router logs were checked live: forwarded public addresses survive
the extra hop. HTTPS Git deliberately depends on Anubis, while authenticated
SSH on port 2222 is independent. Blocking `facebookexternalhit` also disables
Facebook, Messenger and Threads link previews for forge URLs.

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

Install `forgejo/robots.txt` as `/root/forgejo-server/forgejo-data/gitea/public/robots.txt`
(0644), creating `public/` if needed. Forgejo serves it without restarting.
The compose changes disabling LFS/packages require recreation: take a Forgejo
backup first, verify no objects have since appeared, and recreate using the
**currently running image**, with `--pull never`. Do not pull a new Forgejo
release as part of this configuration change; its updater owns upgrades.

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

The `anubis-update.timer` runs daily at 06:00 UTC plus up to 15 minutes.
It shares a lock with `forgejo-update` (`/run/lock/git-stack-update.lock`)
and waits up to 30 minutes for it: its checks pass through Anubis to the
forge, so a forge being recreated would fail them and roll back a good image.
It obtains the latest non-prerelease 1.x release from GitHub, pulls the official
image and resolves its digest. It checks the running service, takes a config
backup, saves the old image under `anubis-rollback:previous`, stops the filter
briefly to copy its challenge state, then replaces it. It checks health,
challenge/deny status, robots, invalid token/Bearer rejection, Git discovery,
feeds and Google/Bing address matching. The container must remain running
without restarting for two minutes and pass the checks again. There is a
brief HTTPS interruption during replacement; SSH is unaffected. After a
verified update it removes every other Anubis image except the rollback copy
(`PRUNE=0` keeps them); old releases keep their version tags, so nothing else
would.

Failures restore both the previous image and its cold state copy, then verify
the rollback. The signing key is never replaced. Failed images are held;
interrupted updates leave a durable journal that triggers recovery next run.
A failed rollback leaves `needs-operator` and blocks further changes. No image
is pruned by this updater. Even an unchanged version must pass health checks.
These are HTTP/protocol checks, not an unattended browser session; the browser
rehearsal below remains necessary after major policy or implementation changes.

```sh
scp tools/anubis-update.py vps:/usr/local/bin/
scp systemd/anubis-update.service systemd/anubis-update.timer vps:/etc/systemd/system/
ssh vps 'chmod 755 /usr/local/bin/anubis-update.py && systemctl daemon-reload'
ssh vps 'systemctl start anubis-update.service && systemctl enable --now anubis-update.timer'
ssh vps 'journalctl -u anubis-update.service -n 30 --no-pager'
tools/vps-status
```

Runtime state is under `/var/lib/anubis-update/`, included in the config backup
along with the accepted image override. To retry a held image after investigating,
remove `hold`. If `needs-operator` exists, inspect `pending.json`, the Compose
override and container first; preserve `previous-state`. Once the underlying
failure is corrected, remove only `needs-operator` and start the unit: its pending
journal restores the old image and state before doing anything else. It exits
failed after this recovery so the incident remains visible. Do not remove the
journal just to make the unit green. A host rebuild must restore the override
and updater state together, or deliberately start with empty challenge state
after reconciling the saved image and pending markers.

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
browser login, persistence across a restart, crawler address checks, and an
updater replacement/rollback using real disposable images. Test containers and the
Forgejo volume are removed; a private scratch directory retains screenshots
and logs for review. No production credentials or repositories are used.

`python3 -m unittest discover -s tests -p test_anubis_update.py -v` additionally
rehearses interrupted updates, failed rollback, held releases, backup/network
failure and crash loops without Docker or production changes.

Upstream references: [installation](https://github.com/TecharoHQ/anubis/blob/v1.27.0/docs/docs/admin/installation.mdx),
[policy expressions](https://github.com/TecharoHQ/anubis/blob/v1.27.0/docs/docs/admin/configuration/expressions.mdx),
[release](https://github.com/TecharoHQ/anubis/releases/tag/v1.27.0).
