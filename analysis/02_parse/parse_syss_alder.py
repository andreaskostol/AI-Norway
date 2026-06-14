"""
Parse 03_syss_alder_*_raw.csv (sysselsatt x alder, ett tabulate per kvartal).

Output: long-format CSV med kolonner date, alder, sysselsatt, n.
Dato hentes fra ARBLONN_PERS_SUM_STILLINGSPST-import (statusdato 16. i mnd).

Usage:
    python parse_syss_alder.py input_raw.csv output_parsed.csv
"""

import csv
import re
import sys
from pathlib import Path


def parse(text: str) -> list[dict]:
    lines = text.split('\n')
    rows = []
    current_date = None
    headers = None
    in_table = False

    for line in lines:
        line = line.strip()
        if not line:
            in_table = False
            continue

        m = re.search(r'ARBLONN_PERS_SUM_STILLINGSPST\s+(\d{4}-\d{2}-\d{2})', line)
        if m:
            current_date = m.group(1)
            continue

        if line.startswith('tabulate'):
            in_table = False
            headers = None
            continue

        if any(line.startswith(c) for c in (
            'require', 'create', 'import', 'generate', 'use', 'merge',
            'replace', 'drop', 'keep', 'define', 'assign', 'delete',
            'Opprettet', 'Importerte', 'Genererte', 'Byttet', 'Flettet',
            'Datasettet', 'Tilegnet', 'Et tomt', 'Konverterte',
        )):
            continue

        cells = [c.strip() for c in line.split(';')]
        while cells and cells[-1] == '':
            cells.pop()
        if not cells:
            continue

        if not in_table and cells[0] == 'sysselsatt':
            headers = cells
            in_table = True
            continue

        if not in_table or headers is None:
            continue

        if cells[0].lower() == 'total':
            continue

        sysselsatt = cells[0]
        for i, h in enumerate(headers[1:], start=1):
            if h == 'Total':
                continue
            val = cells[i] if i < len(cells) else ''
            val = val.replace(' ', '').replace('\xa0', '')
            if val == '-' or val == '':
                continue
            rows.append({
                'date': current_date,
                'alder': h,
                'sysselsatt': sysselsatt,
                'n': val,
            })

    return rows


def main():
    if len(sys.argv) < 3:
        print("Usage: python parse_syss_alder.py input.csv output.csv")
        sys.exit(1)

    text = Path(sys.argv[1]).read_text(encoding='utf-8')
    rows = parse(text)

    with open(sys.argv[2], 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['date', 'alder', 'sysselsatt', 'n'])
        w.writeheader()
        w.writerows(rows)

    dates = sorted(set(r['date'] for r in rows))
    print(f"Saved {len(rows)} rows to {sys.argv[2]}")
    print(f"  Dates: {dates[0]} to {dates[-1]} ({len(dates)} kvartaler)")


if __name__ == '__main__':
    main()
