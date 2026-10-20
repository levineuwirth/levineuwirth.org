#!/usr/bin/env python3
"""What was fetched: requests naming a commit, relative to that commit's publication.

Reads data/hash-requests.csv.gz, data/commit-publication.csv,
data/publication-episodes.csv and data/publication-snapshot.json. Writes
results/hash-results.json, results/first-fetch-by-episode.csv,
results/requested-age-by-day.csv and results/request-target-hourly.csv.
A fetch attempt is a GET naming the commit in a semantic position, any status
(a 403 is a challenge or denial, still an attempt on that URL).
"""
import csv
import datetime as dt
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commitstats as cs  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
UTC = dt.timezone.utc
END = dt.datetime(2026, 10, 19, 22, tzinfo=UTC).timestamp()
STUDY_START = dt.datetime(2026, 10, 1, tzinfo=UTC).timestamp()
COHORTS = {'any': None, 'primary': 'linux-chrome-150-155', 'declared-other': 'other-declared-crawler',
           'amazon': 'amazon-declared', 'meta': 'meta-declared', 'other': 'other'}
AGE_BINS = [(0, 1, '<1h'), (1, 6, '1-6h'), (6, 24, '6-24h'), (24, 72, '1-3d'), (72, 168, '3-7d'), (168, 1e9, '>7d')]


def ts(text):
    return dt.datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()


def age_label(hours):
    for lo, hi, label in AGE_BINS:
        if lo <= hours < hi:
            return label


