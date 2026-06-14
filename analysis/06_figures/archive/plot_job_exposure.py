"""
Figure 5d - age x quintile grid using the time-weighted Anthropic
job_exposure measure (styrk08_job_exposure_mapping.csv).

Reuses plot_figure5() from plot_figures_handa.py by passing in a
synthetic mapping dict keyed on styrk08 with the job_exposure quintile
stored under 'q_job'.
"""

import csv
from pathlib import Path

from plot_handa import (
    BASE_DIR,
    FIG_DIR,
    healy_style,
    load_counts,
    plot_figure5,
)
from _age_adjust import load_population_monthly, load_composition_factors

JOB_EXPOSURE_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_job_exposure_mapping.csv'


def load_job_exposure():
    """Load job_exposure mapping: styrk08 -> {'q_job': int, ...}."""
    mapping = {}
    with open(JOB_EXPOSURE_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            code = row['styrk08']
            try:
                q = int(row['quintile'])
            except (ValueError, KeyError):
                continue
            mapping[code] = {
                'q_job': q,
                'observed_exposure': float(row['observed_exposure']),
            }
    return mapping


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    print("Loading data...")
    counts = load_counts()
    mapping = load_job_exposure()
    pop = load_population_monthly()
    factors = load_composition_factors()
    print(f"  {len(counts):,} count rows, "
          f"{len(mapping)} occupations with job_exposure scores")

    print("Plotting Figure 5d (job_exposure quintiles)...")
    # plot_figure5 saves to figure5{suffix}_age_by_quintile_handa.pdf,
    # so we rename afterwards to match the paper's expected filename.
    plot_figure5(counts, mapping, 'q_job', 'd',
                 'Anthropic job exposure (time-weighted)',
                 pop, factors)

    src = FIG_DIR / 'figure5d_age_by_quintile_handa.pdf'
    dst = FIG_DIR / 'figure5d_age_by_quintile_job_exposure.pdf'
    if src.exists():
        src.replace(dst)
        print(f"Renamed -> {dst.name}")


if __name__ == '__main__':
    main()
