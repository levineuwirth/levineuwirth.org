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
# Any failure after the stop puts the copied data directory and the
# previous image back and holds the failed image; if that does not come
# back either, $ATTENTION is left and every run fails until the operator
# has restored by couchdb/RESTORE.md and removed it. The cold copy is what
# makes going back safe whatever the new version did to its files. As in
# forgejo-update.sh, a declined image never keeps the local tag.
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
KEEP_COPIES=${KEEP_COPIES:-2}
STATE=${STATE:-/var/lib/couchdb-update}
HOLD=${HOLD:-$STATE/hold}
ATTENTION=${ATTENTION:-$STATE/needs-operator}
log() { echo "couchdb-update: $*"; }

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
    local db out=""
    for db in $DBS; do out+="$db=$(get "/$db" | field doc_count) "; done
    printf '%s' "${out% }"
}
image_version() { docker image inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$1" | sed -n 's/^COUCHDB_VERSION=//p'; }
up_at() {    # up_at <image version>: answers /_up, at that version (the image's
    local _ v   # COUCHDB_VERSION may add a packaging revision: 3.5.2.1 serves 3.5.2)
    for _ in $(seq "$WAIT"); do
        if get /_up >/dev/null 2>&1; then
            v=$(get / | field version)
            case "$1" in "$v"|"$v".*) return 0 ;; esac
        fi
        sleep 1
    done
    return 1
}
ini_value() { sed -n "/^\[$1\]/,/^\[/{s/^$2[[:space:]]*=[[:space:]]*//p}" "$3" | head -1; }

hold() { mkdir -p "$STATE"; echo "$pulled" > "$HOLD"; }
decline() { docker tag "$running" "$IMAGE" 2>/dev/null || true; log "$1"; exit 1; }

if [ -f "$ATTENTION" ]; then
    log "a previous update needs the operator: $(cat "$ATTENTION")"
    log "restore by couchdb/RESTORE.md, then remove $ATTENTION"
    exit 1
fi

cd "$DIR"
grep -q "image: $IMAGE\$" docker-compose.yml || { log "docker-compose.yml does not use $IMAGE; refusing"; exit 1; }

running=$(docker inspect -f '{{.Image}}' "$CONTAINER")
before=$(image_version "$running")
[ "$PULL" = 1 ] && docker pull -q "$IMAGE" >/dev/null
pulled=$(docker image inspect -f '{{.Id}}' "$IMAGE")

if [ "$pulled" = "$running" ]; then
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
origins_want=$(ini_value cors origins "$DIR/local.ini")

log "couchdb ${before:-?} -> $new: backing up first"
$BACKUP || decline "backup failed; not updating"
counts_before=$(counts) || decline "could not count documents; not updating"
log "documents: $counts_before; images: running $running, applying $pulled"

ts=$(date -u +%Y%m%dT%H%M%SZ)
copy="$DIR/couchdb-data.pre-$ts"
docker compose stop >/dev/null 2>&1 || decline "could not stop CouchDB; not updating"
if ! cp -a "$DIR/couchdb-data" "$copy"; then
    rm -rf "$copy"; docker compose start >/dev/null 2>&1 || true
    decline "could not copy the data directory; not updating"
fi
log "stopped; data directory copied to $copy"

docker tag "$pulled" "$IMAGE"
docker compose up -d >/dev/null 2>&1 || log "compose up reported an error; checking anyway"

why=""
if ! up_at "$new"; then
    why="did not come up at $new"
elif [ "$(counts)" != "$counts_before" ]; then
    why="document counts changed: $counts_before -> $(counts)"
elif [ -n "$uuid_want" ] && [ "$(get / | field uuid)" != "$uuid_want" ]; then
    why="uuid is not the one in instance.ini"
elif [ -n "$origins_want" ] && [ "$(get /_node/_local/_config/cors/origins | field)" != "$origins_want" ]; then
    why="effective CORS origins are not local.ini's"
fi

if [ -z "$why" ]; then
    rm -f "$HOLD"
    # keep the newest KEEP_COPIES data copies
    find "$DIR" -maxdepth 1 -name 'couchdb-data.pre-*' -type d | sort -r | tail -n +$((KEEP_COPIES + 1)) \
        | while read -r d; do rm -rf "$d"; done
    docker image prune -f >/dev/null 2>&1 || true
    log "couchdb running at $new ($counts_before, uuid and CORS as configured)"
    exit 0
fi

log "couchdb $new $why; putting $before and its data back"
hold
docker compose stop >/dev/null 2>&1 || true
mv "$DIR/couchdb-data" "$DIR/couchdb-data.failed-$ts"
cp -a "$copy" "$DIR/couchdb-data"
docker tag "$running" "$IMAGE"
docker compose up -d >/dev/null 2>&1 || true
if up_at "$before" && [ "$(counts)" = "$counts_before" ]; then
    log "rolled back to $before with its data; $new is on hold (the failed data directory is $DIR/couchdb-data.failed-$ts)"
else
    mkdir -p "$STATE"
    printf '%s rollback from %s did not come back (image %s, data copy %s)\n' "$(date -u +%FT%TZ)" "$new" "$running" "$copy" > "$ATTENTION"
    log "rollback did not come back either; operator needed (couchdb/RESTORE.md)"
fi
exit 1
