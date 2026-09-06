#!/usr/bin/env bash
# with-lock.sh — run a command while holding an exclusive lock on a file.
#
#   ./tools/with-lock.sh <lockfile> <command> [args...]
#
# Why: _site/ and _cache/ are shared mutable state with no concurrency
# story. `make build` in one terminal while `make watch` runs in another
# has both processes writing the same Hakyll cache and the same output
# tree; `make deploy` can then rsync --delete a half-written mixture of
# the two to the VPS. `.NOTPARALLEL:` prevents that inside one make
# invocation and does nothing at all between invocations.
#
# The lock is advisory and process-scoped: it is held on file descriptor 9,
# which survives the `exec` below, so it is released by the kernel when the
# command exits — including when it is killed, which a lock file guarded by
# a trap would not survive.
#
# Environment:
#   LOCK_TIMEOUT   seconds to wait for the lock (default 0 = fail at once)
#
# Exit status is the command's own, except 1 when the lock is unavailable.

set -euo pipefail

if [ "$#" -lt 2 ]; then
    echo "usage: $0 <lockfile> <command> [args...]" >&2
    exit 2
fi

lock="$1"
shift

mkdir -p "$(dirname "$lock")"

if ! command -v flock >/dev/null 2>&1; then
    # macOS and minimal containers have no flock(1). Serialising is a
    # safety property, not a correctness one for a single user, so warn
    # rather than refusing to build.
    echo "with-lock: flock(1) not found — running WITHOUT an inter-process lock" >&2
    exec "$@"
fi

exec 9>"$lock"
if ! flock -w "${LOCK_TIMEOUT:-0}" 9; then
    echo "" >&2
    echo "  Another build, deploy, watch or dev session already holds" >&2
    echo "  $lock." >&2
    echo "" >&2
    echo "  They share _site/ and _cache/, so running both would interleave" >&2
    echo "  writes into the same output tree. Wait for the other one, or:" >&2
    echo "" >&2
    echo "    LOCK_TIMEOUT=600 make <target>   # block up to 10 minutes" >&2
    echo "" >&2
    exit 1
fi

exec "$@"
