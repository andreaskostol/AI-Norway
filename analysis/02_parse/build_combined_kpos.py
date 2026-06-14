"""Bygger samlet 09-fil fra de 4 kpos-parsed-filene.

Output: microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv

Drop-in-erstatning for `09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv` for
analyser som bruker kun count, kontantlonn, kontantlonn_sd, stillingspst,
ny_jobb. Filen inneholder IKKE timelonn eller overtid_timer (de er ikke laget
i kpos-varianten); scripts som trenger de variablene maa bruke den eldre,
ufiltrede samlefilen.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "microdata-output"

INPUTS = [
    OUT / "09a_count_kpos_2021m01_2026m02_parsed.csv",
    OUT / "09b_kontantlonn_kpos_2021m01_2026m02_parsed.csv",
    OUT / "09c_stillingspst_kpos_2021m01_2026m02_parsed.csv",
    OUT / "09f_nyjobb_kpos_2021m01_2026m02_parsed.csv",
]
OUTPUT = OUT / "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv"


def main() -> None:
    parts = []
    for p in INPUTS:
        if not p.exists():
            raise SystemExit(f"missing input: {p}")
        # Les value som streng for aa bevare opprinnelig formatering
        # (count er heltall, kontantlonn/stillingspst/ny_jobb er float).
        df = pd.read_csv(p, dtype={"yrke4": str, "alder_gr": str, "sekt": str,
                                   "variable": str, "value": str})
        print(f"  {p.name}: {len(df):,} rader, "
              f"variabler={sorted(df['variable'].unique())}")
        parts.append(df)

    combined = pd.concat(parts, ignore_index=True)
    combined = combined[["date", "yrke4", "alder_gr", "sekt", "variable",
                          "value"]]
    combined.sort_values(["variable", "date", "yrke4", "alder_gr", "sekt"],
                          inplace=True)
    combined.to_csv(OUTPUT, index=False)
    print(f"\nWrote {len(combined):,} rader til {OUTPUT}")
    print(f"  variabler: {sorted(combined['variable'].unique())}")
    print(f"  datoer:    {combined['date'].min()} til {combined['date'].max()} "
          f"({combined['date'].nunique()} mnd)")
    print(f"  yrke4:     {combined['yrke4'].nunique()} unike")


if __name__ == "__main__":
    main()
