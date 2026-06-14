"""
create_tables.py

Compute pairwise Spearman rank correlations across all AI exposure measures
mapped to STYRK-08 occupations, and export the correlation matrix as a LaTeX
table (Table 2).

Usage:
    python analysis/python/create_tables.py
"""

import os
import pandas as pd
from scipy.stats import spearmanr
import numpy as np

# ---------------------------------------------------------------------------
# Paths (relative to project root)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "data", "ai_exposure")
OUT_DIR = os.path.join(BASE_DIR, "analysis", "output", "tables")

# ---------------------------------------------------------------------------
# 1. Load all measures and merge on styrk08
# ---------------------------------------------------------------------------

# Each entry: (filename, column(s) to keep, rename dict)
SOURCES = [
    (
        "styrk08_eloundou_beta_mapping.csv",
        ["styrk08", "eloundou_beta"],
        {"eloundou_beta": "Eloundou"},
    ),
    (
        "styrk08_handa_mapping.csv",
        ["styrk08", "overall_exposure"],
        {"overall_exposure": "Handa"},
    ),
    (
        "styrk08_felten_mapping.csv",
        ["styrk08", "aioe", "aioe_lm"],
        {"aioe": "Felten AIOE", "aioe_lm": "Felten LM"},
    ),
    (
        "styrk08_job_exposure_mapping.csv",
        ["styrk08", "observed_exposure"],
        {"observed_exposure": "Observed"},
    ),
    (
        "kostol_ai_exposure.csv",
        ["styrk08", "exposure_index"],
        {"exposure_index": "Kostol"},
    ),
]


def load_sources():
    """Load each CSV, keep relevant columns, rename, and merge on styrk08."""
    merged = None
    for filename, cols, rename in SOURCES:
        path = os.path.join(DATA_DIR, filename)
        df = pd.read_csv(path, dtype={"styrk08": str})
        df = df[cols].rename(columns=rename)
        if merged is None:
            merged = df
        else:
            merged = merged.merge(df, on="styrk08", how="outer")
    return merged


# ---------------------------------------------------------------------------
# 2. Compute pairwise Spearman rank correlations
# ---------------------------------------------------------------------------

def spearman_matrix(df, measures):
    """
    Compute NxN Spearman correlation matrix using pairwise complete
    observations (i.e., drop NaN separately for each pair).
    """
    n = len(measures)
    corr = pd.DataFrame(np.ones((n, n)), index=measures, columns=measures)

    for i in range(n):
        for j in range(i + 1, n):
            pair = df[[measures[i], measures[j]]].dropna()
            if len(pair) >= 3:
                rho, _ = spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
            else:
                rho = np.nan
            corr.iloc[i, j] = rho
            corr.iloc[j, i] = rho

    return corr


# ---------------------------------------------------------------------------
# 3. Print nicely
# ---------------------------------------------------------------------------

def print_matrix(corr):
    """Pretty-print the Spearman correlation matrix to the console."""
    print("\n=== Spearman rank correlation matrix (pairwise complete obs) ===\n")
    # Format to 3 decimals
    formatted = corr.map(lambda x: f"{x:.3f}")
    print(formatted.to_string())
    print()


# ---------------------------------------------------------------------------
# 4. Save as LaTeX table
# ---------------------------------------------------------------------------

def save_latex(corr, path):
    """
    Save the lower triangle of the correlation matrix as a LaTeX table.
    Diagonal shows 1.000; upper triangle is left blank for readability.
    """
    measures = corr.columns.tolist()
    n = len(measures)

    # Build lower-triangle version
    display = corr.copy()
    for i in range(n):
        for j in range(n):
            if j > i:
                display.iloc[i, j] = np.nan  # blank upper triangle

    # Number the columns for compact headers
    col_labels = [f"({k+1})" for k in range(n)]

    lines = []
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\caption{Spearman rank correlations across AI exposure measures}")
    lines.append(r"\label{tab:correlations}")
    # First column for measure name, then one column per measure
    col_spec = "l" + "c" * n
    lines.append(r"\begin{tabular}{" + col_spec + "}")
    lines.append(r"\toprule")

    # Header row
    header = " & ".join([""] + col_labels) + r" \\"
    lines.append(header)
    lines.append(r"\midrule")

    # Data rows
    for i, measure in enumerate(measures):
        row_label = f"({i+1}) {measure}"
        cells = []
        for j in range(n):
            val = display.iloc[i, j]
            if pd.isna(val):
                cells.append("")
            elif i == j:
                cells.append("1")
            else:
                cells.append(f"{val:.3f}")
        row = " & ".join([row_label] + cells) + r" \\"
        lines.append(row)

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(
        r"\begin{minipage}{\textwidth}"
        "\n"
        r"\footnotesize\textit{Note:} "
        r"Pairwise Spearman rank correlations computed over STYRK-08 "
        r"four-digit occupations with non-missing values for each pair."
        "\n"
        r"\end{minipage}"
    )
    lines.append(r"\end{table}")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"LaTeX table saved to: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    df = load_sources()
    measures = [col for col in df.columns if col != "styrk08"]

    print(f"Loaded {len(df)} STYRK-08 occupations, {len(measures)} measures.")
    print(f"Non-missing counts:\n{df[measures].count()}\n")

    corr = spearman_matrix(df, measures)
    print_matrix(corr)

    out_path = os.path.join(OUT_DIR, "table2_correlations.tex")
    save_latex(corr, out_path)


if __name__ == "__main__":
    main()
