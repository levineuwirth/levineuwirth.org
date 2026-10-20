#!/usr/bin/env python3
"""Detectable effect sizes for the planned test on the observed request series.

Placebo push trains are drawn from the rotation null (the eligible blocks, each
rotated by a random shift), a response is planted into a copy of the real
primary series in minutes +1..+10 after each placebo push, and the planned
test is run against its own rotation null. The real series keeps its bursts,
trends and any genuine response, so this is a dependence-preserving check.
It measures detection of added request volume under this injection model only:
not hash-specific behavior, and not a general family of monitoring mechanisms.
A per-novel-commit size k plants an expected k requests per commit (Poisson).
Also reports zero-event binomial bounds as an illustration only: they assume
independent opportunities with a common probability, which clustered pushes
and crawler campaigns do not establish. Writes results/power.json.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commitstats as cs  # noqa: E402
from analysis import Study, SEED  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
REPS = 300
DRAWS = 999


def simulate(st, y, chosen, add, rng, per_commit=False):
    blocks = cs.blocks_for([e['pos'] for e in chosen])
    rot = cs.Rotation(blocks)
    # rot.positions() keeps the block and within-block order of the episodes sorted by position.
    weights = np.array([int(e['novel_commits']) for e in sorted(chosen, key=lambda e: e['pos'])], dtype=float)
    hits = 0
    for r in range(REPS):
        shifts = rng.integers(0, 60, size=len(blocks))
        placebo = rot.positions(shifts)
        z = y.copy()
        amount = add * (weights if per_commit else np.ones(len(placebo)))
        for p, a in zip(placebo, amount):
            z[p + 1:p + 11] += rng.poisson(a / 10, 10)
        res = cs.rotation_test(cs.cumulative(z), cs.blocks_for(list(placebo)), 30, DRAWS, int(rng.integers(1 << 31)))
        hits += res['p'] <= 0.05
    return hits / REPS


def upper95(successes, trials):
    """Exact one-sided 95% upper bound for a binomial proportion with zero successes."""
    assert successes == 0
    return 1 - 0.05 ** (1 / trials)


def main():
    st = Study()
    y = st.series('w_get200_primary')
    chosen = st.select(30)
    rng = np.random.default_rng(SEED)
    out = {'reps': REPS, 'draws_per_test': DRAWS, 'window': 30, 'episodes': len(chosen),
           'planted_minutes': '+1..+10 after each placebo push, Poisson; per-commit sizes are expected counts',
           'power_added_requests_per_episode': {}, 'power_added_requests_per_novel_commit': {}}
    out['false_positive_rate_no_injection'] = simulate(st, y, chosen, 0, rng)
    for add in (2, 5, 10, 20, 40):
        out['power_added_requests_per_episode'][str(add)] = simulate(st, y, chosen, add, rng)
    for k in (0.5, 1, 2, 5):
        out['power_added_requests_per_novel_commit'][str(k)] = simulate(st, y, chosen, k, rng, per_commit=True)
    d2 = [e for e in chosen if e['phase'] == 'difficulty-2']
    out['difficulty2_only'] = {str(add): simulate(st, y, d2, add, rng) for add in (5, 10, 20)}
    # Review addition: only the episodes on dates when the cohort was active on this repository.
    active_test = [e for e in chosen if e['date_utc'] >= '2026-10-06']
    out['cohort_active_oct6_13_only'] = {'episodes': len(active_test), 'dates': len({e['date_utc'] for e in active_test}),
                                         **{str(add): simulate(st, y, active_test, add, rng) for add in (5, 10, 20, 40)}}
    first = [r for r in csv.DictReader(open(HERE / 'results/first-fetch-by-episode.csv')) if r['in_study'] == 'True']
    no_deploy_day = [r for r in first if r['phase'] != 'anubis-deployment-day']
    active = [r for r in first if r['time_utc'] >= '2026-10-06']
    fast = lambda rows: sum(int(r['primary_fetched_within_1h']) > 0 for r in rows)
    commits = sum(int(r['novel_commits']) for r in first)
    out['illustrative_binomial_model'] = {
        'assumption': 'independent opportunities with one common probability; not established for clustered pushes, '
                      'crawler campaigns, or dates when the cohort was absent. Illustration only, not an inferential bound.',
        'study_episodes_including_anubis_day': {'episodes': len(first), 'with_primary_fetch_within_1h': fast(first),
                                                'zero_event_upper95': round(upper95(fast(first), len(first)), 4)},
        'study_episodes_excluding_anubis_day': {'episodes': len(no_deploy_day), 'with_primary_fetch_within_1h': fast(no_deploy_day),
                                                'zero_event_upper95': round(upper95(fast(no_deploy_day), len(no_deploy_day)), 4)},
        'cohort_active_oct6_13': {'episodes': len(active), 'with_primary_fetch_within_1h': fast(active),
                                  'zero_event_upper95': round(upper95(fast(active), len(active)), 4)},
        'study_commits_batched_not_independent': {'commits': commits, 'zero_event_upper95': round(upper95(0, commits), 4)},
    }
    (HERE / 'results/power.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
