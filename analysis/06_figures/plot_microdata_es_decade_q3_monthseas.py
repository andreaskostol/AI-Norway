"""plot_microdata_es_decade_q3_monthseas.py

Q3-referenced ChatGPT event-study figure WITH quintile x calendar-month
seasonal FE. Parallel to plot_microdata_es_decade_q3.py but reads
coef_microdata_es_decade_q3_monthseas.csv.

Note: ~44 (k, q) coefficients per age group are dropped due to collinearity
between the monthly seasonal FE and i(k, ai_q). The figure shows only the
identified coefficients, so lines have gaps at dropped k values.

Output: analysis/output/figures/figure_microdata_poisson_es_grid_q3_monthseas.pdf
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

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                    "coef_microdata_es_decade_q3_monthseas.csv")
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
    d = pd.read_csv(COEF)
    d["hi"] = d["coef"] + 1.96 * d["se"]
    d["lo"] = d["coef"] - 1.96 * d["se"]
    d["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in d["k"]]
    ylo, yhi = -0.20, 0.10

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        sub = d[d["age_group"] == a]
        for q in QUINTILE_ORDER:
            s = sub[sub["ai_q"] == q].sort_values("date")
            if not len(s):
                continue
            ax.fill_between(s["date"], s["lo"], s["hi"],
                            color=QUINTILE_COLORS[q], alpha=0.12)
            ax.plot(s["date"], s["coef"],
                    color=QUINTILE_COLORS[q], linewidth=1.6, marker="o", ms=2)
        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=CHATGPT, color="#D55E00", linestyle="--",
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
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.0), fontsize=20)
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = os.path.join(FIG_DIR,
                       "figure_microdata_poisson_es_grid_q3_monthseas.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
