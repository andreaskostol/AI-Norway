"""
make_quintile_top_occupations.py

Descriptive data-section table: the five largest occupations (by employment)
in each Eloundou exposure quintile as of February 2026, with occupation code,
title, Eloundou score, employment, and the occupation's share of the
quintile's total employment.

Employment ("overall") = sum of headcount over both sectors and all decade
age groups present in the parsed file (alder_gr 1-5, i.e. ages 21+), for the
February-2026 status month.

Writes a caption-less LaTeX fragment (just the tabular). The float, caption
and label live in paper/section3_data.tex around \\input{}.

  -> analysis/output/tables/table_quintile_top_occ.tex

Usage:
    python analysis/05_tables/make_quintile_top_occupations.py
"""

import os
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
PARSED = os.path.join(BASE_DIR, "microdata-output",
                      "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE = os.path.join(BASE_DIR, "data", "ai_exposure",
                        "styrk08_eloundou_beta_mapping.csv")
ISCO_FILE = os.path.join(BASE_DIR, "data", "ai_exposure", "isco_soc_crosswalk.xls")
OUT = os.path.join(BASE_DIR, "analysis", "output", "tables",
                   "table_quintile_top_occ.tex")

STATUS_DATE = "2026-02-16"
TOP_N = 5
QUINTILE_LABELS = {
    1: "Quintile 1 (least exposed)",
    2: "Quintile 2",
    3: "Quintile 3",
    4: "Quintile 4",
    5: "Quintile 5 (most exposed)",
}


def latex_escape(s):
    repl = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
            "_": r"\_", "{": r"\{", "}": r"\}"}
    out = str(s)
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


def load_employment():
    df = pd.read_csv(PARSED, dtype={"yrke4": str, "alder_gr": str},
                     usecols=["date", "yrke4", "alder_gr", "sekt",
                              "variable", "value"])
    df = df[(df["date"] == STATUS_DATE) & (df["variable"] == "count")]
    df = df[df["alder_gr"].isin(["1", "2", "3", "4", "5"])]
    emp = df.groupby("yrke4", as_index=False)["value"].sum()
    emp = emp.rename(columns={"value": "employment"})
    emp["employment"] = emp["employment"].round().astype(int)
    return emp


def load_titles():
    # Use official English ISCO-08 titles for overlapping STYRK/ISCO codes.
    isco = pd.read_excel(ISCO_FILE, dtype=str, header=6)
    isco = isco[["ISCO-08 Code", "ISCO-08 Title EN"]].dropna()
    isco = isco.rename(columns={"ISCO-08 Code": "yrke4", "ISCO-08 Title EN": "title"})
    isco = isco.drop_duplicates(subset="yrke4")
    return isco


def main():
    emp = load_employment()
    exp = pd.read_csv(EXP_FILE, dtype={"styrk08": str})
    exp = exp[exp["quintile"].notna()][["styrk08", "eloundou_beta", "quintile"]]
    exp = exp.rename(columns={"styrk08": "yrke4"})
    exp["quintile"] = exp["quintile"].astype(int)

    d = emp.merge(exp, on="yrke4", how="inner")
    titles = load_titles()
    d = d.merge(titles, on="yrke4", how="left")
    # STYRK-08 nursing-specific codes have no 4-digit ISCO-08 analog; use
    # direct English labels.
    d.loc[d["yrke4"] == "2223", "title"] = "Nurses"
    d.loc[d["yrke4"] == "2224", "title"] = "Social educators"
    d["title"] = d["title"].fillna("")

    qtot = d.groupby("quintile")["employment"].sum().to_dict()

    lines = []
    lines.append(r"\begin{tabular}{l p{6.2cm} r r r}")
    lines.append(r"\toprule")
    lines.append(r"Code & Occupation & Eloundou & Employment & Share of \\")
    lines.append(r" & & score & (Feb 2026) & quintile \\")
    lines.append(r"\midrule")

    for q in range(1, 6):
        sub = d[d["quintile"] == q].nlargest(TOP_N, "employment")
        lines.append(r"\multicolumn{5}{l}{\textit{%s}} \\" % QUINTILE_LABELS[q])
        for _, r in sub.iterrows():
            share = 100.0 * r["employment"] / qtot[q]
            lines.append(
                f"{r['yrke4']} & {latex_escape(r['title'])} & "
                f"{r['eloundou_beta']:.3f} & {int(r['employment']):,} & "
                f"{share:.1f}\\% \\\\"
            )
        if q < 5:
            lines.append(r"\addlinespace")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
