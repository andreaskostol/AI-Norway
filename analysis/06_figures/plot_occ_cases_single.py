"""
plot_occ_cases_single.py

Single-panel per-occupation employment figures for the Arendalsgata talk,
in the style of the kiindeksen.no yrkescase section: one occupation group
per figure, one line per decade age group, seasonally adjusted headcount
indexed to October 2022 = 1.0. No title baked in (the slide carries it).

Reads analysis/output/figure_data/fig_selected_occ_by_age.csv
(built by build_figure_data.py). Outputs one PDF per occupation group:
analysis/output/figures/figure_case_<slug>_sa.pdf

Usage:
    python analysis/06_figures/plot_occ_cases_single.py
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
                    "fig_selected_occ_by_age.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

CHATGPT = mdates.date2num(datetime(2022, 11, 1))
AGE_LABELS = {"1": "21-30", "2": "31-40", "3": "41-50", "4": "51-60"}
AGE_COLORS = {"1": "#AAAAAA", "2": "#777777", "3": "#555555", "4": "#1A1A1A"}
AGE_LINESTYLES = {"1": "-", "2": "-", "3": "--", "4": "-"}

# occ_group label in fig_selected_occ_by_age.csv -> output slug
CASES = {
    "Software developers": "utviklere",
    "Informasjonsradgivere": "informasjonsradgivere",
    "Designyrker": "designyrker",
    "Customer service agents": "kundebehandlere",
    "Electricians": "elektrikere",
    "Home health aides": "hjemmehjelpere",
}


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
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 16,
        "lines.linewidth": 1.4,
    })


def sa_index(g):
    """SA headcount for one occ x age series, indexed to Oct 2022 = 1.0."""
    g = g.sort_values("date").copy()
    sa = seasonal_adjust(g[["date", "count"]].rename(columns={"count": "value"}),
                         SEAS_FROM, SEAS_TO)
    base = sa.loc[sa["date"] == NORM_DATE, "value"].iloc[0]
    g["y"] = sa["value"].to_numpy() / base
    return g


def make(df, grp, slug):
    fig, ax = plt.subplots(figsize=(9, 5.4))
    last = {}
    for a in ["1", "2", "3", "4"]:
        s = df[(df["occ_group"] == grp) & (df["age_group"] == a)]
        if not len(s):
            continue
        s = sa_index(s)
        s["dt"] = pd.to_datetime(s["date"])
        ax.plot(s["dt"], s["y"], color=AGE_COLORS[a], linewidth=1.8,
                linestyle=AGE_LINESTYLES[a])
        ax.annotate(AGE_LABELS[a], xy=(s["dt"].iloc[-1], s["y"].iloc[-1]),
                    xytext=(5, 0), textcoords="offset points",
                    fontsize=15, color=AGE_COLORS[a], va="center",
                    annotation_clip=False)
        last[a] = s["y"].iloc[-1]
    ax.axhline(y=1.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
    ax.axvline(x=CHATGPT, color="#555555", linestyle="--", linewidth=0.7, alpha=0.8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    fig.tight_layout()
    out = os.path.join(FIG_DIR, f"figure_case_{slug}_sa.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    chg = {AGE_LABELS[a]: f"{(v - 1) * 100:+.1f}%" for a, v in last.items()}
    print(f"Saved {out}  siste mnd vs okt 2022: {chg}")


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    df = pd.read_csv(DATA, dtype={"age_group": str})
    for grp, slug in CASES.items():
        make(df, grp, slug)


if __name__ == "__main__":
    main()
