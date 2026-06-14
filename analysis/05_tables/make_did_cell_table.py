"""
make_did_cell_table.py

Build the cell-level difference-in-differences result tables from
analysis/output/coefficients/coef_microdata_did_cell.csv.

Writes caption-less LaTeX fragments (just the tabular; no \\begin{table},
\\caption or \\label). The float, caption and label live in the paper section
files around \\input{} (see CLAUDE convention: captions belong in paper/*.tex).

  private (main)     -> analysis/output/tables/table3_did_cell.tex
  public  (appendix) -> analysis/output/tables/appendix_did_cell_public.tex

Usage:
    python analysis/05_tables/make_did_cell_table.py
"""

import os
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF_FILE = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                         "coef_microdata_did_cell.csv")
OUT_DIR = os.path.join(BASE_DIR, "analysis", "output", "tables")

AGE_ORDER = [1, 2, 3, 4]
AGE_HEADERS = {
    1: ("Early career", "(21--30)"),
    2: ("31--40", ""),
    3: ("41--50", ""),
    4: ("Senior", "(51--60)"),
}
# (outcome key, panel label)
PANELS = [
    ("employment", "Panel A. Employment (Poisson)"),
    ("new_hires", "Panel B. New hires (Poisson)"),
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


def fmt_coef(coef, p):
    return f"{coef:.4f}{stars(p)}"


def fmt_se(se):
    return f"({se:.4f})"


def build_tabular(df_sec):
    """df_sec: rows for one sector. Returns the LaTeX tabular as a string."""
    ncol = len(AGE_ORDER)
    lines = []
    lines.append(r"\begin{tabular}{l" + "c" * ncol + "}")
    lines.append(r"\toprule")

    # Header: two label rows + numbered row
    top = [""] + [AGE_HEADERS[a][0] for a in AGE_ORDER]
    sub = [""] + [AGE_HEADERS[a][1] for a in AGE_ORDER]
    num = [""] + [f"({i + 1})" for i in range(ncol)]
    lines.append(" & ".join(top) + r" \\")
    lines.append(" & ".join(sub) + r" \\")
    lines.append(" & ".join(num) + r" \\")
    lines.append(r"\midrule")

    for pi, (outcome, label) in enumerate(PANELS):
        lines.append(r"\multicolumn{%d}{l}{\textit{%s}} \\" % (ncol + 1, label))
        sub = df_sec[df_sec["outcome"] == outcome]
        for q in QUINTILES:
            coef_cells = [f"Q{q} $\\times$ Post"]
            se_cells = [""]
            for a in AGE_ORDER:
                r = sub[(sub["age_group"] == a) & (sub["ai_q"] == q)]
                if len(r) == 1:
                    coef_cells.append(fmt_coef(r["coef"].iloc[0], r["p_value"].iloc[0]))
                    se_cells.append(fmt_se(r["se"].iloc[0]))
                else:
                    coef_cells.append("")
                    se_cells.append("")
            lines.append(" & ".join(coef_cells) + r" \\")
            lines.append(" & ".join(se_cells) + r" \\")
        if pi < len(PANELS) - 1:
            lines.append(r"\addlinespace")

    lines.append(r"\midrule")

    # Footer: occupations and observations (from employment)
    emp = df_sec[df_sec["outcome"] == "employment"]

    def footrow(label, frame, col):
        cells = [label]
        for a in AGE_ORDER:
            r = frame[frame["age_group"] == a]
            cells.append(f"{int(r[col].iloc[0]):,}" if len(r) else "")
        return " & ".join(cells) + r" \\"

    lines.append(footrow("Occupations", emp, "n_occ"))
    lines.append(footrow("Observations (count)", emp, "n_obs"))

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    return "\n".join(lines) + "\n"


def main():
    df = pd.read_csv(COEF_FILE)
    os.makedirs(OUT_DIR, exist_ok=True)

    targets = {2: "table3_did_cell.tex", 1: "appendix_did_cell_public.tex"}
    for sector, fname in targets.items():
        frag = build_tabular(df[df["sector"] == sector])
        path = os.path.join(OUT_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(frag)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
