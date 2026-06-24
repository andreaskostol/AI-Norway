"""
plot_firmfe_es_decade.py

Purpose:
    Plot the individual-level firm-FE Poisson event-study coefficients (decade
    age groups, private sector) as a four-panel grid, one panel per decade age
    group, with Q2-Q5 vs Q1 lines and 95% CI bands.
    Spec: foretak x q + foretak x month FE, clustered at foretak, separate
    fit per age_bin. Reference month: October 2022 (k = -1), reference
    quintile Q1. Direct counterpart to plot_microdata_es_decade.py.
    Feeds the paper's Figure "fig:firmfe_poisson_grid"
    (figure_firmfe_poisson_es_grid.pdf).

Inputs:
    analysis-indiv/from_secure_server/coefficients/coef_event_study_fepois.csv

Outputs:
    analysis/output/figures/figure_firmfe_poisson_es_grid.pdf

Usage:
    python analysis/06_figures/plot_firmfe_es_decade.py
"""

import os                                              # filesystem paths and mkdir

from datetime import datetime                          # build the k=0 anchor date

import matplotlib                                      # plotting backend selection
matplotlib.use("Agg")                                  # headless backend: write files, no display
import matplotlib.pyplot as plt                        # figure/axes plotting API
import matplotlib.dates as mdates                      # date axis formatting/locators
from matplotlib.lines import Line2D                    # custom legend handles
import pandas as pd                                    # read the coefficient CSV, build frames

BASE_DT = datetime(2022, 11, 1)   # event time k = 0 (November 2022)
CHATGPT = mdates.date2num(BASE_DT)                     # k=0 as a matplotlib date number (vertical line)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")   # repo root, two levels up from this file
# Firm-FE event-study coefficients exported from the secure server (one row per age_bin x quintile x k).
COEF = os.path.join(BASE_DIR, "analysis-indiv", "from_secure_server",
                    "coefficients", "coef_event_study_fepois.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")   # where the PDF is written

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",   # panel titles by age group
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]                               # age groups in panel order
QUINTILE_COLORS = {2: "#9ECAE1", 3: "#4292C6", 4: "#2171B5", 5: "#08306B"}   # darker blue = more AI-exposed quintile


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
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 22,
        "lines.linewidth": 1.4,
    })


def add_k_minus1_reference(d):
    """Inject the omitted reference point k=-1 (coef=0, se=0) for each
    (age_bin, ai_q) series. fepois drops the reference level, so the CSV has no
    k=-1 row; without this the event-study lines skip the October-2022 baseline
    and never anchor at 0 there (cf. _add_zero_reference in
    analysis-indiv/code/plot_secure_server_results.py)."""
    # Set of (age, quintile) pairs that already carry an explicit k=-1 row.
    have = {(int(a), int(q))
            for a, q in d.loc[d["k"] == -1, ["age_bin", "ai_q"]].to_numpy()}
    # All (age, quintile) combinations present anywhere in the data.
    combos = {(int(a), int(q)) for a, q in d[["age_bin", "ai_q"]].to_numpy()}
    # Build a zero-anchored k=-1 row for every combo that lacks one.
    rows = [{"age_bin": a, "ai_q": q, "k": -1, "coef": 0.0, "se": 0.0}
            for (a, q) in combos if (a, q) not in have]
    if rows:                                           # only append if there were missing references
        d = pd.concat([d, pd.DataFrame(rows)], ignore_index=True)   # add the synthetic baseline rows
    return d                                           # return the augmented frame


def main():
    os.makedirs(FIG_DIR, exist_ok=True)                # ensure the output figures directory exists
    healy_style()                                      # set the shared plot styling
    d = pd.read_csv(COEF)                              # load the firm-FE event-study coefficients
    d = add_k_minus1_reference(d)                      # anchor each series at 0 in the reference month
    d["hi"] = d["coef"] + 1.96 * d["se"]               # upper end of the 95% CI
    d["lo"] = d["coef"] - 1.96 * d["se"]               # lower end of the 95% CI
    # Convert each event time k (months relative to Nov 2022) to a calendar date for the x-axis.
    d["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in d["k"]]
    # Symmetric y-limit: at least 0.10, at most 0.35, otherwise the largest CI endpoint magnitude.
    ymax = min(0.35, max(0.10, d["hi"].abs().max(), d["lo"].abs().max()))

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))   # 2x2 grid, one panel per age group
    for ax, a in zip(axes.flatten(), AGE_ORDER):       # iterate panels paired with age groups
        sub = d[d["age_bin"] == a]                     # rows for this age group only
        for q in [2, 3, 4, 5]:                         # plot one line per exposure quintile (Q1 is the base)
            s = sub[sub["ai_q"] == q].sort_values("date")   # this quintile's series, in date order
            if not len(s):                             # skip if this age x quintile has no rows
                continue                               # nothing to draw
            ax.fill_between(s["date"], s["lo"], s["hi"],
                            color=QUINTILE_COLORS[q], alpha=0.12)   # faint 95% CI band
            ax.plot(s["date"], s["coef"],
                    color=QUINTILE_COLORS[q], linewidth=1.6)   # the point-estimate line
        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)   # zero reference line
        ax.axvline(x=CHATGPT, color="#D55E00", linestyle="--",
                   linewidth=0.8, alpha=0.8)           # ChatGPT launch marker (k=0)
        ax.set_title(AGE_TITLES[a])                    # label the panel with its age group
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))   # show years on the x-axis
        ax.xaxis.set_major_locator(mdates.YearLocator())   # one tick per year
        ax.set_ylim(-ymax, ymax)                       # symmetric y-axis across all panels

    # Build shared legend handles: label Q5 "most exposed", Q2 "vs Q1", Q3/Q4 just "Qk".
    handles = [Line2D([0], [0], color=QUINTILE_COLORS[q], lw=2.5,
                      label=f"Q{q}" + (" (most exposed)" if q == 5 else
                                       " (vs Q1)" if q == 2 else ""))
               for q in [2, 3, 4, 5]]
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.0), fontsize=20)   # one shared legend across the top
    fig.autofmt_xdate(rotation=0, ha="center")         # keep year labels horizontal and centered
    fig.tight_layout(rect=(0, 0, 1, 0.96))             # tidy spacing, leaving room for the top legend
    out = os.path.join(FIG_DIR, "figure_firmfe_poisson_es_grid.pdf")   # output PDF path
    fig.savefig(out, dpi=200, bbox_inches="tight")     # write the figure to disk
    plt.close(fig)                                     # free the figure
    print(f"Saved {out}")                              # progress message


if __name__ == "__main__":                             # run main() only when executed as a script
    main()                                             # build and save the figure
