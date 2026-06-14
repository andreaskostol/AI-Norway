"""Genererer 4 microdata.no-scripts for konsistente tidsserier paa
arbeidsforhold med utbetalt kontantlonn (kontantlonn > 0), 2021m01-2026m02.

Forskjell fra generate_09_split.py:
- Utvidet vindu: 2021-01 til 2026-02 (62 maaneder, ikke 46).
- Eksplisitt populasjonsrestriksjon: vi importerer kontantlonn i alle
  scriptene og dropper rader hvor kontantlonn er missing eller <= 0.
  Det restrikterer arbeidsforhold til ARB_SYSS 1a + 1b med faktisk
  utbetalt loenn, og utelater 2a (NAV-ytelser), 2b (permittert <90d),
  2c (permisjon <90d), 3a-3b (jobb t-1 og t+1, ikke t).
- 4 utfall: count, kontantlonn, stillingspst, ny_jobb. Alle har naa
  identisk populasjon og identisk cellestruktur (yrke4 x alder_gr x sekt),
  saa figurene kan sammenligne nivaaer paa tvers av seriene uten
  populasjonsforskyvning.

09d (timelonn), 09e (overtid), 09g (hourly_wage) er ikke laget i denne
kpos-varianten -- legg til etter behov.

Output:
  09a_count_kpos_2021m01_2026m02.mdata
  09b_kontantlonn_kpos_2021m01_2026m02.mdata
  09c_stillingspst_kpos_2021m01_2026m02.mdata
  09f_nyjobb_kpos_2021m01_2026m02.mdata
"""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "microdata-scripts" / "monthly"

DB_VERSION = 54
START_YEAR, START_MONTH = 2021, 1
END_YEAR, END_MONTH = 2026, 2
EPOCH = date(1970, 1, 1)


def _days(y: int, m: int, d: int) -> int:
    return (date(y, m, d) - EPOCH).days

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


def _months(start_y, start_m, end_y, end_m):
    y, m = start_y, start_m
    while (y, m) <= (end_y, end_m):
        yield y, m
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1


# Felles: importer kontantlonn og dropp rader uten utbetalt loenn.
# extra_imports = ekstra variabler trengt for summarize-tabulasjonen.
# needs_ny_jobb = True genererer ny_jobb-indikator basert paa startdato.
SPECS = {
    "09a_count_kpos": {
        "extra_imports": [],
        "needs_ny_jobb": False,
        "tabs": [
            "tabulate yrke4 alder_gr sekt, flatten",
        ],
    },
    "09b_kontantlonn_kpos": {
        "extra_imports": [],
        "needs_ny_jobb": False,
        "tabs": [
            "tabulate yrke4 alder_gr sekt, summarize(kontantlonn) flatten",
            "tabulate yrke4 alder_gr sekt, summarize(kontantlonn) std flatten",
        ],
    },
    "09c_stillingspst_kpos": {
        "extra_imports": [
            ("ARBLONN_ARB_STILLINGSPST", "stillingspst"),
        ],
        "needs_ny_jobb": False,
        "tabs": [
            "tabulate yrke4 alder_gr sekt, summarize(stillingspst) flatten",
        ],
    },
    "09f_nyjobb_kpos": {
        "extra_imports": [
            ("ARBLONN_ARB_START", "startdato"),
        ],
        "needs_ny_jobb": True,
        "tabs": [
            "tabulate yrke4 alder_gr sekt, summarize(ny_jobb) flatten",
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
        f"import db/ARBLONN_LONN_KONTANT_IMP {arb_date} as kontantlonn",
    ]
    for table, alias in spec["extra_imports"]:
        lines.append(f"import db/{table} {arb_date} as {alias}")
    # Populasjonsrestriksjon: bare arbeidsforhold med utbetalt loenn.
    lines.append("drop if sysmiss(kontantlonn)")
    lines.append("drop if kontantlonn <= 0")
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

    out_path = OUT_DIR / f"{name}_2021m01_2026m02.mdata"
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
