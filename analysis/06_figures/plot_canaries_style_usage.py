"""
plot_canaries_style_usage.py

Norwegian version of the Stanford Canaries Dashboard usage figures
("Employment Index by Anthropic usage pattern"): occupations grouped by
observed Claude usage (Anthropic Economic Index via Handa et al. 2025,
release 2025-03-27) instead of Eloundou exposure.

Grouping follows BCC (2025) Figure 3, Panels B/C: per usage pattern p in
{augmentation, automation}, occupations are ranked by the SHARE of the
occupation's Claude queries classified as p (automation_share /
augmentation_share), quintiles equal-weighted by occupation. "No usage"
= occupations in the canaries sample (Eloundou-mapped) without Handa
coverage, i.e. below the minimum query threshold (BCC's category 0).
BCC collapse automation Q1+Q2 because >20 percent of their SOC codes
have automation share exactly 0; our STYRK-level shares have only 16.5
percent zeros (SOC-to-STYRK averaging dilutes them) and the Q1 boundary
is 0.122, so the collapse does not bind and we keep five quintiles.
Grouping saved to data/ai_exposure/styrk08_usage_groups.csv.

Figures: 2x2 decade age-group grid per pattern, six lines (No usage +
usage quintiles), employment index Nov 2022 = 100, private sector.
Variants: raw (Stanford's method) and per capita seasonally adjusted.

Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
        data/ai_exposure/styrk08_handa_mapping.csv
        data/ai_exposure/styrk08_eloundou_beta_mapping.csv
        analysis/output/figure_data/fig_employment_by_age_quintile.csv
Output: analysis/output/figures/figure_canaries_style_usage_{augmentation,automation}{,_percap_sa}.pdf
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
HANDA = os.path.join(BASE_DIR, "data", "ai_exposure",
                     "styrk08_handa_mapping.csv")
ELOUNDOU = os.path.join(BASE_DIR, "data", "ai_exposure",
                        "styrk08_eloundou_beta_mapping.csv")
POP_SRC = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                       "fig_employment_by_age_quintile.csv")
GROUPS_OUT = os.path.join(BASE_DIR, "data", "ai_exposure",
                          "styrk08_usage_groups.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

BASE_MONTH = "2022-11-16"
CHATGPT = mdates.date2num(datetime(2022, 11, 30))
SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"

AGE_ORDER = ["1", "2", "3", "4"]
AGE_TITLES = {"1": "21-30", "2": "31-40", "3": "41-50", "4": "51-60"}
GROUP_ORDER = ["No usage", "Q1", "Q2", "Q3", "Q4", "Q5"]
GROUP_LABELS = {"No usage": "No usage", "Q1": "Q1 (least usage)",
                "Q2": "Q2", "Q3": "Q3", "Q4": "Q4",
                "Q5": "Q5 (most usage)"}
GROUP_COLORS = {"No usage": "#888780", "Q1": "#8C1515", "Q2": "#577590",
                "Q3": "#E54A2B", "Q4": "#E6A817", "Q5": "#401415"}


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
        "xtick.labelsize": 12, "ytick.labelsize": 12, "legend.fontsize": 13,
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


def label_line_ends(ax, ends, fontsize=10):
    if not ends:
        return
    x = max(e[0] for e in ends)
    ymin, ymax = ax.get_ylim()
    gap = 0.06 * (ymax - ymin)
    items = sorted(ends, key=lambda e: e[1])
    ys, prev = [], -1e18
    for _, yv, _g in items:
        ny = yv if yv >= prev + gap else prev + gap
        ys.append(ny)
        prev = ny
    if ys[-1] > ymax:
        ax.set_ylim(top=ys[-1] + 0.03 * (ymax - ymin))
    for (_, _yv, g), ny in zip(items, ys):
        lab = "No use" if g == "No usage" else g
        ax.annotate(lab, xy=(x, ny), xytext=(5, 0),
                    textcoords="offset points", va="center", ha="left",
                    color=GROUP_COLORS[g], fontsize=fontsize,
                    fontweight="bold", annotation_clip=False)
    ax.set_xlim(right=x + pd.Timedelta(days=240))


def build_groups():
    """Brukskvintiler per moenster + No usage, lagres til CSV."""
    el = pd.read_csv(ELOUNDOU, dtype={"styrk08": str})
    universe = set(el.loc[el["quintile"].notna(), "styrk08"])
    h = pd.read_csv(HANDA, dtype={"styrk08": str})
    h = h[h["styrk08"].isin(universe)].copy()
    out = pd.DataFrame({"styrk08": sorted(universe)})
    for pat in ["augmentation", "automation"]:
        q = pd.qcut(h[f"{pat}_share"].rank(method="first"), 5,
                    labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
        grp = dict(zip(h["styrk08"], q.astype(str)))
        out[f"group_{pat}"] = [grp.get(c, "No usage")
                               for c in out["styrk08"]]
        share = dict(zip(h["styrk08"], h[f"{pat}_share"]))
        out[f"{pat}_share"] = [share.get(c, np.nan) for c in out["styrk08"]]
    out.to_csv(GROUPS_OUT, index=False)
    print(f"Saved {GROUPS_OUT} ({len(out)} codes, "
          f"{(out['group_augmentation'] == 'No usage').sum()} no-usage)")
    return out


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    groups = build_groups()

    d = pd.read_csv(DATA, dtype={"yrke4": str, "alder_gr": str, "sekt": int})
    d = d[(d["variable"] == "count") & (d["sekt"] == 2)
          & (d["alder_gr"].isin(AGE_ORDER))]
    d = d.merge(groups, left_on="yrke4", right_on="styrk08")

    pop_src = pd.read_csv(POP_SRC, dtype={"age_group": str, "ai_q": str})
    pop_src = pop_src[(pop_src["sector"] == 2) & (pop_src["ai_q"] == "1")]
    pop_src["pop"] = pop_src["employment"] / pop_src["percap"]
    pop = pop_src.set_index(["date", "age_group"])["pop"]

    for pat in ["augmentation", "automation"]:
        agg = d.groupby(["date", "alder_gr", f"group_{pat}"],
                        as_index=False)["value"].sum()
        for variant, suffix in [("raw", ""), ("percap_sa", "_percap_sa")]:
            fig, axes = plt.subplots(2, 2, figsize=(12, 10),
                                     sharex=True, sharey=True)
            panel_ends = []
            for ax, a in zip(axes.flatten(), AGE_ORDER):
                ends = []
                for g in GROUP_ORDER:
                    s = agg[(agg["alder_gr"] == a)
                            & (agg[f"group_{pat}"] == g)][["date", "value"]]
                    s = s.sort_values("date").copy()
                    if not len(s):
                        continue
                    if variant == "percap_sa":
                        s["value"] = [v / pop[(dt, a)] for dt, v
                                      in zip(s["date"], s["value"])]
                        s = seasonal_adjust(s)
                    base = s.loc[s["date"] == BASE_MONTH, "value"]
                    idx = 100.0 * s["value"] / float(base.iloc[0])
                    dt = pd.to_datetime(s["date"])
                    ax.plot(dt, idx, color=GROUP_COLORS[g], linewidth=1.5)
                    ends.append((dt.iloc[-1], idx.iloc[-1], g))
                panel_ends.append((ax, ends))
                ax.axhline(y=100.0, color="#AAAAAA", linestyle="-",
                           linewidth=0.6)
                ax.axvline(x=CHATGPT, color="#555555", linestyle="--",
                           linewidth=0.8, alpha=0.8)
                ax.set_title(AGE_TITLES[a])
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
                ax.xaxis.set_major_locator(mdates.YearLocator())
            for ax, ends in panel_ends:
                label_line_ends(ax, ends)
            for ax in axes[:, 0]:
                ax.set_ylabel("Employment index (Nov 2022 = 100)")
            fig.autofmt_xdate(rotation=0, ha="center")
            fig.tight_layout()
            out = os.path.join(
                FIG_DIR, f"figure_canaries_style_usage_{pat}{suffix}.pdf")
            fig.savefig(out, dpi=200, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved {out}")


if __name__ == "__main__":
    main()
