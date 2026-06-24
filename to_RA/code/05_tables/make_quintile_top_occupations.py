"""
make_quintile_top_occupations.py

Purpose:
  Descriptive data-section table feeding Table 1 (tab:quintile_top_occ): the
  five largest occupations (by employment) in each Eloundou exposure quintile
  as of February 2026, with occupation code, title, Eloundou score, employment,
  and the occupation's share of the quintile's total employment.

Employment ("overall") = sum of headcount over both sectors and all decade
age groups present in the parsed file (alder_gr 1-5, i.e. ages 21+), for the
February-2026 status month.

Writes a caption-less LaTeX fragment (just the tabular). The float, caption
and label live in paper/section3_data.tex around \\input{}.

  -> analysis/output/tables/table_quintile_top_occ.tex

Usage:
    python analysis/05_tables/make_quintile_top_occupations.py
"""

# os: build file paths and create the output directory
import os
# pandas: read the parsed CSVs, group, merge, and rank occupations
import pandas as pd

# Repo root, relative to this script (analysis/05_tables/ -> ../../)
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
# Parsed microdata.no cell aggregates (occupation x age x sector x month)
PARSED = os.path.join(BASE_DIR, "microdata-output",
                      "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
# Occupation -> Eloundou exposure score and quintile mapping
EXP_FILE = os.path.join(BASE_DIR, "data", "ai_exposure",
                        "styrk08_eloundou_beta_mapping.csv")
# ISCO-08 crosswalk used to label occupations with official English titles
ISCO_FILE = os.path.join(BASE_DIR, "data", "ai_exposure", "isco_soc_crosswalk.xls")
# Output LaTeX tabular fragment (caption-less; the float lives in the paper)
OUT = os.path.join(BASE_DIR, "analysis", "output", "tables",
                   "table_quintile_top_occ.tex")

# Status month for the employment snapshot (ARBLONN status date = the 16th)
STATUS_DATE = "2026-02-16"
# How many largest occupations to list per quintile
TOP_N = 5
# Human-readable headers printed above each quintile block in the table
QUINTILE_LABELS = {
    1: "Quintile 1 (least exposed)",
    2: "Quintile 2",
    3: "Quintile 3",
    4: "Quintile 4",
    5: "Quintile 5 (most exposed)",
}


# Escape characters that are special in LaTeX so occupation titles render safely.
def latex_escape(s):
    # Map each LaTeX-special character to its escaped form
    repl = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
            "_": r"\_", "{": r"\{", "}": r"\}"}
    # Coerce to string (titles may arrive as non-str)
    out = str(s)
    # Replace each special character with its escaped version
    for k, v in repl.items():
        out = out.replace(k, v)
    # Return the LaTeX-safe string
    return out


# Compute February-2026 headcount per occupation, summed over sector and age.
def load_employment():
    # Read only the columns needed; keep codes as strings to preserve leading zeros
    df = pd.read_csv(PARSED, dtype={"yrke4": str, "alder_gr": str},
                     usecols=["date", "yrke4", "alder_gr", "sekt",
                              "variable", "value"])
    # Keep the status month and employment-count rows only
    df = df[(df["date"] == STATUS_DATE) & (df["variable"] == "count")]
    # Keep decade age groups 1-5 (ages 21+)
    df = df[df["alder_gr"].isin(["1", "2", "3", "4", "5"])]
    # Sum headcount across sectors and age groups -> one row per occupation
    emp = df.groupby("yrke4", as_index=False)["value"].sum()
    # Rename the summed column to "employment"
    emp = emp.rename(columns={"value": "employment"})
    # Round to whole persons and store as integers
    emp["employment"] = emp["employment"].round().astype(int)
    # Return the per-occupation employment table
    return emp


