# VPS units

What runs on the VPS, when, and what it touches; the units and scripts here
are the source of truth, installed by hand (each unit's header has its
`scp` lines). `archive-check.*` is the exception: a user unit on the
laptop, linked from this checkout.

All times UTC. `+n` is the timer's `RandomizedDelaySec`.

| Unit | When | Touches |
|---|---|---|
| `anki-sync.service` | always | the Anki sync server, 127.0.0.1:8080 (nginx `anki.`) |
| `couchdb-backup` | daily 03:15 +10m | CouchDB dump → `/root/couchdb-backups`, borg `couchdb-*` |
| `forgejo-backup` | daily 03:30 +20m | Forgejo snapshot + tarball → `/root/forgejo-backups`, borg `forgejo-*` |
| `anki-sync-backup` | daily 03:45 +10m | stops the server, snapshots, restarts → `/root/anki-sync-backups`, borg `anki-*` |
| `vps-config-backup` | daily 04:00 +10m | `/etc` (not `/etc/borg`), the compose directories without their data, `/usr/local`, update state, an inventory of packages, Docker networks and units → `/root/vps-config-backups`, borg `config-*` |
| `anki-sync-upgrade` | daily 04:30 +15m | the server's venv (PyPI `anki`); restarts the server |
| `forgejo-backup-verify` | Sun 04:30 +20m | restores the newest local Forgejo archive into a scratch container |
| `couchdb-backup-verify` | Sun 04:45 +10m | restores the newest local CouchDB archive into a scratch container on 127.0.0.1:15984 |
| `forgejo-update` | daily 05:00 +15m | pulls `forgejo:15`; backs up, recreates, checks (state in `/var/lib/forgejo-update/`) |
| `couchdb-update` | daily 05:30 +15m | pulls `couchdb:3`; backs up, copies `couchdb-data` cold, recreates, checks; puts data and image back on failure (state in `/var/lib/couchdb-update/`) |
| `anubis-update` | daily 06:00 +15m | resolves the latest stable 1.x image to a digest; backs up, saves cold challenge state, replaces, checks stability and rolls back on failure (`anubis/README.md`) |
| `vps-offsite-verify` | 1st 05:00 +1h | `borg check`, then restores the newest archive of every set from the storage box |

Containers: `forgejo` (127.0.0.1:3000, and :2222 for git over ssh) and
`couchdb` (127.0.0.1:5984), both behind nginx. The forge's HTTPS traffic first
passes through `anubis` (127.0.0.1:8923); its private health/metrics listener
is 127.0.0.1:9091.

The four backups and the monthly verify share one borg repository on the
storage box; every borg call waits for its lock (`BORG_LOCK_WAIT`, default
30 min) rather than failing the job that comes second. `anki-sync-backup`
and `anki-sync-upgrade` share `/run/lock/anki-sync.lock`.

Health: `tools/vps-status` (run from the laptop). A backup set is fresh when
its `offhost` age is under a day: `local` is stamped before the upload,
`offhost` only after the upload has been read back.

## Rebuilding the host

A new VPS needs the repo, the borg repository and the password manager (the
borg passphrase and the storage-box key, neither of which is in any backup).
The newest `config-*` archive holds the rest of the host: restore `/etc/nginx`,
`/etc/letsencrypt`, `/etc/default/*`, `/etc/anki-sync`, the compose
directories and `/usr/local` from it, reinstall the packages in
`inventory/packages.txt`, recreate `proxy-net` before Forgejo's first start
with the command in `forgejo/docker-compose.yml` (check the subnet against
`inventory/docker-networks.json`), then restore each service's data from its
own set (`couchdb/RESTORE.md`, `forgejo/UPGRADE.md`).

The config set also holds `/root/anubis-server` including its signing key,
but excludes the temporary `state/` database. Recreate `state/` as UID/GID
1000, mode 0700, and start Anubis before enabling the forge's nginx vhost;
see `anubis/README.md`. Restoring without its temporary challenge database
can make visitors solve the challenge again.

## Installing the configuration backup (audit Y13)

