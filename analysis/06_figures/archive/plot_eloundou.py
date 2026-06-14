"""
Replicate Brynjolfsson, Chandar & Chen (2025) Figures 1 and 2
using Norwegian microdata.no employment counts.

Figure 1: Specific occupations (software developers, customer service)
          by age group. Normalized to Oct 2022 = 1.
Figure 2: 2x3 grid by age group, each showing employment by
          Eloundou GPT-4 beta exposure quintile. Normalized to Oct 2022 = 1.

ADJUSTED VERSION: Employment per capita (divided by population in each age
group), with composition adjustment for within-group age shifts.
Unadjusted version: plot_eloundou_unadjusted.py

Style: Kieran Healy - white background, Okabe-Ito palette, minimal spines,
       light gridlines, direct end-labels, high data-ink ratio.
"""

import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from collections.abc import Mapping

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from _plot_notes import place_note
from _age_adjust import (load_population_monthly, load_composition_factors,
                         get_age_label, get_comp_factor, compute_adjusted_rate)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FILE = BASE_DIR / 'data' / '01_occ_agemonth_count_2021_2026.csv'
EXPOSURE_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

CHATGPT_LAUNCH = mdates.date2num(datetime(2022, 11, 1))
NORM_DATE = '2022-10-16'

# ---------------------------------------------------------------------------
# Kieran Healy style setup
# ---------------------------------------------------------------------------
# Okabe-Ito colorblind-safe palette
OI = {
    'grey':   '#999999',
    'orange': '#E69F00',
    'sky':    '#56B4E9',
    'green':  '#009E73',
    'yellow': '#F0E442',
    'blue':   '#0072B2',
    'red':    '#D55E00',
    'pink':   '#CC79A7',
}


def healy_style() -> None:
    """Set global matplotlib rcParams to approximate Kieran Healy's style."""
    plt.rcParams.update({
        # White, clean background
        'figure.facecolor': 'white',
        'axes.facecolor':   'white',
        'savefig.facecolor': 'white',
        # Thin spines, only left + bottom
        'axes.linewidth': 0.5,
        'axes.spines.top':   False,
        'axes.spines.right': False,
        'axes.edgecolor':  '#333333',
        # Light grid
        'axes.grid':       True,
        'grid.color':      '#BBBBBB',
        'grid.linewidth':  0.7,
        'grid.linestyle':  '-',
        # Ticks
        'xtick.major.width': 0.4,
        'ytick.major.width': 0.4,
        'xtick.color':  '#333333',
        'ytick.color':  '#333333',
        'xtick.major.size': 3,
        'ytick.major.size': 3,
        # Font - prefer condensed sans-serif; fall back gracefully
        'font.family':     'serif',
        'font.serif':      ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size':       18,
        'axes.titlesize':  20,
        'axes.labelsize':  18,
        'xtick.labelsize': 16,
        'ytick.labelsize': 16,
        'legend.fontsize': 16,
        'figure.titlesize': 22,
        # Lines
        'lines.linewidth': 1.4,
    })


# ---------------------------------------------------------------------------
# Age groups (Brynjolfsson definitions)
# ---------------------------------------------------------------------------
# Our codes: 0=missing, 1=<=21, 2=22-25, 3=26-30, 4=31-34, 5=35-40,
#            6=41-49, 7=50-59, 8=60-69, 9=70+
AGE_MAP = {
    '2': '22-25',
    '3': '26-30',
    '4': '31-34',
    '5': '35-40',
    '6': '41-49',
}
AGE_50PLUS = {'7', '8'}

AGE_LABELS_ORDERED = ['22-25', '26-30', '31-34', '35-40', '41-49', '50+']
AGE_COLORS = {
    '22-25': OI['blue'],
    '26-30': OI['orange'],
    '31-34': OI['green'],
    '35-40': OI['red'],
    '41-49': OI['pink'],
    '50+':   OI['grey'],
}

# Figure 1 occupations (ordered)
FIGURE1_OCCUPATIONS = [
    ('Software developers (2512\u20132514, 2519)', ['2512', '2513', '2514', '2519']),
    ('Customer service agents (4222)', ['4222']),
    ('ICT systems analysts (2511)', ['2511']),
    ('ICT operations technicians (3511)', ['3511']),
]

