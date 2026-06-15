"""
plot_cell_vs_firmfe_q5.py

Validation plot: cell-level Poisson event-study coefficients (from
coef_microdata_es_decade.csv) against the individual-level firm-FE
Poisson event-study coefficients (from
analysis-indiv/from_secure_server/coefficients/coef_event_study_fepois.csv),
for Q5 vs Q1, on the same 2x2 decade-age-group grid as the cell-level
figure in section 4.6.

Each panel shows:
  - Q5 coef from the cell-level model (blue)
  - Q5 coef from the firm-FE model (orange)
  - Difference, cell minus firm-FE (gray)
plus 95% CI bands around the two estimates.

Output: analysis/output/figures/figure_cell_vs_firmfe_q5_grid.pdf
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import pandas as pd

BASE_DT = datetime(2022, 11, 1)
CHATGPT = mdates.date2num(BASE_DT)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
CELL_CSV = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                        "coef_microdata_es_decade.csv")
FIRM_CSV = os.path.join(BASE_DIR, "analysis-indiv", "from_secure_server",
                        "coefficients", "coef_event_study_fepois.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]
COL_CELL = "#2171B5"
COL_FIRM = "#D55E00"
COL_DIFF = "#444444"


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
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 20,
        "lines.linewidth": 1.6,
    })


def _inject_ref(df, coef_col, se_col):
    """Add the omitted reference point k=-1 (coef=0, se=0) per age where missing.
    fepois drops the reference level, so the firm-FE CSV has no k=-1 row; without
    this the firm-FE and difference lines skip the October-2022 baseline and fail
    to anchor at 0 alongside the cell-level line."""
    have = {int(a) for a in df.loc[df["k"] == -1, "age"].to_numpy()}
    rows = [{"age": a, "k": -1, coef_col: 0.0, se_col: 0.0}
            for a in {int(x) for x in df["age"].to_numpy()} if a not in have]
    if rows:
        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    return df


def load_q5() -> pd.DataFrame:
    cell = pd.read_csv(CELL_CSV)
    firm = pd.read_csv(FIRM_CSV)
    cell = cell[cell["ai_q"] == 5].rename(columns={"age_group": "age"})
    firm = firm[firm["ai_q"] == 5].rename(columns={"age_bin": "age"})
    cell = cell[["age", "k", "coef", "se"]].rename(
        columns={"coef": "coef_cell", "se": "se_cell"})
    firm = firm[["age", "k", "coef", "se"]].rename(
        columns={"coef": "coef_firm", "se": "se_firm"})
    cell = _inject_ref(cell, "coef_cell", "se_cell")   # already anchored; no-op
    firm = _inject_ref(firm, "coef_firm", "se_firm")   # fepois omits k=-1: anchor it
    m = pd.merge(cell, firm, on=["age", "k"], how="outer")
    m = m.sort_values(["age", "k"]).reset_index(drop=True)
    m["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in m["k"]]
    m["diff"] = m["coef_cell"] - m["coef_firm"]
    return m


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()
    d = load_q5()

    ymax_candidates = pd.concat([
        (d["coef_cell"] + 1.96 * d["se_cell"]).abs(),
        (d["coef_cell"] - 1.96 * d["se_cell"]).abs(),
        (d["coef_firm"] + 1.96 * d["se_firm"]).abs(),
        (d["coef_firm"] - 1.96 * d["se_firm"]).abs(),
        d["diff"].abs(),
    ])
    ymax = min(0.35, max(0.10, float(ymax_candidates.max(skipna=True))))

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        sub = d[d["age"] == a].sort_values("date")

        cell = sub.dropna(subset=["coef_cell"])
        ax.fill_between(
            cell["date"],
            cell["coef_cell"] - 1.96 * cell["se_cell"],
            cell["coef_cell"] + 1.96 * cell["se_cell"],
            color=COL_CELL, alpha=0.12,
        )
        ax.plot(cell["date"], cell["coef_cell"], color=COL_CELL, linewidth=1.6)

        firm = sub.dropna(subset=["coef_firm"])
        ax.fill_between(
            firm["date"],
            firm["coef_firm"] - 1.96 * firm["se_firm"],
            firm["coef_firm"] + 1.96 * firm["se_firm"],
            color=COL_FIRM, alpha=0.12,
        )
        ax.plot(firm["date"], firm["coef_firm"], color=COL_FIRM, linewidth=1.6)

        diff = sub.dropna(subset=["diff"])
        ax.plot(diff["date"], diff["diff"], color=COL_DIFF,
                linewidth=1.8, linestyle="--")

        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=CHATGPT, color="#888888", linestyle=":",
                   linewidth=0.8, alpha=0.8)
        ax.set_title(AGE_TITLES[a])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(-ymax, ymax)

    handles = [
        Line2D([0], [0], color=COL_CELL, lw=2.5, label="Cell-level Q5"),
        Line2D([0], [0], color=COL_FIRM, lw=2.5, label="Firm-FE Q5"),
        Line2D([0], [0], color=COL_DIFF, lw=2.5, linestyle="--",
               label="Difference (cell - firm-FE)"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.0), fontsize=18)
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = os.path.join(FIG_DIR, "figure_cell_vs_firmfe_q5_grid.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")

    # Summary stats on the difference series
    print()
    print("Difference (cell - firm-FE) summary per age group, in log points:")
    print("  age  | n_overlap |  mean |   sd  |   p5  |  p50  |  p95")
    for a in AGE_ORDER:
        s = d[(d["age"] == a)].dropna(subset=["diff"])["diff"]
        if not len(s):
            continue
        q = s.quantile([0.05, 0.50, 0.95])
        print(f"  {a}    | {len(s):>9} | {s.mean():+.3f} | {s.std():.3f} "
              f"| {q[0.05]:+.3f} | {q[0.50]:+.3f} | {q[0.95]:+.3f}")


if __name__ == "__main__":
    main()
