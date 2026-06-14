"""
plot_consulting_hiring.py

Hiring in advisory/professional-services occupations, by decade age
group. Motivated by ManpowerGroup's Q3 2026 staffing barometer (DN):
hiring expectations in consulting down sharply, reportedly hitting
inexperienced workers hardest.

Grid: occupations as rows (management consultants 2421, ICT systems
analysts 2511, accountants/auditors 2411, lawyers 2611), columns:
  1. Employment, per capita, seasonally adjusted (index Nov 2022 = 100)
  2. New-hire volume = ny_jobb share x headcount, seasonally adjusted,
     3-month centered MA (index Nov 2022 = 100)
  3. New-hire rate, seasonally adjusted, 3-month centered MA (percent)
Private sector. Seasonal adjustment per series as documented in
analysis/docs/sesongjustering.md. Baseline headcount (Nov 2022, ages
21-60) printed in the first panel of each row.

Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
        analysis/output/figure_data/fig_employment_by_age_quintile.csv
Output: analysis/output/figures/figure_consulting_hiring.pdf
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA = os.path.join(BASE_DIR, "microdata-output",
                    "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
POP_SRC = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                       "fig_employment_by_age_quintile.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

BASE_MONTH = "2022-11-16"
CHATGPT = mdates.date2num(datetime(2022, 11, 30))
AGENTIC = mdates.date2num(datetime(2025, 5, 1))
SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"

OCCUPATIONS = [
    ("Management consultants (2421)", ["2421"]),
    ("ICT systems analysts (2511)", ["2511"]),
    ("Accountants and auditors (2411)", ["2411"]),
    ("Lawyers (2611)", ["2611"]),
]
AGE_ORDER = ["1", "2", "3", "4"]
AGE_LABELS = {"1": "21-30", "2": "31-40", "3": "41-50", "4": "51-60"}
AGE_COLORS = {"1": "#8C1515", "2": "#577590", "3": "#E54A2B", "4": "#E6A817"}


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
    """X-11-kjerne (jf. analysis/docs/sesongjustering.md)."""
    s = s.sort_values("date").copy()
    est = s[(s["date"] >= seas_from) & (s["date"] <= seas_to)]
    y = np.log(est["value"].to_numpy())
    m = est["date"].str[5:7].astype(int).to_numpy()
    n = len(est)
    w = np.ones(13)
    w[0] = w[12] = 0.5
    w = w / 12.0
    ma = np.full(n, np.nan)
    for i in range(6, n - 6):
        ma[i] = (y[i - 6:i + 7] * w).sum()
    d = y - ma
    ok = ~np.isnan(d)
    fac = np.array([d[ok & (m == mm)].mean() for mm in range(1, 13)])
    fac = fac - fac.mean()
    m_all = s["date"].str[5:7].astype(int).to_numpy()
    s["value"] = np.exp(np.log(s["value"].to_numpy()) - fac[m_all - 1])
    return s


def smooth3(s):
    s = s.sort_values("date").copy()
    s["value"] = s["value"].rolling(3, center=True, min_periods=2).mean()
    return s


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
    d = d[(d["sekt"] == 2) & (d["alder_gr"].isin(AGE_ORDER))
          & (d["variable"].isin(["count", "ny_jobb"]))]
    d = d.pivot_table(index=["date", "yrke4", "alder_gr"],
                      columns="variable", values="value").reset_index()
    d["nyvol"] = d["count"] * d["ny_jobb"]

    pop_src = pd.read_csv(POP_SRC, dtype={"age_group": str, "ai_q": str})
    pop_src = pop_src[(pop_src["sector"] == 2) & (pop_src["ai_q"] == "1")]
    pop_src["pop"] = pop_src["employment"] / pop_src["percap"]
    pop = pop_src.set_index(["date", "age_group"])["pop"]

    cols = [("Employment, per capita, seas. adj.", "emp", True),
            ("New hires, seas. adj., 3-mo MA", "nyvol", True),
            ("New-hire rate (%), seas. adj., 3-mo MA", "rate", False)]

    fig, axes = plt.subplots(4, 3, figsize=(16, 16), sharex=True)
    for i, (occ_label, codes) in enumerate(OCCUPATIONS):
        occ = d[d["yrke4"].isin(codes)].groupby(
            ["date", "alder_gr"], as_index=False).agg(
            count=("count", "sum"), nyvol=("nyvol", "sum"))
        occ["rate"] = 100.0 * occ["nyvol"] / occ["count"]
        n_base = int(occ[occ["date"] == BASE_MONTH]["count"].sum())

        for j, (title, kind, index_it) in enumerate(cols):
            ax = axes[i, j]
            ends = []
            for a in AGE_ORDER:
                s = occ[occ["alder_gr"] == a].copy()
                if kind == "emp":
                    s["value"] = [c / pop[(dt, a)] for dt, c
                                  in zip(s["date"], s["count"])]
                    s = seasonal_adjust(s[["date", "value"]])
                elif kind == "nyvol":
                    s["value"] = s["nyvol"]
                    s = smooth3(seasonal_adjust(s[["date", "value"]]))
                else:
                    s["value"] = s["rate"]
                    s = smooth3(seasonal_adjust(s[["date", "value"]]))
                s = s.sort_values("date")
                if index_it:
                    base = s.loc[s["date"] == BASE_MONTH, "value"]
                    s["value"] = 100.0 * s["value"] / float(base.iloc[0])
                dt = pd.to_datetime(s["date"])
                ax.plot(dt, s["value"], color=AGE_COLORS[a], linewidth=1.5)
                ends.append((dt.iloc[-1], s["value"].iloc[-1], a))
            if index_it:
                ax.axhline(y=100.0, color="#AAAAAA", linestyle="-",
                           linewidth=0.6)
            ax.axvline(x=CHATGPT, color="#555555", linestyle="--",
                       linewidth=0.8, alpha=0.8)
            ax.axvline(x=AGENTIC, color="#555555", linestyle=":",
                       linewidth=0.8, alpha=0.8)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax.xaxis.set_major_locator(mdates.YearLocator())
            if i == 0:
                ax.set_title(title, fontsize=15)
            label_line_ends(ax, ends)
        axes[i, 0].set_ylabel(f"{occ_label}\nindex (Nov 2022 = 100)",
                              fontsize=13)
        axes[i, 0].annotate(f"N = {n_base:,} (Nov 2022)".replace(",", " "),
                            xy=(0.97, 0.04), xycoords="axes fraction",
                            ha="right", va="bottom", fontsize=11,
                            color="#555555")
    axes[0, 0].annotate("ChatGPT", xy=(CHATGPT, 0.96),
                        xycoords=("data", "axes fraction"),
                        xytext=(4, 0), textcoords="offset points",
                        fontsize=10, color="#555555")
    axes[0, 0].annotate("Agentic", xy=(AGENTIC, 0.96),
                        xycoords=("data", "axes fraction"),
                        xytext=(4, 0), textcoords="offset points",
                        fontsize=10, color="#555555")
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "figure_consulting_hiring.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
