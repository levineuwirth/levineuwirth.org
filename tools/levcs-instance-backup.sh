#!/bin/bash
#
# levcs-instance-backup.sh — nightly archive of the LeVCS instance's repositories.
#
# Installed at /usr/local/bin/levcs-instance-backup.sh, driven by
# systemd/levcs-instance-backup.timer, environment from
# /etc/default/levcs-instance-backup. Source of truth is this file in the repo.
#
# The instance (levcs-instance.service, 127.0.0.1:7117, reached through an
# SSH tunnel) serves every repository from LEVCS_ROOT, one directory per
# repository id. LeVCS installs two tools of its own beside its binaries in
# /usr/local/bin, from deploy/ in its repository: levcs-backup archives the
# root and reads the archive back, and levcs-restore puts an archive in
# place only once every repository in it passes `levcs verify` and holds
# the id it is named for. This job drives those rather than tar, so the
# archive is the kind LeVCS's deployment gate restores, checked by the
# tool a real restore would use.
#
# A copy taken while the instance runs can hold a ref without the objects
# it names, or a push half applied, so the job stops the instance for the
# seconds the archive takes and starts it again on every exit path, as
# anki-sync-backup does. A push in flight finishes first (the instance's
# unit allows it 150 s); one sent during the window is refused at connect
# and can be sent again. An instance found stopped or failed is archived
# as it stands and left that way.
#
# A backup counts once levcs-restore has restored it into a scratch root,
# with at least one repository in it. --verify repeats that for the newest
# (or a given) archive with the levcs installed now; it reads only, and
# never touches the live root.
#
#   levcs-instance-backup.sh            # run
#   levcs-instance-backup.sh --verify   # restore the newest (or a given) archive into a scratch root
#
# Environment (systemd EnvironmentFile, KEY=value):
#   LEVCS_ROOT  /var/lib/levcs   DEST  /root/levcs-backups   KEEP  14
#   BORG_REPO, BORG_PASSCOMMAND, BORG_RSH, OFFHOST_PRUNE — see borg-offhost.sh; unset BORG_REPO = local only
set -euo pipefail
export TMPDIR=${TMPDIR:-/var/tmp}       # /tmp on the VPS is a RAM tmpfs (audit Y10)
umask 077

LEVCS_ROOT=${LEVCS_ROOT:-/var/lib/levcs}
LEVCS_ROOT=${LEVCS_ROOT%/}
DEST=${DEST:-/root/levcs-backups}
KEEP=${KEEP:-14}
SERVICE=levcs-instance.service

log() { echo "levcs-instance-backup: $*"; }
die() { echo "levcs-instance-backup: $*" >&2; exit 1; }
. "${BACKUP_PAIR_LIB:-/usr/local/lib/backup-pair.sh}" || die "backup-pair.sh is missing (install it to /usr/local/lib)"

# Globals, not locals: the EXIT trap runs after a function's scope is gone.
WAS_ACTIVE=0 STAGE='' SCRATCH='' TMP_ARCHIVE='' TMP_SUM=''

start_again() {
    [ "$WAS_ACTIVE" = 1 ] || return 0
    if systemctl start "$SERVICE"; then
        WAS_ACTIVE=0
        log "$SERVICE started again"
    else
        log "$SERVICE did NOT start again — check it"
        return 1
    fi
}
cleanup() {
    rm -rf ${STAGE:+"$STAGE"} ${SCRATCH:+"$SCRATCH"} ${TMP_ARCHIVE:+"$TMP_ARCHIVE"} ${TMP_SUM:+"$TMP_SUM"}
    start_again || true
}
trap cleanup EXIT

