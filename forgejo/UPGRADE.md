# Upgrading git.levineuwirth.org

A runbook, executed by hand. Written 2026-09-06 against a live instance
reporting `1.21.11+0` at <https://git.levineuwirth.org/api/v1/version>, a
release line that left support in 2024. Nothing here has been run against
the production box; every command below is for the operator to run.

**Target: `15.0.7`** — the current LTS, supported until 2027-07-15.

Not `16.0.x`: it is the newer stable, but its support window closes
2026-10-29, seven weeks from this writing, and `17.0` lands 2026-10-15.
An instance that gets touched twice a year belongs on the LTS line. The
route to 16 is the same as the route to 15 plus one hop, and § 6 records
that it was rehearsed too.

---

## 0. What is actually being changed

The database is SQLite. That makes this whole operation a container image
swap plus schema migrations that Forgejo runs itself on first start, and
makes a rollback the restoration of one file. There is no database server
to upgrade alongside, and none of the MySQL/PostgreSQL minimum-version
requirements introduced in 7.0 apply.

`forgejo/docker-compose.yml` in this repo is the tracked mirror of
`/root/forgejo-server/docker-compose.yml` on the VPS. **Its image tag still
reads `1.21.11-0` on purpose**: it describes the live instance, and editing
it before the upgrade lands would make the tracked copy a lie. The tags to
put there are in § 3 and § 5; commit the change once production is actually
running the new image.

### The supported upgrade path, as Forgejo documents it

