"""
Share of Norwegian employment in each Eloundou GPT-4 exposure quintile,
plotted monthly from January 2021 through the latest available month.
Companion to the single-month bar chart in plot_eloundou_employment_share.py.

The bar chart shows a single-month snapshot. The time-series version shows
whether the employment composition across quintiles is stable over the
post-ChatGPT period, or whether the high-exposure share has been shrinking
as predicted by a displacement reading.
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FILE = BASE_DIR / 'data' / '01_occ_agemonth_count_2021_2026.csv'
EXPOSURE_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

WORKING_AGES = {'2', '3', '4', '5', '6', '7', '8'}  # 22-69
CHATGPT_LAUNCH = mdates.date2num(datetime(2022, 11, 1))

QUINTILE_COLORS = {
    1: '#C6DBEF',
    2: '#9ECAE1',
    3: '#4292C6',
    4: '#2171B5',
    5: '#08306B',
}


def healy_style() -> None:
    plt.rcParams.update({
        'figure.facecolor':  'white',
        'axes.facecolor':    'white',
        'savefig.facecolor': 'white',
        'axes.linewidth':    0.5,
        'axes.spines.top':   False,
        'axes.spines.right': False,
        'axes.edgecolor':    '#333333',
        'axes.grid':         True,
        'axes.axisbelow':    True,
        'grid.color':        '#BBBBBB',
        'grid.linewidth':    0.7,
        'grid.linestyle':    '-',
        'xtick.major.width': 0.4,
        'ytick.major.width': 0.4,
        'xtick.color':       '#333333',
        'ytick.color':       '#333333',
        'font.family':       'serif',
        'font.serif':        ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size':         16,
        'axes.titlesize':    20,
        'axes.labelsize':    18,
        'xtick.labelsize':   16,
        'ytick.labelsize':   16,
        'figure.titlesize':  22,
        'lines.linewidth':   2.0,
    })


def load_quintiles() -> dict[str, int]:
    with open(EXPOSURE_FILE, encoding='utf-8') as f:
        return {row['styrk08'].zfill(4): int(row['quintile'])
                for row in csv.DictReader(f)
                if row['quintile'] and len(row['styrk08'].zfill(4)) == 4}


def date_to_dt(s: str) -> datetime:
    y, m, _ = s.split('-')
    return datetime(int(y), int(m), 1)


def load_shares_by_month():
    """Return {date: {quintile 1..5: share, 'unmapped': share}}."""
    quintile = load_quintiles()
    by_dq: dict[datetime, dict] = defaultdict(lambda: defaultdict(int))
    totals: dict[datetime, int] = defaultdict(int)

    with open(DATA_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['alder_gr'] not in WORKING_AGES:
                continue
            dt = date_to_dt(row['date'])
            n = int(row['count']) if row['count'] else 0
            totals[dt] += n
            q = quintile.get(row['yrke4'])
            if q is None:
                by_dq[dt]['unmapped'] += n
            else:
                by_dq[dt][q] += n

    out = {}
    for dt, parts in by_dq.items():
        tot = totals[dt]
        out[dt] = {k: 100 * v / tot for k, v in parts.items()}
    return out


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    shares = load_shares_by_month()
    dates = sorted(shares.keys())

    fig, ax = plt.subplots(figsize=(12, 7))

    # 20 % reference line first so it sits behind the data
    ax.axhline(y=20, color='#999999', linestyle='--', linewidth=1.0,
               zorder=1)
    ax.text(dates[0], 20.4, '20 % equal-employment benchmark',
            fontsize=12, color='#666666', va='bottom', ha='left')

    # ChatGPT release marker
    ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle=':',
               linewidth=1.0, alpha=0.8, zorder=1)
    ax.text(CHATGPT_LAUNCH, 28.4, 'ChatGPT\n(Nov 2022)',
            fontsize=12, color='#555555', va='top', ha='left',
            bbox=dict(facecolor='white', edgecolor='none', pad=2))

    for q in [1, 2, 3, 4, 5]:
        vals = [shares[dt][q] for dt in dates]
        ax.plot(dates, vals, color=QUINTILE_COLORS[q],
                linewidth=2.0, zorder=3)
        # End-of-line direct label
        ax.text(dates[-1], vals[-1],
                f' Q{q}', fontsize=14,
                color=QUINTILE_COLORS[q], va='center', ha='left',
                fontweight='semibold' if q in (1, 5) else 'normal')

    ax.set_ylim(15, 29)
    ax.set_ylabel('Share of total employment (%)')
    ax.set_xlabel('')

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator())
    ax.tick_params(axis='x', which='minor', length=2, width=0.4)

    # Compute the average Q5 share so we can put it in the title
    q5_avg = sum(shares[dt][5] for dt in dates) / len(dates)
    q4q5_avg = sum(shares[dt][4] + shares[dt][5] for dt in dates) / len(dates)

    ax.set_title(
        f'Norwegian employment by AI-exposure quintile, monthly, 2021–2026\n'
        f'Q5 averages {q5_avg:.1f} % of employment; Q4 + Q5 averages '
        f'{q4q5_avg:.0f} %',
        fontweight='semibold', pad=14)

    note = (
        'Notes: Monthly shares of total Norwegian employment (ages 22–69) '
        'in each Eloundou et al.\\ (2024) GPT-4 $\\beta$ exposure quintile. '
        'Quintiles are equal-occupation: each 4-digit STYRK-08 code counts '
        'once, with Q5 containing the 20 % of occupations with the highest '
        'exposure scores. Under equal-employment quintiles every line would '
        'sit at 20 %. About 0.6 % of employment in unmapped occupations '
        '(military, clergy, small specialties) is excluded from the shares. '
        'Microdata.no extract covers January 2021 through February 2026. '
        'Source: microdata.no.'
    )
    fig.text(0.06, 0.02, note, fontsize=11, color='#555555',
             wrap=True, ha='left', va='bottom')

    fig.tight_layout(rect=(0, 0.09, 1, 1))

    out = FIG_DIR / 'figure_eloundou_employment_share_timeseries.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out}')

    # Print a quick numerical summary
    print()
    print(f'{"date":>10}  {"Q1":>5}  {"Q2":>5}  {"Q3":>5}  {"Q4":>5}  {"Q5":>5}')
    for dt in [dates[0], dates[len(dates)//2], dates[-1]]:
        s = shares[dt]
        print(f'{dt.strftime("%Y-%m"):>10}  '
              f'{s[1]:5.2f}  {s[2]:5.2f}  {s[3]:5.2f}  {s[4]:5.2f}  {s[5]:5.2f}')


if __name__ == '__main__':
    main()
