"""
build_combined_styrk_exposure.py

Purpose: Build a single wide-format CSV with all 4-digit STYRK-08 occupation
    codes and one column per AI-exposure measure (Eloundou beta, Felten AIOE,
    Handa overall/automation/augmentation, Anthropic-2026 job exposure, and the
    relational axis), plus a derived exposure x relational interaction and a 2x2
    quadrant. This is the master occupation -> AI-exposure crosswalk: it gathers
    every per-measure mapping into one table and supplies the per-occupation
    quintile columns the figures and tables key on, and is the file shared with
    collaborators.

Inputs:  data/ai_exposure/styrk08_codes.csv               (master code list)
         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
         data/ai_exposure/styrk08_felten_mapping.csv
         data/ai_exposure/styrk08_handa_mapping.csv
         data/ai_exposure/styrk08_job_exposure_mapping.csv  (Anthropic 2026)
         data/ai_exposure/styrk08_relational_mapping.csv

Output:  data/ai_exposure/styrk08_all_exposure_measures.csv

Usage:   python analysis/03_mappings/build_combined_styrk_exposure.py
"""

from pathlib import Path                          # filesystem-path handling

import pandas as pd                               # tabular data / CSV I/O

BASE = Path(__file__).resolve().parent.parent.parent  # repo root (this file is 3 levels deep)
DATA = BASE / 'data' / 'ai_exposure'              # directory holding all the mapping CSVs
OUT = DATA / 'styrk08_all_exposure_measures.csv'  # combined wide-format output path


def four_digit_codes() -> pd.DataFrame:
    # Read the master STYRK-08 code list (latin-1 encoded, all columns as strings).
    df = pd.read_csv(DATA / 'styrk08_codes.csv', encoding='latin-1', dtype=str)
    # Keep only the 4-digit (level 4) codes and their names.
    df = df[df['level'] == '4'][['code', 'name']].copy()
    # Zero-pad codes to 4 digits so leading-zero codes (e.g. "0110") survive.
    df['code'] = df['code'].str.zfill(4)
    # Rename to the canonical join key and label columns.
    df = df.rename(columns={'code': 'styrk08', 'name': 'styrk08_name'})
    # Return sorted by code with a clean 0..N index.
    return df.sort_values('styrk08').reset_index(drop=True)


def load_eloundou() -> pd.DataFrame:
    # Read the Eloundou beta mapping (styrk08 as string).
    df = pd.read_csv(DATA / 'styrk08_eloundou_beta_mapping.csv', dtype={'styrk08': str})
    # Zero-pad the join key to 4 digits.
    df['styrk08'] = df['styrk08'].str.zfill(4)
    # Keep the score and quintile; rename the generic 'quintile' to a measure-specific name.
    return df[['styrk08', 'eloundou_beta', 'quintile']].rename(
        columns={'quintile': 'eloundou_q'})


def load_felten() -> pd.DataFrame:
    # Read the Felten AIOE mapping (styrk08 as string).
    df = pd.read_csv(DATA / 'styrk08_felten_mapping.csv', dtype={'styrk08': str})
    # Zero-pad the join key to 4 digits.
    df['styrk08'] = df['styrk08'].str.zfill(4)
    # Keep AIOE score/quintile plus the labour-market-weighted variant, renamed per-measure.
    return df[['styrk08', 'aioe', 'q_aioe', 'aioe_lm', 'q_aioe_lm']].rename(
        columns={'aioe': 'felten_aioe',
                 'q_aioe': 'felten_q',
                 'aioe_lm': 'felten_aioe_lm',
                 'q_aioe_lm': 'felten_lm_q'})


def load_handa() -> pd.DataFrame:
    # Read the Handa et al. mapping (styrk08 as string).
    df = pd.read_csv(DATA / 'styrk08_handa_mapping.csv', dtype={'styrk08': str})
    # Zero-pad the join key to 4 digits.
    df['styrk08'] = df['styrk08'].str.zfill(4)
    # Keep overall/automation/augmentation scores and their quintiles, renamed per-measure.
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
    # Read the Anthropic-2026 observed job-exposure mapping (styrk08 as string).
    df = pd.read_csv(DATA / 'styrk08_job_exposure_mapping.csv', dtype={'styrk08': str})
    # Zero-pad the join key to 4 digits.
    df['styrk08'] = df['styrk08'].str.zfill(4)
    # Keep the observed exposure and quintile, renamed per-measure.
    return df[['styrk08', 'observed_exposure', 'quintile']].rename(
        columns={'observed_exposure': 'anthropic2026_job_exposure',
                 'quintile': 'anthropic2026_q'})


