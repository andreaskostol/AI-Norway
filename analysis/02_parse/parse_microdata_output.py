"""
parse_microdata_output.py

Purpose: Parse the raw text that microdata.no produces when you "Eksporter
    skriptresultatene" -> "Kopier til utklippstavlen" into a clean long-format
    CSV. This is step 5 of the workflow and the entry point of the whole local
    analysis: every downstream timeseries, table, and figure reads the *_parsed
    CSVs this script writes. Twoway (occupation x age-group) tables are melted to
    one row per (date, occupation, age-group, count); cell suppression and
    script/log noise from the export are stripped out.

    Handles two export formats:
    1. Pipe-separated: | col1 | col2 | (text-format copy)
    2. Semicolon-separated: col1; val1; val2 (CSV-format copy)
    Detects tabulate commands to recover month/date context, and treats '-'
    (and cells < 5 that microdata.no hides) as suppressed.

Input:   input_file   (raw microdata.no export, typically microdata-output/*_raw.csv)
Output:  output.csv   (parsed long-format CSV, typically microdata-output/*_parsed.csv)

Usage:
    python analysis/02_parse/parse_microdata_output.py input_file output.csv
"""

import csv                                          # write the parsed output CSV
import re                                           # regex matching for dates / filters
import sys                                          # read command-line arguments
from pathlib import Path                            # read the input file


def detect_separator(text: str) -> str:
    """Detect whether the file uses pipe or semicolon separation."""
    # Scan lines until we find a data-looking (non-command) line.
    for line in text.split('\n'):
        # Trim surrounding whitespace.
        line = line.strip()
        # Skip blank lines and microdata.no script/command lines.
        if line and not line.startswith(('require', 'create', 'import', 'generate',
                                         'use', 'merge', 'replace', 'drop', 'keep',
                                         'define', 'assign', 'delete', 'tabulate')):
            # A semicolon but no pipe means CSV-format export.
            if ';' in line and '|' not in line:
                return ';'
            # Any pipe means text-format (pipe) export.
            if '|' in line:
                return '|'
    # Default to semicolon if nothing decisive was found.
    return ';'


def parse_bulk_export(text: str) -> list[dict]:
    """Parse a microdata.no bulk export file containing multiple twoway tables.

    Returns list of dicts with keys depending on table structure.
    For twoway yrke4 × alder_gr: {date, yrke4, alder_gr_0, alder_gr_1, ..., Total}
    For oneway with if: {date, yrke4, count, alder_gr_filter}
    """
    # Decide which delimiter this export uses.
    sep = detect_separator(text)
    # Split the whole export into individual lines.
    lines = text.split('\n')
    # Accumulator for every parsed data row.
    all_rows = []
    # The date currently in effect (set by the most recent import line).
    current_date = None
    # The tabulate command currently in effect (for context).
    current_tabulate = None
    # Whether we are currently inside a table's data rows.
    in_table = False
    # The column headers for the current table.
    headers = None

    # Walk the export line by line.
    for line in lines:
        # Trim surrounding whitespace.
        line = line.strip()

        # Detect import command to extract date
        # An import of the wage/occupation dataset carries the YYYY-MM-DD status date.
        date_match = re.search(r'ARBLONN_ARB_YRKE_STYRK08\s+(\d{4}-\d{2}-\d{2})', line)
        # If this line names a date, remember it for the rows that follow.
        if date_match:
            # Store the captured date.
            current_date = date_match.group(1)
            # Nothing more to do with this line.
            continue

        # Detect tabulate command
        # A tabulate line starts a fresh table.
        if line.startswith('tabulate'):
            # Remember the command text.
            current_tabulate = line
            # We have not yet seen this table's data rows.
            in_table = False
            # Reset headers for the new table.
            headers = None
            # Check for if-filter on age
            # Capture an optional "if alder == N" filter (context only).
            age_match = re.search(r'if\s+alder(?:_gr)?\s*==\s*(\d+)', line)
            # Move on to the next line.
            continue

        # Skip script commands
        # Drop microdata.no script verbs and Norwegian log/echo lines.
        if any(line.startswith(cmd) for cmd in (
            'require', 'create', 'import', 'generate', 'use', 'merge',
            'replace', 'drop', 'keep', 'define', 'assign', 'delete',
            'Opprettet', 'Importerte', 'Genererte', 'Byttet', 'Flettet',
            'Datasettet', 'Tilegnet', 'Et tomt', 'Konverterte'
        )):
            # These are not data; skip them.
            continue

        # A blank line ends the current table.
        if not line:
            # Close out the table if one was open.
            if in_table:
                in_table = False
            # Nothing to parse on a blank line.
            continue

        # Split the line into cells according to the detected separator.
        if sep == '|':
            # Pipe-separated format
            # Skip the ASCII rule lines (e.g. |----|----|).
            if '---' in line:
                continue
            # Split on '|' and keep only non-empty trimmed cells.
            cells = [c.strip() for c in line.split('|') if c.strip()]
        else:
            # Semicolon-separated format
            # Split on ';' and trim each cell.
            cells = [c.strip() for c in line.split(';')]
            # Remove empty trailing cells
            # Drop empty cells at the end (trailing separators).
            while cells and cells[-1] == '':
                cells.pop()

        # Nothing usable on this line.
        if not cells:
            continue

        # Detect header row
        # Before a table's data begins, look for its header row.
        if not in_table and headers is None:
            # Header if first cell looks like a variable name
            # A known variable name in the first cell marks the header.
            if cells[0] in ('yrke4', 'yrke', 'alder_gr', 'ai_q', 'kjoenn'):
                # Record the header cells as column names.
                headers = cells
                # We are now inside the table's data section.
                in_table = True
                # Header consumed; move on.
                continue

        # If we are not inside a table with known headers, skip the line.
        if not in_table or headers is None:
            continue

        # Data row
        # Build a row dict seeded with the current date.
        row = {'date': current_date}

        # Flag the "Total" summary row so it can be dropped later.
        if cells[0].lower() == 'total':
            # Mark as the total row.
            row['_is_total'] = True
        else:
            # Mark as an ordinary data row.
            row['_is_total'] = False

        # Map cells to headers
        # Pair each header with its cell value.
        for i, h in enumerate(headers):
            # Only map cells that actually exist on this line.
            if i < len(cells):
                # Strip spaces and non-breaking spaces from the value.
                val = cells[i].replace(' ', '').replace('\xa0', '')
                # A '-' marks a suppressed cell.
                if val == '-':
                    val = ''  # suppressed cell
                # Store the cleaned value under its column name.
                row[h] = val

        # Keep this parsed row.
        all_rows.append(row)

    # Return all parsed rows.
    return all_rows


