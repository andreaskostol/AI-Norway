"""
plot_recursive_kiindeks.py

Purpose:
    Real-time KI-indeks (the kiindeksen.no headline number) re-estimated on
    expanding data vintages, with a +/-1.96 occupation-bootstrap standard-error
    band. The point estimate drifts from about +1.7 pp (data through Jan 2025)
    to about -0.2 pp (Feb 2026) but the band spans zero in every vintage.
    Appendix figure for the Discussion's "Companion Dashboard" subsection
    (fig:recursive_kiindeks, figure_recursive_kiindeks_ci.pdf).
    No title/notes baked into the PDF (the caption lives in the .tex).

Inputs:
    analysis/output/coefficients/coef_recursive_kiindeks_headline.csv
    (built by recursive_kiindeks_headline.py)

Outputs:
    analysis/output/figures/figure_recursive_kiindeks_ci.pdf

Usage:
    python analysis/06_figures/plot_recursive_kiindeks.py
"""

import os                                              # filesystem paths and mkdir
from datetime import date                              # parse cutoff strings into dates

import matplotlib                                      # plotting backend selection
matplotlib.use("Agg")                                  # headless backend: write files, no display
import matplotlib.pyplot as plt                        # figure/axes plotting API
import matplotlib.dates as mdates                      # date axis formatting/locators
import pandas as pd                                    # read the recursive-estimate CSV

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")   # repo root, two levels up from this file
# Recursive KI-indeks point estimates and bootstrap SEs, one row per data vintage (cutoff).
DATA = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                    "coef_recursive_kiindeks_headline.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")   # where the PDF is written

WINE = "#8C1515"                                       # Stanford-cardinal line/band color


def healy_style():
    """Match the house figure style used by the other plot scripts."""
    # White background, serif fonts, light grid, thin dark spines.
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
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 15,
        "lines.linewidth": 1.4,
    })


def main():
    os.makedirs(FIG_DIR, exist_ok=True)                # ensure the output figures directory exists
    healy_style()                                      # set the shared plot styling

    df = pd.read_csv(DATA).sort_values("cutoff")       # load the recursive estimates, ordered by vintage
    # Place each vintage on the 16th of its cutoff month (ARBLONN status date).
    dts = [date.fromisoformat(c + "-16") for c in df["cutoff"]]
    ki = df["ki"].to_numpy()                           # point estimate (pp) per vintage
    se = df["se"].to_numpy()                           # bootstrap standard error per vintage
    lo, hi = ki - 1.96 * se, ki + 1.96 * se            # 95% band endpoints

    fig, ax = plt.subplots(figsize=(10, 6))            # single-panel figure
    ax.axhline(0, color="#AAAAAA", lw=0.7, ls="--", zorder=1)   # zero reference line
    ax.fill_between(dts, lo, hi, color=WINE, alpha=0.16, zorder=2,
                    label=r"$\pm$1.96 SE (occupation bootstrap)")   # shaded confidence band
    ax.plot(dts, ki, "-o", color=WINE, lw=1.8, ms=5, zorder=3,
            label="KI-indeks (Q5 − Q1 growth)")        # point estimate line with markers
    ax.set_xlabel("Data vintage (register through month)")   # x-axis label
    ax.set_ylabel("KI-indeks (percentage points)")     # y-axis label
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))   # show year-month ticks
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))   # one tick every two months
    fig.autofmt_xdate(rotation=45)                     # angle the date labels to avoid overlap
    ax.legend(loc="upper right", frameon=False)        # legend in the top-right corner

    fig.tight_layout()                                 # tidy spacing
    out = os.path.join(FIG_DIR, "figure_recursive_kiindeks_ci.pdf")   # output PDF path
    fig.savefig(out, dpi=200, bbox_inches="tight")     # write the figure to disk
    plt.close(fig)                                     # free the figure
    print(f"Saved {out}")                              # progress message


if __name__ == "__main__":                             # run main() only when executed as a script
    main()                                             # build and save the figure