# Figure 2 quintile colors - graduated from light to dark
QUINTILE_COLORS = {
    1: '#C6DBEF',   # light blue
    2: '#9ECAE1',
    3: '#4292C6',
    4: '#2171B5',
    5: '#08306B',   # near-black blue
}


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def load_counts() -> list[dict]:
    with open(DATA_FILE, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_exposure() -> dict[str, int]:
    """Load exposure mapping: yrke4 -> quintile (1-5)."""
    mapping = {}
    with open(EXPOSURE_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            code = row['styrk08']
            q = row['quintile']
            if q and len(code) == 4:
                mapping[code] = int(q)
    return mapping


def assign_quintile(pctl_rank: float) -> int:
    if pctl_rank <= 20:
        return 1
    elif pctl_rank <= 40:
        return 2
    elif pctl_rank <= 60:
        return 3
    elif pctl_rank <= 80:
        return 4
    else:
        return 5


def date_to_dt(date_str: str) -> datetime:
    parts = date_str.split('-')
    return datetime(int(parts[0]), int(parts[1]), 1)


def normalize_series(series: Mapping[datetime, int | float],
                     norm_dt: datetime) -> dict[datetime, float]:
    ref = series.get(norm_dt)
    if not ref or ref == 0:
        return {}
    return {dt: val / ref for dt, val in series.items()}


def filter_date_range(series: dict[datetime, float]) -> dict[datetime, float]:
    start = datetime(2021, 1, 1)
    end = datetime(2026, 3, 1)
    return {dt: val for dt, val in series.items() if start <= dt <= end}


def add_end_label(ax: plt.Axes, dates: tuple, vals: tuple,
                  label: str, color: str, fontsize: int = 16) -> None:
    """Place a direct label at the end of a line (Healy-style)."""
    ax.annotate(label, xy=(dates[-1], vals[-1]),
                xytext=(6, 0), textcoords='offset points',
                fontsize=fontsize or 16, color=color, va='center',
                annotation_clip=False)


# ---------------------------------------------------------------------------
# Figure 1 - specific occupations by age group
# ---------------------------------------------------------------------------
def plot_figure1(counts: list[dict], pop, factors) -> None:
    norm_dt = date_to_dt(NORM_DATE)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    for ax, (occ_label, occ_codes) in zip(axes.flatten(), FIGURE1_OCCUPATIONS):
        agg: dict[tuple[str, datetime], int] = defaultdict(int)
        for row in counts:
            if row['yrke4'] not in occ_codes:
                continue
            age_label = get_age_label(row['alder_gr'])
            if not age_label:
                continue
            dt = date_to_dt(row['date'])
            count = int(row['count']) if row['count'] else 0
            agg[(age_label, dt)] += count

        for age_label in AGE_LABELS_ORDERED:
            raw = {}
            for (al, dt), emp in agg.items():
                if al != age_label:
                    continue
                adj = compute_adjusted_rate(emp, age_label, dt, pop, factors)
                if adj is not None:
                    raw[dt] = adj
            if not raw:
                continue
            normed = normalize_series(raw, norm_dt)
            normed = filter_date_range(normed)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=AGE_COLORS[age_label], linewidth=1.4)
            add_end_label(ax, dates, vals, age_label, AGE_COLORS[age_label])

        # Reference line + ChatGPT marker
        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)
        ax.set_title(occ_label)
        ax.set_ylabel('')
        ax.set_xlabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(0.7, 1.2)

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle('Employment per capita by age group\n'
                 '(October 2022 = 1)',
                 fontweight='semibold')

    note = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1), normalized to October 2022 = 1. '
        'Dashed vertical line marks the\n'
        'launch of ChatGPT (November 2022). '
        'STYRK-08 occupation codes in parentheses. '
        'Age is calculated using month of birth.'
    )
    fig.tight_layout(w_pad=3, h_pad=3, rect=(0, 0, 1, 0.95))
    place_note(fig, axes, note, y=0.01)
    out = FIG_DIR / 'figure1_occupations_by_age.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------------------