The [upgrade guide](https://forgejo.org/docs/latest/admin/upgrade/) says you
may "upgrade straight to the latest released Forgejo version", and adds that
if an upgrade between non-consecutive versions fails, you should then test
each intermediate release series to find the version that broke.

There is exactly one hard waypoint, and it concerns databases of Gitea
lineage — which this one is, `1.21` predating Forgejo's own numbering:

> Upgrade from any Gitea version up to and including v1.22.x to Forgejo
> v10.0.x, then from Forgejo v10.0.x to any later version.

That rule is visible in the migration log. Forgejo `10.0.3` runs
`Migration[303]: Gitea last drop`, after which the Gitea-lineage schema
counter freezes at 305 and every later change is a Forgejo migration. So
`10.0.3` is where this database stops being a Gitea database.

**Both routes were rehearsed here and both worked** (§ 6), including the
single-jump `1.21.11-0 → 15.0.7`. The stepwise chain in § 3 is still the
recommendation, for one reason that has nothing to do with what Forgejo
supports: nine stops are nine rollback points and nine places where a
failure names the version that caused it. A single jump that fails leaves
you bisecting a chain of 94 migrations under time pressure.

---

## 1. Pre-flight

Run all of this before touching anything. Every step is read-only except
the backup itself.

### 1.1 Record the starting state

```bash
curl -s https://git.levineuwirth.org/api/v1/version
ssh root@<vps> 'docker inspect -f "{{.Config.Image}}" forgejo'
ssh root@<vps> 'grep -c . /root/forgejo-server/docker-compose.yml'
```

Write the version string down. The rollback in § 5 restores *to* it.

### 1.2 Disk space

The migrations that widen columns (`Migration[286]: Add support for SHA256
git repositories`, among others) are table rewrites under SQLite: the engine
builds a new table beside the old one and swaps. Budget twice the database
size for that, and twice the size of `/root/forgejo-server` for the backup
archive.

```bash
ssh root@<vps> 'df -h /; du -sh /root/forgejo-server /root/forgejo-backups
                du -h /root/forgejo-server/forgejo-data/gitea/gitea.db'
```

Stop and free space if `/` is above ~80 % or if free space is less than
`2 × (data directory + backups directory)`.

### 1.3 Flush the queues

Forgejo's documented pre-upgrade step. It drains work that would otherwise
be re-run or lost across the restart.

```bash
ssh root@<vps> 'docker exec -u git forgejo forgejo manager flush-queues'
# if it times out, repeat with a larger deadline:
ssh root@<vps> 'docker exec -u git forgejo forgejo manager flush-queues --timeout 5m'
```

### 1.4 Doctor, before

Establish that the instance is healthy *before* the upgrade, so that
anything `doctor` says afterwards is attributable to the upgrade.

```bash
ssh root@<vps> 'docker exec -u git forgejo forgejo doctor check --all --log-file /tmp/doctor-before.log'
ssh root@<vps> 'tail -40 /tmp/doctor-before.log'
```

Do **not** pass `--fix`, and do not run `doctor` at all on 7.0.0 — that
release had an LFS-corrupting bug in `doctor check --fix`, fixed in 7.0.1.
The chain in § 3 lands on 7.0.16, so this only matters if you deviate.

### 1.5 Check for unexpected authorized_keys — this one can block startup

Forgejo **14.0** added a startup check: if it manages
`/data/git/.ssh/authorized_keys` and finds a key in it that it did not put
there, **it refuses to start**. This is the single most likely way for the
chain in § 3 to stop dead at hop 8 on a box that has been touched by hand.

```bash
ssh root@<vps> 'docker exec forgejo sh -c "cat /data/git/.ssh/authorized_keys" | grep -c .'
ssh root@<vps> 'docker exec forgejo sh -c "grep -vc \"forgejo-\" /data/git/.ssh/authorized_keys"'
```

Every line Forgejo wrote carries a `command=".../forgejo serv key-N"`
prefix. Any line without one is a hand-added key. If there are none, this
step costs nothing. If there are, decide before you start:

* delete the file and let Forgejo regenerate it from the keys in the
  database (the keys users actually registered), or
* set `FORGEJO__security__SSH_ALLOW_UNEXPECTED_AUTHORIZED_KEYS: "true"` in
  the compose file, which keeps the old permissive behaviour.

### 1.6 Take the backup, and prove it

```bash
ssh root@<vps> 'systemctl start forgejo-backup.service && systemctl status --no-pager forgejo-backup.service'
ssh root@<vps> 'ls -l /root/forgejo-backups/ && readlink -f /root/forgejo-backups/LATEST'
ssh root@<vps> '/usr/local/bin/forgejo-backup.sh --verify'
```

`--verify` extracts the newest archive to a temporary directory, checks its
`sha256`, and runs `PRAGMA integrity_check` on the snapshot inside. It is
the same check § 2 depends on. It must print
`verify: OK — restore this snapshot over forgejo-data/gitea/gitea.db`.

**The snapshot is the database.** The archive contains exactly one copy of
the database: `forgejo-server/forgejo-data/gitea/hot-<TS>.db`. The live
`gitea.db` is deliberately excluded, because tar reads it while Forgejo
writes to it and produces a file that unpacks cleanly and will not open. A
restore copies the `hot-*.db` over `gitea.db`. Note the exact filename now:

```bash
ssh root@<vps> 'tar tzf "$(readlink -f /root/forgejo-backups/LATEST)" | grep "hot-.*\.db"'
```

### 1.7 Copy the archive off the host, with a verified checksum

Until this step the backup lives on the disk it is backing up.

```bash
A=$(ssh root@<vps> 'readlink -f /root/forgejo-backups/LATEST')
mkdir -p ~/backups/forgejo
scp root@<vps>:"$A" root@<vps>:"$A.sha256" ~/backups/forgejo/
cd ~/backups/forgejo && sha256sum -c "$(basename "$A").sha256"
```

That last line must print `OK`. If it does not, the transfer is bad; do it
again and do not proceed on a checksum you have not seen pass.

To make this automatic from here on, configure `OFFHOST_DEST` — see
`systemd/forgejo-backup.env.example` and § 7.3.

---

## 2. Rehearse on a workstation, not on the VPS

This is the step that turns a plan into a tested plan. It uses the archive
you just copied down; the production instance is untouched throughout.

### 2.1 Restore the archive into a disposable stack

```bash
mkdir -p ~/tmp/forgejo-lab && cd ~/tmp/forgejo-lab
tar xzf ~/backups/forgejo/forgejo-<TS>.tar.gz          # yields ./forgejo-server/
cd forgejo-server

# The snapshot becomes the live database. This is the whole restore.
cp forgejo-data/gitea/hot-*.db forgejo-data/gitea/gitea.db
rm -f forgejo-data/gitea/hot-*.db
```

Now edit the extracted `docker-compose.yml` so it cannot touch anything
real. Four changes, all required:

```yaml
services:
  forgejo:
    image: codeberg.org/forgejo/forgejo:1.21.11-0   # start where production is
    container_name: forgejo-lab                     # not "forgejo"
    environment:
      # ...keep every FORGEJO__* line from production as-is...
      FORGEJO__server__ROOT_URL: http://localhost:33000/
      FORGEJO__server__DOMAIN: localhost
      FORGEJO__server__SSH_DOMAIN: localhost
    ports:
      - "127.0.0.1:33000:3000"                      # loopback only, high port
      # delete the "2222:22" mapping entirely
    networks: []                                    # delete the proxy-net block
```

Deleting the external `proxy-net` network matters: without it the lab
cannot be reached by the host's nginx even by accident.

```bash
docker compose -p forgejo-lab up -d
curl -s http://127.0.0.1:33000/api/v1/version     # expect {"version":"1.21.11+0"}
```

### 2.2 The health check, run at every stop

Five things, in this order. Anything red stops the chain.

```bash
BASE=http://127.0.0.1:33000

# 1. version endpoint reports the tag you just deployed
curl -s $BASE/api/v1/version

# 2. web login works — a real form POST, then an authenticated page.
#    Forgejo <= 13 renders a hidden _csrf input and requires it; 14+ dropped
#    it. Send it only if the page has one.
JAR=$(mktemp)
CSRF=$(curl -s -c $JAR -b $JAR $BASE/user/login | grep -oP 'name="_csrf"\s+value="\K[^"]+' | head -1)
curl -s -o /dev/null -c $JAR -b $JAR -X POST \
     ${CSRF:+--data-urlencode "_csrf=$CSRF"} \
     --data-urlencode "user_name=<admin>" --data-urlencode "password=<password>" \
     $BASE/user/login
curl -s -o /dev/null -w '%{http_code}\n' -b $JAR $BASE/user/settings   # expect 200

# 3. a repo page renders and lists its files
curl -s -o /dev/null -w '%{http_code}\n' $BASE/neuwirth/levineuwirth.org

# 4. a clone succeeds and the content is intact
git clone $BASE/neuwirth/levineuwirth.org.git /tmp/clonecheck && \
  git -C /tmp/clonecheck log --oneline | head -3 && rm -rf /tmp/clonecheck

# 5. the API still lists repositories
curl -s -u '<admin>:<password>' "$BASE/api/v1/repos/search?limit=50" | head -c 300
```

And watch the migrations actually run, rather than assuming they did:

```bash
docker compose -p forgejo-lab logs --tail 200 | grep -E 'Migration\[|\[E\]|\[F\]'
docker compose -p forgejo-lab exec -u git forgejo \
    sqlite3 /data/gitea/gitea.db 'PRAGMA integrity_check;'
```

The last line must print `ok` at every stop. A migration that half-applied
shows up here and nowhere else.

### 2.3 Step through the hops

For each tag in the table in § 3, in order:

```bash
TAG=7.0.16                                  # then 8.0.3, 9.0.3, ...
sed -i "s|forgejo:.*|forgejo:$TAG|" docker-compose.yml
docker compose -p forgejo-lab pull
docker compose -p forgejo-lab up -d
# wait for the version endpoint to answer with the new tag, then run § 2.2
```

`up -d` recreates the container, which is what applies both the new image
and any changed `FORGEJO__*` variable. `docker restart` does neither.

### 2.4 Tear the lab down

```bash
docker compose -p forgejo-lab down -v
cd ~ && rm -rf ~/tmp/forgejo-lab
```

---

## 3. The hop sequence, with exact tags

Latest patch of each major as of 2026-09-06. Use these exact tags — a
floating `:15` tag makes the rollback in § 5 ambiguous.

| # | image tag | what happens |
|---|---|---|
| 0 | `codeberg.org/forgejo/forgejo:1.21.11-0` | where production is now |
| 1 | `codeberg.org/forgejo/forgejo:7.0.16` | Gitea schema 280→293, Forgejo 3→10. Includes `Migration[286]` (SHA-256 repository support), the slowest of the chain |
| 2 | `codeberg.org/forgejo/forgejo:8.0.3` | Gitea 294→299, Forgejo 11→17. MS SQL Server support removed (irrelevant here) |
| 3 | `codeberg.org/forgejo/forgejo:9.0.3` | Gitea 300→302, Forgejo 18→21 |
| 4 | `codeberg.org/forgejo/forgejo:10.0.3` | **the waypoint.** `Migration[303]: Gitea last drop`; the Gitea schema counter freezes at 305 |
| 5 | `codeberg.org/forgejo/forgejo:11.0.16` | Forgejo 25→27. SSPI auth dropped (Windows only) |
| 6 | `codeberg.org/forgejo/forgejo:12.0.4` | Forgejo 28→35. The bleve issue index is detected as stale and rebuilt |
| 7 | `codeberg.org/forgejo/forgejo:13.0.5` | Forgejo 36→39 |
| 8 | `codeberg.org/forgejo/forgejo:14.0.5` | named migrations begin (`v14a_*`, `v14b_*`); the numeric `forgejo_version` stops advancing and `forgejo_migration` takes over. **This is the hop that refuses to start on unexpected `authorized_keys` — see § 1.5** |
| 9 | `codeberg.org/forgejo/forgejo:15.0.7` | **target.** `v15a_*`–`v15c_*`; bleve index rebuilt again. **Everyone is logged out — see § 4.2** |

Shorter routes, both documented as supported and both rehearsed here:

* `1.21.11-0 → 10.0.3 → 15.0.7` — keeps the one waypoint Forgejo's own
  documentation names, drops the rest.
* `1.21.11-0 → 15.0.7` — a single jump, 94 migrations in one start.

Take one of these only if you are prepared to bisect by hand when it fails.

---

## 4. Compose changes

### 4.1 Nothing has to change

Every `FORGEJO__*` variable in `forgejo/docker-compose.yml` survives to
15.0.7 and 16.0.3 under the same name. This was checked by reading the
generated `app.ini` out of an upgraded instance, not by reading docs:

| variable | status at 15.0.7 / 16.0.3 |
|---|---|
| `FORGEJO__server__DOMAIN` | unchanged |
| `FORGEJO__server__SSH_DOMAIN` | unchanged |
| `FORGEJO__server__ROOT_URL` | unchanged |
| `FORGEJO__server__SSH_PORT` | unchanged |
| `FORGEJO__database__DB_TYPE` | unchanged |
| `FORGEJO__service__DISABLE_REGISTRATION` | unchanged |
| `FORGEJO__service__NO_REPLY_ADDRESS` | unchanged |
| `FORGEJO__actions__ENABLED` | unchanged |

No deprecation or removal warning appeared in the logs at any hop for any
of them. `USER_UID`/`USER_GID` are container-entrypoint variables, not
`app.ini`, and are likewise unchanged.

### 4.2 What should change anyway

Add these to the `environment:` block. Each is a decision the upgrade
forces rather than a rename it requires.

```yaml
      # Forgejo 16.0 removed "REVERSE_PROXY_TRUSTED_PROXIES = *" from the
      # image's app.ini template. That template only ever runs on a FRESH
      # install, so the "*" written by the 1.21 image is still sitting in
      # forgejo-data/gitea/conf/app.ini and survives every hop below.
      # nginx is on the same host, so name it and stop trusting the world.
      FORGEJO__security__REVERSE_PROXY_TRUSTED_PROXIES: "127.0.0.1"
      FORGEJO__security__REVERSE_PROXY_LIMIT: "1"

      # 15.0 made session cookie names brand-independent, which logs every
      # user out on that hop. With one human user that is a shrug; setting
      # the old name back avoids even that.
      FORGEJO__security__COOKIE_REMEMBER_NAME: "gitea_incredible"

      # Only if § 1.5 found hand-added keys you intend to keep. Leaving it
      # unset is the safer default; 14.0 refusing to start is the feature.
      # FORGEJO__security__SSH_ALLOW_UNEXPECTED_AUTHORIZED_KEYS: "true"
```

Verify after the upgrade that the value actually landed, since `app.ini`
already had a conflicting line:

```bash
ssh root@<vps> 'grep -A4 "^\[security\]" /root/forgejo-server/forgejo-data/gitea/conf/app.ini'
```

### 4.3 The image tag

Only after production is running it:

```yaml
    image: codeberg.org/forgejo/forgejo:15.0.7
```

Also update the header comment in `forgejo/docker-compose.yml`, which still
describes 1.21-era behaviour.

---

## 5. Production execution

One hop at a time. The loop below is the whole procedure; repeat it for
each tag in § 3, in order, and do not start the next one until the previous
one is green.

```bash
ssh root@<vps>
cd /root/forgejo-server

TAG=7.0.16          # then 8.0.3, 9.0.3, 10.0.3, 11.0.16, 12.0.4, 13.0.5, 14.0.5, 15.0.7

# --- 1. a backup per hop. This is the rollback point for THIS hop. ---------
systemctl start forgejo-backup.service
systemctl status --no-pager forgejo-backup.service      # must be inactive/success
/usr/local/bin/forgejo-backup.sh --verify               # must print verify: OK
PREHOP=$(readlink -f /root/forgejo-backups/LATEST)
echo "rollback for $TAG is $PREHOP"

# --- 2. flush, then swap the image ----------------------------------------
docker exec -u git forgejo forgejo manager flush-queues
sed -i "s|forgejo:.*|forgejo:$TAG|" docker-compose.yml
docker compose pull
docker compose up -d

# --- 3. watch the migration finish before touching anything ----------------
docker compose logs -f --tail 100        # Ctrl-C once "Listen: http://" appears
docker compose logs --tail 300 | grep -E 'Migration\[|\[E\]|\[F\]'
docker exec forgejo sqlite3 /data/gitea/gitea.db 'PRAGMA integrity_check;'   # ok

# --- 4. health check, from a machine that is not the VPS -------------------
curl -s https://git.levineuwirth.org/api/v1/version
# then, by hand in a browser: log in, open a repository page, read a file
git clone https://git.levineuwirth.org/neuwirth/levineuwirth.org.git /tmp/cc && \
  git -C /tmp/cc log --oneline | head -3 && rm -rf /tmp/cc
```

`KEEP=14` on the backup script means nine per-hop backups plus a week of
nightlies fits without pruning anything you still want. If you would rather
be certain, run the chain with `KEEP=30` exported for the day.

### 5.1 Rollback, per hop

A hop fails if the container will not stay up, the migration log shows
`[E]`/`[F]`, `integrity_check` is not `ok`, or a health check is red. Then,
for that hop only:

```bash
cd /root/forgejo-server
docker compose down

# 1. restore the pre-hop archive. Extract somewhere with room for a second
#    copy of the data directory; /tmp on this box may not have it.
mv forgejo-data forgejo-data.failed-$TAG
R=$(mktemp -d -p /root)
tar xzf "$PREHOP" -C "$R"
mv "$R/forgejo-server/forgejo-data" ./forgejo-data
rm -rf "$R"
cp forgejo-data/gitea/hot-*.db forgejo-data/gitea/gitea.db   # snapshot IS the db
rm -f forgejo-data/gitea/hot-*.db
chown -R 1000:1000 forgejo-data

# 2. revert the pin to the tag you came from
sed -i "s|forgejo:.*|forgejo:<previous-tag>|" docker-compose.yml

# 3. bring it back
docker compose up -d
curl -s https://git.levineuwirth.org/api/v1/version   # expect the previous tag
```

Keep `forgejo-data.failed-$TAG` until you understand what happened; it is
the only evidence of the failure.

Two things this rollback cannot undo, which is why the chain is stepwise:
an *older* Forgejo will not open a database a *newer* Forgejo has migrated,
so restoring the data is mandatory and reverting the tag alone will not
work — this is also why "just roll back the image" is not a step. And any
push that landed between the pre-hop backup and the failure is lost, so do
the upgrade when nothing is being pushed, and take the per-hop backup
immediately before the hop rather than reusing an earlier one.

---

## 6. What was rehearsed, and what that does and does not prove

Every hop in § 3 was run locally on 2026-09-06, on Docker 29.7.2, against a
**freshly created empty instance** — one admin user, one repository with two
commits — restored and re-restored between runs. Production data was never
present on this machine.

| hop | migrations observed | schema after | integrity | health |
|---|---|---|---|---|
| `1.21.11-0` baseline | — | gitea 280 / forgejo 3 | ok | all green |
| → `7.0.16` | gitea 280–293, forgejo 3–10 | gitea 294 / forgejo 11 | ok | all green |
| → `8.0.3` | gitea 294–299, forgejo 11–17 | gitea 300 / forgejo 18 | ok | all green |
| → `9.0.3` | gitea 300–302, forgejo 18–21 | gitea 303 / forgejo 22 | ok | all green |
| → `10.0.3` | gitea 303–304 (`Gitea last drop`), forgejo 22–24 | gitea 305 / forgejo 25 | ok | all green |
| → `11.0.16` | forgejo 25–27 | forgejo 28 | ok | all green |
| → `12.0.4` | forgejo 28–35 | forgejo 36 | ok | all green |
| → `13.0.5` | forgejo 36–39 | forgejo 40 | ok | all green |
| → `14.0.5` | legacy 40–43 + 15 named `v14a`/`v14b` migrations | forgejo 44 + named | ok | all green |
| → `15.0.7` | 14 named `v14a`/`v15a`/`v15b`/`v15c`/`v17a` migrations | named | ok | all green |

Also rehearsed, all green:

* **`1.21.11-0 → 15.0.7` in one jump** — 94 migrations, same end state as the
  chain. The direct route works.
* **`15.0.7 → 16.0.3`** — 11 migrations. And `1.21.11-0 → 16.0.3` direct,
  105 migrations.
* **rollback** — restoring the pre-15.0.7 archive and starting 14.0.5 on it
  came back green, which is the § 5.1 procedure end to end.
* **restore** — an archive produced by the fixed `tools/forgejo-backup.sh`,
  unpacked into a fresh compose stack with the `hot-*.db` snapshot copied
  over `gitea.db`, produced a working instance: login, repo page, clone.
* **`forgejo doctor check --all` at 15.0.7** — 28 checks, all OK.

Warnings seen, all benign:

* `[W] Table X has column Y but struct has not related field` on hops 1–3.
  xorm comparing a mid-migration schema against the new structs; they stop
  once the hop completes.
* `[W] Found older bleve index with version 4/5, Forgejo will remove it and
  rebuild` at 12.0.4 and 15.0.7. Expected; on a real instance this rebuild
  takes proportionally longer and issue search is briefly incomplete.
* The container's own `sshd` logging `Bind to port 22 ... Address in use` —
  an artifact of the lab's host networking, not present in production.

**Limits of the rehearsal, stated plainly.** An empty instance exercises
schema migrations but not *data* migrations. `Migration[286]` rewrites
`commit_status`, `comment` and `release`; on an empty database that is
instant, and on a real one it is the slowest step of hop 1. Wall-clock times
observed (2–6 s per hop) are a floor and no guide at all to production.
Nothing here tested LFS objects, packages, webhooks, Actions artifacts,
attachments, or a database with real row counts, because none were present.
Memory peaked at 107 MiB against the compose file's `mem_limit: 512m`, but
on an empty instance — if a hop is OOM-killed on the VPS, raise that limit
for the upgrade and put it back afterwards.

---

## 7. After the upgrade

### 7.1 Verify, then commit

```bash
ssh root@<vps> 'docker exec -u git forgejo forgejo doctor check --all --log-file /tmp/doctor-after.log'
ssh root@<vps> 'tail -40 /tmp/doctor-after.log'
ssh root@<vps> 'systemctl start forgejo-backup.service && /usr/local/bin/forgejo-backup.sh --verify'
```

Compare against `/tmp/doctor-before.log` from § 1.4. Then commit, in this
repo, the change that is now true:

* `forgejo/docker-compose.yml` — image tag `15.0.7`, the `[security]`
  variables from § 4.2, and a header comment that no longer describes 1.21.
* `forgejo/UPGRADE.md` — the date this was executed and anything that
  differed from this runbook. A runbook that is not corrected after use is
  a runbook nobody trusts the second time.

### 7.2 nginx and HSTS

The forge's vhost lives on the VPS and is **not** tracked in this repo's
`nginx/` — that directory is the website's configuration. Nothing in the
upgrade requires an nginx change, but three things are worth confirming
while you are already in there:

* **HSTS needs no change and constrains you.** `nginx/security-headers.conf`
  sets `max-age=31536000; includeSubDomains; preload` on the apex, so
  `git.levineuwirth.org` is already covered by the parent domain. A
  consequence: any maintenance page you put up during the upgrade must be
  served over HTTPS on the same certificate. A plain-HTTP holding page will
  not render for anyone who has visited the site before.
* **`client_max_body_size`.** The classic post-upgrade surprise is a `413`
  on a large push over HTTPS, because SSH on 2222 is filtered on many
  networks and HTTPS is the dependable path here. Confirm the forge vhost
  sets it generously (`512m` or more), not nginx's 1 MB default.
* **`proxy_read_timeout`.** A first clone after an index rebuild can be slow;
  60 s is not enough for a large repository.

Confirm the real client IP still reaches Forgejo after the § 4.2
`REVERSE_PROXY_TRUSTED_PROXIES` change — the admin panel's user list shows
last-login addresses, and `127.0.0.1` everywhere means nginx's
`X-Forwarded-For` is not being set or not being trusted.

### 7.3 Close the backup gaps

Two of the three are already code; they need configuring:

1. **Off-host copies.** Copy `systemd/forgejo-backup.env.example` to
   `/etc/default/forgejo-backup`, set `OFFHOST_DEST`, `chmod 600`. Until you
   do, every nightly run logs `OFFHOST_DEST is unset — this backup exists
   ONLY on the host it backs up`. `id_storagebox` already exists on the
   laptop, so a destination probably already does too.
2. **Weekly verification.** Install and enable
   `systemd/forgejo-backup-verify.{service,timer}`; it runs
   `forgejo-backup.sh --verify` every Sunday.
3. **A real restore rehearsal**, § 2, at least once a year. `--verify`
   proves the archive is readable and the database inside it is intact; only
   § 2 proves the thing starts.

### 7.4 The security-update process

The finding this whole document answers was not "1.21 has a known
vulnerability". It was that an Internet-facing forge had drifted two years
out of support with nothing in place to notice. Fixing the version without
fixing that leaves the same instance drifting again from a newer number.

* **Subscribe to the security announcements first.** Forgejo publishes
  advance notice of security releases as issues in a dedicated repository,
  <https://codeberg.org/forgejo/security-announcements/issues>, with an RSS
  feed. That is the one feed worth an inbox rule; it exists so operators can
  plan before details are public.
* **Subscribe to releases.** <https://codeberg.org/forgejo/forgejo/releases.rss>
  (verified 200). The project also announces on `@forgejo@floss.social`.
  Security fixes land as patch releases on the supported lines.
* **Turn on the built-in checker.** Forgejo 7.0 onwards ships a
  privacy-preserving DNS-based update check, enabled by default. Leave it
  on and read the admin dashboard notice it produces.
* **Diarise a monthly check** — five minutes, mechanical:

  ```bash
  curl -s https://git.levineuwirth.org/api/v1/version
  curl -s "https://codeberg.org/api/v1/repos/forgejo/forgejo/releases?limit=5" \
    | python3 -c 'import json,sys;[print(r["tag_name"], r["published_at"][:10]) for r in json.load(sys.stdin)]'
  ```

  A patch bump on the same LTS line (`15.0.7 → 15.0.x`) needs no runbook:
  edit the tag, `docker compose pull && docker compose up -d`, check
  `api/v1/version`. Take a backup first regardless; it is eight seconds.
* **Diarise the LTS end date: 2027-07-15.** The next LTS is 19.0
  (2028-07-13), so the move is `15.0.x → 19.0.x` and it should start in
  spring 2027, not in July. Put it in the calendar now — that is the control
  that would have prevented this document.

### 7.5 Re-check the token in `tools/forgejo-sync.sh`

Forgejo 15.0 tightened access-token scoping considerably: repository
creation and deletion now require `write:user` or `write:organization`, and
public-only tokens can no longer see private repositories. `forgejo-sync.sh`
documents its token as `write:repository`. If `--create-missing` starts
returning HTTP 403 after the upgrade, regenerate the token with
`write:repository` **and** `write:user`, and correct the script's header.

---

## 8. Breaking changes between 1.21 and 15.0 that touch this instance

Compiled from the published release notes of every major in the chain. Only
entries with a plausible bearing here are listed; the full notes are at
<https://codeberg.org/forgejo/forgejo/src/branch/forgejo/release-notes-published>.

* **7.0** — Gitea themes renamed (`gitea` → `gitea-light` etc.); only matters
  if `[ui].THEMES` is set, and it is not. Webhooks now always send full refs
  (`refs/heads/x`, not `x`) — no webhooks are configured, but if any are
  added before the upgrade, check the receiver. Repository descriptions are
  restricted in what they may contain. `doctor check --fix` corrupts LFS on
  7.0.0 exactly; 7.0.16 is unaffected.
* **8.0** — MS SQL Server support removed (SQLite here). Mermaid ELK renderer
  and APA citation export removed over a licence incompatibility. Default
  `[repository].USE_COMPAT_SSH_URI` becomes `true`, so displayed SSH clone
  URLs change to `ssh://` form — cosmetic, and SSH is the convenience path
  here anyway.
* **9.0** — Application tokens carrying the `public` scope stop returning
  private resources; such tokens must be deleted and recreated. OIDC
  introspection now requires HTTP basic auth. Neither applies unless tokens
  were created with the `public` scope explicitly.
* **10.0** — the Gitea-lineage waypoint (§ 0). One API pagination fix.
* **11.0** — SSPI authentication dropped (Windows only).
* **12.0** — URL-query API authentication removed; only bites if
  `[security].DISABLE_QUERY_AUTH_TOKEN=false` was set explicitly, and it was
  not. `forgejo docs` deprecated; CLI errors move to stderr.
* **13.0** — minimum git bumped to 2.34.1 (satisfied by the image). Actions
  workflows are schema-validated; Actions are disabled here.
* **14.0** — **the `authorized_keys` startup check (§ 1.5)**, the one entry
  in this list that can stop the upgrade. Also: subcommands now error on
  stray non-flag arguments, so `--must-change-password false` (space, not
  `=`) becomes an error rather than a silent misparse — worth knowing if you
  script `forgejo admin user create`.
* **15.0** — **session cookie names become brand-independent, logging
  everyone out** unless `[security].COOKIE_REMEMBER_NAME` is pinned to
  `gitea_incredible` (§ 4.2). Access tokens tighten as in § 7.5. The
  `/etc/gitea` backward-compatibility shim is removed from the **rootless**
  images; this deployment uses the standard image and is unaffected.
* **16.0**, for when you go there — `REVERSE_PROXY_TRUSTED_PROXIES = *` is
  dropped from the image's default config (§ 4.2), git hooks move to a
  central location with a documented cleanup, and git mirror HTTP operations
  stop following redirects.

Nothing in the chain requires a SQLite-specific intervention. SQLite's
supported-version requirements did not change at any hop; only the MySQL and
PostgreSQL minimums did, at 7.0.
