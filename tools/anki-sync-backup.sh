#!/bin/bash
#
# anki-sync-backup.sh — nightly snapshot of the Anki sync server's data.
#
# Installed at /usr/local/bin/anki-sync-backup.sh, driven by
# systemd/anki-sync-backup.timer, environment from /etc/default/anki-sync-backup.
# Source of truth is this file in the repo.
#
# What is protected is review history — the one thing the memoria records
# store cannot rebuild. SYNC_BASE holds one directory per user with a
# collection.anki2 (SQLite, WAL) and the media store. A plain tar can catch
# a torn write, so each collection is snapshotted with sqlite's `.backup`,
# integrity-checked, and only then tarred with the media alongside; the
# archive counts as a backup once its .sha256 exists beside it, both
# renamed into place last. Off-host through borg (borg-offhost.sh),
# prefix anki-*, its own prune. Local retention keeps KEEP completed pairs.
#
# The integrity check runs through the sync server's own venv, not the
# sqlite3 CLI: Anki's schema uses a custom collation (unicase) that only
# its backend registers, and without it PRAGMA integrity_check cannot
# verify the indexes.
#
# The server holds each user's media.db under an exclusive lock, so the
# job stops anki-sync for the seconds the snapshot takes (03:45 UTC; a
# client that syncs into that window retries) and starts it again on
# every exit path, success or failure. With the server down the files
# are quiescent: collection.anki2 still goes through .backup + the
# integrity check, media.db and the media files are copied as they are.
#
#   anki-sync-backup.sh            # run
#   anki-sync-backup.sh --verify   # extract the newest archive, integrity_check every snapshot
#
# Environment (systemd EnvironmentFile, KEY=value):
#   SYNC_BASE   /var/lib/anki-sync       DEST  /root/anki-sync-backups   KEEP  7
#   BORG_REPO, BORG_PASSCOMMAND, BORG_RSH, OFFHOST_PRUNE — see borg-offhost.sh; unset BORG_REPO = local only
set -euo pipefail

SYNC_BASE=${SYNC_BASE:-/var/lib/anki-sync}
DEST=${DEST:-/root/anki-sync-backups}
KEEP=${KEEP:-7}
ANKI_PY=${ANKI_PY:-/opt/anki-sync/venv/bin/python}

log() { echo "anki-sync-backup: $*"; }
die() { echo "anki-sync-backup: $*" >&2; exit 1; }

# integrity_check with Anki's collations registered; prints "ok" or the problem
anki_integrity() {
    "$ANKI_PY" - "$1" <<'PY'
import sys
from anki.collection import Collection
col = Collection(sys.argv[1])
try:
    print(col.db.scalar("pragma integrity_check"))
finally:
    col.close()
PY
}

anki_count() { sqlite3 "$1" "select count(*) from $2"; }

verify_archive() {
    local archive=${1:-} tmp n
    [ -n "$archive" ] || archive=$(readlink -f "$DEST/LATEST" 2>/dev/null) \
        || die "--verify: no archive given and $DEST/LATEST does not resolve"
    [ -f "$archive.sha256" ] || die "--verify: $archive has no .sha256 companion — not a completed backup"
    (cd "$(dirname "$archive")" && sha256sum -c --quiet "$(basename "$archive.sha256")") \
        || die "--verify: checksum mismatch"
    # a global, not a local: the EXIT trap fires after the function's
    # scope is gone, and under set -u a vanished local is an error
    VERIFY_TMP=$(mktemp -d -t anki-verify-XXXXXX); trap 'rm -rf "$VERIFY_TMP"' EXIT
    local tmp=$VERIFY_TMP
    tar xzf "$archive" -C "$tmp" || die "--verify: extraction failed"
    n=0
    while IFS= read -r db; do
        local r; r=$(anki_integrity "$db" 2>&1 | tail -1)
        [ "$r" = ok ] || die "--verify: $db failed integrity_check ($r)"
        log "--verify: $(basename "$(dirname "$db")"): $(anki_count "$db" notes) notes, $(anki_count "$db" revlog) reviews, integrity ok"
        n=$((n + 1))
    done < <(find "$tmp" -name 'collection.anki2' -type f)
    [ "$n" -ge 1 ] || die "--verify: no collection.anki2 inside the archive"
    log "--verify: $archive restores ($n collection(s))"
}