```bash
scp tools/vps-config-backup.sh tools/vps-offsite-verify.sh root@vps:/usr/local/bin/
scp systemd/vps-config-backup.{service,timer} systemd/vps-offsite-verify.service root@vps:/etc/systemd/system/
scp systemd/vps-config-backup.env.example root@vps:/etc/default/vps-config-backup
ssh root@vps 'chmod 600 /etc/default/vps-config-backup && chmod 755 /usr/local/bin/vps-config-backup.sh && systemctl daemon-reload'
ssh root@vps 'systemctl start vps-config-backup.service && vps-config-backup.sh --verify && ls -l /root/vps-config-backups/'
ssh root@vps 'systemctl enable --now vps-config-backup.timer'
ssh root@vps "docker network inspect proxy-net -f '{{json .IPAM.Config}}'"   # 172.18.0.0/16 via 172.18.0.1, as the compose file says
```

`tools/vps-status` (run from the laptop) now lists the job and the `config`
set's stamps, and the monthly verify restores the set.

## Installing the 2026-10-04 cleanup changes

The four backup scripts now source `tools/backup-pair.sh` for the
archive-and-checksum steps and retention they each used to copy; only
forgejo-backup's copy swept the temporaries a killed run leaves, so the
others could keep a multi-gigabyte `.partial` forever. `couchdb-update.sh`
gains forgejo-update's stability window and a health check on runs with
nothing to apply, and `forgejo-update.sh` takes a lock as the other
updaters do. Install the library before the scripts, in one go, so no
nightly run finds one without the other:

```bash
scp tools/backup-pair.sh root@vps:/usr/local/lib/
scp tools/{forgejo-backup,couchdb-backup,anki-sync-backup,vps-config-backup,couchdb-update,forgejo-update}.sh root@vps:/usr/local/bin/
ssh root@vps 'chmod 644 /usr/local/lib/backup-pair.sh && chmod 755 /usr/local/bin/*.sh && bash -n /usr/local/lib/backup-pair.sh'
```

Then run one backup by hand and verify it, e.g.
`systemctl start vps-config-backup.service && vps-config-backup.sh --verify`;
its log ends with the retention lines from `pair_prune`. The updaters need
no hand run; their next timer runs use the new checks.

## Installing the 2026-10-02 changes (audit phase 4)

Everything below is committed and was rehearsed locally (real borg 1.4.5,
stubbed docker/pip/systemctl); none of it is on the VPS until these steps
run. From the checkout:

```bash
scp tools/borg-offhost.sh root@vps:/usr/local/lib/
scp tools/{forgejo-backup,anki-sync-backup,couchdb-backup,vps-offsite-verify,forgejo-update,anki-sync-upgrade}.sh root@vps:/usr/local/bin/
scp systemd/{forgejo-backup,anki-sync-backup,couchdb-backup,vps-offsite-verify}.service \
    systemd/{forgejo-update,anki-sync-upgrade,forgejo-backup-verify}.service \
    systemd/{anki-sync-backup,couchdb-backup-verify}.timer root@vps:/etc/systemd/system/
ssh root@vps 'chmod 755 /usr/local/bin/*.sh && systemctl daemon-reload'
```

Then, in each `/etc/default/{forgejo,anki-sync,couchdb}-backup` that sets
`BORG_RSH`, add the keepalive the examples now carry
(`-o ServerAliveInterval=30 -o ServerAliveCountMax=4`). Leave `OFFHOST_PRUNE`
unset when it is absent, so the new default applies. If it is already set,
add `--keep-within 7d` while retaining the existing daily, weekly and monthly
rules; an explicit old value overrides the new default. Check:

```bash
ssh root@vps 'systemd-analyze verify /etc/systemd/system/{forgejo,anki-sync,couchdb}-backup.service; systemctl list-timers --all | grep -E "backup|verify|update|upgrade"'
ssh root@vps 'systemctl start couchdb-backup.service && ls -l /root/couchdb-backups/last-offhost-success'
tools/vps-status
```

The first nightly runs write `last-offhost-success` for the other two sets;
until then `vps-status` shows `offhost=none` for them.

## Installing the CouchDB changes (audit phase 2)

Committed and rehearsed locally against real `couchdb:3.4.2` and
`couchdb:3` (3.5.2.1) images: a backup/verify/restore round trip, a rebuild
from an archive alone, an update 3.4.2 → 3.5.2, and rollbacks from an
image that never starts and from one that starts and wipes the data. In
this order, because the new compose file mounts `instance.ini` and moves to
`couchdb:3`:

