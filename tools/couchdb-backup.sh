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
# Besides one <db>.jsonl per database, an archive holds what a document dump
# leaves out and a restore needs (audit Y12): security/<db>.json (who may use
# the database), users.json (the scoped org.couchdb.user:* accounts LiveSync
# logs in with, password hashes included), node-config.json (the server's
# effective configuration: its uuid, the cookie-auth secret, the admin hash —
# a recreated container would otherwise generate new ones) and server.json.
# couchdb/RESTORE.md is the procedure.
#
# The admin credentials reach curl on stdin (-K -) and couchbackup through
# its environment, never through an argv any local user can read in /proc
# (audit Y11).
#
#   couchdb-backup.sh                          # take a backup
#   couchdb-backup.sh --verify [archive]       # restore into a scratch container and compare
#   couchdb-backup.sh --restore [archive]      # restore into COUCHDB_URL (couchdb/RESTORE.md)
#   couchdb-backup.sh --instance-ini [archive] # print the server's uuid + secret as local.d ini
#
# Environment (systemd EnvironmentFile, KEY=value):
#   COUCHDB_URL   http://127.0.0.1:5984         DEST  /root/couchdb-backups   KEEP  14
#   COUCHDB_USER, COUCHDB_PASSWORD (admin)       DBS   "universum apocrypha"
#   COUCHDB_IMAGE (--verify only) the image the live `couchdb` container runs, by default
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
COUCHDB_IMAGE=${COUCHDB_IMAGE:-}

log() { echo "couchdb-backup: $*"; }
die() { echo "couchdb-backup: $*" >&2; exit 1; }

