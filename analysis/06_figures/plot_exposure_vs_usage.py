"""
plot_exposure_vs_usage.py

Scatter of theoretical AI exposure (Eloundou et al. 2024 GPT-4 beta)
against observed Claude usage (Anthropic 2026 job_exposure: time-weighted
observed usage with an automation penalty), one point per 4-digit
STYRK-08 code. Companion to plot_mouchel_vs_eloundou.py: that figure
compares two capability-side measures (Eloundou's prior-based beta and
Mouchel's evidence-grounded beta -- "evidensbasert" refers to the
documentary evidence behind the capability judgments; neither is built
from usage logs; Spearman 0.94). This one crosses the family divide to
revealed usage from actual Claude logs (Spearman 0.78) and
shows the capability-use gap -- median observed usage is near zero while
theoretical exposure is spread across the full 0-1 range, and several
highly exposed occupations have no recorded usage at all.

Reads the combined exposure crosswalk directly (both measures live
there). Correlations for both revealed-usage measures (Anthropic 2026
and Handa overall) are printed to the console; the figure plots the
Anthropic 2026 pair and carries its numbers in the corner annotation.

Labels are in Norwegian because the figure is built for the dashboard's
"Eksponering vs faktisk bruk" section and the Norwegian slide decks.
No title/notes are baked into the PDF.

Outputs:
  analysis/output/figures/figure_exposure_vs_usage.pdf
  analysis/output/figures/figure_exposure_vs_usage.png  (for quick checks)

Usage:
    python analysis/06_figures/plot_exposure_vs_usage.py
"""

import os                                    # path handling

import matplotlib                            # plotting backend selection
matplotlib.use("Agg")                        # headless rendering (no display)
import matplotlib.pyplot as plt              # the plotting API
import pandas as pd                          # CSV reading + correlations

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")   # repo root
DATA = os.path.join(BASE_DIR, "data", "ai_exposure",             # combined crosswalk
                    "styrk08_all_exposure_measures.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")  # output folder

POINT_COLOR = "#2F6FB0"                      # illBlue from the slide decks (single series)
LABEL_COLOR = "#516274"                      # illGray for the outlier annotations
X_COL = "eloundou_beta"                      # theoretical exposure (x-axis)
Y_COL = "anthropic2026_job_exposure"         # observed usage (y-axis)

# Hand-picked points to annotate: styrk08 -> (short label, x-offset, y-offset).
# Offsets are in data units and placed manually so no label collides.
ANNOTATE = {
    "2514": ("Applikasjonsprogrammerere", -0.175, 0.030),
    "4132": ("Dataregistrere",            -0.030, 0.035),
    "4222": ("Kundesentermedarbeidere",   -0.055, 0.035),
    "2330": ("Lektorer",                   0.000, 0.035),
    "3342": ("Advokatsekretærer",     0.055, 0.030),
}


def healy_style():
    # Same rcParams as the other house figures (plot_employment_decade.py).
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
        "font.size": 15, "axes.labelsize": 15,
        "xtick.labelsize": 13, "ytick.labelsize": 13,
    })


def main():
    # Apply the shared figure style before any axes are created.
    healy_style()
    # Make sure the output folder exists.
    os.makedirs(FIG_DIR, exist_ok=True)

    # Read the combined crosswalk with the code as a string (leading zeros).
    df = pd.read_csv(DATA, dtype={"styrk08": str})
    # Keep the pairwise-complete sample for the two plotted measures.
    sub = df[["styrk08", "styrk08_name", X_COL, Y_COL]].dropna(
        subset=[X_COL, Y_COL]).copy()

    # Correlations for the plotted pair.
    pearson = sub[X_COL].corr(sub[Y_COL])
    spearman = sub[X_COL].corr(sub[Y_COL], method="spearman")
    n = len(sub)
    print(f"Anthropic 2026: N = {n}, Pearson r = {pearson:.3f}, "
          f"Spearman rho = {spearman:.3f}")
    # Console reference: the same correlations against Handa overall.
    hs = df[[X_COL, "handa_overall"]].dropna()
    print(f"Handa overall:  N = {len(hs)}, "
          f"Pearson r = {hs[X_COL].corr(hs['handa_overall']):.3f}, "
          f"Spearman rho = "
          f"{hs[X_COL].corr(hs['handa_overall'], method='spearman'):.3f}")

    # One panel; single scatter needs no legend (one series only). The two
    # measures live on different scales (usage is heavily right-skewed with
    # median 0.03), so there is no identity line here.
    fig, ax = plt.subplots(figsize=(7.0, 6.0))

    # The scatter itself: one point per occupation, white edge as the
    # "surface ring" so overlapping points stay distinguishable.
    ax.scatter(sub[X_COL], sub[Y_COL],
               s=34, color=POINT_COLOR, alpha=0.75,
               edgecolors="white", linewidths=0.6, zorder=2)

    # Annotate the hand-picked points with small gray labels.
    for code, (label, dx, dy) in ANNOTATE.items():
        # Find the row for this occupation code (skip if unmapped).
        row = sub[sub["styrk08"] == code]
        if row.empty:
            continue
        # Point coordinates for this occupation.
        x = float(row[X_COL].iloc[0])
        y = float(row[Y_COL].iloc[0])
        # Place the label at the manual offset from the point.
        ax.annotate(label, xy=(x, y), xytext=(x + dx, y + dy),
                    fontsize=10.5, color=LABEL_COLOR,
                    ha="center", va="center", zorder=3)

    # Corner annotation with the correlation numbers (Norwegian comma decimals).
    stats = (f"Pearson $r$ = {pearson:.2f}\n"
             f"Spearman $\\rho$ = {spearman:.2f}\n"
             f"$N$ = {n} yrker").replace(".", ",")
    ax.text(0.03, 0.97, stats, transform=ax.transAxes,
            fontsize=13, va="top", ha="left", color="#333333")

    # Axis labels: theoretical exposure on x, observed usage on y.
    ax.set_xlabel("Eloundou mfl. (2024): GPT-4-$\\beta$")
    ax.set_ylabel("Anthropic (2026): observert Claude-bruk")
    # Full 0-1 exposure range on x; usage tops out at 0.75 (2514).
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 0.8)
    xticks = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
    yticks = [0, 0.2, 0.4, 0.6, 0.8]
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    # Norwegian comma-decimal tick labels on both axes.
    ax.set_xticklabels([f"{t:.1f}".replace(".", ",") for t in xticks])
    ax.set_yticklabels([f"{t:.1f}".replace(".", ",") for t in yticks])

    # Tight layout, then save both the PDF (deck/site) and a PNG (quick checks).
    fig.tight_layout()
    for ext in ("pdf", "png"):
        out = os.path.join(FIG_DIR, f"figure_exposure_vs_usage.{ext}")
        fig.savefig(out, dpi=200, bbox_inches="tight")
        print(f"Wrote {out}")
    # Free the figure object.
    plt.close(fig)


if __name__ == "__main__":
    # Run the plot build when executed as a script.
    main()
