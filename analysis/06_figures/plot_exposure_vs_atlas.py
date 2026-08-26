"""
plot_exposure_vs_atlas.py

Scatter of theoretical AI exposure (Eloundou et al. 2024 GPT-4 beta,
averaged within SOC 2018 major group) against Google ATLAS's Gemini
usage representation ratio (share of US work-related Gemini interactions
in the group divided by the group's US employment share), one point per
SOC major group. Google has not published occupation-level ATLAS data,
so this comparison is honest to the source's resolution: 22 groups, no
detailed-occupation variation (see data/ai_exposure/atlas/README.md and
build_atlas_mapping.py).

The y-axis is logarithmic: the ratio spans 0.03 (food preparation) to
8.8 (computer and mathematical). The dashed line at 1 marks usage
proportional to employment. Dot size is proportional to the group's US
employment share.

Labels are in Norwegian because the figure is built for the dashboard's
"Eksponering vs faktisk bruk" section and the Norwegian slide decks.
No title/notes are baked into the PDF.

Outputs:
  analysis/output/figures/figure_exposure_vs_atlas.pdf
  analysis/output/figures/figure_exposure_vs_atlas.png  (for quick checks)

Usage:
    python analysis/06_figures/plot_exposure_vs_atlas.py
"""

import os                                    # path handling

import matplotlib                            # plotting backend selection
matplotlib.use("Agg")                        # headless rendering (no display)
import matplotlib.pyplot as plt              # the plotting API
import pandas as pd                          # CSV reading + correlations

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")   # repo root
ATLAS = os.path.join(BASE_DIR, "data", "ai_exposure", "atlas",
                     "atlas_v1_soc_major_gemini_shares_digitized_2026-07.csv")
ELOUNDOU_OCC = os.path.join(BASE_DIR, "data", "ai_exposure",
                            "eloundou_occ_level.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")  # output folder

POINT_COLOR = "#2F6FB0"                      # illBlue from the slide decks (single series)
LABEL_COLOR = "#516274"                      # illGray for the group labels
LEADER_COLOR = "#9AA7B4"                     # thin leader line from label to marker
IDENT_COLOR = "#999999"                      # recessive gray for the ratio=1 line