def load_relational() -> pd.DataFrame:
    # Read the relational-axis mapping (styrk08 as string).
    df = pd.read_csv(DATA / 'styrk08_relational_mapping.csv', dtype={'styrk08': str})
    # Zero-pad the join key to 4 digits.
    df['styrk08'] = df['styrk08'].str.zfill(4)
    # Keep the relational score and quintile, renaming the generic 'quintile'.
    return df[['styrk08', 'relational', 'quintile']].rename(
        columns={'quintile': 'relational_q'})


def add_relational_quadrant(out: pd.DataFrame) -> pd.DataFrame:
    """Derive the exposure x relational interaction + 2x2 quadrant.

    Exposure axis is the canonical ensemble of the repo's own measures
    (z-mean of Felten AIOE + Eloundou beta) — the relational mapping contributes
    only the relational axis. See relational-economy/INTEGRATION_PLAN.md §2.
    """
    # Helper: standardise a column to z-scores (population sd, NaN-safe).
    def z(s):
        # Coerce to numeric, turning non-numeric entries into NaN.
        s = pd.to_numeric(s, errors='coerce')
        # Subtract the mean and divide by the population standard deviation.
        return (s - s.mean()) / s.std(ddof=0)

    # Exposure axis = the average of the z-scored Felten AIOE and Eloundou beta.
    out['ai_exposure_z'] = pd.concat(
        [z(out['felten_aioe']), z(out['eloundou_beta'])], axis=1).mean(axis=1, skipna=True)
    # Relational axis = the z-scored relational score.
    out['relational_z'] = z(out['relational'])
    # Interaction term = product of the two standardised axes.
    out['exposure_relational_interaction'] = out['ai_exposure_z'] * out['relational_z']

    # Mask of occupations that have both axes defined (needed for medians and quadrant).
    both = out['ai_exposure_z'].notna() & out['relational_z'].notna()
    # Median exposure among occupations with both axes (the 2x2 split point).
    ai_med = out.loc[both, 'ai_exposure_z'].median()
    # Median relational score among the same occupations.
    rel_med = out.loc[both, 'relational_z'].median()

    # Helper: assign one occupation to a quadrant based on the two medians.
    def quad(r):
        # Leave blank if either axis is missing for this occupation.
        if pd.isna(r['ai_exposure_z']) or pd.isna(r['relational_z']):
            return ''
        # High vs low exposure relative to the median.
        hi_ai = r['ai_exposure_z'] >= ai_med
        # High vs low relational score relative to the median.
        hi_rel = r['relational_z'] >= rel_med
        # Name the quadrant from the (exposure, relational) high/low combination.
        return ('exposed_relational' if hi_ai and hi_rel else
                'exposed_transactional' if hi_ai and not hi_rel else
                'shielded_relational' if not hi_ai and hi_rel else
                'shielded_transactional')

    # Apply the quadrant rule row by row.
    out['quadrant'] = out.apply(quad, axis=1)
    # Return the augmented table.
    return out


def main() -> None:
    # Start from the full list of 4-digit codes (the row backbone).
    base = four_digit_codes()
    # Left-join each per-measure mapping onto the backbone so every code is kept.
    out = (base
           .merge(load_eloundou(), on='styrk08', how='left')
           .merge(load_felten(), on='styrk08', how='left')
           .merge(load_handa(), on='styrk08', how='left')
           .merge(load_anthropic2026(), on='styrk08', how='left')
           .merge(load_relational(), on='styrk08', how='left'))

    # Add the derived exposure x relational interaction and the 2x2 quadrant.
    out = add_relational_quadrant(out)

    # Write the combined wide table to disk (no row index, UTF-8).
    out.to_csv(OUT, index=False, encoding='utf-8')

    # Total number of occupation rows (for the coverage report).
    n = len(out)
    # Report the output file and row count.
    print(f'Wrote {OUT.name}: {n} STYRK-08 4-digit codes')
    # For each core measure, report how many codes received a (non-missing) value.
    for col in ['eloundou_beta', 'felten_aioe', 'handa_overall',
                'anthropic2026_job_exposure', 'relational']:
        # Count non-missing values for this measure.
        cov = out[col].notna().sum()
        # Print count and percentage coverage.
        print(f'  {col:30} {cov:>4} / {n} mapped ({100*cov/n:5.1f} %)')

    # Quadrant labels with the blanks dropped (only fully-classified occupations).
    q = out['quadrant'].replace('', pd.NA).dropna()
    # Report how many occupations got a quadrant.
    print(f'  quadrant assigned: {len(q)} / {n}')
    # Break down the quadrant counts by label.
    for label, cnt in q.value_counts().items():
        # Print one line per quadrant label and its count.
        print(f'    {label:24} {cnt}')


if __name__ == '__main__':
    # Run the build when executed as a script.
    main()
