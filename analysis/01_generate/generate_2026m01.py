"""
Genererer ETT samlet microdata.no-script for den nye maaneden 2026-01
(v53, som inneholder a-ordningen til og med januar 2026).

Scriptet er delt i tydelig markerte deler. Det limes inn i microdata.no
EN gang og produserer alle aggregeringer vi trenger for 2026-01.

Deler (mapper mot eksisterende scripts):

  Del A: yrke4 x alder_gr (jobbtelling)              -- 01_yrke4_aldersgruppe
  Del B: kontantlonn / stillingspst / timelonn       -- 02_lonn_agemonth
  Del C: yrke4 x alder_gr x sektor                   -- 04_occ_agem_sector
  Del D: ai_q x alder_gr x sektor                    -- 04_quintile_age_sector
  Del E: ai_q x alder_gr x sektor, summarize(lonn)   -- 05_quintile_age_sector_wage
  Del F: overtid_timer + ny_jobb                     -- 06_overtid_nyjobb
  Del G: kontantlonn std                             -- 07_lonn_sd
  Del H: sysselsatt x alder (kvartalspunkt 2026q1)   -- 03_syss_alder
  Del I: utd_gr x alder_gr (alle og sysselsatte)     -- 04_utd_alder
  Del J: nus3 x alder_gr (alle og sysselsatte)       -- 05_utd3_alder

Strategi for line-economy:
  - Del A-G: ett felles jobb-datasett med alle jobbvariabler + person-merge.
    Tabulater A, B, C, F, G kjoeres mot full populasjon.
    Deretter `keep if ai_q > 0` og tabulater D, E.
  - Del H-J: ett felles person-datasett (BEFOLKNING + NUDB + ARBLONN_PERS_SUM_STILLINGSPST).
    Del H tabulerer paa alder (kontinuerlig) over alle bosatte.
    Del I/J tabuleres foerst paa alle bosatte, deretter paa keep if sysselsatt == 1.

ai_q-recoden bygges fra data/ai_exposure/styrk08_eloundou_beta_mapping.csv.
NUDB_BU er capped paa 2024-07-01 (siste tilgjengelige NUDB-vintage).
"""

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAPPING_FILE = ROOT / "data" / "ai_exposure" / "styrk08_eloundou_beta_mapping.csv"
OUTPUT_FILE = ROOT / "microdata-scripts" / "monthly" / "08_alle_2026m01.mdata"

DB_VERSION = 53
YEAR = 2026
MONTH = 1
ARB_DATE = f"{YEAR}-{MONTH:02d}-16"
BEF_DATE = f"{YEAR}-01-01"
NUDB_DATE = "2024-07-01"
BATCH = 20

# ny_jobb-vindu (matcher konvensjonen i 06_overtid_nyjobb_2021_2025.mdata):
# Statusdato er den 16. i maaneden. Vinduet er > forrige statusdato & <= naavarende
# statusdato, dvs. startdato i (forrige_16., naavarende_16.] -- 31 dager.
# Eksempel fra eksisterende script for jan 2021: > 18612 (2020-12-16) & <= 18643 (2021-01-16).
EPOCH = date(1970, 1, 1)


def _days(y: int, m: int, d: int) -> int:
    return (date(y, m, d) - EPOCH).days


prev_year = YEAR if MONTH > 1 else YEAR - 1
prev_month = MONTH - 1 if MONTH > 1 else 12
NY_JOBB_LOW = _days(prev_year, prev_month, 16)        # 2025-12-16
NY_JOBB_HIGH = _days(YEAR, MONTH, 16)                  # 2026-01-16


