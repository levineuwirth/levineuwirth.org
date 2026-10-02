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
| `anki-sync-upgrade` | daily 04:30 +15m | the server's venv (PyPI `anki`); restarts the server |
| `forgejo-backup-verify` | Sun 04:30 +20m | restores the newest local Forgejo archive into a scratch container |
| `couchdb-backup-verify` | Sun 04:45 +10m | restores the newest local CouchDB archive into a scratch container on 127.0.0.1:15984 |
| `forgejo-update` | daily 05:00 +15m | pulls `forgejo:15`; backs up, recreates, checks (state in `/var/lib/forgejo-update/`) |
| `couchdb-update` | daily 05:30 +15m | pulls `couchdb:3`; backs up, copies `couchdb-data` cold, recreates, checks; puts data and image back on failure (state in `/var/lib/couchdb-update/`) |
| `vps-offsite-verify` | 1st 05:00 +1h | `borg check`, then restores the newest archive of every set from the storage box |

Containers: `forgejo` (127.0.0.1:3000, and :2222 for git over ssh) and
`couchdb` (127.0.0.1:5984), both behind nginx.

The three backups and the monthly verify share one borg repository on the
storage box; every borg call waits for its lock (`BORG_LOCK_WAIT`, default
30 min) rather than failing the job that comes second. `anki-sync-backup`
and `anki-sync-upgrade` share `/run/lock/anki-sync.lock`.

Health: `tools/vps-status` (run from the laptop). A backup set is fresh when
its `offhost` age is under a day: `local` is stamped before the upload,
`offhost` only after the upload has been read back.

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
# 2. pin the server's identity BEFORE the compose file that mounts it
#    (root's shell is fish, so the environment is read inside bash)
ssh root@vps "bash -c 'set -a; . /etc/default/couchdb-backup; set +a; couchdb-backup.sh --instance-ini > /root/couchdb-server/instance.ini && chmod 600 /root/couchdb-server/instance.ini && cat /root/couchdb-server/instance.ini'"
# 3. the compose file — do NOT `docker compose up` it by hand: that would
#    pull couchdb:3 and recreate without a backup, a cold copy or any check
scp couchdb/docker-compose.yml root@vps:/root/couchdb-server/
# 4. the first update, supervised: 3.4.2 -> 3.5.x through the script's own safety
ssh root@vps couchdb-update.sh
# 5. the timer
scp systemd/couchdb-update.{service,timer} root@vps:/etc/systemd/system/
ssh root@vps 'systemctl daemon-reload && systemctl enable --now couchdb-update.timer'
```

Then check what the script already checks, by hand once: `curl -su admin
http://127.0.0.1:5984/` shows 3.5.x and the uuid in `instance.ini`; a
foreign `Origin` gets no `Access-Control-Allow-Origin`; desktop and iPad
sync (still owed for W02). `couchdb/RESTORE.md` is the procedure for
everything this does not cover.

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
