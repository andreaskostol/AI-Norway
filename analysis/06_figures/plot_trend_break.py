"""
plot_trend_break.py

Seasonally adjusted full-window event study with the fitted piecewise
linear trend-break model (knots November 2022 and May 2025) overlaid.
All quintiles vs Q3, 2x2 decade age-group grid, same style as
plot_microdata_es_decade_q3.py.

Input:  analysis/output/coefficients/coef_microdata_es_decade_q3_full_preseas.csv
        analysis/output/coefficients/coef_trend_break.csv
Output: analysis/output/figures/figure_trend_break_grid.pdf
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

BASE_DT = datetime(2022, 11, 1)
CHATGPT = mdates.date2num(BASE_DT)
AGENTIC = mdates.date2num(datetime(2025, 5, 1))
T_AGE = 30  # april 2025 i t-koding (t = 0 ved oktober 2022)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF_DIR = os.path.join(BASE_DIR, "analysis", "output", "coefficients")
ES_CSV = os.path.join(COEF_DIR, "coef_microdata_es_decade_q3_full_preseas.csv")
TB_CSV = os.path.join(COEF_DIR, "coef_trend_break.csv")
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
    es = pd.read_csv(ES_CSV)
    es["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in es["k"]]
    tb = pd.read_csv(TB_CSV)
    tb = tb[tb["spec"] == "joint"]
    ylo, yhi = -0.20, 0.12

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        for q in QUINTILE_ORDER:
            s = es[(es["age_group"] == a)
                   & (es["ai_q"] == q)].sort_values("date")
            ax.plot(s["date"], s["coef"], color=QUINTILE_COLORS[q],
                    linewidth=0.9, alpha=0.55)
            b = tb[(tb["age_group"] == a)
                   & (tb["ai_q"] == q)].set_index("term")["coef"]
            k = np.arange(s["k"].min(), s["k"].max() + 1)
            t = k + 1  # ES: okt 2022 = k=-1; trendmodell: okt 2022 = t=0
            fitted = (b["slope_pre"] * t
                      + b["dslope_chatgpt"] * np.maximum(t, 0)
                      + b["dslope_agentic"] * np.maximum(t - T_AGE, 0))
            dates = [BASE_DT + pd.DateOffset(months=int(x)) for x in k]
            ax.plot(dates, fitted, color=QUINTILE_COLORS[q], linewidth=2.4)
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
    handles += [Line2D([0], [0], color="#777777", lw=0.9, alpha=0.6,
                       label="Event study (seasonally adjusted)"),
                Line2D([0], [0], color="#777777", lw=2.4,
                       label="Piecewise trend fit")]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.04), fontsize=18)
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(FIG_DIR, "figure_trend_break_grid.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
