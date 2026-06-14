"""
plot_agentic_outcomes_grid.py
=============================
Three agentic-anchored event-study grids (Apr 2025 = k=-1), one per outcome:
  - count (employed)
  - kontantlonn (cash earnings)
  - nyjobb (new hires)

Same q3-style layout as plot_q3_outcomes_grid.py.
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

BASE_DT = datetime(2025, 5, 1)               # k = 0 = May 2025
AGENTIC = mdates.date2num(BASE_DT)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF_DIR = os.path.join(BASE_DIR, "analysis", "output", "coefficients")
FIG_DIR  = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]
Q_COLORS = {1: "#C6DBEF", 2: "#9ECAE1", 4: "#2171B5", 5: "#08306B"}
Q_ORDER  = [1, 2, 4, 5]

# (coef_filename, output_filename, ylim_lo, ylim_hi, ytick_step)
# Sized to actual CI envelope per outcome:
#   count:        coef [-0.07, +0.05], CI [-0.10, +0.10] -> [-0.15, +0.15] step 0.05
#   kontantlonn:  coef [-0.20, +0.14], CI [-0.23, +0.19] -> [-0.30, +0.20] step 0.10
#   nyjobb:       coef [-0.57, +0.48], CI [-0.82, +0.65] -> [-1.0,  +1.0]  step 0.50
OUTCOMES = [
    ("coef_microdata_es_decade_agentic.csv",
     "figure_microdata_es_decade_agentic_q3.pdf",
     -0.15, 0.15, 0.05),
    ("coef_microdata_es_decade_agentic_kontantlonn.csv",
     "figure_microdata_es_decade_agentic_kontantlonn.pdf",
     -0.30, 0.20, 0.10),
    ("coef_microdata_es_decade_agentic_nyjobb.csv",
     "figure_microdata_es_decade_agentic_nyjobb.pdf",
     -1.00, 1.00, 0.50),
]


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


def make_figure(coef_path, fig_path, ylo, yhi, ystep):
    d = pd.read_csv(coef_path)
    d["hi"] = d["coef"] + 1.96 * d["se"]
    d["lo"] = d["coef"] - 1.96 * d["se"]
    d["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in d["k"]]

    yticks = np.arange(round(ylo / ystep) * ystep, yhi + 1e-9, ystep)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        sub = d[d["age_group"] == a]
        for q in Q_ORDER:
            s = sub[sub["ai_q"] == q].sort_values("date")
            if not len(s):
                continue
            ax.fill_between(s["date"], s["lo"], s["hi"],
                            color=Q_COLORS[q], alpha=0.12)
            ax.plot(s["date"], s["coef"],
                    color=Q_COLORS[q], linewidth=1.6)
        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=AGENTIC, color="#D55E00", linestyle="--",
                   linewidth=0.8, alpha=0.8)
        ax.set_title(AGE_TITLES[a])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(ylo, yhi)
        ax.set_yticks(yticks)

    def _lab(q):
        if q == 1:
            return "Q1 (least exposed)"
        if q == 5:
            return "Q5 (most exposed)"
        return f"Q{q}"

    handles = [Line2D([0], [0], color=Q_COLORS[q], lw=2.5,
                      label=_lab(q)) for q in Q_ORDER]
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.0), fontsize=20)
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(fig_path, dpi=200, bbox_inches="tight")
    fig.savefig(fig_path.replace(".pdf", ".png"), dpi=150,
                bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    for coef_name, fig_name, ylo, yhi, ystep in OUTCOMES:
        coef_path = os.path.join(COEF_DIR, coef_name)
        fig_path  = os.path.join(FIG_DIR, fig_name)
        if not os.path.exists(coef_path):
            print(f"  SKIP {coef_name} (not found)")
            continue
        make_figure(coef_path, fig_path, ylo, yhi, ystep)
        print(f"  Saved {fig_name}")


if __name__ == "__main__":
    main()
