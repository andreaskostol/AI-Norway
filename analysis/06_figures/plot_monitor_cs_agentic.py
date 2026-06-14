"""
plot_monitor_cs_agentic.py

Anytime-valid monitoring of the agentic break: the cumulative
(average post-May 2025) Poisson DiD coefficient for Q5 vs Q3,
re-estimated at each monitoring month, with the conventional 95%
confidence interval and the anytime-valid confidence sequence
side by side. One panel per decade age group.

Input:  analysis/output/coefficients/coef_monitor_cs_agentic.csv
Output: analysis/output/figures/figure_monitor_cs_agentic.pdf
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                    "coef_monitor_cs_agentic.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]
COL_POINT = "#08306B"
COL_CS = "#EF9F27"


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
    d = pd.read_csv(COEF, parse_dates=["monitor_date"])
    d = d[d["ai_q"] == 5]

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        s = d[d["age_group"] == a].sort_values("monitor_date")
        ax.fill_between(s["monitor_date"], s["cs_lo"], s["cs_hi"],
                        color=COL_CS, alpha=0.22)
        ax.fill_between(s["monitor_date"], s["ci_lo"], s["ci_hi"],
                        color=COL_POINT, alpha=0.18)
        ax.plot(s["monitor_date"], s["coef"], color=COL_POINT,
                linewidth=1.8, marker="o", markersize=4)
        cross = s[s["cs_excl_zero"] == 1]
        if len(cross):
            first = cross.iloc[0]
            ax.axvline(x=mdates.date2num(first["monitor_date"]),
                       color="#D55E00", linestyle="--", linewidth=1.2)
        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.set_title(AGE_TITLES[a])
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
        ax.set_ylim(-0.15, 0.10)

    handles = [
        Line2D([0], [0], color=COL_POINT, lw=2.5, marker="o",
               label="Cumulative DiD, Q5 vs Q3"),
        Patch(facecolor=COL_POINT, alpha=0.18, label="95% CI (pointwise)"),
        Patch(facecolor=COL_CS, alpha=0.30,
              label="95% confidence sequence (anytime-valid)"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, 1.02), fontsize=17)
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(FIG_DIR, "figure_monitor_cs_agentic.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
