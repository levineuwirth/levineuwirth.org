#!/usr/bin/env python3
"""Plot publication inventory from frozen, public commit-response tables.

Run with the website's .venv/bin/python; requires matplotlib and numpy.
Defaults read commit-response/data beside this script and write ../figures.
The frozen analysis and its manifests are left untouched.
"""
import argparse
import csv
import datetime as dt
import json
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/publication-timeline-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

ROOT = Path(__file__).resolve().parent
BLUE, TEAL = '#1764a0', '#00877e'
INK, MUTED, GRID = '#24303b', '#58636f', '#e6e9ec'


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def prepare(source):
    episodes = [r for r in read_csv(source / 'publication-episodes.csv')
                if '2026-10-01' <= r['date_utc'] < '2026-10-20']
    by_id = {r['episode']: r for r in episodes}
    commits = [r for r in read_csv(source / 'commit-publication.csv')
               if r['episode'] in by_id]
    # Use the reconstruction's conservative 20-second notification tolerance.
    earlier = [r for r in commits if r['github_first_unix']
               and int(r['github_first_unix']) < int(r['first_forgejo_unix']) - 20]
    events = json.loads((source / 'github-push-events.json').read_text())['events']
    push_times = {int(dt.datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')).timestamp())
                  for e in events if e['type'] == 'PushEvent'}
    first_times = {int(r['github_first_unix']) for r in earlier}
    assert first_times <= push_times
    # Each counted GitHub push has no simultaneous Forgejo episode.
    assert all(abs(t - int(e['time_unix'])) > 20
               for t in first_times for e in episodes)
    assert len({r['sha'] for r in commits}) == len(commits) == 271
    assert len(episodes) == 48
    assert len(earlier) == 28 and len(first_times) == 11
    for e in episodes:
        own = [r for r in commits if r['episode'] == e['episode']]
        assert len(own) == int(e['novel_commits'])
        assert sum(r in earlier for r in own) == int(e['github_preceded_novel_commits'])
    daily_episodes = Counter(e['date_utc'] for e in episodes)
    daily_commits = Counter(r['first_forgejo_utc'][:10] for r in commits)
    daily_earlier = Counter(r['first_forgejo_utc'][:10] for r in earlier)
    daily = [dict(date_utc=f'2026-10-{day:02}',
                  publication_episodes=daily_episodes[f'2026-10-{day:02}'],
                  new_commits=daily_commits[f'2026-10-{day:02}'],
                  github_earlier_commits=daily_earlier[f'2026-10-{day:02}'])
             for day in range(1, 20)]
    summary = dict(publication_episodes=len(episodes), new_commits=len(commits),
                   github_earlier_commits=len(earlier), github_only_pushes=len(first_times),
                   affected_forgejo_episodes=len({r['episode'] for r in earlier}),
                   maximum_github_lead_seconds=max(int(r['first_forgejo_unix']) - int(r['github_first_unix'])
                                                   for r in earlier),
                   github_only_push_times_utc=[dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat()
                                               for t in sorted(first_times)],
                   note='The report said nine GitHub-only pushes; the frozen tables contain eleven, '
                        'including 2026-10-07 10:08:33 and 10:48:21 UTC.')
    return daily, summary


def render(daily, summary, output):
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 11, 'svg.fonttype': 'none',
        'svg.hashsalt': 'publication-timeline-20261020', 'figure.facecolor': 'white',
        'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED,
        'axes.spines.top': False, 'axes.spines.right': False,
    })
    fig = plt.figure(figsize=(14, 8.4))
    fig.text(.085, .96, 'When the website’s commits became public',
             fontsize=23, weight='bold', color=INK, va='top')
    fig.text(.085, .908, 'levineuwirth.org · all branches · October 2026 · UTC · frozen record: 19 October',
             fontsize=12, color=MUTED)
    fig.text(.085, .849, '48 publication episodes', fontsize=19, color=INK, weight='bold')
    fig.text(.51, .849, '271 new commits', fontsize=19, color=BLUE, weight='bold')
    fig.text(.085, .805, '11 GitHub-only pushes exposed 28 commits earlier · largest head start: 17.6 hours',
             fontsize=12, color=TEAL, weight='bold')
    ax = fig.add_axes((.085, .375, .88, .325))
    ep = fig.add_axes((.085, .135, .88, .145), sharex=ax)
    x = np.arange(1, 20)
    totals = np.array([r['new_commits'] for r in daily])
    earlier = np.array([r['github_earlier_commits'] for r in daily])
    counts = np.array([r['publication_episodes'] for r in daily])
    fig.legend([Patch(facecolor=BLUE), Patch(facecolor=TEAL)],
               ['First on Forgejo', 'Already available on GitHub'],
               loc='lower left', bbox_to_anchor=(.079, .727), ncol=2,
               frameon=False, fontsize=11, columnspacing=2.5)
    ax.bar(x, totals - earlier, width=.7, color=BLUE, zorder=3)
    ax.bar(x, earlier, bottom=totals - earlier, width=.7, color=TEAL, zorder=3)
    ax.set_title('New commits by first Forgejo publication date', loc='left', fontsize=12,
                 color=INK, weight='bold', pad=15)
    ax.set_ylim(0, 63)
    ax.set_yticks([0, 20, 40, 60])
    ax.set_ylabel('New commits', labelpad=12)
    ax.tick_params(axis='x', labelbottom=False)
    for day, total in zip(x, totals):
        if total:
            ax.text(day, total + 1.8, str(total), ha='center', color=INK, fontsize=10, weight='bold')
    for day, pre in zip(x, earlier):
        if pre:
            ax.text(day, totals[day - 1] - pre / 2, str(pre), ha='center', va='center',
                    fontsize=10, color='white', weight='bold')
    ep.vlines(x, 0, counts, color=INK, lw=2, zorder=3)
    ep.scatter(x[counts > 0], counts[counts > 0], s=28, color=INK, zorder=4)
    ep.set_title('Publication episodes per day · branch updates grouped by second', loc='left', fontsize=12,
                 color=INK, weight='bold', pad=15)
    ep.set_ylim(0, 11)
    ep.set_yticks([0, 3, 6, 9])
    ep.set_ylabel('Episodes', labelpad=12)
    for day, count in zip(x, counts):
        if count:
            ep.text(day, count + .65, str(count), ha='center', fontsize=10, color=INK, weight='bold')
    for panel in (ax, ep):
        panel.axvspan(13.5, 19.5, color='#f2f4f5', zorder=0)
        panel.set_axisbelow(True)
        panel.grid(axis='y', color=GRID)
        panel.spines['left'].set_visible(False)
        panel.spines['bottom'].set_color(GRID)
        panel.tick_params(axis='both', length=0, pad=8)
    ax.text(16.5, 32, 'No later publications\nin the frozen record',
            color=MUTED, ha='center', va='center', fontsize=12, linespacing=1.5)
    ep.set_xlim(.35, 19.65)
    ep.set_xticks(x)
    ep.set_xlabel('October 2026 · UTC day', labelpad=10)
    for ext in ('svg', 'png'):
        meta = {'Date': None, 'Title': 'Website repository publication timeline'} if ext == 'svg' else None
        fig.savefig(output / f'publication-timeline.{ext}', dpi=180, metadata=meta,
                    bbox_inches='tight', pad_inches=.18)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir', type=Path, default=ROOT / 'commit-response/data')
    p.add_argument('--output-dir', type=Path, default=ROOT.parent / 'figures')
    args = p.parse_args()
    daily, summary = prepare(args.source_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'publication-timeline.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(daily[0]))
        writer.writeheader(); writer.writerows(daily)
    (ROOT / 'publication-timeline-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    render(daily, summary, args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
