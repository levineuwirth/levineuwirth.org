#!/bin/bash
#
# borg-offhost.sh — the off-host half shared by the VPS backup scripts.
#
# Installed at /usr/local/lib/borg-offhost.sh and sourced by
# forgejo-backup.sh (OFFHOST_TOOL=borg), anki-sync-backup.sh and
# couchdb-backup.sh. Source of truth is this file in the repo. Not
# executable on its own.
#
# One borg repository on the storage box holds every set, told apart by
# archive prefix: forgejo-<TS>, anki-<TS>, couchdb-<TS>. Each caller prunes
# only its own prefix, so a broken Anki run can never thin the Forgejo
# history. The jobs' timer windows overlap, so every borg call waits for
# the repository lock (BORG_LOCK_WAIT) instead of borg's default of one
# second, which failed whichever job came second (audit Y03).
#
# Environment (from /etc/default/<caller>, read by systemd — one KEY=value
# per line, no shell):
#   BORG_REPO         ssh://storagebox/./backup/vps
#   BORG_PASSCOMMAND  cat /etc/borg/passphrase
#   BORG_RSH          ssh -i /root/.ssh/id_storagebox -o BatchMode=yes
#   OFFHOST_PRUNE     --keep-within 7d --keep-daily 14 --keep-weekly 8 --keep-monthly 12
#                     (default). keep-daily keeps only the last archive of a
#                     day, so without keep-within a pre-update or per-hop
#                     archive vanished at the next same-day backup (audit Y08).
#   BORG_LOCK_WAIT    seconds to wait for the repository lock (default 1800;
#                     the units' TimeoutStartSec bounds it)
#
# After the readback, the caller's $DEST/last-offhost-success is stamped.
# $DEST/last-success only says the local archive is complete; it is written
# before the upload, so it stays fresh while every upload fails (audit Y01).
#
# Readback is the same proof the rsync path gives: the archived file is
# streamed back out of the repository and hashed here, so what is verified
# is the bytes that arrived, not a claim about them.

OFFHOST_PRUNE=${OFFHOST_PRUNE:---keep-within 7d --keep-daily 14 --keep-weekly 8 --keep-monthly 12}
BORG_LOCK_WAIT=${BORG_LOCK_WAIT:-1800}

borg_offhost_copy() {
    # $1 prefix (forgejo|anki), $2 archive path, $3 its .sha256; logs via
    # the caller's log/die.
    local prefix=$1 archive=$2 sum=$3 name
    command -v borg >/dev/null 2>&1 || die "off-host: borg is not installed"
    [ -n "${BORG_REPO:-}" ] || die "off-host: BORG_REPO is unset"
    name="$prefix-$(date -u +%Y%m%dT%H%M%SZ)"
    log "off-host: borg create ::$name"
    borg create --lock-wait "$BORG_LOCK_WAIT" --compression zstd,3 --stats --show-rc \
        "::$name" "$archive" "$sum" \
        || die "off-host: borg create failed — the local archive is kept, retention did not run"

    local want got
    want=$(awk '{print $1}' "$sum")
    # borg stores paths without the leading slash
    got=$(borg extract --lock-wait "$BORG_LOCK_WAIT" --stdout "::$name" "${archive#/}" | sha256sum | awk '{print $1}')
    [ "$want" = "$got" ] || die "off-host: read-back checksum mismatch (want $want, got $got)"
    log "off-host: verified — ::$name/$(basename "$archive") hashes to $got"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$(dirname "$archive")/last-offhost-success"

    # shellcheck disable=SC2086
    borg prune --lock-wait "$BORG_LOCK_WAIT" --glob-archives "$prefix-*" $OFFHOST_PRUNE --show-rc \
        || die "off-host: borg prune failed (the archive is safe; retention on the box was not applied)"
    borg compact --lock-wait "$BORG_LOCK_WAIT" --show-rc || log "off-host: borg compact failed — space is not reclaimed until the next success"
    log "off-host: pruned to '$OFFHOST_PRUNE' for $prefix-*"
}
