# Canaries By Exposure Results Data Dictionary

## Files Included

- `canaries_by_exposure_annualized.csv`: Annualized growth for all workers by exposure.
- `canaries_by_exposure_yoy_change.csv`: Year-over-year change for all workers by exposure.
- `canaries_by_exposure.csv`: Underlying Employment Index series for all workers by exposure.
- `canaries_by_exposure_data_dictionary.md`: Documentation for this package.

## Conventions

- Exposure quintile labels may appear as facet columns or value columns: `Quintile 1 (least exposed)`, `Quintile 2`, `Quintile 3`, `Quintile 4`, `Quintile 5 (most exposed)`.
- Age bucket labels may appear as facet columns or value columns: `Early Career 1 (22-25)`, `Early Career 2 (26-30)`, `Developing (31-34)`, `Mid-Career 1 (35-40)`, `Mid-Career 2 (41-49)`, `Senior (50+)`.
- The Canaries normalization date is `2022-11-01`.
- Annualized growth values are stored as signed decimal rates; multiply by 100 for percent text.
- Year-over-year change values are stored as signed decimal rates; multiply by 100 for percent text.

## `canaries_by_exposure_annualized.csv`

- Rows: 36

| Column | Type | Role | Units or transformation | Allowed values | Notes |
| --- | --- | --- | --- | --- | --- |
| `observation_date` | date | facet | First day of the observation month. | ISO date formatted as YYYY-MM-DD. | Monthly observation date. |
| `Quintile 1 (least exposed)` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `Quintile 1 (least exposed)`. |
| `Quintile 2` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `Quintile 2`. |
| `Quintile 3` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `Quintile 3`. |
| `Quintile 4` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `Quintile 4`. |
| `Quintile 5 (most exposed)` | number | value | Annualized percent change stored as a signed decimal rate; 0.02 means +2.0% per year. | Numeric or blank when unavailable. | Value column for `Quintile 5 (most exposed)`. |

Derivation notes:

- Annualized growth values are computed upstream from the corresponding normalized employment-index series.
- Values are not display-scaled in the CSV. Multiply by 100 to render percent text such as 2.0%.

## `canaries_by_exposure_yoy_change.csv`

- Rows: 48

| Column | Type | Role | Units or transformation | Allowed values | Notes |
| --- | --- | --- | --- | --- | --- |
| `observation_date` | date | facet | First day of the observation month. | ISO date formatted as YYYY-MM-DD. | Monthly observation date. |
| `Quintile 1 (least exposed)` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `Quintile 1 (least exposed)`. |
| `Quintile 2` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `Quintile 2`. |
| `Quintile 3` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `Quintile 3`. |
| `Quintile 4` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `Quintile 4`. |
| `Quintile 5 (most exposed)` | number | value | Year-over-year percent change stored as a signed decimal rate; 0.02 means +2.0% from the same month one year earlier. | Numeric or blank when unavailable. | Value column for `Quintile 5 (most exposed)`. |

Derivation notes:

- Year-over-year change values are computed upstream from the corresponding normalized employment-index series.
- Values are not display-scaled in the CSV. Multiply by 100 to render percent text such as 2.0%.

## `canaries_by_exposure.csv`

- Rows: 60

| Column | Type | Role | Units or transformation | Allowed values | Notes |
| --- | --- | --- | --- | --- | --- |
| `observation_date` | date | facet | First day of the observation month. | ISO date formatted as YYYY-MM-DD. | Monthly observation date. |
| `Quintile 1 (least exposed)` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `Quintile 1 (least exposed)`. |
| `Quintile 2` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `Quintile 2`. |
| `Quintile 3` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `Quintile 3`. |
| `Quintile 4` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `Quintile 4`. |
| `Quintile 5 (most exposed)` | number | value | Employment Index scaled by 100; 100 is the value at the 2022-11-01 normalization date for each series. | Numeric or blank when unavailable. | Value column for `Quintile 5 (most exposed)`. |
| `composition_E1` | number | value | Exposure composition share stored in percentage points; 7 means 7%. | Numeric or blank when unavailable. | Companion exposure-share column in the underlying series file. |
| `composition_E2` | number | value | Exposure composition share stored in percentage points; 7 means 7%. | Numeric or blank when unavailable. | Companion exposure-share column in the underlying series file. |
| `composition_E3` | number | value | Exposure composition share stored in percentage points; 7 means 7%. | Numeric or blank when unavailable. | Companion exposure-share column in the underlying series file. |
| `composition_E4` | number | value | Exposure composition share stored in percentage points; 7 means 7%. | Numeric or blank when unavailable. | Companion exposure-share column in the underlying series file. |
| `composition_E5` | number | value | Exposure composition share stored in percentage points; 7 means 7%. | Numeric or blank when unavailable. | Companion exposure-share column in the underlying series file. |

Derivation notes:

- The normalization date `2022-11-01` is indexed to 100 for each series.
- `composition_E*` columns are exposure composition shares stored in percentage points.