def build_inlist_lines() -> str:
    by_q: dict[int, list[str]] = defaultdict(list)
    with open(MAPPING_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_q[int(row["quintile"])].append(row["styrk08"])
    out = []
    for q in sorted(by_q):
        codes = sorted(by_q[q])
        for i in range(0, len(codes), BATCH):
            vals = ", ".join(f"'{c}'" for c in codes[i : i + BATCH])
            out.append(f"replace ai_q = {q} if inlist(yrke4, {vals})")
    return "\n".join(out)


ALDER_GR_BLOCK = """generate alder_gr = 0
replace alder_gr = 1 if alder <= 21
replace alder_gr = 2 if alder >= 22 & alder <= 25
replace alder_gr = 3 if alder >= 26 & alder <= 30
replace alder_gr = 4 if alder >= 31 & alder <= 34
replace alder_gr = 5 if alder >= 35 & alder <= 40
replace alder_gr = 6 if alder >= 41 & alder <= 49
replace alder_gr = 7 if alder >= 50 & alder <= 59
replace alder_gr = 8 if alder >= 60 & alder <= 69
replace alder_gr = 9 if alder >= 70"""

SEKTOR_BLOCK = """generate sekt = 3
replace sekt = 1 if sektor == '1110'
replace sekt = 1 if sektor == '1120'
replace sekt = 1 if sektor == '6100'
replace sekt = 2 if sektor == '1510'
replace sekt = 2 if sektor == '1520'
replace sekt = 2 if sektor == '6500'"""


def main() -> None:
    inlist_lines = build_inlist_lines()

    p: list[str] = []
    p.append(f"require no.ssb.fdb:{DB_VERSION} as db")
    p.append("")

    # Felles datasett for merge
    p.append("create-dataset kobling")
    p.append("import db/ARBEIDSFORHOLD_PERSON as personid")
    p.append("")
    p.append("create-dataset pers")
    p.append("import db/BEFOLKNING_FOEDSELS_AAR_MND as fodtaarmd")
    p.append("")

    # ===========================================================
    # JOBB-DATASETT (Del A-G)
    # ===========================================================
    j = f"jobb_y{YEAR}m{MONTH:02d}"
    p.append(f"create-dataset {j}")
    p.append(f"import db/ARBLONN_ARB_YRKE_STYRK08 {ARB_DATE} as yrke")
    p.append(f"import db/ARBLONN_FRTK_SEKTOR_2014 {ARB_DATE} as sektor")
    p.append(f"import db/ARBLONN_LONN_KONTANT_IMP {ARB_DATE} as kontantlonn")
    p.append(f"import db/ARBLONN_ARB_STILLINGSPST {ARB_DATE} as stillingspst")
    p.append(f"import db/ARBLONN_LONN_TIME {ARB_DATE} as timelonn")
    p.append(f"import db/ARBLONN_LONN_OVERTID_TIMER {ARB_DATE} as overtid_timer")
    p.append("replace overtid_timer = 0 if sysmiss(overtid_timer)")
    p.append(f"import db/ARBLONN_ARB_START {ARB_DATE} as startdato")
    p.append("generate yrke4 = substr(yrke, 1, 4)")
    p.append("")
    p.append(SEKTOR_BLOCK)
    p.append("")
    p.append("generate ny_jobb = 0")
    p.append(f"replace ny_jobb = 1 if startdato > {NY_JOBB_LOW} & startdato <= {NY_JOBB_HIGH}")
    p.append("")
    p.append("generate ai_q = 0")
    p.append(inlist_lines)
    p.append("")
    p.append("use kobling")
    p.append(f"merge personid into {j}")
    p.append("use pers")
    p.append(f"merge fodtaarmd into {j} on personid")
    p.append("")
    p.append(f"use {j}")
    p.append("generate birth_yr = int(fodtaarmd / 100)")
    p.append("generate birth_mo = fodtaarmd - birth_yr * 100")
    p.append(f"generate alder = {YEAR} - birth_yr")
    p.append(f"replace alder = alder - 1 if birth_mo > {MONTH}")
    p.append(ALDER_GR_BLOCK)
    p.append("")

    # Del A: yrke4 x alder_gr (jobbtelling)
    p.append("tabulate yrke4 alder_gr, flatten")
    p.append("")

    # Del B: lonnsmaal
    p.append("tabulate yrke4 alder_gr, summarize(kontantlonn) flatten")
    p.append("tabulate yrke4 alder_gr, summarize(stillingspst) flatten")
    p.append("tabulate yrke4 alder_gr, summarize(timelonn) flatten")
    p.append("")

    # Del C: yrke4 x alder_gr per sektor
    p.append("tabulate yrke4 alder_gr if sekt == 1, flatten")
    p.append("tabulate yrke4 alder_gr if sekt == 2, flatten")
    p.append("tabulate yrke4 alder_gr if sekt == 3, flatten")
    p.append("")

    # Del F: overtid_timer + ny_jobb
    p.append("tabulate yrke4 alder_gr, summarize(overtid_timer) flatten")
    p.append("tabulate yrke4 alder_gr, summarize(ny_jobb) flatten")
    p.append("")

    # Del G: kontantlonn std
    p.append("tabulate yrke4 alder_gr, summarize(kontantlonn) std flatten")
    p.append("")

    # Del D + E: ai_q x alder_gr x sekt (filtrer paa ai_q > 0)
    p.append("keep if ai_q > 0")
    p.append("tabulate ai_q alder_gr sekt, flatten")
    p.append("tabulate ai_q alder_gr sekt, summarize(kontantlonn) flatten")
    p.append("")
    p.append(f"delete-dataset {j}")
    p.append("")

    # ===========================================================
    # PERSON-DATASETT (Del H-J)
    # ===========================================================
    person = f"pers_y{YEAR}m{MONTH:02d}"
    p.append(f"create-dataset {person}")
    p.append(f"import db/BEFOLKNING_STATUSKODE {BEF_DATE} as regstatus")
    p.append("keep if regstatus == '1'")
    p.append("import db/BEFOLKNING_FOEDSELS_AAR_MND as fodtaarmd")
    p.append(f"import db/NUDB_BU {NUDB_DATE} as nudb")
    p.append(f"import db/ARBLONN_PERS_SUM_STILLINGSPST {ARB_DATE} as stillingspst")
    p.append(f"generate alder = {YEAR} - int(fodtaarmd / 100)")
    p.append(ALDER_GR_BLOCK)
    p.append("generate sysselsatt = 0")
    p.append("replace sysselsatt = 1 if stillingspst > 0")
    p.append("")
    p.append("generate nus1 = substr(nudb, 1, 1)")
    p.append("generate fag1 = substr(nudb, 2, 1)")
    p.append("destring nus1")
    p.append("destring fag1")
    p.append("generate utd_lev = 0")
    p.append("replace utd_lev = 1 if nus1 == 3")
    p.append("replace utd_lev = 1 if nus1 == 4")
    p.append("replace utd_lev = 2 if nus1 == 5")
    p.append("replace utd_lev = 2 if nus1 == 6")
    p.append("replace utd_lev = 3 if nus1 == 7")
    p.append("replace utd_lev = 3 if nus1 == 8")
    p.append("generate utd_gr = utd_lev * 10 + fag1")
    p.append("replace utd_gr = 0 if utd_lev == 0")
    p.append("generate nus3 = substr(nudb, 1, 3)")
    p.append("destring nus3")
    p.append("")

    # Del H: sysselsatt x alder (kontinuerlig)
    p.append("tabulate sysselsatt alder, flatten")
    p.append("")

    # Del I og J -- alle bosatte
    p.append("tabulate alder_gr utd_gr, flatten")
    p.append("tabulate alder_gr nus3, flatten")
    p.append("")

    # Del I og J -- kun sysselsatte
    p.append("keep if sysselsatt == 1")
    p.append("tabulate alder_gr utd_gr, flatten")
    p.append("tabulate alder_gr nus3, flatten")
    p.append("")
    p.append(f"delete-dataset {person}")

    script = "\n".join(p) + "\n"
    OUTPUT_FILE.write_text(script, encoding="utf-8")
    n_lines = script.count("\n")
    print(f"Wrote {OUTPUT_FILE}")
    print(f"  {n_lines} linjer")
    print(f"  ny_jobb-vindu: startdato > {NY_JOBB_LOW} (forrige statusdato) & <= {NY_JOBB_HIGH} (naavarende statusdato)")


if __name__ == "__main__":
    main()
