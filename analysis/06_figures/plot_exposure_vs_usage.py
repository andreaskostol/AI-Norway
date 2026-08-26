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
there). Dot area is proportional to Norwegian paid employment in the
occupation (A-ordningen kpos, ages 21-60, public + private, April
2026), as in the Microsoft and ATLAS companions; larger dots are drawn
first so small occupations stay visible. Correlations (unweighted) for
both revealed-usage measures (Anthropic 2026 and Handa overall) are
printed to the console; the figure plots the Anthropic 2026 pair and
carries its numbers in the corner annotation.

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
EMPLOYMENT = os.path.join(BASE_DIR, "microdata-output",          # dot-size source
                          "09_occ_agedecade_sektor_kpos_2021m01_2026m04_parsed.csv")
EMP_MONTH = "2026-04-16"                     # employment reference month
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")  # output folder

POINT_COLOR = "#2F6FB0"                      # illBlue from the slide decks (single series)
ACCENT_COLOR = "#1D4E85"                     # darker blue for annotated markers
LABEL_COLOR = "#516274"                      # illGray for the outlier annotations
LEADER_COLOR = "#9AA7B4"                     # thin leader line from label to marker
X_COL = "eloundou_beta"                      # theoretical exposure (x-axis)
Y_COL = "anthropic2026_job_exposure"         # observed usage (y-axis)

# Hand-picked occupations to annotate: styrk08 -> label position in data
# coordinates. The label text is the official STYRK-08 name from the
# register (styrk08_name); a thin leader line connects label and marker,
# and annotated markers are drawn in a darker blue on top.
ANNOTATE = {
    "2514": (0.78, 0.780),
    "4132": (0.76, 0.640),
    "4222": (0.42, 0.620),
    "4110": (0.72, 0.420),
    "2330": (0.22, 0.350),
    "2643": (0.82, 0.260),
    "5223": (0.20, 0.220),
    "3342": (0.79, 0.060),
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

    # Employment per occupation for the dot sizes: total paid employment
    # (both sectors), ages 21-60, at the reference month.
    emp = pd.read_csv(EMPLOYMENT, dtype={"yrke4": str, "alder_gr": str,
                                         "sekt": int})
    emp = emp[(emp["variable"] == "count") & (emp["date"] == EMP_MONTH)
              & (emp["alder_gr"].isin(["1", "2", "3", "4"]))]
    emp = emp.groupby("yrke4", as_index=False)["value"].sum() \
             .rename(columns={"yrke4": "styrk08", "value": "employment"})
    sub = sub.merge(emp, on="styrk08", how="left")
    # Suppressed/absent cells get the minimum dot size.
    sub["employment"] = sub["employment"].fillna(0)

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
    # "surface ring" so overlapping points stay distinguishable. Dot area
    # is proportional to employment; largest dots are drawn first so the
    # small occupations stay visible on top.
    sub = sub.sort_values("employment", ascending=False)
    sizes = 8 + 192 * sub["employment"] / sub["employment"].max()
    ax.scatter(sub[X_COL], sub[Y_COL],
               s=sizes, color=POINT_COLOR, alpha=0.75,
               edgecolors="white", linewidths=0.6, zorder=2)

    # Redraw the annotated markers in the darker accent blue on top, then
    # label each with its official register name and a thin leader line.
    ann = sub[sub["styrk08"].isin(ANNOTATE)]
    ann_sizes = 8 + 192 * ann["employment"] / sub["employment"].max()
    ax.scatter(ann[X_COL], ann[Y_COL], s=ann_sizes, color=ACCENT_COLOR,
               edgecolors="white", linewidths=0.6, zorder=3)
    for code, (lx, ly) in ANNOTATE.items():
        # Find the row for this occupation code (skip if unmapped).
        row = sub[sub["styrk08"] == code]
        if row.empty:
            continue
        # Marker coordinates and official name for this occupation.
        x = float(row[X_COL].iloc[0])
        y = float(row[Y_COL].iloc[0])
        name = str(row["styrk08_name"].iloc[0])
        # Label at its manual position, connected by a leader line.
        ax.annotate(name, xy=(x, y), xytext=(lx, ly),
                    fontsize=10.5, color=LABEL_COLOR,
                    ha="center", va="center", zorder=4,
                    arrowprops=dict(arrowstyle="-", color=LEADER_COLOR,
                                    lw=0.7, shrinkA=2, shrinkB=4))

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
