"""Private source-level checks of young-commit fetches (read-only on the VPS).

Appended to aggregate_requests.py (without its __main__ guard) and to a COMMITS
definition by source/run_private_sources.sh, then piped to python3 on the VPS.
For every website-repository request naming a current commit within 24 hours
of its first Forgejo publication, summarise its source under a per-run
pseudonym: declared crawler token (a claim) or browser/OS family, any owner
signal on any date, referer category, earlier activity on the repository and
the endpoint classes it requested in the preceding 30 minutes. Addresses,
full user agents, queries and paths are not printed.
"""
import collections as _c

LEGACY_REFERER = re.compile(r'" \d+ (?:\d+|-) "([^"]*)"')
YOUNG_SECONDS = 24 * 3600


def ua_label(ua):
    low = ua.lower()
    m = re.search(r'([a-z0-9._-]*(?:bot|crawler|spider)[a-z0-9._-]*)', low)
    if m:
        return 'declared:' + m.group(1)[:40]
    family = ('firefox' if 'firefox/' in low else 'chrome' if 'chrome/' in low else 'safari' if 'safari/' in low
              else 'tool' if re.search(r'curl|wget|python|go-http|java|okhttp|libwww|git/', low) else 'other')
    system = ('android' if 'android' in low else 'linux' if 'linux' in low else 'windows' if 'windows' in low
              else 'mac' if 'mac os' in low else 'ios' if 'iphone' in low else 'other')
    return f'{family}/{system}'


def referer_class(host):
    host = (host or '').lower()
    if host in ('', '-'):
        return 'none'
    if host.startswith('git.levineuwirth.org'):
        return 'forge'
    if host.endswith('levineuwirth.org'):
        return 'website'
    if 'github.com' in host:
        return 'github'
    return 'other'


def private_main():
    manifest = json.loads((STATE / 'manifest.json').read_text())
    archives = sorted((e for e in manifest['archives'].values() if e['kind'] in ('legacy', 'forgejo')),
                      key=lambda e: e['first_time'])
    json_first = min(dt.datetime.fromisoformat(e['first_time']).timestamp() for e in archives if e['kind'] == 'forgejo')
    owner_dates, _ = owner_signals(archives, json_first)
    commits = {sha: (t, ep) for sha, t, ep in COMMITS['commits']}
    tips = {sha for shas in COMMITS['tips'].values() for sha in shas}
    ordered = sorted(commits)
    prefix_cache = {}

    def resolve(h):
        if h not in prefix_cache:
            hits = [s for s in ordered if s.startswith(h)]
            prefix_cache[h] = hits[0] if len(hits) == 1 else None
        return prefix_cache[h]

    pseudonym = {}
    recent = _c.defaultdict(lambda: _c.deque(maxlen=400))
    first_seen, totals, labels = {}, _c.Counter(), _c.defaultdict(_c.Counter)
    events = _c.Counter()
    context = {}
    for e in archives:
        for t, rec in records(e, json_first):
            if isinstance(rec, str):
                if '/' + OWNER not in rec:
                    continue
                try:
                    row = parse_legacy(rec)
                except ValueError:
                    continue
                m = LEGACY_REFERER.search(rec)
                ref = referer_class(re.sub(r'^https?://([^/]+).*$', r'\1', m[1]) if m else '')
            else:
                row = rec
                ref = referer_class(row.get('referer_host', ''))
            scope, repo, rest = route(row['path'])
            if scope != 'repository' or repo != WEBSITE or rest == '\0feed-repo':
                continue
            ua = row.get('ua', '')
            if any(c in ua.lower() for c in CHECKS):
                continue
            ip = row.get('remote_addr', '')
            ep = endpoint(rest)
            for position, value in hashes(rest):
                sha = resolve(value.lower())
                if not sha:
                    continue
                published, episode = commits[sha]
                age = t - published
                if 0 <= age < YOUNG_SECONDS:
                    if ip not in pseudonym:
                        pseudonym[ip] = f'S{len(pseudonym) + 1:03d}'
                        window = [x for x in recent[ip] if t - x[0] <= 1800]
                        context[pseudonym[ip]] = {
                            'first_young_fetch_utc': dt.datetime.fromtimestamp(t, UTC).isoformat(),
                            'seen_on_repository_before_publication': ip in first_seen and first_seen[ip] < published,
                            'repository_requests_before': totals[ip],
                            'endpoint_classes_previous_30min': dict(_c.Counter(x[1] for x in window)),
                            'owner_signal_any_date': ip in owner_dates,
                            'internal': internal(ip),
                        }
                    key = (pseudonym[ip], episode, sha in tips, int(age // 600) * 10, cohort(ua), ua_label(ua),
                           row['method'], status_class(int(row['status'])), position, ref)
                    events[key] += 1
            recent[ip].append((t, ep))
            first_seen.setdefault(ip, t)
            totals[ip] += 1
            labels[ip][ua_label(ua)] += 1
    sources = {}
    for ip, pid in pseudonym.items():
        sources[pid] = dict(context[pid], repository_requests_total=totals[ip],
                            labels=dict(labels[ip].most_common(3)),
                            first_seen_on_repository_utc=dt.datetime.fromtimestamp(first_seen[ip], UTC).isoformat())
    print(json.dumps({
        'generated_at': dt.datetime.now(UTC).isoformat(), 'young_seconds': YOUNG_SECONDS,
        'sources': sources,
        'events': [dict(zip(('source', 'episode', 'tip', 'age_bin_min', 'cohort', 'ua_label', 'method', 'status',
                             'position', 'referer'), k), requests=n) for k, n in sorted(events.items())],
    }, indent=1))


private_main()
