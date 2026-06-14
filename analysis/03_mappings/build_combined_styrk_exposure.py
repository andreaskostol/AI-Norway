"""
Build a single wide-format CSV with all 4-digit STYRK-08 codes and one column
per AI exposure measure, for sharing with collaborators.

Output: data/ai_exposure/styrk08_all_exposure_measures.csv
"""

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent.parent
DATA = BASE / 'data' / 'ai_exposure'
OUT = DATA / 'styrk08_all_exposure_measures.csv'


def four_digit_codes() -> pd.DataFrame:
    df = pd.read_csv(DATA / 'styrk08_codes.csv', encoding='latin-1', dtype=str)
    df = df[df['level'] == '4'][['code', 'name']].copy()
    df['code'] = df['code'].str.zfill(4)
    df = df.rename(columns={'code': 'styrk08', 'name': 'styrk08_name'})
    return df.sort_values('styrk08').reset_index(drop=True)


def load_eloundou() -> pd.DataFrame:
    df = pd.read_csv(DATA / 'styrk08_eloundou_beta_mapping.csv', dtype={'styrk08': str})
    df['styrk08'] = df['styrk08'].str.zfill(4)
    return df[['styrk08', 'eloundou_beta', 'quintile']].rename(
        columns={'quintile': 'eloundou_q'})


def load_felten() -> pd.DataFrame:
    df = pd.read_csv(DATA / 'styrk08_felten_mapping.csv', dtype={'styrk08': str})
    df['styrk08'] = df['styrk08'].str.zfill(4)
    return df[['styrk08', 'aioe', 'q_aioe', 'aioe_lm', 'q_aioe_lm']].rename(
        columns={'aioe': 'felten_aioe',
                 'q_aioe': 'felten_q',
                 'aioe_lm': 'felten_aioe_lm',
                 'q_aioe_lm': 'felten_lm_q'})


def load_handa() -> pd.DataFrame:
    df = pd.read_csv(DATA / 'styrk08_handa_mapping.csv', dtype={'styrk08': str})
    df['styrk08'] = df['styrk08'].str.zfill(4)
    return df[['styrk08',
               'overall_exposure', 'q_overall_exposure',
               'automation_share', 'q_automation_share',
               'augmentation_share', 'q_augmentation_share']].rename(
        columns={'overall_exposure': 'handa_overall',
                 'q_overall_exposure': 'handa_overall_q',
                 'automation_share': 'handa_automation',
                 'q_automation_share': 'handa_automation_q',
                 'augmentation_share': 'handa_augmentation',
                 'q_augmentation_share': 'handa_augmentation_q'})


def load_anthropic2026() -> pd.DataFrame:
    df = pd.read_csv(DATA / 'styrk08_job_exposure_mapping.csv', dtype={'styrk08': str})
    df['styrk08'] = df['styrk08'].str.zfill(4)
    return df[['styrk08', 'observed_exposure', 'quintile']].rename(
        columns={'observed_exposure': 'anthropic2026_job_exposure',
                 'quintile': 'anthropic2026_q'})


def main() -> None:
    base = four_digit_codes()
    out = (base
           .merge(load_eloundou(), on='styrk08', how='left')
           .merge(load_felten(), on='styrk08', how='left')
           .merge(load_handa(), on='styrk08', how='left')
           .merge(load_anthropic2026(), on='styrk08', how='left'))

    out.to_csv(OUT, index=False, encoding='utf-8')

    n = len(out)
    print(f'Wrote {OUT.name}: {n} STYRK-08 4-digit codes')
    for col in ['eloundou_beta', 'felten_aioe', 'handa_overall',
                'anthropic2026_job_exposure']:
        cov = out[col].notna().sum()
        print(f'  {col:30} {cov:>4} / {n} mapped ({100*cov/n:5.1f} %)')


if __name__ == '__main__':
    main()
