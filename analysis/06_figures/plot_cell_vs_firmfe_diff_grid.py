"""
plot_cell_vs_firmfe_diff_grid.py

Per-decade-age-group differences between cell-level and firm-FE Poisson
event-study coefficients, for Q2 through Q5 (vs Q1). One panel per decade
age group on the 2x2 grid; in each panel, four lines (one per quintile)
showing diff_q,k = coef_cell_{q,k} - coef_firm_{q,k}. Shared y-axis,
trimmed to the smallest symmetric range that still contains all plotted
differences.

Output: analysis/output/figures/figure_cell_vs_firmfe_diff_grid.pdf
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
CELL_CSV = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                        "coef_microdata_es_decade.csv")
FIRM_CSV = os.path.join(BASE_DIR, "analysis-indiv", "from_secure_server",
                        "coefficients", "coef_event_study_fepois.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]
QUINTILE_COLORS = {2: "#9ECAE1", 3: "#4292C6", 4: "#2171B5", 5: "#08306B"}
QUINTILES = [2, 3, 4, 5]


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
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 20,
        "lines.linewidth": 1.4,
    })


def load_diff() -> pd.DataFrame:
    cell = pd.read_csv(CELL_CSV)
    firm = pd.read_csv(FIRM_CSV)
    cell = cell.rename(columns={"age_group": "age"})[
        ["age", "ai_q", "k", "coef"]].rename(columns={"coef": "coef_cell"})
    firm = firm.rename(columns={"age_bin": "age"})[
        ["age", "ai_q", "k", "coef"]].rename(columns={"coef": "coef_firm"})
    m = pd.merge(cell, firm, on=["age", "ai_q", "k"], how="inner")
    m["diff"] = m["coef_cell"] - m["coef_firm"]
    m["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in m["k"]]
    return m


def round_up_to_nice(x: float) -> float:
    """Round x up to a 'nice' tick stop (0.01, 0.02, 0.05, 0.1, ...)."""
    if x <= 0:
        return 0.01
    for step in (0.01, 0.02, 0.025, 0.05, 0.075, 0.10,
                 0.15, 0.20, 0.25, 0.30):
        if x <= step:
            return step
    return round(x + 0.05, 2)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    d = load_diff()

    # Smallest symmetric ylim that still contains every plotted point.
    abs_max = d["diff"].abs().max()
    ymax = round_up_to_nice(float(abs_max) * 1.02)
    print(f"Max |diff| = {abs_max:.4f}; ylim = +/- {ymax:.4f}")

    fig, axes = plt.subplots(2, 2, figsize=(12, 10), sharey=True)
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        sub = d[d["age"] == a]
        for q in QUINTILES:
            s = sub[sub["ai_q"] == q].sort_values("k")
            if not len(s):
                continue
            ax.plot(s["date"], s["diff"],
                    color=QUINTILE_COLORS[q], linewidth=1.5,
                    linestyle="--")
        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=CHATGPT, color="#888888", linestyle=":",
                   linewidth=0.8, alpha=0.8)
        ax.set_title(AGE_TITLES[a])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(-ymax, ymax)

    handles = [Line2D([0], [0], color=QUINTILE_COLORS[q], lw=2.5,
                      linestyle="--",
                      label=f"Q{q}" + (" (most exposed)" if q == 5 else ""))
               for q in QUINTILES]
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.0), fontsize=20)
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = os.path.join(FIG_DIR, "figure_cell_vs_firmfe_diff_grid.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")

    print()
    print("Diff (cell - firm-FE) summary, log points, by (age, quintile):")
    print("  age | q | n |  mean |   sd  |   p5  |  p50  |  p95")
    for a in AGE_ORDER:
        for q in QUINTILES:
            s = d[(d["age"] == a) & (d["ai_q"] == q)]["diff"]
            if not len(s):
                continue
            quants = s.quantile([0.05, 0.50, 0.95])
            print(f"  {a}   | {q} | {len(s):>2} | {s.mean():+.3f} "
                  f"| {s.std():.3f} | {quants[0.05]:+.3f} "
                  f"| {quants[0.50]:+.3f} | {quants[0.95]:+.3f}")


if __name__ == "__main__":
    main()
