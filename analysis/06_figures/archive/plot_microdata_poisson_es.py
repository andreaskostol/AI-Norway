"""
Poisson event-study on the microdata.no cell-level employment counts.

Companion to the firm-FE Poisson event study in Appendix C of the paper. The
cell-level data aggregates over firms, so no firm dimension is available; this
script runs the closest counterpart without firm fixed effects:

    count_{j,a,t} ~ Poisson
    log E[count_{j,a,t}] = alpha_j + beta_t
                        + sum_{q in {2..5}, k != -1} gamma_{q,k}
                          * 1[ai_q(j) = q] * 1[k(t) = k]

estimated separately per age bin a, where
    j           = 4-digit STYRK-08 occupation
    t           = month
    ai_q(j)     = Eloundou GPT-4 beta quintile of occupation j
    k(t)        = months since October 2022 (k = -1 is reference)
    alpha_j     = occupation fixed effect (absorbs ai_q baseline)
    beta_t      = month fixed effect (absorbs aggregate time path)
    gamma_{q,k} = Q vs Q1 event-study coefficient (Q1 omitted, k = -1 omitted)

SE clustered at occupation. Coefficients (and SE) saved to
    analysis/output/coefficients/coef_microdata_poisson_es.csv
Figure (6 age x 4 quintile grid, same layout as
firm_fe_es_q2to5_grid_poisson.pdf in Appendix C):
    analysis/output/figures/figure_microdata_poisson_es_grid.pdf
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
import statsmodels.api as sm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FILE = BASE_DIR / 'data' / '01_occ_agemonth_count_2021_2026.csv'
EXPOSURE_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'
COEF_DIR = BASE_DIR / 'analysis' / 'output' / 'coefficients'

sys.path.insert(0, str(BASE_DIR / 'analysis' / '06_figures'))
from _plot_notes import place_note

# --- Layout constants matching firm_fe_es_q2to5_grid_poisson.pdf -----------
CHATGPT_K = 0
JANUARY_TICKS = [(-22, '2021'), (-10, '2022'), (2, '2023'), (14, '2024'),
                 (26, '2025'), (38, '2026')]
K_XLIM = (-23, 40)
REF_K = -1

AGE_LABELS = {
    1: '22-25',
    2: '26-30',
    3: '31-34',
    4: '35-40',
    5: '41-49',
    6: '50+',
}

# alder_gr -> age_bin (50+ = alder_gr 7 + 8 + 9, but we follow BCC and cap at 50-69)
ALDER_GR_TO_BIN = {'2': 1, '3': 2, '4': 3, '5': 4, '6': 5, '7': 6, '8': 6}

QUINTILES = [2, 3, 4, 5]  # Q1 is baseline


# --- Style (mirrors plot_secure_server_results.py) -------------------------
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


# --- Data loading ----------------------------------------------------------
def load_panel() -> pd.DataFrame:
    """Load cell-level counts, attach quintile, age_bin, event time k."""
    df = pd.read_csv(DATA_FILE, dtype={'yrke4': str, 'alder_gr': str})
    df['count'] = df['count'].astype(int)
    df['date'] = pd.to_datetime(df['date'])
    df['ym_int'] = df['date'].dt.year * 12 + df['date'].dt.month
    ref_ym = 2022 * 12 + 10  # Oct 2022 = k = -1
    df['k'] = (df['ym_int'] - (ref_ym + 1)).astype(int)

    df['age_bin'] = df['alder_gr'].map(ALDER_GR_TO_BIN)
    df = df.dropna(subset=['age_bin'])
    df['age_bin'] = df['age_bin'].astype(int)

    exp_df = pd.read_csv(EXPOSURE_FILE, dtype={'styrk08': str})
    exp_df['yrke4'] = exp_df['styrk08'].astype(str).str.zfill(4)
    exp_df = exp_df.dropna(subset=['quintile'])
    exp_df['ai_q'] = exp_df['quintile'].astype(int)
    exp_df = exp_df[['yrke4', 'ai_q']]
    df = df.merge(exp_df, on='yrke4', how='inner')

    df = (df.groupby(['yrke4', 'ai_q', 'age_bin', 'k'], as_index=False)
            ['count'].sum())
    return df


def balance_panel(sub: pd.DataFrame) -> pd.DataFrame:
    """Fill missing (yrke4, k) cells within an age bin with count = 0.

    Cells with < 5 workers are suppressed by microdata.no privacy rules and
    therefore missing from the raw export. Treating them as 0 (vs the true
    value of <5) is a small approximation; Poisson handles zeros naturally.
    """
    yrke4s = sub['yrke4'].unique()
    ks = sub['k'].unique()
    grid = pd.MultiIndex.from_product([yrke4s, ks], names=['yrke4', 'k']) \
        .to_frame(index=False)
    ai_q_map = sub[['yrke4', 'ai_q']].drop_duplicates()
    grid = grid.merge(ai_q_map, on='yrke4', how='left')
    out = grid.merge(sub[['yrke4', 'k', 'count']], on=['yrke4', 'k'], how='left')
    out['count'] = out['count'].fillna(0).astype(int)
    return out


# --- Design matrix construction --------------------------------------------
def build_design(sub: pd.DataFrame):
    """Build sparse design matrix for one age bin.

    Columns (in order):
        intercept                                  (1)
        occupation dummies (drop first as ref)     (J - 1)
        month dummies (drop k = -1 as ref)         (K - 1)
        interactions q x k for q in {2..5}, k != -1   (4 * (K - 1))
    """
    occ_codes = sorted(sub['yrke4'].unique())
    occ_to_idx = {c: i for i, c in enumerate(occ_codes)}
    J = len(occ_codes)

    ks = sorted(sub['k'].unique())
    k_to_idx = {k: i for i, k in enumerate(ks)}
    K = len(ks)
    if REF_K not in k_to_idx:
        raise ValueError(f'Reference k = {REF_K} not present in data')
    k_ref_idx = k_to_idx[REF_K]

    n = len(sub)
    rows = np.arange(n)
    occ_idx = sub['yrke4'].map(occ_to_idx).to_numpy()
    k_idx_arr = sub['k'].map(k_to_idx).to_numpy()
    q_arr = sub['ai_q'].to_numpy()

    # Intercept
    intercept = sp.csr_matrix(np.ones((n, 1)))

    # Occupation dummies, drop col 0 as reference
    occ_full = sp.coo_matrix((np.ones(n), (rows, occ_idx)),
                             shape=(n, J)).tocsr()
    occ_mat = occ_full[:, 1:]

    # Month dummies, drop reference k
    month_full = sp.coo_matrix((np.ones(n), (rows, k_idx_arr)),
                               shape=(n, K)).tocsr()
    keep_cols = [j for j in range(K) if j != k_ref_idx]
    month_mat = month_full[:, keep_cols]

    # Interaction blocks. Within-block col = k_idx with k_ref_idx removed.
    col_within_block = np.where(k_idx_arr < k_ref_idx,
                                k_idx_arr,
                                k_idx_arr - 1)
    int_blocks = []
    int_col_keys = []  # (q, k) tuples in same order as columns
    ks_nonref = [k for k in ks if k != REF_K]
    for q in QUINTILES:
        mask = (q_arr == q) & (k_idx_arr != k_ref_idx)
        rows_q = rows[mask]
        cols_q = col_within_block[mask]
        block = sp.coo_matrix((np.ones(mask.sum()), (rows_q, cols_q)),
                              shape=(n, K - 1)).tocsr()
        int_blocks.append(block)
        for k in ks_nonref:
            int_col_keys.append((q, k))
    int_mat = sp.hstack(int_blocks, format='csr')

    X = sp.hstack([intercept, occ_mat, month_mat, int_mat], format='csr')

    int_col_offset = 1 + (J - 1) + (K - 1)
    return X, int_col_offset, int_col_keys


# --- Fit and extract -------------------------------------------------------
def fit_one_age(sub: pd.DataFrame, age_bin: int) -> pd.DataFrame:
    """Fit Poisson with cluster-robust SE at yrke4; return interaction coefs."""
    print(f'  Age bin {age_bin} ({AGE_LABELS[age_bin]}): {len(sub):,} cells, '
          f'{sub["yrke4"].nunique()} occupations, '
          f'{sub["k"].nunique()} months')
    X, int_col_offset, int_col_keys = build_design(sub)
    y = sub['count'].to_numpy()
    groups = sub['yrke4'].to_numpy()

    model = sm.GLM(y, X.toarray(), family=sm.families.Poisson())
    res = model.fit(method='IRLS', tol=1e-7, maxiter=50,
                    cov_type='cluster',
                    cov_kwds={'groups': groups})

    rows = []
    for j, (q, k) in enumerate(int_col_keys):
        col = int_col_offset + j
        rows.append({'age_bin': age_bin, 'ai_q': q, 'k': k,
                     'coef': res.params[col], 'se': res.bse[col]})
    # Also write the reference row (k=-1, coef=0) so downstream plotting can
    # draw a line through k=-1 cleanly.
    for q in QUINTILES:
        rows.append({'age_bin': age_bin, 'ai_q': q, 'k': REF_K,
                     'coef': 0.0, 'se': 0.0})
    out = pd.DataFrame(rows).sort_values(['ai_q', 'k']).reset_index(drop=True)
    out['n_obs'] = len(sub)
    out['n_occ'] = sub['yrke4'].nunique()
    return out


# --- Plotting (6 age x 4 quintile grid) ------------------------------------
def plot_grid(coef: pd.DataFrame, out_path: Path) -> None:
    nrows, ncols = 6, 4
    fig, axes = plt.subplots(nrows, ncols, sharex=True, sharey=True,
                             figsize=(12.5, 17))

    for r, age_bin in enumerate(range(1, 7)):
        for c, q in enumerate(QUINTILES):
            ax = axes[r, c]
            d = coef[(coef['age_bin'] == age_bin) & (coef['ai_q'] == q)] \
                .sort_values('k')
            if len(d):
                ks = d['k'].to_numpy()
                # Convert to log-points x 100 (~ % change) for comparability
                coefs = d['coef'].to_numpy() * 100
                ses = d['se'].to_numpy() * 100
                lo = coefs - 1.96 * ses
                hi = coefs + 1.96 * ses

                ax.fill_between(ks, lo, hi, color='#2171B5',
                                alpha=0.20, linewidth=0)
                ax.plot(ks, coefs, color='#08306B', linewidth=1.4)

            ax.axhline(y=0, color='#444444', linestyle='-', linewidth=0.8)
            ax.axvline(x=REF_K, color='#555555', linestyle=':',
                       linewidth=0.8, alpha=0.7)
            ax.axvline(x=CHATGPT_K, color='red', linestyle='--',
                       linewidth=0.9, alpha=0.8)

            ax.set_xlim(*K_XLIM)
            ax.set_ylim(-20, 20)
            ax.set_xticks([k for k, _ in JANUARY_TICKS])
            ax.set_xticklabels([lab for _, lab in JANUARY_TICKS], fontsize=11)
            ax.tick_params(axis='y', labelsize=11)
            ax.yaxis.set_major_locator(plt.MultipleLocator(10))

            if r == 0:
                ax.set_title(f'Quintile {q}', fontsize=14)
            if c == 0:
                ax.set_ylabel(f'Ages {AGE_LABELS[age_bin]}', fontsize=13)

    fig.suptitle('Employment by AI-exposure quintile vs. Q1, by age cohort\n'
                 'cell-level event study, Poisson',
                 fontweight='semibold', y=0.995)
    fig.supylabel('Log-points x 100 (~ % change vs Q1, k = −1 reference)',
                  x=0.005, fontsize=14)

    note = (
        'Sample: cell-level microdata.no employment counts, 22–69-year-olds, '
        '2021m1–2026m2. Source: data/01_occ_agemonth_count_2021_2026.csv. '
        'Specification: Poisson GLM with occupation FE (yrke4), month FE, and '
        'quintile x event-time interactions (Q1 and k = −1 omitted), '
        'estimated separately per age bin. SE clustered at occupation. '
        'Aggregates over firms (microdata.no exports collapse the firm '
        'dimension), so this is the counterpart to the firm-FE estimator in '
        'Appendix C with the firm dimension removed --- the gamma_{q,k} '
        'coefficient combines within-firm reallocation and across-firm scale. '
        'Dashed red line: November 2022 (k = 0). Y-axis: gamma_{q,k} '
        '(log-points) x 100, approximately percent change in q employment '
        'relative to Q1 from October 2022 to event time k.'
    )
    fig.tight_layout(rect=(0.03, 0.06, 1, 0.97))
    place_note(fig, axes, note, y=0.045, fontsize=12)

    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out_path}')


# --- Main ------------------------------------------------------------------
def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    COEF_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    print('Loading panel ...')
    panel = load_panel()
    print(f'  panel: {len(panel):,} (yrke4, age_bin, k) rows, '
          f'{panel["yrke4"].nunique()} occupations, '
          f'{panel["k"].min()}..{panel["k"].max()} k range')

    all_coefs = []
    for age_bin in sorted(panel['age_bin'].unique()):
        sub = panel[panel['age_bin'] == age_bin].copy()
        sub = balance_panel(sub)
        coefs = fit_one_age(sub, age_bin)
        all_coefs.append(coefs)

    coef = pd.concat(all_coefs, ignore_index=True)
    coef_path = COEF_DIR / 'coef_microdata_poisson_es.csv'
    coef.to_csv(coef_path, index=False)
    print(f'Saved {coef_path}')

    plot_grid(coef, FIG_DIR / 'figure_microdata_poisson_es_grid.pdf')


if __name__ == '__main__':
    main()
