"""
Figure A0: Norwegian macroeconomic context, 2021-2025.

Single panel with three series (all in percent):
  - Policy rate (Norges Bank)
  - AKU unemployment rate (SSB, seasonally adjusted)
  - Registered unemployment rate (NAV, % of labour force)

Clear gridlines, direct end-labels, high data-ink ratio.
"""

import csv
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from _plot_notes import place_note

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data' / 'macro'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

CHATGPT_LAUNCH = datetime(2022, 11, 1)


def load_series(filename):
    dates, vals = [], []
    with open(DATA_DIR / filename, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            y, m = row['date'].split('-')
            dates.append(datetime(int(y), int(m), 1))
            vals.append(float(row['value']))
    return dates, vals


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size': 26,
        'axes.titlesize': 32,
        'figure.titlesize': 36,
        'lines.linewidth': 1.8,
    })

    rate_d, rate_v = load_series('norges_bank_policy_rate.csv')
    aku_d, aku_v = load_series('ssb_aku_unemployment.csv')
    reg_d, reg_v = load_series('nav_registered_unemployment_pct.csv')

    fig, ax = plt.subplots(figsize=(12, 5.5))

    # Spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.5)
    ax.spines['bottom'].set_linewidth(0.5)
    ax.spines['left'].set_color('#333333')
    ax.spines['bottom'].set_color('#333333')

    # Grid
    ax.grid(True, axis='y', color='#AAAAAA', linewidth=0.9, linestyle='-')
    ax.grid(True, axis='x', color='#BBBBBB', linewidth=0.7, linestyle='-')
    ax.set_axisbelow(True)

    # Colors
    c_rate = '#2171B5'
    c_aku = '#D55E00'
    c_reg = '#009E73'

    # Plot
    ax.plot(rate_d, rate_v, color=c_rate, linewidth=2.2, label='Policy rate')
    ax.plot(aku_d, aku_v, color=c_aku, linewidth=1.8, label='AKU unemployment')
    ax.plot(reg_d, reg_v, color=c_reg, linewidth=1.8, linestyle='--',
            label='Registered unemployment')

    # ChatGPT line
    ax.axvline(x=CHATGPT_LAUNCH, color='#999999', linestyle=':',
               linewidth=0.9)
    ax.text(CHATGPT_LAUNCH, 6.6,
            ' ChatGPT', fontsize=18, color='#999999', va='top', ha='left')

    # Direct labels inside plot region (left side, near start of lines)
    label_x = datetime(2021, 2, 1)
    ax.text(label_x, 6.3, 'AKU unemployment', fontsize=22, color=c_aku,
            fontweight='semibold', va='center')
    ax.text(datetime(2024, 7, 1), 1.4, 'Registered unemployment', fontsize=22,
            color=c_reg, fontweight='semibold', va='center')
    ax.text(label_x, 0.5, 'Policy rate', fontsize=22, color=c_rate,
            fontweight='semibold', va='center')

    # Axes
    ax.set_ylabel('Percent', fontsize=24, color='#555555')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.yaxis.set_major_locator(plt.MultipleLocator(1))
    ax.tick_params(axis='both', length=3, width=0.4, labelsize=24,
                   colors='#333333')
    ax.set_ylim(0, 6.8)

    ax.set_title('Macroeconomic context: Norway 2021\u20132026',
                 fontweight='semibold', pad=12)

    fig.tight_layout()
    place_note(fig, ax,
               'Sources: Norges Bank (policy rate), SSB table 13760 '
               '(AKU, seasonally adjusted), NAV (registered fully '
               'unemployed as % of labour force).',
               y=-0.02, color='#888888')
    out = FIG_DIR / 'figureA0a_macro_context.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == '__main__':
    main()
