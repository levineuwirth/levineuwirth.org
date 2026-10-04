#!/bin/bash
# couchdb-update.sh — see systemd/couchdb-update.service.
#
# Follows the floating `couchdb:3` tag in docker-compose.yml (audit Y05:
# the one Internet-reachable service with neither unattended patching nor
# an upgrade path). When the pulled image differs from the running one:
# refuse anything off the 3.x line, refuse without instance.ini (a recreated
# container would otherwise come up as a different server; RESTORE.md),
# take the nightly backup, note each database's document count, stop
# CouchDB and copy its data directory, then recreate on the new image and
# check the version, the counts, the uuid and the effective CORS origins.
#
# A candidate must also stay up for $STABLE seconds without a restart, and
# a run with nothing to apply still fails when the server is not healthy.
# A failed candidate check puts the copied data directory and previous
# image back and holds the failed image. Interruption or failed recovery
# leaves $ATTENTION and every run fails until the operator
# has restored by couchdb/RESTORE.md and removed it. The cold copy is what
# makes going back safe whatever the new version did to its files. As in
# forgejo-update.sh, a declined image never keeps the local tag. The sync
# proxy must support $MAINTENANCE before the updater can stop the server.
set -euo pipefail
export TMPDIR=${TMPDIR:-/var/tmp}

