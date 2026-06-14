"""Plot firm-FE event-study results from the secure server.

Reads coefficient CSVs in analysis-indiv/from_secure_server/coefficients/ and
produces publication-quality PDFs in analysis/output/figures/.

Two figures:
  firm_fe_es_q5_by_age.pdf   - 6 panels (per age_bin), Q5 vs Q1 event study,
                                from coef_event_study_share.csv (script 6c).
  firm_fe_es_continuous.pdf  - single panel, continuous-exposure x young
                                event study, from
                                coef_event_study_continuous_share.csv (6d).

Coefficients are in workers-per-inhabitant; scaled to per 100 000 inhabitants
for readability.
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SS_DIR   = BASE_DIR / 'analysis-indiv' / 'from_secure_server' / 'coefficients'
FIG_DIR  = BASE_DIR / 'analysis' / 'output' / 'figures'

sys.path.insert(0, str(BASE_DIR / 'analysis' / '06_figures'))
from _plot_notes import place_note

SAMPLE = 'headline_priv'
CHATGPT_K = 0            # k = 0 corresponds to November 2022 (event_zero)

# k -> calendar tick mapping. event_zero = Nov 2022 = k=0; reference k=-1 is
# October 2022. January of each year in the data window corresponds to:
JANUARY_TICKS = [(-22, '2021'), (-10, '2022'), (2, '2023'), (14, '2024'), (26, '2025')]
K_XLIM = (-23, 33)

AGE_LABELS = {
    1: '22\u201325',
    2: '26\u201330',
    3: '31\u201334',
    4: '35\u201340',
    5: '41\u201349',
    6: '50\u201355',
}

QUINTILE_COLORS = {
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
        'grid.color':        '#BBBBBB',
        'grid.linewidth':    0.7,
        'grid.linestyle':    '-',
        'xtick.major.width': 0.4,
        'ytick.major.width': 0.4,
        'xtick.color':       '#333333',
        'ytick.color':       '#333333',
        'xtick.major.size':  3,
        'ytick.major.size':  3,
        'font.family':       'serif',
        'font.serif':        ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size':         16,
        'axes.titlesize':    18,
        'axes.labelsize':    16,
        'xtick.labelsize':   14,
        'ytick.labelsize':   14,
        'legend.fontsize':   14,
        'figure.titlesize':  20,
        'lines.linewidth':   1.4,
    })


def _f(s: str) -> float | None:
    if s == '' or s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_per_age_quintile(path: Path):
    """Return {(age_bin, ai_q): [(k, coef, se), ...]} from 6c output."""
    by_panel: dict[tuple[int, int], list[tuple[int, float, float]]] = defaultdict(list)
    with open(path, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if row['sample'] != SAMPLE:
                continue
            coef = _f(row['coef'])
            se   = _f(row['se'])
            if coef is None:
                continue
            by_panel[(int(row['age_bin']), int(row['ai_q']))].append(
                (int(row['k']), coef, se if se is not None else 0.0)
            )
    for key in by_panel:
        by_panel[key].sort()
    return by_panel


def load_continuous(path: Path):
    """Return [(k, coef, se), ...] sorted by k from 6d output."""
    rows = []
    with open(path, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if row['sample'] != SAMPLE:
                continue
            coef = _f(row['coef'])
            se   = _f(row['se'])
            if coef is None:
                continue
            rows.append((int(row['k']), coef, se if se is not None else 0.0))
    rows.sort()
    return rows


def load_summary_pre_p(path: Path, key_col: str | None) -> dict:
    """Read pre_joint_p from a summary csv. If key_col is None, returns a scalar."""
    with open(path, encoding='utf-8') as fh:
        rows = [r for r in csv.DictReader(fh) if r['sample'] == SAMPLE]
    if key_col is None:
        return _f(rows[0]['pre_joint_p']) if rows else None
    out = {}
    for r in rows:
        out[int(r[key_col])] = _f(r['pre_joint_p'])
    return out


def load_baseline_by_age_q(path: Path) -> dict:
    out: dict[tuple[int, int], float] = {}
    with open(path, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            br = _f(row['baseline_rate'])
            if br is None or br == 0:
                continue
            out[(int(row['age_bin']), int(row['ai_q']))] = br
    return out


def load_baseline_by_age(path: Path) -> dict:
    out: dict[int, float] = {}
    with open(path, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            br = _f(row['baseline_rate'])
            if br is None or br == 0:
                continue
            out[int(row['age_bin'])] = br
    return out


def _format_p(p: float | None) -> str:
    if p is None:
        return 'n/a'
    if p < 1e-4:
        return f'{p:.1e}'
    return f'{p:.3f}'


def _add_zero_reference(series: list[tuple[int, float, float]]):
    """Insert k=-1 with coef = 0 and SE = 0 (reference, omitted from regression)."""
    if not series:
        return series
    if any(k == -1 for k, _, _ in series):
        return series
    series = series + [(-1, 0.0, 0.0)]
    series.sort()
    return series


def plot_q5_by_age(by_panel, pre_p_by_age, baseline_by_age_q,
                   out_path: Path) -> None:
    """Six small multiples: Q5-vs-Q1 event study per age bin, rescaled to
    % of Q5 baseline cohort employment rate at k = -1 (October 2022). Y-axis
    shared across all panels so age groups are directly comparable."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), sharex=True, sharey=True)
    axes_flat = axes.flatten()

    for i, age_bin in enumerate(range(1, 7)):
        ax = axes_flat[i]
        baseline = baseline_by_age_q.get((age_bin, 5))
        series = _add_zero_reference(by_panel.get((age_bin, 5), []))
        if series and baseline:
            scale = 100.0 / baseline                  # rate -> % of baseline
            ks    = [k for k, _, _ in series]
            coefs = [c * scale for _, c, _ in series]
            ses   = [s * scale for _, _, s in series]
            lo    = [c - 1.96 * s for c, s in zip(coefs, ses)]
            hi    = [c + 1.96 * s for c, s in zip(coefs, ses)]

            ax.fill_between(ks, lo, hi, color='#2171B5', alpha=0.20, linewidth=0)
            ax.plot(ks, coefs, color='#08306B', linewidth=2.0)

        ax.axhline(y=0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=-1, color='#555555', linestyle=':', linewidth=0.8, alpha=0.7)
        ax.axvline(x=CHATGPT_K, color='red', linestyle='--', linewidth=0.9,
                   alpha=0.8)

        ax.set_title(f'Ages {AGE_LABELS[age_bin]}')
        ax.set_xlim(*K_XLIM)
        ax.set_xticks([k for k, _ in JANUARY_TICKS])
        ax.set_xticklabels([lab for _, lab in JANUARY_TICKS])

    fig.suptitle('Employment of Q5 (most AI-exposed) occupations vs. Q1, by age cohort\n'
                 'firm-FE event study, per-capita rate (linear OLS)',
                 fontweight='semibold', y=0.99)
    fig.supylabel('% of Q5 cohort employment rate at October 2022',
                  x=0.04, fontsize=15)

    note = (
        'Sample: private-sector foretak (sekt = 3), 22\u201355-year-olds, 2021m1\u20132025m7. '
        'Specification: reghdfe rate = count / N(age, month) on i.k\u00d7i.ai_q, '
        'absorbing foretak\u00d7q and foretak\u00d7month, weighted by SSB cohort '
        'population, clustered at foretak. Estimated separately per age bin. '
        'Reference: October 2022 (k = \u22121, omitted) and Q1 (least exposed, omitted). '
        'Dashed red line: November 2022 (GPT-4 era). '
        'Tick marks at January of each year. '
        'Shaded band: 95 % CI. '
        'Y-axis: gamma_{Q5,k} divided by Q5 cohort employment rate at October 2022, '
        'times 100 (% of Q5 baseline). Shared across panels so age groups are '
        'directly comparable. '
        'Source: from_secure_server/coefficients/coef_event_study_share.csv + baseline_kref_by_age_q.csv.'
    )
    fig.tight_layout(rect=(0.04, 0.17, 1.0, 0.94))
    place_note(fig, axes, note, y=0.13, fontsize=13)

    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out_path}')


