#!/bin/bash
#
# vps-config-backup.sh — nightly archive of the VPS's own configuration.
#
# Installed at /usr/local/bin/vps-config-backup.sh, driven by
# systemd/vps-config-backup.timer, environment from /etc/default/vps-config-backup.
# Source of truth is this file in the repo.
#
# The other backups hold what the services hold. A rebuilt host also needs
# what the host holds, and most of it was in no backup (audit Y13): nginx
# and the certificates, the backup jobs' environment files, the sync
# servers' credentials, CouchDB's identity, the units and scripts as
# installed, which timers are enabled, and the Docker network whose gateway
# Forgejo trusts. The repo has the files but not the secrets or the state.
#
# One tarball:
#   etc/                       all of /etc but /etc/borg: the passphrase that
#                              opens this archive is in the password manager,
#                              and a copy inside it would be no use
#   root/forgejo-server/, root/couchdb-server/
#                              compose files, server.env, instance.ini,
#                              local.ini; not the data directories, which are
#                              the forgejo and couchdb sets
#   root/.ssh/config, known_hosts
#                              not the keys: the storage-box key that reaches
#                              this archive cannot be restored from it
#   usr/local/bin/, usr/local/lib/, var/lib/*-update/
#   inventory/                 written at backup time: installed packages,
#                              Docker networks, containers and images, enabled
#                              units, timers, addresses
#
# The archive holds every secret on the host. It is written 0600 under a
# 0700 DEST, and leaves the host only inside the encrypted borg repository.
# Off-host prefix config-*, its own prune; local retention keeps KEEP pairs.
#
#   vps-config-backup.sh            # run
#   vps-config-backup.sh --verify   # check the newest (or a given) archive
#
# Environment (systemd EnvironmentFile, KEY=value):
#   DEST  /root/vps-config-backups   KEEP  14
#   BORG_REPO, BORG_PASSCOMMAND, BORG_RSH, OFFHOST_PRUNE — see borg-offhost.sh; unset BORG_REPO = local only
set -euo pipefail
export TMPDIR=${TMPDIR:-/var/tmp}
umask 077

DEST=${DEST:-/root/vps-config-backups}
KEEP=${KEEP:-14}
ROOT=${CONFIG_ROOT:-/}     # a scratch tree in tests

log() { echo "vps-config-backup: $*"; }
die() { echo "vps-config-backup: $*" >&2; exit 1; }

# What a restore needs before anything else works, by path inside the archive.
REQUIRED=(etc/nginx/nginx.conf etc/letsencrypt inventory/packages.txt inventory/docker-networks.json)

verify_archive() {
    local archive=${1:-} listing missing=()
    [ -n "$archive" ] || archive=$(readlink -f "$DEST/LATEST" 2>/dev/null) \
        || die "--verify: no archive given and $DEST/LATEST does not resolve"
    [ -f "$archive.sha256" ] || die "--verify: $archive has no .sha256 companion — not a completed backup"
    (cd "$(dirname "$archive")" && sha256sum -c --quiet "$(basename "$archive.sha256")") \
        || die "--verify: checksum mismatch"
    listing=$(tar tzf "$archive") || die "--verify: the archive does not read to the end"
    for p in "${REQUIRED[@]}"; do
        grep -qx "\./$p/\?" <<<"$listing" || missing+=("$p")
    done
    [ ${#missing[@]} -eq 0 ] || die "--verify: missing from the archive: ${missing[*]}"
    if grep -q '^\./etc/borg' <<<"$listing"; then
        die "--verify: the archive contains etc/borg — the repository passphrase must not be in it"
    fi
    log "--verify: $archive restores ($(grep -c . <<<"$listing") entries)"
}

case "${1:-}" in
    --verify) verify_archive "${2:-}"; exit 0 ;;
    "") ;;
    *) die "unknown argument: $1" ;;
esac

mkdir -p "$DEST"
chmod 700 "$DEST"
TS=$(date -u +%Y%m%dT%H%M%SZ)
STAGE=$(mktemp -d -t config-backup-XXXXXX)
TMP_ARCHIVE="$DEST/.config-$TS.tar.gz.partial"
TMP_SUM="$DEST/.config-$TS.sha256.partial"
trap 'rm -rf "$STAGE" "$TMP_ARCHIVE" "$TMP_SUM"' EXIT

