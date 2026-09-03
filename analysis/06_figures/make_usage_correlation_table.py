"""
Rank correlations between the Eloundou et al. (2024) exposure measure and
the revealed-usage measures, collected in one citable table.

The three scatter scripts (plot_exposure_vs_usage.py,
plot_exposure_vs_microsoft.py, plot_exposure_vs_atlas.py) each print their
correlation to the console but write nothing, so the numbers quoted in
posts and plans had no source in the repo. This script replicates each
figure's own computation exactly and writes:

  analysis/output/coefficients/coef_exposure_vs_usage_correlations.csv

Note the unit of analysis differs by source and is recorded per row.
Anthropic 2026, Handa and Microsoft are matched at the STYRK-08 (4-digit)
occupation level. Google ATLAS publishes only 22 SOC major groups, so its
correlation is across those 22 groups against the unweighted mean Eloundou
beta per group, and is NOT comparable to the occupation-level numbers.

Usage:
    python analysis/06_figures/make_usage_correlation_table.py
"""

import os

import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "data", "ai_exposure")
ALL_MEASURES = os.path.join(DATA_DIR, "styrk08_all_exposure_measures.csv")
MICROSOFT = os.path.join(DATA_DIR, "styrk08_microsoft_mapping.csv")
ELOUNDOU = os.path.join(DATA_DIR, "styrk08_eloundou_beta_mapping.csv")
ATLAS = os.path.join(DATA_DIR, "atlas",
                     "atlas_v1_soc_major_gemini_shares_digitized_2026-07.csv")
ELOUNDOU_OCC = os.path.join(DATA_DIR, "eloundou_occ_level.csv")
OUT = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                   "coef_exposure_vs_usage_correlations.csv")

# Occupation-level measures carried by the combined crosswalk.
OCC_MEASURES = [
    ("Anthropic 2026 job exposure", "anthropic2026_job_exposure",
     "Anthropic (2026)"),
    ("Handa overall usage", "handa_overall", "Handa et al. (2025)"),
]


def main():
    rows = []
    a = pd.read_csv(ALL_MEASURES, dtype={"styrk08": str})

    for label, col, source in OCC_MEASURES:
        s = a[["eloundou_beta", col]].dropna()
        rows.append({
            "measure": label, "source": source,
            "unit": "STYRK-08 occupation", "n": len(s),
            "pearson_r": round(s["eloundou_beta"].corr(s[col]), 3),
            "spearman_rho": round(
                s["eloundou_beta"].corr(s[col], method="spearman"), 3)})

    # Microsoft: read from its own mapping, as the figure does.
    el = pd.read_csv(ELOUNDOU, dtype={"styrk08": str})
    ms = pd.read_csv(MICROSOFT, dtype={"styrk08": str})
    s = el.merge(ms, on="styrk08")[["eloundou_beta",
                                    "microsoft_applicability"]].dropna()
    rows.append({
        "measure": "Microsoft Copilot applicability",
        "source": "Tomlinson et al. (2025)",
        "unit": "STYRK-08 occupation", "n": len(s),
        "pearson_r": round(s["eloundou_beta"].corr(
            s["microsoft_applicability"]), 3),
        "spearman_rho": round(s["eloundou_beta"].corr(
            s["microsoft_applicability"], method="spearman"), 3)})

    # ATLAS: 22 SOC major groups, against the unweighted mean beta per group.
    at = pd.read_csv(ATLAS)
    at["grp"] = at["soc2018_major_group"].str[:2]
    occ = pd.read_csv(ELOUNDOU_OCC)
    occ["grp"] = occ["O*NET-SOC Code"].str[:2]
    gb = occ.groupby("grp")["dv_rating_beta"].mean().rename("beta")
    sub = at.merge(gb, left_on="grp", right_index=True, how="inner")
    rows.append({
        "measure": "Google ATLAS representation ratio",
        "source": "Google (2026)",
        "unit": "SOC major group (22)", "n": len(sub),
        "pearson_r": "",
        "spearman_rho": round(sub["beta"].corr(sub["representation_ratio"],
                                               method="spearman"), 3)})

    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT, index=False)
    print(out.to_string(index=False))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
