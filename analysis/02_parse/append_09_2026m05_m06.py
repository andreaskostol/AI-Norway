"""
Incrementally extend the kpos decade pipeline with May + June 2026, from the
single combined export produced by
microdata-scripts/monthly/09_kpos_decade_2026m05_m06.mdata (no.ssb.fdb:56).

Clone of append_09_2026m03_m04.py: parses the 2-month export, drops any
existing 2026-05/2026-06 rows (idempotent), appends the new months, and writes
new `_2021m01_2026m06_parsed.csv` files, leaving the `_2026m04` files
untouched.

It writes:
  * the four per-variable kpos files (09a/09b/09c/09f) -> _2026m06
  * the kpos combined file  -> _2026m06  (same concat/sort as build_combined_kpos.py)
  * the non-kpos combined file -> _2026m06 (only timelonn + overtid_timer added)

Usage:
    python analysis/02_parse/append_09_2026m05_m06.py
"""

import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from parse_multi_tabulate import parse_multi_tabulate  # noqa: E402

ROOT = SCRIPT_DIR.parents[1]
OUT = ROOT / "microdata-output"

SRC = OUT / "09_kpos_decade_2026_05_06.csv"

NEW_DATES = {"2026-05-16", "2026-06-16"}

# Variables carried by each destination file.
KPOS_VARS = {"count", "kontantlonn", "kontantlonn_sd", "stillingspst", "ny_jobb"}
NONKPOS_ADD_VARS = {"timelonn", "overtid_timer"}

# Per-variable kpos files: (old parsed path, new parsed path, variables kept).
PER_VAR = [
    ("09a_count_kpos",        {"count"}),
    ("09b_kontantlonn_kpos",  {"kontantlonn", "kontantlonn_sd"}),
    ("09c_stillingspst_kpos", {"stillingspst"}),
    ("09f_nyjobb_kpos",       {"ny_jobb"}),
]

OLD_TAG = "2021m01_2026m04"
NEW_TAG = "2021m01_2026m06"

COLS = ["date", "yrke4", "alder_gr", "sekt", "variable", "value"]
DTYPE = {c: str for c in COLS}


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=DTYPE)


def without_new_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop any pre-existing rows for the months we are re-appending."""
    return df[~df["date"].isin(NEW_DATES)].copy()


def sort_like_combined(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(["variable", "date", "yrke4", "alder_gr", "sekt"]).reset_index(drop=True)


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"missing raw export: {SRC}")

    rows = parse_multi_tabulate(SRC.read_text(encoding="utf-8"))
    new = pd.DataFrame(rows)
    # parse_multi_tabulate returns keys date, yrke4, alder_gr, sekt, variable, value
    missing = [c for c in COLS if c not in new.columns]
    if missing:
        raise SystemExit(f"parsed export missing columns {missing}; got {sorted(new.columns)}")
    new = new[COLS].astype(str)

    got_dates = sorted(new["date"].unique())
    got_vars = sorted(new["variable"].unique())
    print(f"Parsed {len(new):,} rows | dates={got_dates} | variables={got_vars}")
    if set(got_dates) - NEW_DATES:
        print(f"  WARNING: unexpected dates present: {set(got_dates) - NEW_DATES}")
    for v in KPOS_VARS | NONKPOS_ADD_VARS:
        if v not in set(got_vars):
            print(f"  WARNING: expected variable {v!r} not found in export")

    new_kpos = new[new["variable"].isin(KPOS_VARS)]

    # --- per-variable kpos files -> _2026m06 -------------------------------
    for stem, keep in PER_VAR:
        old_path = OUT / f"{stem}_{OLD_TAG}_parsed.csv"
        new_path = OUT / f"{stem}_{NEW_TAG}_parsed.csv"
        base = without_new_dates(load(old_path))
        add = new_kpos[new_kpos["variable"].isin(keep)]
        combined = pd.concat([base, add], ignore_index=True)
        combined = combined.sort_values(["date", "yrke4", "alder_gr", "sekt", "variable"]).reset_index(drop=True)
        combined.to_csv(new_path, index=False)
        print(f"  {new_path.name}: {len(base):,} + {len(add):,} = {len(combined):,} rows")

    # --- kpos combined -> _2026m06 (mirrors build_combined_kpos.py) --------
    kpos_old = OUT / f"09_occ_agedecade_sektor_kpos_{OLD_TAG}_parsed.csv"
    kpos_new = OUT / f"09_occ_agedecade_sektor_kpos_{NEW_TAG}_parsed.csv"
    kpos_base = without_new_dates(load(kpos_old))
    kpos_combined = sort_like_combined(pd.concat([kpos_base, new_kpos], ignore_index=True))
    kpos_combined.to_csv(kpos_new, index=False)
    print(f"  {kpos_new.name}: {len(kpos_base):,} + {len(new_kpos):,} = {len(kpos_combined):,} rows "
          f"({kpos_combined['date'].nunique()} months, vars={sorted(kpos_combined['variable'].unique())})")

    # --- non-kpos combined -> _2026m06 (add timelonn + overtid_timer only) -
    new_nonkpos = new[new["variable"].isin(NONKPOS_ADD_VARS)]
    nk_old = OUT / f"09_occ_agedecade_sektor_{OLD_TAG}_parsed.csv"
    nk_new = OUT / f"09_occ_agedecade_sektor_{NEW_TAG}_parsed.csv"
    nk_base = load(nk_old)
    # idempotent only for the two variables we add for the new months
    nk_base = nk_base[~(nk_base["date"].isin(NEW_DATES) & nk_base["variable"].isin(NONKPOS_ADD_VARS))].copy()
    nk_combined = sort_like_combined(pd.concat([nk_base, new_nonkpos], ignore_index=True))
    nk_combined.to_csv(nk_new, index=False)
    print(f"  {nk_new.name}: {len(nk_base):,} + {len(new_nonkpos):,} = {len(nk_combined):,} rows "
          f"({nk_combined['date'].nunique()} months, vars={sorted(nk_combined['variable'].unique())})")

    print("\nDone. Next: repoint build_figure_data.py / build_release.py at the _2026m06 files.")


if __name__ == "__main__":
    main()
