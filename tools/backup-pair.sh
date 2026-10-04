#!/bin/bash
#
# backup-pair.sh — the local half shared by the VPS backup scripts.
#
# Installed at /usr/local/lib/backup-pair.sh and sourced by forgejo-backup.sh,
# couchdb-backup.sh, anki-sync-backup.sh and vps-config-backup.sh
# (BACKUP_PAIR_LIB overrides the path, for tests). Source of truth is this
# file in the repo. Not executable on its own; it logs through the caller's
# `log` and `die`, as borg-offhost.sh does.
#
# A backup is a pair: <prefix>-<TS>.tar.gz and its .sha256. Each is written
# under a dot-prefixed `.partial` name and renamed into place, checksum
# first, so only a complete pair ever counts. The four scripts carried a copy
# of these steps each, and only forgejo-backup's swept up after a run that
# was killed outright (SIGKILL, out of memory, power loss — the scripts'
# EXIT traps clean up everything else): the other three kept a temporary
# archive, possibly gigabytes, in DEST forever (cleanup pass, 2026-10-04).

# pair_lock <dest>
#   Hold an exclusive lock on <dest>/.backup.lock for the rest of the run,
#   or fail at once. pair_prune sweeps temporaries, so two runs into one
#   DEST — a hand run overlapping the timer's — must never overlap: the
#   second would delete the first's archive in progress. Call it before
#   writing any temporary.
pair_lock() {
    local dest=$1
    mkdir -p "$dest"
    exec 8>"$dest/.backup.lock" || die "cannot open $dest/.backup.lock"
    flock -n 8 || die "another backup into $dest is running; not starting a second"
}

# pair_finalize <tmp-archive> <tmp-sum> <archive>
#   Checksum the temporary under the final name and rename both into place.
#   It does not announce the backup: a script that checks the archive
#   further calls pair_publish only once that check passes, so a failed
#   backup never moves LATEST or last-success.
pair_finalize() {
    local tmp=$1 tmp_sum=$2 archive=$3 dest
    dest=$(dirname "$archive")
    # The checksum names the final archive, not the temporary, so
    # `sha256sum -c` works unchanged in DEST after the renames.
    ( cd "$dest" && sha256sum "$(basename "$tmp")" \
        | sed "s|$(basename "$tmp")|$(basename "$archive")|" > "$(basename "$tmp_sum")" ) \
        || die "could not checksum $tmp"
    # Checksum first. A run killed between the renames leaves a checksum
    # with no archive — ignored by retention, swept by pair_prune — whereas
    # the other order would leave an archive that never becomes complete.
    mv "$tmp_sum" "$archive.sha256"
    mv "$tmp" "$archive"
}

# pair_publish <archive>
#   Point LATEST at the archive and stamp last-success: what vps-status and
#   the restore runbooks read as "the newest good backup".
pair_publish() {
    local archive=$1 dest
    dest=$(dirname "$archive")
    ln -sfn "$archive" "$dest/LATEST"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$dest/last-success"
}

# pair_prune <dest> <prefix> <keep>
#   Keep the newest <keep> complete pairs, newest first by NAME (the UTC
#   timestamp in it sorts chronologically and survives a copy or a touch,
#   which mtime does not). An archive without its checksum is reported and
#   left alone: it is not counted, so it can never displace a good backup.
#   Then sweep the debris a killed run leaves: temporaries, and checksums
#   whose archive never landed. Local only: a broken remote must not be able
#   to delete history here.
pair_prune() {
    local dest=$1 prefix=$2 keep=$3 complete=() f i
    while IFS= read -r f; do
        if [ -f "$f.sha256" ]; then
            complete+=("$f")
        else
            log "retention: $(basename "$f") has no .sha256 — NOT counted, NOT pruned; inspect by hand"
        fi
    done < <(find "$dest" -maxdepth 1 -name "$prefix-*.tar.gz" -type f 2>/dev/null | sort -r)

    log "retention: ${#complete[@]} completed archive(s) present, keeping $keep"
    for ((i = keep; i < ${#complete[@]}; i++)); do
        log "retention: pruning $(basename "${complete[$i]}")"
        rm -f "${complete[$i]}" "${complete[$i]}.sha256"
    done

    while IFS= read -r f; do
        log "retention: removing leftover $(basename "$f")"
        rm -f "$f"
    done < <(find "$dest" -maxdepth 1 -name ".$prefix-*.partial" -type f 2>/dev/null)
    while IFS= read -r f; do
        [ -f "${f%.sha256}" ] && continue
        log "retention: removing orphan $(basename "$f")"
        rm -f "$f"
    done < <(find "$dest" -maxdepth 1 -name "$prefix-*.tar.gz.sha256" -type f 2>/dev/null)
}
