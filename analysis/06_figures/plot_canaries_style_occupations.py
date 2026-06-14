"""
plot_canaries_style_occupations.py

Occupation case studies following the Stanford Canaries Dashboard
(software developers, customer service representatives, stock clerks,
home health aides): employment index by decade age group within each
occupation, normalized to November 2022 = 100, with direct line-end
labels and the dashboard palette.

Grid: occupations as rows, adjustment variants as columns (headcount
raw, headcount seasonally adjusted, per capita, per capita seasonally
adjusted). Per capita divides by the resident population of the age
group. Baseline employment (Nov 2022, ages 21-60) printed in the first
panel of each row.

Sector: private sector throughout (the dashboard convention), also for
the Q1/health figure. Note for the health rows that the public sector
dominates these occupations, and that private series there can be
affected by staffing regulation (innleieforbudet 2023) and municipal
contracting.

STYRK-08 mapping: software developers 2512-2514 + 2519 (as in the
paper's Figure 1), customer service 4222, stock clerks 4321, home
health aides 5322.

Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
        analysis/output/figure_data/fig_employment_by_age_quintile.csv (befolkning)
Output: analysis/output/figures/figure_canaries_style_occupations.pdf
        analysis/output/figures/figure_canaries_style_occupations_q5.pdf
        analysis/output/figures/figure_canaries_style_occupations_q1_health.pdf
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from seasonal import seasonal_adjust as _seasonal_adjust  # shared X-11 core

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA = os.path.join(BASE_DIR, "microdata-output",
                    "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
POP_SRC = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                       "fig_employment_by_age_quintile.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

BASE_MONTH = "2022-11-16"
CHATGPT = mdates.date2num(datetime(2022, 11, 30))
SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"

OCCUPATIONS = [
    ("Software developers", ["2512", "2513", "2514", "2519"]),
    ("Customer service representatives", ["4222"]),
    ("Stock clerks", ["4321"]),
    ("Home health aides", ["5322"]),
]

# Stoerste yrker i Q5 (mest eksponert). Regnskap holdes som to grupper,
# men merk omkodingshendelse mai 2025: ~400-600 unge flyttet fra 4311
# til 3313 i en enkelt maaned (summen er glatt). Spranget i 3313- og
# 4311-panelene for 21-30 er omkoding, ikke reell endring; nedgangen
# blant 41-60 i 4311 er derimot i hovedsak reell (det meste foer mai
# 2025, og synlig i summen).
OCCUPATIONS_Q5 = [
    ("ICT analysts and software developers", ["2511", "2519"]),
    ("Wholesale sales representatives", ["3322"]),
    ("Office clerks", ["4110"]),
    ("Accountants", ["3313"]),
    ("Bookkeeping clerks", ["4311"]),
]

# Q1-benchmark (elektrikere, stoerste Q1-ungdomsyrket, stabilt) og
# helse/omsorg: helsefagarbeidere, vernepleiere, sykepleiere. Privat
# sektor som ellers, jf. docstring.
OCCUPATIONS_Q1_HEALTH = [
    ("Electricians", ["7411"]),
    ("Health care assistants\n(helsefagarbeidere)", ["5321"]),
    ("Social educators\n(vernepleiere)", ["2224"]),
    ("Nurses (sykepleiere)", ["2223"]),
]

# out_name -> (yrkesliste, sektorer)
FIGURES = {
    "figure_canaries_style_occupations.pdf": (OCCUPATIONS, [2]),
    "figure_canaries_style_occupations_q5.pdf": (OCCUPATIONS_Q5, [2]),
    "figure_canaries_style_occupations_q1_health.pdf":
        (OCCUPATIONS_Q1_HEALTH, [2]),
}
AGE_ORDER = ["1", "2", "3", "4"]
AGE_LABELS = {"1": "21-30", "2": "31-40", "3": "41-50", "4": "51-60"}
AGE_COLORS = {"1": "#8C1515", "2": "#577590", "3": "#E54A2B", "4": "#E6A817"}

VARIANTS = [
    ("count", False, "Headcount (raw)"),
    ("count", True, "Headcount, seasonally adj."),
    ("percap", False, "Per capita"),
    ("percap", True, "Per capita, seasonally adj."),
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
        "font.size": 16, "axes.titlesize": 18, "axes.labelsize": 15,
        "xtick.labelsize": 12, "ytick.labelsize": 12, "legend.fontsize": 14,
        "lines.linewidth": 1.4,
    })


def seasonal_adjust(s, seas_from=SEAS_FROM, seas_to=SEAS_TO):
    """Thin wrapper over the shared X-11 core (seasonal.py) that supplies this
    script's default estimation window so existing call sites stay unchanged."""
    return _seasonal_adjust(s, seas_from, seas_to)