def main():
    snap = json.loads((HERE / 'data/publication-snapshot.json').read_text())
    current = sorted(snap['commits'])
    old = set()
    for a in snap['actions']:
        for key in ('compare_old', 'compare_new', 'head_sha'):
            if a.get(key) and a[key] not in snap['commits']:
                old.add(a[key])
        old.update(c['sha'] for c in a.get('listed_commits', []) if c['sha'] not in snap['commits'])
    old = sorted(old)
    pub = {r['sha']: r for r in csv.DictReader(open(HERE / 'data/commit-publication.csv'))}
    episodes = {r['episode']: r for r in csv.DictReader(open(HERE / 'data/publication-episodes.csv'))}
    tips = {s for e in episodes.values() for s in e['new_tips'].split()}
    timing = {r['episode']: r for r in csv.DictReader(open(HERE / 'results/episode-windows.csv'))} if (HERE / 'results/episode-windows.csv').exists() else {}

    cache = {}

    def resolve(h):
        if h not in cache:
            a = [s for s in current if s.startswith(h)]
            b = [s for s in old if s.startswith(h)]
            if len(a) + len(b) > 1:
                cache[h] = ('ambiguous', None)
            elif a:
                cache[h] = ('current', a[0])
            elif b:
                cache[h] = ('rewritten-history-listed', b[0])
            else:
                cache[h] = ('unresolved', None)
        return cache[h]

    resolution = Counter()
    resolution_status = Counter()
    first = defaultdict(dict)               # sha -> cohort label -> first minute (seconds)
    pre_publication = Counter()
    by_day_age = Counter()
    target_hourly = Counter()
    rate_num = Counter()
    head_vs_get = Counter()
    youngest_start, older_than_7d_at_start = float('inf'), 0
    for r in csv.DictReader(gzip.open(HERE / 'data/hash-requests.csv.gz', 'rt')):
        n = int(r['requests'])
        head_vs_get[r['method']] += n
        if r['method'] != 'GET':
            continue
        kind, sha = resolve(r['hex'])
        resolution[kind] += n
        resolution_status[(kind, r['cohort'], r['status'])] += n
        t = ts(r['minute_utc'])
        day = r['minute_utc'][:10]
        if kind != 'current':
            unresolved_status = 'unresolved-404' if r['status'] == '404' else 'unresolved-other'
            by_day_age[(day, r['cohort'], kind if kind != 'unresolved' else unresolved_status)] += n
            continue
        published = float(pub[sha]['first_forgejo_unix'])
        age = (t + 30 - published) / 3600          # minute midpoint
        if t + 60 <= published:
            pre_publication[(sha, r['cohort'], r['status'])] += n
            continue
        by_day_age[(day, r['cohort'], age_label(max(age, 0)))] += n
        target_hourly[(r['minute_utc'][:13], pub[sha]['episode'], r['cohort'])] += n
        for label, cohort in COHORTS.items():
            if cohort is None or r['cohort'] == cohort:
                if label not in first[sha] or t < first[sha][label]:
                    first[sha][label] = t
        if r['cohort'] == 'linux-chrome-150-155':
            rate_num[(r['minute_utc'][:13], age_label(max(age, 0)))] += n
            start_age = (t - published) / 3600          # age at the start of the request minute
            youngest_start = min(youngest_start, start_age)
            older_than_7d_at_start += n if start_age >= 168 else 0

    # First fetch by episode.
    rows = []
    for ep_id, ep in sorted(episodes.items()):
        if ts(ep['time_utc']) < dt.datetime(2026, 9, 29, tzinfo=UTC).timestamp():
            continue
        shas = [s for s, p in pub.items() if p['episode'] == ep_id]
        t0 = float(ep['time_unix'])
        row = {'episode': ep_id, 'time_utc': ep['time_utc'], 'phase': ep['phase'], 'novel_commits': len(shas),
               'in_study': t0 >= STUDY_START, 'in_primary_test': timing.get(ep_id, {}).get('in_primary', ''),
               'github_first_novel_lead_s': ep['github_first_novel_lead_s']}
        for label in COHORTS:
            lags = sorted((first[s][label] - t0) / 3600 for s in shas if label in first[s])
            for h in (1, 6, 24):
                row[f'{label}_fetched_within_{h}h'] = sum(x < h for x in lags)
            row[f'{label}_fetched_by_end'] = len(lags)
            row[f'{label}_first_lag_h'] = round(lags[0], 2) if lags else ''
            tip_lags = [(first[s][label] - t0) / 3600 for s in shas if s in tips and label in first[s]]
            row[f'{label}_tip_first_lag_h'] = round(min(tip_lags), 2) if tip_lags else ''
        rows.append(row)
    out = HERE / 'results'
    with open(out / 'first-fetch-by-episode.csv', 'w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with open(out / 'requested-age-by-day.csv', 'w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['date_utc', 'cohort', 'target_age_or_class', 'get_requests'])
        for key, n in sorted(by_day_age.items()):
            writer.writerow([*key, n])
    with open(out / 'request-target-hourly.csv', 'w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['hour_utc', 'target_episode', 'target_published_utc', 'cohort', 'get_requests'])
        for (hour, ep_id, cohort), n in sorted(target_hourly.items()):
            writer.writerow([hour, ep_id, episodes[ep_id]['time_utc'], cohort, n])

    # Time to first fetch for commits first published in the study window, censored at END.
    study_commits = [s for s, p in pub.items() if float(p['first_forgejo_unix']) >= STUDY_START]
    survival = {}
    for label in ('any', 'primary', 'declared-other', 'other'):
        durations, observed = [], []
        for s in study_commits:
            t0 = float(pub[s]['first_forgejo_unix'])
            if label in first[s]:
                durations.append(max(first[s][label] - t0, 0) / 3600)
                observed.append(True)
            else:
                durations.append((END - t0) / 3600)
                observed.append(False)
        times, surv = cs.kaplan_meier(durations, observed)
        survival[label] = {f'fetched_by_{h}h': round(1 - cs.km_at(times, surv, h), 4) for h in (1, 6, 24, 72, 168)}
        survival[label]['fetched_by_end'] = int(sum(observed))
    # Per-commit request rate by age, primary cohort, over hours with any primary commit request.
    # Exposure: minutes of each active hour that each published commit spends in each age bin.
    active_hours = sorted({h for h, _ in rate_num})
    pairs, hits = Counter(), Counter()
    for (hour, label), n in rate_num.items():
        hits[label] += n
    for hour in active_hours:
        h0 = ts(hour + ':00:00Z')
        for s, p in pub.items():
            a0 = (h0 - float(p['first_forgejo_unix'])) / 3600
            for lo, hi, label in AGE_BINS:
                overlap = min(a0 + 1, hi) - max(a0, lo, 0)
                if overlap > 0:
                    pairs[label] += overlap
    rate = {label: {'commit_hours': pairs[label], 'requests': hits[label],
                    'requests_per_commit_hour': round(hits[label] / pairs[label], 4) if pairs[label] else None}
            | {'commit_hours': round(pairs[label], 1)}
            for _, _, label in AGE_BINS}
    primary_total = sum(n for (d, c, a), n in by_day_age.items() if c == 'linux-chrome-150-155' and a in {x[2] for x in AGE_BINS})
    non_current = {}
    for kind in ('rewritten-history-listed', 'unresolved'):
        statuses = Counter()
        for (k, cohort, status), n in resolution_status.items():
            if k == kind:
                statuses[status] += n
        non_current[kind] = {'get_requests': sum(statuses.values()), 'by_status': dict(statuses)}
    non_current['note'] = ('rewritten-history-listed: hashes named in pre-rewrite push notifications (objects removed). '
                           'unresolved: no match in the current graph or that list; not shown to be removed history.')
    results = {
        'definition': 'GET naming a commit in a semantic path position, any status; HEAD excluded (paired HEAD/GET by one declared crawler)',
        'methods_in_hash_positions': dict(head_vs_get),
        'resolution_get_requests': dict(resolution),
        'resolution_by_cohort_status': {'|'.join(k): v for k, v in sorted(resolution_status.items())},
        'requests_before_publication': {'|'.join(map(str, k)): v for k, v in pre_publication.items()},
        'study_novel_commits': len(study_commits),
        'time_to_first_fetch_km': survival,
        'primary_cohort_requests_to_current_commits': primary_total,
        'non_current_hash_requests': non_current,
        'age_binning': 'Ages use the request-minute midpoint (completion time, minute resolution).',
        'primary_cohort_youngest_target_age_hours_at_minute_start': round(youngest_start, 4),
        'primary_cohort_requests_older_than_7d_at_minute_start': older_than_7d_at_start,
        'primary_cohort_requests_by_target_age': {a: sum(n for (d, c, aa), n in by_day_age.items() if c == 'linux-chrome-150-155' and aa == a) for _, _, a in AGE_BINS},
        'primary_cohort_rate_by_age_active_hours': rate,
        'primary_cohort_active_hours': len(active_hours),
        'primary_cohort_latest_target_episode': max((pub[s]['episode'] for s in pub if 'primary' in first[s]), default=None),
        'episodes_with_primary_fetch_within_1h': sum(r['primary_fetched_within_1h'] > 0 for r in rows if r['in_study']),
        'episodes_with_any_fetch_within_1h': [r['episode'] for r in rows if r['in_study'] and r['any_fetched_within_1h'] > 0],
    }
    (out / 'hash-results.json').write_text(json.dumps(results, indent=1) + '\n')
    print(json.dumps({k: v for k, v in results.items() if k != 'resolution_by_cohort_status'}, indent=1))


if __name__ == '__main__':
    main()
