"""
plot_honest_did_agentic.py

Rambachan-Roth sensitivity plot for the re-anchored agentic design:
robust confidence sets for the average post-May 2025 effect (Q5 vs Q3)
as a function of Mbar, under Delta^SDRM (deviation from linear trend,
i.e. the continued mid-period trend is the counterfactual) and
Delta^RM (deviation from parallel trends). Original CI at the left.
One panel per decade age group.

Input:  analysis/output/coefficients/coef_honest_did_full_preseas.csv
Output: analysis/output/figures/figure_honest_did_agentic.pdf
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                    "coef_honest_did_full_preseas.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]
COL_ORIG = "#08306B"
COL_SDRM = "#2171B5"
COL_RM = "#D55E00"
OFF = 0.06  # horisontal forskyvning SDRM/RM


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
    d = d[d["design"] == "agentic"]

    fig, axes = plt.subplots(2, 2, figsize=(12, 10), sharey=True)
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        sub = d[d["age_group"] == a]
        if not len(sub):
            ax.set_title(AGE_TITLES[a])
            continue
        orig = sub[sub["delta"] == "original"].iloc[0]
        ax.errorbar([-0.5], [(orig["lb"] + orig["ub"]) / 2],
                    yerr=[[(orig["ub"] - orig["lb"]) / 2]],
                    fmt="none", ecolor=COL_ORIG, elinewidth=3, capsize=5)
        for delta, col, off in [("SDRM", COL_SDRM, -OFF),
                                ("RM", COL_RM, OFF)]:
            s = sub[sub["delta"] == delta].sort_values("Mbar")
            for _, r in s.iterrows():
                ax.errorbar([r["Mbar"] + off],
                            [(r["lb"] + r["ub"]) / 2],
                            yerr=[[(r["ub"] - r["lb"]) / 2]],
                            fmt="none", ecolor=col, elinewidth=3, capsize=5)
        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.set_title(AGE_TITLES[a])
        ax.set_xticks([-0.5, 0, 0.5, 1, 2])
        ax.set_xticklabels(["Orig.", "0", "0.5", "1", "2"])
        ax.set_xlim(-0.85, 2.4)
        ax.set_ylim(-0.55, 0.55)
    for ax in axes[1, :]:
        ax.set_xlabel(r"$\bar{M}$")
    for ax in axes[:, 0]:
        ax.set_ylabel("Log points vs Q3")

    handles = [
        Line2D([0], [0], color=COL_ORIG, lw=3, label="Original 95% CI"),
        Line2D([0], [0], color=COL_SDRM, lw=3,
               label=r"$\Delta^{SDRM}$ (continued trend)"),
        Line2D([0], [0], color=COL_RM, lw=3,
               label=r"$\Delta^{RM}$ (parallel trends)"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.02), fontsize=17)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(FIG_DIR, "figure_honest_did_agentic.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
