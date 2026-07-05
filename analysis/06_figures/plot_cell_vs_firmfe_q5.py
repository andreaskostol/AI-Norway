"""
plot_cell_vs_firmfe_q5.py

Purpose:
    Validation plot comparing cell-level Poisson event-study coefficients
    against the individual-level firm-FE Poisson event-study coefficients,
    for Q5 vs Q1, on the same 2x2 decade-age-group grid as the cell-level
    figure in section 4.6.
    Each panel shows:
      - Q5 coef from the cell-level model (blue)
      - Q5 coef from the firm-FE model (orange)
      - Difference, cell minus firm-FE (gray)
    plus 95% CI bands around the two estimates.
    Feeds the paper's Figure "fig:cell_vs_firmfe_q5"
    (figure_cell_vs_firmfe_q5_grid.pdf).

Inputs:
    analysis/output/coefficients/coef_microdata_es_decade_2026m02.csv
    analysis-indiv/from_secure_server/coefficients/coef_event_study_fepois.csv

The cell-level side reads the FROZEN 2026m02 coefficient snapshot, not the
live coef_microdata_es_decade.csv: the firm-FE side is fixed at the
2021m1-2026m2 secure-server vintage, so the cell side must stay on the same
window for the comparison to be like-with-like. Refresh the snapshot only
when the secure-server estimates are re-run on a longer window.

Outputs:
    analysis/output/figures/figure_cell_vs_firmfe_q5_grid.pdf

Usage:
    python analysis/06_figures/plot_cell_vs_firmfe_q5.py
"""

import os                                              # filesystem paths and mkdir
from datetime import datetime                          # build the k=0 anchor date

import matplotlib                                      # plotting backend selection
matplotlib.use("Agg")                                  # headless backend: write files, no display
import matplotlib.pyplot as plt                        # figure/axes plotting API
import matplotlib.dates as mdates                      # date axis formatting/locators
from matplotlib.lines import Line2D                    # custom legend handles
import pandas as pd                                    # read the coefficient CSVs, merge and build frames

BASE_DT = datetime(2022, 11, 1)                        # event time k = 0 (November 2022)
CHATGPT = mdates.date2num(BASE_DT)                     # k=0 as a matplotlib date number (vertical line)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")   # repo root, two levels up from this file
# Cell-level event-study coefficients (one row per age group x quintile x event time k).
# Frozen 2026m02 snapshot, matching the firm-FE vintage (see docstring).
CELL_CSV = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                        "coef_microdata_es_decade_2026m02.csv")
# Individual-level firm-FE event-study coefficients exported from the secure server.
FIRM_CSV = os.path.join(BASE_DIR, "analysis-indiv", "from_secure_server",
                        "coefficients", "coef_event_study_fepois.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")   # where the PDF is written

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",   # panel titles by age group
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]                               # age groups in panel order
COL_CELL = "#2171B5"                                   # blue = cell-level estimate
COL_FIRM = "#D55E00"                                   # orange = firm-FE estimate
COL_DIFF = "#444444"                                   # gray = cell-minus-firm-FE difference


def healy_style():
    # Apply the shared house figure style (Kieran Healy-inspired): white bg, serif fonts, light grid.
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
    # Ages that already have an explicit k=-1 row.
    have = {int(a) for a in df.loc[df["k"] == -1, "age"].to_numpy()}
    # Build a zero-anchored k=-1 row for every age that lacks one.
    rows = [{"age": a, "k": -1, coef_col: 0.0, se_col: 0.0}
            for a in {int(x) for x in df["age"].to_numpy()} if a not in have]
    if rows:                                           # only append if there were missing references
        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)   # add the synthetic baseline rows
    return df                                          # return the augmented frame


