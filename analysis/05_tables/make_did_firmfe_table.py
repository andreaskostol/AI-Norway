"""
make_did_firmfe_table.py

Build the individual-level (firm-FE) difference-in-differences table from the
secure-server output coef_did_byage_fepois.csv (produced by
analysis-indiv/scripts/7b_did_byage_fepois.R and synced into
analysis-indiv/from_secure_server/coefficients/).

Same layout as make_did_cell_table.py so the firm-FE estimates sit beside the
cell-level ones for validation. Writes a caption-less LaTeX fragment (just the
tabular); the float, caption and label live in the paper section file.

  -> analysis/output/tables/table4_did_firmfe.tex

Usage:
    python analysis/05_tables/make_did_firmfe_table.py
"""

import os
import sys
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF_FILE = os.path.join(BASE_DIR, "analysis-indiv", "from_secure_server",
                         "coefficients", "coef_did_byage_fepois.csv")
OUT = os.path.join(BASE_DIR, "analysis", "output", "tables", "table4_did_firmfe.tex")

AGE_ORDER = [1, 2, 3, 4]
AGE_HEADERS = {
    1: ("Early career", "(21--30)"),
    2: ("31--40", ""),
    3: ("41--50", ""),
    4: ("Senior", "(51--60)"),
}
PANELS = [
    ("employment", "Panel A. Employment (Poisson)"),
    ("new_hires", "Panel B. New hires (Poisson)"),
    ("log_wage", "Panel C. Log monthly earnings (OLS)"),
]
QUINTILES = [2, 3, 4, 5]


def stars(p):
    if p < 0.01:
        return "$^{***}$"
    if p < 0.05:
        return "$^{**}$"
    if p < 0.1:
        return "$^{*}$"
    return ""


def build_tabular(df):
    ncol = len(AGE_ORDER)
    lines = [r"\begin{tabular}{l" + "c" * ncol + "}", r"\toprule"]
    lines.append(" & ".join([""] + [AGE_HEADERS[a][0] for a in AGE_ORDER]) + r" \\")
    lines.append(" & ".join([""] + [AGE_HEADERS[a][1] for a in AGE_ORDER]) + r" \\")
    lines.append(" & ".join([""] + [f"({i + 1})" for i in range(ncol)]) + r" \\")
    lines.append(r"\midrule")

    for pi, (outcome, label) in enumerate(PANELS):
        lines.append(r"\multicolumn{%d}{l}{\textit{%s}} \\" % (ncol + 1, label))
        sub = df[df["outcome"] == outcome]
        for q in QUINTILES:
            coef_cells, se_cells = [f"Q{q} $\\times$ Post"], [""]
            for a in AGE_ORDER:
                r = sub[(sub["age_bin"] == a) & (sub["ai_q"] == q)]
                if len(r) == 1:
                    coef_cells.append(f"{r['coef'].iloc[0]:.4f}{stars(r['p_value'].iloc[0])}")
                    se_cells.append(f"({r['se'].iloc[0]:.4f})")
                else:
                    coef_cells.append("")
                    se_cells.append("")
            lines.append(" & ".join(coef_cells) + r" \\")
            lines.append(" & ".join(se_cells) + r" \\")
        if pi < len(PANELS) - 1:
            lines.append(r"\addlinespace")

    lines.append(r"\midrule")
    emp = df[df["outcome"] == "employment"]

    def footrow(label, col):
        cells = [label]
        for a in AGE_ORDER:
            r = emp[emp["age_bin"] == a]
            cells.append(f"{int(r[col].iloc[0]):,}" if len(r) else "")
        return " & ".join(cells) + r" \\"

    lines.append(footrow("Firms", "n_frtk"))
    lines.append(footrow("Observations", "n_obs"))
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    return "\n".join(lines) + "\n"


def main():
    if not os.path.exists(COEF_FILE):
        sys.exit(f"Coefficient file not found: {COEF_FILE}\n"
                 "Run analysis-indiv/scripts/7b_did_byage_fepois.R on the secure "
                 "server and sync from_secure_server/ back first.")
    df = pd.read_csv(COEF_FILE)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build_tabular(df))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
