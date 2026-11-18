#!/usr/bin/env python3
"""Recreate the two exported article figures from the bundled data.

From the site root: .venv/bin/python content/essays/exponential-magic/code/plot-figures.py
Or use any Python environment with matplotlib. No games or network calls run.
These are standalone exports, embedded as captioned Markdown images.
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "arcana-essay-matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullLocator

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", type=Path, default=ROOT / "figures")
args = parser.parse_args()
OUT = args.output_dir
OUT.mkdir(parents=True, exist_ok=True)
data = json.loads((ROOT / "data/figure-data.json").read_text())
growth = data["growth_at_start_of_controllers_turn"]
timings = data["emblem_resolution_timings"]
model = data["theoretical_growth"]

BG, INK, GREEN, PURPLE, ORANGE = "#faf8f2", "#252d2a", "#23765b", "#75519b", "#bd643a"
plt.rcParams.update({"svg.hashsalt": "arcana-exponential-magic-20261110", "font.family": "DejaVu Sans", "font.size": 11,
                     "figure.facecolor": BG, "axes.facecolor": BG,
                     "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#bdbfb6", "svg.fonttype": "none"})
def decorate(ax):
    ax.grid(axis="y", color="#dedfd6", linewidth=.7)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
def save(fig, name):
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", metadata={"Date": None})
    fig.savefig(OUT / f"{name}.png", dpi=175, bbox_inches="tight")
    plt.close(fig)

# Pair each timed end step with the population observed at the start of its turn.
replay = [point for point in timings if point["replay"] == "growth replay"]
starts = [max((row for row in growth if row["step"] <= point["step"]),
              key=lambda row: row["step"]) for point in replay]
zombies = [row["zombies"] for row in starts]
seconds = [point["seconds"] for point in replay]

fig, ax = plt.subplots(figsize=(6.2, 3.45), layout="constrained")
ax.plot(zombies, seconds, "o-", linewidth=2.4, markersize=7, color=PURPLE)
ax.set_title("Time to resolve Liliana’s emblem", loc="left", fontsize=15, weight="bold", pad=12)
ax.set_xlabel("Zombies at the start of the turn", labelpad=8)
ax.set_xticks(zombies, [f"{count:,}" for count in zombies])
ax.set(xlim=(650, 3900), ylim=(0, 40), yticks=[0, 10, 20, 30, 40])
decorate(ax)
ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f} s"))
save(fig, "liliana-replay")

# Start at the first event so all three model totals are positive on a log axis.
rows = [row for row in model if row["events"] > 0]
events = [row["events"] for row in rows]
fig, ax = plt.subplots(figsize=(6.2, 3.45), layout="constrained")
ax.set_title("Scute Swarm with doublers and Liliana’s emblem", loc="left",
             fontsize=14, weight="bold", pad=12)
for key, name, color in [
    ("life_gain_two_wardens_one_life_doubler", "life gained", ORANGE),
    ("scutes_one_token_doubler", "Scutes", GREEN),
    ("liliana_zombies", "Zombies", PURPLE),
]:
    totals = [row[key] for row in rows]
    ax.plot(events, totals, "o-", linewidth=2, markersize=4, color=color)
    ax.annotate(f"{totals[-1]:,} {name}", (events[-1], totals[-1]),
                xytext=(6, 0), textcoords="offset points", va="center", color=color)
ax.set_yscale("log")
ax.set(xlim=(0.8, 11.1), ylim=(1, 45000), xticks=events,
       yticks=[1, 10, 100, 1000, 10000], ylabel="Total (log scale)",
       xlabel="Land drops for Scute Swarm · end steps for Liliana")
ax.spines["bottom"].set_bounds(events[0], events[-1])
ax.yaxis.set_minor_locator(NullLocator())
decorate(ax)
save(fig, "scute-and-life")