# urlenc <string> — percent-encode for the credentials in COUCH_URL, which
# couchbackup reads from its environment; a raw password containing @, :, or
# / would otherwise change where it thinks the host part ends.
urlenc() {
    local s=$1 out='' c i
    for ((i = 0; i < ${#s}; i++)); do
        c=${s:i:1}
        case "$c" in [a-zA-Z0-9.~_-]) out+=$c ;; *) out+=$(printf '%%%02X' "'$c") ;; esac
    done
    printf '%s' "$out"
}

# curlcfg <user> <password> — a curl config line carrying the credentials,
# for `curl -K -` on stdin: the password never appears in an argv.
curlcfg() {
    local u=$1 p=$2
    u=${u//\\/\\\\}; u=${u//\"/\\\"}
    p=${p//\\/\\\\}; p=${p//\"/\\\"}
    printf 'user = "%s:%s"\n' "$u" "$p"
}

# req <base-url> <user> <password> <method> <path> [curl args…]
req() {
    local base=$1 u=$2 p=$3 method=$4 path=$5; shift 5
    curlcfg "$u" "$p" | curl -fsS -K - -X "$method" "$@" "$base$path"
}
live() { req "$COUCHDB_URL" "$COUCHDB_USER" "$COUCHDB_PASSWORD" "$@"; }

doc_count() { # the doc_count in a database's info JSON on stdin
    grep -o '"doc_count":[0-9]*' | head -1 | cut -d: -f2
}

# json_same <a.json> <b.json> [field…] — equal as JSON, or on the listed
# top-level fields only. python3 is on the box already (the Anki server).
json_same() {
    python3 - "$@" <<'PY'
import json, sys
a, b = (json.load(open(f)) for f in sys.argv[1:3])
fields = sys.argv[3:]
if fields:
    a = {k: a.get(k) for k in fields}; b = {k: b.get(k) for k in fields}
sys.exit(0 if a == b else 1)
PY
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

# open_archive [archive] — check and unpack an archive (LATEST by default)
# into $VERIFY_TMP; sets ARCHIVE_PATH.
open_archive() {
    local archive=${1:-}
    [ -n "$archive" ] || archive=$(readlink -f "$DEST/LATEST" 2>/dev/null) \
        || die "no archive given and $DEST/LATEST does not resolve"
    [ -f "$archive" ] || die "$archive does not exist"
    [ -f "$archive.sha256" ] || die "$archive has no .sha256 companion — not a completed backup"
    ( cd "$(dirname "$archive")" && sha256sum -c --quiet "$(basename "$archive").sha256" ) \
        || die "checksum mismatch: $archive"
    log "checksum ok: $archive"
    trap verify_cleanup EXIT
    VERIFY_TMP=$(mktemp -d -t couchdb-verify-XXXXXX)
    tar xzf "$archive" -C "$VERIFY_TMP" || die "extraction failed"
    [ -f "$VERIFY_TMP/manifest" ] || die "no manifest inside the archive"
    ARCHIVE_PATH=$archive
}

# restore_into <url> <admin-user> <admin-password> — load the unpacked
# archive in $VERIFY_TMP into a CouchDB: the accounts, then each database
# with its documents and _security, checking that each reads back as
# archived. The --verify run and a real restore (couchdb/RESTORE.md) take
# exactly this path.
restore_into() {
    local url=$1 au=$2 ap=$3 db want got n=0 id
    command -v couchrestore >/dev/null 2>&1 || die "couchrestore is not installed (npm install -g @cloudant/couchbackup)"
    to() { req "$url" "$au" "$ap" "$@"; }
    to PUT /_users -o /dev/null 2>/dev/null || true   # single node: not created until setup

    if [ -f "$VERIFY_TMP/users.list" ]; then
        # Admin PUTs keep the stored hash (derived_key, salt, iterations) as
        # it is, so each account comes back able to log in with its password.
        while IFS= read -r id; do
            python3 - "$VERIFY_TMP/users/$id.json" "$(to GET "/_users/$id" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("_rev",""))' 2>/dev/null)" \
                > "$VERIFY_TMP/user-put.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d.pop("_rev", None)
if sys.argv[2]: d["_rev"] = sys.argv[2]           # an existing account is replaced
json.dump(d, sys.stdout)
PY
            to PUT "/_users/$id" -H 'Content-Type: application/json' \
                --data-binary "@$VERIFY_TMP/user-put.json" -o /dev/null || die "could not restore user $id"
            to GET "/_users/$id" > "$VERIFY_TMP/user-back.json"
            json_same "$VERIFY_TMP/users/$id.json" "$VERIFY_TMP/user-back.json" \
                name roles type password_scheme derived_key salt iterations pbkdf2_prf \
                || die "user $id does not read back as archived"
            n=$((n + 1))
        done < "$VERIFY_TMP/users.list"
        log "$n user account(s) restored with their password hashes"
    else
        log "archive predates users.json — accounts not restored"
    fi

    while read -r db want; do
        [ -f "$VERIFY_TMP/$db.jsonl" ] || die "manifest lists $db but $db.jsonl is missing from the archive"
        to PUT "/$db" -o /dev/null || die "could not create database $db"
        COUCH_URL="${url/:\/\//:\/\/$(urlenc "$au"):$(urlenc "$ap")@}" \
            couchrestore --db "$db" < "$VERIFY_TMP/$db.jsonl" >/dev/null \
            || die "couchrestore failed for $db"
        got=$(to GET "/$db" | doc_count)
        [ "$got" = "$want" ] || die "$db restored $got documents, manifest says $want"
        if [ -f "$VERIFY_TMP/security/$db.json" ]; then
            to PUT "/$db/_security" -H 'Content-Type: application/json' \
                --data-binary "@$VERIFY_TMP/security/$db.json" -o /dev/null \
                || die "$db: could not restore _security"
            to GET "/$db/_security" > "$VERIFY_TMP/security-back.json"
            json_same "$VERIFY_TMP/security/$db.json" "$VERIFY_TMP/security-back.json" \
                || die "$db: _security does not read back as archived"
            log "$db: $got documents and _security restored"
        else
            log "$db: $got documents restored (archive predates _security)"
        fi
    done < "$VERIFY_TMP/manifest"
}

verify_archive() {
    command -v docker >/dev/null 2>&1 || die "--verify: docker is not installed"
    [ -n "$COUCHDB_IMAGE" ] || COUCHDB_IMAGE=$(docker inspect -f '{{.Image}}' couchdb 2>/dev/null) \
        || die "--verify: no COUCHDB_IMAGE given and no running couchdb container to take it from"
    open_archive "${1:-}"

    # A password for this run only: the scratch copy holds the vaults, and a
    # fixed one in this repository would open them to any local process for
    # as long as the test runs (audit Y11).
    local vpass port=${VERIFY_PORT:-15984} tries=0
    vpass=$(head -c 18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')
    VERIFY_CONTAINER="couchdb-verify-$$"
    COUCHDB_USER=verify COUCHDB_PASSWORD="$vpass" docker run -d --rm --name "$VERIFY_CONTAINER" \
        -e COUCHDB_USER -e COUCHDB_PASSWORD \
        -p "127.0.0.1:$port:5984" "$COUCHDB_IMAGE" >/dev/null \
        || die "--verify: could not start a scratch CouchDB ($COUCHDB_IMAGE)"
    until req "http://127.0.0.1:$port" verify "$vpass" GET / -o /dev/null 2>/dev/null; do
        tries=$((tries + 1))
        [ "$tries" -lt 60 ] || die "--verify: scratch CouchDB never became ready"
        sleep 1
    done
    restore_into "http://127.0.0.1:$port" verify "$vpass"
    log "verify: OK — $ARCHIVE_PATH restores"
}

# restore_archive [archive] — load an archive into the CouchDB at
# COUCHDB_URL (couchdb/RESTORE.md). Refuses a target whose databases already
# hold documents unless RESTORE_OVER=1: a restore is for an empty server.
restore_archive() {
    [ -n "${COUCHDB_USER:-}" ] && [ -n "${COUCHDB_PASSWORD:-}" ] || die "COUCHDB_USER/COUCHDB_PASSWORD are unset"
    open_archive "${1:-}"
    local db want n
    while read -r db want; do
        n=$(live GET "/$db" 2>/dev/null | doc_count || true)
        if [ -n "$n" ] && [ "$n" != 0 ] && [ "${RESTORE_OVER:-0}" != 1 ]; then
            die "$db already holds $n documents at $COUCHDB_URL — refusing (RESTORE_OVER=1 to restore over it)"
        fi
    done < "$VERIFY_TMP/manifest"
    restore_into "$COUCHDB_URL" "$COUCHDB_USER" "$COUCHDB_PASSWORD"
    log "restore: OK — $ARCHIVE_PATH is in $COUCHDB_URL"
}

# instance_ini [archive] — the server's identity as an ini file for
# local.d/20-instance.ini: its uuid and the cookie-auth secret. The image's
# entrypoint keeps a secret it finds there and CouchDB keeps a configured
# uuid, so a recreated container (an image update) stays the same server.
# From the live server, or from an archive's server.json/node-config.json.
instance_ini() {
    local uuid secret
    if [ -n "${1:-}" ]; then
        open_archive "$1" >&2
        uuid=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["uuid"])' "$VERIFY_TMP/server.json")
        secret=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["chttpd_auth"]["secret"])' "$VERIFY_TMP/node-config.json")
    else
        [ -n "${COUCHDB_USER:-}" ] && [ -n "${COUCHDB_PASSWORD:-}" ] || die "COUCHDB_USER/COUCHDB_PASSWORD are unset"
        uuid=$(live GET / | python3 -c 'import json,sys; print(json.load(sys.stdin)["uuid"])')
        secret=$(live GET /_node/_local/_config/chttpd_auth/secret | python3 -c 'import json,sys; print(json.load(sys.stdin))')
    fi
    [ -n "$uuid" ] && [ -n "$secret" ] || die "could not read the server's uuid and secret"
    printf '; This server'"'"'s identity, kept across container updates (couchdb/RESTORE.md).\n'
    printf '[couchdb]\nuuid = %s\n\n[chttpd_auth]\nsecret = %s\n' "$uuid" "$secret"
}

case "${1:-}" in
    --verify)       verify_archive "${2:-}"; exit 0 ;;
    --restore)      restore_archive "${2:-}"; exit 0 ;;
    --instance-ini) instance_ini "${2:-}"; exit 0 ;;
    -h|--help) sed -n '2,/^set -euo pipefail/p' "$0" | sed '$d'; exit 0 ;;
    "")        ;;
    *)         die "unknown argument: $1 (try --help)" ;;
