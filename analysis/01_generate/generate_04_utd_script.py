"""
Genererer microdata-scripts/monthly/04_utd_alder_2020_2025.mdata.

For hver maaned 2020-01 til 2025-12:
  - BEFOLKNING_STATUSKODE pr 1. jan i aaret
  - NUDB_BU pr 1. juli samme aar (capped paa 2024-07-01 for senere maaneder)
  - ARBLONN_PERS_SUM_STILLINGSPST pr maanedens 16.

Tabulerer alder_gr x utd_gr to ganger: alle bosatte og kun sysselsatte.

utd_gr = 0 (lav, NUS<3 + uoppgitt) +
         10..19 (VGS, NUS 3-4, fagfelt 0-9) +
         20..29 (bachelor, NUS 5-6, fagfelt 0-9) +
         30..39 (master+, NUS 7-8, fagfelt 0-9)
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "microdata-scripts" / "monthly" / "04_utd_alder_2020_2025.mdata"

NUDB_LATEST = "2024-07-01"


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
generate nus1 = substr(nudb, 1, 1)
generate fag1 = substr(nudb, 2, 1)
destring nus1
destring fag1
generate utd_lev = 0
replace utd_lev = 1 if nus1 == 3
replace utd_lev = 1 if nus1 == 4
replace utd_lev = 2 if nus1 == 5
replace utd_lev = 2 if nus1 == 6
replace utd_lev = 3 if nus1 == 7
replace utd_lev = 3 if nus1 == 8
generate utd_gr = utd_lev * 10 + fag1
replace utd_gr = 0 if utd_lev == 0
generate sysselsatt = 0
replace sysselsatt = 1 if stillingspst > 0
tabulate alder_gr utd_gr, flatten
keep if sysselsatt == 1
tabulate alder_gr utd_gr, flatten
delete-dataset {name}
"""


def main():
    parts = ["require no.ssb.fdb:52 as db"]
    for year in range(2020, 2026):
        for month in range(1, 13):
            parts.append(block(year, month))
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"  {sum(1 for _ in OUT.read_text(encoding='utf-8').splitlines())} lines, 72 months")


if __name__ == "__main__":
    main()
