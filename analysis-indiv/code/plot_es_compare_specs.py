"""Event-study comparison: employment gamma_{q,k} across the four DiD specs.

Dynamic counterpart to fig_comparison_employment (DESIGN_CHOICES.md §22). Four
specifications, all on the BCC reference (Q1 omitted, k = -1 = Oct 2022),
private sector, employment count:

    firm-FE       coef_event_study_fepois.csv          (firm x q + firm x t FE)
    cell restr    coef_es_byage_cellspec.csv (restricted)        yrke4 + month FE
    cell unrestr  coef_es_byage_cellspec.csv (unrestricted_priv) yrke4 + month FE
    microdata.no  coef_microdata_es_cell_q1_full.csv (sector 2)  yrke4 + month FE

All quintiles shown (Q2-Q5 vs Q1). Outputs to analysis-indiv/output/:
    fig_es_compare_age{1..4}.png  one figure per age group, 4 spec panels
    fig_es_compare_grid.png       4 ages (rows) x 4 specs (cols), lines only

Run: python analysis-indiv/code/plot_es_compare_specs.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FSS = ROOT / "analysis-indiv" / "from_secure_server" / "coefficients"
FIRM = FSS / "coef_event_study_fepois.csv"
CELL = FSS / "coef_es_byage_cellspec.csv"
MICRO = ROOT / "analysis" / "output" / "coefficients" / "coef_microdata_es_cell_q1_full.csv"
OUTDIR = ROOT / "analysis-indiv" / "output"

SPEC_ORDER = ["firm-FE", "cell restr", "cell unrestr", "microdata.no"]
SPEC_LABEL = {
    "firm-FE": "7b firm-FE (firm×q + firm×t)",
    "cell restr": "7d cell-spec, restricted",
    "cell unrestr": "7d cell-spec, unrestricted",
    "microdata.no": "microdata.no cell",
}
AGE_LABEL = {1: "21-30", 2: "31-40", 3: "41-50", 4: "51-60"}
# Canaries Flourish palette; Q1 is the omitted reference so only Q2-Q5 drawn.
QCOLOR = {2: "#577590", 3: "#E54A2B", 4: "#E6A817", 5: "#401415"}
QUINTS = [2, 3, 4, 5]
K0 = pd.Timestamp("2022-11-01")          # event time k = 0 = ChatGPT (Nov 2022)


def k_to_date(k):
    return K0 + pd.DateOffset(months=int(k))


def load() -> pd.DataFrame:
    frames = []

    f = pd.read_csv(FIRM)
    f = f[["age_bin", "ai_q", "k", "coef", "se"]].copy()
    f["spec"] = "firm-FE"
    frames.append(f)

    c = pd.read_csv(CELL)
    c = c[c["outcome"] == "employment"].copy()
    c["spec"] = c["variant"].map({"restricted": "cell restr",
                                  "unrestricted_priv": "cell unrestr"})
    frames.append(c[["age_bin", "ai_q", "k", "coef", "se", "spec"]])

    m = pd.read_csv(MICRO)
    m = m[m["sector"] == 2].rename(columns={"age_group": "age_bin"}).copy()
    m["spec"] = "microdata.no"
    frames.append(m[["age_bin", "ai_q", "k", "coef", "se", "spec"]])

    df = pd.concat(frames, ignore_index=True)
    for col in ("age_bin", "ai_q", "k"):
        df[col] = df[col].astype(int)

    # fixest omits the reference period (ref = -1), so each series has NO row at
    # k = -1. Inject it explicitly with coef = 0 (the reference is normalized to
    # zero by construction) so every line passes through 0 at k = -1.
    keys = df[["spec", "age_bin", "ai_q"]].drop_duplicates()
    ref = keys.assign(k=-1, coef=0.0, se=0.0)
    df = pd.concat([df, ref], ignore_index=True)

    df["lo"] = df["coef"] - 1.96 * df["se"]
    df["hi"] = df["coef"] + 1.96 * df["se"]
    df["date"] = df["k"].map(k_to_date)
    return df


def style():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.color": "#DDDDDD",
        "grid.linewidth": 0.6, "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 12, "axes.titlesize": 13,
    })


def draw(ax, sub, ribbons: bool):
    for q in QUINTS:
        s = sub[sub["ai_q"] == q].sort_values("k")
        if s.empty:
            continue
        ax.plot(s["date"], s["coef"], color=QCOLOR[q], lw=1.4, label=f"Q{q}")
        if ribbons:
            ax.fill_between(s["date"], s["lo"], s["hi"], color=QCOLOR[q], alpha=0.10,
                            linewidth=0)
    ax.axhline(0, color="#888888", lw=0.6)
    ax.axvline(K0, color="#555555", ls="--", lw=0.8)   # ChatGPT (k=0 = Nov 2022)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator((1, 4, 7, 10)))
    ax.set_xlabel("Month")


def per_age_figures(df):
    for age in sorted(df["age_bin"].unique()):
        fig, axes = plt.subplots(1, 4, figsize=(20, 4.6), sharey=True)
        for ax, spec in zip(axes, SPEC_ORDER):
            draw(ax, df[(df["age_bin"] == age) & (df["spec"] == spec)], ribbons=True)
            ax.set_title(SPEC_LABEL[spec])
        axes[0].set_ylabel("Employment γ_{q,k} (log points, vs Q1)")
        axes[-1].legend(title="vs Q1", fontsize=10, loc="best")
        fig.suptitle(f"Employment event study by AI-exposure quintile — age {AGE_LABEL[age]} "
                     f"(Q1 reference, k=−1 = Oct 2022)", y=1.02, fontsize=14)
        fig.tight_layout()
        out = OUTDIR / f"fig_es_compare_age{age}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote {out}")


def grid_figure(df):
    ages = sorted(df["age_bin"].unique())
    fig, axes = plt.subplots(len(ages), 4, figsize=(20, 16), sharex=True, sharey="row")
    for i, age in enumerate(ages):
        for j, spec in enumerate(SPEC_ORDER):
            ax = axes[i, j]
            draw(ax, df[(df["age_bin"] == age) & (df["spec"] == spec)], ribbons=False)
            if i == 0:
                ax.set_title(SPEC_LABEL[spec])
            if i != len(ages) - 1:
                ax.set_xlabel("")
        axes[i, 0].set_ylabel(f"age {AGE_LABEL[age]}\nγ_{{q,k}} vs Q1")
    axes[0, -1].legend(title="vs Q1", fontsize=9, loc="best")
    fig.suptitle("Employment event study by AI-exposure quintile: four specifications "
                 "(Q1 reference, k=−1 = Oct 2022, private sector)", y=1.01, fontsize=15)
    fig.tight_layout()
    out = OUTDIR / "fig_es_compare_grid.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    style()
    df = load()
    per_age_figures(df)
    grid_figure(df)


if __name__ == "__main__":
    main()
