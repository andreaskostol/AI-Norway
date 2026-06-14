"""
Generate 03_quintile_age_sector_2021_2025.mdata using inlist() batching
to avoid disclosure control issues with rare occupation codes.

Also regenerates the library file from the authoritative mapping CSV.
"""

import csv
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MAPPING_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv'
LIBRARY_FILE = BASE_DIR / 'microdata-scripts' / 'library' / '_ai_exposure_recode.mdata'
OUTPUT_FILE = BASE_DIR / 'microdata-scripts' / 'monthly' / '04_quintile_age_sector_2021_2025.mdata'

BATCH_SIZE = 20  # codes per inlist() call


def build_inlist_lines() -> str:
    """Build batched inlist() replace lines from the mapping CSV."""
    codes_by_q: dict[int, list[str]] = defaultdict(list)
    with open(MAPPING_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            q = int(row['quintile'])
            codes_by_q[q].append(row['styrk08'])

    lines = []
    for q in sorted(codes_by_q):
        codes = sorted(codes_by_q[q])
        for i in range(0, len(codes), BATCH_SIZE):
            batch = codes[i:i + BATCH_SIZE]
            vals = ', '.join(f"'{c}'" for c in batch)
            lines.append(f"replace ai_q = {q} if inlist(yrke4, {vals})")

    return '\n'.join(lines)


def generate_month_block(year: int, month: int, inlist_lines: str) -> str:
    """Generate one monthly block."""
    ym = f"y{year}m{month:02d}"
    date = f"{year}-{month:02d}-16"

    lines = []
    lines.append(f"create-dataset {ym}")
    lines.append(f"import db/ARBLONN_ARB_YRKE_STYRK08 {date} as yrke")
    lines.append(f"import db/ARBLONN_FRTK_SEKTOR_2014 {date} as sektor")
    lines.append("generate yrke4 = substr(yrke, 1, 4)")
    lines.append("")
    lines.append("generate sekt = 3")
    lines.append("replace sekt = 1 if sektor == '1110'")
    lines.append("replace sekt = 1 if sektor == '1120'")
    lines.append("replace sekt = 1 if sektor == '6100'")
    lines.append("replace sekt = 2 if sektor == '1510'")
    lines.append("replace sekt = 2 if sektor == '1520'")
    lines.append("replace sekt = 2 if sektor == '6500'")
    lines.append("")
    lines.append("generate ai_q = 0")
    lines.append(inlist_lines)
    lines.append("drop if ai_q == 0")
    lines.append("")
    lines.append("use kobling")
    lines.append(f"merge personid into {ym}")
    lines.append("use pers")
    lines.append(f"merge fodtaarmd into {ym} on personid")
    lines.append("")
    lines.append(f"use {ym}")
    lines.append("generate birth_yr = int(fodtaarmd / 100)")
    lines.append("generate birth_mo = fodtaarmd - birth_yr * 100")
    lines.append(f"generate alder = {year} - birth_yr")
    lines.append(f"replace alder = alder - 1 if birth_mo > {month}")
    lines.append("generate alder_gr = 0")
    lines.append("replace alder_gr = 1 if alder <= 21")
    lines.append("replace alder_gr = 2 if alder >= 22 & alder <= 25")
    lines.append("replace alder_gr = 3 if alder >= 26 & alder <= 30")
    lines.append("replace alder_gr = 4 if alder >= 31 & alder <= 34")
    lines.append("replace alder_gr = 5 if alder >= 35 & alder <= 40")
    lines.append("replace alder_gr = 6 if alder >= 41 & alder <= 49")
    lines.append("replace alder_gr = 7 if alder >= 50 & alder <= 59")
    lines.append("replace alder_gr = 8 if alder >= 60 & alder <= 69")
    lines.append("replace alder_gr = 9 if alder >= 70")
    lines.append("tabulate ai_q alder_gr sekt, flatten")
    lines.append(f"delete-dataset {ym}")

    return '\n'.join(lines)


def main():
    inlist_lines = build_inlist_lines()

    # Also update the library file
    LIBRARY_FILE.write_text(inlist_lines + '\n', encoding='utf-8')
    print(f"Updated library: {LIBRARY_FILE}")

    parts = []
    parts.append("require no.ssb.fdb:52 as db")
    parts.append("")
    parts.append("create-dataset kobling")
    parts.append("import db/ARBEIDSFORHOLD_PERSON as personid")
    parts.append("")
    parts.append("create-dataset pers")
    parts.append("import db/BEFOLKNING_FOEDSELS_AAR_MND as fodtaarmd")

    for year in range(2021, 2026):
        for month in range(1, 13):
            parts.append("")
            parts.append(generate_month_block(year, month, inlist_lines))

    script = '\n'.join(parts) + '\n'
    OUTPUT_FILE.write_text(script, encoding='utf-8')

    line_count = script.count('\n')
    print(f"Generated {OUTPUT_FILE}")
    print(f"  {line_count} lines")


if __name__ == '__main__':
    main()
