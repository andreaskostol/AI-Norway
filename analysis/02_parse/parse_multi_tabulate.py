"""
Parse microdata.no raw output files with multiple tabulate blocks per month.

Handles files where each monthly block produces several tabulate outputs
(e.g. summarize(kontantlonn), summarize(stillingspst), summarize(timelonn))
and reshapes them into a single long-format CSV.

Output format: date, yrke4, alder_gr, variable, value

Usage:
    python parse_multi_tabulate.py input1.csv [input2.csv ...] output.csv

Can combine multiple split files (e.g. 2021-2025m06 + 2025m07-2025m12).
"""

import csv
import re
import sys
from pathlib import Path


def extract_variable_name(tabulate_cmd: str) -> str:
    """Extract the summarized variable name from a tabulate command.

    Examples:
        'tabulate yrke4 alder_gr, summarize(kontantlonn) flatten'
            -> 'kontantlonn'
        'tabulate yrke4 alder_gr, summarize(overtid_timer) flatten'
            -> 'overtid_timer'
        'tabulate yrke4 alder_gr, summarize(kontantlonn) std flatten'
            -> 'kontantlonn_sd'
        'tabulate yrke4 alder_gr, flatten'
            -> 'count'
    """
    m = re.search(r'summarize\((\w+)\)', tabulate_cmd)
    if m:
        var = m.group(1)
        if ' std ' in tabulate_cmd or tabulate_cmd.endswith(' std'):
            return var + '_sd'
        return var
    return 'count'


def parse_multi_tabulate(text: str) -> list[dict]:
    """Parse a raw microdata.no export with multiple tabulate outputs per month.

    Returns list of dicts: {date, yrke4, alder_gr, variable, value}
    """
    lines = text.split('\n')
    all_rows = []
    current_date = None
    current_variable = None
    current_filter = {}  # e.g. {'sekt': '1'} from "if sekt == 1"
    in_table = False
    headers = None

    for line in lines:
        line = line.strip()

        # Detect import command to extract date
        date_match = re.search(r'ARBLONN_\w+\s+(\d{4}-\d{2}-\d{2})', line)
        if date_match:
            current_date = date_match.group(1)
            continue

        # Detect tabulate command
        if line.startswith('tabulate'):
            current_variable = extract_variable_name(line)
            in_table = False
            headers = None
            # Extract if-filter (e.g. "if sekt == 1")
            current_filter = {}
            filter_match = re.search(r'if\s+(\w+)\s*==\s*(\S+)', line)
            if filter_match:
                current_filter[filter_match.group(1)] = filter_match.group(2).strip("'\",")
            continue

        # Skip script commands and microdata.no status messages
        if any(line.startswith(cmd) for cmd in (
            'require', 'create', 'import', 'generate', 'use', 'merge',
            'replace', 'drop', 'keep', 'define', 'assign', 'delete',
            'Opprettet', 'Importerte', 'Genererte', 'Byttet', 'Flettet',
            'Datasettet', 'Tilegnet', 'Et tomt', 'Konverterte', 'Slettet',
            'Erstattet', 'Droppet', 'Beholdt'
        )):
            continue

        if not line:
            if in_table:
                in_table = False
            continue

        # Parse semicolon-separated data
        cells = [c.strip() for c in line.split(';')]
        while cells and cells[-1] == '':
            cells.pop()

        if not cells:
            continue

        # Detect header row
        if not in_table and headers is None:
            if cells[0] in ('yrke4', 'ai_q', 'alder_gr'):
                headers = cells
                in_table = True
                continue

        if not in_table or headers is None:
            continue

        # Skip Total row
        if cells[0].lower() == 'total':
            continue

        # Data row: reshape wide to long.
        # Leading non-numeric headers (e.g. yrke4, sekt) are key/dimension
        # columns; numeric headers are age groups. This handles both the
        # one-key format (yrke4; 0; 1; ...) and the two-key format produced
        # by `tabulate yrke4 alder_gr sekt, flatten` (yrke4; sekt; 0; 1; ...).
        key_cols = [(i, h) for i, h in enumerate(headers)
                    if not h.isdigit() and h.lower() != 'total']
        age_cols = [(i, h) for i, h in enumerate(headers) if h.isdigit()]

        key_values = {}
        incomplete = False
        for i, h in key_cols:
            if i >= len(cells):
                incomplete = True
                break
            key_values[h] = cells[i]
        if incomplete:
            continue

        for i, h in age_cols:
            if i >= len(cells):
                continue
            val = cells[i].replace(' ', '').replace('\xa0', '')
            if val == '-' or val == '':
                continue  # suppressed or missing

            row_dict = {
                'date': current_date,
                'alder_gr': h,
                'variable': current_variable,
                'value': val,
            }
            row_dict.update(key_values)   # yrke4 (+ sekt if present)
            row_dict.update(current_filter)
            all_rows.append(row_dict)

    return all_rows


def main():
    if len(sys.argv) < 3:
        print("Usage: python parse_multi_tabulate.py input1.csv [input2.csv ...] output.csv")
        print("  Parses microdata.no raw output with multiple summarize variables")
        print("  Output: date, yrke4, alder_gr, variable, value")
        sys.exit(1)

    output_path = sys.argv[-1]
    input_paths = sys.argv[1:-1]

    all_rows = []
    for input_path in input_paths:
        print(f"Parsing {input_path}...")
        text = Path(input_path).read_text(encoding='utf-8')
        rows = parse_multi_tabulate(text)
        all_rows.extend(rows)
        dates = set(r['date'] for r in rows if r.get('date'))
        variables = set(r['variable'] for r in rows)
        print(f"  {len(rows):,} rows, {len(dates)} months, variables: {sorted(variables)}")

    if not all_rows:
        print("No data found")
        return

    # Deduplicate: split files can overlap (e.g. an early file ending in
    # 2022m05 and a later file starting in 2022m05). Identical extraction
    # logic => identical values, so keep the first occurrence of each
    # (everything except value) key.
    before = len(all_rows)
    seen = set()
    deduped = []
    for r in all_rows:
        k = tuple(sorted((kk, vv) for kk, vv in r.items() if kk != 'value'))
        if k in seen:
            continue
        seen.add(k)
        deduped.append(r)
    if len(deduped) < before:
        print(f"Removed {before - len(deduped):,} duplicate rows (overlapping months)")
    all_rows = deduped

    # Determine fieldnames from all rows (some may have filter columns)
    all_keys = set()
    for r in all_rows:
        all_keys.update(r.keys())
    key_col = [k for k in all_rows[0] if k not in ('date', 'alder_gr', 'variable', 'value')
               and k not in ('sekt',)][0]
    # Build fieldnames: date, key_col, alder_gr, then any filter columns, then variable, value
    filter_cols = sorted(all_keys - {'date', key_col, 'alder_gr', 'variable', 'value'})
    fieldnames = ['date', key_col, 'alder_gr'] + filter_cols + ['variable', 'value']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    # Summary
    dates = sorted(set(r['date'] for r in all_rows if r.get('date')))
    variables = sorted(set(r['variable'] for r in all_rows))
    keys = set(r[key_col] for r in all_rows)
    print(f"\nSaved {len(all_rows):,} rows to {output_path}")
    print(f"  Dates: {dates[0]} to {dates[-1]} ({len(dates)} months)")
    print(f"  Variables: {variables}")
    print(f"  {key_col} codes: {len(keys)} unique")


if __name__ == '__main__':
    main()
