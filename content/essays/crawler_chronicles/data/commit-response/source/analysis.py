#!/usr/bin/env python3
"""Timing tests: planned (analysis-plan.json), amended (amendments.json) and exploratory.

Reads data/minute-series.csv.gz and data/publication-episodes.csv; writes
results/timing-results.json and results/episode-windows.csv.
Requires numpy. Seeds are fixed; reruns reproduce every number.
"""
import csv
import datetime as dt
import gzip
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commitstats as cs  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
UTC = dt.timezone.utc
SEED = 20261020
DRAWS = 10000
STUDY_START = '2026-10-01T00:00:00Z'
STABLE = {'before-anubis', 'difficulty-2'}
STATUSES = ['200', '2xx', '3xx', '403', '404', '429', '499', '4xx', '5xx']
CONTROL_REPOS = ['pmacs', 'epiphany', 'levcs', 'ozymandias', 'where-simd-helps', 'neuropose', 'beyond_comorbidity_indices', 'unknown-repo']


def ts(text):
    return dt.datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()


def load():
    with gzip.open(HERE / 'data/minute-series.csv.gz', 'rt') as stream:
        rows = list(csv.DictReader(stream))
    origin = ts(rows[0]['minute_utc'])
    cols = {k: np.array([int(r[k]) if r[k] != '' else -1 for r in rows]) for k in rows[0]
            if k not in ('minute_utc', 'regime', 'phase', 'coverage_reason')}
    meta = {k: np.array([r[k] for r in rows]) for k in ('minute_utc', 'regime', 'phase', 'coverage_reason')}
    episodes = list(csv.DictReader(open(HERE / 'data/publication-episodes.csv')))
    return origin, cols, meta, episodes


