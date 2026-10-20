"""Minute-level request aggregates for the commit-response study.

Runs read-only on the VPS: python3 - < aggregate_requests.py > out.json
Streams the private archive once for owner signals and once for counts. Prints
JSON with sparse per-minute series, hash-position counts and coverage
diagnostics. Addresses, user agents, cookies, queries and request sequences
never leave the VPS; owner and internal addresses only become flags.
Standard library only. Nothing is written on the server.
"""
import collections
import datetime as dt
import gzip
import hashlib
import ipaddress
import json
import re
import subprocess
import sys
from pathlib import Path

UTC = dt.timezone.utc
STATE = Path('/root/anubis-observations/live')
START = dt.datetime(2026, 9, 27, tzinfo=UTC).timestamp()
END = dt.datetime(2026, 10, 19, 22, tzinfo=UTC).timestamp()
if len(sys.argv) > 3 and sys.argv[1] == '--range':        # smoke tests only
    START, END = (dt.datetime.fromisoformat(v).timestamp() for v in sys.argv[2:4])
N = int((END - START) // 60)
WEBSITE = 'levineuwirth.org'
OWNER = 'neuwirth'
REPOS = {'levineuwirth.org', 'pmacs', 'epiphany', 'levcs', 'ozymandias', 'where-simd-helps', 'neuropose',
         'beyond_comorbidity_indices'}
CHECKS = ('anubis-update', 'anubis-d4-check', 'anubis-d4-deploy', 'anubis-d4-git-check',
          'anubis-d5-check', 'anubis-d5-deploy')
LEGACY = re.compile(r'^(\S+) \S+ \S+ \[([^]]+)\] "(\S+) ([^ ]*) [^"]*" (\d+) (\d+|-) "[^"]*" "([^"]*)"')
HEX = re.compile(r'^[0-9a-fA-F]{7,40}$')
COMMIT_POS = re.compile(r'^(src|commits|raw|media|blame|rss|atom)/commit/([0-9a-fA-F]{7,40})(?:/|$)')
COMMIT_VIEW = re.compile(r'^commit/([0-9a-fA-F]{7,40})(\.diff|\.patch)?(?:/|$)')
ARCHIVE = re.compile(r'^archive/([0-9a-fA-F]{7,40})\.(zip|tar\.gz|bundle)$')
CHERRY = re.compile(r'^(?:_cherrypick|cherry-pick)/([0-9a-fA-F]{7,40})(?:/|$)')
SRC_BARE = re.compile(r'^src/([0-9a-fA-F]{40})(?:/|$)')
API_COMMIT = re.compile(r'^(git/commits|commits|archive)/([0-9a-fA-F]{7,40})(?:\.(?:zip|tar\.gz|bundle|diff|patch))?(?:/|$)')


def cohort(ua):
    ua = ua.lower()
    if re.search(r'meta-external|facebook|facebot|meta-webindexer', ua):
        return 'meta-declared'
    if 'amazonbot' in ua:
        return 'amazon-declared'
    if 'x11; linux x86_64' in ua and re.search(r'chrome/(150|155)\.', ua):
        return 'linux-chrome-150-155'
    if re.search(r'bot|crawler|spider', ua):
        return 'other-declared-crawler'
    return 'other'


def status_class(s):
    if s == 200:
        return '200'
    if s in (403, 404, 429, 499):
        return str(s)
    if 200 <= s < 300:
        return '2xx'
    if 300 <= s < 400:
        return '3xx'
    if 400 <= s < 500:
        return '4xx'
    return '5xx' if s >= 500 else 'other'


def is_git(rest):
    return (rest.startswith('info/refs') or rest in ('git-upload-pack', 'git-receive-pack', 'HEAD')
            or rest.startswith('objects/') or rest.startswith('info/'))


def endpoint(rest):
    """Website-repository endpoint class from the path after /neuwirth/<repo>/."""
    if rest == '':
        return 'root'
    parts = rest.split('/')
    head = parts[0]
    second = parts[1] if len(parts) > 1 else ''
    if head == 'commit':
        tail = parts[1] if len(parts) > 1 else ''
        return 'commit-patch' if tail.endswith(('.diff', '.patch')) else 'commit'
    if head in ('src', 'raw', 'media', 'blame', 'commits', 'rss', 'atom'):
        kind = second if second in ('branch', 'commit', 'tag') else ('bare' if second else 'none')
        group = 'feed' if head in ('rss', 'atom') else head
        return f'{group}-{kind}'
    if head == 'archive':
        return 'archive'
    if head == 'compare':
        return 'compare'
    if head in ('activity', 'branches', 'tags', 'releases', 'graph', 'issues', 'pulls', 'wiki', 'milestones',
                'labels', 'projects', 'stars', 'watchers', 'forks', 'find', 'search', 'settings', 'actions',
                'packages', 'tree', 'contributors', 'code-frequency', 'recent-commits', 'lastcommit'):
        return 'meta-' + head
    if head in ('_cherrypick', 'cherry-pick'):
        return 'cherry-pick'
    return 'other'


def hashes(rest, api=False):
    out = []
    if api:
        m = API_COMMIT.match(rest)
        if m:
            out.append(('api-' + m[1].replace('/', '-'), m[2]))
        return out
    for rx, label in ((COMMIT_POS, None), (COMMIT_VIEW, 'commit'), (ARCHIVE, 'archive'), (CHERRY, 'cherry-pick'),
                      (SRC_BARE, 'src-bare')):
        m = rx.match(rest)
        if m:
            if rx is COMMIT_POS:
                out.append((m[1] + '-commit', m[2]))
            elif rx is COMMIT_VIEW:
                out.append(('commit-patch' if m[2] else 'commit', m[1]))
            else:
                out.append((label, m[1]))
            return out
    if rest.startswith('compare/'):
        spec = rest[len('compare/'):].split('/')[0]
        sides = spec.split('...') if '...' in spec else spec.split('..')
        for side, label in zip(sides, ('compare-base', 'compare-head')):
            side = side.split(':')[-1]
            if HEX.match(side):
                out.append((label, side))
    return out


def route(path):
    """(scope, repo, rest) for forge paths."""
    parts = path.split('/', 3)
    if len(parts) >= 3 and parts[1] == OWNER and parts[2]:
        repo = parts[2].lower()
        suffix = ''
        for ext in ('.rss', '.atom'):
            if repo.endswith(ext) and len(parts) == 3:
                repo, suffix = repo[:-len(ext)], 'feed-repo'
        git_dir = repo.endswith('.git')
        repo = repo.removesuffix('.git')
        rest = parts[3] if len(parts) > 3 else ''
        if suffix:
            return 'repository', repo, '\0feed-repo'
        if git_dir or is_git(rest):
            return 'git', repo, rest
        return 'repository', repo, rest
    if path.startswith('/api/v1/repos/'):
        sub = path[len('/api/v1/repos/'):].split('/', 2)
        if len(sub) >= 2 and sub[0].lower() == OWNER:
            return 'api-repo', sub[1].lower(), sub[2] if len(sub) > 2 else ''
        return 'api-other', '', ''
    if path.startswith('/api/'):
        return 'api-other', '', ''
    if path in ('/' + OWNER, '/' + OWNER + '/'):
        return 'user-profile', '', ''
    if path in ('/' + OWNER + '.rss', '/' + OWNER + '.atom'):
        return 'user-feed', '', ''
    if path.startswith('/explore'):
        return 'explore', '', ''
    if path == '/':
        return 'forge-root', '', ''
    if 'pass-challenge' in path:
        return 'pass-challenge', '', ''
    if path.startswith('/.within.website/'):
        return 'anubis', '', ''
    if path.startswith('/user/login'):
        return 'login', '', ''
    if path.startswith(('/assets/', '/avatars/', '/repo-avatars/')):
        return 'assets', '', ''
    return 'other', '', ''


def local_networks():
    nets = [ipaddress.ip_network(n) for n in ('127.0.0.0/8', '::1/128', '172.16.0.0/12', '10.0.0.0/8', '192.168.0.0/16')]
    try:
        out = subprocess.run(['ip', '-o', 'addr'], capture_output=True, text=True, timeout=10).stdout
        for m in re.finditer(r'inet6? ([0-9a-f.:]+)/', out):
            nets.append(ipaddress.ip_network(m[1]))
    except OSError:
        pass
    return nets


NETS = local_networks()
_internal_cache = {}


def internal(ip):
    if ip not in _internal_cache:
        try:
            addr = ipaddress.ip_address(ip)
            _internal_cache[ip] = any(addr in n for n in NETS if n.version == addr.version)
        except ValueError:
            _internal_cache[ip] = False
    return _internal_cache[ip]


_legacy_stamp = {}
_iso_stamp = {}


def records(entry, json_first):
    """Yield (epoch_seconds, row) for in-range records; count diagnostics."""
    kind = entry['kind']
    with gzip.open(STATE / 'nginx' / entry['file'], 'rt', errors='replace') as stream:
        for line in stream:
            DIAG[kind + '_lines'] += 1
            try:
                if kind == 'legacy':
                    left = line.find('[')
                    right = line.find(']', left)
                    stamp = line[left + 1:right]
                    t = _legacy_stamp.get(stamp)
                    if t is None:
                        t = dt.datetime.strptime(stamp, '%d/%b/%Y:%H:%M:%S %z').timestamp()
                        _legacy_stamp[stamp] = t
                    if not START <= t < END:
                        DIAG['legacy_out_of_range'] += 1
                        continue
                    if t >= json_first:
                        DIAG['legacy_at_or_after_json_start'] += 1
                        continue
                    yield t, line
                else:
                    row = json.loads(line)
                    if 'time_unix' in row:
                        t = float(row['time_unix'])
                    else:
                        t = _iso_stamp.get(row['time'])
                        if t is None:
                            t = dt.datetime.fromisoformat(row['time']).timestamp()
                            _iso_stamp[row['time']] = t
                    if not START <= t < END:
                        DIAG['json_out_of_range'] += 1
                        continue
                    yield t, row
            except (ValueError, KeyError, TypeError) as error:
                DIAG['malformed_' + kind] += 1


def parse_legacy(line):
    m = LEGACY.search(line)
    if not m:
        raise ValueError('legacy')
    ip, _, method, path, status, size, ua = m.groups()
    return {'remote_addr': ip, 'method': method, 'path_full': path, 'path': path.split('?', 1)[0],
            'status': int(status), 'ua': ua}


DIAG = collections.Counter()


def owner_signals(archives, json_first):
    """Pass 1: owner signals, address -> UTC dates (private, in memory only)."""
    owner_dates = collections.defaultdict(set)
    signals = collections.Counter()
    for e in archives:
        for t, rec in records(e, json_first):
            text = rec if isinstance(rec, str) else rec.get('path', '')
            if not any(k in text for k in ('git-receive-pack', '/user/settings', '/user/logout', '/notifications',
                                            '/repo/create', '/-/admin', '/settings', '/user/login')):
                continue
            try:
                row = parse_legacy(rec) if isinstance(rec, str) else rec
            except ValueError:
                continue
            path, method, status = row['path'], row['method'], int(row['status'])
            kind = None
            if method == 'POST' and path.endswith('/git-receive-pack') and status == 200:
                kind = 'receive-pack'
            elif method == 'GET' and status == 200 and (path.startswith(('/user/settings', '/notifications', '/repo/create', '/-/admin'))
                                                        or re.match(r'^/[^/]+/[^/]+/settings(/|$)', path)):
                kind = 'authenticated-page'
            elif method == 'POST' and path.startswith('/user/login') and status in (302, 303):
                kind = 'login'
            elif path.startswith('/user/logout') and status in (302, 303) and method == 'POST':
                kind = 'logout'
            if kind:
                day = dt.datetime.fromtimestamp(t, UTC).date()
                owner_dates[row['remote_addr']].add(day)
                signals[(kind, day.isoformat())] += 1
    return owner_dates, signals


def main():
    manifest = json.loads((STATE / 'manifest.json').read_text())
    archives = sorted((e for e in manifest['archives'].values() if e['kind'] in ('legacy', 'forgejo')),
                      key=lambda e: e['first_time'])
    json_first = min(dt.datetime.fromisoformat(e['first_time']).timestamp() for e in archives if e['kind'] == 'forgejo')
    archives = [e for e in archives if dt.datetime.fromisoformat(e['first_time']).timestamp() < END + 3600
                and dt.datetime.fromisoformat(e['last_time']).timestamp() >= START - 3600]
    sources = []
    for e in archives:
        digest = hashlib.sha256()
        with open(STATE / 'nginx' / e['file'], 'rb') as f:
            for block in iter(lambda: f.read(1 << 20), b''):
                digest.update(block)
        sources.append({k: e.get(k) for k in ('file', 'kind', 'first_time', 'last_time', 'raw_sha256', 'raw_bytes', 'captured_at')}
                       | {'compressed_sha256_at_read': digest.hexdigest()})

    owner_dates, signals = owner_signals(archives, json_first)
    owner_days = {ip: {d + dt.timedelta(days=k) for d in days for k in (-1, 0, 1)} for ip, days in owner_dates.items()}
    DIAG.clear()                # pass-2 diagnostics only

    # Pass 2: counts.
    series = collections.defaultdict(collections.Counter)
    hash_rows = collections.Counter()
    seen_ids = set()
    per_archive = []
    for e in archives:
        before = dict(DIAG)
        tmin, tmax, prev, backwards = None, None, None, 0
        for t, rec in records(e, json_first):
            minute = int((t - START) // 60)
            tmin = t if tmin is None or t < tmin else tmin
            tmax = t if tmax is None or t > tmax else tmax
            if prev is not None and t < prev - 1:
                backwards += 1
            prev = t
            if e['kind'] == 'legacy':
                series['L|lines'][minute] += 1
                if '/' + OWNER not in rec and 'git-receive-pack' not in rec:
                    continue
                try:
                    row = parse_legacy(rec)
                except ValueError:
                    DIAG['malformed_legacy_parse'] += 1
                    continue
                start_minute = None
                regime = 'L'
            else:
                row = rec
                rid = row.get('request_id')
                if rid:
                    if rid in seen_ids:
                        DIAG['duplicate_request_ids'] += 1
                        continue
                    seen_ids.add(rid)
                series['J|lines'][minute] += 1
                status = int(row['status'])
                if status >= 500:
                    series['J|5xx'][minute] += 1
                if status in (502, 503, 504):
                    series['J|502-504'][minute] += 1
                rt = row.get('request_time')
                start_minute = int((t - float(rt) - START) // 60) if rt not in (None, '') else None
                regime = 'J'
            path, method, status, ua, ip = row['path'], row['method'], int(row['status']), row.get('ua', ''), row.get('remote_addr', '')
            scope, repo, rest = route(path)
            if regime == 'L' and scope not in ('repository', 'git'):
                continue            # mixed-host log: only repository routes are forge-assignable
            if any(c in ua.lower() for c in CHECKS):
                series[f'CHECK|{scope}'][minute] += 1
                DIAG['excluded_check_requests'] += 1
                continue
            day = dt.datetime.fromtimestamp(t, UTC).date()
            flag = 'internal' if internal(ip) else ('owner' if day in owner_days.get(ip, ()) else '')
            group = cohort(ua)
            sc = status_class(status)
            mclass = method if method in ('GET', 'HEAD', 'POST') else 'OTHER'
            if scope == 'git':
                gitpath = ('info-refs' if rest.startswith('info/refs') else 'upload-pack' if rest == 'git-upload-pack'
                           else 'receive-pack' if rest == 'git-receive-pack' else 'other')
                name = 'website' if repo == WEBSITE else ('other-repo' if repo in REPOS else 'unknown-repo')
                series[f'G|{name}|{mclass}|{gitpath}|{sc}|{flag or "-"}'][minute] += 1
                continue
            if scope == 'repository':
                ep = 'feed-repo' if rest == '\0feed-repo' else endpoint(rest)
                if repo == WEBSITE:
                    keys = [f'W|{mclass}|{group}|{sc}', f'W|{mclass}|{group}|{sc}|{ep}']
                    if flag:
                        keys += [f'W{flag}|{mclass}|{group}|{sc}', f'W{flag}|{mclass}|{group}|{sc}|{ep}']
                    for k in keys:
                        series[k][minute] += 1
                    if start_minute is not None and 0 <= start_minute < N:
                        series[f'Wstart|{mclass}|{group}|{sc}'][start_minute] += 1
                        if flag:
                            series[f'Wstart{flag}|{mclass}|{group}|{sc}'][start_minute] += 1
                    if rest != '\0feed-repo':
                        for position, value in hashes(rest):
                            hash_rows[(value.lower(), position, group, sc, mclass, minute, flag)] += 1
                else:
                    name = repo if repo in REPOS else 'unknown-repo'
                    series[f'R|{name}|{mclass}|{group}|{sc}'][minute] += 1
                    if flag:
                        series[f'R{flag}|{name}|{mclass}|{group}|{sc}'][minute] += 1
                continue
            if scope == 'api-repo':
                name = 'website' if repo == WEBSITE else 'other'
                series[f'F|api-repo-{name}|{mclass}|{group}|{sc}'][minute] += 1
                if flag:
                    series[f'F{flag}|api-repo-{name}|{mclass}|{group}|{sc}'][minute] += 1
                if repo == WEBSITE:
                    for position, value in hashes(rest, api=True):
                        hash_rows[(value.lower(), position, group, sc, mclass, minute, flag)] += 1
                continue
            series[f'F|{scope}|{mclass}|{group}|{sc}'][minute] += 1
            if flag:
                series[f'F{flag}|{scope}|{mclass}|{group}|{sc}'][minute] += 1
        per_archive.append({'file': e['file'], 'kind': e['kind'],
                            'first_in_range': dt.datetime.fromtimestamp(tmin, UTC).isoformat() if tmin else None,
                            'last_in_range': dt.datetime.fromtimestamp(tmax, UTC).isoformat() if tmax else None,
                            'backward_steps_over_1s': backwards,
                            'diagnostics_delta': {k: DIAG[k] - before.get(k, 0) for k in DIAG if DIAG[k] != before.get(k, 0)}})
    owner_summary = {
        'owner_addresses': len(owner_dates),
        'owner_addresses_by_signal_date': {f'{k}|{d}': n for (k, d), n in sorted(signals.items())},
        'flag_rule': 'address with an owner signal on that UTC date, or the adjacent dates',
        'internal_networks_checked': len(NETS),
    }
    print(json.dumps({
        'generated_at': dt.datetime.now(UTC).isoformat(), 'start': dt.datetime.fromtimestamp(START, UTC).isoformat(),
        'end_exclusive': dt.datetime.fromtimestamp(END, UTC).isoformat(), 'minutes': N,
        'json_first': dt.datetime.fromtimestamp(json_first, UTC).isoformat(),
        'sources': sources, 'per_archive': per_archive, 'diagnostics': dict(DIAG), 'owner': owner_summary,
        'series': {k: {str(m): c for m, c in sorted(v.items())} for k, v in sorted(series.items())},
        'hash_rows': [list(k) + [c] for k, c in sorted(hash_rows.items(), key=lambda kv: (kv[0][5], kv[0][0]))],
    }, separators=(',', ':')))


if __name__ == '__main__':
    main()
