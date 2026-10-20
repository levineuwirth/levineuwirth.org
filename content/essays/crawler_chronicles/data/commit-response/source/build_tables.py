#!/usr/bin/env python3
"""Turn the VPS aggregate into reviewed tables.

Usage: build_tables.py <aggregate.json>
Writes data/minute-series.csv.gz (dense, one row per UTC minute, with coverage
flags), data/hash-requests.csv.gz (requests whose path names a commit),
data/coverage.json and data/aggregation-meta.json. Standard library only.
"""
import csv
import datetime as dt
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
UTC = dt.timezone.utc
JSON_FIRST = 1791067375                 # 2026-10-03T22:42:55Z
PHASES = [(None, 1791072000, 'before-anubis'), (1791072000, 1791158400, 'anubis-deployment-day'),
          (1791158400, 1792008845.044611, 'difficulty-2'), (1792008845.044611, 1792010723.046673, 'd4-cookie-transition'),
          (1792010723.046673, 1792144163.860856, 'after-d4-cookie-fix'),
          (1792144163.860856, 1792144165.521649, 'd5-transition'), (1792144165.521649, None, 'difficulty-5')]
# Recorded operational disruptions (A7). The archive-route switch is located from the data below.
DISRUPTIONS = [('2026-10-01T19:20:00Z', '2026-10-01T19:50:00Z', 'forgejo-upgrade-1.21-to-15.0.9'),
               ('2026-10-15T16:07:00Z', '2026-10-15T16:20:00Z', 'host-reboot')]
COHORTS = {'linux-chrome-150-155': 'primary', 'meta-declared': 'meta', 'amazon-declared': 'amazon',
           'other-declared-crawler': 'otherbot', 'other': 'other'}
STATUSES = ['200', '2xx', '3xx', '403', '404', '429', '499', '4xx', '5xx']
ENDPOINT_GROUPS = {
    'root': 'root', 'commit': 'commit', 'commit-patch': 'commit', 'src-commit': 'src-commit', 'src-branch': 'src-branch',
    'src-tag': 'src-other', 'src-bare': 'src-other', 'src-none': 'src-other',
    'raw-commit': 'raw-commit', 'media-commit': 'raw-commit', 'raw-branch': 'raw-branch', 'media-branch': 'raw-branch',
    'raw-tag': 'raw-other', 'raw-bare': 'raw-other', 'raw-none': 'raw-other', 'media-tag': 'raw-other', 'media-bare': 'raw-other', 'media-none': 'raw-other',
    'blame-commit': 'blame', 'blame-branch': 'blame', 'blame-tag': 'blame', 'blame-bare': 'blame', 'blame-none': 'blame',
    'commits-commit': 'history-commit', 'commits-branch': 'history-branch', 'commits-tag': 'history-other',
    'commits-bare': 'history-other', 'commits-none': 'history-other',
    'feed-repo': 'feed', 'feed-branch': 'feed', 'feed-commit': 'feed', 'feed-tag': 'feed', 'feed-bare': 'feed', 'feed-none': 'feed',
    'archive': 'archive', 'compare': 'compare', 'cherry-pick': 'other', 'other': 'other'}
CONTROL_REPOS = ['pmacs', 'epiphany', 'levcs', 'ozymandias', 'where-simd-helps', 'neuropose', 'beyond_comorbidity_indices', 'unknown-repo']


def ts(text):
    return dt.datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()


def phase(t):
    for lo, hi, name in PHASES:
        if (lo is None or t >= lo) and (hi is None or t < hi):
            return name


