"""
Build the automation-vs-augmentation grouping of STYRK-08 occupations
used for the exposure x usage heterogeneity analysis.

This is a decision layer on top of the measurement file
data/ai_exposure/styrk08_aei_collaboration.csv (one row per STYRK-08 x
platform x vintage, built by build_aei_collaboration_mapping.py on the
arbeidsmarkedet branch from the Anthropic Economic Index releases and
copied verbatim to main on 2026-08-26). The measurement file takes no
decisions; this script takes them, once, so the DiD scripts, tables,
dashboard packages and paper text read identical groups. Decisions, with
the evidence behind them documented in
data/ai_exposure/docs/styrk08_automation_groups_README.md:

  1. Platform: Claude.ai chat only. The API automation share does not
     separate occupations (interquartile range 0.84-1.00 in Feb 2026) and
     correlates 0.13-0.28 with the chat share.
  2. Vintages pooled: Aug 2025, Nov 2025 and Feb 2026, count-weighted
     (sum of automation conversations / sum of classified conversations).
     The Handa vintage (Dec 2024-Jan 2025) is kept only as a robustness
     column: it has no conversation counts, so it cannot be gated, and it
     comes from a different regime (chat-only, pre-agentic, directive
     share 27 percent against 39 percent by Aug 2025).
  3. Definition: Anthropic's rule, automation = directive + feedback loop.
     The directive-only variant used by build_handa_mapping.py and the
     dashboard's usage groups is carried as a separate column.
  4. Threshold: pooled n >= 100 classified chat conversations. Occupations
     below, or absent from the file altogether (no task above Anthropic's
     release floor of 15 conversations), get the group `too_few`.
     Precedents: Massenkoff & McCrory (2026) gate tasks at 100 work-related
     conversations; Brynjolfsson, Chandar & Chen (2025) keep occupations
     below the usage floor as a separate category coded 0.
  5. Groups: equal-occupation terciles of the pooled share among the
     occupations that pass the threshold (rank method 'first', ties
     broken by STYRK-08 code, the repo's quintile convention). Cutpoints
     are printed and written to the README.
  6. Universe: the 397 STYRK-08 codes with an Eloundou et al. (2024)
     score, i.e. the canaries sample the heterogeneity analysis runs on.

Robustness columns: Feb 2026 alone (gated at n >= 100 on the Feb count),
directive-only pooled share, and the Handa vintage (terciles among
covered codes, no gate possible).

Interpretation caveats (README, "Interpretation caveats"): the share is
conditional on the task still being used in the chat channel, so it
understates automation where it succeeds and migrates to API/agentic
surfaces; and it is a share of global Claude.ai conversations, not of
Norwegian working time.

Output: data/ai_exposure/styrk08_automation_groups.csv, one row per
STYRK-08 code in the universe.

Usage:
    python analysis/03_mappings/build_automation_groups.py
"""

from pathlib import Path                     # filesystem-path handling

import numpy as np                           # weighted averages
import pandas as pd                          # tabular work + qcut

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # repo root (3 levels up)
DATA_DIR = BASE_DIR / 'data' / 'ai_exposure'              # exposure-data folder

COLLAB_FILE = DATA_DIR / 'styrk08_aei_collaboration.csv'      # measurement panel
ELOUNDOU_FILE = DATA_DIR / 'styrk08_eloundou_beta_mapping.csv'  # universe + quintiles
EMPLOYMENT_FILE = (BASE_DIR / 'microdata-output'                # optional, for the
                   / '09_occ_agedecade_sektor_kpos_2021m01_2026m04_parsed.csv')  # coverage report
OUTPUT_FILE = DATA_DIR / 'styrk08_automation_groups.csv'      # output grouping

PLATFORM = 'claude_ai'                                   # decision 1
POOL_DATES = ['2025-08-04', '2025-11-13', '2026-02-05']  # decision 2
FEB_DATE = '2026-02-05'                                  # robustness: single vintage
HANDA_DATE = '2024-12-01'                                # robustness: original vintage
MIN_N = 100                                              # decision 4
GROUP_LABELS = ['low', 'mid', 'high']                    # decision 5
TOO_FEW = 'too_few'                                      # below threshold / absent


def terciles(share: pd.Series) -> pd.Series:
    """Equal-occupation terciles, ties broken by the (sorted) index."""
    # Rank with method='first' so ties break by STYRK-08 sort order.
    ranks = share.sort_index().rank(method='first')
    # Cut the ranks into three equal groups labelled low / mid / high.
    return pd.qcut(ranks, 3, labels=GROUP_LABELS).astype(str).reindex(share.index)


def cutpoints(share: pd.Series) -> tuple[float, float]:
    """The share values at the tercile boundaries (for documentation)."""
    return float(share.quantile(1 / 3)), float(share.quantile(2 / 3))


def pooled(df: pd.DataFrame, col: str) -> pd.Series:
    """Count-weighted pooled share of `col` over the vintages in `df`."""
    # Weighted numerator: share x count, summed over vintages.
    num = (df[col] * df['n_classified']).groupby(df['styrk08']).sum()
    # Denominator: total classified conversations over the vintages.
    den = df.groupby('styrk08')['n_classified'].sum()
    return num / den


