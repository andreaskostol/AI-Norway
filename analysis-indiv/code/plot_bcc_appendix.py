"""BCC-replication appendix figures 1, 2, 3, 5 on Norwegian register data.

Matches Brynjolfsson-Chandar-Chen (2025): full-time private-sector workers,
BCC's six age bins, employment/compensation indexed to October 2022 = 1.00,
monthly, Eloundou GPT-4 beta quintiles (Figs 2, 5) and Anthropic/Handa
usage/automation/augmentation quintiles (Fig 3), with a pooled "Overall" line.

Inputs (from A1_bcc_descriptive_agg.R, in from_secure_server/coefficients/):
    bcc_desc_employment.csv  measure, group, bcc_age, ym, count, k
    bcc_desc_wage.csv        group, bcc_age, ym, mean_wage, n, k
    bcc_desc_occ.csv         yrke4, occ_label, bcc_age, ym, count, k

Outputs (analysis-indiv/output/bcc_appendix/):
    fig_bcc_1_occ.pdf        2 occupation panels x 6 age lines
    fig_bcc_2_eloundou.pdf   6 age panels, 5 quintiles + Overall
    fig_bcc_3_handa.pdf      age 22-25, 3 panels (usage/auto/augm) + Overall
    fig_bcc_5_comp.pdf       6 age panels, mean cash wage, 5 quintiles + Overall

Run: python analysis-indiv/code/plot_bcc_appendix.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COEF = ROOT / "analysis-indiv" / "from_secure_server" / "coefficients"
OUTDIR = ROOT / "analysis-indiv" / "output" / "bcc_appendix"

K0 = pd.Timestamp("2022-11-01")            # k = 0 = Nov 2022 (ChatGPT)
BASE_K = -1                                # index base = Oct 2022 (k = -1)
BCC_AGE = {1: "22-25", 2: "26-30", 3: "31-34", 4: "35-40", 5: "41-49", 6: "50-55"}
AGE_ORDER = [1, 2, 3, 4, 5, 6]
# Grayscale gradient, darker = more exposed (BCC convention); Overall in red.
QSHADE = {1: "#BBBBBB", 2: "#999999", 3: "#6E6E6E", 4: "#454545", 5: "#000000"}
OVERALL = "#C1272D"
# Age lines for the two-occupation Fig 1 (sequential blue→red by age).
ACOLOR = {1: "#1b4965", 2: "#5fa8d3", 3: "#62b6b7", 4: "#e6a817",
          5: "#e07a5f", 6: "#8c1c13"}


def k_to_date(k):
    return K0 + pd.DateOffset(months=int(k))


def style():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.color": "#E2E2E2",
        "grid.linewidth": 0.6, "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        # These grids are drawn 15 in wide but embedded at \textwidth, so the
        # on-page scale is ~0.4; sizes are set large so they stay legible after
        # shrinking (consistent with the Appendix A population figure).
        "font.size": 24, "axes.titlesize": 26, "axes.labelsize": 24,
        "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 20,
        "figure.titlesize": 22, "lines.linewidth": 2.4,
    })


def index_to_base(g):
    """Index a (sorted-by-k) series to value at BASE_K = 1.0."""
    g = g.sort_values("k")
    base = g.loc[g["k"] == BASE_K, "val"]
    if not len(base):
        return None
    g = g.copy()
    g["idx"] = g["val"] / float(base.iloc[0])
    g["date"] = g["k"].map(k_to_date)
    return g


def fmt_axis(ax):
    ax.axhline(1.0, color="#999999", lw=0.6)
    ax.axvline(K0, color="#555555", ls="--", lw=0.8)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def ydense(ax, n=9):
    """More y-axis tick labels (nice round values) on the index/coef panels."""
    ax.yaxis.set_major_locator(MaxNLocator(nbins=n))


def quintile_panel(ax, sub, valcol):
    """sub has columns group, k, <valcol>; draw 5 quintile lines + Overall."""
    sub = sub.rename(columns={valcol: "val"})
    for q in [1, 2, 3, 4, 5]:
        g = index_to_base(sub[sub["group"] == str(q)])
        if g is not None:
            ax.plot(g["date"], g["idx"], color=QSHADE[q], label=f"Q{q}")
    g = index_to_base(sub[sub["group"] == "overall"])
    if g is not None:
        ax.plot(g["date"], g["idx"], color=OVERALL, lw=1.8, label="Overall")
    fmt_axis(ax)


def fig2_eloundou(emp):
    e = emp[emp["measure"] == "eloundou"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True, sharey=True)
    for ax, age in zip(axes.flat, AGE_ORDER):
        quintile_panel(ax, e[e["bcc_age"] == age], "count")
        ydense(ax)
        ax.set_title(BCC_AGE[age])
    for ax in axes[:, 0]:
        ax.set_ylabel("Employment (Oct 2022 = 1)")
    axes.flat[2].legend(fontsize=18, ncol=2, loc="upper left")
    fig.suptitle("BCC Fig 2 — employment by Eloundou exposure quintile, full-time private", y=1.01)
    _save(fig, "fig_bcc_2_eloundou.pdf")


def fig3_handa(emp):
    panels = [("handa_usage", "A. Anthropic usage quintile"),
              ("handa_auto", "B. Automation quintile"),
              ("handa_augm", "C. Augmentation quintile")]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6), sharey=True)
    for ax, (meas, title) in zip(axes, panels):
        quintile_panel(ax, emp[(emp["measure"] == meas) & (emp["bcc_age"] == 1)], "count")
        ydense(ax)
        ax.set_title(title)
    axes[0].set_ylabel("Employment (Oct 2022 = 1)")
    axes[-1].legend(fontsize=18, ncol=2, loc="best")
    fig.suptitle("BCC Fig 3 — employment by Anthropic/Handa index, age 22-25, full-time private", y=1.02)
    _save(fig, "fig_bcc_3_handa.pdf")


def fig5_comp(wage, valcol, label, suffix, ymax=1.6):
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True, sharey=True)
    for ax, age in zip(axes.flat, AGE_ORDER):
        quintile_panel(ax, wage[wage["bcc_age"] == age], valcol)
        ax.set_title(BCC_AGE[age])
    # Cap y: keeps the genuine June holiday-pay (feriepenger) seasonal peaks
    # (~1.5) visible while clipping the anomalous 2023-07 Q1 35-40 mean spike
    # (index ~2.6). sharey=True propagates to all panels.
    axes.flat[0].set_ylim(0.8, ymax)
    short = label.split(" (")[0]                  # drop the winsorization parenthetical
    for ax in axes[:, 0]:
        ax.set_ylabel(f"{short} (Oct 2022 = 1)")  # full detail stays in the suptitle
    axes.flat[2].legend(fontsize=18, ncol=2, loc="upper left")
    fig.suptitle(f"BCC Fig 5 — {label} (nominal) by exposure quintile, full-time private", y=1.01)
    _save(fig, f"fig_bcc_5_comp{suffix}.pdf")


def fig4_event_study(coef):
    """BCC Fig 4: Poisson firm-FE event study, 6 age panels, Q2-Q5 vs Q1.
    coef has age_bin, k, ai_q, coef, se. Inject k=-1 = 0 so lines pass through
    the reference (fixest omits ref=-1)."""
    keys = coef[["age_bin", "ai_q"]].drop_duplicates()
    ref = keys.assign(k=-1, coef=0.0, se=0.0)
    c = pd.concat([coef[["age_bin", "ai_q", "k", "coef", "se"]], ref],
                  ignore_index=True)
    c["lo"] = c["coef"] - 1.96 * c["se"]
    c["hi"] = c["coef"] + 1.96 * c["se"]
    c["date"] = c["k"].map(k_to_date)
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True, sharey=True)
    for ax, age in zip(axes.flat, AGE_ORDER):
        for q in [2, 3, 4, 5]:
            s = c[(c["age_bin"] == age) & (c["ai_q"] == q)].sort_values("k")
            if s.empty:
                continue
            ax.plot(s["date"], s["coef"], color=QSHADE[q], label=f"Q{q}")
            ax.fill_between(s["date"], s["lo"], s["hi"], color=QSHADE[q],
                            alpha=0.10, linewidth=0)
        ax.axhline(0, color="#999999", lw=0.6)
        ax.axvline(K0, color="#555555", ls="--", lw=0.8)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ydense(ax)
        ax.set_title(BCC_AGE[age])
    for ax in axes[:, 0]:
        ax.set_ylabel("γ_{q,k}  (log points, vs Q1)")
    axes.flat[2].legend(fontsize=18, ncol=2, loc="best")
    fig.suptitle("BCC Fig 4 — Poisson firm-FE event study (count_ft, in_bcc_full), vs Q1, k=−1 = Oct 2022", y=1.01)
    _save(fig, "fig_bcc_4_es.pdf")


def fig1_occ(occ):
    occs = occ["occ_label"].dropna().unique()
    fig, axes = plt.subplots(1, len(occs), figsize=(7 * len(occs), 4.6), sharey=True)
    if len(occs) == 1:
        axes = [axes]
    for ax, lab in zip(axes, occs):
        sub = occ[occ["occ_label"] == lab].rename(columns={"count": "val"})
        for age in AGE_ORDER:
            g = index_to_base(sub[sub["bcc_age"] == age])
            if g is not None:
                ax.plot(g["date"], g["idx"], color=ACOLOR[age], label=BCC_AGE[age])
        fmt_axis(ax)
        ydense(ax)
        ax.set_title(f"{lab} (normalized)")
    axes[0].set_ylabel("Headcount (Oct 2022 = 1)")
    axes[-1].legend(title="Age", fontsize=18, loc="best")
    fig.suptitle("BCC Fig 1 — occupation case studies by age, full-time private", y=1.02)
    _save(fig, "fig_bcc_1_occ.pdf")


def _save(fig, name):
    fig.tight_layout()
    out = OUTDIR / name
    fig.savefig(out, dpi=150, bbox_inches="tight")                 # PDF for the paper
    fig.savefig(OUTDIR / name.replace(".pdf", ".png"), dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    style()
    emp = pd.read_csv(COEF / "bcc_desc_employment.csv", dtype={"group": str})
    wage = pd.read_csv(COEF / "bcc_desc_wage.csv", dtype={"group": str})
    occ = pd.read_csv(COEF / "bcc_desc_occ.csv")
    fig1_occ(occ)
    fig2_eloundou(emp)
    fig3_handa(emp)
    fig5_comp(wage, "mean_wage", "Mean cash wage (winsorized occ×month p99.9)", "")
    es_path = COEF / "coef_bcc_event_study.csv"
    if es_path.exists():
        fig4_event_study(pd.read_csv(es_path))
    else:
        print(f"(skipping Fig 4 -- {es_path.name} not present yet; run A3)")


if __name__ == "__main__":
    main()
