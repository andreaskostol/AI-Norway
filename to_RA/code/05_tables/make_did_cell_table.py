"""
make_did_cell_table.py

Purpose:
  Build the cell-level difference-in-differences result tables from
  analysis/output/coefficients/coef_microdata_did_cell.csv. The private-sector
  fragment feeds the paper's Table referenced as \\label{tab:did_cell}; the
  public-sector fragment is an appendix table.

Writes caption-less LaTeX fragments (just the tabular; no \\begin{table},
\\caption or \\label). The float, caption and label live in the paper section
files around \\input{} (see CLAUDE convention: captions belong in paper/*.tex).

  private (main)     -> analysis/output/tables/table3_did_cell.tex
  public  (appendix) -> analysis/output/tables/appendix_did_cell_public.tex

Usage:
    python analysis/05_tables/make_did_cell_table.py
"""

# os: build file paths and create the output directory
import os
# pandas: read the coefficient CSV and filter by sector/outcome/quintile/age
import pandas as pd

# Repo root, relative to this script (analysis/05_tables/ -> ../../)
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
# Cell-level DiD coefficient estimates (one row per sector x outcome x age x quintile)
COEF_FILE = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                         "coef_microdata_did_cell.csv")
# Directory where the LaTeX table fragments are written
OUT_DIR = os.path.join(BASE_DIR, "analysis", "output", "tables")

# Decade age groups, in column order (1=21-30 ... 4=51-60)
AGE_ORDER = [1, 2, 3, 4]
# Two-line column headers for each age group
AGE_HEADERS = {
    1: ("Early career", "(21--30)"),
    2: ("31--40", ""),
    3: ("41--50", ""),
    4: ("Senior", "(51--60)"),
}
# (outcome key, panel label)
# Panels stacked in the table: each is (outcome key in CSV, printed panel title)
PANELS = [
    ("employment", "Panel A. Employment (Poisson)"),
    ("new_hires", "Panel B. New hires (Poisson)"),
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


# Format a coefficient to four decimals with its significance stars.
def fmt_coef(coef, p):
    return f"{coef:.4f}{stars(p)}"


# Format a standard error to four decimals, in parentheses.
def fmt_se(se):
    return f"({se:.4f})"


# Build the full LaTeX tabular string for one sector's coefficients.
def build_tabular(df_sec):
    """df_sec: rows for one sector. Returns the LaTeX tabular as a string."""
    # Number of numeric (age-group) columns
    ncol = len(AGE_ORDER)
    # Accumulate the tabular's lines
    lines = []
    # Open the tabular: a label column plus one centered column per age group
    lines.append(r"\begin{tabular}{l" + "c" * ncol + "}")
    # Top rule
    lines.append(r"\toprule")

    # Header: two label rows + numbered row
    # First header row: blank label cell + age-group names
    top = [""] + [AGE_HEADERS[a][0] for a in AGE_ORDER]
    # Second header row: blank label cell + age ranges
    sub = [""] + [AGE_HEADERS[a][1] for a in AGE_ORDER]
    # Third header row: blank label cell + column numbers (1)..(ncol)
    num = [""] + [f"({i + 1})" for i in range(ncol)]
    # Emit the three header rows
    lines.append(" & ".join(top) + r" \\")
    lines.append(" & ".join(sub) + r" \\")
    lines.append(" & ".join(num) + r" \\")
    # Rule under the header
    lines.append(r"\midrule")

    # One panel per outcome (employment, new hires)
    for pi, (outcome, label) in enumerate(PANELS):
        # Italic spanning header naming the panel
        lines.append(r"\multicolumn{%d}{l}{\textit{%s}} \\" % (ncol + 1, label))
        # Rows for this outcome only
        sub = df_sec[df_sec["outcome"] == outcome]
        # One coefficient/SE row pair per quintile
        for q in QUINTILES:
            # Coefficient row starts with the "Qq x Post" row label
            coef_cells = [f"Q{q} $\\times$ Post"]
            # SE row starts with a blank label cell
            se_cells = [""]
            # Fill one cell per age group
            for a in AGE_ORDER:
                # The single estimate for this age group and quintile
                r = sub[(sub["age_group"] == a) & (sub["ai_q"] == q)]
                # Expect exactly one matching row
                if len(r) == 1:
                    # Coefficient with stars
                    coef_cells.append(fmt_coef(r["coef"].iloc[0], r["p_value"].iloc[0]))
                    # Standard error in parentheses
                    se_cells.append(fmt_se(r["se"].iloc[0]))
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

    # Footer: occupations and observations (from employment)
    # Sample sizes are taken from the employment rows
    emp = df_sec[df_sec["outcome"] == "employment"]

    # Build one footer row: a label followed by one count per age group.
    def footrow(label, frame, col):
        # Row starts with its label
        cells = [label]
        # One count cell per age group
        for a in AGE_ORDER:
            # The employment row for this age group
            r = frame[frame["age_group"] == a]
            # Thousands-separated count, or blank if missing
            cells.append(f"{int(r[col].iloc[0]):,}" if len(r) else "")
        # Join into a LaTeX row
        return " & ".join(cells) + r" \\"

    # Number of occupations (cells) per age group
    lines.append(footrow("Occupations", emp, "n_occ"))
    # Number of observations per age group
    lines.append(footrow("Observations (count)", emp, "n_obs"))

    # Bottom rule
    lines.append(r"\bottomrule")
    # Close the tabular
    lines.append(r"\end{tabular}")
    # Return the joined fragment with a trailing newline
    return "\n".join(lines) + "\n"


# Read coefficients, build one fragment per sector, and write them out.
def main():
    # Load all cell-level DiD coefficients
    df = pd.read_csv(COEF_FILE)
    # Ensure the output directory exists
    os.makedirs(OUT_DIR, exist_ok=True)

    # Sector code -> output filename (2 = private main, 1 = public appendix)
    targets = {2: "table3_did_cell.tex", 1: "appendix_did_cell_public.tex"}
    # Build and write one table per sector
    for sector, fname in targets.items():
        # Tabular for this sector's rows
        frag = build_tabular(df[df["sector"] == sector])
        # Full output path
        path = os.path.join(OUT_DIR, fname)
        # Write the fragment
        with open(path, "w", encoding="utf-8") as f:
            f.write(frag)
        # Progress message
        print(f"Wrote {path}")


# Run main() only when executed as a script, not when imported
if __name__ == "__main__":
    main()
