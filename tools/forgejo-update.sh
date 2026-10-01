#!/bin/bash
# forgejo-update.sh — see systemd/forgejo-update.service.
#
# Follows the floating LTS tag in docker-compose.yml. When the pulled image
# differs from the running one: refuse anything off the 15.0 line, back up,
# recreate, wait for the new version, check the database. If the new version
# does not come up and it ran no migrations, put the previous image back and
# hold the failed one; if it ran migrations, stop and leave it to the
# operator, because an older Forgejo cannot open a migrated database
# (forgejo/UPGRADE.md § 5.1, with the archive this run logged).
set -euo pipefail

DIR=${DIR:-/root/forgejo-server}
IMAGE=${IMAGE:-codeberg.org/forgejo/forgejo:15}
LINE=${LINE:-15.0.}                     # only patches on this line are applied
CONTAINER=${CONTAINER:-forgejo}
API=${API:-http://127.0.0.1:3000}
BACKUP=${BACKUP:-systemctl start forgejo-backup.service}
PULL=${PULL:-1}
WAIT=${WAIT:-300}
HOLD=${HOLD:-/var/lib/forgejo-update/hold}
PRUNE=${PRUNE:-1}                       # drop the now-dangling previous image after a success
log() { echo "forgejo-update: $*"; }

version() { curl -s --max-time 5 "$API/api/v1/version" | sed -n 's/.*"version":"\([^"+]*\).*/\1/p' || true; }
image_version() {
    docker run --rm --entrypoint /app/gitea/gitea "$1" --version 2>/dev/null \
        | sed -n 's/^forgejo version \([^+ ]*\).*/\1/p' || true
}
wait_for() {   # wait_for <version> — the API answers with it, and the container is not restarting
    local _
    for _ in $(seq "$WAIT"); do
        [ "$(version)" = "$1" ] && return 0
        sleep 1
    done
    return 1
}

cd "$DIR"
grep -q "image: $IMAGE\$" docker-compose.yml || { log "docker-compose.yml does not use $IMAGE; refusing"; exit 1; }

running=$(docker inspect -f '{{.Image}}' "$CONTAINER")
before=$(version)
[ "$PULL" = 1 ] && docker pull -q "$IMAGE" >/dev/null
pulled=$(docker image inspect -f '{{.Id}}' "$IMAGE")

if [ "$pulled" = "$running" ]; then
    log "forgejo ${before:-?} — unchanged"
    exit 0
fi
if [ -f "$HOLD" ] && [ "$(cat "$HOLD")" = "$pulled" ]; then
    log "the pulled image failed before and is on hold; not applying it (remove $HOLD to retry)"
    exit 1
fi
new=$(image_version "$pulled")
case "$new" in
    "$LINE"*) ;;
    *) log "pulled image reports '${new:-nothing}', not a $LINE* patch; refusing (a new major is a manual upgrade)"; exit 1 ;;
esac

log "forgejo ${before:-?} -> $new: backing up first"
$BACKUP || { log "backup failed; not updating"; exit 1; }
log "pre-update archive: $(readlink -f /root/forgejo-backups/LATEST 2>/dev/null || echo unknown)"

docker exec -u git "$CONTAINER" gitea manager flush-queues --timeout 60s >/dev/null 2>&1 \
    || log "flush-queues did not complete; continuing"
since=$(date -u +%Y-%m-%dT%H:%M:%SZ)
docker compose up -d 2>&1 | tail -1 || log "compose up reported an error; waiting anyway"

if wait_for "$new"; then
    integrity=$(docker exec -u git "$CONTAINER" sqlite3 -cmd '.timeout 15000' /data/gitea/gitea.db 'PRAGMA integrity_check;' 2>&1 | head -1)
    migrations=$(docker logs --since "$since" "$CONTAINER" 2>&1 | grep -c 'Migration\[' || true)
    if [ "$integrity" = ok ]; then
        rm -f "$HOLD"
        [ "$PRUNE" = 1 ] && { docker image prune -f >/dev/null 2>&1 || true; }
        log "forgejo running at $new (migrations: $migrations, integrity ok)"
        exit 0
    fi
    log "forgejo $new is up but integrity_check says: $integrity; leaving it for the operator"
    exit 1
fi

# The new version did not come up.
migrations=$(docker logs --since "$since" "$CONTAINER" 2>&1 | grep -c 'Migration\[' || true)
docker logs --since "$since" "$CONTAINER" 2>&1 | grep -E '\[F\]|\[E\]' | tail -5 | sed 's/^/forgejo-update:   /' || true
if [ "$migrations" != 0 ]; then
    log "forgejo $new did not come up after $migrations migration(s); NOT rolling back the image."
    log "restore the pre-update archive above by UPGRADE.md § 5.1."
    exit 1
fi
log "forgejo $new did not come up and ran no migrations; putting ${before:-the previous image} back"
mkdir -p "$(dirname "$HOLD")"; echo "$pulled" > "$HOLD"
docker tag "$running" "$IMAGE"
docker compose up -d 2>&1 | tail -1 || true
if [ -n "$before" ] && wait_for "$before"; then
    log "rolled back to $before; $new is on hold"
else
    log "rollback did not come up either; operator needed"
fi
exit 1
