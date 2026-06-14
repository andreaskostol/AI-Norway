"""
plot_employment_decade_counts_vs_percap.py

Side-by-side comparison of the two un-indexed private-sector employment
figures: absolute headcount (left block) and per-capita share of the cohort
(right block). Each block is the usual 2x2 decade-age grid with the five
exposure-quintile lines, direct-labelled Q1-Q5 at their right ends. No
October-2022 indexing.

Reads the same stage-1 artifact as plot_employment_decade.py:
  analysis/output/figure_data/fig_employment_by_age_quintile.csv

Outputs:
  analysis/output/figures/figure_emp_decade_private_counts_vs_percap.pdf

Usage:
    python analysis/06_figures/plot_employment_decade_counts_vs_percap.py
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                    "fig_employment_by_age_quintile.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

CHATGPT = mdates.date2num(datetime(2022, 11, 1))
SECTOR = 2  # private

AGE_TITLES = {
    "1": "Early career (21–30)",
    "2": "31–40",
    "3": "41–50",
    "4": "Senior (51–60)",
}
AGE_ORDER = ["1", "2", "3", "4"]
QUINTILE_COLORS = {1: "#C6DBEF", 2: "#9ECAE1", 3: "#4292C6", 4: "#2171B5", 5: "#08306B"}


def healy_style():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "axes.linewidth": 0.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#333333", "axes.grid": True,
        "grid.color": "#BBBBBB", "grid.linewidth": 0.7, "grid.linestyle": "-",
        "xtick.major.width": 0.4, "ytick.major.width": 0.4,
        "xtick.color": "#333333", "ytick.color": "#333333",
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 15, "axes.titlesize": 16, "axes.labelsize": 15,
        "xtick.labelsize": 13, "ytick.labelsize": 13,
        "lines.linewidth": 1.3,
    })


def label_line_ends(ax, ends):
    """Direct-label each quintile line at its right end, de-colliding vertically."""
    if not ends:
        return
    x = max(e[0] for e in ends)
    ymin, ymax = ax.get_ylim()
    gap = 0.07 * (ymax - ymin)
    items = sorted(ends, key=lambda e: e[1])
    ys, prev = [], -1e18
    for _, yv, _q in items:
        ny = yv if yv >= prev + gap else prev + gap
        ys.append(ny)
        prev = ny
    if ys[-1] > ymax:
        ax.set_ylim(top=ys[-1] + 0.03 * (ymax - ymin))
    for (_, _yv, q), ny in zip(items, ys):
        ax.annotate(f"Q{q}", xy=(x, ny), xytext=(5, 0),
                    textcoords="offset points", va="center", ha="left",
                    color=QUINTILE_COLORS[q], fontsize=12, fontweight="bold",
                    annotation_clip=False)
    ax.set_xlim(right=x + pd.Timedelta(days=160))


def draw_block(subfig, sub, value_col, ylabel, yfmt, title):
    subfig.suptitle(title, fontsize=18, fontweight="bold")
    axes = subfig.subplots(2, 2)
    for idx, (ax, age) in enumerate(zip(axes.flatten(), AGE_ORDER)):
        a = sub[sub["age_group"].astype(str) == age]
        ends = []
        for q in range(1, 6):
            s = a[a["ai_q"] == str(q)].sort_values("dt")
            if len(s):
                ax.plot(s["dt"], s[value_col], color=QUINTILE_COLORS[q], linewidth=1.3)
                ends.append((s["dt"].iloc[-1], s[value_col].iloc[-1], q))
        ax.axvline(x=CHATGPT, color="#555555", linestyle="--", linewidth=0.7, alpha=0.8)
        ax.set_title(AGE_TITLES[age])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.yaxis.set_major_formatter(yfmt)
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(0)
            lbl.set_ha("center")
        if idx % 2 == 0:
            ax.set_ylabel(ylabel)
        label_line_ends(ax, ends)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    df = pd.read_csv(DATA, dtype={"age_group": str, "ai_q": str})
    df = df[(df["sector"] == SECTOR) & (df["ai_q"] != "all")].copy()
    df["dt"] = pd.to_datetime(df["date"])
    df["pct"] = df["percap"] * 100.0

    fig = plt.figure(figsize=(20, 10), layout="constrained")
    left, right = fig.subfigures(1, 2, wspace=0.02)
    draw_block(left, df, "employment", "Employment (1,000s)",
               FuncFormatter(lambda y, _: f"{y / 1000:.0f}"), "Absolute headcount")
    draw_block(right, df, "pct", "Employment / cohort (%)",
               FuncFormatter(lambda y, _: f"{y:.0f}"), "Per capita")

    out = os.path.join(FIG_DIR, "figure_emp_decade_private_counts_vs_percap.pdf")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
