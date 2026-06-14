"""
plot_es_full_preseas_boot.py

Full-window seasonally adjusted event study (Q5 vs Q3) with naive
(analytic, offset-as-known) and cluster-bootstrap 95% CI bands side
by side. The bootstrap propagates step-1 seasonal-estimation error.

Input:  analysis/output/coefficients/coef_microdata_es_decade_q3_full_preseas_boot.csv
Output: analysis/output/figures/figure_es_full_preseas_boot.pdf
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd

BASE_DT = datetime(2022, 11, 1)
CHATGPT = mdates.date2num(BASE_DT)
AGENTIC = mdates.date2num(datetime(2025, 5, 1))

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                    "coef_microdata_es_decade_q3_full_preseas_boot.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]
COL_POINT = "#08306B"
COL_BOOT = "#D55E00"


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
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 18,
        "lines.linewidth": 1.4,
    })


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    d = pd.read_csv(COEF)
    d = d[d["ai_q"] == 5].copy()
    d["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in d["k"]]

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        s = d[d["age_group"] == a].sort_values("k")
        ax.fill_between(s["date"], s["coef"] - 1.96 * s["se"],
                        s["coef"] + 1.96 * s["se"],
                        color=COL_BOOT, alpha=0.20)
        ax.fill_between(s["date"], s["coef"] - 1.96 * s["se_naive"],
                        s["coef"] + 1.96 * s["se_naive"],
                        color=COL_POINT, alpha=0.18)
        ax.plot(s["date"], s["coef"], color=COL_POINT, linewidth=1.8)
        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=CHATGPT, color="#D55E00", linestyle="--",
                   linewidth=0.8, alpha=0.8)
        ax.axvline(x=AGENTIC, color="#D55E00", linestyle=":",
                   linewidth=0.8, alpha=0.8)
        ax.set_title(AGE_TITLES[a])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(-0.20, 0.12)

    handles = [
        Line2D([0], [0], color=COL_POINT, lw=2.5,
               label="Q5 vs Q3, seasonally adjusted"),
        Patch(facecolor=COL_POINT, alpha=0.18,
              label="95% CI, analytic (offset as known)"),
        Patch(facecolor=COL_BOOT, alpha=0.30,
              label="95% CI, cluster bootstrap (both steps)"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, 1.02), fontsize=17)
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(FIG_DIR, "figure_es_full_preseas_boot.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
