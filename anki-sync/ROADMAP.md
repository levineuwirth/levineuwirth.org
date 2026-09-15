# VPS backups and the Anki sync server — roadmap

**Status 2026-09-16: phases 1–6 are live** (done in one evening, 2026-09-15,
with the author's key for the two steps that needed it). Borg repository
`ssh://storagebox/./backup/vps` (repokey-blake2; key and passphrase in his
manager); Forgejo and Anki archives ship nightly and were restored from
the box by the verify unit; `anki-sync` serves `https://anki.levineuwirth.org/`
at PyPI `anki 26.09.2`, upgraded daily; the author's desktop and
AnkiMobile sync against it (first upload 2026-09-15 21:54 UTC: 10,009
notes). Found and fixed on the way: `/tmp` on the box is a RAM tmpfs, so
every backup/verify unit sets `TMPDIR=/var/tmp`; the sync server holds
`media.db` under an exclusive lock, so the nightly snapshot stops it for
a few seconds; Anki's `unicase` collation means integrity checks go
through the server's venv, not the sqlite3 CLI; root's login shell on
the box is fish, so remote scripts run under `bash -c`. Open: the
partner's onboarding (`nat`, files handed over by the author); the
checksum-less 2 GB Forgejo archive of 2026-09-11 awaiting his word;
the old script and unit kept as `.bak-20260915`.

Written 2026-09-15 for one dedicated session of three to four hours, in
order. The ordering is the point: the storage-box link comes first because
everything after it either writes into it (Forgejo, Anki) or is worthless
without it (a sync server whose review history has one copy). Tracked
artifacts land in this repository as they are made — `systemd/`, `nginx/`,
`tools/` — the way `forgejo/` is kept; `~/Repos/personal/memoria/docs/sync-server.md`
becomes the client-side runbook and points here.

Decisions already taken (2026-09-15, in conversation), so they are not
re-argued below: runtime is a venv with the PyPI `anki` wheel under systemd,
always latest, upgraded unattended by a daily timer that restarts only when
the version changed; exposure is a public HTTPS vhost `anki.levineuwirth.org`
with the server bound to `127.0.0.1`; two accounts with PHC `pbkdf2-sha256`
hashes (`PASSWORDS_HASHED=1`), passwords born in password managers; backups
are `sqlite3 .backup` snapshots shipped off-host by **borg** (the fleet's
tool — oneiros already backs up to the same storage box with it) into one
repository with per-set archive prefixes, Forgejo's backups moving off-host
through the same library; the mobile client is AnkiMobile (TLS 1.2 stays
on); a `vps-status` script feeds the weekly agent log — the only reader of
the journal, by design.

Every artifact is already written and reviewed in this repository; the
session is installing them. Read-only checks on the box (2026-09-15):
Arch, `borg 1.4.5` and `sqlite3` available, the storage box reachable on
port 23 from the VPS, no root ssh keys yet, `/etc/default/forgejo-backup`
absent (so Forgejo keeps 14 locally: 5.7 GB), 21 GB free, Python 3.14, no
`uv` (plain `venv` then).

| Artifact | Installs at |
|---|---|
| `tools/borg-offhost.sh` | `/usr/local/lib/borg-offhost.sh` — shared off-host half |
| `tools/forgejo-backup.sh` (borg branch added) | `/usr/local/bin/forgejo-backup.sh` |
| `systemd/forgejo-backup.env.example` | `/etc/default/forgejo-backup` |
| `tools/anki-sync-backup.sh`, `systemd/anki-sync-backup.{service,timer,env.example}` | `/usr/local/bin`, `/etc/systemd/system`, `/etc/default/anki-sync-backup` |
| `tools/vps-offsite-verify.sh`, `systemd/vps-offsite-verify.{service,timer}` | monthly restore test |
| `systemd/anki-sync.service`, `anki-sync/server.env.example`, `anki-sync/users.env.example`, `tools/anki-sync-hash` | the server |
| `tools/anki-sync-upgrade.sh`, `systemd/anki-sync-upgrade.{service,timer}` | daily latest |
| `nginx/anki-sync.conf` | `/etc/nginx/sites-available/anki-sync.conf` |
| `tools/vps-status` | runs from oneiros |

Legend: **[you]** an action only your key or account can perform; everything
else the operator (agent) does with you watching the commands that touch the
live box. Each phase ends with a check that must pass before the next.

---

## 0. Before the session — [you], ten minutes

- Her sync username: `nat` (2026-09-15).
- DNS: an `A` record `anki.levineuwirth.org → 178.104.77.249` (and `AAAA`
  if the zone has one for `git.`). Propagation is the slowest thing in
  the whole plan, so this goes first.
- Password-manager entries created empty, to be filled during the
  session: `anki sync — ln`, `anki sync — nat`, `borg — vps` (the
  passphrase and, after init, the exported repo key).

## 1. Storage-box link — 30 min

The foundation. A dedicated key on the VPS, a borg repository on the box,
the passphrase under `/etc/borg/`.

1. `pacman -S borg` on the VPS.
2. `ssh-keygen -t ed25519 -N "" -f /root/.ssh/id_storagebox -C vps-borg`
   — a machine key; the box is the only thing it can reach.
3. **[you]** authorize it on the box, the way `oneiros-config/README.md`
   records for your own key — Hetzner rejects `ssh-copy-id`:
   `ssh vps cat /root/.ssh/id_storagebox.pub | ssh -p23 storagebox install-ssh-key`
   (from oneiros, which already holds a box key).
4. `/root/.ssh/config`: `Host storagebox` → `<box>.your-storagebox.de`,
   `User <box>`, `Port 23`, `IdentityFile /root/.ssh/id_storagebox`,
   `IdentitiesOnly yes`; accept the host key once.
5. Passphrase: generated **[you]** into the manager, written to
   `/etc/borg/passphrase` (root, 0600). Then
   `BORG_PASSCOMMAND='cat /etc/borg/passphrase' borg init --encryption=repokey-blake2 ssh://storagebox/./backup/vps`,
   and `borg key export` **[you]** into the manager beside the passphrase
   — the insurance your own `borg-repo-key.txt` is.

Check: `borg info ssh://storagebox/./backup/vps` answers; a throwaway
`borg create ::probe /etc/hostname` extracts back identical, then
`borg delete ::probe`. `df` on the box says how much room retention has.

## 2. Forgejo off-host — 20 min

Closes the audit's open item. The working script already had an
off-host hook (rsync/rclone with readback); it gains `OFFHOST_TOOL=borg`,
which calls the shared library: `borg create ::forgejo-<TS>` of the
tarball and its `.sha256`, readback through `borg extract --stdout` hashed
locally, `borg prune` on the `forgejo-*` prefix, `borg compact`.

1. Install `tools/borg-offhost.sh` → `/usr/local/lib/`, the updated
   `tools/forgejo-backup.sh` → `/usr/local/bin/` (diff against the live
   copy first — the live one is the truth if they differ elsewhere).
2. `/etc/default/forgejo-backup` from the example: `OFFHOST_DEST`,
   `OFFHOST_TOOL=borg`, `BORG_PASSCOMMAND`, `BORG_RSH`; `KEEP` stays 14
   for now.
3. `systemctl start forgejo-backup.service` by hand, read the journal:
   snapshot, archive, `borg create`, readback verified, prune.
4. Install `tools/vps-offsite-verify.sh` and its units (they also cover
   the Anki set from phase 5); run the service once by hand.
5. Lower `KEEP` to 3 once step 4 passed.

Check: `borg list --glob-archives 'forgejo-*'` shows one; the verify unit
passes; the journal line reads "verified — … hashes to …".

Later, not now: point borg at Forgejo's raw data plus the SQLite snapshot
instead of the gzipped tarball, so daily runs deduplicate (gzip defeats
borg's chunking; ~1 GB/day goes to the box until then).

## 3. Sync server runtime — 30 min

1. System user `anki-sync`, home `/var/lib/anki-sync` (= `SYNC_BASE`);
   `python3 -m venv /opt/anki-sync/venv` + `pip install anki` (34 MB,
   abi3, fine on 3.14).
2. `/etc/anki-sync/server.env` from the example; `/etc/anki-sync/users.env`
   (root, 0600) with the two hashes. **[you]** generate both passwords in
   the manager, pipe each through `tools/anki-sync-hash`, share hers to
   her manager.
3. `systemd/anki-sync.service` installed and started; `journalctl -u
   anki-sync` shows `listening addr=127.0.0.1:8080`.
4. `tools/anki-sync-upgrade.sh` + timer installed; run the service once
   by hand and read "unchanged".

Check: from the VPS, `curl -s http://127.0.0.1:8080/` answers; from
oneiros over an ssh tunnel, `col.sync_login(...)` against the tunnel
succeeds for both accounts with their passwords and fails with a wrong
one.

## 4. Exposure — 20 min

1. `nginx/anki-sync.conf` (written: large bodies, long timeouts, no
   buffering, `limit_req` on `/sync/hostKey` only with 429, TLS 1.2 kept
   for AnkiMobile, its own logs, no website header snippets) → `sites-available`, symlink; the `limit_req_zone` line into `conf.d/anki-sync-zone.conf`; `nginx -t`.
2. `certbot --nginx -d anki.levineuwirth.org` — the renewal timer already
   runs; it rewrites the port-80 block into a redirect.
3. `systemctl reload nginx`.

Check: `col.sync_login(..., endpoint="https://anki.levineuwirth.org/")`
from oneiros; a sixth `hostKey` request inside a minute gets a 429.

## 5. Anki snapshot into the backup job — 15 min

`tools/anki-sync-backup.sh` (written: per-user `sqlite3 .backup` +
`integrity_check`, media alongside, tar + `.sha256`, keep 7 locally, then
the borg library with prefix `anki-*`) and its units installed;
`/etc/default/anki-sync-backup` from the example. It skips users who have
not synced yet, so it can be installed before phase 6 and starts backing
up the night after the first upload.

Check: after phase 6, run `anki-sync-backup.service` by hand and then
`vps-offsite-verify.service`; read the journal.

## 6. Clients — 30 min

In this order, because the first upload defines the server's copy:

1. **[you]** oneiros: Preferences → Syncing → self-hosted server
   `https://anki.levineuwirth.org/`, log in as `ln`, sync. Choose
   **upload** when asked — the fresh collection from 2026-09-15 is the
   truth and the server is empty.
2. **[you]** AnkiMobile: Preferences → Sync → custom sync server, the same
   URL, log in, sync (download). Then its daily reminder — the
   accountability piece this was for.
3. **[you]** her: send `build/partner-de.apkg` and the password; she
   imports the file, then sets the server URL and logs in, upload.

Check: a review done on the phone appears on the desktop after both sync.

## 7. Records — 20 min

- Commit any drift between the tracked files and what was actually
  installed — the tracked copies must describe the live box, as with
  `forgejo/`. `tools/vps-status` becomes part of the weekly agent pass.
- `~/Repos/personal/memoria/docs/sync-server.md`: replace the sketch with
  the client runbook (URLs, the upload/download choice, what to do when
  a client says the server is too old — it can't, by construction, but
  say so), pointing at this repository for the server side.
- Apocrypha `Opera/Language records.md` `## Status`: sync live, where
  backups go, what the partner has.
- Session memory: the deployed state.

---

## What is deliberately not in this session

- The Forgejo upgrade to 15.0.7 (`forgejo/UPGRADE.md`). Same box, unrelated
  risk; do it on its own day with phase 2's off-site backup already proven.
- Restic on Forgejo's raw data (see phase 2, "later").
- fail2ban. The access log will say whether it is ever needed.
- Any monitoring that pushes at you. The verify units fail loudly in the
  journal; reading it is the check.