DIR=${DIR:-/root/couchdb-server}
IMAGE=${IMAGE:-couchdb:3}
LINE=${LINE:-3.}                         # only this major is applied unattended
CONTAINER=${CONTAINER:-couchdb}
URL=${URL:-http://127.0.0.1:5984}
DBS=${DBS:-"universum apocrypha"}
BACKUP=${BACKUP:-systemctl start couchdb-backup.service}
PULL=${PULL:-1}
WAIT=${WAIT:-120}
STABLE=${STABLE:-120}                    # seconds CouchDB must stay up once it answers
CHECK_EVERY=${CHECK_EVERY:-5}
KEEP_COPIES=${KEEP_COPIES:-2}
STATE=${STATE:-/var/lib/couchdb-update}
HOLD=${HOLD:-$STATE/hold}
ATTENTION=${ATTENTION:-$STATE/needs-operator}
MAINTENANCE=${MAINTENANCE:-$STATE/maintenance}
PUBLIC_URL=${PUBLIC_URL:-https://sync.levineuwirth.org/}
log() { echo "couchdb-update: $*"; }

# Serialise hand runs and the timer too. The directory must be traversable
# by nginx, which checks only the non-secret maintenance marker.
mkdir -p "$STATE"
exec 9>"$STATE/lock"
flock -n 9 || { log "another update is running"; exit 1; }

# Admin credentials from the compose directory's server.env, handed to curl
# on stdin (-K -), never in its argv.
admin_cfg() {
    local u p
    u=$(sed -n 's/^COUCHDB_USER=//p' "$DIR/server.env")
    p=$(sed -n 's/^COUCHDB_PASSWORD=//p' "$DIR/server.env")
    u=${u//\\/\\\\}; u=${u//\"/\\\"}; p=${p//\\/\\\\}; p=${p//\"/\\\"}
    printf 'user = "%s:%s"\n' "$u" "$p"
}
get() { admin_cfg | curl -fsS -K - --max-time 5 "$URL$1"; }
field() { python3 -c 'import json,sys; v=json.load(sys.stdin); print(v[sys.argv[1]] if sys.argv[1] else v)' "${1:-}"; }
counts() {   # "db=count …" for every database in DBS
    local db count out=""
    for db in $DBS; do
        count=$(get "/$db" | field doc_count) || return 1
        [[ "$count" =~ ^[0-9]+$ ]] || return 1
        out+="$db=$count "
    done
    printf '%s' "${out% }"
}
image_version() { docker image inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$1" | sed -n 's/^COUCHDB_VERSION=//p'; }
up_at() {    # up_at <image version>: answers /_up, at that version (the image's
    local _ v   # COUCHDB_VERSION may add a packaging revision: 3.5.2.1 serves 3.5.2)
    for _ in $(seq "$WAIT"); do
        if get /_up >/dev/null 2>&1; then
            v=$(get / | field version) || { sleep 1; continue; }
            case "$1" in "$v"|"$v".*) return 0 ;; esac
        fi
        sleep 1
    done
    return 1
}
# Status, restarting, restart count and start time: a restart under
# `restart: unless-stopped` changes the count and the start time. The same
# function as in forgejo-update.sh (tests/test_couchdb_update.py compares).
container_state() {
    local state
    state=$(docker inspect -f '{{.State.Status}} {{.State.Restarting}} {{.RestartCount}} {{.State.StartedAt}}' "$CONTAINER" 2>/dev/null) || state=
    echo "${state:-missing}"
}
stays_up() {   # running, unrestarted for $STABLE s, and still answering /_up
    local first now t=0
    first=$(container_state)
    case "$first" in
        "running false "*) ;;
        *) log "container is not running steadily ($first)"; return 1 ;;
    esac
    while [ "$t" -lt "$STABLE" ]; do
        sleep "$CHECK_EVERY"
        t=$(( t + CHECK_EVERY ))
        now=$(container_state)
        if [ "$now" != "$first" ]; then
            log "container restarted or stopped within ${t}s of answering ($first -> $now)"
            return 1
        fi
    done
    get /_up >/dev/null 2>&1 || { log "CouchDB stopped answering within ${STABLE}s"; return 1; }
}
ini_value() { sed -n "/^\[$1\]/,/^\[/{s/^$2[[:space:]]*=[[:space:]]*//p}" "$3" | head -1; }

hold() { mkdir -p "$STATE"; echo "$pulled" > "$HOLD"; }
decline() { docker tag "$running" "$IMAGE" 2>/dev/null || true; log "$1"; exit 1; }

if [ -f "$ATTENTION" ]; then
    log "a previous update needs the operator: $(cat "$ATTENTION")"
    log "restore by couchdb/RESTORE.md, then remove $ATTENTION"
    exit 1
fi
[ ! -e "$MAINTENANCE" ] || { log "maintenance marker remains; operator needed"; exit 1; }

cd "$DIR"
grep -q "image: $IMAGE\$" docker-compose.yml || { log "docker-compose.yml does not use $IMAGE; refusing"; exit 1; }

running=$(docker inspect -f '{{.Image}}' "$CONTAINER")
before=$(image_version "$running")
[ "$PULL" = 1 ] && docker pull -q "$IMAGE" >/dev/null
pulled=$(docker image inspect -f '{{.Id}}' "$IMAGE")

if [ "$pulled" = "$running" ]; then
    # Nothing to apply still says whether the server is well: a crash loop
    # that starts after an update must not read as "unchanged" each day.
    get /_up >/dev/null 2>&1 || { log "nothing to apply, but CouchDB is not answering on $URL"; exit 1; }
    stays_up || { log "nothing to apply, but CouchDB did not stay healthy"; exit 1; }
    log "couchdb ${before:-?} — unchanged"
    exit 0
fi
if [ -f "$HOLD" ] && [ "$(cat "$HOLD")" = "$pulled" ]; then
    decline "the pulled image failed before and is on hold; not applying it (remove $HOLD to retry)"
fi
new=$(image_version "$pulled")
case "$new" in
    "$LINE"*) ;;
    *) decline "pulled image reports '${new:-nothing}', not a $LINE* release; refusing (a new major is a manual upgrade)" ;;
esac
[ -s "$DIR/instance.ini" ] || decline "no $DIR/instance.ini: a recreated container would be a different server (couchdb/RESTORE.md)"
uuid_want=$(ini_value couchdb uuid "$DIR/instance.ini")
secret_want=$(ini_value chttpd_auth secret "$DIR/instance.ini")
origins_want=$(ini_value cors origins "$DIR/local.ini")
[ -n "$uuid_want" ] && [ -n "$secret_want" ] && [ -n "$origins_want" ] \
    || decline "instance.ini or local.ini is incomplete; refusing"
