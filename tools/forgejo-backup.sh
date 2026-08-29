#!/bin/bash
#
# forgejo-backup.sh — nightly backup of the Forgejo instance on the VPS.
#
# Installed at /usr/local/bin/forgejo-backup.sh and driven by
# systemd/forgejo-backup.timer. Source of truth is this file in the repo.
#
# The database is SQLite, so the whole instance is a directory and a 2 MB
# file — but a plain `cp` of a live SQLite database can capture a torn
# write. `.backup` takes a consistent snapshot of a running database, and
# the snapshot is integrity-checked before anything is allowed to depend on
# it. If the check fails the run aborts non-zero, so systemd marks the unit
# failed rather than quietly writing a corrupt archive over a good one.
#
# Nothing is stopped: Forgejo stays up for the duration.
set -euo pipefail

SRC=/root/forgejo-server
DEST=/root/forgejo-backups
KEEP=${KEEP:-14}
TS=$(date -u +%Y%m%dT%H%M%SZ)
SNAP_REL="gitea/hot-$TS.db"
SNAP="$SRC/forgejo-data/$SNAP_REL"

mkdir -p "$DEST"

# Remove the in-data snapshot on any exit path, success or failure, so a
# crashed run cannot leave stray database copies inside the live data
# directory where the next tar would pick them up.
cleanup() { rm -f "$SNAP"; }
trap cleanup EXIT

echo "forgejo-backup: starting $TS"

if ! docker ps --format '{{.Names}}' | grep -qx forgejo; then
    echo "forgejo-backup: container 'forgejo' is not running — aborting" >&2
    exit 1
fi

docker exec forgejo sqlite3 /data/gitea/gitea.db ".backup '/data/$SNAP_REL'"

INTEGRITY=$(docker exec forgejo sqlite3 "/data/$SNAP_REL" "PRAGMA integrity_check;")
if [ "$INTEGRITY" != "ok" ]; then
    echo "forgejo-backup: snapshot failed integrity_check ($INTEGRITY) — aborting" >&2
    exit 1
fi

REPOS=$(docker exec forgejo sqlite3 "/data/$SNAP_REL" "SELECT COUNT(*) FROM repository;")
echo "forgejo-backup: snapshot ok, $REPOS repositories"

ARCHIVE="$DEST/forgejo-$TS.tar.gz"
tar czf "$ARCHIVE" -C /root forgejo-server

# Prove the archive reads back before it is allowed to count as a backup and
# push an older one out of the retention window.
if ! tar tzf "$ARCHIVE" >/dev/null 2>&1; then
    echo "forgejo-backup: archive is unreadable — removing and aborting" >&2
    rm -f "$ARCHIVE"
    exit 1
fi

sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"
ln -sfn "$ARCHIVE" "$DEST/LATEST"
date -u +%Y-%m-%dT%H:%M:%SZ > "$DEST/last-success"

SIZE=$(du -h "$ARCHIVE" | cut -f1)
echo "forgejo-backup: wrote $ARCHIVE ($SIZE)"

# Retention. Prune only fully-formed archives (each has a .sha256 beside
# it), so a partial file from an interrupted run is never counted as one of
# the copies being kept.
mapfile -t OLD < <(ls -1t "$DEST"/forgejo-*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)))
for f in "${OLD[@]:-}"; do
    [ -n "$f" ] || continue
    echo "forgejo-backup: pruning $(basename "$f")"
    rm -f "$f" "$f.sha256"
done

COUNT=$(ls -1 "$DEST"/forgejo-*.tar.gz 2>/dev/null | wc -l)
echo "forgejo-backup: done — $COUNT archive(s) retained, keeping $KEEP"
