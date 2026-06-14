"""
Genererer microdata-scripts for utdanning (3-siffer NUS) x aldersgruppe x maaned.

Produserer ett script per 2-aarsperiode:
  05_utd3_alder_2021_2022.mdata, 05_utd3_alder_2023_2024.mdata, etc.

Hver maaned: to tabulate (alle bosatte + kun sysselsatte).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "microdata-scripts" / "monthly"


def block(year: int, month: int) -> str:
    nudb_year = min(year, 2024)
    nudb_date = f"{nudb_year}-07-01"
    befolk_date = f"{year}-01-01"
    arblonn_date = f"{year}-{month:02d}-16"
    name = f"m{year}{month:02d}"
    return f"""
create-dataset {name}
import db/BEFOLKNING_STATUSKODE {befolk_date} as regstatus
keep if regstatus == '1'
import db/BEFOLKNING_FOEDSELS_AAR_MND as fodtaarmd
import db/NUDB_BU {nudb_date} as nudb
import db/ARBLONN_PERS_SUM_STILLINGSPST {arblonn_date} as stillingspst
generate alder = {year} - int(fodtaarmd / 100)
generate alder_gr = 0
replace alder_gr = 1 if alder <= 21
replace alder_gr = 2 if alder >= 22 & alder <= 25
replace alder_gr = 3 if alder >= 26 & alder <= 30
replace alder_gr = 4 if alder >= 31 & alder <= 34
replace alder_gr = 5 if alder >= 35 & alder <= 40
replace alder_gr = 6 if alder >= 41 & alder <= 49
replace alder_gr = 7 if alder >= 50 & alder <= 59
replace alder_gr = 8 if alder >= 60 & alder <= 69
replace alder_gr = 9 if alder >= 70
generate nus3 = substr(nudb, 1, 3)
destring nus3
tabulate alder_gr nus3, flatten
keep if stillingspst > 0
tabulate alder_gr nus3, flatten
delete-dataset {name}
"""


def generate(start_year: int, end_year: int):
    parts = ["require no.ssb.fdb:52 as db"]
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            parts.append(block(year, month))
    fname = f"05_utd3_alder_{start_year}_{end_year}.mdata"
    out = OUTDIR / fname
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    n_months = (end_year - start_year + 1) * 12
    n_lines = sum(1 for _ in out.read_text(encoding="utf-8").splitlines())
    print(f"Wrote {out.name}: {n_lines} lines, {n_months} months")


if __name__ == "__main__":
    generate(2021, 2022)
    generate(2023, 2024)
    generate(2025, 2025)