def plot_q2to5_grid(by_panel, pre_p_by_age, baseline_by_age_q,
                    out_path: Path) -> None:
    """BCC Figure 4 analogue: Q2-Q5 vs Q1 for each age cohort. Layout is
    6 rows (age) x 4 cols (quintile) so the figure stays narrow. Each row
    shares its y-axis. gamma_{q,k} is divided by baseline_rate[age, q]
    (cohort employment rate in that (age, q) cell at October 2022), so the
    y-axis reads as % of q-specific baseline employment."""
    quintiles = [2, 3, 4, 5]
    nrows, ncols = 6, 4
    fig, axes = plt.subplots(nrows, ncols, sharex=True, sharey='row',
                             figsize=(12.5, 17))

    for r, age_bin in enumerate(range(1, 7)):
        for c, q in enumerate(quintiles):
            ax = axes[r, c]
            baseline = baseline_by_age_q.get((age_bin, q))
            series   = _add_zero_reference(by_panel.get((age_bin, q), []))

            if series and baseline:
                scale = 100.0 / baseline
                ks    = [k for k, _, _ in series]
                coefs = [cc * scale for _, cc, _ in series]
                ses   = [ss * scale for _, _, ss in series]
                lo    = [cc - 1.96 * ss for cc, ss in zip(coefs, ses)]
                hi    = [cc + 1.96 * ss for cc, ss in zip(coefs, ses)]

                ax.fill_between(ks, lo, hi, color='#2171B5',
                                alpha=0.20, linewidth=0)
                ax.plot(ks, coefs, color='#08306B', linewidth=1.4)

            ax.axhline(y=0, color='#AAAAAA', linestyle='--', linewidth=0.5)
            ax.axvline(x=-1, color='#555555', linestyle=':',
                       linewidth=0.8, alpha=0.7)
            ax.axvline(x=CHATGPT_K, color='red', linestyle='--',
                       linewidth=0.9, alpha=0.8)

            ax.set_xlim(*K_XLIM)
            ax.set_xticks([k for k, _ in JANUARY_TICKS])
            ax.set_xticklabels([lab for _, lab in JANUARY_TICKS], fontsize=11)
            ax.tick_params(axis='y', labelsize=11)

            if r == 0:
                ax.set_title(f'Quintile {q}', fontsize=14)
            if c == 0:
                ax.set_ylabel(f'Ages {AGE_LABELS[age_bin]}', fontsize=13)

    fig.suptitle('Employment by AI-exposure quintile vs. Q1, by age cohort\n'
                 'firm-FE event study, per-capita rate (linear OLS)',
                 fontweight='semibold', y=0.995)
    fig.supylabel('% of cohort employment rate at October 2022 '
                  '(divided by baseline in same (age, q) cell)',
                  x=0.005, fontsize=14)

    note = (
        'Sample: private-sector foretak (sekt = 3), 22\u201355-year-olds, '
        '2021m1\u20132025m7. '
        'Specification: reghdfe rate = count / N(age, month) on '
        'i.k\u00d7i.ai_q, absorbing foretak\u00d7q and foretak\u00d7month, '
        'weighted by SSB cohort population, clustered at foretak. '
        'Estimated separately per age bin. '
        'Reference: October 2022 (k = \u22121, omitted) and Q1 (least exposed, '
        'omitted). '
        'Dashed red line: November 2022 (GPT-4 era). '
        'Tick marks at January of each year. '
        'Shaded band: 95 % CI. '
        'Y-axis: gamma_{q,k} divided by cohort employment rate in (age, q) cell '
        'at October 2022, times 100. '
        'Source: from_secure_server/coefficients/coef_event_study_share.csv + '
        'baseline_kref_by_age_q.csv.'
    )
    fig.tight_layout(rect=(0.03, 0.06, 1, 0.97))
    place_note(fig, axes, note, y=0.045, fontsize=12)

    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out_path}')


