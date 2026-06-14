"""
Parse microdata.no bulk export output into structured CSV files.

Handles two export formats:
1. Pipe-separated: | col1 | col2 | (from "Kopier til utklippstavlen" with text format)
2. Semicolon-separated: col1; val1; val2 (from "Kopier til utklippstavlen" with CSV format)

Detects tabulate commands to identify month/date context.
Handles cell suppression (marked as '-' or cells < 5 not shown).

Usage:
    python parse_microdata_output.py input_file output.csv
"""

import csv
import re
import sys
from pathlib import Path


def detect_separator(text: str) -> str:
    """Detect whether the file uses pipe or semicolon separation."""
    for line in text.split('\n'):
        line = line.strip()
        if line and not line.startswith(('require', 'create', 'import', 'generate',
                                         'use', 'merge', 'replace', 'drop', 'keep',
                                         'define', 'assign', 'delete', 'tabulate')):
            if ';' in line and '|' not in line:
                return ';'
            if '|' in line:
                return '|'
    return ';'


def parse_bulk_export(text: str) -> list[dict]:
    """Parse a microdata.no bulk export file containing multiple twoway tables.

    Returns list of dicts with keys depending on table structure.
    For twoway yrke4 × alder_gr: {date, yrke4, alder_gr_0, alder_gr_1, ..., Total}
    For oneway with if: {date, yrke4, count, alder_gr_filter}
    """
    sep = detect_separator(text)
    lines = text.split('\n')
    all_rows = []
    current_date = None
    current_tabulate = None
    in_table = False
    headers = None

    for line in lines:
        line = line.strip()

        # Detect import command to extract date
        date_match = re.search(r'ARBLONN_ARB_YRKE_STYRK08\s+(\d{4}-\d{2}-\d{2})', line)
        if date_match:
            current_date = date_match.group(1)
            continue

        # Detect tabulate command
        if line.startswith('tabulate'):
            current_tabulate = line
            in_table = False
            headers = None
            # Check for if-filter on age
            age_match = re.search(r'if\s+alder(?:_gr)?\s*==\s*(\d+)', line)
            continue

        # Skip script commands
        if any(line.startswith(cmd) for cmd in (
            'require', 'create', 'import', 'generate', 'use', 'merge',
            'replace', 'drop', 'keep', 'define', 'assign', 'delete',
            'Opprettet', 'Importerte', 'Genererte', 'Byttet', 'Flettet',
            'Datasettet', 'Tilegnet', 'Et tomt', 'Konverterte'
        )):
            continue

        if not line:
            if in_table:
                in_table = False
            continue

        if sep == '|':
            # Pipe-separated format
            if '---' in line:
                continue
            cells = [c.strip() for c in line.split('|') if c.strip()]
        else:
            # Semicolon-separated format
            cells = [c.strip() for c in line.split(';')]
            # Remove empty trailing cells
            while cells and cells[-1] == '':
                cells.pop()

        if not cells:
            continue

        # Detect header row
        if not in_table and headers is None:
            # Header if first cell looks like a variable name
            if cells[0] in ('yrke4', 'yrke', 'alder_gr', 'ai_q', 'kjoenn'):
                headers = cells
                in_table = True
                continue

        if not in_table or headers is None:
            continue

        # Data row
        row = {'date': current_date}

        if cells[0].lower() == 'total':
            row['_is_total'] = True
        else:
            row['_is_total'] = False

        # Map cells to headers
        for i, h in enumerate(headers):
            if i < len(cells):
                val = cells[i].replace(' ', '').replace('\xa0', '')
                if val == '-':
                    val = ''  # suppressed cell
                row[h] = val

        all_rows.append(row)

    return all_rows


def reshape_twoway(rows: list[dict]) -> list[dict]:
    """Reshape twoway table (wide format) to long format.

    Input: rows with columns like {date, yrke4, 0, 1, 2, ..., 9, Total}
    Output: rows with {date, yrke4, alder_gr, count}
    """
    long_rows = []
    # Detect age group columns (numeric headers)
    sample = rows[0] if rows else {}
    age_cols = [k for k in sample.keys()
                if k not in ('date', 'yrke4', 'Total', '_is_total')
                and k.isdigit()]

    if not age_cols:
        return rows  # Not a twoway table

    for row in rows:
        if row.get('_is_total'):
            continue
        for ag in age_cols:
            val = row.get(ag, '')
            if val:  # Skip suppressed/empty
                long_rows.append({
                    'date': row.get('date', ''),
                    'yrke4': row.get('yrke4', ''),
                    'alder_gr': ag,
                    'count': val
                })

    return long_rows


def parse_and_save(input_path: str, output_path: str, long_format: bool = True):
    """Parse input file and save as CSV."""
    text = Path(input_path).read_text(encoding='utf-8')
    rows = parse_bulk_export(text)

    if not rows:
        print("No data found in input file")
        return

    # Check if this is a twoway table
    sample = rows[0]
    is_twoway = any(k.isdigit() for k in sample.keys()
                    if k not in ('date', '_is_total'))

    if is_twoway and long_format:
        rows = reshape_twoway(rows)
        fieldnames = ['date', 'yrke4', 'alder_gr', 'count']
    else:
        # Keep wide format, remove internal fields
        fieldnames = [k for k in rows[0].keys() if k != '_is_total']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, '') for k in fieldnames})

    print(f"Saved {len(rows)} rows to {output_path}")

    # Summary
    dates = set(r.get('date', '') for r in rows if r.get('date'))
    occupations = set(r.get('yrke4', '') for r in rows if r.get('yrke4'))
    print(f"  Dates: {min(dates)} to {max(dates)} ({len(dates)} months)")
    print(f"  Occupations: {len(occupations)} unique")
    if 'count' in rows[0]:
        total = sum(int(r['count']) for r in rows if r.get('count', '').isdigit())
        print(f"  Total count: {total:,}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python parse_microdata_output.py input_file output.csv")
        print("  Parses microdata.no bulk export to structured CSV")
        print("  Twoway tables are reshaped to long format (date, yrke4, alder_gr, count)")
        sys.exit(1)
    parse_and_save(sys.argv[1], sys.argv[2])
