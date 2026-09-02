# canaries_no_wages_occupations Data Dictionary

## Files Included

- `canaries_no_wages_occupations.csv`: Underlying series.
- `canaries_no_wages_occupations_yoy_change.csv`: Year-over-year change.
- `canaries_no_wages_occupations_annualized.csv`: Annualized growth.
- `canaries_no_wages_occupations_data_dictionary.md`: Documentation.

## Conventions

- Norwegian counterpart to the Stanford/ADP Canaries Dashboard data
  packages, built from Norwegian register data (A-ordningen via
  microdata.no): the full population of private-sector employees,
  all ages 21-60 pooled, monthly from 2021-01.
- The series is the FTE-adjusted average monthly cash wage of the
  group: sum(count x mean cash wage) / sum(count x mean contractual
  FTE share) over the occupation-by-age cells in the group, where
  cash wage is ARBLONN_LONN_KONTANT_IMP and the FTE share is
  ARBLONN_ARB_STILLINGSPST / 100. Each cell's average stillingsprosent
  thus weights its wage up to a full-time-equivalent level. The
  normalization date is `2022-11-01`; the Wage Index is 100 at that
  date for each series.
- Caveat: the FTE adjustment corrects for part-time work but not for
  partial first-month pay among new hires; that effect is small and
  seasonally stable.
- `observation_date` is the first day of the observation month. The
  underlying register reference is the week containing the 16th.
- The sample is every 4-digit STYRK-08 (= ISCO-08) occupation code with
  at least 30 private-sector employees aged 21-60 in every month from
  2021-01 (single codes, unlike the grouped occupation cases; not
  restricted to the canaries sample). `exposure_quintile` carries the
  national Eloundou et al. (2024) quintile where the code has a score
  and is empty where it does not.
- Time-series files carry an `adjustment` facet column with the values
  `raw` (FTE-adjusted wage, not seasonally adjusted) and `sa`
  (seasonally adjusted; X-11 core with factors estimated 2021-2024 and
  frozen). The per-capita variants are not meaningful for wages and
  are not published.
- Annualized growth: (index/100)^(12/k) - 1, k = months since 2022-11,
  published from k = 6. Year-over-year: index_t/index_(t-12) - 1.
  Both stored as signed decimal rates. Wage indices are nominal; no
  deflation is applied.

Value column: Wage Index per 4-digit occupation. Long-format package behind the occupation selector: facets `styrk08` and `occupation` (Norwegian STYRK-08 name). `n_base` is the occupation's headcount at the normalization date and `exposure_quintile` its Eloundou quintile (empty when the code lacks a score); both are constant within occupation. Small occupations are noisy, and the composition of workers within an occupation can change over time.