def reshape_twoway(rows: list[dict]) -> list[dict]:
    """Reshape twoway table (wide format) to long format.

    Input: rows with columns like {date, yrke4, 0, 1, 2, ..., 9, Total}
    Output: rows with {date, yrke4, alder_gr, count}
    """
    # Accumulator for the long-format rows.
    long_rows = []
    # Detect age group columns (numeric headers)
    # Use the first row to discover the column names.
    sample = rows[0] if rows else {}
    # Age-group columns are the numeric headers (not date/yrke4/Total/internal).
    age_cols = [k for k in sample.keys()
                if k not in ('date', 'yrke4', 'Total', '_is_total')
                and k.isdigit()]

    # If there are no numeric age columns, this is not a twoway table.
    if not age_cols:
        return rows  # Not a twoway table

    # Melt each wide row into one long row per age group.
    for row in rows:
        # Skip the "Total" summary rows.
        if row.get('_is_total'):
            continue
        # One output row for each age-group column.
        for ag in age_cols:
            # The count for this occupation x age group.
            val = row.get(ag, '')
            # Skip suppressed/empty cells.
            if val:  # Skip suppressed/empty
                # Emit the long-format record.
                long_rows.append({
                    'date': row.get('date', ''),
                    'yrke4': row.get('yrke4', ''),
                    'alder_gr': ag,
                    'count': val
                })

    # Return the long-format rows.
    return long_rows


def parse_and_save(input_path: str, output_path: str, long_format: bool = True):
    """Parse input file and save as CSV."""
    # Read the raw export as UTF-8 text.
    text = Path(input_path).read_text(encoding='utf-8')
    # Parse it into a list of row dicts.
    rows = parse_bulk_export(text)

    # Bail out if the file held no parseable data.
    if not rows:
        print("No data found in input file")
        return

    # Check if this is a twoway table
    # Inspect the first row's keys.
    sample = rows[0]
    # Twoway if any non-internal key is a numeric (age-group) column.
    is_twoway = any(k.isdigit() for k in sample.keys()
                    if k not in ('date', '_is_total'))

    # Decide output shape: melt twoway tables to long format if requested.
    if is_twoway and long_format:
        # Reshape wide -> long.
        rows = reshape_twoway(rows)
        # Fixed long-format columns.
        fieldnames = ['date', 'yrke4', 'alder_gr', 'count']
    else:
        # Keep wide format, remove internal fields
        # Keep every column except the internal _is_total flag.
        fieldnames = [k for k in rows[0].keys() if k != '_is_total']

    # Write the parsed rows to the output CSV.
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        # DictWriter restricted to the chosen field names.
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        # Write the header line.
        writer.writeheader()
        # Write one line per row (missing keys become empty).
        for row in rows:
            writer.writerow({k: row.get(k, '') for k in fieldnames})

    # Report how many rows were written.
    print(f"Saved {len(rows)} rows to {output_path}")

    # Summary
    # Distinct dates present in the output.
    dates = set(r.get('date', '') for r in rows if r.get('date'))
    # Distinct occupation codes present in the output.
    occupations = set(r.get('yrke4', '') for r in rows if r.get('yrke4'))
    # Report the date span and month count.
    print(f"  Dates: {min(dates)} to {max(dates)} ({len(dates)} months)")
    # Report the number of unique occupations.
    print(f"  Occupations: {len(occupations)} unique")
    # If counts are present, report the grand total as a sanity check.
    if 'count' in rows[0]:
        # Sum only the cells that are plain integers.
        total = sum(int(r['count']) for r in rows if r.get('count', '').isdigit())
        # Print the grand total with thousands separators.
        print(f"  Total count: {total:,}")


if __name__ == '__main__':
    # Require both an input and an output path.
    if len(sys.argv) < 3:
        # Print usage help and exit non-zero on misuse.
        print("Usage: python parse_microdata_output.py input_file output.csv")
        print("  Parses microdata.no bulk export to structured CSV")
        print("  Twoway tables are reshaped to long format (date, yrke4, alder_gr, count)")
        sys.exit(1)
    # Parse the first argument and write to the second.
    parse_and_save(sys.argv[1], sys.argv[2])
