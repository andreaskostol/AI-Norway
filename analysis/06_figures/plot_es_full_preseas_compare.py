"""
plot_es_full_preseas_compare.py

Full-window Q3-referenced Poisson event study: raw (month FE only) vs
seasonally adjusted (pre-period quintile x calendar-month offset).
All quintiles, 2x2 decade age-group grid, same style as
plot_microdata_es_decade_q3.py.

Input:  analysis/output/coefficients/coef_microdata_es_decade_q3_full.csv
        analysis/output/coefficients/coef_microdata_es_decade_q3_full_preseas.csv
Output: analysis/output/figures/figure_es_full_preseas_compare.pdf
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import pandas as pd

BASE_DT = datetime(2022, 11, 1)
CHATGPT = mdates.date2num(BASE_DT)
AGENTIC = mdates.date2num(datetime(2025, 5, 1))

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF_DIR = os.path.join(BASE_DIR, "analysis", "output", "coefficients")
RAW_CSV = os.path.join(COEF_DIR, "coef_microdata_es_decade_q3_full.csv")
ADJ_CSV = os.path.join(COEF_DIR, "coef_microdata_es_decade_q3_full_preseas.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]
QUINTILE_COLORS = {1: "#C6DBEF", 2: "#9ECAE1",
                   4: "#2171B5", 5: "#08306B"}
QUINTILE_ORDER = [1, 2, 4, 5]


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


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    raw = pd.read_csv(RAW_CSV)
    adj = pd.read_csv(ADJ_CSV)
    for d in (raw, adj):
        d["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in d["k"]]
    ylo, yhi = -0.20, 0.12

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        for q in QUINTILE_ORDER:
            r = raw[(raw["age_group"] == a)
                    & (raw["ai_q"] == q)].sort_values("date")
            s = adj[(adj["age_group"] == a)
                    & (adj["ai_q"] == q)].sort_values("date")
            ax.plot(r["date"], r["coef"], color=QUINTILE_COLORS[q],
                    linewidth=0.8, alpha=0.45)
            ax.plot(s["date"], s["coef"], color=QUINTILE_COLORS[q],
                    linewidth=1.8)
        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=CHATGPT, color="#D55E00", linestyle="--",
                   linewidth=0.8, alpha=0.8)
        ax.axvline(x=AGENTIC, color="#D55E00", linestyle=":",
                   linewidth=0.8, alpha=0.8)
        ax.set_title(AGE_TITLES[a])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(ylo, yhi)

    def _lab(q):
        if q == 1:
            return "Q1 (least exposed)"
        if q == 5:
            return "Q5 (most exposed)"
        return f"Q{q}"

    handles = [Line2D([0], [0], color=QUINTILE_COLORS[q], lw=2.5,
                      label=_lab(q)) for q in QUINTILE_ORDER]
    handles += [Line2D([0], [0], color="#777777", lw=0.8, alpha=0.6,
                       label="Unadjusted (month FE only)"),
                Line2D([0], [0], color="#777777", lw=1.8,
                       label="Seasonally adjusted")]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.04), fontsize=18)
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(FIG_DIR, "figure_es_full_preseas_compare.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
