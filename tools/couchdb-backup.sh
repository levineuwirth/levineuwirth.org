#!/bin/bash
#
# couchdb-backup.sh — nightly logical dump of the LiveSync databases.
#
# Installed at /usr/local/bin/couchdb-backup.sh, driven by
# systemd/couchdb-backup.timer, environment from /etc/default/couchdb-backup.
# Source of truth is this file in the repo.
#
# CouchDB's own on-disk files are crash-only and can be tarred while live,
# but a raw file copy is only ever restorable by starting an identical
# CouchDB against it — there is no equivalent of `PRAGMA integrity_check`
# to prove the copy is sound, and no way to restore one database without
# the others. `couchbackup`/`couchrestore` (the project's own logical dump
# tool) write one database as a stream of documents instead: restorable on
# its own, into any CouchDB, and provably intact because --verify below
# actually restores it into a scratch container and compares document
# counts, not just untars it.
#
# Needs couchbackup/couchrestore on the host: `npm install -g
# @cloudant/couchbackup`. That is a new dependency for this VPS — forgejo
# and anki-sync back up with tools already on the box.
#
# DBS is a fixed list, not autodiscovered from _all_dbs, so a stray test
# database never silently starts counting as something this backs up, and
# a renamed vault fails loudly instead of quietly stopping being backed up.
#
# Off-host through borg (borg-offhost.sh), prefix couchdb-*, its own
# prune. Local retention keeps KEEP completed pairs — same shape as
# forgejo-backup.sh / anki-sync-backup.sh.
#
#   couchdb-backup.sh              # take a backup
#   couchdb-backup.sh --verify     # restore the newest archive into a scratch container, compare doc counts
#
# Environment (systemd EnvironmentFile, KEY=value):
#   COUCHDB_URL   http://127.0.0.1:5984         DEST  /root/couchdb-backups   KEEP  14
#   COUCHDB_USER, COUCHDB_PASSWORD (admin)       DBS   "universum apocrypha"
#   COUCHDB_IMAGE couchdb:3.4.2 — keep in sync with couchdb/docker-compose.yml (--verify only)
#   BORG_REPO, BORG_PASSCOMMAND, BORG_RSH, OFFHOST_PRUNE — see borg-offhost.sh; unset BORG_REPO = local only
set -euo pipefail
# Units set TMPDIR=/var/tmp; a run by hand from root's shell would otherwise
# extract gigabytes into /tmp, which on the VPS is a 1.9 GB RAM tmpfs
# (audit Y10).
export TMPDIR=${TMPDIR:-/var/tmp}

COUCHDB_URL=${COUCHDB_URL:-http://127.0.0.1:5984}
DEST=${DEST:-/root/couchdb-backups}
KEEP=${KEEP:-14}
DBS=${DBS:-"universum apocrypha"}
COUCHDB_IMAGE=${COUCHDB_IMAGE:-couchdb:3.4.2}

log() { echo "couchdb-backup: $*"; }
die() { echo "couchdb-backup: $*" >&2; exit 1; }

# urlenc <string> — percent-encode for embedding the admin password in a
# URL; a raw password containing @, :, or / would otherwise change where
# curl/couchbackup think the host part ends.
urlenc() {
    local s=$1 out= c i
    for ((i = 0; i < ${#s}; i++)); do
        c=${s:i:1}
        case "$c" in [a-zA-Z0-9.~_-]) out+=$c ;; *) out+=$(printf '%%%02X' "'$c") ;; esac
    done
    printf '%s' "$out"
}

doc_count() { # doc_count <url-with-auth> <db>
    curl -fsS "$1/$2" | grep -o '"doc_count":[0-9]*' | head -1 | cut -d: -f2
}

# ---------------------------------------------------------------------------
# --verify — restore each dump into a scratch, disposable CouchDB and
# compare document counts against the manifest recorded at backup time.
# Never touches the live instance; the scratch container is removed on
# every exit path.
# ---------------------------------------------------------------------------
VERIFY_TMP=""
VERIFY_CONTAINER=""
verify_cleanup() {
    [ -n "$VERIFY_CONTAINER" ] && docker rm -f "$VERIFY_CONTAINER" >/dev/null 2>&1
    [ -n "$VERIFY_TMP" ] && rm -rf "$VERIFY_TMP"
}

verify_archive() {
    command -v couchrestore >/dev/null 2>&1 || die "--verify: couchrestore is not installed (npm install -g @cloudant/couchbackup)"
    command -v docker >/dev/null 2>&1 || die "--verify: docker is not installed"

    local archive=${1:-}
    [ -n "$archive" ] || archive=$(readlink -f "$DEST/LATEST" 2>/dev/null) \
        || die "--verify: no archive given and $DEST/LATEST does not resolve"
    [ -f "$archive" ] || die "--verify: $archive does not exist"
    [ -f "$archive.sha256" ] || die "--verify: $archive has no .sha256 companion — not a completed backup"
    ( cd "$(dirname "$archive")" && sha256sum -c --quiet "$(basename "$archive").sha256" ) \
        || die "--verify: checksum mismatch"
    log "verify: checksum ok"

    trap verify_cleanup EXIT
    VERIFY_TMP=$(mktemp -d -t couchdb-verify-XXXXXX)
    tar xzf "$archive" -C "$VERIFY_TMP" || die "--verify: extraction failed"
    [ -f "$VERIFY_TMP/manifest" ] || die "--verify: no manifest inside the archive"

    VERIFY_CONTAINER="couchdb-verify-$$"
    docker run -d --rm --name "$VERIFY_CONTAINER" \
        -e COUCHDB_USER=verify -e COUCHDB_PASSWORD=verify \
        -p 127.0.0.1:15984:5984 "$COUCHDB_IMAGE" >/dev/null \
        || die "--verify: could not start a scratch CouchDB ($COUCHDB_IMAGE)"

    local tries=0
    until curl -fsS -o /dev/null http://verify:verify@127.0.0.1:15984/; do
        tries=$((tries + 1))
        [ "$tries" -lt 30 ] || die "--verify: scratch CouchDB never became ready"
        sleep 1
    done

    while read -r db want; do
        [ -f "$VERIFY_TMP/$db.jsonl" ] || die "--verify: manifest lists $db but $db.jsonl is missing from the archive"
        curl -fsS -X PUT "http://verify:verify@127.0.0.1:15984/$db" >/dev/null \
            || die "--verify: could not create scratch database $db"
        couchrestore --url http://verify:verify@127.0.0.1:15984 --db "$db" < "$VERIFY_TMP/$db.jsonl" >/dev/null \
            || die "--verify: couchrestore failed for $db"
        local got
        got=$(doc_count "http://verify:verify@127.0.0.1:15984" "$db")
        [ "$got" = "$want" ] || die "--verify: $db restored $got documents, manifest says $want"
        log "verify: $db restores clean ($got documents)"
    done < "$VERIFY_TMP/manifest"

    log "verify: OK — $archive restores"
}

case "${1:-}" in
    --verify)  verify_archive "${2:-}"; exit 0 ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    "")        ;;
    *)         die "unknown argument: $1 (try --help)" ;;
