#!/bin/sh
# with-deploy-credentials.sh — run a command with a git credential cache of
# its own for one URL.
#
#   tools/with-deploy-credentials.sh <url> <command> [args...]
#
# The deploy pushes the engine and then the site to the same Forgejo, and
# each push used to ask for the token. Under this wrapper the first push
# stores it in a cache private to this run and the second reads it there.
#
# The cache holds the token in memory, behind a socket in a fresh 0700
# directory, so concurrent deploys from two checkouts never share one. For
# <url> it replaces every helper configured elsewhere, so none of them is
# handed the token to keep. It exits with the command, or after
# DEPLOY_CRED_TIMEOUT seconds (default 120) if this script is killed.
# Configuration the caller passes through GIT_CONFIG_COUNT is kept.

set -eu

if [ "$#" -lt 2 ]; then
    echo "usage: $0 <url> <command> [args...]" >&2
    exit 2
fi
url=$1
shift

dir=$(mktemp -d "${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/git-deploy.XXXXXX")
export DEPLOY_CRED_SOCKET="$dir/socket"
cleanup() {
    git credential-cache --socket="$DEPLOY_CRED_SOCKET" exit 2>/dev/null || true
    rm -rf "$dir"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# An empty helper first clears the list for <url>; then the cache. Git runs
# the helper through the shell, so the socket is named by the variable
# above, quoted, rather than spelled out: a path with a space in it would be
# split.
n=${GIT_CONFIG_COUNT:-0}
export "GIT_CONFIG_KEY_$n=credential.$url.helper" "GIT_CONFIG_VALUE_$n="
n=$((n + 1))
export "GIT_CONFIG_KEY_$n=credential.$url.helper" \
       "GIT_CONFIG_VALUE_$n=cache --timeout=${DEPLOY_CRED_TIMEOUT:-120} --socket=\"\$DEPLOY_CRED_SOCKET\""
export GIT_CONFIG_COUNT=$((n + 1))

rc=0
"$@" || rc=$?
exit "$rc"