# The inventory: how the host is put together, not just its files. Each
# command is optional; a missing one is noted in the file instead.
inv() {   # inv <file> <command…>
    local out="$STAGE/inventory/$1"; shift
    "$@" > "$out" 2>&1 || echo "(exit $?: $*)" >> "$out"
}
mkdir -p "$STAGE/inventory"
if command -v pacman >/dev/null 2>&1; then
    inv packages.txt pacman -Qqe
    inv packages-all.txt pacman -Q
else
    echo "(no pacman)" > "$STAGE/inventory/packages.txt"
fi
if command -v docker >/dev/null 2>&1; then
    # `docker network create --subnet … --gateway …` from this recreates
    # proxy-net as Forgejo's REVERSE_PROXY_TRUSTED_PROXIES expects it.
    inv docker-networks.json sh -c 'docker network inspect $(docker network ls -q)'
    inv docker-containers.txt docker ps -a --no-trunc --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Networks}}'
    inv docker-images.txt docker image ls --digests --no-trunc
else
    echo "[]" > "$STAGE/inventory/docker-networks.json"
fi
inv systemd-enabled.txt systemctl list-unit-files --state=enabled --no-pager
inv timers.txt systemctl list-timers --all --no-pager
inv addresses.txt ip -br addr
inv uname.txt uname -a

# Paths that exist on this host; tar fails on one that does not.
paths=()
for p in etc root/forgejo-server root/couchdb-server root/.ssh/config root/.ssh/known_hosts \
         usr/local/bin usr/local/lib var/lib/forgejo-update var/lib/couchdb-update; do
    [ -e "$ROOT/$p" ] && paths+=("$p")
done
[ -d "$ROOT/etc" ] || die "$ROOT/etc does not exist"

# --rsyncable: a night that changes little leaves most bytes where they
# were, so borg stores only the difference (audit Y19). Exit 1 is GNU tar's
# "a file changed while it was read", which /etc's logs and caches do; the
# archive is complete, and anything else is a failure.
rc=0
tar -I 'gzip --rsyncable' -cf "$TMP_ARCHIVE" \
    --exclude='./etc/borg' \
    --exclude='./root/forgejo-server/forgejo-data' \
    --exclude='./root/couchdb-server/couchdb-data' \
    --exclude='./root/couchdb-server/couchdb-data.*' \
    -C "$ROOT" "${paths[@]/#/./}" \
    -C "$STAGE" ./inventory || rc=$?
[ "$rc" -le 1 ] || die "tar failed (exit $rc)"

(cd "$DEST" && sha256sum "$(basename "$TMP_ARCHIVE")" | sed "s/\.config-$TS.tar.gz.partial/config-$TS.tar.gz/" > "$TMP_SUM")
ARCHIVE="$DEST/config-$TS.tar.gz"
mv "$TMP_SUM" "$ARCHIVE.sha256"
mv "$TMP_ARCHIVE" "$ARCHIVE"
verify_archive "$ARCHIVE"
ln -sfn "$ARCHIVE" "$DEST/LATEST"
date -u +%Y-%m-%dT%H:%M:%SZ > "$DEST/last-success"
log "wrote $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1)) + .sha256"

if [ -n "${BORG_REPO:-}" ]; then
    . "${BORG_OFFHOST_LIB:-/usr/local/lib/borg-offhost.sh}" || die "off-host: borg-offhost.sh is missing"
    borg_offhost_copy config "$ARCHIVE" "$ARCHIVE.sha256"
else
    log "off-host: BORG_REPO is unset — this backup exists ONLY on the host it backs up."
fi

# local retention: completed pairs only, newest first by name
mapfile -t complete < <(find "$DEST" -maxdepth 1 -name 'config-*.tar.gz' -type f | sort -r | while read -r f; do [ -f "$f.sha256" ] && echo "$f"; done)
for ((i = KEEP; i < ${#complete[@]}; i++)); do
    log "retention: pruning $(basename "${complete[$i]}")"
    rm -f "${complete[$i]}" "${complete[$i]}.sha256"
done
log "done"