esac

# Only the backup path (not --verify, which uses a scratch container's own
# throwaway credentials) needs the admin account and couchbackup itself.
[ -n "${COUCHDB_USER:-}" ] && [ -n "${COUCHDB_PASSWORD:-}" ] || die "COUCHDB_USER/COUCHDB_PASSWORD are unset"
command -v couchbackup >/dev/null 2>&1 || die "couchbackup is not installed (npm install -g @cloudant/couchbackup)"
# couchbackup takes its URL from the environment (COUCH_URL), not argv.
AUTH_URL="${COUCHDB_URL/:\/\//:\/\/$(urlenc "$COUCHDB_USER"):$(urlenc "$COUCHDB_PASSWORD")@}"

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
mkdir -p "$STAGE/security" "$STAGE/users"
for db in $DBS; do
    before=$(live GET "/$db" | doc_count) || die "$db: could not reach CouchDB to count documents"
    log "$db: dumping ($before documents live)"
    COUCH_URL="$AUTH_URL" couchbackup --db "$db" > "$STAGE/$db.jsonl" \
        || die "$db: couchbackup failed"
    live GET "/$db/_security" > "$STAGE/security/$db.json" || die "$db: could not read _security"
    printf '%s\t%s\n' "$db" "$before" >> "$STAGE/manifest"
done

# The accounts LiveSync logs in with (org.couchdb.user:*), one file each,
# hashes included; couchbackup does not dump _users.
live GET '/_users/_all_docs?include_docs=true&startkey=%22org.couchdb.user%3A%22&endkey=%22org.couchdb.user%3B%22' \
    > "$STAGE/users.json" || die "could not read _users"
python3 - "$STAGE" <<'PY' || die "could not split users.json"
import json, sys, urllib.parse
stage = sys.argv[1]
rows = json.load(open(f"{stage}/users.json"))["rows"]
with open(f"{stage}/users.list", "w") as ids:
    for r in rows:
        doc_id = urllib.parse.quote(r["id"], safe="")
        json.dump(r["doc"], open(f"{stage}/users/{doc_id}.json", "w"))
        ids.write(doc_id + "\n")
PY
live GET /_node/_local/_config > "$STAGE/node-config.json" || die "could not read the node configuration"
live GET / > "$STAGE/server.json" || die "could not read the server's identity"
log "accounts: $(wc -l < "$STAGE/users.list"), _security for each database, node configuration"

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
