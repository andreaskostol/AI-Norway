"""
plot_employment_decade_fte.py

FTE-employment figure (stillingsprosent-weighted) on decade age groups by
AI-exposure quintile, separately for private (main) and public sector.

Reads the stage-1 artifact analysis/output/figure_data/
fig_fte_by_age_quintile.csv (built by build_figure_data.py). Indexed to
October 2022 = 1.0. Mirrors plot_employment_decade.py.

Outputs:
  analysis/output/figures/figure_fte_decade_private.pdf
  analysis/output/figures/figure_fte_decade_public.pdf

Usage:
    python analysis/06_figures/plot_employment_decade_fte.py
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                    "fig_fte_by_age_quintile.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

CHATGPT = mdates.date2num(datetime(2022, 11, 1))

AGE_TITLES = {
    "1": "Early career (21-30)",
    "2": "31-40",
    "3": "41-50",
    "4": "Senior (51-60)",
}
AGE_ORDER = ["1", "2", "3", "4"]
SECTOR_FILE = {2: "figure_fte_decade_private.pdf", 1: "figure_fte_decade_public.pdf"}

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


def plot_sector(df, sector, out_name):
    sub = df[df["sector"] == sector].copy()
    sub["dt"] = pd.to_datetime(sub["date"])

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, age in zip(axes.flatten(), AGE_ORDER):
        a = sub[sub["age_group"].astype(str) == age]
        for q in range(1, 6):
            s = a[a["ai_q"] == str(q)].sort_values("dt")
            if len(s):
                ax.plot(s["dt"], s["fte_index"], color=QUINTILE_COLORS[q], linewidth=1.6)
        overall = a[a["ai_q"] == "all"].sort_values("dt")
        if len(overall):
            ax.plot(overall["dt"], overall["fte_index"], color="red", linewidth=2.0)

        ax.axhline(y=1.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=CHATGPT, color="#555555", linestyle="--", linewidth=0.7, alpha=0.8)
        ax.set_title(AGE_TITLES[age])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(0.8, 1.1)

    handles = [
        Line2D([0], [0], color=QUINTILE_COLORS[1], lw=2.5, label="Q1 (least exposed)"),
        Line2D([0], [0], color=QUINTILE_COLORS[3], lw=2.5, label="Q3"),
        Line2D([0], [0], color=QUINTILE_COLORS[5], lw=2.5, label="Q5 (most exposed)"),
        Line2D([0], [0], color="red", lw=2.5, label="Overall"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.0), fontsize=20)
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
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