[ "$(get / | field uuid)" = "$uuid_want" ] \
    && [ "$(get /_node/_local/_config/chttpd_auth/secret | field)" = "$secret_want" ] \
    || decline "instance.ini does not match the running identity; refusing"

healthy() {
    local got
    up_at "$1" || return 1
    got=$(counts) || return 1
    [ "$got" = "$counts_before" ] || return 1
    [ "$(get / | field uuid)" = "$uuid_want" ] || return 1
    [ "$(get /_node/_local/_config/chttpd_auth/secret | field)" = "$secret_want" ] || return 1
    [ "$(get /_node/_local/_config/cors/origins | field)" = "$origins_want" ] || return 1
    # Answering once is not enough: a release that then crash-loops would
    # otherwise pass, and its rollback copy and previous image be pruned.
    stays_up || return 1
}

log "couchdb ${before:-?} -> $new: backing up first"
$BACKUP || decline "backup failed; not updating"
ts=$(date -u +%Y%m%dT%H%M%SZ)
copy="$DIR/couchdb-data.pre-$ts"
# Persist recovery information BEFORE any stop or replacement. A timeout,
# signal or failed filesystem command must never become "unchanged" tomorrow.
printf '%s update pending; previous image %s; candidate %s; data copy %s\n' \
    "$(date -u +%FT%TZ)" "$running" "$pulled" "$copy" > "$ATTENTION"
touch "$MAINTENANCE"
# The proxy blocks new sync requests throughout validation and rollback.
# Otherwise a candidate could acknowledge writes which its rollback discards.
status=$(curl -sS --max-time 10 --output /dev/null --write-out '%{http_code}' "$PUBLIC_URL") || status=000
if [ "$status" != 503 ]; then
    rm -f "$ATTENTION" "$MAINTENANCE"
    decline "sync proxy did not return maintenance 503; install nginx/couchdb-sync.conf first"
fi
if ! counts_before=$(counts); then
    rm -f "$ATTENTION" "$MAINTENANCE"
    decline "could not count documents; not updating"
fi
log "documents: $counts_before; images: running $running, applying $pulled"
hold
docker compose stop >/dev/null 2>&1 || decline "could not stop CouchDB; operator needed"
if ! cp -a "$DIR/couchdb-data" "$copy"; then
    docker compose start >/dev/null 2>&1 || true
    if healthy "$before"; then rm -f "$ATTENTION" "$MAINTENANCE"; fi
    decline "could not copy the data directory; not updating"
fi
log "stopped; data directory copied to $copy"

docker tag "$pulled" "$IMAGE"
docker compose up -d >/dev/null 2>&1 || log "compose up reported an error; checking anyway"

if healthy "$new"; then
    # keep the newest KEEP_COPIES data copies
    find "$DIR" -maxdepth 1 -name 'couchdb-data.pre-*' -type d | sort -r | tail -n +$((KEEP_COPIES + 1)) \
        | while read -r d; do rm -rf "$d"; done
    docker image prune -f >/dev/null 2>&1 || true
    rm -f "$HOLD" "$ATTENTION" "$MAINTENANCE"
    log "couchdb running at $new ($counts_before, uuid and CORS as configured)"
    exit 0
fi

log "couchdb $new failed version, counts, identity or CORS validation; putting $before and its data back"
hold
docker compose stop >/dev/null 2>&1 || { log "could not stop candidate; operator needed"; exit 1; }
mv "$DIR/couchdb-data" "$DIR/couchdb-data.failed-$ts"
cp -a "$copy" "$DIR/couchdb-data"
docker tag "$running" "$IMAGE"
docker compose up -d >/dev/null 2>&1 || true
if healthy "$before"; then
    rm -f "$ATTENTION" "$MAINTENANCE"
    log "rolled back to $before with its data; $new is on hold (the failed data directory is $DIR/couchdb-data.failed-$ts)"
else
    mkdir -p "$STATE"
    printf '%s rollback from %s did not come back (image %s, data copy %s)\n' "$(date -u +%FT%TZ)" "$new" "$running" "$copy" > "$ATTENTION"
    log "rollback did not come back either; operator needed (couchdb/RESTORE.md)"
fi
exit 1
