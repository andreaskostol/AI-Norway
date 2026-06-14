"""
plot_figure1_decade.py

Figure 1: employment in selected high-exposure occupations by decade age group,
private sector, indexed to October 2022 = 1.0. Four panels, one per occupation
group; one line per decade age group.

Reads analysis/output/figure_data/fig_selected_occ_by_age.csv
(built by build_figure_data.py). No title/notes baked into the PDF.

Output: analysis/output/figures/figure1_occupations_by_age.pdf

Usage:
    python analysis/06_figures/plot_figure1_decade.py
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                    "fig_selected_occ_by_age.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

CHATGPT = mdates.date2num(datetime(2022, 11, 1))
AGE_LABELS = {"1": "21-30", "2": "31-40", "3": "41-50", "4": "51-60"}
AGE_COLORS = {"1": "#0072B2", "2": "#E69F00", "3": "#009E73", "4": "#999999"}
# Panel order = the kiindeksen.no yrkescase occupations (see build_figure_data.py).
PANEL_ORDER = ["Software developers", "Customer service agents",
               "Electricians", "Home health aides"]


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
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 16,
        "lines.linewidth": 1.4,
    })


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    df = pd.read_csv(DATA, dtype={"age_group": str})
    df["dt"] = pd.to_datetime(df["date"])

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, grp in zip(axes.flatten(), PANEL_ORDER):
        g = df[df["occ_group"] == grp]
        for a in ["1", "2", "3", "4"]:
            s = g[g["age_group"] == a].sort_values("dt")
            if len(s):
                ax.plot(s["dt"], s["emp_index"], color=AGE_COLORS[a], linewidth=1.6)
                ax.annotate(AGE_LABELS[a], xy=(s["dt"].iloc[-1], s["emp_index"].iloc[-1]),
                            xytext=(5, 0), textcoords="offset points",
                            fontsize=16, color=AGE_COLORS[a], va="center",
                            annotation_clip=False)
        ax.axhline(y=1.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=CHATGPT, color="#555555", linestyle="--", linewidth=0.7, alpha=0.8)
        ax.set_title(grp)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(0.7, 1.4)

    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "figure1_occupations_by_age.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
