"""Genererer 5 mindre microdata.no-scripts for 09-pipelinen.

Bakgrunn: 09_age_decades_sektor_2021_2026 (alle 7 utfall, 62 maaneder)
brukte 7 timer og kom bare gjennom 2022-04 + delvis 2022-05 (6 av 7
tabuleringer). microdata.no har minneproblemer naar hver maaneds
jobb-datasett blir for stort. Loesningen er aa dele per variabel slik at
hver maaneds-blokk imports kun det den trenger.

Splittene:

  09a: count                   (yrke, sektor)
  09b: kontantlonn mean + SD   (yrke, sektor, kontantlonn)
  09c: stillingspst mean       (yrke, sektor, stillingspst)
  09d: timelonn mean           (yrke, sektor, timelonn)
  09e: overtid_timer mean      (yrke, sektor, overtid_timer)
  09f: ny_jobb mean            (yrke, sektor, startdato)

Vindu: 2022-05 til 2026-02 (46 maaneder). 2022-05 inkluderes for aa fylle
den manglende kontantlonn-std-tabuleringen + overskrive de 6 partielle
2022-05-tabellene fra det eksisterende outputet. 2021-01 til 2022-04 er
fullstendig dekket av det gamle scriptet og henter vi ikke paa nytt.

ny_jobb-strategi (09f): bruker `summarize(ny_jobb)` for aa unngaa
celle-suppression som ville ramme tynne celler under en
`keep if ny_jobb == 1` + count-tilnaerming. Tellingen av nye jobber
rekonstrueres post-hoc som mean_ny_jobb * total_count per celle.
ny_jobb er splittet ut fra count fordi to tabuleringer per maaned krever
mer minne enn en, og 09a-skriptet skal vaere saa magert som mulig
(bare yrke + sektor importert).
"""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "microdata-scripts" / "monthly"

DB_VERSION = 54
START_YEAR, START_MONTH = 2022, 5
END_YEAR, END_MONTH = 2026, 2
EPOCH = date(1970, 1, 1)

ALDER_GR_BLOCK = """generate alder_gr = 0
replace alder_gr = 1 if alder >= 21 & alder <= 30
replace alder_gr = 2 if alder >= 31 & alder <= 40
replace alder_gr = 3 if alder >= 41 & alder <= 50
replace alder_gr = 4 if alder >= 51 & alder <= 60
replace alder_gr = 5 if alder >= 61"""

SEKTOR_BLOCK = """generate sekt = 2
replace sekt = 1 if sektor == '1110'
replace sekt = 1 if sektor == '1120'
replace sekt = 1 if sektor == '6100'
replace sekt = 1 if sektor == '1510'
replace sekt = 1 if sektor == '1520'
replace sekt = 1 if sektor == '6500'"""


def _days(y: int, m: int, d: int) -> int:
    return (date(y, m, d) - EPOCH).days


def _months(start_y, start_m, end_y, end_m):
    y, m = start_y, start_m
    while (y, m) <= (end_y, end_m):
        yield y, m
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1