class Study:
    def __init__(self):
        self.origin, self.cols, self.meta, all_episodes = load()
        self.n = len(self.meta['minute_utc'])
        self.covered = self.cols['covered'] == 1
        self.all_episodes = [dict(e, pos=int((ts(e['minute_utc']) - self.origin) // 60)) for e in all_episodes
                             if self.origin <= ts(e['minute_utc']) < self.origin + 60 * self.n]
        self.episodes = [e for e in self.all_episodes if ts(e['minute_utc']) >= ts(STUDY_START)]

    def series(self, *names, minus=()):
        y = sum(self.cols[n].clip(min=0) for n in names)
        for n in minus:
            y = y - self.cols[n].clip(min=0)
        return y

    def block_ok(self, start, w, relax_regime=False, phases=STABLE):
        lo, hi = start - w, start + 60 + w
        if lo < 0 or hi > self.n or not self.covered[lo:hi].all():
            return False
        ph = set(self.meta['phase'][lo:hi])
        if len(ph) != 1 or not ph <= phases:
            return False
        if not relax_regime:
            regimes = set(self.meta['regime'][lo:hi])
            if len(regimes) != 1:
                return False
        return True

    def select(self, w, origin=0, relax_regime=False, phases=STABLE, keep=lambda e: True, literal=False):
        chosen = []
        for e in self.episodes:
            start = origin + 60 * ((e['pos'] - origin) // 60)
            if keep(e) and self.block_ok(start, w, relax_regime, phases):
                chosen.extend([e] * (int(e['ref_updates']) if literal else 1))
        return chosen

    def test(self, y, w, chosen, origin=0, stat=cs.diff_stat, seed=SEED, draws=DRAWS):
        if not chosen:
            return {'episodes': 0}
        c = cs.cumulative(y)
        blocks = cs.blocks_for([e['pos'] for e in chosen], origin)
        out = cs.rotation_test(c, blocks, w, draws, seed, stat)
        out['episode_ids'] = sorted({e['episode'] for e in chosen})
        out['dates'] = sorted({e['date_utc'] for e in chosen})
        post, pre = cs.windows(c, np.array(sorted(e['pos'] for e in chosen)), w)
        out['sum_pre'], out['sum_post'] = int(pre.sum()), int(post.sum())
        out['episodes_post_gt_pre'] = int((post > pre).sum())
        out['episodes_post_lt_pre'] = int((post < pre).sum())
        return out


def clean(result):
    return {k: v for k, v in result.items() if k not in ('null', 'per_episode_excess')}


def main():
    st = Study()
    results = {'seed': SEED, 'draws': DRAWS, 'numpy': np.__version__}
    primary_y = st.series('w_get200_primary')
    W = 30

    # Minute-of-hour of all study episodes (A11b), before any test.
    minutes = [int(e['minute_utc'][14:16]) for e in st.episodes]
    results['episode_minute_of_hour'] = {'counts_by_quarter': [sum(q * 15 <= m < q * 15 + 15 for m in minutes) for q in range(4)],
                                         'minutes': sorted(minutes)}

    # Eligibility inventory.
    inventory = []
    for e in st.episodes:
        start = 60 * (e['pos'] // 60)
        inventory.append({'episode': e['episode'], 'minute_utc': e['minute_utc'], 'phase': e['phase'],
                          **{f'eligible_w{w}': st.block_ok(start, w) for w in (5, 30, 60, 180)},
                          'eligible_w30_offset_blocks': st.block_ok(30 + 60 * ((e['pos'] - 30) // 60), 30),
                          'eligible_w30_relaxed_regime': st.block_ok(start, 30, relax_regime=True)})
    results['eligibility'] = inventory

    # PLANNED PRIMARY (with A3 episodes and A6 eligibility).
    chosen = st.select(W)
    primary = st.test(primary_y, W, chosen)
    results['planned_primary'] = clean(primary)
    ids = cs.clusters(np.array([e['pos'] for e in sorted(chosen, key=lambda e: e['pos'])]), W)
    excess = primary['per_episode_excess']
    results['planned_primary']['excess_ci95_episode_cluster_bootstrap'] = cs.cluster_bootstrap(excess, ids, 10000, SEED)
    results['planned_primary']['clusters'] = int(ids.max() + 1)
    # Review sensitivity: resample whole UTC dates (few clusters; not a validated 95% guarantee).
    dates = [e['date_utc'] for e in sorted(chosen, key=lambda e: e['pos'])]
    date_ids = np.array([sorted(set(dates)).index(d) for d in dates])
    results['planned_primary']['excess_ci95_date_cluster_bootstrap'] = cs.cluster_bootstrap(excess, date_ids, 10000, SEED)
    results['planned_primary']['date_clusters'] = len(set(dates))
    results['planned_primary']['estimands'] = {
        'observed': 'raw mean post-minus-pre per episode', 'null_mean_exact': 'expected raw difference over rotations',
        'excess': 'observed minus null_mean_exact (rotation-adjusted); the bootstrap intervals are for this'}
    # Plan-literal: each ref update its own batch.
    results['plan_literal_ref_updates'] = clean(st.test(primary_y, W, st.select(W, literal=True)))

    # Leave one date out.
    lodo = {}
    for d in primary['dates']:
        r = st.test(primary_y, W, [e for e in chosen if e['date_utc'] != d])
        lodo[d] = {'raw_observed': r['observed'], 'adjusted_excess': r['excess'], 'p': r['p'], 'episodes': r['episodes']}
    results['planned_primary_leave_one_date_out'] = lodo

    # PLANNED SENSITIVITIES.
    all_pos = sorted(e['pos'] for e in st.all_episodes)
    isolated = lambda e: all(abs(p - e['pos']) > 60 for p in all_pos if p != e['pos'])
    sens = {}
    sens['isolated_60min'] = clean(st.test(primary_y, W, st.select(W, keep=isolated)))
    sens['all_agents_200'] = clean(st.test(st.series('w_get200_all'), W, chosen))
    sens['primary_all_statuses_get'] = clean(st.test(st.series(*[f'w_get{s}_primary' for s in STATUSES]), W, chosen))
    sens['control_other_repositories_primary_200'] = clean(st.test(st.series(*[f'r_{r}_get200_primary' for r in CONTROL_REPOS]), W, chosen))
    sens['control_other_repositories_all_200'] = clean(st.test(st.series(*[f'r_{r}_get200_all' for r in CONTROL_REPOS]), W, chosen))
    for ph in sorted(STABLE):
        sens[f'phase_{ph}'] = clean(st.test(primary_y, W, [e for e in chosen if e['phase'] == ph]))
        sens[f'phase_{ph}_all_agents_200'] = clean(st.test(st.series('w_get200_all'), W, [e for e in chosen if e['phase'] == ph]))
    windows = {}
    for w in (5, 60, 180):
        windows[w] = clean(st.test(primary_y, w, st.select(w)))
    adjusted = cs.holm([windows[w]['p'] for w in (5, 60, 180)])
    for w, a in zip((5, 60, 180), adjusted):
        windows[w]['p_holm'] = float(a)
    sens['windows'] = {str(k): v for k, v in windows.items()}
    results['planned_sensitivities'] = sens

    # AMENDED ANALYSES.
    am = {}
    am['owner_internal_removed'] = clean(st.test(st.series('w_get200_primary', minus=('w_get200_primary_owner', 'w_get200_primary_internal')), W, chosen))
    am['all_agents_owner_internal_removed'] = clean(st.test(st.series('w_get200_all', minus=('w_get200_all_owner', 'w_get200_all_internal')), W, chosen))
    am['github_preceded_removed'] = clean(st.test(primary_y, W, st.select(W, keep=lambda e: e['github_first_novel_lead_s'] == '')))
    json_chosen = [e for e in chosen if e['log_regime'] == 'forge-json']
    am['json_era_completion_time'] = clean(st.test(primary_y, W, json_chosen))
    am['json_era_start_time'] = clean(st.test(st.series('w_get200start_primary'), W, json_chosen))
    am['offset_blocks_30'] = clean(st.test(primary_y, W, st.select(W, origin=30), origin=30))
    am['relaxed_regime'] = clean(st.test(primary_y, W, st.select(W, relax_regime=True)))
    am['robust_share_post_gt_pre'] = clean(st.test(primary_y, W, chosen, stat=cs.positive_stat))
    am['robust_mean_log_ratio'] = clean(st.test(primary_y, W, chosen, stat=cs.logratio_stat))
    am['robust_mean_log_ratio_all_agents'] = clean(st.test(st.series('w_get200_all'), W, chosen, stat=cs.logratio_stat))
    am['batch_size_weighted_episode_mean'] = weighted(st, primary_y, W, chosen)
    # Aggregate requests per novel commit, sum(D) / sum(n): a fixed rescaling of the primary statistic, same p.
    k_novel = sum(int(e['novel_commits']) for e in chosen)
    am['per_novel_commit_aggregate'] = {
        'raw_observed': primary['observed'] * primary['episodes'] / k_novel,
        'adjusted_excess': primary['excess'] * primary['episodes'] / k_novel,
        'p': primary['p'], 'episodes': primary['episodes'], 'novel_commits': k_novel,
        'note': 'Not an independent result: the primary statistic times episodes / novel commits.'}
    active = [e for e in chosen if e['date_utc'] >= '2026-10-06']
    am['post_review_cohort_active_oct6_13'] = clean(st.test(primary_y, W, active))
    am['time_of_day_referents'] = referents(st, primary_y, W, chosen)
    am['time_of_day_referents_all_agents'] = referents(st, st.series('w_get200_all'), W, chosen)
    results['amended'] = am

    # EXPLORATORY: endpoints and other outcome families.
    ex = {}
    for name in ('src-commit', 'history-commit', 'blame', 'raw-commit', 'commit', 'src-branch', 'history-branch', 'raw-branch', 'root', 'feed'):
        ex[f'endpoint_{name}_primary_200'] = clean(st.test(st.series(f'w_get200_primary_ep_{name}'), W, chosen))
    ex['git_upload_pack_unflagged'] = clean(st.test(st.series('git_website_info-refs', 'git_website_upload-pack'), W, chosen))
    ex['primary_403'] = clean(st.test(st.series('w_get403_primary'), W, chosen))
    for scope in ('explore', 'user-profile', 'user-feed', 'api-repo-website', 'forge-root'):
        ex[f'forge_{scope}_all_statuses'] = clean(st.test(st.series(f'f_{scope}_all'), W, json_chosen))
    for cohort in ('meta', 'amazon', 'otherbot', 'other'):
        ex[f'cohort_{cohort}_200'] = clean(st.test(st.series(f'w_get200_{cohort}'), W, chosen))
    results['exploratory'] = ex

    # Per-episode table (primary series, W=30 and W=180).
    c = cs.cumulative(primary_y)
    c_all = cs.cumulative(st.series('w_get200_all'))
    rows = []
    chosen_ids = {e['episode'] for e in chosen}
    excess_by_id = dict(zip([e['episode'] for e in sorted(chosen, key=lambda e: e['pos'])], excess))
    for e in st.episodes:
        p = e['pos']
        row = {'episode': e['episode'], 'minute_utc': e['minute_utc'], 'date_utc': e['date_utc'], 'phase': e['phase'],
               'novel_commits': e['novel_commits'], 'refs': e['refs'], 'in_primary': e['episode'] in chosen_ids,
               'github_first_novel_lead_s': e['github_first_novel_lead_s']}
        for w in (30, 180):
            if p - w >= 0 and p + w < st.n:
                post, pre = cs.windows(c, np.array([p]), w)
                pa, pr = cs.windows(c_all, np.array([p]), w)
                row.update({f'pre{w}_primary': int(pre[0]), f'post{w}_primary': int(post[0]),
                            f'pre{w}_all': int(pr[0]), f'post{w}_all': int(pa[0])})
        row['excess30_primary'] = round(float(excess_by_id.get(e['episode'], np.nan)), 3) if e['episode'] in excess_by_id else ''
        rows.append(row)
    out = HERE / 'results'
    out.mkdir(exist_ok=True)
    with open(out / 'episode-windows.csv', 'w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out / 'timing-results.json').write_text(json.dumps(results, indent=1, default=float) + '\n')
    np.save(out / 'primary-null.npy', primary['null'])
    summary = {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()
                   if kk in ('observed', 'raw_observed', 'adjusted_excess', 'p', 'excess', 'episodes', 'blocks', 'sum_pre', 'sum_post', 'p_holm')}
               for k, v in [('planned_primary', results['planned_primary'])] + list(sens.items()) + list(am.items())
               if isinstance(v, dict) and 'p' in v}
    print(json.dumps(summary, indent=0))


def weighted(st, y, w, chosen):
    """Batch-size-weighted mean episode difference: sum(n_i * D_i) / sum(n_i), n_i = novel commits.

    Not requests per novel commit; that aggregate, sum(D_i) / sum(n_i), is a rescaling of the primary statistic.
    """
    c = cs.cumulative(y)
    blocks = cs.blocks_for([e['pos'] for e in chosen])
    weight = {}
    for e in chosen:
        weight.setdefault(e['pos'], 0)
        weight[e['pos']] += int(e['novel_commits'])
    rot = cs.Rotation(blocks)
    f = cs.diff_stat(c, w)
    # Weights travel with episodes under rotation.
    tab = []
    for (start, offsets), positions in zip(blocks, rot.shift_positions):
        wts = np.array([weight[start + o] for o in offsets])
        tab.append((f(positions.ravel()).reshape(positions.shape) * wts[None, :]).sum(axis=1))
    tab = np.stack(tab)
    total = sum(weight.values())
    rng = np.random.default_rng(SEED)
    null = cs.Rotation.totals(tab, rot.draws(rng, DRAWS)) / total
    observed = tab[:, 0].sum() / total
    return {'observed': float(observed), 'p': float(cs.mc_pvalue(observed, null)),
            'excess': float(observed - tab.mean(axis=1).sum() / total), 'episodes': len(chosen), 'novel_commits': total}


def referents(st, y, w, chosen):
    """Move each push date's episodes to the same clock minutes on another eligible date of the same phase."""
    c = cs.cumulative(y)
    day0 = int(st.origin // 86400)
    days, candidates = {}, {}
    by_date = {}
    for e in chosen:
        by_date.setdefault(e['pos'] // 1440, []).append(e)
    n_days = st.n // 1440
    for d, eps in by_date.items():
        mins = [e['pos'] % 1440 for e in eps]
        ph = eps[0]['phase']
        cand = [k for k in range(n_days)
                if all(st.block_ok(k * 1440 + 60 * (m // 60), w, phases={ph}) for m in mins)]
        if d not in cand:
            continue
        days[d], candidates[d] = mins, cand
    r = cs.referent_test(c, days, candidates, w, DRAWS, SEED)
    r['candidate_dates'] = {dt.datetime.fromtimestamp((day0 + d) * 86400, UTC).date().isoformat(): n for d, n in r['candidate_days'].items()}
    del r['candidate_days']
    return clean(r)


if __name__ == '__main__':
    main()
