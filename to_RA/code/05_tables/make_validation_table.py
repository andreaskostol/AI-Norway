"""
make_validation_table.py

Purpose:
  Cell-vs-individual reconciliation table feeding the paper's Table referenced
  as \\label{tab:validation}. Shows the Q5-vs-Q1 (most vs least exposed)
  post-October-2022 employment DiD coefficient under four nested
  specifications, isolating the contribution of data source, the >=20-worker
  restriction, and the firm-FE specification:

  (1) microdata.no aggregates, cell spec (yrke4 + month FE)
  (2) universe 1191 individual records, cell spec, all private foretak
  (3) universe 1191 individual records, cell spec, foretak with >=20 workers
  (4) universe 1191 individual records, firm-FE spec (firm x quintile + firm x month FE)

(1)->(2): data source.  (2)->(3): >=20 restriction.  (3)->(4): specification.

Inputs:
  analysis/output/coefficients/coef_microdata_did_cell.csv          (sector 2 = private)
  analysis-indiv/from_secure_server/coefficients/coef_did_byage_cellspec.csv
  analysis-indiv/from_secure_server/coefficients/coef_did_byage_fepois.csv

Output:
  analysis/output/tables/table_validation_cell_vs_firmfe.tex  (caption-less tabular)

Usage:
    python analysis/05_tables/make_validation_table.py
"""

# os: build file paths and create the output directory
import os
# pandas: read the three coefficient CSVs and filter them
import pandas as pd

# Repo root, relative to this script (analysis/05_tables/ -> ../../)
BASE = os.path.join(os.path.dirname(__file__), "..", "..")
# Column (1): microdata.no cell-level DiD coefficients
MICRO = os.path.join(BASE, "analysis", "output", "coefficients",
                     "coef_microdata_did_cell.csv")
# Columns (2)-(3): individual-record cell-spec DiD (secure-server output)
CELLSPEC = os.path.join(BASE, "analysis-indiv", "from_secure_server",
                        "coefficients", "coef_did_byage_cellspec.csv")
# Column (4): individual-record firm-FE Poisson DiD (secure-server output)
FEPOIS = os.path.join(BASE, "analysis-indiv", "from_secure_server",
                      "coefficients", "coef_did_byage_fepois.csv")
# Output LaTeX tabular fragment (caption-less; the float lives in the paper)
OUT = os.path.join(BASE, "analysis", "output", "tables",
                   "table_validation_cell_vs_firmfe.tex")

# Decade age groups, in row order (1=21-30 ... 4=51-60)
AGE_ORDER = [1, 2, 3, 4]
# Two-part row labels for each age group (name, range)
AGE_LAB = {1: ("Early career", "(21--30)"), 2: ("31--40", ""),
           3: ("41--50", ""), 4: ("Senior", "(51--60)")}
# Outcome shown in this table
OUTCOME = "employment"
QCOL = 5  # Q5 vs Q1


# Return LaTeX significance stars for a p-value (***/**/* or none).
def stars(p):
    return "$^{***}$" if p < 0.01 else "$^{**}$" if p < 0.05 else "$^{*}$" if p < 0.1 else ""


# Pull (coef, se, p) for one age group from a frame; None if not exactly one row.
def get(df, age, agecol, coefcol, secol, pcol):
    # Rows matching this age group
    r = df[df[agecol] == age]
    # Require exactly one matching row
    if len(r) != 1:
        return None
    # Return coefficient, standard error, and p-value as floats
    return float(r[coefcol].iloc[0]), float(r[secol].iloc[0]), float(r[pcol].iloc[0])


# Read the four specifications, build the table, and write the fragment.
def main():
    # Column (1): microdata.no cell coefficients
    micro = pd.read_csv(MICRO)
    # Keep private sector, employment, Q5-vs-Q1 only
    micro = micro[(micro["sector"] == 2) & (micro["outcome"] == OUTCOME)
                  & (micro["ai_q"] == QCOL)]

    # Columns (2)-(3): individual-record cell-spec coefficients
    cs = pd.read_csv(CELLSPEC)
    # Keep employment, Q5-vs-Q1 only
    cs = cs[(cs["outcome"] == OUTCOME) & (cs["ai_q"] == QCOL)]
    # Column (2): all private foretak (unrestricted)
    unr = cs[cs["variant"] == "unrestricted_priv"]
    # Column (3): foretak with >=20 workers (restricted)
    res = cs[cs["variant"] == "restricted"]

    # Column (4): individual-record firm-FE Poisson coefficients
    fe = pd.read_csv(FEPOIS)
    # Keep the headline private sample, employment, Q5-vs-Q1 only
    fe = fe[(fe["sample"] == "headline_priv") & (fe["outcome"] == OUTCOME)
            & (fe["ai_q"] == QCOL)]

    # The four columns, each as (frame, age column name, coef/se/p columns)
    cols = [
        (micro, "age_group", "coef", "se", "p_value"),
        (unr, "age_bin", "coef", "se", "p_value"),
        (res, "age_bin", "coef", "se", "p_value"),
        (fe, "age_bin", "coef", "se", "p_value"),
    ]

    # Accumulate the LaTeX lines of the tabular
    L = []
    # Open the tabular: row label + four centered specification columns
    L.append(r"\begin{tabular}{lcccc}")
    # Top rule
    L.append(r"\toprule")
    # Grouped header: microdata.no vs the three individual-record columns
    L.append(r" & microdata.no & \multicolumn{3}{c}{Individual records (universe 1191)} \\")
    # Rules underlining the two header groups
    L.append(r"\cmidrule(lr){2-2}\cmidrule(lr){3-5}")
    # Specification labels for the four columns
    L.append(r" & cell & cell, all & cell, $\geq$20 & firm FE \\")
    # Column numbers (1)-(4)
    L.append(r" & (1) & (2) & (3) & (4) \\")
    # Rule under the header
    L.append(r"\midrule")

    # One coefficient/SE row pair per age group
    for a in AGE_ORDER:
        # Age-group label parts (name on coef row, range on SE row)
        top, sub = AGE_LAB[a]
        # Coefficient and SE rows start with their respective labels
        coef_cells, se_cells = [top], [sub]
        # Fill one cell per specification column
        for df, agecol, c, s, p in cols:
            # Pull this column's estimate for this age group
            v = get(df, a, agecol, c, s, p)
            # Missing estimate: leave both cells blank
            if v is None:
                coef_cells.append("")
                se_cells.append("")
            else:
                # Signed coefficient with stars
                coef_cells.append(f"{v[0]:+.4f}{stars(v[2])}")
                # Standard error in parentheses
                se_cells.append(f"({v[1]:.4f})")
        # Emit the coefficient row
        L.append(" & ".join(coef_cells) + r" \\")
        # Emit the standard-error row
        L.append(" & ".join(se_cells) + r" \\")

    # Bottom rule
    L.append(r"\bottomrule")
    # Close the tabular
    L.append(r"\end{tabular}")

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # Write the joined lines as the LaTeX fragment
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    # Progress message
    print(f"Wrote {OUT}")


# Run main() only when executed as a script, not when imported
if __name__ == "__main__":
    main()
