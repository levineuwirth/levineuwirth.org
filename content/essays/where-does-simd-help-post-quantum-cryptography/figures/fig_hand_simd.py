import sys
import csv
import numpy as np

sys.path.insert(0, 'tools')
from viz_theme import apply_monochrome, save_svg

apply_monochrome()
import matplotlib.pyplot as plt

def read_data(filepath):
    ops = []
    m512 = []; m512_err = []
    m768 = []; m768_err = []
    m1024 = []; m1024_err = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ops.append(row['op'])
            m512.append(float(row['m512_sp']))
            m512_err.append([float(row['m512_elo']), float(row['m512_ehi'])])
            m768.append(float(row['m768_sp']))
            m768_err.append([float(row['m768_elo']), float(row['m768_ehi'])])
            m1024.append(float(row['m1024_sp']))
            m1024_err.append([float(row['m1024_elo']), float(row['m1024_ehi'])])
            
    m512_err = np.array(m512_err).T
    m768_err = np.array(m768_err).T
    m1024_err = np.array(m1024_err).T
    return ops, m512, m512_err, m768, m768_err, m1024, m1024_err

filepath = "content/essays/where-does-simd-help-post-quantum-cryptography/figures/data/hand_simd.csv"
ops, m512, m512_err, m768, m768_err, m1024, m1024_err = read_data(filepath)

fig, ax = plt.subplots(figsize=(10, 4))
bar_width = 0.25
colors = ['#333333', '#777777', '#bbbbbb']
labels = ['ML-KEM-512', 'ML-KEM-768', 'ML-KEM-1024']

x = np.arange(len(ops))
ax.bar(x - bar_width, m512, bar_width, label=labels[0], color=colors[0], yerr=m512_err, edgecolor='none')
ax.bar(x, m768, bar_width, label=labels[1], color=colors[1], yerr=m768_err, edgecolor='none')
ax.bar(x + bar_width, m1024, bar_width, label=labels[2], color=colors[2], yerr=m1024_err, edgecolor='none')

ax.set_xticks(x)
display_ops = [op.replace('gena', 'gen_a') for op in ops]
ax.set_xticklabels(display_ops, rotation=45, ha='right')

ax.set_yscale('log')
ax.set_ylabel("Speedup ref $\\to$ avx2 ($\\times$)")
ax.set_ylim(bottom=1, top=100)
import matplotlib.ticker as ticker
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, pos: f"${int(y)}\\times$"))

ax.legend(loc='upper left', frameon=False, fontsize='small')

save_svg(fig)
