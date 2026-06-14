"""Build the 7b / 7d / published-cell specification-comparison deliverable.

Implements the §22 decomposition chain (DESIGN_CHOICES.md): on the per-age,
per-quintile DiD-Poisson coefficients (Q1 reference), line up four estimates
per (age_bin, outcome, ai_q) so that each adjacent pair isolates one factor:

    7b firm-FE            --[specification]--   7d cell-spec restricted
    7d restricted         --[>=20 restriction + balancing]--  7d unrestricted_priv
    7d unrestricted_priv  --[data source: register vs microdata.no]--  published cell

Inputs (all already on disk after a full secure-server run + the local cell run):
    analysis-indiv/from_secure_server/coefficients/coef_did_byage_fepois.csv     (7b)
    analysis-indiv/from_secure_server/coefficients/coef_did_byage_cellspec.csv   (7d)
    analysis/output/coefficients/coef_microdata_did_cell.csv                     (published)

Outputs (analysis-indiv/output/):
    comparison_7b_7d_cell.csv         tidy long: one row per (age_bin, outcome, ai_q, spec)
    comparison_7b_7d_cell_wide.csv    wide: coef/se/p side by side per spec
    comparison_employment.md          readable employment table (headline)
    fig_comparison_employment.png     coefficient plot, employment, by age x quintile

Run locally (no secure data needed): python analysis-indiv/code/build_comparison_7b_7d_cell.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAVE_MPL = True
except Exception:  # pragma: no cover - figure is optional
    HAVE_MPL = False

ROOT = Path(__file__).resolve().parents[2]
FSS = ROOT / "analysis-indiv" / "from_secure_server" / "coefficients"
PUBLISHED = ROOT / "analysis" / "output" / "coefficients" / "coef_microdata_did_cell.csv"
OUTDIR = ROOT / "analysis-indiv" / "output"

# Display order and labels for the four specifications.
SPEC_ORDER = ["7b_firm", "7d_cell_restricted", "7d_cell_unrestr", "cell_microdata"]
SPEC_LABEL = {
    "7b_firm": "7b firm-FE (firm x q + firm x t)",
    "7d_cell_restricted": "7d cell-spec, restricted",
    "7d_cell_unrestr": "7d cell-spec, unrestricted_priv",
    "cell_microdata": "published microdata.no cell",
}
AGE_LABEL = {1: "21-30", 2: "31-40", 3: "41-50", 4: "51-60"}
QUINT_ORDER = [2, 3, 4, 5]  # Q1 (lowest exposure) is the omitted reference (BCC)


def _need(path: Path) -> Path:
    if not path.exists():
        sys.exit(f"Missing required input: {path}")
    return path


def load_long() -> pd.DataFrame:
    """Return tidy long frame: age_bin, outcome, ai_q, spec, coef, se, p_value, n_obs, n_units."""
    frames = []

    # 7b firm-FE -------------------------------------------------------------
    b = pd.read_csv(_need(FSS / "coef_did_byage_fepois.csv"))
    b = b[b["sample"] == "headline_priv"].copy()
    b["spec"] = "7b_firm"
    b = b.rename(columns={"n_frtk": "n_units"})
    frames.append(b[["age_bin", "outcome", "ai_q", "spec", "coef", "se", "p_value", "n_obs", "n_units"]])

    # 7d cell-spec (two variants) -------------------------------------------
    d = pd.read_csv(_need(FSS / "coef_did_byage_cellspec.csv"))
    d = d.rename(columns={"n_occ": "n_units"})
    for variant, spec in (("restricted", "7d_cell_restricted"),
                          ("unrestricted_priv", "7d_cell_unrestr")):
        dv = d[d["variant"] == variant].copy()
        dv["spec"] = spec
        frames.append(dv[["age_bin", "outcome", "ai_q", "spec", "coef", "se", "p_value", "n_obs", "n_units"]])

    # Published microdata.no cell (private sector only) ---------------------
    # NB: in microdata_did_cell.R, sector 2 = private, sector 1 = public.
    # 7b/7d are private (in_headline_priv), so the cell column must be sector 2.
    c = pd.read_csv(_need(PUBLISHED))
    c = c[c["sector"] == 2].copy()
    c = c.rename(columns={"age_group": "age_bin", "n_occ": "n_units"})
    c["spec"] = "cell_microdata"
    frames.append(c[["age_bin", "outcome", "ai_q", "spec", "coef", "se", "p_value", "n_obs", "n_units"]])

    long = pd.concat(frames, ignore_index=True)
    long["age_bin"] = long["age_bin"].astype(int)
    long["ai_q"] = long["ai_q"].astype(int)
    long["spec"] = pd.Categorical(long["spec"], categories=SPEC_ORDER, ordered=True)
    long = long.sort_values(["outcome", "age_bin", "ai_q", "spec"]).reset_index(drop=True)
    return long


def stars(p: float) -> str:
    if pd.isna(p):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def make_wide(long: pd.DataFrame) -> pd.DataFrame:
    wide = long.pivot_table(
        index=["outcome", "age_bin", "ai_q"],
        columns="spec",
        values=["coef", "se", "p_value"],
        observed=True,
    )
    wide.columns = [f"{spec}_{stat}" for stat, spec in wide.columns]
    return wide.reset_index()


def write_employment_md(long: pd.DataFrame) -> str:
    emp = long[long["outcome"] == "employment"]
    lines = [
        "# Specification comparison: per-age DiD-Poisson, employment (Q1 reference)",
        "",
        "Coefficient (std. error) on `post x quintile`, employment count, private sector.",
        "Each column is one specification; reading across a row isolates the factor",
        "named in the chain (see DESIGN_CHOICES.md §22). Stars: * p<.10, ** p<.05, *** p<.01.",
        "",
        "n_units = foretak (7b) / occupations (cell specs). The published-cell occupation",
        "count is lower than the register cell specs because microdata.no suppresses small",
        "cells -- a documented residual gap, not a like-for-like occupation universe.",
        "",
    ]
    for age in sorted(emp["age_bin"].unique()):
        lines.append(f"## Age {AGE_LABEL.get(age, age)} (age_bin {age})")
        lines.append("")
        header = "| Q vs Q1 | " + " | ".join(SPEC_LABEL[s] for s in SPEC_ORDER) + " |"
        sep = "|" + "---|" * (len(SPEC_ORDER) + 1)
        lines.append(header)
        lines.append(sep)
        for q in QUINT_ORDER:
            cells = []
            for spec in SPEC_ORDER:
                r = emp[(emp["age_bin"] == age) & (emp["ai_q"] == q) & (emp["spec"] == spec)]
                if len(r) == 0:
                    cells.append("--")
                    continue
                r = r.iloc[0]
                cells.append(f"{r['coef']:+.4f}{stars(r['p_value'])} ({r['se']:.4f})")
            lines.append(f"| Q{q} | " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def make_figure(long: pd.DataFrame, path: Path) -> None:
    emp = long[long["outcome"] == "employment"]
    ages = sorted(emp["age_bin"].unique())
    fig, axes = plt.subplots(1, len(ages), figsize=(4 * len(ages), 4.2), sharey=True)
    if len(ages) == 1:
        axes = [axes]
    colors = {"7b_firm": "#1b4965", "7d_cell_restricted": "#5fa8d3",
              "7d_cell_unrestr": "#9ad1d4", "cell_microdata": "#bc4749"}
    offs = {s: (i - 1.5) * 0.15 for i, s in enumerate(SPEC_ORDER)}
    for ax, age in zip(axes, ages):
        for spec in SPEC_ORDER:
            sub = emp[(emp["age_bin"] == age) & (emp["spec"] == spec)].sort_values("ai_q")
            if len(sub) == 0:
                continue
            x = [QUINT_ORDER.index(q) + offs[spec] for q in sub["ai_q"]]
            ax.errorbar(x, sub["coef"], yerr=1.96 * sub["se"], fmt="o", ms=4,
                        capsize=2, color=colors[spec], label=SPEC_LABEL[spec])
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xticks(range(len(QUINT_ORDER)))
        ax.set_xticklabels([f"Q{q}" for q in QUINT_ORDER])
        ax.set_title(f"Age {AGE_LABEL.get(age, age)}")
        ax.set_xlabel("AI-exposure quintile (vs Q1)")
    axes[0].set_ylabel("post x quintile (log points)")
    axes[-1].legend(fontsize=7, loc="best")
    fig.suptitle("Employment DiD by AI-exposure quintile: four specifications on (near-)identical data")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    long = load_long()
    long.to_csv(OUTDIR / "comparison_7b_7d_cell.csv", index=False)
    make_wide(long).to_csv(OUTDIR / "comparison_7b_7d_cell_wide.csv", index=False)
    (OUTDIR / "comparison_employment.md").write_text(write_employment_md(long), encoding="utf-8")
    msg = [f"Wrote {OUTDIR / 'comparison_7b_7d_cell.csv'} ({len(long)} rows)",
           f"Wrote {OUTDIR / 'comparison_7b_7d_cell_wide.csv'}",
           f"Wrote {OUTDIR / 'comparison_employment.md'}"]
    if HAVE_MPL:
        make_figure(long, OUTDIR / "fig_comparison_employment.png")
        msg.append(f"Wrote {OUTDIR / 'fig_comparison_employment.png'}")
    else:
        msg.append("matplotlib unavailable -- skipped figure")
    print("\n".join(msg))


if __name__ == "__main__":
    main()