esac

# Only the backup path (not --verify, which uses a scratch container's own
# throwaway credentials) needs the admin account and couchbackup itself.
[ -n "${COUCHDB_USER:-}" ] && [ -n "${COUCHDB_PASSWORD:-}" ] || die "COUCHDB_USER/COUCHDB_PASSWORD are unset"
command -v couchbackup >/dev/null 2>&1 || die "couchbackup is not installed (npm install -g @cloudant/couchbackup)"
AUTH_URL="${COUCHDB_URL/:\/\//:\/\/$COUCHDB_USER:$(urlenc "$COUCHDB_PASSWORD")@}"

mkdir -p "$DEST"
TS=$(date -u +%Y%m%dT%H%M%SZ)
STAGE=$(mktemp -d -t couchdb-backup-XXXXXX)
TMP_ARCHIVE="$DEST/.couchdb-$TS.tar.gz.partial"
TMP_SUM="$DEST/.couchdb-$TS.tar.gz.sha256.partial"
ARCHIVE="$DEST/couchdb-$TS.tar.gz"
cleanup() { rm -rf "$STAGE" "$TMP_ARCHIVE" "$TMP_SUM"; }
trap cleanup EXIT

log "starting $TS"

: > "$STAGE/manifest"
for db in $DBS; do
    before=$(doc_count "$AUTH_URL" "$db") || die "$db: could not reach CouchDB to count documents"
    log "$db: dumping ($before documents live)"
    COUCH_URL="$AUTH_URL" couchbackup --db "$db" > "$STAGE/$db.jsonl" \
        || die "$db: couchbackup failed"
    printf '%s\t%s\n' "$db" "$before" >> "$STAGE/manifest"
done

# gzip --rsyncable resets its compressor at content-defined boundaries, so a
# night that changes little produces a tarball whose bytes mostly match the
# last one, and borg stores only the difference (audit Y19: 162.7 MB of new
# data on a 167 MB test tree became 12.5 MB). Same .tar.gz, same checksum.
tar -I 'gzip --rsyncable' -cf "$TMP_ARCHIVE" -C "$STAGE" . || die "tar failed"

# The checksum names the final archive, not the temporary, so `sha256sum -c`
# works unchanged in $DEST after the renames below.
( cd "$DEST" && sha256sum "$(basename "$TMP_ARCHIVE")" \
    | sed "s|$(basename "$TMP_ARCHIVE")|$(basename "$ARCHIVE")|" > "$(basename "$TMP_SUM")" )

# Two renames, checksum first — see forgejo-backup.sh for why.
mv "$TMP_SUM" "$ARCHIVE.sha256"
mv "$TMP_ARCHIVE" "$ARCHIVE"
ln -sfn "$ARCHIVE" "$DEST/LATEST"
date -u +%Y-%m-%dT%H:%M:%SZ > "$DEST/last-success"
log "wrote $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1)) + .sha256"

if [ -n "${BORG_REPO:-}" ]; then
    . /usr/local/lib/borg-offhost.sh || die "off-host: /usr/local/lib/borg-offhost.sh is missing"
    borg_offhost_copy couchdb "$ARCHIVE" "$ARCHIVE.sha256"
else
    log "off-host: BORG_REPO is unset — this backup exists ONLY on the host it backs up."
fi

# local retention: completed pairs only, newest first by name
mapfile -t complete < <(find "$DEST" -maxdepth 1 -name 'couchdb-*.tar.gz' -type f | sort -r | while read -r f; do [ -f "$f.sha256" ] && echo "$f"; done)
for ((i = KEEP; i < ${#complete[@]}; i++)); do
    log "retention: pruning $(basename "${complete[$i]}")"
    rm -f "${complete[$i]}" "${complete[$i]}.sha256"
done
log "done"
