# canaries_no_mouchel_wages_by_exposure Data Dictionary

## Files Included

- `canaries_no_mouchel_wages_by_exposure.csv`: Underlying series.
- `canaries_no_mouchel_wages_by_exposure_yoy_change.csv`: Year-over-year change.
- `canaries_no_mouchel_wages_by_exposure_annualized.csv`: Annualized growth.
- `canaries_no_mouchel_wages_by_exposure_data_dictionary.md`: Documentation.

## Conventions

- Norwegian counterpart to the Stanford/ADP Canaries Dashboard data
  packages, built from Norwegian register data (A-ordningen via
  microdata.no): the full population of private-sector employees,
  decade age groups 21-30, 31-40, 41-50, 51-60, monthly from 2021-01.
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
- The canaries sample is the 397 STYRK-08 (= ISCO-08) occupation codes
  with an Eloundou et al. (2024) exposure score. In this package the
  quintiles are instead assigned from the Mouchel et al. (2026)
  evidence-grounded exposure measure, equal-frequency over the same
  occupations.
- Time-series files carry an `adjustment` facet column with the values
  `raw` (FTE-adjusted wage, not seasonally adjusted) and `sa`
  (seasonally adjusted; X-11 core with factors estimated 2021-2024 and
  frozen). The per-capita variants are not meaningful for wages and
  are not published.
- Annualized growth: (index/100)^(12/k) - 1, k = months since 2022-11,
  published from k = 6. Year-over-year: index_t/index_(t-12) - 1.
  Both stored as signed decimal rates. Wage indices are nominal; no
  deflation is applied.

Value columns: Wage Index (FTE-adjusted average monthly cash wage) per Mouchel exposure quintile, all ages 21-60 pooled. Mouchel package: quintiles are assigned from the Mouchel et al. (2026) evidence-grounded exposure measure (mouchel_grounded in styrk08_mouchel_mapping.csv) over the same 397 occupations as the Eloundou-based packages (equal-frequency by occupation). Spearman rank correlation with the Eloundou beta is 0.94 and 66 percent of occupations fall in the same quintile, so levels are comparable but not identical across measures.
