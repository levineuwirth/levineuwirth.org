"""How R6 was collected: slots against time, with every stop and review.

The step line counts slots collected, from each run's ledger
reconciliation (runs.csv). Events are from timeline.csv, which names the
record behind each. Two windows, at different scales: three hours of 24
September, and the 29 hours from the evening of 28 September.

Monochrome per tools/viz_theme.py.
"""

import sys

sys.path.insert(0, 'tools')
from viz_theme import apply_monochrome, save_svg, load_csv

apply_monochrome()

from datetime import datetime, timedelta, timezone

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

FS = 7.5
LEADER = dict(color='#999999', lw=0.5, linestyle=(0, (1, 1.5)))
SOLID = dict(color='black', linestyle='solid')

TOP = ('2026-09-24T08:40:00Z', '2026-09-24T11:40:00Z')
BOTTOM = ('2026-09-28T19:30:00Z', '2026-09-30T00:30:00Z')

# Where each event's label sits: (y, ha), placed by hand so that no label
# crosses the step line, another label, or another event's leader.
PLACE = {
    'block 1 signed': (116, 'left'),
    'audit rejects block 1: layout': (104, 'left'),
    'amendment 1 prepared': (92, 'left'),
    'approved; lock v2': (45, 'right'),
    'block 1 accepted (550 cases)': (58, 'right'),
    'pricing revision': (116, 'left'),
    'run 1 interrupted; nothing reserved': (104, 'left'),
    'run 2 begins': (92, 'left'),
    'pause 1: connection failed before sending': (72, 'left'),
    'decision: amendment 2, then resume': (50, 'left'),
    'amendment 2 for review': (39, 'left'),
    'review finds two defects': (28, 'left'),
    'revision 2': (17, 'left'),
    'approved; lock v3': (6, 'left'),
    'run 3: preflight, retry, 23 slots': (104, 'right'),
    'collection accepted (4,327 cases)': (116, 'right'),
    'tag r6; release': (92, 'right'),
}


def ts(s):
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


def steps(runs):
    """Cumulative slots collected, as step vertices."""
    xs, ys, n = [ts('2026-09-24T08:00:00Z')], [0], 0
    for r in runs:
        if r['kind'] != 'send_grant':
            continue
        n += 1
        xs.append(ts(r['reconciled_utc']))
        ys.append(n)
    xs.append(ts('2026-09-30T01:00:00Z'))
    ys.append(n)
    return xs, ys


def fmt(x, _pos):
    d = mdates.num2date(x)
    return d.strftime('%H:%M') + (d.strftime('\n%-d Sep') if d.hour == 0 else '')


def build():
    runs = load_csv('runs.csv')
    events = load_csv('timeline.csv')
    xs, ys = steps(runs)
    assert ys[-1] == 88

    fig, (a, b) = plt.subplots(2, 1, figsize=(7.9, 5.0),
                               gridspec_kw=dict(hspace=0.62,
                                                height_ratios=[0.85, 1]))
    for ax, (lo, hi) in ((a, TOP), (b, BOTTOM)):
        ax.step(xs, ys, where='post', lw=1.6, **SOLID)
        ax.axhline(88, lw=0.6, color='black', linestyle=(0, (4, 2)))
        ax.set_xlim(ts(lo), ts(hi))
        ax.set_ylim(0, 126)
        ax.set_yticks([0, 11, 64, 88])
        ax.set_ylabel('slots collected', fontsize=FS)
        ax.tick_params(labelsize=FS)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(fmt))
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
    a.set_yticks([0, 11, 88])
    a.xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 30]))
    a.set_xlabel('24 September, UTC: three hours', fontsize=FS)
    b.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0, 24, 3)))
    b.set_xlabel('28–29 September, UTC: 29 hours', fontsize=FS)
    a.text(ts(TOP[1]), 88, 'authorized', fontsize=FS, ha='right',
           va='bottom', style='italic')
    a.text(ts(TOP[1]), 14, 'block 2 authorized on 25 September',
           fontsize=FS, ha='right', va='bottom', style='italic')

    for e in events:
        t = ts(e['utc'])
        ax = a if t < ts(TOP[1]) else b if t > ts(BOTTOM[0]) else None
        if ax is None:
            continue
        y, ha = PLACE[e['label']]
        ax.plot([t, t], [0, y - 1.5], **LEADER)
        ax.text(t, y, e['label'], fontsize=FS, ha=ha, va='bottom',
                style='italic' if e['lane'] == 'review' else 'normal')

    # The interrupted launch reserved nothing; the paused slot was released.
    b.plot([ts('2026-09-28T20:31:13Z')], [11], marker='x', ms=6, mew=1.2,
           **SOLID)
    b.plot([ts('2026-09-28T23:34:30Z')], [64], marker='o', ms=4.5, mew=1.0,
           mfc='none', mec='black', linestyle='none')
    return fig


if __name__ == '__main__':
    save_svg(
        build(),
        tight=False,
        alt=('Step chart of slots collected over time, with review events. '
             'Block 1 collects 11 slots on 24 September; run 2 collects 53 more '
             'on 28 September and pauses at 64; after amendment 2 is reviewed, '
             'revised and approved, run 3 collects the last 24 on 29 September.'),
        desc=('Left panel, 24 September: block 1 is signed and collects 11 '
              'slots within ten minutes; the first frozen audit rejects it on '
              'the policy-directory layout; amendment 1 is prepared, approved '
              'and locked as v2, and block 1 is accepted with 550 cases. Block 2 '
              'is authorized on 25 September. Right panel: a pricing revision; '
              'a first launch interrupted before any reservation; run 2 from '
              '23:00 collects 53 slots and pauses at 23:34 on a connection that '
              'failed before sending. The next day: the decision to amend, '
              'amendment 2 for review, a review that finds two defects, '
              'revision 2, approval and lock v3, then run 3 retries the released '
              'slot and collects the remaining 23 in eighteen minutes, reaching '
              'the authorized 88. The complete collection is accepted with 4,327 '
              'cases, and the release follows.'),
    )
