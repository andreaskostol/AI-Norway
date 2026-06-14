"""Sammenlikner kpos-filtrerte tidsserier mot eksisterende ufiltret 09-output.

Ufiltret kilde: microdata-output/09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv
Kpos-kilder:   microdata-output/09{a,b,c,f}_*_kpos_2021m01_2026m02_parsed.csv

Schema (begge): date, yrke4, alder_gr, sekt, variable, value

Rapport for hvert utfall:
  - dekning (antall celler i kpos vs ufiltret)
  - ratio kpos/ufiltret (mean, median, p10, p90) over alle matchende celler
  - for count og ny_jobb: total over hele perioden
  - for kontantlonn og stillingspst: mean av celleverdier

Filter for analyse: alder_gr in {1,2,3,4}, sekt in {1,2}, yrke4 != '0000'.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "microdata-output"

OLD = OUT / "09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv"
KPOS_FILES = {
    "count":       OUT / "09a_count_kpos_2021m01_2026m02_parsed.csv",
    "kontantlonn": OUT / "09b_kontantlonn_kpos_2021m01_2026m02_parsed.csv",
    "stillingspst":OUT / "09c_stillingspst_kpos_2021m01_2026m02_parsed.csv",
    "ny_jobb":     OUT / "09f_nyjobb_kpos_2021m01_2026m02_parsed.csv",
}

VAR_TYPE = {
    "count":        "count",  # heltallsverdier, totaler meningsfulle
    "kontantlonn":  "mean",   # celle-snitt
    "stillingspst": "mean",   # celle-snitt
    "ny_jobb":      "mean",   # celle-andel
}


def load(path):
    df = pd.read_csv(
        path,
        dtype={"yrke4": str, "alder_gr": str, "sekt": str, "variable": str},
    )
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[df["alder_gr"].isin({"1", "2", "3", "4"})]
    df = df[df["sekt"].isin({"1", "2"})]
    df = df[df["yrke4"] != "0000"]
    df = df.dropna(subset=["value"])
    return df


def compare(var_name, kpos_path):
    print(f"\n=== {var_name} ===")
    old = load(OLD)
    old = old[old["variable"] == var_name].copy()
    kpos = load(kpos_path)
    kpos = kpos[kpos["variable"] == var_name].copy()

    print(f"  ufiltret rader: {len(old):,}")
    print(f"  kpos rader:     {len(kpos):,}")

    key = ["date", "yrke4", "alder_gr", "sekt"]
    merged = old.merge(
        kpos[key + ["value"]],
        on=key,
        how="inner",
        suffixes=("_unf", "_kpos"),
    )
    print(f"  matchende celler: {len(merged):,}")

    if VAR_TYPE[var_name] == "count":
        tot_unf = merged["value_unf"].sum()
        tot_kpos = merged["value_kpos"].sum()
        print(f"  total ufiltret:   {tot_unf:>15,.0f}")
        print(f"  total kpos:       {tot_kpos:>15,.0f}")
        print(f"  ratio kpos/unf:   {tot_kpos/tot_unf:>15.4f}")
        merged["ratio"] = merged["value_kpos"] / merged["value_unf"].replace(0, np.nan)
    else:
        mean_unf = merged["value_unf"].mean()
        mean_kpos = merged["value_kpos"].mean()
        print(f"  mean ufiltret:    {mean_unf:>15.3f}")
        print(f"  mean kpos:        {mean_kpos:>15.3f}")
        print(f"  ratio kpos/unf:   {mean_kpos/mean_unf:>15.4f}")
        merged["ratio"] = merged["value_kpos"] / merged["value_unf"].replace(0, np.nan)
        merged["diff"] = merged["value_kpos"] - merged["value_unf"]

    r = merged["ratio"].dropna()
    print(f"  celle-ratio: p10={r.quantile(0.1):.4f}  median={r.median():.4f}"
          f"  mean={r.mean():.4f}  p90={r.quantile(0.9):.4f}")

    if VAR_TYPE[var_name] == "mean":
        d = merged["diff"].dropna()
        print(f"  celle-diff: p10={d.quantile(0.1):+.3f}  median={d.median():+.3f}"
              f"  mean={d.mean():+.3f}  p90={d.quantile(0.9):+.3f}")


def main():
    if not OLD.exists():
        sys.exit(f"missing: {OLD}")
    for var, path in KPOS_FILES.items():
        if not path.exists():
            print(f"[skip] {var}: missing {path}")
            continue
        compare(var, path)


if __name__ == "__main__":
    main()
