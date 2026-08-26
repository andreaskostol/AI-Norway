"""
plot_exposure_vs_microsoft.py

Scatter of theoretical AI exposure (Eloundou et al. 2024 GPT-4 beta)
against Microsoft's AI applicability score (Tomlinson et al. 2025: 200k
Bing Copilot conversations scored against O*NET work activities), one
point per 4-digit STYRK-08 code. Third panel in the exposure-vs-usage
family (plot_exposure_vs_usage.py covers Anthropic 2026): a usage-based
measure from a different provider with a much broader consumer user base
than Claude, so agreement here is evidence the exposure-usage relation
is not Claude-specific.

Reads the Eloundou and Microsoft STYRK-08 mappings directly and takes
occupation names from the combined crosswalk. Dot area is proportional
to Norwegian paid employment in the occupation (A-ordningen kpos, ages
21-60, public + private, April 2026), mirroring the employment-share
sizing in plot_exposure_vs_atlas.py; larger dots are drawn first so
small occupations stay visible. Correlations (unweighted, as in the
companion figures) are printed to the console; the figure carries the
same numbers in its corner annotation.

Labels are in Norwegian because the figure is built for the dashboard's
"Eksponering vs faktisk bruk" section and the Norwegian slide decks.
No title/notes are baked into the PDF.

Outputs:
  analysis/output/figures/figure_exposure_vs_microsoft.pdf
  analysis/output/figures/figure_exposure_vs_microsoft.png  (for quick checks)

Usage:
    python analysis/06_figures/plot_exposure_vs_microsoft.py
"""

import os                                    # path handling

import matplotlib                            # plotting backend selection
matplotlib.use("Agg")                        # headless rendering (no display)
import matplotlib.pyplot as plt              # the plotting API
import pandas as pd                          # CSV reading + correlations

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")   # repo root
DATA_DIR = os.path.join(BASE_DIR, "data", "ai_exposure")         # exposure data
ELOUNDOU = os.path.join(DATA_DIR, "styrk08_eloundou_beta_mapping.csv")
MICROSOFT = os.path.join(DATA_DIR, "styrk08_microsoft_mapping.csv")
NAMES = os.path.join(DATA_DIR, "styrk08_all_exposure_measures.csv")
EMPLOYMENT = os.path.join(BASE_DIR, "microdata-output",          # dot-size source
                          "09_occ_agedecade_sektor_kpos_2021m01_2026m04_parsed.csv")
EMP_MONTH = "2026-04-16"                     # employment reference month
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")  # output folder

POINT_COLOR = "#2F6FB0"                      # illBlue from the slide decks (single series)
LABEL_COLOR = "#516274"                      # illGray for the outlier annotations

# Hand-picked points to annotate: styrk08 -> (short label, x-offset, y-offset).
# Offsets are in data units and placed manually so no label collides.
ANNOTATE = {
    "2643": ("Oversettere og tolker",     -0.14,  0.030),
    "2514": ("Applikasjonsprogrammerere", -0.10,  0.030),
    "4222": ("Kundesentermedarbeidere",   -0.06,  0.028),
    "2652": ("Musikere mv.",               0.07,  -0.022),
    "3256": ("Helsesekretærer",       0.00,  -0.025),
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

    # Merge the two mappings and attach occupation names.
    el = pd.read_csv(ELOUNDOU, dtype={"styrk08": str})[["styrk08", "eloundou_beta"]]
    ms = pd.read_csv(MICROSOFT, dtype={"styrk08": str})[
        ["styrk08", "microsoft_applicability"]]
    nm = pd.read_csv(NAMES, dtype={"styrk08": str})[["styrk08", "styrk08_name"]]
    sub = el.merge(ms, on="styrk08").merge(nm, on="styrk08", how="left")

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

    # Correlations for the plotted pair (pairwise-complete by construction).
    pearson = sub["eloundou_beta"].corr(sub["microsoft_applicability"])
    spearman = sub["eloundou_beta"].corr(sub["microsoft_applicability"],
                                         method="spearman")
    n = len(sub)
    print(f"N = {n}, Pearson r = {pearson:.3f}, Spearman rho = {spearman:.3f}")

    # One panel; single scatter needs no legend (one series only). The two
    # measures live on different scales (the applicability score tops out
    # near 0.42), so there is no identity line here.
    fig, ax = plt.subplots(figsize=(7.0, 6.0))

    # The scatter itself: one point per occupation, white edge as the
    # "surface ring" so overlapping points stay distinguishable. Dot area
    # is proportional to employment; largest dots are drawn first so the
    # small occupations stay visible on top.
    sub = sub.sort_values("employment", ascending=False)
    sizes = 8 + 192 * sub["employment"] / sub["employment"].max()
    ax.scatter(sub["eloundou_beta"], sub["microsoft_applicability"],
               s=sizes, color=POINT_COLOR, alpha=0.75,
               edgecolors="white", linewidths=0.6, zorder=2)

    # Annotate the hand-picked points with small gray labels.
    for code, (label, dx, dy) in ANNOTATE.items():
        # Find the row for this occupation code (skip if unmapped).
        row = sub[sub["styrk08"] == code]
        if row.empty:
            continue
        # Point coordinates for this occupation.
        x = float(row["eloundou_beta"].iloc[0])
        y = float(row["microsoft_applicability"].iloc[0])
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

    # Axis labels: theoretical exposure on x, Copilot-based usage on y.
    ax.set_xlabel("Eloundou mfl. (2024): GPT-4-$\\beta$")
    ax.set_ylabel("Microsoft (2025): Copilot-basert anvendbarhet")
    # Full 0-1 exposure range on x; the score tops out at 0.42.
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 0.5)
    xticks = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
    yticks = [0, 0.1, 0.2, 0.3, 0.4, 0.5]
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    # Norwegian comma-decimal tick labels on both axes.
    ax.set_xticklabels([f"{t:.1f}".replace(".", ",") for t in xticks])
    ax.set_yticklabels([f"{t:.1f}".replace(".", ",") for t in yticks])

    # Tight layout, then save both the PDF (deck/site) and a PNG (quick checks).
    fig.tight_layout()
    for ext in ("pdf", "png"):
        out = os.path.join(FIG_DIR, f"figure_exposure_vs_microsoft.{ext}")
        fig.savefig(out, dpi=200, bbox_inches="tight")
        print(f"Wrote {out}")
    # Free the figure object.
    plt.close(fig)


if __name__ == "__main__":
    # Run the plot build when executed as a script.
    main()
