"""
plot_es_full_preseas_boot_grid_q1.py

Q1-referenced variant of the bootstrap event-study grid, following the
Brynjolfsson-Chandar-Chen convention of comparing against the least
exposed quintile. Full-window seasonally adjusted event study with
cluster-bootstrap 95% CI bands: decade age groups as rows, quintiles
Q2, Q3, Q4, Q5 (each vs Q1) as columns.

Input:  analysis/output/coefficients/coef_microdata_es_decade_q1_full_preseas_boot.csv
Output: analysis/output/figures/figure_es_full_preseas_boot_grid_q1.pdf
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

BASE_DT = datetime(2022, 11, 1)
CHATGPT = mdates.date2num(BASE_DT)
AGENTIC = mdates.date2num(datetime(2025, 5, 1))

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                    "coef_microdata_es_decade_q1_full_preseas_boot.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "21-30", 2: "31-40", 3: "41-50", 4: "51-60"}
AGE_ORDER = [1, 2, 3, 4]
QUINTILE_ORDER = [2, 3, 4, 5]
QUINTILE_TITLES = {2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5 (most exposed)"}
QUINTILE_COLORS = {2: "#9ECAE1", 3: "#6BAED6", 4: "#2171B5", 5: "#08306B"}


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
        "font.size": 16, "axes.titlesize": 18, "axes.labelsize": 16,
        "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 16,
        "lines.linewidth": 1.3,
    })


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    d = pd.read_csv(COEF)
    d["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in d["k"]]

    fig, axes = plt.subplots(4, 4, figsize=(16, 13),
                             sharex=True, sharey=True)
    for i, a in enumerate(AGE_ORDER):
        for j, q in enumerate(QUINTILE_ORDER):
            ax = axes[i, j]
            s = d[(d["age_group"] == a)
                  & (d["ai_q"] == q)].sort_values("k")
            col = QUINTILE_COLORS[q]
            band_alpha = 0.40 if q in (2, 3) else 0.25
            ax.fill_between(s["date"], s["coef"] - 1.96 * s["se"],
                            s["coef"] + 1.96 * s["se"],
                            color=col, alpha=band_alpha, linewidth=0)
            ax.plot(s["date"], s["coef"], color=col, linewidth=1.5)
            ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
            ax.axvline(x=CHATGPT, color="#D55E00", linestyle="--",
                       linewidth=0.7, alpha=0.8)
            ax.axvline(x=AGENTIC, color="#D55E00", linestyle=":",
                       linewidth=0.7, alpha=0.8)
            if i == 0:
                ax.set_title(QUINTILE_TITLES[q])
            if j == 0:
                ax.set_ylabel(f"{AGE_TITLES[a]}\nlog points vs Q1")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%y"))
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.set_ylim(-0.20, 0.12)

    fig.tight_layout()
    out = os.path.join(FIG_DIR, "figure_es_full_preseas_boot_grid_q1.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