# Load official English ISCO-08 titles to label occupations.
def load_titles():
    # Use official English ISCO-08 titles for overlapping STYRK/ISCO codes.
    # Read the crosswalk sheet; the real header starts at row 7 (header=6)
    isco = pd.read_excel(ISCO_FILE, dtype=str, header=6)
    # Keep just the code and English title columns, dropping blank rows
    isco = isco[["ISCO-08 Code", "ISCO-08 Title EN"]].dropna()
    # Rename to the join key (yrke4) and a short "title" column
    isco = isco.rename(columns={"ISCO-08 Code": "yrke4", "ISCO-08 Title EN": "title"})
    # Drop duplicate codes so the later merge stays one-to-one
    isco = isco.drop_duplicates(subset="yrke4")
    # Return the code -> title lookup
    return isco


# Assemble the table and write the LaTeX fragment.
def main():
    # February-2026 employment per occupation
    emp = load_employment()
    # Read the exposure mapping; keep code as string
    exp = pd.read_csv(EXP_FILE, dtype={"styrk08": str})
    # Drop unmapped occupations and keep code, score, and quintile
    exp = exp[exp["quintile"].notna()][["styrk08", "eloundou_beta", "quintile"]]
    # Rename the code column to the common join key
    exp = exp.rename(columns={"styrk08": "yrke4"})
    # Store the quintile as an integer
    exp["quintile"] = exp["quintile"].astype(int)

    # Inner join keeps only occupations with both employment and a quintile
    d = emp.merge(exp, on="yrke4", how="inner")
    # Load the ISCO-08 title lookup
    titles = load_titles()
    # Left join titles onto the occupations (unmatched titles stay missing)
    d = d.merge(titles, on="yrke4", how="left")
    # STYRK-08 nursing-specific codes have no 4-digit ISCO-08 analog; use
    # direct English labels.
    # Manually label STYRK-only code 2223 (nurses)
    d.loc[d["yrke4"] == "2223", "title"] = "Nurses"
    # Manually label STYRK-only code 2224 (social educators)
    d.loc[d["yrke4"] == "2224", "title"] = "Social educators"
    # Replace any remaining missing titles with empty strings
    d["title"] = d["title"].fillna("")

    # Total employment per quintile, for the within-quintile share denominator
    qtot = d.groupby("quintile")["employment"].sum().to_dict()

    # Accumulate the LaTeX lines of the tabular
    lines = []
    # Open the tabular: code, wrapped title, three right-aligned numeric columns
    lines.append(r"\begin{tabular}{l p{6.2cm} r r r}")
    # Top rule
    lines.append(r"\toprule")
    # First header row
    lines.append(r"Code & Occupation & Eloundou & Employment & Share of \\")
    # Second header row (continuation of multi-line column labels)
    lines.append(r" & & score & (Feb 2026) & quintile \\")
    # Rule under the header
    lines.append(r"\midrule")

    # One block per quintile, 1 (least exposed) to 5 (most exposed)
    for q in range(1, 6):
        # The TOP_N largest occupations in this quintile by employment
        sub = d[d["quintile"] == q].nlargest(TOP_N, "employment")
        # Italic spanning header naming the quintile
        lines.append(r"\multicolumn{5}{l}{\textit{%s}} \\" % QUINTILE_LABELS[q])
        # One row per occupation in this quintile block
        for _, r in sub.iterrows():
            # Occupation's percentage share of its quintile's total employment
            share = 100.0 * r["employment"] / qtot[q]
            # Build the data row: code, escaped title, score, employment, share
            lines.append(
                f"{r['yrke4']} & {latex_escape(r['title'])} & "
                f"{r['eloundou_beta']:.3f} & {int(r['employment']):,} & "
                f"{share:.1f}\\% \\\\"
            )
        # Add vertical space between quintile blocks (not after the last)
        if q < 5:
            lines.append(r"\addlinespace")

    # Bottom rule
    lines.append(r"\bottomrule")
    # Close the tabular
    lines.append(r"\end{tabular}")

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # Write the joined lines as the LaTeX fragment
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    # Progress message
    print(f"Wrote {OUT}")


# Run main() only when executed as a script, not when imported
if __name__ == "__main__":
    main()
