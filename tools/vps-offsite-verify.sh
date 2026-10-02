#!/bin/bash
#
# vps-offsite-verify.sh — restore-test the off-host backups, monthly.
#
# Installed at /usr/local/bin/vps-offsite-verify.sh (systemd/vps-offsite-verify.*).
# Uses the borg environment of /etc/default/anki-sync-backup (same repo).
# For each prefix: the newest archive must exist and be recent, then it is
# extracted into a temp dir, the tarball's .sha256 checked, and handed to
# that set's own --verify.
#
# A set with no archive, or whose newest archive is older than
# OFFSITE_MAX_AGE_HOURS (default 48), fails the run: before, a missing set
# was "skipped" and a set that stopped shipping weeks ago still verified
# green (audit Y01).
set -euo pipefail
export TMPDIR=${TMPDIR:-/var/tmp}       # /tmp on the VPS is a RAM tmpfs (audit Y10)
log() { echo "vps-offsite-verify: $*"; }
die() { echo "vps-offsite-verify: $*" >&2; exit 1; }
[ -n "${BORG_REPO:-}" ] || die "BORG_REPO is unset"
LOCK=(--lock-wait "${BORG_LOCK_WAIT:-1800}")   # the nightly jobs share the repository
PREFIXES=${OFFSITE_PREFIXES:-forgejo anki couchdb}
MAX_AGE_H=${OFFSITE_MAX_AGE_HOURS:-48}
BIN=${VERIFY_BIN_DIR:-/usr/local/bin}

log "borg check (repository + archives, no data verify — that is what readback is for)"
borg check "${LOCK[@]}" --show-rc || die "borg check failed"

tmp=$(mktemp -d -t offsite-verify-XXXXXX); trap 'rm -rf "$tmp"' EXIT
now=$(date -u +%s)
for prefix in $PREFIXES; do
    newest=$(borg list "${LOCK[@]}" --glob-archives "$prefix-*" --short --last 1)
    [ -n "$newest" ] || die "$prefix: no archive in the repository"
    # Archive names carry their UTC creation time: <prefix>-YYYYmmddTHHMMSSZ.
    ts=${newest#"$prefix"-}
    created=$(date -u -d "${ts:0:4}-${ts:4:2}-${ts:6:2}T${ts:9:2}:${ts:11:2}:${ts:13:2}Z" +%s 2>/dev/null) \
        || die "$prefix: cannot read a time from ::$newest"
    age_h=$(( (now - created) / 3600 ))
    [ "$age_h" -le "$MAX_AGE_H" ] || die "$prefix: newest archive ::$newest is ${age_h}h old (limit ${MAX_AGE_H}h) — the nightly upload has stopped"
    log "$prefix: extracting ::$newest (${age_h}h old)"
    (cd "$tmp" && borg extract "${LOCK[@]}" "::$newest") || die "$prefix: extract failed"
    tarball=$(find "$tmp" -name "$prefix-*.tar.gz" -type f | head -1)
    [ -n "$tarball" ] || die "$prefix: no tarball in ::$newest"
    (cd "$(dirname "$tarball")" && sha256sum -c --quiet "$(basename "$tarball").sha256") || die "$prefix: checksum mismatch after extract"
    case $prefix in
        forgejo) "$BIN/forgejo-backup.sh" --verify "$tarball" ;;
        anki)    "$BIN/anki-sync-backup.sh" --verify "$tarball" ;;
        couchdb) "$BIN/couchdb-backup.sh" --verify "$tarball" ;;
        *)       die "$prefix: no verifier" ;;
    esac || die "$prefix: restore test failed"
    rm -rf "${tmp:?}"/*
done
log "ok"