def plot_continuous(series, pre_p, baseline_young, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 7))
    series = _add_zero_reference(series)

    if not baseline_young:
        raise RuntimeError('Missing young baseline (age_bin=1) for continuous plot.')

    scale = 100.0 / baseline_young        # rate -> % of young baseline
    ks    = [k for k, _, _ in series]
    coefs = [c * scale for _, c, _ in series]
    ses   = [s * scale for _, _, s in series]
    lo    = [c - 1.96 * s for c, s in zip(coefs, ses)]
    hi    = [c + 1.96 * s for c, s in zip(coefs, ses)]

    ax.fill_between(ks, lo, hi, color='#2171B5', alpha=0.20, linewidth=0)
    ax.plot(ks, coefs, color='#08306B', linewidth=2.4)

    ax.axhline(y=0, color='#AAAAAA', linestyle='-', linewidth=0.5)
    ax.axvline(x=-1, color='#555555', linestyle=':', linewidth=0.8, alpha=0.7)
    ax.axvline(x=CHATGPT_K, color='red', linestyle='--', linewidth=0.9,
               alpha=0.8)

    ax.set_xlim(*K_XLIM)
    ax.set_xticks([k for k, _ in JANUARY_TICKS])
    ax.set_xticklabels([lab for _, lab in JANUARY_TICKS])
    ax.set_ylabel('% of young (22\u201325) cohort employment rate at October 2022,\nper SD of exposure')

    ax.set_title('Differential young-cohort employment by AI exposure\n'
                 'continuous-exposure event study, per-capita rate (linear OLS)',
                 fontweight='semibold')

    note = (
        'Sample: private-sector foretak (sekt = 3), 22\u201355-year-olds, 2021m1\u20132025m7. '
        'Specification: reghdfe rate = count / N(age, month) on i.k\u00d7young\u00d7exposure_std, '
        'absorbing foretak\u00d7age + foretak\u00d7month + age\u00d7month, '
        'weighted by SSB cohort population, clustered at foretak. '
        'Young = ages 22\u201325; exposure_std = standardized Eloundou GPT-4 \u03b2. '
        'Event time k aggregated to 2-month bins (k = \u22121, 1, 3, \u2026, 31), labelled '
        'by the last calendar month of the bin. '
        'Reference: October 2022 (omitted). '
        'Dashed red line: November 2022 (GPT-4 era). '
        'Tick marks at January of each year. '
        'Shaded band: 95 % CI. '
        'Coefficient = differential employment-rate change at event time k for young workers '
        'per SD of exposure, divided by the young (22\u201325) cohort employment rate at October '
        '2022, times 100 (% of young baseline). '
        'Source: from_secure_server/coefficients/coef_event_study_continuous_share.csv + '
        'baseline_kref_by_age.csv.'
    )
    fig.tight_layout(rect=(0, 0.22, 1, 1))
    place_note(fig, ax, note, y=0.18, fontsize=13)

    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out_path}')