case "${1:-}" in
    --verify) verify_archive "${2:-}"; exit 0 ;;
    "") ;;
    *) die "unknown argument: $1" ;;
esac

[ -d "$SYNC_BASE" ] || die "$SYNC_BASE does not exist — is the sync server installed?"
mkdir -p "$DEST"
TS=$(date -u +%Y%m%dT%H%M%SZ)
STAGE=$(mktemp -d -t anki-backup-XXXXXX)
TMP_ARCHIVE="$DEST/.anki-$TS.tar.gz.partial"
TMP_SUM="$DEST/.anki-$TS.sha256.partial"
WAS_ACTIVE=0
cleanup() {
    rm -rf "$STAGE" "$TMP_ARCHIVE" "$TMP_SUM"
    if [ "$WAS_ACTIVE" = 1 ]; then
        systemctl start anki-sync.service && log "anki-sync started again" || log "anki-sync did NOT start again — check it"
    fi
}
trap cleanup EXIT

if systemctl is-active --quiet anki-sync.service; then
    WAS_ACTIVE=1
    systemctl stop anki-sync.service || die "could not stop anki-sync"
    log "anki-sync stopped for the snapshot"
fi

users=0
for userdir in "$SYNC_BASE"/*/; do
    [ -d "$userdir" ] || continue
    user=$(basename "$userdir")
    [ -f "$userdir/collection.anki2" ] || { log "$user: no collection yet — skipped"; continue; }
    mkdir -p "$STAGE/$user"
    sqlite3 "$userdir/collection.anki2" ".backup '$STAGE/$user/collection.anki2'" \
        || die "$user: sqlite .backup failed"
    r=$(anki_integrity "$STAGE/$user/collection.anki2" 2>&1 | tail -1)
    [ "$r" = ok ] || die "$user: snapshot failed integrity_check ($r)"
    # media.db (and a WAL if one is left) and the media files: quiescent
    # with the server stopped, so plain copies are consistent
    for f in media.db media.db-wal media.db-shm media; do
        [ -e "$userdir/$f" ] && cp -a "$userdir/$f" "$STAGE/$user/"
    done
    log "$user: snapshot ok ($(anki_count "$STAGE/$user/collection.anki2" revlog) reviews, $(find "$STAGE/$user/media" -type f 2>/dev/null | wc -l) media files)"
    users=$((users + 1))
done
if [ "$users" -eq 0 ]; then
    # before the first client sync there is nothing to protect; not a failure
    log "no user collections under $SYNC_BASE yet — nothing to back up"
    exit 0
fi

tar czf "$TMP_ARCHIVE" -C "$STAGE" . || die "tar failed"
(cd "$DEST" && sha256sum "$(basename "$TMP_ARCHIVE")" | sed "s/\.anki-$TS.tar.gz.partial/anki-$TS.tar.gz/" > "$TMP_SUM")
ARCHIVE="$DEST/anki-$TS.tar.gz"
mv "$TMP_SUM" "$ARCHIVE.sha256"
mv "$TMP_ARCHIVE" "$ARCHIVE"
ln -sfn "$ARCHIVE" "$DEST/LATEST"
date -u +%Y-%m-%dT%H:%M:%SZ > "$DEST/last-success"
log "wrote $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1)) + .sha256, $users user(s)"

# the snapshot is on disk: bring the server back before the slow off-host part
if [ "$WAS_ACTIVE" = 1 ]; then
    systemctl start anki-sync.service && log "anki-sync started again" || die "anki-sync did NOT start again"
    WAS_ACTIVE=0
fi

if [ -n "${BORG_REPO:-}" ]; then
    . /usr/local/lib/borg-offhost.sh || die "off-host: /usr/local/lib/borg-offhost.sh is missing"
    borg_offhost_copy anki "$ARCHIVE" "$ARCHIVE.sha256"
else
    log "off-host: BORG_REPO is unset — this backup exists ONLY on the host it backs up."
fi

# local retention: completed pairs only, newest first by name
mapfile -t complete < <(find "$DEST" -maxdepth 1 -name 'anki-*.tar.gz' -type f | sort -r | while read -r f; do [ -f "$f.sha256" ] && echo "$f"; done)
for ((i = KEEP; i < ${#complete[@]}; i++)); do
    log "retention: pruning $(basename "${complete[$i]}")"
    rm -f "${complete[$i]}" "${complete[$i]}.sha256"
done
log "done"
