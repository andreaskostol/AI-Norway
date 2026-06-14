# Canaries Age by Anthropic Augmentation Ratio Composition Results Data Dictionary

## Files Included

- `canaries_anthropic_usage_augmentation_ratio_composition.csv`: Composition share snapshot for canaries anthropic usage augmentation ratio composition.
- `canaries_anthropic_usage_augmentation_ratio_composition_data_dictionary.md`: Documentation for this package.

## Conventions

- Exposure quintile labels may appear as facet columns or value columns: `Quintile 1 (least exposed)`, `Quintile 2`, `Quintile 3`, `Quintile 4`, `Quintile 5 (most exposed)`.
- Age bucket labels may appear as facet columns or value columns: `Early Career 1 (22-25)`, `Early Career 2 (26-30)`, `Developing (31-34)`, `Mid-Career 1 (35-40)`, `Mid-Career 2 (41-49)`, `Senior (50+)`.
- The Canaries normalization date is `2022-11-01`.
- Annualized growth values are stored as signed decimal rates; multiply by 100 for percent text.
- Year-over-year change values are stored as signed decimal rates; multiply by 100 for percent text.

## `canaries_anthropic_usage_augmentation_ratio_composition.csv`

- Rows: 36

| Column | Type | Role | Units or transformation | Allowed values | Notes |
| --- | --- | --- | --- | --- | --- |
| `observation_date` | date | facet | First day of the observation month. | ISO date formatted as YYYY-MM-DD. | Monthly observation date. |
| `Age Group` | string | facet | Worker age bucket label. | `Early Career 1 (22-25)`, `Early Career 2 (26-30)`, `Developing (31-34)`, `Mid-Career 1 (35-40)`, `Mid-Career 2 (41-49)`, `Senior (50+)` | Age bucket for composition share rows. |
| `Share` | number | value | Employment share stored in percentage points; 1.5 means 1.5%. | Numeric or blank when unavailable. | Share for the age-by-exposure composition cell. |
| `Usage Group` | string | value | Product-specific value. | See package documentation. | No additional column-specific metadata is configured. |

Derivation notes:

- Composition values are a `2022-11-01` snapshot; shares are stored as decimals.
