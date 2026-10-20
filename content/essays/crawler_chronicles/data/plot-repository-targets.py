#!/usr/bin/env python3
"""Render daily repository shares and traffic volume from the frozen CSV.

Requires matplotlib/numpy. Example:
  .venv/bin/python plot.py --output-dir /path/to/essay/figures
The source CSV and metadata are read beside this script; no live data access.
"""
import argparse
import csv
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/repository-targets-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, NullFormatter
import numpy as np

ROOT = Path(__file__).resolve().parent
GROUPS = ['pmacs', 'levineuwirth.org', 'epiphany', 'LeVCS', 'Other']
COLORS = ['#1764a0', '#00877e', '#7960a7', '#d39b2b', '#b9bec4']
INK, MUTED, GRID = '#24303b', '#58636f', '#e6e9ec'


def compact(n):
    return f'{n / 1000:.1f}k' if n >= 1000 else f'{n:,}'


def render(rows, metric, output):
    dates = sorted({r['date_utc'] for r in rows})
    index = {(r['date_utc'], r['repository']): r for r in rows}
    values = np.array([[int(index[d, repo][metric]) for d in dates] for repo in GROUPS])
    totals = values.sum(axis=0)
    shares = values / totals[None, :] * 100
    assert np.allclose(shares.sum(axis=0), 100)
    early = values[:, :3].sum(axis=1) / totals[:3].sum() * 100
    d13 = shares[:, dates.index('2026-10-13')]
    success = metric == 'http200'
    prefix = 'repository-targets' if success else 'repository-targets-all-requests'

    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 11, 'svg.fonttype': 'none',
        'svg.hashsalt': 'repository-targets-20261020', 'figure.facecolor': 'white',
        'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED,
        'axes.spines.top': False, 'axes.spines.right': False,
    })
    fig = plt.figure(figsize=(14, 9.3))
    fig.text(.085, .970, 'The shift from pmacs to levineuwirth.org',
             fontsize=22, weight='bold', color=INK, va='top')
    definition = 'Successful repository responses · HTTP 200' if success else 'All repository requests · every response status'
    fig.text(.085, .922, f'{definition} · 1–19 October 2026 · UTC', color=MUTED, fontsize=12)
    fig.text(.085, .875, f'pmacs: {early[0]:.1f}% → {d13[0]:.1f}%',
             fontsize=17, color=COLORS[0], weight='bold')
    fig.text(.515, .875, f'levineuwirth.org: {early[1]:.1f}% → {d13[1]:.1f}%',
             fontsize=17, color=COLORS[1], weight='bold')
    fig.text(.085, .845, '1–3 Oct combined → 13 Oct', fontsize=10, color=MUTED)
    fig.legend([Patch(facecolor=c) for c in COLORS], GROUPS,
               loc='lower left', bbox_to_anchor=(.079, .789), ncol=5,
               frameon=False, fontsize=11, columnspacing=2.5, handlelength=1.8)

    ax = fig.add_axes((.085, .360, .875, .365))
    volume = fig.add_axes((.085, .145, .875, .125), sharex=ax)
    x = np.arange(len(dates))
    bottom = np.zeros(len(dates))
    for i, (repo, color) in enumerate(zip(GROUPS, COLORS)):
        bars = ax.bar(x, shares[i], bottom=bottom, width=.79, color=color,
                      edgecolor='white', linewidth=.4, zorder=3)
        bars[-1].set_hatch('///')
        bars[-1].set_edgecolor('#74818b')
        bars[-1].set_linewidth(.35)
        bottom += shares[i]
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100], ['0%', '25%', '50%', '75%', '100%'])
    ax.set_ylabel('Share of the day’s responses' if success else 'Share of the day’s requests', labelpad=12)
    ax.tick_params(axis='x', length=0, labelbottom=False)
    ax.tick_params(axis='y', length=0, pad=9)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis='y', color=GRID)

    # The daily bars are centered on noon; transition markers retain time
    # within the day, without pretending a deployment day has one policy.
    events = [(2.5, '4 Oct\nAnubis introduced'),
              (13 + (20 + 14 / 60) / 24 - .5, '14 Oct\nDifficulty 4'),
              (15 + (9 + 49 / 60) / 24 - .5, '16 Oct\nDifficulty 5')]
    for at, label in events:
        for panel in (ax, volume):
            panel.axvline(at, color=MUTED, lw=.8, ls=(0, (3, 3)), alpha=.7, zorder=2)
        ax.text(at, 1.035, label, transform=ax.get_xaxis_transform(),
                ha='center', va='bottom', fontsize=9, color=MUTED, linespacing=1.3)
    ax.text(x[-1], 1.035, '19 Oct\n00:00–19:00', transform=ax.get_xaxis_transform(),
            ha='center', va='bottom', fontsize=9, color=MUTED, linespacing=1.3)
    # Highlight a few large segments rather than cramming labels into every bar.
    for day, repo in [('2026-10-01', 'pmacs'), ('2026-10-03', 'pmacs'),
                      ('2026-10-10', 'levineuwirth.org'), ('2026-10-13', 'levineuwirth.org')]:
        d, r = dates.index(day), GROUPS.index(repo)
        if shares[r, d] >= 20:
            y = shares[:r, d].sum() + shares[r, d] / 2
            ax.text(d, y, f'{shares[r, d]:.0f}%', ha='center', va='center',
                    fontsize=10, color='white', weight='bold')

    volume.set_title('Daily volume',
                     loc='left', fontsize=11, color=INK, weight='bold', pad=16)
    volume.plot(x[:-1], totals[:-1], color=INK, lw=1.8, marker='o', markersize=4, zorder=3)
    volume.plot(x[-2:], totals[-2:], color=INK, lw=1.4, ls=(0, (2, 3)), zorder=3)
    volume.scatter(x[-1], totals[-1], s=35, color='white', edgecolor=INK, lw=1.5, zorder=4)
    volume.set_yscale('log')
    volume.set_ylim(50 if success else 1000, max(totals) * 2.5)
    ticks = [100, 1000, 10000, 100000] if success else [1000, 10000, 100000]
    volume.set_yticks(ticks)
    volume.yaxis.set_major_formatter(FuncFormatter(lambda n, _: compact(int(n))))
    volume.yaxis.set_minor_formatter(NullFormatter())
    volume.set_ylabel('Responses\n(log scale)' if success else 'Requests\n(log scale)', fontsize=10)
    volume.set_xlim(-.65, len(dates) - .35)
    volume.set_xticks(x, [str(i + 1) for i in x])
    volume.set_xlabel('October 2026 · UTC day', labelpad=10, fontsize=10)
    volume.tick_params(axis='both', length=0, pad=8, labelsize=10)
    volume.tick_params(axis='y', which='minor', length=0)
    volume.spines['left'].set_visible(False)
    volume.spines['bottom'].set_color(GRID)
    volume.set_axisbelow(True)
    volume.grid(axis='y', color=GRID)
    for i in (0, 4, 12, 17, 18):
        volume.annotate(f'{totals[i]:,}', (x[i], totals[i]),
                        xytext=(0, 11), textcoords='offset points', ha='center',
                        fontsize=9, color=INK, weight='bold')

    for ext in ('svg', 'png'):
        metadata = {'Date': None, 'Title': 'Daily repository targets and their share'} if ext == 'svg' else None
        fig.savefig(output / f'{prefix}.{ext}', dpi=180, metadata=metadata,
                    bbox_inches='tight', pad_inches=.18)
    plt.close(fig)
    return {'metric': metric, 'early_pmacs_percent': early[0], 'early_website_percent': early[1],
            'oct13_pmacs_percent': d13[0], 'oct13_website_percent': d13[1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'repository-targets.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    results = [render(rows, metric, args.output_dir) for metric in ('http200', 'requests')]
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