# Norwegian labels per SOC major-group prefix (translations of the
# official BLS major-group titles; SOC groups have no official Norwegian
# names). 21 of 22 groups are labeled -- Production is skipped in the
# crowded bottom-left corner. Offsets are (dx in data units, dy as a
# multiplicative factor on the log axis); a thin leader line connects
# each label to its marker.
LABELS = {
    "15": ("Data og matematikk",             -0.115, 1.00),
    "27": ("Kunst, media og sport",          -0.045, 1.30),
    "13": ("Økonomi og forretningsdrift", 0.000, 1.35),
    "19": ("Naturvitenskap og samfunnsfag",  -0.140, 1.00),
    "17": ("Arkitektur og ingeniørfag",  -0.130, 1.05),
    "23": ("Juridisk arbeid",                 0.020, 0.82),
    "43": ("Kontorstøtte",                0.075, 1.00),
    "21": ("Sosialt arbeid",                  0.000, 0.80),
    "11": ("Ledelse",                         0.075, 1.00),
    "49": ("Installasjon og reparasjon",      0.090, 1.15),
    "25": ("Undervisning og bibliotek",       0.100, 1.00),
    "45": ("Jordbruk, fiske og skogbruk",     0.000, 0.72),
    "29": ("Helsepersonell",                 -0.095, 1.05),
    "33": ("Vakthold og beredskap",          -0.020, 0.78),
    "41": ("Salg",                            0.045, 1.00),
    "47": ("Bygg og anlegg",                  0.035, 1.35),
    "39": ("Personlig tjenesteyting",         0.115, 1.00),
    "53": ("Transport og lager",              0.105, 1.00),
    "31": ("Helsestøtteyrker",            0.100, 0.90),
    "37": ("Renhold og vedlikehold",         -0.010, 1.45),
    "35": ("Servering og matlaging",          0.045, 0.75),
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

    # ATLAS group table: representation ratio + employment share per group.
    at = pd.read_csv(ATLAS)
    at["grp"] = at["soc2018_major_group"].str[:2]

    # Mean Eloundou beta per SOC major group from the O*NET-level file
    # (unweighted mean across the group's O*NET occupations).
    occ = pd.read_csv(ELOUNDOU_OCC)
    occ["grp"] = occ["O*NET-SOC Code"].str[:2]
    gb = occ.groupby("grp")["dv_rating_beta"].mean().rename("eloundou_group_beta")
    sub = at.merge(gb, left_on="grp", right_index=True, how="inner")

    # Rank correlation across the 22 groups.
    spearman = sub["eloundou_group_beta"].corr(sub["representation_ratio"],
                                               method="spearman")
    n = len(sub)
    print(f"N = {n} groups, Spearman rho = {spearman:.3f}")

    # One panel; log y-axis for the ratio (spans 0.03 to 8.8).
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    ax.set_yscale("log")

    # Reference line: usage proportional to employment (ratio = 1).
    ax.axhline(1.0, linestyle="--", linewidth=1.0, color=IDENT_COLOR, zorder=1)
    ax.annotate("bruk = sysselsettingsandel", xy=(0.015, 1.07),
                fontsize=10.5, color=IDENT_COLOR, ha="left", va="bottom")

    # Dot area proportional to the group's US employment share.
    sizes = 30 + 28 * sub["oews_us_employment_share_pct"]
    ax.scatter(sub["eloundou_group_beta"], sub["representation_ratio"],
               s=sizes, color=POINT_COLOR, alpha=0.75,
               edgecolors="white", linewidths=0.6, zorder=2)

    # Label the groups with small gray labels and thin leader lines.
    for _, row in sub.iterrows():
        if row["grp"] not in LABELS:
            continue
        label, dx, fy = LABELS[row["grp"]]
        x = float(row["eloundou_group_beta"])
        y = float(row["representation_ratio"])
        # dy is multiplicative because the axis is logarithmic.
        ax.annotate(label, xy=(x, y), xytext=(x + dx, y * fy),
                    fontsize=10.5, color=LABEL_COLOR,
                    ha="center", va="center", zorder=3,
                    arrowprops=dict(arrowstyle="-", color=LEADER_COLOR,
                                    lw=0.7, shrinkA=2, shrinkB=4))

    # Corner annotation with the correlation (Norwegian comma decimals).
    stats = (f"Spearman $\\rho$ = {spearman:.2f}\n"
             f"$N$ = {n} yrkeshovedgrupper").replace(".", ",")
    ax.text(0.03, 0.97, stats, transform=ax.transAxes,
            fontsize=13, va="top", ha="left", color="#333333")

    # Axis labels: group-mean exposure on x, relative Gemini usage on y.
    ax.set_xlabel("Eloundou mfl. (2024): GPT-4-$\\beta$, snitt i gruppen")
    ax.set_ylabel("Google ATLAS (2026): relativ Gemini-bruk (log)")
    ax.set_xlim(0, 0.85)
    ax.set_ylim(0.02, 15)
    xticks = [0, 0.2, 0.4, 0.6, 0.8]
    ax.set_xticks(xticks)
    ax.set_xticklabels([f"{t:.1f}".replace(".", ",") for t in xticks])
    # Explicit log ticks with comma-decimal labels.
    yticks = [0.03, 0.1, 0.3, 1, 3, 10]
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{t:g}".replace(".", ",") for t in yticks])
    ax.minorticks_off()

    # Tight layout, then save both the PDF (deck/site) and a PNG (quick checks).
    fig.tight_layout()
    for ext in ("pdf", "png"):
        out = os.path.join(FIG_DIR, f"figure_exposure_vs_atlas.{ext}")
        fig.savefig(out, dpi=200, bbox_inches="tight")
        print(f"Wrote {out}")
    # Free the figure object.
    plt.close(fig)


if __name__ == "__main__":
    # Run the plot build when executed as a script.
    main()
