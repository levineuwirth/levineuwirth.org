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
#
# WHAT THE ARCHIVE CONTAINS, AND WHAT IT DELIBERATELY DOES NOT
#
#   The archive carries exactly one copy of the database: the hot snapshot
#   `forgejo-data/gitea/hot-<TS>.db`. The live `gitea.db` and its `-wal` and
#   `-shm` companions are EXCLUDED, because tar reads them page by page
#   while Forgejo is writing to them: what lands in the archive is a torn
#   file that passes `tar tzf` and fails `PRAGMA integrity_check`. Keeping
#   both invited exactly one mistake — restoring the file with the familiar
#   name. The snapshot is the database record; a restore copies it into
#   place as `gitea.db`. `--verify` and forgejo/UPGRADE.md both assume this.
#
# COMPLETENESS IS THE `.sha256` COMPANION
#
#   An archive counts as a backup only once its checksum file exists beside
#   it. Both are written under dot-prefixed temporary names and renamed into
#   place — checksum first, archive second — so a run killed at any point
#   leaves either nothing or a complete pair, never a half-written tarball
#   that retention would count as one of the copies being kept. Retention
#   enumerates only completed pairs for the same reason.
#
# OFF-HOST COPY
#
#   Everything above still lives on the disk it is backing up, which
#   protects against "I broke the database" and not against losing the VPS.
#   Set OFFHOST_DEST (see systemd/forgejo-backup.env.example) to copy each
#   completed archive somewhere else and verify it by reading it back and
#   comparing hashes. When it is unset the run says so on every line of the
#   log rather than letting the gap go quiet.
#
# Usage:
#   forgejo-backup.sh              # take a backup
#   forgejo-backup.sh --verify     # restore-test the newest archive
#   forgejo-backup.sh --verify /path/to/forgejo-<TS>.tar.gz
#
set -euo pipefail

SRC=${SRC:-/root/forgejo-server}
DEST=${DEST:-/root/forgejo-backups}
KEEP=${KEEP:-14}
CONTAINER=${CONTAINER:-forgejo}

# Off-host copy. Unset by default: the feature is opt-in, and a run with no
# destination configured is a successful local backup, not a failure.
#   OFFHOST_DEST   rsync/rclone destination, e.g. user@storage:forgejo/ or remote:forgejo/
#   OFFHOST_TOOL   rsync (default) or rclone
#   OFFHOST_VERIFY readback (default) or none
OFFHOST_DEST=${OFFHOST_DEST:-}
OFFHOST_TOOL=${OFFHOST_TOOL:-}
OFFHOST_VERIFY=${OFFHOST_VERIFY:-readback}