```bash
# 1. the new backup script, and a backup that carries _security, accounts and identity
scp tools/couchdb-backup.sh tools/couchdb-update.sh root@vps:/usr/local/bin/
ssh root@vps 'chmod 755 /usr/local/bin/couchdb-{backup,update}.sh && systemctl start couchdb-backup.service && couchdb-backup.sh --verify'
# 2. pin the identity BEFORE the compose mount. Let systemd read its own
#    EnvironmentFile syntax (unquoted spaces are valid there, not in bash).
#    The identity contains the cookie secret: never print it to the terminal.
ssh root@vps "bash -c 'set -e; umask 077; t=\$(mktemp /root/couchdb-server/.instance-XXXXXX); systemd-run --quiet --wait --pipe -p EnvironmentFile=/etc/default/couchdb-backup /usr/local/bin/couchdb-backup.sh --instance-ini > \"\$t\"; test -s \"\$t\"; mv \"\$t\" /root/couchdb-server/instance.ini'"
# 3. install the sync proxy's maintenance guard before enabling updates
scp nginx/couchdb-sync.conf root@vps:/etc/nginx/sites-available/couchdb-sync.conf
ssh root@vps 'nginx -t && systemctl reload nginx'
# 4. the compose file — do NOT `docker compose up` it by hand: that would
#    pull couchdb:3 and recreate without a backup, a cold copy or any check
scp couchdb/docker-compose.yml root@vps:/root/couchdb-server/
# 5. the first update, supervised: 3.4.2 -> 3.5.x through the script's own safety
ssh root@vps couchdb-update.sh
# 6. the timer
scp systemd/couchdb-update.{service,timer} root@vps:/etc/systemd/system/
ssh root@vps 'systemctl daemon-reload && systemctl enable --now couchdb-update.timer'
```

Then check what the script already checks, by hand once: `curl -su admin
http://127.0.0.1:5984/` shows 3.5.x and the uuid in `instance.ini`; a
foreign `Origin` gets no `Access-Control-Allow-Origin`; desktop and iPad
sync (still owed for W02). `couchdb/RESTORE.md` is the procedure for
everything this does not cover.

The proxy returns 503 during candidate validation and rollback, so clients
cannot receive a successful write that a rollback would discard. Interrupted
updates retain `needs-operator`, `hold`, and `maintenance` in
`/var/lib/couchdb-update/`; the recovery marker names the previous image and
cold copy. Check those files and the journal before recovering. Remove
`needs-operator` and `maintenance` only after checking the recovered server's
version, counts, uuid, auth secret and effective CORS. Keep `hold` until the
failed candidate is understood. See `couchdb/RESTORE.md`.

## Isolating the VPS's storage-box key (audit Y02)

Today the VPS key logs in to the storage box's main account, so a root
compromise of the VPS can delete the laptop's backups (`backup/thissystem`)
as well as its own. In the Hetzner console:

1. Storage Box → Sub-accounts → create one with base directory
   `backup/vps` and SSH enabled. Note its user (`<box>-subN`).
2. If the plan offers it, enable automatic snapshots of the storage box:
   a sub-account cannot delete them, which is the protection against a
   deleted or encrypted repository.

Then:

```bash
# install the VPS key on the sub-account (asks for the sub-account password once)
ssh root@vps 'cat /root/.ssh/id_storagebox.pub | ssh -p23 <box>-subN@<box>-subN.your-storagebox.de install-ssh-key'
# point the VPS's ssh alias at the sub-account: in /root/.ssh/config,
# Host storagebox → User <box>-subN and HostName <box>-subN.your-storagebox.de
# the repository is now the sub-account's home directory:
#   BORG_REPO=ssh://storagebox/./   in /etc/default/{anki-sync,couchdb}-backup
#   OFFHOST_DEST=ssh://storagebox/./   in /etc/default/forgejo-backup
ssh root@vps 'BORG_RELOCATED_REPO_ACCESS_IS_OK=yes BORG_PASSCOMMAND="cat /etc/borg/passphrase" borg list ssh://storagebox/./ | tail -3'
# confirm the sub-account cannot see the laptop's repository (this must fail):
ssh root@vps 'ssh storagebox ls ../thissystem'
```

Last, remove the VPS key (comment `vps-borg`) from the **main** account's
`.ssh/authorized_keys` on the box, and confirm
`ssh root@vps 'ssh -p23 <box>@<box>.your-storagebox.de ls'` is refused.
Whether the box honours a `command="borg serve --append-only"` restriction
on a key is unverified; if it does, add it to the sub-account's key and
run `borg prune`/`compact` for the VPS repository from the laptop instead.
