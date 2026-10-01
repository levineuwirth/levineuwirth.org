"""Where R6's slots and obligations fell away, stage by stage.

Two panels, one per unit, each on its own scale: the 88 slots (eleven
posed obligations, eight draws each) and the census's fifteen primary
obligations. Beside each drop, what accounts for it.

Monochrome per tools/viz_theme.py: the final rung is solid, the rest a
mid-grey that holds in both themes.
"""

import sys

sys.path.insert(0, 'tools')
from viz_theme import apply_monochrome, save_svg, load_csv

apply_monochrome()

import matplotlib.pyplot as plt

FS = 8
GREY = '#8a8a8a'

PANELS = {
    'slots': ('slots: 11 posed obligations × 8 draws', {
        'returned': 'returned',
        'verified': 'witness verified',
        'consumed': 'consumed by the closer',
        'whole_validated': 'whole declaration validated',
    }, {
        'verified': '8 fewer: the negative control; no certificate exists',
        'consumed': '32 fewer: four ℤ goals, refused by the ℕ closer',
        'whole_validated': 'every consumed witness became a proof',
    }),
    'obligations': ('obligations: the census of one file', {
        'primary': 'primary',
        'posed': 'posed',
        'certificate_feasible': 'certificate-feasible',
        'proved': 'proved at every draw',
    }, {
        'posed': '4 fewer: goal form refused before any request',
        'certificate_feasible': '1 fewer: the negative control',
        'proved': '4 fewer: verified, then refused by the closer',
    }),
}


def build():
    rows = load_csv('ladder.csv')
    fig, axes = plt.subplots(2, 1, figsize=(7.6, 3.9))
    for ax, (panel, (title, labels, notes)) in zip(axes, PANELS.items()):
        data = [r for r in rows if r['panel'] == panel]
        top = int(data[0]['count'])
        for i, r in enumerate(data):
            n = int(r['count'])
            last = i == len(data) - 1
            ax.barh(i, n, height=0.62, color='black' if last else GREY,
                    edgecolor='none')
            ax.text(n + top * 0.015, i, str(n), fontsize=FS, va='center',
                    weight='bold' if last else 'normal')
            if r['stage'] in notes:
                ax.text(top * 1.12, i, notes[r['stage']], fontsize=FS - 0.5,
                        va='center', style='italic')
        ax.set_yticks(range(len(data)))
        ax.set_yticklabels([labels[r['stage']] for r in data], fontsize=FS)
        ax.invert_yaxis()
        ax.set_xlim(0, top * 2.3)
        ax.set_xticks([])
        ax.tick_params(axis='y', length=0)
        for side in ('top', 'right', 'bottom'):
            ax.spines[side].set_visible(False)
        ax.set_title(title, fontsize=FS, loc='left', weight='bold')
    fig.subplots_adjust(hspace=0.55)
    return fig


if __name__ == '__main__':
    save_svg(
        build(),
        alt=('Two bar ladders. Slots: 88 returned, 80 verified, 48 consumed, '
             '48 whole-validated. Obligations: 15 primary, 11 posed, 10 '
             'certificate-feasible, 6 proved.'),
        desc=('In the slot ladder, the eight slots lost at verification are '
              'the negative control, for which no valid certificate exists, and '
              'the 32 lost at consumption are the four integer goals the '
              'natural-number closer refused; every consumed witness became a '
              'whole-validated proof. In the obligation ladder, four of the '
              'fifteen were never posed because the SDK refused their goal form, '
              'one is the negative control, and four were verified and then '
              'refused by the closer, leaving six proved. No step was lost to a '
              'missing or invalid proposal on a feasible obligation.'),
    )