VERIFY_TMP=""
log() { echo "forgejo-backup: $*"; }
die() { echo "forgejo-backup: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# sqlite3, wherever it lives.
#
# The host does not necessarily have sqlite3 installed; the Forgejo image
# always does. During a backup the container is running and `docker exec` is
# the obvious route. During `--verify` it may not be (a verify is exactly
# what one runs when the instance is down), so fall back to the host binary
# and then to a throwaway container built from the same image.
# ---------------------------------------------------------------------------
sqlite_on_host_path() {
    # sqlite_on_host_path <db-path-on-host> <sql>
    local db=$1 sql=$2 image
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$db" "$sql"
        return
    fi
    image=${FORGEJO_IMAGE:-}
    if [ -z "$image" ]; then
        image=$(docker inspect -f '{{.Config.Image}}' "$CONTAINER" 2>/dev/null) || true
    fi
    [ -n "$image" ] || die "no sqlite3 on the host and no image to borrow one from (set FORGEJO_IMAGE)"
    docker run --rm --entrypoint sqlite3 \
        -v "$(dirname "$db")":/verify:ro "$image" "/verify/$(basename "$db")" "$sql"
}

# ---------------------------------------------------------------------------
# --verify — the restoration test the runbook calls for.
#
# A `tar tzf` proves the archive decompresses. It does not prove the thing
# inside it is a database anyone can start Forgejo against. This extracts a
# real copy and runs the same integrity check the backup path runs, on the
# same file a restore would put in place.
# ---------------------------------------------------------------------------
verify_archive() {
    local archive=${1:-}
    if [ -z "$archive" ]; then
        archive=$(readlink -f "$DEST/LATEST" 2>/dev/null) \
            || die "--verify: no archive given and $DEST/LATEST does not resolve"
    fi
    [ -f "$archive" ] || die "--verify: $archive does not exist"
    [ -f "$archive.sha256" ] || die "--verify: $archive has no .sha256 companion — it is not a completed backup"

    log "verify: $archive"
    ( cd "$(dirname "$archive")" && sha256sum -c "$(basename "$archive").sha256" >/dev/null ) \
        || die "--verify: checksum mismatch — the archive on disk is not the one that was written"
    log "verify: checksum ok"

    # An EXIT trap, not RETURN: `die` exits, which never fires RETURN, and a
    # verification that fails is exactly when a stray extracted copy of the
    # whole instance would be left behind in /tmp.
    VERIFY_TMP=$(mktemp -d -t forgejo-verify-XXXXXX)
    trap 'rm -rf "$VERIFY_TMP"' EXIT
    local tmp=$VERIFY_TMP
    tar xzf "$archive" -C "$tmp" || die "--verify: extraction failed"

    # The archive's top-level directory follows $SRC's basename; find it
    # rather than assuming it is still "forgejo-server".
    local top data
    top=$(find "$tmp" -mindepth 1 -maxdepth 1 -type d | head -1)
    data="$top/forgejo-data"
    [ -d "$data" ] || die "--verify: $archive has no */forgejo-data — wrong archive layout"

    if [ -e "$data/gitea/gitea.db" ]; then
        log "verify: WARNING — the archive contains a live gitea.db; this script excludes it,"
        log "verify: so this archive predates that change. Restore the hot-*.db snapshot, not gitea.db."
    fi

    local snaps snap n
    mapfile -t snaps < <(find "$data/gitea" -maxdepth 1 -name 'hot-*.db' -print | sort)
    n=${#snaps[@]}
    [ "$n" -ge 1 ] || die "--verify: no hot-*.db snapshot inside the archive — nothing to restore from"
    [ "$n" -eq 1 ] || log "verify: WARNING — $n snapshots present, using the newest"
    snap=${snaps[$((n - 1))]}
    log "verify: snapshot $(basename "$snap") ($(du -h "$snap" | cut -f1))"

    # sqlite3 exits non-zero on a malformed file, and under `set -e` that
    # would end the run with sqlite's own message and no context. Catch it so
    # the failure reads as a failed backup verification, which is what it is.
    local integrity
    integrity=$(sqlite_on_host_path "$snap" "PRAGMA integrity_check;" 2>&1) \
        || integrity="sqlite3 could not read the snapshot: $integrity"
    [ "$integrity" = "ok" ] || die "--verify: snapshot failed integrity_check ($integrity)"
    log "verify: PRAGMA integrity_check ok"

    local repos users
    repos=$(sqlite_on_host_path "$snap" "SELECT COUNT(*) FROM repository;" 2>/dev/null) || repos="?"
    users=$(sqlite_on_host_path "$snap" "SELECT COUNT(*) FROM user;" 2>/dev/null) || users="?"
    log "verify: snapshot holds $repos repositories, $users users"

    # The invariant worth checking is agreement, not a positive count: a forge
    # with no repositories is unusual but legitimate, whereas a database that
    # knows about repositories the archive does not carry means the tar
    # excluded too much, which is the failure this whole file is guarding.
    local bare
    bare=$(find "$data/git/repositories" -maxdepth 2 -name '*.git' -type d 2>/dev/null | wc -l)
    log "verify: archive holds $bare bare repositories under git/repositories"
    if [ "$repos" != "?" ] && [ "$repos" -gt 0 ] && [ "$bare" -eq 0 ]; then
        die "--verify: the snapshot lists $repos repositories but the archive carries none"
    fi

    if [ -f "$top/docker-compose.yml" ]; then
        log "verify: docker-compose.yml present (image: $(grep -m1 'image:' "$top/docker-compose.yml" | sed 's/^[[:space:]]*image:[[:space:]]*//'))"
    else
        log "verify: WARNING — no docker-compose.yml in the archive"
    fi

    log "verify: OK — restore this snapshot over forgejo-data/gitea/gitea.db"
    return 0
}

# ---------------------------------------------------------------------------
# Off-host copy.
# ---------------------------------------------------------------------------
offhost_copy() {
    local archive=$1 sum="$1.sha256" tool=$OFFHOST_TOOL

    if [ -z "$tool" ]; then
        # `remote:path` with no @ and no / before the colon is rclone's
        # syntax; anything else (a path, or user@host:path) is rsync's.
        if [[ "$OFFHOST_DEST" =~ ^[A-Za-z0-9_-]+: ]] && command -v rclone >/dev/null 2>&1; then
            tool=rclone
        else
            tool=rsync
        fi
    fi
    command -v "$tool" >/dev/null 2>&1 || die "off-host: $tool is not installed"

    log "off-host: copying to $OFFHOST_DEST with $tool"
    case "$tool" in
        rsync)  rsync -a --partial "$archive" "$sum" "$OFFHOST_DEST" ;;
        rclone) rclone copy "$archive" "$OFFHOST_DEST" && rclone copy "$sum" "$OFFHOST_DEST" ;;
        *)      die "off-host: unknown OFFHOST_TOOL '$tool'" ;;
    esac || die "off-host: transfer failed — the local archive is kept, retention did not run"

    if [ "$OFFHOST_VERIFY" = none ]; then
        log "off-host: OFFHOST_VERIFY=none — transfer NOT verified"
        return 0
    fi

    # Read the remote copy back and hash it here. Slower than asking the
    # remote for a digest, but it works against storage that offers no shell
    # and it proves the bytes that arrived are the bytes that left.
    local back want got
    back=$(mktemp -t forgejo-offhost-XXXXXX)
    case "$tool" in
        rsync)  rsync -a "${OFFHOST_DEST%/}/$(basename "$archive")" "$back" ;;
        rclone) rclone cat "${OFFHOST_DEST%/}/$(basename "$archive")" > "$back" ;;
    esac || { rm -f "$back"; die "off-host: could not read the copy back — treat the transfer as failed"; }

    want=$(awk '{print $1}' "$sum")
    got=$(sha256sum "$back" | awk '{print $1}')
    rm -f "$back"
    [ "$want" = "$got" ] || die "off-host: read-back checksum mismatch (want $want, got $got)"
    log "off-host: verified — remote copy hashes to $got"
}

