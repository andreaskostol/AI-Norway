"""
make_quintile_change_table.py

Build the cross-sectional quintile-change table from
analysis/output/coefficients/coef_quintile_change_lastmonth.csv.

Writes a caption-less LaTeX fragment (just the tabular; no \\begin{table},
\\caption or \\label -- those live in the paper .tex, per house convention).
Two panels (seasonally adjusted, raw); columns Q1..Q5 and the Q5-Q1 double
difference; each panel has a change row (in percent) and a robust-SE row;
footer reports the number of occupations.

  -> analysis/output/tables/table_quintile_change.tex

Usage:
    python analysis/05_tables/make_quintile_change_table.py
"""

import os                                    # build file paths
import pandas as pd                          # read the coefficient CSV

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")   # repo root
COEF_FILE = os.path.join(BASE_DIR, "analysis", "output", "coefficients",
                         "coef_quintile_change_lastmonth.csv")    # input data
OUT_DIR = os.path.join(BASE_DIR, "analysis", "output", "tables")  # output dir
OUT_FILE = os.path.join(OUT_DIR, "table_quintile_change.tex")     # output file

COLS = ["1", "2", "3", "4", "5", "Q5mQ1"]    # column order: Q1..Q5 then the contrast
PANELS = [("sa", "Panel A. Seasonally adjusted"),   # (basis key, panel heading)
          ("raw", "Panel B. Raw")]


def stars(coef, se):
    """Significance stars from the robust z-ratio |coef/se|."""
    if se <= 0:                              # guard against a zero/missing SE
        return ""
    z = abs(coef / se)                       # robust z-statistic
    if z > 2.576:                            # 1% two-sided critical value
        return "$^{***}$"
    if z > 1.96:                             # 5% two-sided critical value
        return "$^{**}$"
    if z > 1.645:                            # 10% two-sided critical value
        return "$^{*}$"
    return ""                                # not significant at 10%


def fmt_change(coef, se):
    """Format a change as a signed percent with stars (proportion -> percent)."""
    return f"{coef * 100:+.2f}{stars(coef, se)}"   # e.g. +0.12 or -0.05$^{*}$


def fmt_se(se):
    """Format a robust SE as a percent in parentheses (proportion -> percent)."""
    return f"({se * 100:.2f})"               # e.g. (1.47)


def build_tabular(df):
    """Return the LaTeX tabular as a string from the long coefficient frame."""
    by_key = {(r["basis"], str(r["ai_q"])): r          # look-up by (basis, column)
              for _, r in df.iterrows()}

    lines = []                                # accumulate LaTeX lines
    lines.append(r"\begin{tabular}{l" + "c" * len(COLS) + "}")  # one col per entry
    lines.append(r"\toprule")
    # Header: quintile labels + the contrast column.
    head = ["", "Q1", "Q2", "Q3", "Q4", "Q5", r"Q5$-$Q1"]
    sub = ["", "(least)", "", "", "", "(most)", "(DD)"]
    lines.append(" & ".join(head) + r" \\")
    lines.append(" & ".join(sub) + r" \\")
    lines.append(r"\midrule")

    for basis, heading in PANELS:             # one block per basis (SA, then raw)
        lines.append(r"\multicolumn{%d}{l}{\textit{%s}} \\"      # panel heading row
                     % (len(COLS) + 1, heading))
        change_cells = ["Change (\\%)"]       # row label for the point estimates
        se_cells = [""]                       # SE row has a blank label
        for c in COLS:                        # fill Q1..Q5 and the contrast
            r = by_key[(basis, c)]            # the matching coefficient row
            change_cells.append(fmt_change(r["mean_change"], r["se"]))  # change %
            se_cells.append(fmt_se(r["se"]))  # robust SE %
        lines.append(" & ".join(change_cells) + r" \\")   # write the change row
        lines.append(" & ".join(se_cells) + r" \\")       # write the SE row
        lines.append(r"\addlinespace")        # small gap before the next panel

    lines.append(r"\midrule")
    # Footer: number of occupations per quintile (and total in the contrast col).
    occ = ["Occupations"]                      # footer row label
    for c in COLS:                             # one count per column
        occ.append(f"{int(by_key[('sa', c)]['n_occ']):,}")  # same N across bases
    lines.append(" & ".join(occ) + r" \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    return "\n".join(lines) + "\n"


def main():
    df = pd.read_csv(COEF_FILE, dtype={"ai_q": str})   # read the coefficients
    os.makedirs(OUT_DIR, exist_ok=True)                # ensure output dir exists
    frag = build_tabular(df)                            # build the LaTeX tabular
    with open(OUT_FILE, "w", encoding="utf-8") as f:    # write the fragment
        f.write(frag)
    print(f"Wrote {OUT_FILE}")                          # progress message
    print(frag)                                         # echo for a quick visual check


if __name__ == "__main__":
    main()
