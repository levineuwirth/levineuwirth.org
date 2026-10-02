#!/bin/bash
# anki-sync-upgrade.sh — see systemd/anki-sync-upgrade.service.
#
# Upgrades the anki wheel in the server's venv and restarts the server when
# the version changed. The server must then answer HTTP — any status: `/`
# is a 404 through nginx, which still proves it is serving — within
# PROBE_SECS. If it does not, the previous version is reinstalled and the run
# fails. (Before, the only check was `is-active` two seconds after the
# restart, which a release that crashes after three seconds or never binds
# passes, and nothing put the old version back; audit Y06.)
#
# A venv that no longer imports anki (a Python minor bump) is rebuilt beside
# the old one and swapped in only once it imports anki and the server
# answers from it; a failed rebuild — PyPI down, no wheel yet for the new
# Python — leaves the old venv where it was.
set -euo pipefail
VENV=${VENV:-/opt/anki-sync/venv}
SERVICE=${SERVICE:-anki-sync}
PROBE_URL=${PROBE_URL:-http://127.0.0.1:8080/}
PROBE_SECS=${PROBE_SECS:-20}
PY=$VENV/bin/python
log() { echo "anki-sync-upgrade: $*"; }

version() { "$PY" -c 'import anki.buildinfo; print(anki.buildinfo.version)' 2>/dev/null || echo none; }
answers() {   # the server answers HTTP at all within PROBE_SECS
    local _
    for _ in $(seq "$PROBE_SECS"); do
        curl -s -o /dev/null --max-time 2 "$PROBE_URL" && return 0
        sleep 1
    done
    return 1
}
restart_and_probe() { systemctl restart "$SERVICE" && answers; }

if ! "$PY" -c 'import anki' >/dev/null 2>&1; then
    log "the venv no longer imports anki (Python bump?) — rebuilding beside it"
    rm -rf "$VENV.new"
    if ! { python3 -m venv "$VENV.new" \
           && "$VENV.new/bin/python" -m pip install --quiet --upgrade pip anki \
           && "$VENV.new/bin/python" -c 'import anki'; }; then
        rm -rf "$VENV.new"
        log "rebuild failed; the old venv is left in place"
        exit 1
    fi
    # The service runs `$VENV/bin/python -m anki.syncserver`, which resolves
    # its site-packages relative to the interpreter, so a venv can be renamed.
    rm -rf "$VENV.old"
    mv "$VENV" "$VENV.old"
    mv "$VENV.new" "$VENV"
    if restart_and_probe; then
        rm -rf "$VENV.old"
        log "rebuilt; anki-sync running at $(version)"
        exit 0
    fi
    log "the rebuilt venv does not serve; putting the old one back"
    rm -rf "$VENV"
    mv "$VENV.old" "$VENV"
    systemctl restart "$SERVICE" || true
    exit 1
fi

before=$(version)
"$PY" -m pip install --quiet --upgrade anki
after=$(version)
if [ "$before" = "$after" ]; then
    log "anki $after — unchanged"
    exit 0
fi
log "anki $before -> $after — restarting $SERVICE"
if restart_and_probe; then
    log "$SERVICE answering at $after"
    exit 0
fi
log "$SERVICE does not answer at $after"
if [ "$before" = none ]; then
    log "no previous version to return to; operator needed"
    exit 1
fi
log "reinstalling anki $before"
"$PY" -m pip install --quiet "anki==$before" || { log "reinstalling $before failed; operator needed"; exit 1; }
if restart_and_probe; then
    log "rolled back to $before; $after does not serve"
else
    log "$before does not answer either; operator needed"
fi
exit 1