# ---------------------------------------------------------------------------
# Retention. Only completed pairs (archive + .sha256) are counted, so a
# partial file from an interrupted run can never displace a good backup.
# Local only, deliberately: a broken remote must not be able to delete
# history here.
# ---------------------------------------------------------------------------
prune_retention() {
    # Newest first by NAME, not by mtime: the timestamp is in the filename in
    # UTC and sorts chronologically, so the order survives a copy, a restore,
    # or a `touch` in a way `ls -1t` does not.
    local complete=() incomplete=() f
    while IFS= read -r f; do
        if [ -f "$f.sha256" ]; then complete+=("$f"); else incomplete+=("$f"); fi
    done < <(find "$DEST" -maxdepth 1 -name 'forgejo-*.tar.gz' -type f 2>/dev/null | sort -r)

    for f in "${incomplete[@]+"${incomplete[@]}"}"; do
        log "retention: $(basename "$f") has no .sha256 — NOT counted, NOT pruned; inspect by hand"
    done

    local total=${#complete[@]} i
    log "retention: $total completed archive(s) present, keeping $KEEP"
    if [ "$total" -gt "$KEEP" ]; then
        for ((i = KEEP; i < total; i++)); do
            log "retention: pruning $(basename "${complete[$i]}")"
            rm -f "${complete[$i]}" "${complete[$i]}.sha256"
        done
    fi

    # Sweep debris: temporaries from a killed run, and checksums whose
    # archive never landed (the window between the two renames below).
    while IFS= read -r f; do
        log "retention: removing leftover $(basename "$f")"
        rm -f "$f"
    done < <(find "$DEST" -maxdepth 1 -name '.forgejo-*.partial' -type f 2>/dev/null)
    while IFS= read -r f; do
        [ -f "${f%.sha256}" ] && continue
        log "retention: removing orphan $(basename "$f")"
        rm -f "$f"
    done < <(find "$DEST" -maxdepth 1 -name 'forgejo-*.tar.gz.sha256' -type f 2>/dev/null)
}

# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------
case "${1:-}" in
    --verify)  verify_archive "${2:-}"; exit 0 ;;
    --prune)   prune_retention; exit 0 ;;
    -h|--help) sed -n '2,50p' "$0"; exit 0 ;;
    "")        ;;
    *)         die "unknown argument: $1 (try --help)" ;;
esac

TS=$(date -u +%Y%m%dT%H%M%SZ)
SNAP_REL="gitea/hot-$TS.db"
SNAP="$SRC/forgejo-data/$SNAP_REL"
ARCHIVE="$DEST/forgejo-$TS.tar.gz"
TMP_ARCHIVE="$DEST/.forgejo-$TS.tar.gz.partial"
TMP_SUM="$DEST/.forgejo-$TS.tar.gz.sha256.partial"

