"""
plot_handa_decade.py

Handa et al.\ automation- and augmentation-share quintile employment by decade
age group, private sector, indexed to October 2022 = 1.0. Companion to the
Eloundou employment figure; reported in the appendix.

Reads the parsed cell file and the Handa mapping directly (one pass), assigns
each occupation to its Handa automation and augmentation quintile, and plots a
four-panel (decade age group) grid per measure. No title/notes in the PDF.

Outputs:
  analysis/output/figures/figure5b_age_by_quintile_handa.pdf  (automation)
  analysis/output/figures/figure5c_age_by_quintile_handa.pdf  (augmentation)

Usage:
    python analysis/06_figures/plot_handa_decade.py
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import pandas as pd

from seasonal import seasonal_adjust       # shared X-11 core (for the SA twins)

SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"   # SA factor-estimation window

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
PARSED = os.path.join(BASE_DIR, "microdata-output",
                      "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
HANDA = os.path.join(BASE_DIR, "data", "ai_exposure", "styrk08_handa_mapping.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

NORM_DATE = "2022-10-16"
CHATGPT = mdates.date2num(datetime(2022, 11, 1))
AGE_TITLES = {"1": "Early career (21–30)", "2": "31–40",
              "3": "41–50", "4": "Senior (51–60)"}
AGE_ORDER = ["1", "2", "3", "4"]
QUINTILE_COLORS = {1: "#C6DBEF", 2: "#9ECAE1", 3: "#4292C6", 4: "#2171B5", 5: "#08306B"}
MEASURES = {
    "q_automation_share": "figure5b_age_by_quintile_handa.pdf",
    "q_augmentation_share": "figure5c_age_by_quintile_handa.pdf",
}


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


def build_series(counts, handa, qcol, adjust=False):
    m = handa[handa[qcol].notna()][["yrke4", qcol]].copy()
    m["ai_q"] = m[qcol].astype(float).astype(int)
    d = counts.merge(m[["yrke4", "ai_q"]], on="yrke4", how="inner")
    by_q = d.groupby(["date", "age_group", "ai_q"], as_index=False)["count"].sum()
    by_q["ai_q"] = by_q["ai_q"].astype(str)
    by_all = d.groupby(["date", "age_group"], as_index=False)["count"].sum()
    by_all["ai_q"] = "all"
    s = pd.concat([by_q, by_all], ignore_index=True)
    if adjust:                                 # seasonally adjust each (age, quintile) series
        parts = []                             # collect the adjusted pieces
        for (ag, q), g in s.groupby(["age_group", "ai_q"]):   # one series at a time
            g = seasonal_adjust(g[["date", "count"]].rename(columns={"count": "value"}),
                                SEAS_FROM, SEAS_TO)            # remove frozen factors
            g = g.rename(columns={"value": "count"})          # back to the count name
            g["age_group"] = ag; g["ai_q"] = q                # restore the group keys
            parts.append(g)                                   # stash the adjusted series
        s = pd.concat(parts, ignore_index=True)               # reassemble the long frame
    ref = (s[s["date"] == NORM_DATE].set_index(["age_group", "ai_q"])["count"]
           .rename("_ref"))
    s = s.merge(ref, left_on=["age_group", "ai_q"], right_index=True, how="left")
    s["idx"] = s["count"] / s["_ref"]
    s["dt"] = pd.to_datetime(s["date"])
    return s


def plot_measure(s, out_name, title):
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    # Shared y-limits across panels so every panel shows the full trend (quintile
    # lines only; the overall line is no longer drawn).
    qy = s[s["ai_q"].isin([str(q) for q in range(1, 6)])]["idx"]
    ylo, yhi = float(qy.min()), float(qy.max())          # full data range
    pad = max(0.02 * (yhi - ylo), 0.01)                  # small visual margin
    for ax, age in zip(axes.flatten(), AGE_ORDER):
        a = s[s["age_group"] == age]
        for q in range(1, 6):
            ser = a[a["ai_q"] == str(q)].sort_values("dt")
            if len(ser):
                ax.plot(ser["dt"], ser["idx"], color=QUINTILE_COLORS[q], linewidth=1.6)
        ax.axhline(y=1.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=CHATGPT, color="#555555", linestyle="--", linewidth=0.7, alpha=0.8)
        ax.set_title(AGE_TITLES[age])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(ylo - pad, yhi + pad)               # include the full trend
    handles = [                                          # legend without "Overall"
        Line2D([0], [0], color=QUINTILE_COLORS[1], lw=2.5, label="Q1 (least exposed)"),
        Line2D([0], [0], color=QUINTILE_COLORS[3], lw=2.5, label="Q3"),
        Line2D([0], [0], color=QUINTILE_COLORS[5], lw=2.5, label="Q5 (most exposed)"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.01), fontsize=20)
    fig.suptitle(title, fontsize=24, fontweight="bold", y=1.10)  # figure title
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = os.path.join(FIG_DIR, out_name)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    df = pd.read_csv(PARSED, dtype={"yrke4": str, "alder_gr": str})
    counts = df[(df["variable"] == "count") & (df["sekt"] == 2)
                & (df["alder_gr"].isin(AGE_ORDER))][
        ["date", "yrke4", "alder_gr", "value"]
    ].rename(columns={"alder_gr": "age_group", "value": "count"})
    handa = pd.read_csv(HANDA, dtype={"styrk08": str}).rename(columns={"styrk08": "yrke4"})
    # Seasonally adjusted twins shown in the body (filenames referenced in the paper).
    sa_names = {"q_automation_share": "figure_age_by_quintile_handa_auto_sa.pdf",
                "q_augmentation_share": "figure_age_by_quintile_handa_aug_sa.pdf"}
    titles = {"q_automation_share": "Automation quintiles: Employment",
              "q_augmentation_share": "Augmentation quintiles: Employment"}
    for qcol, out_name in MEASURES.items():
        plot_measure(build_series(counts, handa, qcol), out_name, titles[qcol])      # raw (appendix)
        plot_measure(build_series(counts, handa, qcol, adjust=True),                 # SA (body)
                     sa_names[qcol], titles[qcol])


if __name__ == "__main__":
    main()