verify_archive() {
    local archive=${1:-} root n
    [ -n "$archive" ] || archive=$(readlink -f "$DEST/LATEST" 2>/dev/null) \
        || die "--verify: no archive given and $DEST/LATEST does not resolve"
    [ -f "$archive.sha256" ] || die "--verify: $archive has no .sha256 companion — not a completed backup"
    (cd "$(dirname "$archive")" && sha256sum -c --quiet "$(basename "$archive.sha256")") \
        || die "--verify: checksum mismatch"
    command -v levcs-restore >/dev/null 2>&1 \
        || die "--verify: levcs-restore is not installed (LeVCS's deploy/, into /usr/local/bin)"
    SCRATCH=$(mktemp -d -t levcs-verify-XXXXXX)
    # Run as root, levcs-restore checks each repository as the user that
    # owns it (levcs), who must be able to pass through these two.
    chmod 0711 "$SCRATCH"
    mkdir -m 0711 "$SCRATCH/srv"
    root="$SCRATCH/srv/$(basename "$LEVCS_ROOT")"
    levcs-restore "$archive" "$root" >/dev/null \
        || die "--verify: levcs-restore refused $archive for the reasons above (the scratch copy it names is removed; the archive is not)"
    # levcs-restore refused anything in the root but repositories, so each
    # directory left is one that verified.
    n=$(find "$root" -mindepth 1 -maxdepth 1 -type d | wc -l)
    [ "$n" -ge 1 ] || die "--verify: no repository in $(basename "$archive")"
    rm -rf "$SCRATCH"
    SCRATCH=''
    if [ "$n" -eq 1 ]; then n="1 repository"; else n="$n repositories"; fi
    log "--verify: $archive restores ($n, each verified by levcs-restore)"
}

case "${1:-}" in
    --verify) verify_archive "${2:-}"; exit 0 ;;
    "") ;;
    *) die "unknown argument: $1" ;;
esac

[ -d "$LEVCS_ROOT" ] || die "$LEVCS_ROOT does not exist — is the instance installed?"
command -v levcs-backup >/dev/null 2>&1 \
    || die "levcs-backup is not installed (LeVCS's deploy/, into /usr/local/bin)"
mkdir -p "$DEST"
chmod 700 "$DEST"
pair_lock "$DEST"
TS=$(date -u +%Y%m%dT%H%M%SZ)
STAGE=$(mktemp -d -t levcs-backup-XXXXXX)
TMP_ARCHIVE="$DEST/.levcs-$TS.tar.gz.partial"
TMP_SUM="$DEST/.levcs-$TS.sha256.partial"

# Anything but stopped or failed is stopped first: an instance waiting out
# its RestartSec reads "activating", and would come up during the archive.
state=$(systemctl is-active "$SERVICE" || true)
case $state in
    inactive|failed)
        log "$SERVICE is $state: archiving the root as it stands, and leaving it $state" ;;
    *)
        WAS_ACTIVE=1
        systemctl stop "$SERVICE" || die "could not stop $SERVICE"
        log "$SERVICE stopped for the archive" ;;
esac

# levcs-backup reads the archive back whole before it publishes it under
# this name. Its own message names the staging path; the one below names
# the archive.
levcs-backup "$STAGE/levcs.tgz" "$LEVCS_ROOT" >/dev/null || die "levcs-backup failed"

# the archive is on disk: bring the instance back before the checks and the slow off-host part
start_again || die "$SERVICE did NOT start again"

mv "$STAGE/levcs.tgz" "$TMP_ARCHIVE"
ARCHIVE="$DEST/levcs-$TS.tar.gz"
pair_finalize "$TMP_ARCHIVE" "$TMP_SUM" "$ARCHIVE"
verify_archive "$ARCHIVE"
pair_publish "$ARCHIVE"     # only once the archive has restored
log "wrote $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1)) + .sha256"

if [ -n "${BORG_REPO:-}" ]; then
    . "${BORG_OFFHOST_LIB:-/usr/local/lib/borg-offhost.sh}" || die "off-host: borg-offhost.sh is missing"
    borg_offhost_copy levcs "$ARCHIVE" "$ARCHIVE.sha256"
else
    log "off-host: BORG_REPO is unset — this backup exists ONLY on the host it backs up."
fi

pair_prune "$DEST" levcs "$KEEP"
log "done"