def label_line_ends(ax, ends, fontsize=10):
    if not ends:
        return
    x = max(e[0] for e in ends)
    ymin, ymax = ax.get_ylim()
    gap = 0.06 * (ymax - ymin)
    items = sorted(ends, key=lambda e: e[1])
    ys, prev = [], -1e18
    for _, yv, _a in items:
        ny = yv if yv >= prev + gap else prev + gap
        ys.append(ny)
        prev = ny
    if ys[-1] > ymax:
        ax.set_ylim(top=ys[-1] + 0.03 * (ymax - ymin))
    for (_, _yv, a), ny in zip(items, ys):
        ax.annotate(AGE_LABELS[a], xy=(x, ny), xytext=(5, 0),
                    textcoords="offset points", va="center", ha="left",
                    color=AGE_COLORS[a], fontsize=fontsize,
                    fontweight="bold", annotation_clip=False)
    ax.set_xlim(right=x + pd.Timedelta(days=230))


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()

    d = pd.read_csv(DATA, dtype={"yrke4": str, "alder_gr": str, "sekt": int})
    d = d[(d["variable"] == "count") & (d["alder_gr"].isin(AGE_ORDER))]

    # Befolkning per aldersgruppe og maaned fra stage-1-artefakten
    # (pop = employment / percap, lik paa tvers av kvintiler).
    pop_src = pd.read_csv(POP_SRC, dtype={"age_group": str, "ai_q": str})
    pop_src = pop_src[(pop_src["sector"] == 2) & (pop_src["ai_q"] == "1")]
    pop_src["pop"] = pop_src["employment"] / pop_src["percap"]
    pop = pop_src.set_index(["date", "age_group"])["pop"]

    for out_name, (occupations, sectors) in FIGURES.items():
        draw_figure(d, pop, occupations, sectors, out_name)


def draw_figure(d, pop, occupations, sectors, out_name):
    d = d[d["sekt"].isin(sectors)]
    nrows = len(occupations)
    fig, axes = plt.subplots(nrows, 4, figsize=(19, 4 * nrows),
                             sharex=True, sharey="row")
    for i, (occ_label, codes) in enumerate(occupations):
        occ = d[d["yrke4"].isin(codes)]
        occ = occ.groupby(["date", "alder_gr"], as_index=False)["value"].sum()
        n_base = int(occ[occ["date"] == BASE_MONTH]["value"].sum())

        panel_ends = []
        for j, (col, do_sa, title) in enumerate(VARIANTS):
            ax = axes[i, j]
            ends = []
            for a in AGE_ORDER:
                s = occ[occ["alder_gr"] == a][["date", "value"]].copy()
                if col == "percap":
                    s["value"] = [v / pop[(dt, a)] for dt, v
                                  in zip(s["date"], s["value"])]
                if do_sa:
                    s = seasonal_adjust(s)
                s = s.sort_values("date")
                base = s.loc[s["date"] == BASE_MONTH, "value"]
                idx = 100.0 * s["value"] / float(base.iloc[0])
                dt = pd.to_datetime(s["date"])
                ax.plot(dt, idx, color=AGE_COLORS[a], linewidth=1.5)
                ends.append((dt.iloc[-1], idx.iloc[-1], a))
            panel_ends.append((ax, ends))
            ax.axhline(y=100.0, color="#AAAAAA", linestyle="-",
                       linewidth=0.6)
            ax.axvline(x=CHATGPT, color="#555555", linestyle="--",
                       linewidth=0.8, alpha=0.8)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax.xaxis.set_major_locator(mdates.YearLocator())
            if i == 0:
                ax.set_title(title, fontsize=16)
        for ax, ends in panel_ends:        # etter at radens ylim er satt
            label_line_ends(ax, ends)
        axes[i, 0].set_ylabel(f"{occ_label}\nindex (Nov 2022 = 100)",
                              fontsize=14)
        axes[i, 0].annotate(f"N = {n_base:,} (Nov 2022)".replace(",", " "),
                            xy=(0.97, 0.04), xycoords="axes fraction",
                            ha="right", va="bottom", fontsize=12,
                            color="#555555")
    axes[0, 0].annotate("ChatGPT launch", xy=(CHATGPT, 0.96),
                        xycoords=("data", "axes fraction"),
                        xytext=(4, 0), textcoords="offset points",
                        fontsize=10, color="#555555")
    sector_note = ("All sectors (public + private)." if set(sectors) == {1, 2}
                   else "Private sector.")
    fig.text(0.005, -0.012, sector_note, fontsize=11, color="#555555",
             ha="left", va="top")
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout()
    out = os.path.join(FIG_DIR, out_name)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
