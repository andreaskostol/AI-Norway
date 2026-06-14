"""
plot_honest_did_es.py

Event-study display of the exact Rambachan-Roth honest CIs (HonestDiD,
Delta^SDRM, deviation from linear trend) along the quarterly aggregated
seasonally adjusted Q5-vs-Q3 path. Two figures:

  figure_honest_es_chatgpt.pdf : ref October 2022, honest CI per post
      quarter under Mbar = 0 (pure linear continuation of pre-trend).
  figure_honest_es_agentic.pdf : re-anchored April 2025, pre = stable
      mid-period, honest CI per post quarter under Mbar = 0 and 1.

Input:  analysis/output/coefficients/coef_honest_did_es.csv
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                    "coef_honest_did_es.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]
COL_POINT = "#08306B"
COL_M0 = "#D55E00"
COL_M1 = "#EF9F27"


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
        "xtick.labelsize": 14, "ytick.labelsize": 16, "legend.fontsize": 18,
        "lines.linewidth": 1.4,
    })


def qtick(q):
    return q.replace("q", "\nq") if q.endswith(("q1",)) else q[4:]


def draw(design, mbars, cols, ylim, fname, ref_label):
    d = pd.read_csv(COEF)
    d = d[d["design"] == design]

    fig, axes = plt.subplots(2, 2, figsize=(12, 10), sharey=True)
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        sub = d[d["age_group"] == a]
        path = sub[sub["delta"] == "path"].reset_index(drop=True)
        x = range(len(path))
        ax.fill_between(x, path["lb"], path["ub"],
                        color=COL_POINT, alpha=0.15)
        ax.plot(x, path["coef"], color=COL_POINT, linewidth=1.8,
                marker="o", markersize=4)
        n_pre = path["post_idx"].isna().sum()
        for mbar, col, off in zip(mbars, cols, (0.12, -0.12)):
            h = sub[(sub["delta"] == "SDRM") & (sub["Mbar"] == mbar)]
            for _, r in h.iterrows():
                xi = n_pre + r["post_idx"] - 1 + off
                ax.errorbar([xi], [(r["lb"] + r["ub"]) / 2],
                            yerr=[[(r["ub"] - r["lb"]) / 2]],
                            fmt="none", ecolor=col, elinewidth=2.4,
                            capsize=4, alpha=0.9)
        ax.axvline(x=n_pre - 0.5, color="#888888", linestyle="--",
                   linewidth=0.8, alpha=0.8)
        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.set_title(AGE_TITLES[a])
        ticks = [i for i, q in enumerate(path["quarter"])
                 if q.endswith(("q1", "q3"))]
        ax.set_xticks(ticks)
        ax.set_xticklabels([path["quarter"][i] for i in ticks], rotation=45)
        ax.set_ylim(*ylim)
    for ax in axes[:, 0]:
        ax.set_ylabel("Log points vs Q3")

    handles = [
        Line2D([0], [0], color=COL_POINT, lw=2.5, marker="o",
               label=f"Quarterly path ({ref_label})"),
        Patch(facecolor=COL_POINT, alpha=0.15, label="95% CI (pointwise)"),
    ]
    for mbar, col in zip(mbars, cols):
        handles.append(Line2D([0], [0], color=col, lw=2.4,
                              label=rf"Honest CI, $\Delta^{{SDRM}}"
                                    rf"(\bar{{M}}={mbar:g})$"))
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, 1.04), fontsize=16)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = os.path.join(FIG_DIR, fname)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    draw("chatgpt", [0.0], [COL_M0], (-0.45, 0.45),
         "figure_honest_es_chatgpt.pdf", "ref Oct 2022")
    draw("agentic", [0.0, 1.0], [COL_M0, COL_M1], (-0.30, 0.30),
         "figure_honest_es_agentic.pdf", "ref Apr 2025")


if __name__ == "__main__":
    main()
