import sys
import os
import csv
import numpy as np

sys.path.insert(0, 'tools')
from viz_theme import apply_monochrome, save_svg

apply_monochrome()
import matplotlib.pyplot as plt

def read_data(filepath):
    ops = []
    refnv = []; refnv_err = []
    ref = []; ref_err = []
    avx2 = []; avx2_err = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ops.append(row['op'])
            refnv.append(float(row['refnv_sp']))
            refnv_err.append([float(row['refnv_elo']), float(row['refnv_ehi'])])
            ref.append(float(row['ref_sp']))
            ref_err.append([float(row['ref_elo']), float(row['ref_ehi'])])
            avx2.append(float(row['avx2_sp']))
            avx2_err.append([float(row['avx2_elo']), float(row['avx2_ehi'])])
    
    refnv_err = np.array(refnv_err).T
    ref_err = np.array(ref_err).T
    avx2_err = np.array(avx2_err).T
    return ops, refnv, refnv_err, ref, ref_err, avx2, avx2_err

base_path = "content/essays/where-does-simd-help-post-quantum-cryptography/figures/data"
params = [("ML-KEM-512", f"{base_path}/decomp_mlkem512.csv"),
          ("ML-KEM-768", f"{base_path}/decomp_mlkem768.csv"),
          ("ML-KEM-1024", f"{base_path}/decomp_mlkem1024.csv")]

fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)

bar_width = 0.25
colors = ['#333333', '#777777', '#bbbbbb']
labels = ['O3 (no auto-vec)', 'O3 + auto-vec', 'O3 + hand SIMD']

for i, (title, filepath) in enumerate(params):
    ops, refnv, refnv_err, ref, ref_err, avx2, avx2_err = read_data(filepath)
    ax = axes[i]
    x = np.arange(len(ops))
    
    ax.bar(x - bar_width, refnv, bar_width, label=labels[0], color=colors[0], yerr=refnv_err, edgecolor='none')
    ax.bar(x, ref, bar_width, label=labels[1], color=colors[1], yerr=ref_err, edgecolor='none')
    ax.bar(x + bar_width, avx2, bar_width, label=labels[2], color=colors[2], yerr=avx2_err, edgecolor='none')
    
    ax.set_title(title, pad=10)
    ax.set_xticks(x)
    
    # Format xticklabels to replace iDec, iEnc, iKeypair, gena
    display_ops = [op.replace('gena', 'gen_a') for op in ops]
    ax.set_xticklabels(display_ops, rotation=45, ha='right')
    
    ax.set_yscale('log')
    if i == 0:
        ax.set_ylabel("Speedup over -O0 ($\times$)")
    
    # Tick formatting
    ax.set_ylim(bottom=1, top=500)
    import matplotlib.ticker as ticker
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, pos: f"${int(y)}\\times$"))

axes[-1].legend(loc='upper right', frameon=False, fontsize='small')
save_svg(fig)
