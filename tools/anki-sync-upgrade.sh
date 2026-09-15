#!/bin/bash
# anki-sync-upgrade.sh — see systemd/anki-sync-upgrade.service.
set -euo pipefail
VENV=/opt/anki-sync/venv
PY=$VENV/bin/python
log() { echo "anki-sync-upgrade: $*"; }

version() { "$PY" -c 'import anki.buildinfo; print(anki.buildinfo.version)' 2>/dev/null || echo none; }

if ! "$PY" -c 'import anki' >/dev/null 2>&1; then
    log "venv broken (Python bump?) — rebuilding $VENV"
    rm -rf "$VENV"
    python3 -m venv "$VENV"
    "$PY" -m pip install --quiet --upgrade pip
fi
before=$(version)
"$PY" -m pip install --quiet --upgrade anki
after=$(version)
if [ "$before" = "$after" ]; then
    log "anki $after — unchanged"
    exit 0
fi
log "anki $before -> $after — restarting anki-sync"
systemctl restart anki-sync
sleep 2
systemctl is-active --quiet anki-sync || { log "anki-sync did not come back after the upgrade"; exit 1; }
log "anki-sync running at $after"
