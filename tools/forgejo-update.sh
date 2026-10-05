#!/bin/bash
# forgejo-update.sh — see systemd/forgejo-update.service.
#
# Follows the floating LTS tag in docker-compose.yml. When the pulled image
# differs from the running one: refuse anything off the 15.0 line, back up,
# recreate, wait for the new version, watch that it stays up, check the
# database. If the new version does not come up, or comes up and then
# restarts or stops within $STABLE seconds, and it ran no migrations, put the
# previous image back and hold the failed one; if it ran migrations, stop
# and leave it to the operator, because an older Forgejo cannot open a
# migrated database
# (forgejo/UPGRADE.md § 5.1, with the archive this run logged).
#
# Every failure holds the image it tried, so the next morning's run does
# not apply it again; a failure after migrations, or a failed integrity
# check, also leaves $ATTENTION, and every run fails until the operator has
# restored and removed it (a crash-looping container otherwise reads as
# "unchanged" the next day, and the failed unit cleared itself). Whenever a
# run declines a pulled image, the local tag is pointed back at the running
# one, so a hand-run `docker compose up -d` cannot recreate the forge on an
# image that was held or refused (audit Y04).
#
# A run that finds nothing to apply rechecks the API after pulling and
# requires the same stability window. A later crash loop caught during
# that window must not pass as "unchanged".
#
# From $EOL_WARN_DAYS before the end of the 15.0 LTS, patches still apply
# but every run fails with a reminder to plan the next LTS (audit Y09).
set -euo pipefail

DIR=${DIR:-/root/forgejo-server}
IMAGE=${IMAGE:-codeberg.org/forgejo/forgejo:15}
LINE=${LINE:-15.0.}                     # only patches on this line are applied
CONTAINER=${CONTAINER:-forgejo}
API=${API:-http://127.0.0.1:3000}
BACKUP=${BACKUP:-systemctl start forgejo-backup.service}
PULL=${PULL:-1}
WAIT=${WAIT:-300}
STABLE=${STABLE:-120}                   # seconds any accepted version must stay up after answering
CHECK_EVERY=${CHECK_EVERY:-5}
HOLD=${HOLD:-/var/lib/forgejo-update/hold}
PRUNE=${PRUNE:-1}                       # drop the now-dangling previous image after a success
ATTENTION=${ATTENTION:-/var/lib/forgejo-update/needs-operator}
EOL=${EOL:-2027-07-15}                  # end of the 15.0 LTS (forgejo.org release schedule)
EOL_WARN_DAYS=${EOL_WARN_DAYS:-90}
STACK_LOCK=${STACK_LOCK:-/run/lock/git-stack-update.lock}   # shared with anubis-update.py
STACK_WAIT=${STACK_WAIT:-1800}          # seconds to wait for it before giving up
log() { echo "forgejo-update: $*"; }

version() { curl -s --max-time 5 "$API/api/v1/version" | sed -n 's/.*"version":"\([^"+]*\).*/\1/p' || true; }
image_version() {
    docker run --rm --entrypoint /app/gitea/gitea "$1" --version 2>/dev/null \
        | sed -n 's/^forgejo version \([^+ ]*\).*/\1/p' || true
}
wait_for() {   # wait_for <version> — poll the API ($WAIT tries, a second apart) until it reports it
    local _
    for _ in $(seq "$WAIT"); do
        [ "$(version)" = "$1" ] && return 0
        sleep 1
    done
    return 1
}
# Status, restarting, restart count and start time: a restart under
# `restart: unless-stopped` changes the count and the start time.
container_state() {
    local state
    state=$(docker inspect -f '{{.State.Status}} {{.State.Restarting}} {{.RestartCount}} {{.State.StartedAt}}' "$CONTAINER" 2>/dev/null) || state=
    echo "${state:-missing}"
}
stays_up() {   # stays_up <version> — running, unrestarted for $STABLE s, and still answering <version>
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
    [ "$(version)" = "$1" ] || { log "the API stopped answering $1 within ${STABLE}s"; return 1; }
}

hold() { mkdir -p "$(dirname "$HOLD")"; echo "$pulled" > "$HOLD"; }
needs_operator() {   # needs_operator <why>
    mkdir -p "$(dirname "$ATTENTION")"
    printf '%s %s (image %s, previous image %s, pre-update archive %s)\n' "$(date -u +%FT%TZ)" "$1" "$pulled" "$running" "$archive" > "$ATTENTION"
}
decline() {   # decline <message>: leave the running image named by the local tag, and fail
    docker tag "$running" "$IMAGE" 2>/dev/null || true
    log "$1"
    exit 1
}
done_ok() {   # done_ok <message>
    log "$1"
    if [ "$(date -u +%s)" -ge $(( $(date -u -d "$EOL" +%s) - EOL_WARN_DAYS * 86400 )) ]; then
        log "the $LINE* LTS line ends $EOL: plan the next LTS (forgejo/UPGRADE.md); failing as a reminder"
        exit 1
    fi
    exit 0
}

# Serialise hand runs and the timer, as couchdb-update.sh and
# anubis-update.py do: two runs could both recreate or roll back the forge.
mkdir -p "$(dirname "$HOLD")"
exec 9>"$(dirname "$HOLD")/lock"
flock -n 9 || { log "another update is running"; exit 1; }

# And one update of the git stack at a time, waiting for the other rather
# than failing: anubis-update.py probes the forge through Anubis (Git
# discovery, feeds, the API, crawler pages), so a forge being backed up
# and recreated fails those probes and rolls back, and holds, a good
# Anubis image. A slow run here (up to its hour) reaches 06:00.
mkdir -p "$(dirname "$STACK_LOCK")"
exec 7>"$STACK_LOCK"
if ! flock -n 7; then
    log "waiting for another update of the git stack (anubis-update) to finish"
    flock -w "$STACK_WAIT" 7 || { log "the git stack was still being updated after ${STACK_WAIT}s; not starting"; exit 1; }
fi

if [ -f "$ATTENTION" ]; then
    log "a previous update needs the operator: $(cat "$ATTENTION")"
    log "restore by forgejo/UPGRADE.md § 5.1, then remove $ATTENTION"
    exit 1
fi

cd "$DIR"
grep -q "image: $IMAGE\$" docker-compose.yml || { log "docker-compose.yml does not use $IMAGE; refusing"; exit 1; }

running=$(docker inspect -f '{{.Image}}' "$CONTAINER")
before=$(version)
archive=none
[ "$PULL" = 1 ] && docker pull -q "$IMAGE" >/dev/null
pulled=$(docker image inspect -f '{{.Id}}' "$IMAGE")

if [ "$pulled" = "$running" ]; then
    # Pulling can take long enough for the earlier API reply to go stale.
    current=$(version)
    [ -n "$current" ] || { log "nothing to apply, but forgejo is not answering on $API"; exit 1; }
    stays_up "$current" || { log "nothing to apply, but forgejo did not stay healthy"; exit 1; }
    done_ok "forgejo $current — unchanged"
fi
if [ -f "$HOLD" ] && [ "$(cat "$HOLD")" = "$pulled" ]; then
    decline "the pulled image failed before and is on hold; not applying it (remove $HOLD to retry)"
fi
new=$(image_version "$pulled")
case "$new" in
    "$LINE"*) ;;
    *) decline "pulled image reports '${new:-nothing}', not a $LINE* patch; refusing (a new major is a manual upgrade)" ;;
