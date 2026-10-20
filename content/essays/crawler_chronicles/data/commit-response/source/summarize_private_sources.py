#!/usr/bin/env python3
"""Reduce run_private_sources.sh output (stdin) to reviewed aggregates: no pseudonyms.

Usage: source/run_private_sources.sh | python3 source/summarize_private_sources.py
Writes results/young-fetch-sources.json.
"""
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
d = json.load(sys.stdin)
src, events = d['sources'], d['events']


def label_class(label):
    return label if label.startswith('declared:') else 'browser-like:' + label


out = {'generated_at_private_run': d['generated_at'], 'young_window_hours': d['young_seconds'] / 3600,
       'definition': 'GET or HEAD naming a current commit within the window after its first Forgejo publication; '
                     'declared tokens and browser families are user-agent claims; sources are addresses, not operators',
       'by_lag': {}}
for limit, name in ((60, 'under_60_min'), (360, 'under_6_h'), (1440, 'under_24_h')):
    sel = [e for e in events if e['age_bin_min'] < limit and e['method'] == 'GET']
    per = defaultdict(Counter)
    for e in sel:
        s = src[e['source']]
        key = (e['episode'], e['cohort'], label_class(e['ua_label']), e['referer'],
               'seen-before-publication' if s['seen_on_repository_before_publication'] else 'new-to-repository',
               'owner-signal' if s['owner_signal_any_date'] else 'no-owner-signal')
        per[key]['requests'] += e['requests']
        per[key]['tip_requests'] += e['requests'] if e['tip'] else 0
    sources_per_key = defaultdict(set)
    for e in sel:
        s = src[e['source']]
        key = (e['episode'], e['cohort'], label_class(e['ua_label']), e['referer'],
               'seen-before-publication' if s['seen_on_repository_before_publication'] else 'new-to-repository',
               'owner-signal' if s['owner_signal_any_date'] else 'no-owner-signal')
        sources_per_key[key].add(e['source'])
    out['by_lag'][name] = {
        'get_requests': sum(e['requests'] for e in sel),
        'sources': len({e['source'] for e in sel}),
        'episodes': sorted({e['episode'] for e in sel}),
        'owner_signal_sources': len({e['source'] for e in sel if src[e['source']]['owner_signal_any_date']}),
        'rows': [dict(zip(('episode', 'cohort', 'user_agent_claim', 'referer', 'source_history', 'owner'), k),
                      requests=v['requests'], tip_requests=v['tip_requests'], sources=len(sources_per_key[k]))
                 for k, v in sorted(per.items())] if limit <= 360 else 'omitted (see by_cohort)',
        'by_cohort': {c: {'requests': sum(e['requests'] for e in sel if e['cohort'] == c),
                          'sources': len({e['source'] for e in sel if e['cohort'] == c})}
                      for c in sorted({e['cohort'] for e in sel})},
    }
prim = [e for e in events if e['cohort'] == 'linux-chrome-150-155']
psrc = {e['source'] for e in prim}
req_per = [src[s]['repository_requests_total'] for s in psrc]
out['primary_cohort_young_fetches'] = {
    'episodes': sorted({e['episode'] for e in prim}), 'tip_only': all(e['tip'] for e in prim),
    'requests': sum(e['requests'] for e in prim), 'sources': len(psrc),
    'sources_new_to_repository_at_first_young_fetch': sum(not src[s]['seen_on_repository_before_publication'] for s in psrc),
    'median_total_repository_requests_per_source': statistics.median(req_per) if req_per else None,
    'max_total_repository_requests_per_source': max(req_per) if req_per else None,
    'status_counts': dict(Counter(e['status'] for e in prim for _ in range(e['requests']))),
    'referer_of_200s': dict(Counter(e['referer'] for e in prim if e['status'] == '200' for _ in range(e['requests']))),
    'referer_of_403s': dict(Counter(e['referer'] for e in prim if e['status'] == '403' for _ in range(e['requests']))),
    'earliest_lag_minutes_bin': min(e['age_bin_min'] for e in prim) if prim else None,
}
(HERE / 'results/young-fetch-sources.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps({k: (v if k != 'by_lag' else {kk: {x: y for x, y in vv.items() if x != 'rows'} for kk, vv in v.items()}) for k, v in out.items()}, indent=1))
