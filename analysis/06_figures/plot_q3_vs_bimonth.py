"""
plot_q3_vs_bimonth.py
=====================
4x2 event-study grid: rows = age decade, columns = (base Q3, Q3 + bimonth FE).
Shows whether the bimonth-quintile seasonal absorber removes oscillation
without distorting headline post-period coefficients.

Inputs:
  analysis/output/coefficients/coef_microdata_es_decade_q3.csv
  analysis/output/coefficients/coef_microdata_es_decade_q3_bimonth.csv

Output:
  analysis/output/figures/figure_es_q3_vs_bimonth.pdf / .png
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
COEF_BASE = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                         "coef_microdata_es_decade_q3.csv")
COEF_BIM  = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                         "coef_microdata_es_decade_q3_bimonth.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]
# Match plot_microdata_es_decade_q3.py exactly: sequential blues.
Q_COLORS = {1: "#C6DBEF", 2: "#9ECAE1", 4: "#2171B5", 5: "#08306B"}
Q_ORDER  = [1, 2, 4, 5]

SPECS = [
    ("Base Q3 (month FE only)",             COEF_BASE),
    ("Q3 + bimonth x quintile seasonal FE", COEF_BIM),
]


def healy_style():
    # Mirror plot_microdata_es_decade_q3.py rcParams exactly.
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


def load(path):
    d = pd.read_csv(path)
    d["hi"] = d["coef"] + 1.96 * d["se"]
    d["lo"] = d["coef"] - 1.96 * d["se"]
    d["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in d["k"]]
    return d


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    data = {label: load(p) for label, p in SPECS}

    # Y-axis: wider window with explicit ticks 0.1 apart.
    ylo, yhi = -0.35, 0.15
    yticks = [-0.3, -0.2, -0.1, 0.0, 0.1]

    fig, axes = plt.subplots(len(AGE_ORDER), len(SPECS),
                             figsize=(14, 18), sharex=True, sharey=True)

    for row, a in enumerate(AGE_ORDER):
        for col, (label, _) in enumerate(SPECS):
            ax = axes[row, col]
            d = data[label]
            sub = d[d["age_group"] == a]
            for q in Q_ORDER:
                s = sub[sub["ai_q"] == q].sort_values("date")
                if not len(s):
                    continue
                ax.fill_between(s["date"], s["lo"], s["hi"],
                                color=Q_COLORS[q], alpha=0.12)
                ax.plot(s["date"], s["coef"], color=Q_COLORS[q], lw=1.6)
            ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", lw=0.5)
            ax.axvline(x=CHATGPT, color="#D55E00", linestyle="--",
                       lw=0.8, alpha=0.8)
            if row == 0:
                ax.set_title(label)
            if col == 0:
                ax.set_ylabel(AGE_TITLES[a])
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

    out_pdf = os.path.join(FIG_DIR, "figure_es_q3_vs_bimonth.pdf")
    out_png = os.path.join(FIG_DIR, "figure_es_q3_vs_bimonth.png")
    fig.savefig(out_pdf, dpi=200, bbox_inches="tight")
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out_pdf}")
    print(f"Saved {out_png}")


if __name__ == "__main__":
    main()
