"""
plot_byexposure_sa.py

All-ages (21-60) employment by AI-exposure quintile, private sector, seasonally
adjusted -- the paper analog of the kiindeksen.no hero figure "Sysselsetting
etter KI-eksponering". Headcount is pooled across the four decade age groups,
seasonally adjusted with the shared X-11 core, and indexed to October 2022 = 1.0
(the paper convention). Single panel, five quintile lines.

Reads analysis/output/figure_data/fig_employment_by_age_quintile.csv
(built by build_figure_data.py). No title/notes baked into the PDF.

Output: analysis/output/figures/figure_emp_byexposure_sa.pdf

Usage:
    python analysis/06_figures/plot_byexposure_sa.py
"""

import os                                  # build output paths
from datetime import datetime             # for the ChatGPT marker date

import matplotlib                         # plotting backend
matplotlib.use("Agg")                     # headless (no display) rendering
import matplotlib.pyplot as plt           # pyplot interface
import matplotlib.dates as mdates         # date axis helpers
import pandas as pd                       # data handling

from seasonal import seasonal_adjust      # shared X-11 core (same as the dashboard)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")   # repo root
DATA = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                    "fig_employment_by_age_quintile.csv")        # stage-1 artifact
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")  # output dir

NORM_DATE = "2022-10-16"                   # October 2022 = 1.0 (paper convention)
SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"   # SA factor-estimation window
CHATGPT = mdates.date2num(datetime(2022, 11, 30))  # ChatGPT-launch marker

# kiindeksen / Stanford Canaries quintile palette, Q1..Q5.
QUINTILE_COLORS = {1: "#8C1515", 2: "#577590", 3: "#E54A2B",
                   4: "#E6A817", 5: "#401415"}


def healy_style():
    """Match the house figure style used by the other plot scripts."""
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
    os.makedirs(FIG_DIR, exist_ok=True)               # ensure the output dir exists
    healy_style()                                     # apply the house style

    df = pd.read_csv(DATA, dtype={"age_group": str, "ai_q": str})  # read figure data
    df = df[df["sector"] == 2]                         # private sector only
    df = df[df["ai_q"].isin(["1", "2", "3", "4", "5"])]  # drop the pooled 'all' rows

    # Pool headcount across the four decade age groups -> one series per quintile.
    pooled = (df.groupby(["date", "ai_q"], as_index=False)["employment"].sum())

    fig, ax = plt.subplots(figsize=(10, 6))           # single-panel figure
    for q in range(1, 6):                              # one line per quintile Q1..Q5
        s = pooled[pooled["ai_q"] == str(q)].sort_values("date").copy()  # this quintile
        s = seasonal_adjust(                           # seasonally adjust the headcount
            s[["date", "employment"]].rename(columns={"employment": "value"}),
            SEAS_FROM, SEAS_TO)
        base = s.loc[s["date"] == NORM_DATE, "value"]  # October 2022 level
        idx = s["value"].to_numpy() / float(base.iloc[0])  # index to Oct 2022 = 1.0
        dt = pd.to_datetime(s["date"])                 # x-axis dates
        ax.plot(dt, idx, color=QUINTILE_COLORS[q], linewidth=1.8)  # draw the line
        ax.annotate(f"Q{q}", xy=(dt.iloc[-1], idx[-1]),  # direct end-of-line label
                    xytext=(6, 0), textcoords="offset points", va="center",
                    color=QUINTILE_COLORS[q], fontsize=14, fontweight="bold",
                    annotation_clip=False)

    ax.axhline(y=1.0, color="#AAAAAA", linestyle="-", linewidth=0.5)  # reference line
    ax.axvline(x=CHATGPT, color="#555555", linestyle="--",           # ChatGPT marker
               linewidth=0.7, alpha=0.8)
    ax.set_ylabel("Employment index (Oct 2022 = 1.0), seasonally adjusted")  # y label
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))  # year tick labels
    ax.xaxis.set_major_locator(mdates.YearLocator())          # one tick per year
    ax.set_xlim(right=dt.iloc[-1] + pd.Timedelta(days=180))   # room for end labels

    fig.tight_layout()                                 # trim whitespace
    out = os.path.join(FIG_DIR, "figure_emp_byexposure_sa.pdf")  # output path
    fig.savefig(out, dpi=200, bbox_inches="tight")     # write the PDF
    plt.close(fig)                                      # free the figure
    print(f"Saved {out}")                               # progress message


if __name__ == "__main__":
    main()
