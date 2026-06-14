"""
Build time series from monthly microdata.no exports.

Expects CSV files in exports/YYYY-MM/ with employment counts
by age group and AI exposure quartile.

Produces normalized time series (Oct 2022 = 1.0) for plotting.
"""

import csv
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXPORTS_DIR = BASE_DIR / 'exports'
OUTPUT_DIR = BASE_DIR / 'analysis' / 'output' / 'time_series'


def load_monthly_data(exports_dir: Path) -> dict:
    """Load all monthly CSV exports into a dict keyed by (year, month)."""
    data = {}
    for folder in sorted(exports_dir.iterdir()):
        if folder.is_dir() and len(folder.name) == 7:  # YYYY-MM
            year, month = folder.name.split('-')
            csv_files = list(folder.glob('*.csv'))
            for f in csv_files:
                if 'sysselsetting' in f.name.lower() or 'employment' in f.name.lower():
                    rows = []
                    with open(f, encoding='utf-8') as fh:
                        reader = csv.DictReader(fh)
                        for row in reader:
                            rows.append(row)
                    data[(int(year), int(month))] = rows
    return data


def normalize_to_reference(data: dict, ref_year: int = 2022, ref_month: int = 10) -> dict:
    """Normalize counts to reference period = 1.0.

    Args:
        data: dict keyed by (year, month), values are lists of row dicts
        ref_year, ref_month: reference period for normalization

    Returns:
        dict keyed by (year, month), values are dicts of {(age_group, quartile): normalized_value}
    """
    ref_key = (ref_year, ref_month)
    if ref_key not in data:
        print(f"Warning: reference period {ref_year}-{ref_month:02d} not in data")
        return {}

    # Extract reference values
    ref_values = {}
    for row in data[ref_key]:
        age = row.get('alder_gr', '')
        quartile = row.get('ai_q', '')
        count = row.get('count', row.get('Total', row.get('n', '')))
        if count and age and quartile:
            try:
                ref_values[(age, quartile)] = float(count)
            except ValueError:
                pass

    # Normalize all periods
    normalized = {}
    for (year, month), rows in sorted(data.items()):
        period_data = {}
        for row in rows:
            age = row.get('alder_gr', '')
            quartile = row.get('ai_q', '')
            count = row.get('count', row.get('Total', row.get('n', '')))
            if count and age and quartile:
                try:
                    val = float(count)
                    ref = ref_values.get((age, quartile))
                    if ref and ref > 0:
                        period_data[(age, quartile)] = val / ref
                except ValueError:
                    pass
        normalized[(year, month)] = period_data

    return normalized


def save_timeseries(normalized: dict, output_path: Path):
    """Save normalized time series as CSV."""
    # Collect all (age, quartile) combinations
    all_keys = set()
    for period_data in normalized.values():
        all_keys.update(period_data.keys())

    all_keys = sorted(all_keys)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        header = ['year', 'month'] + [f'{age}_Q{q}' for age, q in all_keys]
        writer.writerow(header)

        for (year, month), period_data in sorted(normalized.items()):
            row = [year, month]
            for key in all_keys:
                row.append(f'{period_data.get(key, ""):.4f}' if key in period_data else '')
            writer.writerow(row)

    print(f"Time series saved to {output_path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    data = load_monthly_data(EXPORTS_DIR)
    if not data:
        print("No monthly data found in exports/. Run microdata.no scripts first.")
        print(f"Expected folder structure: {EXPORTS_DIR}/YYYY-MM/*.csv")
        return

    print(f"Loaded {len(data)} months of data")

    normalized = normalize_to_reference(data)
    if normalized:
        save_timeseries(normalized, OUTPUT_DIR / 'employment_normalized.csv')
    else:
        print("Could not normalize (reference period missing)")


if __name__ == '__main__':
    main()
