#!/usr/bin/env bash
# Build and run the private young-commit source check on the VPS (read-only).
# Usage: source/run_private_sources.sh > private-output.json  (keep the output out of the repository
# until reviewed; it contains pseudonyms and declared user-agent tokens only).
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
{
  sed '/^if __name__ == .__main__.:/,$d' "$here/source/aggregate_requests.py"
  python3 - "$here" <<'PY'
import csv, json, sys
base = sys.argv[1]
commits = [[r['sha'], int(r['first_forgejo_unix']), r['episode']] for r in csv.DictReader(open(base + '/data/commit-publication.csv'))]
tips = {r['episode']: r['new_tips'].split() for r in csv.DictReader(open(base + '/data/publication-episodes.csv'))}
print('COMMITS = ' + json.dumps({'commits': commits, 'tips': tips}))
PY
  cat "$here/source/private_sources.py"
} | ssh -F "$HOME/.ssh/config" -o BatchMode=yes -o ConnectTimeout=10 vps nice -n 10 python3 -