def main() -> None:
    # ---- Load inputs -----------------------------------------------------
    c = pd.read_csv(COLLAB_FILE, dtype={'styrk08': str})
    c['styrk08'] = c['styrk08'].str.zfill(4)
    chat = c[c['platform'] == PLATFORM]

    el = pd.read_csv(ELOUNDOU_FILE, dtype={'styrk08': str})
    el = el[el['quintile'].notna()].copy()
    el['styrk08'] = el['styrk08'].str.zfill(4)
    universe = el.set_index('styrk08')['quintile'].astype(int).sort_index()
    print(f'Universe: {len(universe)} STYRK-08 codes with an Eloundou score')

    # ---- Decision 2: pool the three counted vintages ---------------------
    pool = chat[chat['date_start'].isin(POOL_DATES)]
    out = pd.DataFrame(index=universe.index)
    out['automation_share'] = pooled(pool, 'automation_share').reindex(out.index)
    out['directive_share'] = pooled(pool, 'directive_share').reindex(out.index)
    out['n_classified'] = pool.groupby('styrk08')['n_classified'].sum().reindex(out.index).fillna(0).astype(int)
    out['n_vintages'] = pool.groupby('styrk08').size().reindex(out.index).fillna(0).astype(int)
    out['usage_pct_mean'] = pool.groupby('styrk08')['usage_pct'].mean().reindex(out.index)

    # ---- Decision 4: threshold -------------------------------------------
    out['passes_threshold'] = (out['n_classified'] >= MIN_N).astype(int)

    # ---- Decision 5: terciles on the gated sample ------------------------
    gated = out.loc[out['passes_threshold'] == 1, 'automation_share']
    out['automation_group'] = TOO_FEW
    out.loc[gated.index, 'automation_group'] = terciles(gated)
    lo, hi = cutpoints(gated)
    print(f'Pooled chat, n >= {MIN_N}: {len(gated)} codes grouped, '
          f'{(out["automation_group"] == TOO_FEW).sum()} too_few; '
          f'tercile cutpoints {lo:.3f} / {hi:.3f}')

    # Directive-only variant, same gate, own terciles.
    gated_d = out.loc[out['passes_threshold'] == 1, 'directive_share']
    out['directive_group'] = TOO_FEW
    out.loc[gated_d.index, 'directive_group'] = terciles(gated_d)
    lo_d, hi_d = cutpoints(gated_d)
    print(f'Directive-only variant: cutpoints {lo_d:.3f} / {hi_d:.3f}')

    # ---- Robustness: Feb 2026 alone --------------------------------------
    feb = chat[chat['date_start'] == FEB_DATE].set_index('styrk08')
    out['automation_share_feb'] = feb['automation_share'].reindex(out.index)
    out['n_feb'] = feb['n_classified'].reindex(out.index).fillna(0).astype(int)
    gated_f = out.loc[out['n_feb'] >= MIN_N, 'automation_share_feb']
    out['automation_group_feb'] = TOO_FEW
    out.loc[gated_f.index, 'automation_group_feb'] = terciles(gated_f)
    lo_f, hi_f = cutpoints(gated_f)
    print(f'Feb 2026 alone, n >= {MIN_N}: {len(gated_f)} codes grouped; '
          f'cutpoints {lo_f:.3f} / {hi_f:.3f}')

    # ---- Robustness: Handa vintage (no counts, no gate) ------------------
    handa = chat[chat['date_start'] == HANDA_DATE].set_index('styrk08')
    out['automation_share_handa'] = handa['automation_share'].reindex(out.index)
    covered = out['automation_share_handa'].dropna()
    out['automation_group_handa'] = TOO_FEW
    out.loc[covered.index, 'automation_group_handa'] = terciles(covered)
    lo_h, hi_h = cutpoints(covered)
    print(f'Handa vintage, no gate: {len(covered)} codes grouped; '
          f'cutpoints {lo_h:.3f} / {hi_h:.3f}')

    # ---- Coverage report by Eloundou quintile ----------------------------
    rep = pd.DataFrame({'quintile': universe, 'group': out['automation_group']})
    tab = pd.crosstab(rep['quintile'], rep['group'])[GROUP_LABELS + [TOO_FEW]]
    print('\nGroups by Eloundou quintile (codes):')
    print(tab.to_string())
    agree = (out.loc[out['automation_group'] != TOO_FEW, 'automation_group']
             == out.loc[out['automation_group'] != TOO_FEW, 'automation_group_feb']).mean()
    print(f'\nShare of pooled-grouped codes with the same group in Feb-only: {agree:.2f}')

    # Employment coverage, only if the register aggregates are present.
    if EMPLOYMENT_FILE.exists():
        emp = pd.read_csv(EMPLOYMENT_FILE, dtype={'yrke4': str, 'alder_gr': str})
        month = emp['date'].max()
        emp = emp[(emp['variable'] == 'count') & (emp['date'] == month)
                  & (emp['alder_gr'].isin(['1', '2', '3', '4']))]
        emp = emp.groupby('yrke4')['value'].sum().reindex(out.index).fillna(0)
        share = emp[out['automation_group'] != TOO_FEW].sum() / emp.sum()
        print(f'Employment share (21-60, both sectors, {month}) '
              f'in grouped codes: {share:.2f}')
        by_q = (emp[out['automation_group'] != TOO_FEW].groupby(universe).sum()
                / emp.groupby(universe).sum()).round(2)
        print('By Eloundou quintile:', by_q.to_dict())

    # ---- Save ------------------------------------------------------------
    out = out.reset_index()
    out['automation_share'] = out['automation_share'].round(4)
    out['directive_share'] = out['directive_share'].round(4)
    out['usage_pct_mean'] = out['usage_pct_mean'].round(4)
    out['automation_share_feb'] = out['automation_share_feb'].round(4)
    out['automation_share_handa'] = out['automation_share_handa'].round(4)
    out = out[['styrk08', 'automation_share', 'n_classified', 'n_vintages',
               'usage_pct_mean', 'passes_threshold', 'automation_group',
               'directive_share', 'directive_group',
               'automation_share_feb', 'n_feb', 'automation_group_feb',
               'automation_share_handa', 'automation_group_handa']]
    out.to_csv(OUTPUT_FILE, index=False, lineterminator='\n')
    print(f'\nSaved to {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
