"""
plot_canaries_style_index.py

Employment index figures following the layout and method of the Stanford
Digital Economy Lab / ADP "Canaries Dashboard" figures
(https://digitaleconomy.stanford.edu/project/indicators/canaries-dashboard/),
adapted to Norwegian data and our decade age groups.

Matched to their construction (from canaries_age_by_exposure data
dictionary and Flourish config): employment index normalized to 100 in
November 2022, monthly, five Eloundou exposure quintiles weighted
equally by occupation, ChatGPT launch line, direct line-end labels,
their series palette (Q1 #8C1515 ... Q5 #401415). Private sector
(their ADP panel covers private payrolls).

Three variants to show the effect of each adjustment:
  raw       : headcount index (their exact method)
  percap    : headcount / cohort population (removes population growth,
              notable for 31-40 and 51-60)
  percap_sa : per capita and seasonally adjusted (calendar-month factors
              per series estimated on 2021-2024 with linear trend)

Outputs:
  figure_canaries_style_{raw,percap,percap_sa}.pdf : 2x2 age-group grids
  figure_canaries_style_aggregate.pdf : pooled ages 21-60 ("by AI
      Exposure" figure), three variants side by side

Input:  analysis/output/figure_data/fig_employment_by_age_quintile.csv
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from seasonal import seasonal_adjust    # shared X-11 core (same as the dashboard)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                    "fig_employment_by_age_quintile.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

BASE_MONTH = "2022-11-16"                  # Stanford-normalisering: nov 2022
CHATGPT = mdates.date2num(datetime(2022, 11, 30))

# To vindusoppsett: vaart (full datadekning, sesong fra hele kalenderaar)
# og Stanfords (5-aars rullerende vindu fra mai 2021; sesong fra
# 2021m05-2024m04 = 3 hele sesongsykluser, balansert men ikke
# kalenderjustert).
WINDOWS = {
    "": {"start": "2021-01-16", "seas_from": "2021-01-16",
         "seas_to": "2024-12-16"},
    "_maystart": {"start": "2021-05-16", "seas_from": "2021-05-16",
                  "seas_to": "2024-04-16"},
}

AGE_TITLES = {"1": "21-30", "2": "31-40", "3": "41-50", "4": "51-60"}
AGE_ORDER = ["1", "2", "3", "4"]

# Stanford Canaries Flourish-palett, serierekkefoelge Q1..Q5.
QUINTILE_COLORS = {1: "#8C1515", 2: "#577590", 3: "#E54A2B",
                   4: "#E6A817", 5: "#401415"}

VARIANTS = {
    "raw": ("employment", False, "figure_canaries_style_raw.pdf",
            "Headcount (raw)"),
    "percap": ("percap", False, "figure_canaries_style_percap.pdf",
               "Per capita"),
    "percap_sa": ("percap", True, "figure_canaries_style_percap_sa.pdf",
                  "Per capita, seasonally adjusted"),
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
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 16,
        "lines.linewidth": 1.4,
    })


# seasonal_adjust now lives in seasonal.py (imported above) so the figures and
# the dashboard share one X-11 core; the local copy was removed.


def label_line_ends(ax, ends, fontsize=14):
    """Direktelabel hver kvintillinje ved hoeyre endepunkt, de-kollidert."""
    if not ends:
        return
    x = max(e[0] for e in ends)
    ymin, ymax = ax.get_ylim()
    gap = 0.055 * (ymax - ymin)
    items = sorted(ends, key=lambda e: e[1])
    ys, prev = [], -1e18
    for _, yv, _q in items:
        ny = yv if yv >= prev + gap else prev + gap
        ys.append(ny)
        prev = ny
    if ys[-1] > ymax:
        ax.set_ylim(top=ys[-1] + 0.03 * (ymax - ymin))
    for (_, _yv, q), ny in zip(items, ys):
        ax.annotate(f"Q{q}", xy=(x, ny), xytext=(6, 0),
                    textcoords="offset points", va="center", ha="left",
                    color=QUINTILE_COLORS[q], fontsize=fontsize,
                    fontweight="bold", annotation_clip=False)
    ax.set_xlim(right=x + pd.Timedelta(days=170))


def quintile_series(df, col, do_sa, win, age=None):
    """Indeksserie per kvintil; age=None gir aggregat over 21-60."""
    out = {}
    for q in range(1, 6):
        s = df[df["ai_q"] == str(q)]
        if age is not None:
            s = s[s["age_group"] == age]
            s = s[["date", col]].rename(columns={col: "value"})
        else:
            # Aggregat: summer sysselsetting; per capita = sum emp / sum pop,
            # der pop per aldersgruppe = employment / percap.
            g = s.copy()
            g["pop"] = g["employment"] / g["percap"]
            g = g.groupby("date", as_index=False).agg(
                employment=("employment", "sum"), pop=("pop", "sum"))
            g["percap"] = g["employment"] / g["pop"]
            s = g[["date", col]].rename(columns={col: "value"})
        s = s[s["date"] >= win["start"]].sort_values("date")
        if do_sa:
            s = seasonal_adjust(s, win["seas_from"], win["seas_to"])
        base = s.loc[s["date"] == BASE_MONTH, "value"]
        if not len(base) or not len(s):
            continue
        out[q] = pd.DataFrame({
            "dt": pd.to_datetime(s["date"]),
            "idx": 100.0 * s["value"].to_numpy() / float(base.iloc[0])})
    return out


def draw_panel(ax, series, label_fs=14):
    ends = []
    for q, s in series.items():
        ax.plot(s["dt"], s["idx"], color=QUINTILE_COLORS[q], linewidth=1.7)
        ends.append((s["dt"].iloc[-1], s["idx"].iloc[-1], q))
    ax.axhline(y=100.0, color="#AAAAAA", linestyle="-", linewidth=0.6)
    ax.axvline(x=CHATGPT, color="#555555", linestyle="--",
               linewidth=0.8, alpha=0.8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    return ends


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    df = pd.read_csv(DATA, dtype={"age_group": str, "ai_q": str})
    df = df[(df["sector"] == 2) & (df["age_group"].isin(AGE_ORDER))]

    for wsuf, win in WINDOWS.items():
        # 2x2 aldersgruppe-grids, en figur per variant.
        for variant, (col, do_sa, out_name, _title) in VARIANTS.items():
            fig, axes = plt.subplots(2, 2, figsize=(12, 10),
                                     sharex=True, sharey=True)
            panel_ends = []
            for ax, age in zip(axes.flatten(), AGE_ORDER):
                series = quintile_series(df, col, do_sa, win, age=age)
                ends = draw_panel(ax, series)
                panel_ends.append((ax, ends))
                ax.set_title(AGE_TITLES[age])
            for ax, ends in panel_ends:    # etter at felles ylim er satt
                label_line_ends(ax, ends)
            for ax in axes[:, 0]:
                ax.set_ylabel("Employment index (Nov 2022 = 100)")
            axes[0, 0].annotate("ChatGPT launch", xy=(CHATGPT, 0.02),
                                xycoords=("data", "axes fraction"),
                                xytext=(5, 0), textcoords="offset points",
                                fontsize=13, color="#555555")
            fig.autofmt_xdate(rotation=0, ha="center")
            fig.tight_layout()
            out = os.path.join(
                FIG_DIR, out_name.replace(".pdf", f"{wsuf}.pdf"))
            fig.savefig(out, dpi=200, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved {out}")

        # Aggregert "by AI Exposure"-figur: fire varianter side ved side,
        # i justeringsrekkefoelge (raa, kun sesong, per capita, begge).
        agg_variants = [
            ("employment", False, "Headcount (raw)"),
            ("employment", True, "Headcount, seasonally adj."),
            ("percap", False, "Per capita"),
            ("percap", True, "Per capita, seasonally adj."),
        ]
        fig, axes = plt.subplots(1, 4, figsize=(19, 5.5), sharey=True)
        panel_ends = []
        for ax, (col, do_sa, title) in zip(axes, agg_variants):
            series = quintile_series(df, col, do_sa, win, age=None)
            ends = draw_panel(ax, series)
            panel_ends.append((ax, ends))
            ax.set_title(title, fontsize=17)
        for ax, ends in panel_ends:
            label_line_ends(ax, ends, fontsize=13)
        axes[0].set_ylabel("Employment index (Nov 2022 = 100)")
        axes[0].annotate("ChatGPT launch", xy=(CHATGPT, 0.02),
                         xycoords=("data", "axes fraction"),
                         xytext=(5, 0), textcoords="offset points",
                         fontsize=12, color="#555555")
        fig.autofmt_xdate(rotation=0, ha="center")
        fig.tight_layout()
        out = os.path.join(FIG_DIR,
                           f"figure_canaries_style_aggregate{wsuf}.pdf")
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved {out}")

        # 4x4-samlefigur: aldersgrupper nedover, justeringsvarianter
        # bortover. Delt y-akse innen rad (gruppene har ulike spenn).
        fig, axes = plt.subplots(4, 4, figsize=(19, 16),
                                 sharex=True, sharey="row")
        for i, age in enumerate(AGE_ORDER):
            panel_ends = []
            for j, (col, do_sa, title) in enumerate(agg_variants):
                ax = axes[i, j]
                series = quintile_series(df, col, do_sa, win, age=age)
                ends = draw_panel(ax, series)
                panel_ends.append((ax, ends))
                if i == 0:
                    ax.set_title(title, fontsize=16)
            for ax, ends in panel_ends:    # etter at radens ylim er satt
                label_line_ends(ax, ends, fontsize=11)
            axes[i, 0].set_ylabel(
                f"{AGE_TITLES[age]}\nindex (Nov 2022 = 100)", fontsize=15)
        axes[0, 0].annotate("ChatGPT launch", xy=(CHATGPT, 0.02),
                            xycoords=("data", "axes fraction"),
                            xytext=(4, 0), textcoords="offset points",
                            fontsize=11, color="#555555")
        for ax in axes.flat:
            ax.tick_params(labelsize=12)
        fig.autofmt_xdate(rotation=0, ha="center")
        fig.tight_layout()
        out = os.path.join(FIG_DIR,
                           f"figure_canaries_style_grid4x4{wsuf}.pdf")
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved {out}")


if __name__ == "__main__":
    main()
