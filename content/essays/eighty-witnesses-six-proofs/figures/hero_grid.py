"""Every slot of R6, one square per obligation and draw.

Rows are the fifteen primary obligations, grouped by declaration family;
columns are the eight draws. To the right, the closer the learned arm's
witnesses met, the frozen deterministic arm, and, set apart, the reference
route, which is a separate control and is never pooled with the arm.

Monochrome per tools/viz_theme.py: outcomes are told apart by fill and
shape, never colour.
"""

import sys

sys.path.insert(0, 'tools')
from viz_theme import apply_monochrome, save_svg, load_csv

apply_monochrome()

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

UNIT = 0.22                     # inches per layout unit, both axes
FS = 8
SMALL = 7.5
CELL = 0.62                     # glyph size, in units
GROUP_GAP = 0.6                 # units between families
FAMILY_ORDER = ['lift_cell', 'threshold_unique', 'cell_value_neutral',
                'Row.s1_noninc']
X_LEFT, X_RIGHT = -7.6, 25.0
X_FAMILY = -2.3                 # family labels, right-aligned
X_CLOSER = 8.0                  # the closer the learned witnesses met
X_DET = 12.6                    # deterministic arm
X_REF = 19.0                    # reference route (control)
SOLID = dict(color='black', linestyle='solid')

CLOSER = {
    'term_mode_nat': 'ℕ closer',
    'term_mode_int': 'ℤ closer',
    'nat_closer_int_goal': 'ℕ closer, ℤ goal',
}
ARM = {
    'proof': 'proof',
    'closed_and_validated': 'closed via gated_omega',
    'backend_not_invoked': 'backend not invoked',
    'reconstruction_refused': 'reconstruction refused',
    'witness_not_recovered': 'witness not recovered',
}


def glyph(ax, x, y, stage):
    h = CELL / 2
    if stage == 'proved':
        ax.add_patch(Rectangle((x - h, y - h), CELL, CELL,
                               fc='black', ec='black', lw=0.8))
    elif stage == 'refused':
        ax.add_patch(Rectangle((x - h, y - h), CELL, CELL,
                               fc='none', ec='black', lw=0.8))
        ax.add_patch(Polygon([(x - h, y - h), (x + h, y - h), (x - h, y + h)],
                             closed=True, fc='black', ec='none'))
    elif stage == 'rejected':
        k = h * 0.9
        for sign in (1, -1):
            ax.plot([x - k, x + k], [y - sign * k, y + sign * k], lw=1.1,
                    solid_capstyle='butt', **SOLID)
    else:                       # not posed
        ax.add_patch(Circle((x, y), 0.08, fc='black', ec='none'))


def text(ax, x, y, s, **kw):
    kw.setdefault('fontsize', SMALL)
    kw.setdefault('va', 'center')
    kw.setdefault('ha', 'left')
    ax.text(x, y, s, **kw)


def rows():
    """[(family, [(site row, y), ...])] from the top, and the last row's y."""
    sites = load_csv('sites.csv')
    y, out = 0.0, []
    for fam in FAMILY_ORDER:
        y -= GROUP_GAP
        members = []
        for s in (s for s in sites if s['family'] == fam):
            y -= 1
            members.append((s, y))
        out.append((fam, members))
    return out, y


def build():
    slots = load_csv('slots.csv')
    stage = {(r['site'], int(r['draw'])): r for r in slots}
    layout, y_last = rows()

    top, bottom = 2.3, y_last - 3.1
    fig = plt.figure(figsize=((X_RIGHT - X_LEFT) * UNIT, (top - bottom) * UNIT))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(X_LEFT, X_RIGHT)
    ax.set_ylim(bottom, top)
    ax.set_axis_off()

    # Column heads.
    text(ax, 3.5, 1.55, 'learned arm, by draw', fontsize=FS, weight='bold',
         ha='center')
    for d in range(1, 9):
        text(ax, d - 1, 0.6, str(d), ha='center')
    text(ax, X_CLOSER, 0.6, 'closer')
    text(ax, X_DET, 1.55, 'deterministic arm', fontsize=FS, weight='bold')
    text(ax, X_REF, 1.55, 'reference route', fontsize=FS, style='italic')
    text(ax, X_REF, 0.6, 'a separate control', style='italic')

    for fam, members in layout:
        y0, y1 = members[0][1], members[-1][1]
        rule = y0 + 0.5 + GROUP_GAP / 2
        ax.plot([X_LEFT + 0.2, X_RIGHT - 0.2], [rule, rule],
                lw=0.5, color='#999999', linestyle='solid')
        text(ax, X_FAMILY, (y0 + y1) / 2, fam, ha='right', style='italic')
        for item, y in members:
            draw_row(ax, item, y, stage)

    # The control is set apart by a dashed rule.
    ax.plot([X_REF - 0.5, X_REF - 0.5], [y_last - 0.5, 2.0],
            color='black', lw=0.6, linestyle=(0, (3, 2)))

    # Key, two by two.
    key = (('proved', 'whole declaration validated, axioms unchanged'),
           ('refused', 'verified, then refused by the closer'),
           ('rejected', 'rejected by the verifier'),
           ('not_posed', 'not posed'))
    for i, (st, label) in enumerate(key):
        kx = (i % 2) * 13.2
        ky = y_last - 1.4 - (i // 2) * 1.1
        glyph(ax, kx, ky, st)
        text(ax, kx + 0.65, ky, label)
    return fig


def draw_row(ax, item, y, stage):
    name = item['site']
    text(ax, -0.75, y, name, fontsize=FS, ha='right', family='monospace')
    outcomes = {stage[(name, d)]['stage'] for d in range(1, 9)}
    assert len(outcomes) == 1, (name, outcomes)
    for d in range(1, 9):
        glyph(ax, d - 1, y, stage[(name, d)]['stage'])
    r = stage[(name, 1)]
    if r['refusal'] or r['closer']:
        text(ax, X_CLOSER, y, CLOSER[r['refusal'] or r['closer']])
    text(ax, X_DET, y, ARM[item['deterministic']])
    text(ax, X_REF, y, ARM[item['reference']], style='italic')


if __name__ == '__main__':
    save_svg(
        build(),
        tight=False,
        alt=('Grid of R6 outcomes, fifteen obligations by eight draws. '
             'Six obligations are proved at every draw, four are verified '
             'and then refused by the closer at every draw, the negative '
             'control is rejected at every draw, and four were never posed; '
             'every column is identical.'),
        desc=('Rows are grouped by declaration family. lift_cell: l069, l070, '
              'l071 and l078 proved at all eight draws; the deterministic arm '
              'also proves them. threshold_unique: l096 and l099 proved at all '
              'eight draws, where the deterministic arm never invoked its '
              'backend; l098 and l101 not posed. cell_value_neutral: l166, l175 '
              'and l178 verified and then refused by the natural-number closer '
              'at every draw; l170, the negative control, rejected by the '
              'verifier at every draw; l158 and l180 not posed. Row.s1_noninc: '
              'l204 verified and refused at every draw. The reference route, a '
              'separate control that re-proves goals with omega rather than '
              'consuming the certificate, closes l069 to l078 and the four '
              'refused sites, and misses l096 and l099. Because the eight '
              'columns are identical, repetition added no coverage.'),
    )
