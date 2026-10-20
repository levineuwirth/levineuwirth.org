"""Read-only, sanitized publication-metadata collector for neuwirth/levineuwirth.org.

Runs on the VPS (python3 - < this file). Exports commit hashes, parent graph,
author/committer epoch seconds, ref/reflog transactions, and Forgejo action
and branch rows with messages, names, emails and user identities removed.
Nothing is written on the server.
"""
import datetime as D, hashlib, json, pathlib, re, sqlite3, subprocess

UTC = D.timezone.utc
ROOT = pathlib.Path('/root/forgejo-server/forgejo-data/git/repositories/neuwirth/levineuwirth.org.git')
DB = '/root/forgejo-server/forgejo-data/gitea/gitea.db'
HEX40 = re.compile(r'^[0-9a-f]{40}$')


def git(*args, stdin=None):
    p = subprocess.run(['git', '-c', 'safe.directory=*', '--git-dir=' + str(ROOT), *args],
                       input=stdin, capture_output=True, text=True, timeout=120)
    if p.returncode:
        raise RuntimeError(p.stderr.strip())
    return p.stdout


observed_at = D.datetime.now(UTC).isoformat()
con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
con.row_factory = sqlite3.Row
repo = con.execute("SELECT id, owner_id, is_private, default_branch, is_mirror, created_unix, updated_unix "
                   "FROM repository WHERE owner_name='neuwirth' AND lower_name='levineuwirth.org'").fetchone()
assert repo and not repo['is_private']

# Every commit object in the store, reachable or not.
objects = git('cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype)', '--unordered')
all_commits = sorted(line.split()[0] for line in objects.splitlines() if line.endswith(' commit'))
raw = git('log', '--no-walk=unsorted', '--stdin', '--format=%H %ct %at %P', stdin='\n'.join(all_commits) + '\n')
commits = {}
for line in raw.splitlines():
    parts = line.split()
    commits[parts[0]] = {'committer_unix': int(parts[1]), 'author_unix': int(parts[2]), 'parents': parts[3:]}
reachable_refs = set(git('rev-list', '--all').split())
reachable_reflog = set(git('rev-list', '--all', '--reflog').split())
for sha, c in commits.items():
    c['reachable_from_refs'] = sha in reachable_refs
    c['reachable_from_refs_or_reflogs'] = sha in reachable_reflog

refs = []
for line in git('for-each-ref', '--format=%(refname) %(objectname) %(objecttype) %(*objectname)').splitlines():
    name, obj, kind, *peeled = line.split()
    refs.append({'ref': name, 'object': obj, 'type': kind, 'peeled': peeled[0] if peeled else None})

# Reflog transactions: keep hashes, epoch and timezone; drop identity and free-text message
# except for a short known verb.
reflogs = []
for path in sorted((ROOT / 'logs').rglob('*')):
    if not path.is_file():
        continue
    ref = str(path.relative_to(ROOT / 'logs'))
    for n, line in enumerate(path.read_text(errors='replace').splitlines()):
        head, _, message = line.partition('\t')
        fields = head.split()
        verb = message.split(':')[0].strip()
        reflogs.append({'ref': ref, 'line': n, 'old': fields[0], 'new': fields[1],
                        'time_unix': int(fields[-2]), 'tz': fields[-1],
                        'message_verb': verb if re.fullmatch(r'[a-z -]{1,20}', verb or '') else ('' if not message else 'other')})

actions = []
for row in con.execute('SELECT id, user_id, act_user_id, op_type, ref_name, created_unix, content '
                       'FROM action WHERE repo_id=? ORDER BY created_unix, id', (repo['id'],)):
    item = {'id': row['id'], 'op_type': row['op_type'], 'ref': row['ref_name'], 'time_unix': row['created_unix'],
            'actor_is_owner': row['act_user_id'] == repo['owner_id'], 'feed_user_is_owner': row['user_id'] == repo['owner_id'],
            'content_present': bool(row['content'])}
    try:
        content = json.loads(row['content']) if row['content'] else None
    except ValueError:
        content = None
        item['content_parse_error'] = True
    if isinstance(content, dict):
        compare = content.get('CompareURL') or ''
        m = re.search(r'/compare/([0-9a-f]{7,40})\.\.\.([0-9a-f]{7,40})', compare)
        item['compare_old'] = m[1] if m else None
        item['compare_new'] = m[2] if m else None
        item['compare_url_shape'] = re.sub(r'[0-9a-f]{7,40}', '<sha>', re.sub(r'^https?://[^/]+', '', compare)) if compare else ''
        item['reported_len'] = content.get('Len')
        item['listed_commits'] = [{'sha': c.get('Sha1'), 'timestamp': c.get('Timestamp')}
                                  for c in content.get('Commits') or [] if c.get('Sha1')]
        head = content.get('HeadCommit') or {}
        item['head_sha'] = head.get('Sha1')
        item['head_timestamp'] = head.get('Timestamp')
        item['content_keys'] = sorted(content)
    elif content is not None:
        item['content_type'] = type(content).__name__
    actions.append(item)

branches = [{'name': r['name'], 'commit_id': r['commit_id'], 'pusher_is_owner': r['pusher_id'] == repo['owner_id'],
             'is_deleted': bool(r['is_deleted']), 'deleted_unix': r['deleted_unix'], 'commit_time': r['commit_time'],
             'created_unix': r['created_unix'], 'updated_unix': r['updated_unix']}
            for r in con.execute('SELECT * FROM branch WHERE repo_id=?', (repo['id'],))]
counts = {
    'push_mirror_rows': con.execute('SELECT count(*) FROM push_mirror WHERE repo_id=?', (repo['id'],)).fetchone()[0],
    'pull_mirror_rows': con.execute('SELECT count(*) FROM mirror WHERE repo_id=?', (repo['id'],)).fetchone()[0],
    'release_or_tag_rows': con.execute('SELECT count(*) FROM release WHERE repo_id=?', (repo['id'],)).fetchone()[0],
}
files = {}
for name in ('packed-refs', 'HEAD', 'FETCH_HEAD', 'ORIG_HEAD'):
    p = ROOT / name
    if p.exists():
        files[name] = {'bytes': p.stat().st_size, 'mtime_unix': p.stat().st_mtime,
                       'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
packs = sorted({'name': p.name, 'mtime_unix': p.stat().st_mtime, 'bytes': p.stat().st_size}.items() for p in (ROOT / 'objects/pack').glob('*.pack'))
print(json.dumps({
    'observed_at': observed_at, 'git_version': git('--version').strip(),
    'repository': {k: repo[k] for k in ('id', 'is_private', 'default_branch', 'is_mirror', 'created_unix', 'updated_unix')},
    'commits': commits, 'refs': refs, 'reflogs': reflogs, 'actions': actions, 'branches': branches,
    'table_counts': counts, 'repo_files': files, 'packs': [dict(p) for p in packs],
}, sort_keys=True))