mkdir -p "$DEST"

# Remove the in-data snapshot and any temporaries on any exit path, success
# or failure, so a crashed run cannot leave stray database copies inside the
# live data directory where the next tar would pick them up.
LIST=""
cleanup() { rm -f "$SNAP" "$TMP_ARCHIVE" "$TMP_SUM" ${LIST:+"$LIST"}; }
trap cleanup EXIT

log "starting $TS"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    die "container '$CONTAINER' is not running — aborting"
fi

# Snapshots are only ever created by this script, so anything left over is
# debris from a run that died before its trap fired. Clearing it here keeps
# the archive down to exactly one database.
while IFS= read -r stale; do
    log "clearing stale snapshot $(basename "$stale")"
    rm -f "$stale"
done < <(find "$SRC/forgejo-data/gitea" -maxdepth 1 -name 'hot-*.db' -type f 2>/dev/null)

docker exec "$CONTAINER" sqlite3 /data/gitea/gitea.db ".backup '/data/$SNAP_REL'"

INTEGRITY=$(docker exec "$CONTAINER" sqlite3 "/data/$SNAP_REL" "PRAGMA integrity_check;")
if [ "$INTEGRITY" != "ok" ]; then
    die "snapshot failed integrity_check ($INTEGRITY) — aborting"
fi

REPOS=$(docker exec "$CONTAINER" sqlite3 "/data/$SNAP_REL" "SELECT COUNT(*) FROM repository;")
log "snapshot ok, $REPOS repositories — this file is the database record in the archive"

# The live database is excluded: see the header. tar reading gitea.db while
# Forgejo writes to it produces a file that decompresses and does not open.
# The patterns are relative to the member names tar writes, which start at
# $(basename "$SRC") — hardcoding "forgejo-server" would silently stop
# excluding anything the moment SRC is pointed somewhere else.
TOP=$(basename "$SRC")
tar czf "$TMP_ARCHIVE" \
    --exclude="$TOP/forgejo-data/gitea/gitea.db" \
    --exclude="$TOP/forgejo-data/gitea/gitea.db-wal" \
    --exclude="$TOP/forgejo-data/gitea/gitea.db-shm" \
    -C "$(dirname "$SRC")" "$TOP"

# Prove the archive reads back before it is allowed to count as a backup and
# push an older one out of the retention window. The listing is taken once
# and asserted against, rather than piped into grep: under `pipefail` a
# `grep -q` that matches early kills tar with SIGPIPE and the whole pipeline
# reports failure, which would condemn a perfectly good archive.
LIST=$(mktemp -t forgejo-backup-list-XXXXXX)
if ! tar tzf "$TMP_ARCHIVE" > "$LIST" 2>/dev/null; then
    die "archive is unreadable — discarding and aborting"
fi
grep -q "forgejo-data/$SNAP_REL" "$LIST" \
    || die "archive does not contain the snapshot $SNAP_REL — discarding and aborting"
if grep -qE "forgejo-data/gitea/gitea\.db(-wal|-shm)?\$" "$LIST"; then
    die "the live gitea.db leaked into the archive — the --exclude patterns are wrong"
fi

# The checksum names the final archive, not the temporary, so `sha256sum -c`
# works unchanged in $DEST after the renames below.
( cd "$DEST" && sha256sum "$(basename "$TMP_ARCHIVE")" \
    | sed "s|$(basename "$TMP_ARCHIVE")|$(basename "$ARCHIVE")|" > "$(basename "$TMP_SUM")" )

# Two renames, checksum first. A run killed between them leaves a checksum
# with no archive — invisible to retention, swept by the next run — whereas
# the other order would leave an archive that never becomes complete.
mv "$TMP_SUM" "$ARCHIVE.sha256"
mv "$TMP_ARCHIVE" "$ARCHIVE"

ln -sfn "$ARCHIVE" "$DEST/LATEST"
date -u +%Y-%m-%dT%H:%M:%SZ > "$DEST/last-success"

SIZE=$(du -h "$ARCHIVE" | cut -f1)
log "wrote $ARCHIVE ($SIZE) + .sha256"

if [ -n "$OFFHOST_DEST" ]; then
    offhost_copy "$ARCHIVE"
else
    log "off-host: OFFHOST_DEST is unset — this backup exists ONLY on the host it backs up."
    log "off-host: set it in /etc/default/forgejo-backup to close that gap."
fi

prune_retention
log "done"
