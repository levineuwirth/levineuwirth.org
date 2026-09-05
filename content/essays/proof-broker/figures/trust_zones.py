"""Where trust lives: the broker's three zones.

Left to right: the kernel-checked zone (the only logical TCB), the
broker machinery (unprivileged; certificate verification is its
acceptance boundary), and untrusted external search. The query path
runs along the top, the answer path returns along the bottom, and
nothing closes a goal except a proof term the kernel checks.

Monochrome per tools/viz_theme.py: zones are told apart by border
weight and dash, not colour.
"""

import sys

sys.path.insert(0, 'tools')
from viz_theme import apply_monochrome, save_svg

apply_monochrome()

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

NODE_FS = 8
ZONE_FS = 7.5
EDGE_LW = 0.9


def zone(ax, x0, y0, w, h, name, subtitle, lw, dashed=False):
    ax.add_patch(FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle="round,pad=0,rounding_size=1.5",
        fc='none', ec='black', lw=lw,
        linestyle=(0, (4, 2)) if dashed else 'solid',
    ))
    ax.text(x0 + 1.6, y0 + h - 2.0, name,
            fontsize=ZONE_FS, weight='bold', ha='left', va='top')
    ax.text(x0 + 1.6, y0 + h - 4.6, subtitle,
            fontsize=ZONE_FS - 0.5, style='italic', ha='left', va='top')


def node(ax, x, y, label, lw=0.9):
    ax.text(x, y, label, fontsize=NODE_FS, ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.45', fc='none',
                      ec='black', lw=lw))


def arrow(ax, p, q):
    ax.annotate('', xy=q, xytext=p,
                arrowprops=dict(arrowstyle='-|>', color='black',
                                lw=EDGE_LW, shrinkA=0, shrinkB=0))


def build():
    fig, ax = plt.subplots(figsize=(9.7, 4.3))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 44)
    ax.set_axis_off()

    zone(ax, 1.5, 2, 24, 40, 'KERNEL-CHECKED', 'the only logical TCB',
         lw=2.0)
    zone(ax, 28.5, 2, 45, 40, 'BROKER MACHINERY', 'unprivileged', lw=1.0)
    zone(ax, 76.5, 2, 22, 40, 'UNTRUSTED SEARCH', 'anything may sit here',
         lw=1.0, dashed=True)

    # Query path, along the top.
    node(ax, 13.5, 30, 'Lean goal')
    node(ax, 34, 30, 'reify')
    node(ax, 48.5, 30, 'IR + rewrite trace')
    node(ax, 64, 30, 'dispatch')
    node(ax, 87.5, 21, 'cvc4 · cvc5 · z3\nor Vampire, or an LLM')

    # Answer path, along the bottom.
    node(ax, 60.5, 12, 'certificate verification\n(acceptance boundary)',
         lw=1.6)
    node(ax, 38, 12, 'reconstruction / closer')
    node(ax, 13.5, 18, 'final proof term')
    node(ax, 13.5, 8, 'Lean kernel')

    arrow(ax, (19.5, 30), (29.5, 30))
    arrow(ax, (38.5, 30), (41.0, 30))
    arrow(ax, (56.0, 30), (60.0, 30))
    arrow(ax, (68.0, 29.0), (81.0, 23.8))
    arrow(ax, (79.5, 17.5), (69.5, 13.5))
    arrow(ax, (50.5, 12), (47.5, 12))
    arrow(ax, (28.5, 12.5), (19.5, 16.5))
    arrow(ax, (13.5, 15.5), (13.5, 10.5))

    ax.text(78.8, 15.2, 'certificate\n(tier + provenance)',
            fontsize=6.5, ha='left', va='top', linespacing=1.15)

    return fig


if __name__ == '__main__':
    save_svg(
        build(),
        alt=('Flow diagram in three zones. A Lean goal in the '
             'kernel-checked zone is reified by the unprivileged broker '
             'machinery into an IR and dispatched to untrusted external '
             'solvers. Their certificate returns through certificate '
             'verification, the acceptance boundary, to a reconstruction '
             'or closer, which produces a final proof term that the Lean '
             'kernel checks.'),
    )