def main(path):
    agg = json.loads(Path(path).read_text())
    start, n = ts(agg['start']), agg['minutes']
    series = {k: {int(m): c for m, c in v.items()} for k, v in agg['series'].items()}

    def total(predicate):
        out = [0] * n
        for key, values in series.items():
            parts = key.split('|')
            if predicate(parts):
                for m, c in values.items():
                    out[m] += c
        return out

    cols = {}
    w = lambda prefix, method, cohort, status, ep=None: (lambda p: p[0] == prefix and p[1] == method
                                                          and (cohort is None or p[2] == cohort)
                                                          and (status is None or p[3] == status)
                                                          and (len(p) == 5 if ep else len(p) == 4)
                                                          and (ep is None or ENDPOINT_GROUPS.get(p[4], 'meta') == ep))
    for cohort, label in [('linux-chrome-150-155', 'primary'), (None, 'all')]:
        cols[f'w_get200_{label}'] = total(w('W', 'GET', cohort, '200'))
        for flag in ('owner', 'internal'):
            cols[f'w_get200_{label}_{flag}'] = total(w('W' + flag, 'GET', cohort, '200'))
            cols[f'w_get_{label}_anystatus_{flag}'] = total(w('W' + flag, 'GET', cohort, None))
        for status in STATUSES:
            if status != '200':
                cols[f'w_get{status}_{label}'] = total(w('W', 'GET', cohort, status))
        for ep in sorted(set(ENDPOINT_GROUPS.values()) | {'meta'}):
            cols[f'w_get200_{label}_ep_{ep}'] = total(w('W', 'GET', cohort, '200', ep))
        cols[f'w_get200start_{label}'] = total(w('Wstart', 'GET', cohort, '200'))
        cols[f'w_get200start_{label}_owner'] = total(w('Wstartowner', 'GET', cohort, '200'))
        cols[f'w_get200start_{label}_internal'] = total(w('Wstartinternal', 'GET', cohort, '200'))
        cols[f'w_head_{label}'] = total(w('W', 'HEAD', cohort, None))
        cols[f'w_post_other_{label}'] = total(lambda p, c=cohort: p[0] == 'W' and p[1] in ('POST', 'OTHER') and len(p) == 4 and (c is None or p[2] == c))
    for cohort, label in COHORTS.items():
        if label != 'primary':
            cols[f'w_get200_{label}'] = total(w('W', 'GET', cohort, '200'))
    for repo in CONTROL_REPOS:
        for cohort, label in [('linux-chrome-150-155', 'primary'), (None, 'all')]:
            cols[f'r_{repo}_get200_{label}'] = total(lambda p, r=repo, c=cohort: p[0] == 'R' and p[1] == r and p[2] == 'GET' and p[4] == '200' and (c is None or p[3] == c))
            cols[f'r_{repo}_get200_{label}_owner'] = total(lambda p, r=repo, c=cohort: p[0] in ('Rowner', 'Rinternal') and p[1] == r and p[2] == 'GET' and p[4] == '200' and (c is None or p[3] == c))
        cols[f'r_{repo}_get_primary_anystatus'] = total(lambda p, r=repo: p[0] == 'R' and p[1] == r and p[2] == 'GET' and p[3] == 'linux-chrome-150-155')
    for gitpath in ('info-refs', 'upload-pack', 'receive-pack'):
        cols[f'git_website_{gitpath}'] = total(lambda p, g=gitpath: p[0] == 'G' and p[1] == 'website' and p[3] == g and p[5] == '-')
        cols[f'git_website_{gitpath}_flagged'] = total(lambda p, g=gitpath: p[0] == 'G' and p[1] == 'website' and p[3] == g and p[5] != '-')
        cols[f'git_otherrepo_{gitpath}'] = total(lambda p, g=gitpath: p[0] == 'G' and p[1] != 'website' and p[3] == g and p[5] == '-')
    for scope in ('explore', 'user-profile', 'user-feed', 'api-repo-website', 'api-repo-other', 'forge-root', 'login',
                  'pass-challenge', 'anubis', 'api-other', 'assets', 'other'):
        cols[f'f_{scope}_all'] = total(lambda p, s=scope: p[0] == 'F' and p[1] == s)
        cols[f'f_{scope}_200_primary'] = total(lambda p, s=scope: p[0] == 'F' and p[1] == s and p[3] == 'linux-chrome-150-155' and p[4] == '200')
    cols['checks_excluded'] = total(lambda p: p[0] == 'CHECK')
    repo_responses = total(lambda p: (p[0] == 'W' and len(p) == 4) or p[0] in ('R', 'G'))
    repo_5xx = total(lambda p: (p[0] == 'W' and len(p) == 4 and p[3] == '5xx') or (p[0] == 'R' and p[4] == '5xx')
                     or (p[0] == 'G' and p[4] == '5xx'))
    legacy_lines = [series.get('L|lines', {}).get(m, 0) for m in range(n)]
    json_lines = [series.get('J|lines', {}).get(m, 0) for m in range(n)]
    json_bad = [series.get('J|502-504', {}).get(m, 0) for m in range(n)]

    # Coverage.
    spans = defaultdict(list)
    for s in agg['sources']:
        spans['legacy' if s['kind'] == 'legacy' else 'json'].append((ts(s['first_time']), ts(s['last_time'])))
    for kind in spans:
        spans[kind].sort()
    gaps = []
    for kind, items in spans.items():
        for (a0, a1), (b0, b1) in zip(items, items[1:]):
            if b0 - a1 > 60:
                gaps.append((a1, b0, f'{kind}-rotation-gap'))
    reason = [''] * n
    regime = [''] * n
    lines = [0] * n
    for m in range(n):
        t0, t1 = start + 60 * m, start + 60 * (m + 1)
        if t1 <= JSON_FIRST:
            regime[m], lines[m] = 'legacy', legacy_lines[m]
            inside = any(a <= t0 and t1 - 1 <= b for a, b in spans['legacy'])
        elif t0 >= JSON_FIRST:
            regime[m], lines[m] = 'json', json_lines[m]
            inside = any(a - 60 <= t0 and t1 - 1 <= b + 60 for a, b in spans['json'])
        else:
            regime[m], lines[m], inside = 'mixed', legacy_lines[m] + json_lines[m], True
            reason[m] = 'regime-change-minute'
        if not inside and not reason[m]:
            reason[m] = 'outside-archive-span'
        for a, b, label in gaps:
            if t1 > a and t0 < b and not reason[m]:
                reason[m] = label
        for a, b, label in DISRUPTIONS:
            if t1 > ts(a) and t0 < ts(b) and not reason[m]:
                reason[m] = 'disruption:' + label
        if repo_responses[m] >= 5 and repo_5xx[m] * 2 >= repo_responses[m] and not reason[m]:
            reason[m] = 'repository-5xx-majority'
        if json_bad[m] >= 5 and json_bad[m] * 2 >= json_lines[m] and not reason[m]:
            reason[m] = 'forge-502-504-majority'
    # Quiet runs: >=10 zero-line minutes where the surrounding six hours average >=5 lines per minute.
    m = 0
    quiet = []
    while m < n:
        if lines[m] == 0:
            k = m
            while k < n and lines[k] == 0:
                k += 1
            if k - m >= 10:
                lo, hi = max(0, m - 180), min(n, k + 180)
                rate = sum(lines[lo:hi]) / max(1, (hi - lo) - (k - m))
                if rate >= 5:
                    quiet.append((m, k, rate))
                    for j in range(m, k):
                        reason[j] = reason[j] or 'quiet-gap'
            m = k
        else:
            m += 1

    # Archive-route switch (A7): last 200 and first 404 on website archive routes, 2026-10-01 19:00 to 2026-10-02 12:00.
    lo, hi = int((ts('2026-10-01T19:00:00Z') - start) // 60), int((ts('2026-10-02T12:00:00Z') - start) // 60)
    arch200 = [m for m in range(lo, hi) if total_cache(series, 'archive', '200').get(m)]
    arch404 = [m for m in range(lo, hi) if total_cache(series, 'archive', '404').get(m)]
    switch = None
    if arch404:
        first404 = min(arch404)
        last200 = max([m for m in arch200 if m < max(arch404)] or [first404])
        switch = {'last_200_before_last_404_minute': iso(start + 60 * last200), 'first_404_minute': iso(start + 60 * first404),
                  'archive_200_minutes_after_first_404': sum(1 for m in arch200 if m > first404)}
        a, b = min(last200, first404) - 10, max(last200, first404) + 10
        for j in range(max(0, a), min(n, b + 1)):
            reason[j] = reason[j] or 'disruption:archive-route-switch'

    out = HERE / 'data'
    names = list(cols)
    with gzip.open(out / 'minute-series.csv.gz', 'wt', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['minute_utc', 'regime', 'phase', 'covered', 'coverage_reason', 'log_lines'] + names)
        for m in range(n):
            t = start + 60 * m
            writer.writerow([iso(t), regime[m], phase(t), int(not reason[m]), reason[m], lines[m]]
                            + [('' if (name.startswith(('w_get200start', 'f_')) and regime[m] == 'legacy') else cols[name][m]) for name in names])
    with gzip.open(out / 'hash-requests.csv.gz', 'wt', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['hex', 'position', 'cohort', 'status', 'method', 'minute_utc', 'flag', 'requests'])
        for hexs, position, cohort, status, method, minute, flag, count in agg['hash_rows']:
            writer.writerow([hexs, position, cohort, status, method, iso(start + 60 * minute), flag, count])
    coverage = {
        'start': agg['start'], 'end_exclusive': agg['end_exclusive'], 'minutes': n,
        'uncovered_minutes_by_reason': dict(Counter(r for r in reason if r)),
        'rotation_gaps_over_60s': [[iso(a), iso(b), label] for a, b, label in gaps],
        'quiet_gaps': [[iso(start + 60 * a), iso(start + 60 * b), round(rate, 1)] for a, b, rate in quiet],
        'archive_route_switch': switch,
        'disruptions': DISRUPTIONS,
        'rules': 'amendments.json A6/A7',
    }
    (out / 'coverage.json').write_text(json.dumps(coverage, indent=1) + '\n')
    meta = {k: agg[k] for k in ('generated_at', 'start', 'end_exclusive', 'minutes', 'json_first', 'sources', 'per_archive', 'diagnostics', 'owner')}
    meta['series_keys'] = len(series)
    meta['hash_rows'] = len(agg['hash_rows'])
    meta['column_totals'] = {name: sum(cols[name]) for name in names}
    (out / 'aggregation-meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    print(json.dumps(coverage, indent=1)[:4000])


_cache = {}


def total_cache(series, ep, status):
    key = (ep, status)
    if key not in _cache:
        acc = Counter()
        for k, values in series.items():
            p = k.split('|')
            if p[0] == 'W' and len(p) == 5 and p[1] == 'GET' and p[3] == status and p[4] == ep:
                acc.update(values)
        _cache[key] = acc
    return _cache[key]


def iso(t):
    return dt.datetime.fromtimestamp(t, UTC).isoformat().replace('+00:00', 'Z')


if __name__ == '__main__':
    main(sys.argv[1])
