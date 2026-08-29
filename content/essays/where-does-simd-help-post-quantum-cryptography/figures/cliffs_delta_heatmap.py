import sys
import csv
import numpy as np

sys.path.insert(0, 'tools')
from viz_theme import apply_monochrome, save_svg

apply_monochrome()
import matplotlib.pyplot as plt

def read_data(filepath):
    ops = []
    matrix = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ops.append(row['op'])
            matrix.append([float(row['m512']), float(row['m768']), float(row['m1024'])])
    return ops, np.array(matrix)

filepath = "content/essays/where-does-simd-help-post-quantum-cryptography/figures/data/cliffs_delta.csv"
ops, matrix = read_data(filepath)
labels = ['ML-KEM-512', 'ML-KEM-768', 'ML-KEM-1024']

fig, ax = plt.subplots(figsize=(6, 5))
im = ax.imshow(matrix, cmap='Greys', vmin=0.9, vmax=1.0)

ax.set_xticks(np.arange(len(labels)))
ax.set_yticks(np.arange(len(ops)))
ax.set_xticklabels(labels)
display_ops = [op.replace('gena', 'gen_a') for op in ops]
ax.set_yticklabels(display_ops)

plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

for i in range(len(ops)):
    for j in range(len(labels)):
        val = matrix[i, j]
        text_color = "white" if val > 0.95 else "black"
        ax.text(j, i, f"{val:.3f}", ha="center", va="center", color=text_color)

ax.set_title("Cliff's delta (ref vs. avx2)")
save_svg(fig)
