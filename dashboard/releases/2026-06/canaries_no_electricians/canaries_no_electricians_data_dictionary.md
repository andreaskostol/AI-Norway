# canaries_no_electricians Data Dictionary

## Files Included

- `canaries_no_electricians.csv`: Underlying series.
- `canaries_no_electricians_yoy_change.csv`: Year-over-year change.
- `canaries_no_electricians_annualized.csv`: Annualized growth.
- `canaries_no_electricians_data_dictionary.md`: Documentation.
- `figure_canaries_style_occupations_q1_health.pdf`: 4x4 figure
  (occupations x adjustment variants) showing electricians together
  with three health occupations (health care assistants 5321, social
  educators 2224, nurses 2223). Private sector, like the CSV files.
  Note that the public sector dominates the health occupations, so
  those rows cover only the private segment of each occupation.
  Source: analysis/06_figures/plot_canaries_style_occupations.py.

## Conventions

- Norwegian counterpart to the Stanford/ADP Canaries Dashboard data
  packages, built from Norwegian register data (A-ordningen via
  microdata.no): the full population of private-sector employees,
  decade age groups 21-30, 31-40, 41-50, 51-60, monthly from 2021-01.
- The Canaries normalization date is `2022-11-01`; the Employment Index
  is 100 at that date for each series.
- `observation_date` is the first day of the observation month. The
  underlying register reference is the week containing the 16th.
- The canaries sample is the 397 STYRK-08 (= ISCO-08) occupation codes
  with an Eloundou et al. (2024) exposure score, quintiles
  equal-weighted by occupation.
- Time-series files carry an `adjustment` facet column not present in
  the Stanford files: `raw` (headcount, Stanford's method), `sa`
  (seasonally adjusted; X-11 core with factors estimated 2021-2024 and
  frozen), `percap` (headcount divided by the resident population of
  the age group, Statistics Norway table 07459), `percap_sa` (both).
  The `raw` rows alone reproduce the Stanford schema.
- Annualized growth: (index/100)^(12/k) - 1, k = months since 2022-11,
  published from k = 6. Year-over-year: index_t/index_(t-12) - 1.
  Both stored as signed decimal rates.

Value columns: Employment Index per decade age group for STYRK-08 7411. Per capita divides by the age group's total resident population.
