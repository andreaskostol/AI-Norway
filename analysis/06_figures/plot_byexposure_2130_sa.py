"""
plot_byexposure_2130_sa.py

Employment by AI-exposure quintile for the 21-30 age group only, private
sector -- the deck version of kiindeksen.no figure 2 ("Alder x KI-eksponering")
with the dashboard options seasonally adjusted, per capita, no smoothing.
One line per quintile in the blue ramp shared with the all-ages exposure
figure (plot_byexposure_sa.py), per-capita employment seasonally adjusted
and indexed to October 2022 = 100. No title baked in (the slide carries it).

Reads analysis/output/figure_data/fig_employment_by_age_quintile.csv
(built by build_figure_data.py).

Output: analysis/output/figures/figure_emp_byexposure_2130_sa.pdf

Usage:
    python analysis/06_figures/plot_byexposure_2130_sa.py
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from seasonal import seasonal_adjust

NORM_DATE = "2022-10-16"
SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                    "fig_employment_by_age_quintile.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

CHATGPT = mdates.date2num(datetime(2022, 11, 1))
QUINTILE_COLORS = {1: "#C6DBEF", 2: "#9ECAE1", 3: "#4292C6",
                   4: "#2171B5", 5: "#08306B"}


def style():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "axes.linewidth": 0.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#333333", "axes.grid": True,
        "grid.color": "#DDDDDD", "grid.linewidth": 0.7, "grid.linestyle": "-",
        "xtick.major.width": 0.4, "ytick.major.width": 0.4,
        "xtick.color": "#333333", "ytick.color": "#333333",
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 18, "axes.titlesize": 20, "axes.labelsize": 18,
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 16,
        "lines.linewidth": 1.8,
    })


def sa_index(g):
    """SA per-capita series, indexed to Oct 2022 = 100."""
    g = g.sort_values("date").copy()
    sa = seasonal_adjust(g[["date", "percap"]].rename(columns={"percap": "value"}),
                         SEAS_FROM, SEAS_TO)
    base = sa.loc[sa["date"] == NORM_DATE, "value"].iloc[0]
    g["y"] = 100 * sa["value"].to_numpy() / base
    return g


def label_ends(ax, ends):
    """Direct-label each quintile line at its right end, de-colliding vertically."""
    ymin, ymax = ax.get_ylim()
    gap = 0.05 * (ymax - ymin)
    items = sorted(ends, key=lambda e: e[1])
    prev = -1e18
    for x, yv, q in items:
        ny = yv if yv >= prev + gap else prev + gap
        ax.annotate(f"Q{q}", xy=(x, ny), xytext=(5, 0),
                    textcoords="offset points", va="center",
                    color=QUINTILE_COLORS[q], fontsize=15, fontweight="bold",
                    annotation_clip=False)
        prev = ny


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    style()

    df = pd.read_csv(DATA, dtype={"age_group": str, "ai_q": str})
    df = df[(df["sector"] == 2) & (df["age_group"] == "1")
            & (df["ai_q"].isin(["1", "2", "3", "4", "5"]))]

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ends, last = [], {}
    for q in range(1, 6):
        s = sa_index(df[df["ai_q"] == str(q)])
        s["dt"] = pd.to_datetime(s["date"])
        ax.plot(s["dt"], s["y"], color=QUINTILE_COLORS[q])
        ends.append((s["dt"].iloc[-1], s["y"].iloc[-1], q))
        last[f"Q{q}"] = f"{s['y'].iloc[-1] - 100:+.1f}"

    ax.axhline(y=100, color="#AAAAAA", linestyle="-", linewidth=0.5)
    ax.axvline(x=CHATGPT, color="#555555", linestyle="--", linewidth=0.7, alpha=0.8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    label_ends(ax, ends)

    fig.tight_layout()
    out = os.path.join(FIG_DIR, "figure_emp_byexposure_2130_sa.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}  siste mnd vs okt 2022 (indekspoeng): {last}")


if __name__ == "__main__":
    main()
