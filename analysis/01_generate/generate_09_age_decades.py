"""Genererer microdata.no-script som henter alle utfallsmaal pr.

yrke4 x aldersdekade x sektor (offentlig vs privat), maanedlig
fra 2021-01 til 2026-02.

Forskjell fra 08_alle:
- Aldersgrupper aggregert til dekader (21-30, 31-40, 41-50, 51-60, 61+)
  for aa redusere celle-suppression for unge ansatte.
- Sektor kollapset til to: 1 = offentlig (stat+kommune), 2 = privat.
- 3-veis tabulering (yrke4 x alder_gr x sekt) i stedet for separate
  sektor-filtre. Mister bare 'totalt'; det kan rekonstrueres post-hoc
  fra count men ikke for gjennomsnitt/SD (derfor inkludert per sektor).
- Loop over alle 62 maaneder i ett script.

Utfall (alle med 3-veis xtab yrke4 x alder_gr x sekt):
  count, mean kontantlonn, mean stillingspst, mean timelonn,
  mean overtid_timer, mean ny_jobb, SD kontantlonn.

ny_jobb-vinduet: startdato i (forrige 16., naavarende 16.] -- 31 dager.
"""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_FILE = (
    ROOT / "microdata-scripts" / "monthly"
    / "09_age_decades_sektor_2021_2026.mdata"
)

DB_VERSION = 54
START_YEAR, START_MONTH = 2021, 1
END_YEAR, END_MONTH = 2026, 2
EPOCH = date(1970, 1, 1)

# Aldersdekader: 21-30, 31-40, 41-50, 51-60, 61+
# (alder under 21 faller i alder_gr = 0 og inkluderes ikke i tabuleringer
#  som krysser alder_gr siden vi ikke kaster ut rader, men den lavest
#  meningsfulle gruppen er 1 = 21-30.)
ALDER_GR_BLOCK = """generate alder_gr = 0
replace alder_gr = 1 if alder >= 21 & alder <= 30
replace alder_gr = 2 if alder >= 31 & alder <= 40
replace alder_gr = 3 if alder >= 41 & alder <= 50
replace alder_gr = 4 if alder >= 51 & alder <= 60
replace alder_gr = 5 if alder >= 61"""

# Sektor: 1 = offentlig (stat + kommune), 2 = privat (alt annet).
# Default = 2 (privat). De seks SSB-kodene for stat (1110, 1120, 6100) og
# kommune (1510, 1520, 6500) settes til 1.
SEKTOR_BLOCK = """generate sekt = 2
replace sekt = 1 if sektor == '1110'
replace sekt = 1 if sektor == '1120'
replace sekt = 1 if sektor == '6100'
replace sekt = 1 if sektor == '1510'
replace sekt = 1 if sektor == '1520'
replace sekt = 1 if sektor == '6500'"""


def _days(y: int, m: int, d: int) -> int:
    return (date(y, m, d) - EPOCH).days


def _months(start_y: int, start_m: int, end_y: int, end_m: int):
    """Generer (year, month) inklusiv start..end."""
    y, m = start_y, start_m
    while (y, m) <= (end_y, end_m):
        yield y, m
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1


def month_block(year: int, month: int) -> list[str]:
    arb_date = f"{year}-{month:02d}-16"
    prev_y = year if month > 1 else year - 1
    prev_m = month - 1 if month > 1 else 12
    nj_low = _days(prev_y, prev_m, 16)
    nj_high = _days(year, month, 16)
    j = f"jobb_y{year}m{month:02d}"

    lines = [
        f"create-dataset {j}",
        f"import db/ARBLONN_ARB_YRKE_STYRK08 {arb_date} as yrke",
        f"import db/ARBLONN_FRTK_SEKTOR_2014 {arb_date} as sektor",
        f"import db/ARBLONN_LONN_KONTANT_IMP {arb_date} as kontantlonn",
        f"import db/ARBLONN_ARB_STILLINGSPST {arb_date} as stillingspst",
        f"import db/ARBLONN_LONN_TIME {arb_date} as timelonn",
        f"import db/ARBLONN_LONN_OVERTID_TIMER {arb_date} as overtid_timer",
        "replace overtid_timer = 0 if sysmiss(overtid_timer)",
        f"import db/ARBLONN_ARB_START {arb_date} as startdato",
        "generate yrke4 = substr(yrke, 1, 4)",
        "",
        SEKTOR_BLOCK,
        "",
        "generate ny_jobb = 0",
        f"replace ny_jobb = 1 if startdato > {nj_low} & startdato <= {nj_high}",
        "",
        "use kobling",
        f"merge personid into {j}",
        "use pers",
        f"merge fodtaarmd into {j} on personid",
        "",
        f"use {j}",
        "generate birth_yr = int(fodtaarmd / 100)",
        "generate birth_mo = fodtaarmd - birth_yr * 100",
        f"generate alder = {year} - birth_yr",
        f"replace alder = alder - 1 if birth_mo > {month}",
        ALDER_GR_BLOCK,
        "",
        "tabulate yrke4 alder_gr sekt, flatten",
        "tabulate yrke4 alder_gr sekt, summarize(kontantlonn) flatten",
        "tabulate yrke4 alder_gr sekt, summarize(stillingspst) flatten",
        "tabulate yrke4 alder_gr sekt, summarize(timelonn) flatten",
        "tabulate yrke4 alder_gr sekt, summarize(overtid_timer) flatten",
        "tabulate yrke4 alder_gr sekt, summarize(ny_jobb) flatten",
        "tabulate yrke4 alder_gr sekt, summarize(kontantlonn) std flatten",
        "",
        f"delete-dataset {j}",
        "",
    ]
    return lines


def main() -> None:
    p: list[str] = []
    p.append(f"require no.ssb.fdb:{DB_VERSION} as db")
    p.append("")

    # Felles datasett for merge -- importeres en gang og brukes paa nytt
    # for hver maaned (rendyrket pers / kobling forblir gyldige saa
    # lenge personid og fodtaarmd er tidsuavhengige).
    p.append("create-dataset kobling")
    p.append("import db/ARBEIDSFORHOLD_PERSON as personid")
    p.append("")
    p.append("create-dataset pers")
    p.append("import db/BEFOLKNING_FOEDSELS_AAR_MND as fodtaarmd")
    p.append("")

    n_months = 0
    for y, m in _months(START_YEAR, START_MONTH, END_YEAR, END_MONTH):
        p.extend(month_block(y, m))
        n_months += 1

    script = "\n".join(p) + "\n"
    OUTPUT_FILE.write_text(script, encoding="utf-8")
    n_lines = script.count("\n")
    print(f"Wrote {OUTPUT_FILE}")
    print(f"  {n_months} months ({START_YEAR}-{START_MONTH:02d} "
          f"..  {END_YEAR}-{END_MONTH:02d})")
    print(f"  {n_lines} lines, "
          f"{OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
