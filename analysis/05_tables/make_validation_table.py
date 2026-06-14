"""
make_validation_table.py

Cell-vs-individual reconciliation table. Shows the Q5-vs-Q1 (most vs least
exposed) post-October-2022 employment DiD coefficient under four nested
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

import os
import pandas as pd

BASE = os.path.join(os.path.dirname(__file__), "..", "..")
MICRO = os.path.join(BASE, "analysis", "output", "coefficients",
                     "coef_microdata_did_cell.csv")
CELLSPEC = os.path.join(BASE, "analysis-indiv", "from_secure_server",
                        "coefficients", "coef_did_byage_cellspec.csv")
FEPOIS = os.path.join(BASE, "analysis-indiv", "from_secure_server",
                      "coefficients", "coef_did_byage_fepois.csv")
OUT = os.path.join(BASE, "analysis", "output", "tables",
                   "table_validation_cell_vs_firmfe.tex")

AGE_ORDER = [1, 2, 3, 4]
AGE_LAB = {1: ("Early career", "(21--30)"), 2: ("31--40", ""),
           3: ("41--50", ""), 4: ("Senior", "(51--60)")}
OUTCOME = "employment"
QCOL = 5  # Q5 vs Q1


def stars(p):
    return "$^{***}$" if p < 0.01 else "$^{**}$" if p < 0.05 else "$^{*}$" if p < 0.1 else ""


def get(df, age, agecol, coefcol, secol, pcol):
    r = df[df[agecol] == age]
    if len(r) != 1:
        return None
    return float(r[coefcol].iloc[0]), float(r[secol].iloc[0]), float(r[pcol].iloc[0])


def main():
    micro = pd.read_csv(MICRO)
    micro = micro[(micro["sector"] == 2) & (micro["outcome"] == OUTCOME)
                  & (micro["ai_q"] == QCOL)]

    cs = pd.read_csv(CELLSPEC)
    cs = cs[(cs["outcome"] == OUTCOME) & (cs["ai_q"] == QCOL)]
    unr = cs[cs["variant"] == "unrestricted_priv"]
    res = cs[cs["variant"] == "restricted"]

    fe = pd.read_csv(FEPOIS)
    fe = fe[(fe["sample"] == "headline_priv") & (fe["outcome"] == OUTCOME)
            & (fe["ai_q"] == QCOL)]

    cols = [
        (micro, "age_group", "coef", "se", "p_value"),
        (unr, "age_bin", "coef", "se", "p_value"),
        (res, "age_bin", "coef", "se", "p_value"),
        (fe, "age_bin", "coef", "se", "p_value"),
    ]

    L = []
    L.append(r"\begin{tabular}{lcccc}")
    L.append(r"\toprule")
    L.append(r" & microdata.no & \multicolumn{3}{c}{Individual records (universe 1191)} \\")
    L.append(r"\cmidrule(lr){2-2}\cmidrule(lr){3-5}")
    L.append(r" & cell & cell, all & cell, $\geq$20 & firm FE \\")
    L.append(r" & (1) & (2) & (3) & (4) \\")
    L.append(r"\midrule")

    for a in AGE_ORDER:
        top, sub = AGE_LAB[a]
        coef_cells, se_cells = [top], [sub]
        for df, agecol, c, s, p in cols:
            v = get(df, a, agecol, c, s, p)
            if v is None:
                coef_cells.append("")
                se_cells.append("")
            else:
                coef_cells.append(f"{v[0]:+.4f}{stars(v[2])}")
                se_cells.append(f"({v[1]:.4f})")
        L.append(" & ".join(coef_cells) + r" \\")
        L.append(" & ".join(se_cells) + r" \\")

    L.append(r"\bottomrule")
    L.append(r"\end{tabular}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