def plot_q5_by_age_poisson(by_panel, out_path: Path) -> None:
    """Q5 vs Q1 event study, one panel per age bin, from Poisson fepois output.
    Coefficients are log-points; multiplied by 100 they are approximately
    percent changes relative to Q1, no external baseline needed. Y-axis
    shared across panels."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), sharex=True, sharey=True)
    axes_flat = axes.flatten()

    for i, age_bin in enumerate(range(1, 7)):
        ax = axes_flat[i]
        series = _add_zero_reference(by_panel.get((age_bin, 5), []))
        if series:
            ks    = [k for k, _, _ in series]
            coefs = [c * 100 for _, c, _ in series]
            ses   = [s * 100 for _, _, s in series]
            lo    = [c - 1.96 * s for c, s in zip(coefs, ses)]
            hi    = [c + 1.96 * s for c, s in zip(coefs, ses)]

            ax.fill_between(ks, lo, hi, color='#2171B5', alpha=0.20, linewidth=0)
            ax.plot(ks, coefs, color='#08306B', linewidth=2.0)

        ax.axhline(y=0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=-1, color='#555555', linestyle=':', linewidth=0.8, alpha=0.7)
        ax.axvline(x=CHATGPT_K, color='red', linestyle='--', linewidth=0.9,
                   alpha=0.8)

        ax.set_title(f'Ages {AGE_LABELS[age_bin]}')
        ax.set_xlim(*K_XLIM)
        ax.set_xticks([k for k, _ in JANUARY_TICKS])
        ax.set_xticklabels([lab for _, lab in JANUARY_TICKS])

    fig.suptitle('Employment of Q5 (most AI-exposed) occupations vs. Q1, by age cohort\n'
                 'firm-FE event study, Poisson',
                 fontweight='semibold', y=0.99)
    fig.supylabel('Log-points x 100 (~ % change vs Q1, k = \u22121 reference)',
                  x=0.04, fontsize=15)

    note = (
        'Sample: private-sector foretak (sekt = 3), 22\u201355-year-olds, 2021m1\u20132025m7. '
        'Specification: fepois(count_all ~ i(k, ai_q, ref = -1, ref2 = 1) | '
        'foretak^q + foretak^month), clustered at foretak, estimated separately '
        'per age bin. Reference: k = \u22121 (October 2022) and q = 1 (least exposed). '
        'Dashed red line: November 2022 (GPT-4 era). '
        'Tick marks at January of each year. '
        'Shaded band: 95 % CI. '
        'Poisson log-point coefficients gamma_{Q5,k} multiplied by 100 read approximately '
        'as percent change in Q5 employment relative to Q1 employment, at event time k '
        'vs the omitted reference month. '
        'Source: from_secure_server/coefficients/coef_event_study_fepois.csv.'
    )
    fig.tight_layout(rect=(0.04, 0.17, 1.0, 0.94))
    place_note(fig, axes, note, y=0.13, fontsize=13)

    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out_path}')


def plot_q2to5_grid_poisson(by_panel, out_path: Path) -> None:
    """Q2-Q5 vs Q1 event study, 6 rows (age) x 4 cols (quintile), Poisson.
    Same layout as plot_q2to5_grid but coefficients are log-points * 100,
    no baseline normalisation. All panels share y-axis (Poisson log-points
    are directly comparable across ages and quintiles)."""
    quintiles = [2, 3, 4, 5]
    nrows, ncols = 6, 4
    fig, axes = plt.subplots(nrows, ncols, sharex=True, sharey=True,
                             figsize=(12.5, 17))

    for r, age_bin in enumerate(range(1, 7)):
        for c, q in enumerate(quintiles):
            ax = axes[r, c]
            series = _add_zero_reference(by_panel.get((age_bin, q), []))

            if series:
                ks    = [k for k, _, _ in series]
                coefs = [cc * 100 for _, cc, _ in series]
                ses   = [ss * 100 for _, _, ss in series]
                lo    = [cc - 1.96 * ss for cc, ss in zip(coefs, ses)]
                hi    = [cc + 1.96 * ss for cc, ss in zip(coefs, ses)]

                ax.fill_between(ks, lo, hi, color='#2171B5',
                                alpha=0.20, linewidth=0)
                ax.plot(ks, coefs, color='#08306B', linewidth=1.4)

            ax.axhline(y=0, color='#333333', linestyle='-', linewidth=0.9)
            ax.axvline(x=-1, color='#555555', linestyle=':',
                       linewidth=0.8, alpha=0.7)
            ax.axvline(x=CHATGPT_K, color='red', linestyle='--',
                       linewidth=0.9, alpha=0.8)

            ax.set_xlim(*K_XLIM)
            ax.set_ylim(-20, 20)
            ax.set_xticks([k for k, _ in JANUARY_TICKS])
            ax.set_xticklabels([lab for _, lab in JANUARY_TICKS], fontsize=11)
            ax.tick_params(axis='y', labelsize=11)
            # Tick every 10 log-points (~10 % change)
            ax.yaxis.set_major_locator(plt.MultipleLocator(10))

            if r == 0:
                ax.set_title(f'Quintile {q}', fontsize=14)
            if c == 0:
                ax.set_ylabel(f'Ages {AGE_LABELS[age_bin]}', fontsize=13)

    fig.suptitle('Employment by AI-exposure quintile vs. Q1, by age cohort\n'
                 'firm-FE event study, Poisson',
                 fontweight='semibold', y=0.995)
    fig.supylabel('Log-points x 100 (~ % change vs Q1, k = \u22121 reference)',
                  x=0.005, fontsize=14)

    note = (
        'Sample: private-sector foretak (sekt = 3), 22\u201355-year-olds, '
        '2021m1\u20132025m7. '
        'Specification: fepois(count_all ~ i(k, ai_q, ref = -1, ref2 = 1) | '
        'foretak^q + foretak^month), clustered at foretak, estimated separately '
        'per age bin. Reference: October 2022 (k = \u22121) and Q1. '
        'Dashed red line: November 2022 (GPT-4 era). '
        'Tick marks at January of each year. '
        'Shaded band: 95 % CI. '
        'Y-axis: gamma_{q,k} (log-points) x 100, approximately percent change in '
        'q employment relative to Q1 from the reference month to event time k. '
        'All panels share the y-axis (Poisson log-points are directly comparable '
        'across ages and quintiles). '
        'Source: from_secure_server/coefficients/coef_event_study_fepois.csv.'
    )
    fig.tight_layout(rect=(0.03, 0.06, 1, 0.97))
    place_note(fig, axes, note, y=0.045, fontsize=12)

    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out_path}')


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    # --- Linear OLS plots (need baseline files for %-of-baseline scaling) ---
    bl_age_q_path = SS_DIR / 'baseline_kref_by_age_q.csv'
    bl_age_path   = SS_DIR / 'baseline_kref_by_age.csv'
    if bl_age_q_path.exists() and bl_age_path.exists():
        baseline_by_age_q = load_baseline_by_age_q(bl_age_q_path)
        baseline_by_age   = load_baseline_by_age(bl_age_path)

        es_path     = SS_DIR / 'coef_event_study_share.csv'
        es_sum_path = SS_DIR / 'coef_event_study_share_summary.csv'
        if not es_path.exists():
            print(f'Missing: {es_path}')
        else:
            by_panel = load_per_age_quintile(es_path)
            pre_p_by_age = load_summary_pre_p(es_sum_path, 'age_bin') \
                if es_sum_path.exists() else {}
            plot_q5_by_age(by_panel, pre_p_by_age, baseline_by_age_q,
                           FIG_DIR / 'firm_fe_es_q5_by_age_ols.pdf')
            plot_q2to5_grid(by_panel, pre_p_by_age, baseline_by_age_q,
                            FIG_DIR / 'firm_fe_es_q2to5_grid_ols.pdf')

        cont_path     = SS_DIR / 'coef_event_study_continuous_share.csv'
        cont_sum_path = SS_DIR / 'coef_event_study_continuous_share_summary.csv'
        if not cont_path.exists():
            print(f'Missing: {cont_path}')
        else:
            series = load_continuous(cont_path)
            pre_p  = load_summary_pre_p(cont_sum_path, None) \
                if cont_sum_path.exists() else None
            plot_continuous(series, pre_p, baseline_by_age.get(1),
                            FIG_DIR / 'firm_fe_es_continuous_ols.pdf')
    else:
        print('Missing baseline files - skipping linear OLS plots that need them.')

    # --- Poisson plots (log-points are already ~percent; no baseline needed) ---
    poisson_path = SS_DIR / 'coef_event_study_fepois.csv'
    if not poisson_path.exists():
        print(f'Missing Poisson coefs (skip): {poisson_path}')
    else:
        poisson_panel = load_per_age_quintile(poisson_path)
        plot_q5_by_age_poisson(poisson_panel,
                               FIG_DIR / 'firm_fe_es_q5_by_age_poisson.pdf')
        plot_q2to5_grid_poisson(poisson_panel,
                                FIG_DIR / 'firm_fe_es_q2to5_grid_poisson.pdf')


if __name__ == '__main__':
    main()
