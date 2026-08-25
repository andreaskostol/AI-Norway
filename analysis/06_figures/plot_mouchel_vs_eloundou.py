"""
plot_mouchel_vs_eloundou.py

Scatter of the Mouchel et al. (2026) evidence-grounded AI exposure (arm A1,
the grounded ensemble mean that never touches Anthropic usage data) against
the Eloundou et al. (2024) GPT-4 beta, one point per 4-digit STYRK-08 code.

Reads the combined exposure crosswalk directly (both measures live there);
no separate stage-1 artifact is needed. Correlations are computed on the
pairwise-complete sample and printed to the console; the figure carries the
same numbers in its corner annotation.

Labels are in Norwegian because the figure is built for the Norwegian slide
decks (slides/mouchel). No title/notes are baked into the PDF.

Outputs:
  analysis/output/figures/figure_mouchel_vs_eloundou.pdf
  analysis/output/figures/figure_mouchel_vs_eloundou.png  (for quick checks)

Usage:
    python analysis/06_figures/plot_mouchel_vs_eloundou.py
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
IDENT_COLOR = "#999999"                      # recessive gray for the 45-degree line

# Hand-picked outliers to annotate: styrk08 -> (short label, x-offset, y-offset).
# Offsets are in data units and placed manually so no label collides.
ANNOTATE = {
    "2631": ("Samfunnsøkonomer",        -0.02,  0.055),
    "2611": ("Jurister og advokater",   -0.02,  0.050),
    "2411": ("Revisorer",                0.025, 0.030),
    "4223": ("Sentralbordoperatører",    0.015, -0.055),
    "3343": ("Sjefssekretærer",          0.025, -0.020),
    "5249": ("Andre salgsmedarbeidere",  0.02,  -0.055),
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
    # Keep the pairwise-complete sample for the two measures being compared.
    sub = df[["styrk08", "styrk08_name",
              "eloundou_beta", "mouchel_grounded"]].dropna(
        subset=["eloundou_beta", "mouchel_grounded"]).copy()

    # Pearson correlation between the two measures.
    pearson = sub["eloundou_beta"].corr(sub["mouchel_grounded"])
    # Spearman rank correlation (robust to the level shift between rubrics).
    spearman = sub["eloundou_beta"].corr(sub["mouchel_grounded"], method="spearman")
    # Number of occupations in the plotted sample.
    n = len(sub)
    # Print the headline numbers for the console log / slide text.
    print(f"N = {n}, Pearson r = {pearson:.3f}, Spearman rho = {spearman:.3f}")

    # One square-ish panel; single scatter needs no legend (one series only).
    fig, ax = plt.subplots(figsize=(7.0, 6.4))

    # 45-degree identity line: both measures live on the same 0-1 beta scale.
    ax.plot([0, 1.0], [0, 1.0], linestyle="--", linewidth=1.0,
            color=IDENT_COLOR, zorder=1)
    # Label the identity line directly at its upper end (no legend box).
    ax.annotate("45°-linjen", xy=(0.88, 0.905), fontsize=11,
                color=IDENT_COLOR, rotation=45,
                ha="center", va="bottom", rotation_mode="anchor")

    # The scatter itself: one point per occupation, white edge as the
    # "surface ring" so overlapping points stay distinguishable.
    ax.scatter(sub["eloundou_beta"], sub["mouchel_grounded"],
               s=34, color=POINT_COLOR, alpha=0.75,
               edgecolors="white", linewidths=0.6, zorder=2)

    # Annotate the hand-picked outliers with small gray labels.
    for code, (label, dx, dy) in ANNOTATE.items():
        # Find the row for this occupation code (skip if unmapped).
        row = sub[sub["styrk08"] == code]
        if row.empty:
            continue
        # Point coordinates for this occupation.
        x = float(row["eloundou_beta"].iloc[0])
        y = float(row["mouchel_grounded"].iloc[0])
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

    # Axis labels: source measure on x, new measure on y (Norwegian, for slides).
    ax.set_xlabel("Eloundou mfl. (2024): GPT-4-$\\beta$")
    ax.set_ylabel("Mouchel mfl. (2026): evidensbasert eksponering")
    # Identical limits on both axes so the identity line reads correctly.
    # Full 0-1 range: 4413 (Kodere) sits at (0.975, 0.887) and must not be clipped.
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 1.0)
    # Same tick positions on both axes for the square comparison.
    ticks = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    # Norwegian comma-decimal tick labels on both axes.
    ax.set_xticklabels([f"{t:.1f}".replace(".", ",") for t in ticks])
    ax.set_yticklabels([f"{t:.1f}".replace(".", ",") for t in ticks])
    # Square aspect so equal distances mean equal score differences.
    ax.set_aspect("equal")

    # Tight layout, then save both the PDF (deck) and a PNG (quick checks).
    fig.tight_layout()
    for ext in ("pdf", "png"):
        out = os.path.join(FIG_DIR, f"figure_mouchel_vs_eloundou.{ext}")
        fig.savefig(out, dpi=200, bbox_inches="tight")
        print(f"Wrote {out}")
    # Free the figure object.
    plt.close(fig)


if __name__ == "__main__":
    # Run the plot build when executed as a script.
    main()