# Hvert "spec" sier:
#   imports:  liste av (sti, alias) som importeres etter yrke og sektor
#   gen:      ekstra generate-linjer (paa jobb-datasettet, foer merge)
#   tabs:     tabulering-linjer som kjoeres etter alder_gr-blokken,
#             i rekkefoelge. For 09a ligger keep+tabulate sist i listen.
SPECS = {
    "09a_count": {
        "imports": [],
        "needs_ny_jobb": False,
        "tabs": [
            "tabulate yrke4 alder_gr sekt, flatten",
        ],
    },
    "09b_kontantlonn": {
        "imports": [
            ("ARBLONN_LONN_KONTANT_IMP", "kontantlonn"),
        ],
        "needs_ny_jobb": False,
        "tabs": [
            "tabulate yrke4 alder_gr sekt, summarize(kontantlonn) flatten",
            "tabulate yrke4 alder_gr sekt, summarize(kontantlonn) std flatten",
        ],
    },
    "09c_stillingspst": {
        "imports": [
            ("ARBLONN_ARB_STILLINGSPST", "stillingspst"),
        ],
        "needs_ny_jobb": False,
        "tabs": [
            "tabulate yrke4 alder_gr sekt, summarize(stillingspst) flatten",
        ],
    },
    "09d_timelonn": {
        "imports": [
            ("ARBLONN_LONN_TIME", "timelonn"),
        ],
        "needs_ny_jobb": False,
        "tabs": [
            "tabulate yrke4 alder_gr sekt, summarize(timelonn) flatten",
        ],
    },
    "09e_overtid_timer": {
        "imports": [
            ("ARBLONN_LONN_OVERTID_TIMER", "overtid_timer"),
        ],
        "needs_ny_jobb": False,
        "tabs": [
            "tabulate yrke4 alder_gr sekt, summarize(overtid_timer) flatten",
        ],
        "fix_sysmiss": "replace overtid_timer = 0 if sysmiss(overtid_timer)",
    },
    "09f_nyjobb": {
        "imports": [
            ("ARBLONN_ARB_START", "startdato"),
        ],
        "needs_ny_jobb": True,
        "tabs": [
            "tabulate yrke4 alder_gr sekt, summarize(ny_jobb) flatten",
        ],
    },
    # Hourly wage derived from cash earnings and agreed employment %.
    # Valid for ALL workers (hourly + monthly-salary), unlike LONN_TIME
    # which is only defined for workers on hourly contracts.
    # hourly_wage = kontantlonn / (stillingspst/100) / 162.5
    # 162.5 = 37.5 t/uke x 52/12 = norsk fulltid t/maaned.
    "09g_hourly_wage": {
        "imports": [
            ("ARBLONN_LONN_KONTANT_IMP", "kontantlonn"),
            ("ARBLONN_ARB_STILLINGSPST", "stillingspst"),
        ],
        "needs_ny_jobb": False,
        "fix_sysmiss": [
            "drop if sysmiss(kontantlonn)",
            "drop if sysmiss(stillingspst)",
            "drop if stillingspst <= 0",
            "generate hourly_wage = kontantlonn / (stillingspst / 100) / 162.5",
        ],
        "tabs": [
            "tabulate yrke4 alder_gr sekt, summarize(hourly_wage) flatten",
        ],
    },
}


def month_block(year: int, month: int, spec: dict) -> list[str]:
    arb_date = f"{year}-{month:02d}-16"
    j = f"jobb_y{year}m{month:02d}"

    lines = [
        f"create-dataset {j}",
        f"import db/ARBLONN_ARB_YRKE_STYRK08 {arb_date} as yrke",
        f"import db/ARBLONN_FRTK_SEKTOR_2014 {arb_date} as sektor",
    ]
    for table, alias in spec["imports"]:
        lines.append(f"import db/{table} {arb_date} as {alias}")
    fix = spec.get("fix_sysmiss")
    if fix:
        if isinstance(fix, list):
            lines.extend(fix)
        else:
            lines.append(fix)
    lines.append("generate yrke4 = substr(yrke, 1, 4)")
    lines.append("")
    lines.append(SEKTOR_BLOCK)
    lines.append("")
    if spec["needs_ny_jobb"]:
        prev_y = year if month > 1 else year - 1
        prev_m = month - 1 if month > 1 else 12
        nj_low = _days(prev_y, prev_m, 16)
        nj_high = _days(year, month, 16)
        lines.append("generate ny_jobb = 0")
        lines.append(
            f"replace ny_jobb = 1 if startdato > {nj_low} "
            f"& startdato <= {nj_high}"
        )
        lines.append("")
    lines.extend([
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
    ])
    lines.extend(spec["tabs"])
    lines.append("")
    lines.append(f"delete-dataset {j}")
    lines.append("")
    return lines


def build_script(name: str, spec: dict) -> Path:
    p: list[str] = []
    p.append(f"require no.ssb.fdb:{DB_VERSION} as db")
    p.append("")
    p.append("create-dataset kobling")
    p.append("import db/ARBEIDSFORHOLD_PERSON as personid")
    p.append("")
    p.append("create-dataset pers")
    p.append("import db/BEFOLKNING_FOEDSELS_AAR_MND as fodtaarmd")
    p.append("")

    for y, m in _months(START_YEAR, START_MONTH, END_YEAR, END_MONTH):
        p.extend(month_block(y, m, spec))

    out_path = OUT_DIR / f"{name}_2022m05_2026m02.mdata"
    script = "\n".join(p) + "\n"
    out_path.write_text(script, encoding="utf-8")
    return out_path


def main() -> None:
    print(f"Genererer {len(SPECS)} scripts som dekker "
          f"{START_YEAR}-{START_MONTH:02d} til {END_YEAR}-{END_MONTH:02d}\n")
    for name, spec in SPECS.items():
        out_path = build_script(name, spec)
        n_lines = out_path.read_text().count("\n")
        n_kb = out_path.stat().st_size / 1024
        print(f"  {out_path.name}: {n_lines} lines, {n_kb:.1f} KB")


if __name__ == "__main__":
    main()
