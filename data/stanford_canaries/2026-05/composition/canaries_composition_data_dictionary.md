# Canaries Age by Exposure Composition Results Data Dictionary

## Files Included

- `canaries_composition.csv`: Composition share snapshot for age by exposure composition.
- `canaries_composition_data_dictionary.md`: Documentation for this package.

## Conventions

- Exposure quintile labels may appear as facet columns or value columns: `Quintile 1 (least exposed)`, `Quintile 2`, `Quintile 3`, `Quintile 4`, `Quintile 5 (most exposed)`.
- Age bucket labels may appear as facet columns or value columns: `Early Career 1 (22-25)`, `Early Career 2 (26-30)`, `Developing (31-34)`, `Mid-Career 1 (35-40)`, `Mid-Career 2 (41-49)`, `Senior (50+)`.
- The Canaries normalization date is `2022-11-01`.
- Annualized growth values are stored as signed decimal rates; multiply by 100 for percent text.
- Year-over-year change values are stored as signed decimal rates; multiply by 100 for percent text.

## `canaries_composition.csv`

- Rows: 30

| Column | Type | Role | Units or transformation | Allowed values | Notes |
| --- | --- | --- | --- | --- | --- |
| `observation_date` | date | facet | First day of the observation month. | ISO date formatted as YYYY-MM-DD. | Monthly observation date. |
| `Age Group` | string | facet | Worker age bucket label. | `Early Career 1 (22-25)`, `Early Career 2 (26-30)`, `Developing (31-34)`, `Mid-Career 1 (35-40)`, `Mid-Career 2 (41-49)`, `Senior (50+)` | Age bucket for composition share rows. |
| `Share` | number | value | Employment share stored in percentage points; 1.5 means 1.5%. | Numeric or blank when unavailable. | Share for the age-by-exposure composition cell. |
| `Exposure Group` | string | facet | Occupational AI exposure quintile label. | `Quintile 1 (least exposed)`, `Quintile 2`, `Quintile 3`, `Quintile 4`, `Quintile 5 (most exposed)` | Exposure quintile for composition share rows. |

Derivation notes:

- Composition values are a `2022-11-01` snapshot; shares are stored in percentage points.
