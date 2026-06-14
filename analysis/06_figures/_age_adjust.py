"""
Shared age-adjustment helpers for figure scripts.

Two adjustments available:
1. Rate: employment / population per age group (removes cohort-size changes)
2. Composition: multiply rate by factor from build_age_adjustment.py
   (removes within-group age composition shifts using 2021-Q1 weights)

Usage:
    from _age_adjust import load_population_monthly, load_composition_factors

    pop = load_population_monthly()
    factors = load_composition_factors()

    # Rate for (age_label, dt):
    rate = employment_count / pop[(age_label, dt)]

    # Composition-adjusted rate:
    adjusted = rate * factors[(alder_gr_str, quarter_str)]
"""

import csv
from datetime import datetime
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
POP_FILE = BASE_DIR / 'data' / 'macro' / 'ssb_population_by_age_quarterly.csv'
ADJ_FILE = BASE_DIR / 'microdata-output' / '03_age_adjustment_2020_2026.csv'

AGE_RANGES = {
    '22-25': (22, 25),
    '26-30': (26, 30),
    '31-34': (31, 34),
    '35-40': (35, 40),
    '41-49': (41, 49),
    '50+':   (50, 69),
}

ALDER_GR_TO_LABEL = {
    '2': '22-25', '3': '26-30', '4': '31-34',
    '5': '35-40', '6': '41-49',
}
ALDER_GR_50PLUS = {'7', '8'}


def load_population_monthly():
    """Load quarterly pop by age group, interpolated to monthly.

    Returns: dict[(age_label, datetime)] = population
    """
    quarterly = defaultdict(dict)
    with open(POP_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            year, q = row['date'].split('-Q')
            month = (int(q) - 1) * 3 + 1
            dt = datetime(int(year), month, 1)
            age = int(row['age'])
            pop = float(row['population'])
            for label, (lo, hi) in AGE_RANGES.items():
                if lo <= age <= hi:
                    quarterly[label][dt] = quarterly[label].get(dt, 0) + pop
                    break

    monthly = {}
    for label, q_series in quarterly.items():
        q_dates = sorted(q_series.keys())
        for i in range(len(q_dates) - 1):
            dt0, dt1 = q_dates[i], q_dates[i + 1]
            v0, v1 = q_series[dt0], q_series[dt1]
            months_between = (dt1.year - dt0.year) * 12 + dt1.month - dt0.month
            for m in range(months_between):
                dt_m = datetime(dt0.year + (dt0.month + m - 1) // 12,
                                (dt0.month + m - 1) % 12 + 1, 1)
                frac = m / months_between
                monthly[(label, dt_m)] = v0 + (v1 - v0) * frac
        monthly[(label, q_dates[-1])] = q_series[q_dates[-1]]

    return monthly


def load_composition_factors():
    """Load composition adjustment factors from build_age_adjustment.py output.

    Returns: dict[(alder_gr_str, quarter_str)] = factor
    e.g. factors[('3', '2023-Q2')] = 1.0002
    """
    factors = {}
    with open(ADJ_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            factors[(row['alder_gr'], row['quarter'])] = float(row['factor'])
    return factors


def dt_to_quarter(dt):
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}-Q{q}"


def get_age_label(alder_gr):
    if alder_gr in ALDER_GR_TO_LABEL:
        return ALDER_GR_TO_LABEL[alder_gr]
    if alder_gr in ALDER_GR_50PLUS:
        return '50+'
    return ''


def alder_gr_for_label(age_label):
    """Return list of alder_gr strings that map to an age_label."""
    result = []
    for k, v in ALDER_GR_TO_LABEL.items():
        if v == age_label:
            result.append(k)
    if age_label == '50+':
        result = list(ALDER_GR_50PLUS)
    return result


def get_comp_factor(age_label, dt, factors):
    """Get composition factor for an age_label at a datetime.

    For compound labels (50+ = alder_gr 7+8), returns weighted average
    — but since factors are nearly 1.0 for these groups, simple average
    is fine.
    """
    quarter = dt_to_quarter(dt)
    gr_list = alder_gr_for_label(age_label)
    vals = [factors.get((g, quarter), 1.0) for g in gr_list]
    return sum(vals) / len(vals) if vals else 1.0


def compute_adjusted_rate(employment, age_label, dt, pop, factors):
    """Compute fully adjusted rate: employment per capita * composition factor."""
    p = pop.get((age_label, dt))
    if not p or p <= 0:
        return None
    rate = employment / p
    comp = get_comp_factor(age_label, dt, factors)
    return rate * comp
