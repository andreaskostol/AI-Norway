# Canaries Anthropic Usage Patterns by Age Results Data Dictionary

## Files Included

- `canaries_anthropic_usage_patterns_by_age.csv`: Underlying Employment Index series for Anthropic usage patterns by age.
- `canaries_anthropic_usage_patterns_by_age_annualized.csv`: Annualized growth for Anthropic usage patterns by age.
- `canaries_anthropic_usage_patterns_by_age_yoy_change.csv`: Year-over-year change for Anthropic usage patterns by age.
- `canaries_anthropic_usage_patterns_by_age_data_dictionary.md`: Documentation for this package.

## Conventions

- Exposure quintile labels may appear as facet columns or value columns: `Quintile 1 (least exposed)`, `Quintile 2`, `Quintile 3`, `Quintile 4`, `Quintile 5 (most exposed)`.
- Age bucket labels may appear as facet columns or value columns: `Early Career 1 (22-25)`, `Early Career 2 (26-30)`, `Developing (31-34)`, `Mid-Career 1 (35-40)`, `Mid-Career 2 (41-49)`, `Senior (50+)`.
- The Canaries normalization date is `2022-11-01`.
- Annualized growth values are stored as signed decimal rates; multiply by 100 for percent text.
- Year-over-year change values are stored as signed decimal rates; multiply by 100 for percent text.

## `canaries_anthropic_usage_patterns_by_age.csv`

- Rows: 840

| Column | Type | Role | Units or transformation | Allowed values | Notes |
| --- | --- | --- | --- | --- | --- |
| `observation_date` | date | facet | First day of the observation month. | ISO date formatted as YYYY-MM-DD. | Monthly observation date. |
| `usage_pattern` | string | facet | Anthropic usage measure. | `Augmentation`, `Automation` | Separates augmentation-ratio and automation-ratio series. |
| `age_bucket` | string | facet | Worker age bucket label. | `Early Career 1 (22-25)`, `Early Career 2 (26-30)`, `Developing (31-34)`, `Mid-Career 1 (35-40)`, `Mid-Career 2 (41-49)`, `Senior (50+)`, `All ages` | Age bucket, including a pooled all-age row for each Anthropic usage measure. |
| `No usage` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `No usage`. |
| `Quintile 1 (least usage)` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `Quintile 1 (least usage)`. |
| `Quintile 2` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `Quintile 2`. |
| `Quintile 3` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `Quintile 3`. |
| `Quintile 4` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `Quintile 4`. |
| `Quintile 5 (most usage)` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `Quintile 5 (most usage)`. |

Derivation notes:

- The normalization date `2022-11-01` is indexed to 100 for each series.

## `canaries_anthropic_usage_patterns_by_age_annualized.csv`

- Rows: 504

| Column | Type | Role | Units or transformation | Allowed values | Notes |
| --- | --- | --- | --- | --- | --- |
| `observation_date` | date | facet | First day of the observation month. | ISO date formatted as YYYY-MM-DD. | Monthly observation date. |
| `usage_pattern` | string | facet | Anthropic usage measure. | `Augmentation`, `Automation` | Separates augmentation-ratio and automation-ratio series. |
| `age_bucket` | string | facet | Worker age bucket label. | `Early Career 1 (22-25)`, `Early Career 2 (26-30)`, `Developing (31-34)`, `Mid-Career 1 (35-40)`, `Mid-Career 2 (41-49)`, `Senior (50+)`, `All ages` | Age bucket, including a pooled all-age row for each Anthropic usage measure. |
| `No usage` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `No usage`. |
| `Quintile 1 (least usage)` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `Quintile 1 (least usage)`. |
| `Quintile 2` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `Quintile 2`. |
| `Quintile 3` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `Quintile 3`. |
| `Quintile 4` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `Quintile 4`. |
| `Quintile 5 (most usage)` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `Quintile 5 (most usage)`. |

Derivation notes:

- Annualized growth values are computed upstream from the corresponding normalized employment-index series.
- Values are not display-scaled in the CSV. Multiply by 100 to render percent text such as 2.0%.

## `canaries_anthropic_usage_patterns_by_age_yoy_change.csv`

- Rows: 672

| Column | Type | Role | Units or transformation | Allowed values | Notes |
| --- | --- | --- | --- | --- | --- |
| `observation_date` | date | facet | First day of the observation month. | ISO date formatted as YYYY-MM-DD. | Monthly observation date. |
| `usage_pattern` | string | facet | Anthropic usage measure. | `Augmentation`, `Automation` | Separates augmentation-ratio and automation-ratio series. |
| `age_bucket` | string | facet | Worker age bucket label. | `Early Career 1 (22-25)`, `Early Career 2 (26-30)`, `Developing (31-34)`, `Mid-Career 1 (35-40)`, `Mid-Career 2 (41-49)`, `Senior (50+)`, `All ages` | Age bucket, including a pooled all-age row for each Anthropic usage measure. |
| `No usage` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `No usage`. |
| `Quintile 1 (least usage)` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `Quintile 1 (least usage)`. |
| `Quintile 2` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `Quintile 2`. |
| `Quintile 3` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `Quintile 3`. |
| `Quintile 4` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `Quintile 4`. |
| `Quintile 5 (most usage)` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `Quintile 5 (most usage)`. |

Derivation notes:

- Year-over-year change values are computed upstream from the corresponding normalized employment-index series.
- Values are not display-scaled in the CSV. Multiply by 100 to render percent text such as 2.0%.
