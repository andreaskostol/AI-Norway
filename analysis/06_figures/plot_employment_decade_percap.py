"""
plot_employment_decade_percap.py

Per-capita (un-indexed) variant of plot_employment_decade.py, parallel to
plot_employment_decade_counts.py but dividing headcount by the resident
population in the age group rather than showing raw counts.

Each line is the quintile's headcount as a percentage of the decade age
group's resident population (the `percap` column already in the stage-1
artifact, x100). No October-2022 indexing. As with the counts figure:
  * each age panel autoscales independently (cohorts sit at different levels);
  * the "overall" line (sum across quintiles, ~47-58% of the cohort) is
    dropped so it does not crush the scale; only the five quintile lines show.

Reads the same stage-1 artifact as plot_employment_decade.py:
  analysis/output/figure_data/fig_employment_by_age_quintile.csv

Outputs:
  analysis/output/figures/figure_emp_decade_private_percap.pdf
  analysis/output/figures/figure_emp_decade_public_percap.pdf

Usage:
    python analysis/06_figures/plot_employment_decade_percap.py
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                    "fig_employment_by_age_quintile.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

CHATGPT = mdates.date2num(datetime(2022, 11, 1))

AGE_TITLES = {
    "1": "Early career (21–30)",
    "2": "31–40",
    "3": "41–50",
    "4": "Senior (51–60)",
}
AGE_ORDER = ["1", "2", "3", "4"]
SECTOR_FILE = {2: "figure_emp_decade_private_percap.pdf",
               1: "figure_emp_decade_public_percap.pdf"}

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
        "font.size": 18, "axes.titlesize": 20, "axes.labelsize": 18,
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 22,
        "lines.linewidth": 1.4,
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
        ax.annotate(f"Q{q}", xy=(x, ny), xytext=(6, 0),
                    textcoords="offset points", va="center", ha="left",
                    color=QUINTILE_COLORS[q], fontsize=15, fontweight="bold",
                    annotation_clip=False)
    ax.set_xlim(right=x + pd.Timedelta(days=150))


def plot_sector(df, sector, out_name):
    sub = df[df["sector"] == sector].copy()
    sub["dt"] = pd.to_datetime(sub["date"])
    sub["pct"] = sub["percap"] * 100.0
    pct_fmt = FuncFormatter(lambda y, _: f"{y:.0f}")

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    flat = axes.flatten()
    for idx, (ax, age) in enumerate(zip(flat, AGE_ORDER)):
        a = sub[sub["age_group"].astype(str) == age]
        ends = []
        for q in range(1, 6):
            s = a[a["ai_q"] == str(q)].sort_values("dt")
            if len(s):
                ax.plot(s["dt"], s["pct"], color=QUINTILE_COLORS[q], linewidth=1.6)
                ends.append((s["dt"].iloc[-1], s["pct"].iloc[-1], q))

        ax.axvline(x=CHATGPT, color="#555555", linestyle="--", linewidth=0.7, alpha=0.8)
        ax.set_title(AGE_TITLES[age])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.yaxis.set_major_formatter(pct_fmt)
        if idx % 2 == 0:
            ax.set_ylabel("Employment / cohort (%)")
        label_line_ends(ax, ends)

    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    out = os.path.join(FIG_DIR, out_name)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    df = pd.read_csv(DATA, dtype={"age_group": str, "ai_q": str})
    for sector, name in SECTOR_FILE.items():
        plot_sector(df, sector, name)


if __name__ == "__main__":
    main()
