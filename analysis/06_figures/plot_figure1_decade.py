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

from seasonal import seasonal_adjust       # shared X-11 core (for the SA twin)

NORM_DATE = "2022-10-16"                    # October 2022 = 1.0 (paper convention)
SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"   # SA factor-estimation window

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                    "fig_selected_occ_by_age.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

CHATGPT = mdates.date2num(datetime(2022, 11, 1))
AGE_LABELS = {"1": "21-30", "2": "31-40", "3": "41-50", "4": "51-60"}
# Shades of grey, light (youngest) to dark (oldest).
AGE_COLORS = {"1": "#AAAAAA", "2": "#777777", "3": "#555555", "4": "#1A1A1A"}
# Dash the middle age group (41-50) to separate it from the other grey lines.
AGE_LINESTYLES = {"1": "-", "2": "-", "3": "--", "4": "-"}
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


def add_y(df, adjust):
    """Add column 'y' = the series to plot: raw emp_index, or an SA index."""
    if not adjust:                                  # raw variant: use the precomputed index
        df = df.copy()                              # do not mutate the caller's frame
        df["y"] = df["emp_index"]                   # raw employment index (Oct 2022 = 1.0)
        return df
    parts = []                                      # collect SA series per occ x age
    for (grp, a), g in df.groupby(["occ_group", "age_group"]):  # one series at a time
        g = g.sort_values("date").copy()            # date order for the adjustment
        sa = seasonal_adjust(g[["date", "count"]].rename(columns={"count": "value"}),
                             SEAS_FROM, SEAS_TO)     # remove frozen seasonal factors
        base = sa.loc[sa["date"] == NORM_DATE, "value"].iloc[0]  # SA October 2022 level
        g["y"] = sa["value"].to_numpy() / base      # index the SA series to Oct 2022 = 1.0
        parts.append(g)                             # stash this series
    return pd.concat(parts, ignore_index=True)      # reassemble the long frame


def make(df, adjust, out_name):
    """Draw the four-panel occupations figure, seasonally adjusted or raw."""
    df = add_y(df, adjust)                           # choose raw vs SA series
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, grp in zip(axes.flatten(), PANEL_ORDER):
        g = df[df["occ_group"] == grp]
        for a in ["1", "2", "3", "4"]:
            s = g[g["age_group"] == a].sort_values("dt")
            if len(s):
                ax.plot(s["dt"], s["y"], color=AGE_COLORS[a], linewidth=1.6,
                        linestyle=AGE_LINESTYLES[a])
                ax.annotate(AGE_LABELS[a], xy=(s["dt"].iloc[-1], s["y"].iloc[-1]),
                            xytext=(5, 0), textcoords="offset points",
                            fontsize=16, color=AGE_COLORS[a], va="center",
                            annotation_clip=False)
        ax.axhline(y=1.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=CHATGPT, color="#555555", linestyle="--", linewidth=0.7, alpha=0.8)
        ax.set_title(grp)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        # Let each panel autoscale so the full trend is always visible (home
        # health aides 21-30 climbs above 1.6 and would otherwise be clipped).

    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout()
    out = os.path.join(FIG_DIR, out_name)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    df = pd.read_csv(DATA, dtype={"age_group": str})
    df["dt"] = pd.to_datetime(df["date"])

    make(df, adjust=True,  out_name="figure_occupations_by_age_sa.pdf")  # body figure (SA)
    make(df, adjust=False, out_name="figure1_occupations_by_age.pdf")    # appendix twin (raw)


if __name__ == "__main__":
    main()
