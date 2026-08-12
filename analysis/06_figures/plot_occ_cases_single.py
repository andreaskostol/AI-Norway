"""
plot_occ_cases_single.py

Single-panel per-occupation employment figures for the Arendalsgata talk,
in the style of the kiindeksen.no yrkescase section: one occupation group
per figure, one line per decade age group in the dashboard's age colors,
seasonally adjusted per-capita employment indexed to October 2022 = 100,
no smoothing. No title baked in (the slide carries it).

Reads analysis/output/figure_data/fig_selected_occ_by_age.csv
(built by build_figure_data.py). Outputs one PDF per occupation group:
analysis/output/figures/figure_case_<slug>_sa.pdf

Also builds figure_case_alder_sa.pdf: the same series summed over ALL
occupations per decade age group (the kiindeksen.no "Alder" figure),
read directly from the newest parsed kpos file.

Usage:
    python analysis/06_figures/plot_occ_cases_single.py
"""

import glob
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from seasonal import seasonal_adjust

NORM_DATE = "2022-10-16"
SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                    "fig_selected_occ_by_age.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

CHATGPT = mdates.date2num(datetime(2022, 11, 1))
AGE_LABELS = {"1": "21-30", "2": "31-40", "3": "41-50", "4": "51-60"}
# Age colors from kiindeksen.no (dashboard/site/public/app.js AGE_COLORS).
AGE_COLORS = {"1": "#8C1515", "2": "#E6A817", "3": "#577590", "4": "#401415"}

# occ_group label in fig_selected_occ_by_age.csv -> output slug
CASES = {
    "Software developers": "utviklere",
    "Informasjonsradgivere": "informasjonsradgivere",
    "Designyrker": "designyrker",
    "Customer service agents": "kundebehandlere",
    "Electricians": "elektrikere",
    "Home health aides": "hjemmehjelpere",
}


def style():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "axes.linewidth": 0.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#333333", "axes.grid": True,
        "grid.color": "#DDDDDD", "grid.linewidth": 0.7, "grid.linestyle": "-",
        "xtick.major.width": 0.4, "ytick.major.width": 0.4,
        "xtick.color": "#333333", "ytick.color": "#333333",
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 18, "axes.titlesize": 20, "axes.labelsize": 18,
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 16,
        "lines.linewidth": 1.8,
    })


def sa_index(g, col="percap"):
    """SA per-capita series, indexed to Oct 2022 = 100."""
    g = g.sort_values("date").copy()
    sa = seasonal_adjust(g[["date", col]].rename(columns={col: "value"}),
                         SEAS_FROM, SEAS_TO)
    base = sa.loc[sa["date"] == NORM_DATE, "value"].iloc[0]
    g["y"] = 100 * sa["value"].to_numpy() / base
    return g


def draw(series_by_age, out_name):
    """series_by_age: {age_code: DataFrame with date,count}."""
    fig, ax = plt.subplots(figsize=(9, 5.4))
    last = {}
    for a in ["1", "2", "3", "4"]:
        s = series_by_age.get(a)
        if s is None or not len(s):
            continue
        s = sa_index(s)
        s["dt"] = pd.to_datetime(s["date"])
        ax.plot(s["dt"], s["y"], color=AGE_COLORS[a])
        ax.annotate(AGE_LABELS[a], xy=(s["dt"].iloc[-1], s["y"].iloc[-1]),
                    xytext=(5, 0), textcoords="offset points",
                    fontsize=15, color=AGE_COLORS[a], va="center",
                    annotation_clip=False)
        last[a] = s["y"].iloc[-1]
    ax.axhline(y=100, color="#AAAAAA", linestyle="-", linewidth=0.5)
    ax.axvline(x=CHATGPT, color="#555555", linestyle="--", linewidth=0.7, alpha=0.8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    fig.tight_layout()
    out = os.path.join(FIG_DIR, out_name)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    chg = {AGE_LABELS[a]: f"{v - 100:+.1f}" for a, v in last.items()}
    print(f"Saved {out}  siste mnd vs okt 2022 (indekspoeng): {chg}")


def newest_parsed():
    pats = os.path.join(BASE_DIR, "microdata-output",
                        "09_occ_agedecade_sektor_kpos_*_parsed.csv")
    return sorted(glob.glob(pats))[-1]


DECADE_RANGES = {"1": (21, 30), "2": (31, 40), "3": (41, 50), "4": (51, 60)}


def load_pop():
    """Resident population per decade age group and quarter (as in build_figure_data)."""
    p = pd.read_csv(os.path.join(BASE_DIR, "data", "macro",
                                 "ssb_population_by_age_quarterly.csv"))
    out = {}
    for code, (lo, hi) in DECADE_RANGES.items():
        s = p[(p["age"] >= lo) & (p["age"] <= hi)].groupby("date")["population"].sum()
        for qd, val in s.items():
            out[(code, qd)] = val
    return out


def yq(datestr):
    y, m, _ = datestr.split("-")
    return f"{y}-Q{(int(m) - 1) // 3 + 1}"


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    style()

    # Occupation cases from the shared artifact.
    df = pd.read_csv(DATA, dtype={"age_group": str})
    for grp, slug in CASES.items():
        g = df[df["occ_group"] == grp]
        draw({a: g[g["age_group"] == a] for a in ["1", "2", "3", "4"]},
             f"figure_case_{slug}_sa.pdf")

    # All occupations by age group (kiindeksen.no "Alder" figure),
    # from the newest parsed kpos file, private sector, per capita.
    raw = pd.read_csv(newest_parsed(), dtype={"yrke4": str, "alder_gr": str,
                                              "sekt": str})
    raw = raw[(raw["variable"] == "count") & (raw["sekt"] == "2")
              & (raw["alder_gr"].isin(["1", "2", "3", "4"]))]
    agg = (raw.groupby(["date", "alder_gr"], as_index=False)["value"].sum()
           .rename(columns={"value": "count"}))
    pop = load_pop()
    agg["percap"] = [v / pop[(a, yq(d))]
                     for v, a, d in zip(agg["count"], agg["alder_gr"], agg["date"])]
    draw({a: agg[agg["alder_gr"] == a] for a in ["1", "2", "3", "4"]},
         "figure_case_alder_sa.pdf")


if __name__ == "__main__":
    main()
