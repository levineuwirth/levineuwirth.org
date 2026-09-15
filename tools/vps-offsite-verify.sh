#!/bin/bash
#
# vps-offsite-verify.sh — restore-test the off-host backups, monthly.
#
# Installed at /usr/local/bin/vps-offsite-verify.sh (systemd/vps-offsite-verify.*).
# Uses the borg environment of /etc/default/anki-sync-backup (same repo).
# For each prefix: the newest archive is extracted into a temp dir, the
# tarball's .sha256 checked, then handed to that set's own --verify.
set -euo pipefail
log() { echo "vps-offsite-verify: $*"; }
die() { echo "vps-offsite-verify: $*" >&2; exit 1; }
[ -n "${BORG_REPO:-}" ] || die "BORG_REPO is unset"

log "borg check (repository + archives, no data verify — that is what readback is for)"
borg check --show-rc || die "borg check failed"

tmp=$(mktemp -d -t offsite-verify-XXXXXX); trap 'rm -rf "$tmp"' EXIT
for prefix in forgejo anki; do
    newest=$(borg list --glob-archives "$prefix-*" --short --last 1)
    [ -n "$newest" ] || { log "$prefix: no archive yet — skipped"; continue; }
    log "$prefix: extracting ::$newest"
    (cd "$tmp" && borg extract "::$newest") || die "$prefix: extract failed"
    tarball=$(find "$tmp" -name "$prefix-*.tar.gz" -type f | head -1)
    [ -n "$tarball" ] || die "$prefix: no tarball in ::$newest"
    (cd "$(dirname "$tarball")" && sha256sum -c --quiet "$(basename "$tarball").sha256") || die "$prefix: checksum mismatch after extract"
    case $prefix in
        forgejo) /usr/local/bin/forgejo-backup.sh --verify "$tarball" ;;
        anki)    /usr/local/bin/anki-sync-backup.sh --verify "$tarball" ;;
    esac || die "$prefix: restore test failed"
    rm -rf "${tmp:?}"/*
done
log "ok"