def load_q5() -> pd.DataFrame:
    cell = pd.read_csv(CELL_CSV)                       # cell-level coefficients
    firm = pd.read_csv(FIRM_CSV)                       # firm-FE coefficients
    cell = cell[cell["ai_q"] == 5].rename(columns={"age_group": "age"})   # keep Q5, unify age column name
    firm = firm[firm["ai_q"] == 5].rename(columns={"age_bin": "age"})     # keep Q5, unify age column name
    cell = cell[["age", "k", "coef", "se"]].rename(
        columns={"coef": "coef_cell", "se": "se_cell"})   # keep needed cols, suffix with _cell
    firm = firm[["age", "k", "coef", "se"]].rename(
        columns={"coef": "coef_firm", "se": "se_firm"})   # keep needed cols, suffix with _firm
    cell = _inject_ref(cell, "coef_cell", "se_cell")   # already anchored; no-op
    firm = _inject_ref(firm, "coef_firm", "se_firm")   # fepois omits k=-1: anchor it
    m = pd.merge(cell, firm, on=["age", "k"], how="outer")   # align the two models by age and event time
    m = m.sort_values(["age", "k"]).reset_index(drop=True)   # order by age then event time
    # Convert each event time k (months relative to Nov 2022) to a calendar date for the x-axis.
    m["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in m["k"]]
    m["diff"] = m["coef_cell"] - m["coef_firm"]        # gap between the two models at each (age, k)
    return m                                           # merged long frame ready to plot


def main():
    os.makedirs(FIG_DIR, exist_ok=True)                # ensure the output figures directory exists
    healy_style()                                      # set the shared plot styling
    d = load_q5()                                      # load and merge the two Q5 coefficient series

    # Collect every CI endpoint and the difference magnitude to size a symmetric y-axis.
    ymax_candidates = pd.concat([
        (d["coef_cell"] + 1.96 * d["se_cell"]).abs(),
        (d["coef_cell"] - 1.96 * d["se_cell"]).abs(),
        (d["coef_firm"] + 1.96 * d["se_firm"]).abs(),
        (d["coef_firm"] - 1.96 * d["se_firm"]).abs(),
        d["diff"].abs(),
    ])
    # Clamp the y-limit to at least 0.10 and at most 0.35.
    ymax = min(0.35, max(0.10, float(ymax_candidates.max(skipna=True))))

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))   # 2x2 grid, one panel per age group
    for ax, a in zip(axes.flatten(), AGE_ORDER):       # iterate panels paired with age groups
        sub = d[d["age"] == a].sort_values("date")     # this age group's rows, in date order

        cell = sub.dropna(subset=["coef_cell"])        # months where the cell-level estimate exists
        ax.fill_between(
            cell["date"],
            cell["coef_cell"] - 1.96 * cell["se_cell"],
            cell["coef_cell"] + 1.96 * cell["se_cell"],
            color=COL_CELL, alpha=0.12,
        )                                              # faint 95% CI band for the cell-level estimate
        ax.plot(cell["date"], cell["coef_cell"], color=COL_CELL, linewidth=1.6)   # cell-level point estimate

        firm = sub.dropna(subset=["coef_firm"])        # months where the firm-FE estimate exists
        ax.fill_between(
            firm["date"],
            firm["coef_firm"] - 1.96 * firm["se_firm"],
            firm["coef_firm"] + 1.96 * firm["se_firm"],
            color=COL_FIRM, alpha=0.12,
        )                                              # faint 95% CI band for the firm-FE estimate
        ax.plot(firm["date"], firm["coef_firm"], color=COL_FIRM, linewidth=1.6)   # firm-FE point estimate

        diff = sub.dropna(subset=["diff"])             # months where both models overlap (difference defined)
        ax.plot(diff["date"], diff["diff"], color=COL_DIFF,
                linewidth=1.8, linestyle="--")         # dashed line for the cell-minus-firm-FE gap

        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)   # zero reference line
        ax.axvline(x=CHATGPT, color="#888888", linestyle=":",
                   linewidth=0.8, alpha=0.8)           # ChatGPT launch marker (k=0)
        ax.set_title(AGE_TITLES[a])                    # label the panel with its age group
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))   # show years on the x-axis
        ax.xaxis.set_major_locator(mdates.YearLocator())   # one tick per year
        ax.set_ylim(-ymax, ymax)                       # symmetric y-axis across all panels

    # Three legend handles: cell-level, firm-FE, and their difference.
    handles = [
        Line2D([0], [0], color=COL_CELL, lw=2.5, label="Cell-level Q5"),
        Line2D([0], [0], color=COL_FIRM, lw=2.5, label="Firm-FE Q5"),
        Line2D([0], [0], color=COL_DIFF, lw=2.5, linestyle="--",
               label="Difference (cell - firm-FE)"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.0), fontsize=18)   # one shared legend across the top
    fig.autofmt_xdate(rotation=0, ha="center")         # keep year labels horizontal and centered
    fig.tight_layout(rect=(0, 0, 1, 0.95))             # tidy spacing, leaving room for the top legend
    out = os.path.join(FIG_DIR, "figure_cell_vs_firmfe_q5_grid.pdf")   # output PDF path
    fig.savefig(out, dpi=200, bbox_inches="tight")     # write the figure to disk
    plt.close(fig)                                     # free the figure
    print(f"Saved {out}")                              # progress message

    # Summary stats on the difference series
    print()                                            # blank line before the summary table
    print("Difference (cell - firm-FE) summary per age group, in log points:")   # table header line
    print("  age  | n_overlap |  mean |   sd  |   p5  |  p50  |  p95")   # column headers
    for a in AGE_ORDER:                                # one summary row per age group
        s = d[(d["age"] == a)].dropna(subset=["diff"])["diff"]   # this age group's defined differences
        if not len(s):                                 # skip age groups with no overlap
            continue                                   # nothing to summarize
        q = s.quantile([0.05, 0.50, 0.95])             # 5th, median, 95th percentiles
        print(f"  {a}    | {len(s):>9} | {s.mean():+.3f} | {s.std():.3f} "
              f"| {q[0.05]:+.3f} | {q[0.50]:+.3f} | {q[0.95]:+.3f}")   # formatted summary row


if __name__ == "__main__":                             # run main() only when executed as a script
    main()                                             # build the figure and print the diff summary