# Figure 2 - 2x3 grid by age group, quintile lines
# ---------------------------------------------------------------------------
def plot_figure2(counts: list[dict], exposure: dict[str, int],
                 pop, factors) -> None:
    norm_dt = date_to_dt(NORM_DATE)
    quintile_map = exposure

    agg: dict[tuple[str, int, datetime], int] = defaultdict(int)
    agg_overall: dict[tuple[str, datetime], int] = defaultdict(int)

    for row in counts:
        yrke4 = row['yrke4']
        if yrke4 not in quintile_map:
            continue
        age_label = get_age_label(row['alder_gr'])
        if not age_label:
            continue
        dt = date_to_dt(row['date'])
        count = int(row['count']) if row['count'] else 0
        q = quintile_map[yrke4]
        agg[(age_label, q, dt)] += count
        agg_overall[(age_label, dt)] += count

    fig, axes = plt.subplots(3, 2, figsize=(12, 12))
    axes_flat = axes.flatten()

    title_map = {
        '22-25': 'Early Career 1 (22\u201325)',
        '26-30': 'Early Career 2 (26\u201330)',
        '31-34': 'Developing (31\u201334)',
        '35-40': 'Mid-Career 1 (35\u201340)',
        '41-49': 'Mid-Career 2 (41\u201349)',
        '50+':   'Senior (50+)',
    }

    for i, age_label in enumerate(AGE_LABELS_ORDERED):
        ax = axes_flat[i]

        for q in range(1, 6):
            raw = {}
            for (al, qq, dt), emp in agg.items():
                if al == age_label and qq == q:
                    adj = compute_adjusted_rate(emp, age_label, dt, pop, factors)
                    if adj is not None:
                        raw[dt] = adj
            if not raw:
                continue
            normed = normalize_series(raw, norm_dt)
            normed = filter_date_range(normed)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=QUINTILE_COLORS[q], linewidth=1.6)

        # Overall line (red / Okabe-Ito vermillion)
        raw_all = {}
        for (al, dt), emp in agg_overall.items():
            if al == age_label:
                adj = compute_adjusted_rate(emp, age_label, dt, pop, factors)
                if adj is not None:
                    raw_all[dt] = adj
        if raw_all:
            normed_all = normalize_series(raw_all, norm_dt)
            normed_all = filter_date_range(normed_all)
            if normed_all:
                dates_all, vals_all = zip(*sorted(normed_all.items()))
                ax.plot(dates_all, vals_all, color='red',
                        linewidth=2.0, linestyle='-')

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)

        ax.set_title(title_map[age_label])
        ax.set_ylabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator())
        ax.tick_params(axis='x', which='minor', length=2, width=0.4)
        ax.set_ylim(0.7, 1.2)

    # Shared legend at top of figure
    legend_handles = [
        Line2D([0], [0], color=QUINTILE_COLORS[1], lw=2.5,
               label='Q1 (least exposed)'),
        Line2D([0], [0], color=QUINTILE_COLORS[3], lw=2.5, label='Q3'),
        Line2D([0], [0], color=QUINTILE_COLORS[5], lw=2.5,
               label='Q5 (most exposed)'),
        Line2D([0], [0], color='red', lw=2.5, label='Overall'),
    ]
    fig.legend(handles=legend_handles, loc='upper center',
               ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.98),
               fontsize=16)

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle('Employment per capita by age and AI-exposure quintile\n'
                 '(October 2022 = 1)',
                 y=1.03, fontweight='semibold')

    note = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1), normalized to October 2022 = 1.\n'
        'Dashed vertical line marks the launch of ChatGPT (November 2022). '
        'Exposure quintiles based on GPT-4 $\\beta$ measures from '
        'Eloundou et al. (2024),\nmapped to STYRK-08 '
        'via SOC 2010/ISCO-08 crosswalk. '
        'STYRK-08 = ISCO-08 at 4-digit level (SSB Notater 17/2011). '
        'Darker lines indicate higher AI exposure.'
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    place_note(fig, axes, note, y=0.03)
    out = FIG_DIR / 'figure2_age_by_quintile.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        return
    if not EXPOSURE_FILE.exists():
        print(f"Exposure file not found: {EXPOSURE_FILE}")
        return

    healy_style()

    print("Loading data...")
    counts = load_counts()
    exposure = load_exposure()
    pop = load_population_monthly()
    factors = load_composition_factors()
    print(f"  {len(counts):,} count rows, "
          f"{len(exposure)} occupations with exposure scores, "
          f"{len(pop)} pop entries")

    print("Plotting Figure 1 (adjusted)...")
    plot_figure1(counts, pop, factors)

    print("Plotting Figure 2 (adjusted)...")
    plot_figure2(counts, exposure, pop, factors)


if __name__ == '__main__':
    main()
