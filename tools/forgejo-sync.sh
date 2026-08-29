#!/usr/bin/env bash
#
# forgejo-sync.sh — bring git.levineuwirth.org up to date with the local
# repositories, over HTTPS.
#
# Context: Forgejo is advertised as the canonical home (it is cited by URL
# in the CV PDF) but is three to four months behind on eight of nine repos,
# because the only configured Forgejo remote used ssh://…:2222, which is
# filtered on most public networks. HTTPS works everywhere.
#
# SAFETY PROPERTIES, all deliberate:
#
#   * Dry run by default. Nothing is created, pushed, or modified unless
#     --execute is passed. Without it the script only reads.
#   * Never force-pushes. Plain `git push`. If Forgejo holds commits this
#     machine does not have, the push is REFUSED and reported rather than
#     resolved — losing someone else's commits is not this script's call.
#   * Never touches `origin`. It adds a separate `forgejo` remote, so the
#     existing GitHub workflow keeps working and every change here is
#     undone by `git remote remove forgejo`.
#   * New repositories are created PRIVATE. Some of these (oneiros-config,
#     levshell) are not public on GitHub, and a wrong default here would
#     publish them. Flip individual repos to public in the UI afterwards.
#   * No mirrors are configured. A Forgejo push-mirror force-pushes to its
#     target, so enabling one while Forgejo is behind would overwrite
#     GitHub with stale history. Mirrors come after this has run clean.
#
# Usage:
#   export FORGEJO_TOKEN=…          # Settings → Applications, scope write:repository
#   bash tools/forgejo-sync.sh                 # survey only
#   bash tools/forgejo-sync.sh --execute       # do it
#   bash tools/forgejo-sync.sh --execute --create-missing
#
# The token is required even for the survey: it lists your private repos,
# and a tokenless listing would report them as missing and propose creating
# duplicates.

set -uo pipefail

FORGEJO_URL="https://git.levineuwirth.org"
FORGEJO_USER="neuwirth"
REPO_ROOT="${REPO_ROOT:-$HOME/Repos/personal}"

# Repositories to leave alone entirely. They are still listed in the output,
# marked HELD, so that skipping one stays a visible decision rather than a
# repo that quietly disappears from the report.
#
#   oneiros-config — personal configuration, not ready to leave this machine.
SKIP_REPOS=(
    oneiros-config
)

EXECUTE=false
CREATE_MISSING=false

for arg in "$@"; do
    case "$arg" in
        --execute)        EXECUTE=true ;;
        --create-missing) CREATE_MISSING=true ;;
        -h|--help)        sed -n '2,40p' "$0"; exit 0 ;;
        *) echo "unknown argument: $arg" >&2; exit 2 ;;
    esac
done

if [ -z "${FORGEJO_TOKEN:-}" ]; then
    echo "FORGEJO_TOKEN is not set. Generate one at:" >&2
    echo "  $FORGEJO_URL/user/settings/applications  (scope: write:repository)" >&2
    echo "Then: export FORGEJO_TOKEN=…" >&2
    exit 2
fi

$EXECUTE || echo "### DRY RUN — nothing will be changed. Pass --execute to act. ###"
echo

api() {
    curl -sS -H "Authorization: token $FORGEJO_TOKEN" \
         -H "Content-Type: application/json" "$@"
}

# Git needs the token too, for private repositories. It is handed over via
# GIT_ASKPASS rather than embedded in the URL or passed on a command line,
# so it stays out of `ps` output, out of the remote's stored config, and out
# of any error message git prints on failure.
ASKPASS=$(mktemp)
chmod 700 "$ASKPASS"
printf '#!/bin/sh\nprintf "%%s" "$FORGEJO_TOKEN"\n' > "$ASKPASS"
export GIT_ASKPASS="$ASKPASS"
export GIT_TERMINAL_PROMPT=0
trap 'rm -f "$ASKPASS"' EXIT

