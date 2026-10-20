#!/usr/bin/env python3
"""Figures for the commit-response report (PNG and SVG in results/figures/).

Requires numpy and matplotlib; set MPLCONFIGDIR to a writable temporary path.
"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commitstats as cs  # noqa: E402
from analysis import Study, SEED  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / 'results/figures'
UTC = dt.timezone.utc
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
INK, INK2, MUTED, GRID, SURFACE = '#0b0b0b', '#52514e', '#8a8984', '#e4e3df', '#fcfcfb'
PHASE_SHADE = {'before-anubis': '#fdf0e9', 'anubis-deployment-day': '#e4e3df', 'difficulty-2': '#eef4fc',
               'd4-cookie-transition': '#e4e3df', 'after-d4-cookie-fix': '#efedfb', 'd5-transition': '#e4e3df',
               'difficulty-5': '#e6e3f8'}
VIOLET = '#6250d6'
PHASE_LABEL = {'before-anubis': 'before Anubis', 'anubis-deployment-day': 'Anubis\ndeployed', 'difficulty-2': 'difficulty 2',
               'after-d4-cookie-fix': 'difficulty 4', 'difficulty-5': 'difficulty 5'}

plt.rcParams.update({
    'font.size': 10, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
    'axes.titlecolor': INK, 'axes.titlesize': 11, 'axes.titleweight': 'bold', 'axes.grid': True, 'grid.color': GRID,
    'grid.linewidth': 0.8, 'axes.axisbelow': True, 'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE, 'legend.frameon': False, 'axes.spines.top': False, 'axes.spines.right': False,
    'svg.fonttype': 'none',
})


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f'{name}.png', dpi=160, bbox_inches='tight')
    fig.savefig(OUT / f'{name}.svg', bbox_inches='tight', metadata={'Date': None})
    plt.close(fig)


def when(st, pos):
    return dt.datetime.fromtimestamp(st.origin + 60 * pos, UTC)


def timeline(st, chosen):
    lo = int((dt.datetime(2026, 10, 1, tzinfo=UTC).timestamp() - st.origin) // 60)
    hours = (st.n - lo) // 60
    prim = st.series('w_get200_primary')[lo:lo + 60 * hours].reshape(hours, 60).sum(1)
    allag = st.series('w_get200_all')[lo:lo + 60 * hours].reshape(hours, 60).sum(1)
    x = [when(st, lo + 60 * h) for h in range(hours)]
    fig, (ax, strip) = plt.subplots(2, 1, figsize=(11, 5.6), sharex=True, gridspec_kw={'height_ratios': [4, 1], 'hspace': 0.08})
    phases = st.meta['phase'][lo:lo + 60 * hours:60]
    start = 0
    for h in range(1, hours + 1):
        if h == hours or phases[h] != phases[start]:
            for a in (ax, strip):
                a.axvspan(x[start], x[h - 1] + dt.timedelta(hours=1), color=PHASE_SHADE[phases[start]], lw=0, zorder=0)
            if phases[start] in PHASE_LABEL and h - start > 10:
                ax.text(x[start] + dt.timedelta(hours=(h - start) / 2), 2.2e4, PHASE_LABEL[phases[start]],
                        ha='center', va='top', fontsize=8.5, color=INK2)
            start = h
    ax.step(x, allag + 0.5, where='post', color=ORANGE, lw=1.4, label='all user agents')
    ax.step(x, prim + 0.5, where='post', color=BLUE, lw=1.4, label='linux-chrome-150-155 cohort')
    ax.set_yscale('log')
    ax.set_ylim(0.4, 3e4)
    ax.set_ylabel('successful GETs per hour (+0.5)')
    ids = {e['episode'] for e in chosen}
    for included, color, label in ((True, VIOLET, 'in the primary test'), (False, MUTED, 'excluded (Oct 4, upgrade, archive switch, log cutover)')):
        sel = [e for e in st.episodes if (e['episode'] in ids) == included]
        strip.vlines([when(st, e['pos']) for e in sel], 0, [int(e['novel_commits']) for e in sel], color=color, lw=1.6, label=label)
    strip.set_ylim(0, 22)
    strip.set_ylabel('new\ncommits', fontsize=9)
    strip.legend(loc='upper right', fontsize=8, ncol=2)
    strip.grid(axis='x')
    ax.legend(loc='upper right', bbox_to_anchor=(1, 0.86))
    ax.set_title('Website repository: hourly successful web GETs, Oct 1 to Oct 19 22:00 UTC')
    strip.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    strip.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    strip.set_xlabel('publication episodes (stem height: previously unpublished commits)', fontsize=9)
    save(fig, 'timeline')


def event_aligned(st):
    lags = np.arange(-180, 181)
    panels = [('w_get200_primary', 'difficulty-2', 'linux-chrome-150-155 cohort, difficulty-2 phase', BLUE),
              ('control-repos', 'difficulty-2', 'control: same cohort, other repositories', AQUA),
              ('w_get200_all', 'before-anubis', 'all user agents, before Anubis', ORANGE)]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, (name, ph, title, color) in zip(axes, panels):
        chosen = st.select(180, phases={ph})
        rot = cs.Rotation(cs.blocks_for([e['pos'] for e in chosen]))
        y = st.series(*[f'r_{r}_get200_primary' for r in ('pmacs', 'epiphany', 'levcs', 'ozymandias', 'where-simd-helps', 'neuropose', 'beyond_comorbidity_indices', 'unknown-repo')]) if name == 'control-repos' else st.series(name)
        binned = lambda prof: prof[:-1].reshape(-1, 5).sum(1)        # 5-minute sums, lag -180..+179
        obs = binned(cs.event_profile(y, rot, lags))
        null = np.stack([binned(row) for row in cs.event_null(y, rot, lags, 2000, SEED)])
        centers = np.arange(-180, 180, 5) + 2.5
        ax.fill_between(centers, np.quantile(null, 0.025, 0), np.quantile(null, 0.975, 0), color=GRID, lw=0,
                        label='rotation null, 95% pointwise')
        ax.plot(centers, null.mean(0), color=MUTED, lw=1.2, label='rotation null mean')
        ax.plot(centers, obs, color=color, lw=2, label='observed mean')
        ax.axvline(0, color=INK, lw=0.8)
        ax.set_title(f'{title}\n{len(chosen)} episodes', fontsize=10)
        ax.set_xlabel('minutes from publication (5-minute bins)')
        ax.set_xticks([-180, -120, -60, 0, 60, 120, 180])
    axes[0].set_ylabel('mean requests per 5 minutes')
    axes[0].legend(loc='upper left', fontsize=8)
    fig.suptitle('Event-aligned leads and lags of successful GETs (W=180 eligibility); gray band: what within-hour rotations of the same pushes produce', y=1.06,
                 fontsize=11, color=INK)
    save(fig, 'event-aligned')


def episodes_plot(st, chosen, results):
    c = cs.cumulative(st.series('w_get200_primary'))
    blocks = cs.blocks_for([e['pos'] for e in chosen])
    rot = cs.Rotation(blocks)
    f = cs.diff_stat(c, 30)
    rows = []
    for (start, offsets), positions in zip(blocks, rot.shift_positions):
        vals = f(positions.ravel()).reshape(positions.shape)
        for j, o in enumerate(offsets):
            e = next(e for e in chosen if e['pos'] == start + o)
            rows.append((e, vals[0, j], np.quantile(vals[:, j], 0.025), np.quantile(vals[:, j], 0.975), vals[:, j].mean()))
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={'width_ratios': [2.3, 1]})
    for i, (e, v, q1, q2, m) in enumerate(rows):
        ax.plot([i, i], [q1, q2], color=GRID, lw=5, solid_capstyle='round', zorder=1)
        ax.plot(i, m, marker='_', color=MUTED, ms=9, zorder=2)
        ax.plot(i, v, marker='o', color=BLUE, ms=6, mec=SURFACE, mew=1.2, zorder=3)
    ticks = [i for i, r in enumerate(rows) if i == 0 or r[0]['date_utc'] != rows[i - 1][0]['date_utc']]
    ax.set_xticks(ticks)
    ax.set_xticklabels([dt.date.fromisoformat(rows[i][0]['date_utc']).strftime('%b %d') for i in ticks], rotation=50, ha='right', fontsize=8.5)
    phase_split = next(i for i, r in enumerate(rows) if r[0]['phase'] == 'difficulty-2')
    ax.axvspan(-0.5, phase_split - 0.5, color=PHASE_SHADE['before-anubis'], lw=0, zorder=0)
    ax.axvspan(phase_split - 0.5, len(rows) - 0.5, color=PHASE_SHADE['difficulty-2'], lw=0, zorder=0)
    ax.text(phase_split / 2, 92, 'before Anubis: cohort absent', ha='center', fontsize=8.5, color=INK2)
    ax.text((phase_split + len(rows)) / 2, 92, 'difficulty 2', ha='center', fontsize=8.5, color=INK2)
    ax.set_xlim(-0.5, len(rows) - 0.5)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_ylabel('post minus pre (30 min), requests')
    ax.set_title('Each episode in the primary test: observed (dot), its own 60 rotations (bar: 95%, tick: mean)', fontsize=10)
    for i, (e, v, *_rest) in enumerate(rows):
        if abs(v) >= 40:
            ax.annotate(e['episode'], (i, v), xytext=(4, 0), textcoords='offset points', fontsize=8, color=INK2, va='center')
    null = np.load(HERE / 'results/primary-null.npy')
    p = results['planned_primary']
    ax2.hist(null, bins=60, color=GRID, edgecolor=SURFACE, lw=0.5)
    ax2.axvline(p['observed'], color=BLUE, lw=2)
    ax2.text(p['observed'], ax2.get_ylim()[1] * 0.80, f"  observed\n  {p['observed']:.2f}\n  p = {p['p']:.3f}", color=INK, fontsize=9, va='top')
    lodo = results['planned_primary_leave_one_date_out']
    ax2.set_title('Null distribution of the planned statistic\n(10,000 within-hour rotations)', fontsize=10)
    ax2.set_xlabel('raw mean post minus pre per episode')
    ax2.set_ylabel('draws')
    ax2.axvline(p['null_mean_exact'], color=MUTED, lw=1.2, ls='--')
    # A leave-one-date-out statistic has its own null, so it is stated in text, not drawn on this histogram.
    low = min(lodo.items(), key=lambda kv: kv[1]['raw_observed'])
    ax2.text(0.02, 0.98, f"null mean {p['null_mean_exact']:.2f} (dashed)\nadjusted excess {p['excess']:+.2f}\n\n"
             f"without {dt.date.fromisoformat(low[0]).strftime('%b %d')}:\nraw {low[1]['raw_observed']:+.2f}, "
             f"adjusted {low[1]['adjusted_excess']:+.2f},\np = {low[1]['p']:.2f} (own null)",
             transform=ax2.transAxes, ha='left', va='top', fontsize=8.5, color=INK2,
             bbox={'facecolor': SURFACE, 'edgecolor': 'none', 'alpha': 0.85})
    save(fig, 'episode-contributions')


def request_vs_publication(st):
    rows = list(csv.DictReader(open(HERE / 'results/request-target-hourly.csv')))
    groups = [('linux-chrome-150-155 cohort', {'linux-chrome-150-155'}, BLUE),
              ('declared crawlers (bot/crawler/spider, Amazonbot, Meta)', {'other-declared-crawler', 'amazon-declared', 'meta-declared'}, ORANGE),
              ('other user agents', {'other'}, AQUA)]
    eps = [e for e in csv.DictReader(open(HERE / 'data/publication-episodes.csv'))]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), sharey=True)
    lo, hi = dt.datetime(2026, 9, 27, tzinfo=UTC), dt.datetime(2026, 10, 19, 22, tzinfo=UTC)
    for ax, (title, cohorts, color) in zip(axes, groups):
        agg = {}
        for r in rows:
            if r['cohort'] in cohorts:
                key = (r['hour_utc'], r['target_published_utc'])
                agg[key] = agg.get(key, 0) + int(r['get_requests'])
        xs = [dt.datetime.fromisoformat(h + ':30:00+00:00') for h, _ in agg]
        ys = [dt.datetime.fromisoformat(p.replace('Z', '+00:00')) for _, p in agg]
        sizes = [4 + 3 * np.sqrt(v) for v in agg.values()]
        ax.scatter(xs, ys, s=sizes, color=color, alpha=0.55, lw=0, zorder=3, rasterized=True)
        ax.plot([lo, hi], [lo, hi], color=INK, lw=0.9, zorder=2)
        ax.text(dt.datetime(2026, 10, 7, tzinfo=UTC), dt.datetime(2026, 10, 9, 6, tzinfo=UTC), 'just published',
                rotation=31, fontsize=8, color=INK2, ha='center')
        for e in eps:
            t = dt.datetime.fromisoformat(e['time_utc'].replace('Z', '+00:00'))
            if t >= dt.datetime(2026, 9, 1, tzinfo=UTC):
                ax.plot([lo, lo + dt.timedelta(hours=10)], [t, t], color=MUTED, lw=0.6, zorder=1)
        ax.set_xlim(lo, hi)
        ax.set_ylim(dt.datetime(2026, 8, 28, tzinfo=UTC), hi)
        ax.set_title(f'{title}\n{sum(agg.values()):,} GETs naming a current commit', fontsize=9.5)
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax.set_xlabel('request time (hour)')
    axes[0].yaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    axes[0].set_ylabel('first Forgejo publication of the requested commit')
    fig.suptitle('What was fetched: request time against publication time of the named commit '
                 '(area ~ requests per hour; gray ticks at left: publication episodes)', y=1.03, fontsize=11, color=INK)
    save(fig, 'request-vs-publication')


def first_fetch():
    pub = {r['sha']: r for r in csv.DictReader(open(HERE / 'data/commit-publication.csv'))}
    hr = json.loads((HERE / 'results/hash-results.json').read_text())
    # Recompute curves from the hash table for plotting.
    import gzip
    first = {}
    groups = {'linux-chrome-150-155 cohort': {'linux-chrome-150-155'},
              'declared crawlers': {'other-declared-crawler', 'amazon-declared', 'meta-declared'},
              'other user agents': {'other'}}
    current = sorted(pub)
    cache = {}
    for r in csv.DictReader(gzip.open(HERE / 'data/hash-requests.csv.gz', 'rt')):
        if r['method'] != 'GET':
            continue
        h = r['hex']
        if h not in cache:
            hits = [s for s in current if s.startswith(h)]
            cache[h] = hits[0] if len(hits) == 1 else None
        s = cache[h]
        if not s:
            continue
        t = dt.datetime.fromisoformat(r['minute_utc'].replace('Z', '+00:00')).timestamp()
        if t + 60 <= float(pub[s]['first_forgejo_unix']):
            continue
        for g, cohorts in groups.items():
            if r['cohort'] in cohorts and (s, g) not in first or (r['cohort'] in cohorts and t < first[(s, g)]):
                first[(s, g)] = t
    end = dt.datetime(2026, 10, 19, 22, tzinfo=UTC).timestamp()
    study = [s for s, p in pub.items() if float(p['first_forgejo_unix']) >= dt.datetime(2026, 10, 1, tzinfo=UTC).timestamp()]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for (g, _), color in zip(groups.items(), (BLUE, ORANGE, AQUA)):
        d, o = [], []
        for s in study:
            t0 = float(pub[s]['first_forgejo_unix'])
            if (s, g) in first:
                d.append(max(first[(s, g)] - t0, 30) / 3600)
                o.append(True)
            else:
                d.append((end - t0) / 3600)
                o.append(False)
        times, surv = cs.kaplan_meier(d, o)
        xs = np.concatenate([[0.05], times, [500]])
        ys = np.concatenate([[0], 1 - surv, [1 - surv[-1] if len(surv) else 0]])
        ax.step(xs, ys, where='post', color=color, lw=2, label=f'{g} ({sum(o)} of {len(study)} fetched)')
    ax.set_xscale('log')
    ax.set_xlim(0.05, 500)
    ax.set_ylim(0, 1)
    ax.set_xticks([0.1, 1, 6, 24, 72, 168, 450])
    ax.set_xticklabels(['6 min', '1 h', '6 h', '1 d', '3 d', '7 d', '19 d'])
    ax.set_xlabel('time from first Forgejo publication to first GET naming the commit')
    ax.set_ylabel('share of commits fetched (Kaplan-Meier)')
    ax.set_title(f'{len(study)} commits first published Oct 1 to 13, censored at Oct 19 22:00 UTC', fontsize=10)
    ax.legend(loc='upper left', fontsize=8.5)
    save(fig, 'first-fetch')
    return hr


def main():
    st = Study()
    chosen = st.select(30)
    results = json.loads((HERE / 'results/timing-results.json').read_text())
    timeline(st, chosen)
    event_aligned(st)
    episodes_plot(st, chosen, results)
    request_vs_publication(st)
    first_fetch()
    print('figures in', OUT)


if __name__ == '__main__':
    main()
