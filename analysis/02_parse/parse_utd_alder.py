"""
Parse 04_utd_alder*_raw.csv (alder_gr x utd_gr, to tabulate per maaned).

Hver maaned har to tabulate-blokker:
  1. Alle bosatte (alder_gr x utd_gr, count)
  2. Kun sysselsatte (etter keep if sysselsatt == 1)

Output: long-format CSV med kolonner date, alder_gr, utd_gr, pop, syss.

Usage:
    python parse_utd_alder.py input_raw.csv output_parsed.csv
"""

import csv
import re
import sys
from pathlib import Path


def parse(text: str) -> list[dict]:
    lines = text.split('\n')
    current_date = None
    headers = None
    in_table = False
    is_syss_table = False  # toggles between pop and syss
    # Collect per (date, alder_gr, utd_gr) -> {pop, syss}
    data = {}

    for line in lines:
        line = line.strip()
        if not line:
            in_table = False
            continue

        m = re.search(r'ARBLONN_PERS_SUM_STILLINGSPST\s+(\d{4}-\d{2}-\d{2})', line)
        if m:
            current_date = m.group(1)
            is_syss_table = False
            continue

        if line.startswith('keep if sysselsatt'):
            is_syss_table = True
            in_table = False
            headers = None
            continue

        if line.startswith('tabulate'):
            in_table = False
            headers = None
            continue

        if any(line.startswith(c) for c in (
            'require', 'create', 'import', 'generate', 'use', 'merge',
            'replace', 'drop', 'keep', 'define', 'assign', 'delete',
            'Opprettet', 'Importerte', 'Genererte', 'Byttet', 'Flettet',
            'Datasettet', 'Tilegnet', 'Et tomt', 'Konverterte', 'destring',
        )):
            continue

        cells = [c.strip() for c in line.split(';')]
        while cells and cells[-1] == '':
            cells.pop()
        if not cells:
            continue

        if not in_table and cells[0] == 'alder_gr':
            headers = cells
            in_table = True
            continue

        if not in_table or headers is None:
            continue

        if cells[0].lower() == 'total':
            continue

        alder_gr = cells[0]
        field = 'syss' if is_syss_table else 'pop'
        for i, h in enumerate(headers[1:], start=1):
            if h == 'Total':
                continue
            val = cells[i] if i < len(cells) else ''
            val = val.replace(' ', '').replace('\xa0', '')
            if val == '-' or val == '':
                continue
            key = (current_date, alder_gr, h)
            if key not in data:
                data[key] = {'pop': '', 'syss': ''}
            data[key][field] = val

    rows = []
    for (date, ag, ug), vals in sorted(data.items()):
        rows.append({
            'date': date,
            'alder_gr': ag,
            'utd_gr': ug,
            'pop': vals['pop'],
            'syss': vals['syss'],
        })
    return rows


def main():
    if len(sys.argv) < 3:
        print("Usage: python parse_utd_alder.py input.csv output.csv")
        sys.exit(1)

    text = Path(sys.argv[1]).read_text(encoding='utf-8')
    rows = parse(text)

    with open(sys.argv[2], 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['date', 'alder_gr', 'utd_gr', 'pop', 'syss'])
        w.writeheader()
        w.writerows(rows)

    dates = sorted(set(r['date'] for r in rows))
    utd_grs = sorted(set(r['utd_gr'] for r in rows))
    print(f"Saved {len(rows)} rows to {sys.argv[2]}")
    print(f"  Dates: {dates[0]} to {dates[-1]} ({len(dates)} months)")
    print(f"  utd_gr values: {utd_grs}")
    print(f"  alder_gr values: {sorted(set(r['alder_gr'] for r in rows))}")
    suppressed = sum(1 for r in rows if r['pop'] == '' or r['syss'] == '')
    print(f"  Cells with suppression: {suppressed} ({100*suppressed/len(rows):.1f}%)")


if __name__ == '__main__':
    main()
