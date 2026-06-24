"""
make_did_firmfe_table.py

Purpose:
  Build the individual-level (firm-FE) difference-in-differences table feeding
  the paper's Table referenced as \\label{tab:did_firmfe}, from the
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

# os: build file paths, check existence, create the output directory
import os
# sys: exit with a helpful message if the coefficient file is missing
import sys
# pandas: read the coefficient CSV and filter by outcome/quintile/age
import pandas as pd

# Repo root, relative to this script (analysis/05_tables/ -> ../../)
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
# Firm-FE DiD coefficient estimates synced from the secure server
COEF_FILE = os.path.join(BASE_DIR, "analysis-indiv", "from_secure_server",
                         "coefficients", "coef_did_byage_fepois.csv")
# Output LaTeX tabular fragment (caption-less; the float lives in the paper)
OUT = os.path.join(BASE_DIR, "analysis", "output", "tables", "table4_did_firmfe.tex")

# Decade age groups, in column order (1=21-30 ... 4=51-60)
AGE_ORDER = [1, 2, 3, 4]
# Two-line column headers for each age group
AGE_HEADERS = {
    1: ("Early career", "(21--30)"),
    2: ("31--40", ""),
    3: ("41--50", ""),
    4: ("Senior", "(51--60)"),
}
# Panels stacked in the table: (outcome key in CSV, printed panel title)
PANELS = [
    ("employment", "Panel A. Employment (Poisson)"),
    ("new_hires", "Panel B. New hires (Poisson)"),
    ("log_wage", "Panel C. Log monthly earnings (OLS)"),
]
# Exposure quintiles shown as rows (Q1 is the omitted base, so 2-5)
QUINTILES = [2, 3, 4, 5]


# Return LaTeX significance stars for a given p-value.
def stars(p):
    # 1% significance
    if p < 0.01:
        return "$^{***}$"
    # 5% significance
    if p < 0.05:
        return "$^{**}$"
    # 10% significance
    if p < 0.1:
        return "$^{*}$"
    # Not significant
    return ""


# Build the full LaTeX tabular string from the coefficient frame.
def build_tabular(df):
    # Number of numeric (age-group) columns
    ncol = len(AGE_ORDER)
    # Open the tabular (label column + one centered column per age group) and top rule
    lines = [r"\begin{tabular}{l" + "c" * ncol + "}", r"\toprule"]
    # First header row: blank label + age-group names
    lines.append(" & ".join([""] + [AGE_HEADERS[a][0] for a in AGE_ORDER]) + r" \\")
    # Second header row: blank label + age ranges
    lines.append(" & ".join([""] + [AGE_HEADERS[a][1] for a in AGE_ORDER]) + r" \\")
    # Third header row: blank label + column numbers (1)..(ncol)
    lines.append(" & ".join([""] + [f"({i + 1})" for i in range(ncol)]) + r" \\")
    # Rule under the header
    lines.append(r"\midrule")

    # One panel per outcome (employment, new hires, log earnings)
    for pi, (outcome, label) in enumerate(PANELS):
        # Italic spanning header naming the panel
        lines.append(r"\multicolumn{%d}{l}{\textit{%s}} \\" % (ncol + 1, label))
        # Rows for this outcome only
        sub = df[df["outcome"] == outcome]
        # One coefficient/SE row pair per quintile
        for q in QUINTILES:
            # Coefficient row starts with "Qq x Post"; SE row starts blank
            coef_cells, se_cells = [f"Q{q} $\\times$ Post"], [""]
            # Fill one cell per age group
            for a in AGE_ORDER:
                # The single estimate for this age group and quintile
                r = sub[(sub["age_bin"] == a) & (sub["ai_q"] == q)]
                # Expect exactly one matching row
                if len(r) == 1:
                    # Coefficient (4 decimals) with stars
                    coef_cells.append(f"{r['coef'].iloc[0]:.4f}{stars(r['p_value'].iloc[0])}")
                    # Standard error in parentheses
                    se_cells.append(f"({r['se'].iloc[0]:.4f})")
                else:
                    # Missing estimate: leave both cells blank
                    coef_cells.append("")
                    se_cells.append("")
            # Emit the coefficient row
            lines.append(" & ".join(coef_cells) + r" \\")
            # Emit the standard-error row
            lines.append(" & ".join(se_cells) + r" \\")
        # Space between panels (not after the last)
        if pi < len(PANELS) - 1:
            lines.append(r"\addlinespace")

    # Rule before the footer
    lines.append(r"\midrule")
    # Sample sizes are taken from the employment rows
    emp = df[df["outcome"] == "employment"]

    # Build one footer row: a label followed by one count per age group.
    def footrow(label, col):
        # Row starts with its label
        cells = [label]
        # One count cell per age group
        for a in AGE_ORDER:
            # The employment row for this age group
            r = emp[emp["age_bin"] == a]
            # Thousands-separated count, or blank if missing
            cells.append(f"{int(r[col].iloc[0]):,}" if len(r) else "")
        # Join into a LaTeX row
        return " & ".join(cells) + r" \\"

    # Number of firms per age group
    lines.append(footrow("Firms", "n_frtk"))
    # Number of observations per age group
    lines.append(footrow("Observations", "n_obs"))
    # Bottom rule
    lines.append(r"\bottomrule")
    # Close the tabular
    lines.append(r"\end{tabular}")
    # Return the joined fragment with a trailing newline
    return "\n".join(lines) + "\n"


# Guard against a missing input, then build and write the table.
def main():
    # If the secure-server coefficients are not synced, stop with instructions
    if not os.path.exists(COEF_FILE):
        sys.exit(f"Coefficient file not found: {COEF_FILE}\n"
                 "Run analysis-indiv/scripts/7b_did_byage_fepois.R on the secure "
                 "server and sync from_secure_server/ back first.")
    # Load the firm-FE coefficients
    df = pd.read_csv(COEF_FILE)
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # Build the tabular and write it
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build_tabular(df))
    # Progress message
    print(f"Wrote {OUT}")


# Run main() only when executed as a script, not when imported
if __name__ == "__main__":
    main()