# ---------------------------------------------------------------------------
# What already exists on Forgejo (includes private repos, hence the token).
# ---------------------------------------------------------------------------
existing=$(api "$FORGEJO_URL/api/v1/user/repos?limit=100" \
           | python3 -c 'import json,sys
try:
    print("\n".join(r["name"].lower() for r in json.load(sys.stdin)))
except Exception as e:
    print("APIERROR", e, file=sys.stderr)')

if [ -z "$existing" ]; then
    echo "Could not list repositories — is the token valid?" >&2
    exit 1
fi

echo "Forgejo currently holds: $(echo "$existing" | tr '\n' ' ')"
echo

created=0; pushed=0; skipped=0; blocked=0

for dir in "$REPO_ROOT"/*/; do
    [ -d "$dir/.git" ] || continue
    name=$(basename "$dir")
    cd "$dir" || continue

    for held in "${SKIP_REPOS[@]}"; do
        if [ "$name" = "$held" ]; then
            echo "=== $name"
            echo "    HELD — in SKIP_REPOS, not created, not pushed, no remote added"
            echo
            continue 2
        fi
    done

    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    nbranches=$(git for-each-ref --format='%(refname)' refs/heads | wc -l)
    ntags=$(git tag | wc -l)
    dirty=$(git status --porcelain | wc -l)

    echo "=== $name  ($branch, $nbranches branches, $ntags tags)"
    [ "$dirty" -gt 0 ] && echo "    note: $dirty uncommitted change(s) — not pushed either way"

    # Forgejo repo names are lowercased; the local directory may not be
    # (LeVCS on disk is levcs there).
    remote_name=$(echo "$name" | tr '[:upper:]' '[:lower:]')

    if ! echo "$existing" | grep -qx "$remote_name"; then
        if ! $CREATE_MISSING; then
            echo "    ABSENT on Forgejo — rerun with --create-missing to create it (private)"
            skipped=$((skipped+1)); echo; continue
        fi
        if $EXECUTE; then
            code=$(api -o /dev/null -w '%{http_code}' -X POST \
                   "$FORGEJO_URL/api/v1/user/repos" \
                   -d "{\"name\":\"$remote_name\",\"private\":true,\"auto_init\":false}")
            if [ "$code" != "201" ]; then
                echo "    create FAILED (HTTP $code) — skipping"
                blocked=$((blocked+1)); echo; continue
            fi
            echo "    created $remote_name (private)"
            created=$((created+1))
        else
            echo "    would create $remote_name (private)"
            created=$((created+1))
        fi
    fi

    # Username in the URL, token supplied by GIT_ASKPASS.
    url="https://$FORGEJO_USER@${FORGEJO_URL#https://}/$FORGEJO_USER/$remote_name.git"

    if $EXECUTE; then
        git remote remove forgejo 2>/dev/null || true
        git remote add forgejo "$url"
    fi

    # --- divergence check -------------------------------------------------
    # Read the remote's refs without fetching. If any remote commit is not
    # an object we already hold, the remote is ahead or has diverged, and a
    # plain push would either fail or (with --force) destroy it. Report and
    # move on; a human decides.
    # A failed listing must NOT read as "nothing unknown on the remote".
    # Unauthenticated ls-remote against a private repo returns empty and
    # exits non-zero, which would otherwise look identical to a clean
    # fast-forward and wave through a push that could be refused — or, with
    # any future --force, be destructive.
    if ! remote_refs=$(timeout 45 git ls-remote "$url" 'refs/heads/*' 2>/dev/null); then
        echo "    BLOCKED — cannot read refs from Forgejo (auth, network, or"
        echo "    repository missing). Not pushing blind."
        blocked=$((blocked+1)); echo; continue
    fi
    ahead_of_us=0
    while read -r sha ref; do
        [ -n "${sha:-}" ] || continue
        if ! git cat-file -e "${sha}^{commit}" 2>/dev/null; then
            echo "    REMOTE HAS UNKNOWN COMMIT on ${ref#refs/heads/} ($(echo "$sha" | cut -c1-8))"
            ahead_of_us=1
        fi
    done <<< "$remote_refs"

    if [ "$ahead_of_us" = 1 ]; then
        echo "    BLOCKED — Forgejo holds commits this machine does not."
        echo "    Resolve by hand (fetch and inspect) before syncing this one."
        blocked=$((blocked+1)); echo; continue
    fi

    # --- push -------------------------------------------------------------
    if $EXECUTE; then
        if git push --all "$url" >/dev/null 2>&1 && git push --tags "$url" >/dev/null 2>&1; then
            echo "    pushed all branches + tags"
            pushed=$((pushed+1))
        else
            echo "    PUSH FAILED — rerun by hand to see git's reason:"
            echo "      git -C '$dir' push --all forgejo"
            blocked=$((blocked+1))
        fi
    else
        out=$(git push --all --dry-run "$url" 2>&1 | grep -vE '^To |^$' | head -5)
        if [ -z "$out" ]; then
            echo "    already up to date"
        else
            echo "    would push:"
            echo "$out" | sed 's/^/      /'
        fi
        pushed=$((pushed+1))
    fi
    echo
done

echo "----------------------------------------------------------------"
printf 'created/creatable: %d   pushed/pushable: %d   skipped: %d   blocked: %d\n' \
    "$created" "$pushed" "$skipped" "$blocked"
$EXECUTE || echo "(dry run — nothing above actually happened)"
echo
echo "Next, only once this runs clean:"
echo "  1. Check the new repos' visibility; all were created private."
echo "  2. Configure push mirrors Forgejo → GitHub, per repo, in"
echo "     Settings → Repository → Mirror Settings. A mirror force-pushes,"
echo "     so it is only safe now that Forgejo is not behind."