esac

log "forgejo ${before:-?} -> $new: backing up first"
$BACKUP || decline "backup failed; not updating"
archive=$(readlink -f /root/forgejo-backups/LATEST 2>/dev/null || echo unknown)
log "pre-update archive: $archive"
log "images: running $running, applying $pulled"

docker exec -u git "$CONTAINER" gitea manager flush-queues --timeout 60s >/dev/null 2>&1 \
    || log "flush-queues did not complete; continuing"
since=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# Persist the recovery state before replacement can run migrations. A unit
# timeout, signal, or unexpected command failure must not make tomorrow's
# run mistake a half-finished update for an unchanged, healthy installation.
hold
needs_operator "update to forgejo $new started; completion has not been verified"
docker tag "$pulled" "$IMAGE"           # recreate on exactly the image this run checked
docker compose up -d 2>&1 | tail -1 || log "compose up reported an error; waiting anyway"

if wait_for "$new" && stays_up "$new"; then
    if ! integrity=$(docker exec -u git "$CONTAINER" sqlite3 -cmd '.timeout 15000' /data/gitea/gitea.db 'PRAGMA integrity_check;' 2>&1 | head -1); then
        integrity="integrity_check command failed: $integrity"
    fi
    migrations=$(docker logs --since "$since" "$CONTAINER" 2>&1 | grep -c 'Migration\[' || true)
    if [ "$integrity" = ok ]; then
        rm -f "$HOLD" "$ATTENTION"
        [ "$PRUNE" = 1 ] && { docker image prune -f >/dev/null 2>&1 || true; }
        done_ok "forgejo running at $new (migrations: $migrations, integrity ok)"
    fi
    hold
    needs_operator "forgejo $new is up but integrity_check says: $integrity"
    log "forgejo $new is up but integrity_check says: $integrity; leaving it for the operator"
    exit 1
fi

# The new version did not come up, or did not stay up.
migrations=$(docker logs --since "$since" "$CONTAINER" 2>&1 | grep -c 'Migration\[' || true)
docker logs --since "$since" "$CONTAINER" 2>&1 | grep -E '\[F\]|\[E\]' | tail -5 | sed 's/^/forgejo-update:   /' || true
if [ "$migrations" != 0 ]; then
    hold
    needs_operator "forgejo $new did not come up or stay up after $migrations migration(s)"
    log "forgejo $new did not come up or stay up after $migrations migration(s); NOT rolling back the image."
    log "restore the pre-update archive above by UPGRADE.md § 5.1."
    exit 1
fi
log "forgejo $new did not come up or stay up, and ran no migrations; putting ${before:-the previous image} back"
hold
docker tag "$running" "$IMAGE"
docker compose up -d 2>&1 | tail -1 || true
if [ -n "$before" ] && wait_for "$before" && stays_up "$before"; then
    rm -f "$ATTENTION"
    log "rolled back to $before; $new is on hold"
else
    log "the rollback did not come up and stay up either; operator needed"
fi
exit 1
