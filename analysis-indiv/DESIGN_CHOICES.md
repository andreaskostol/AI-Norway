# Design choices in analysis-indiv

This document records the methodological choices in the pipeline and the
reasoning behind them. Scripts cross-reference the relevant sections here so
that the rationale is in one place rather than scattered across comments.

---

## 1. Estimator for count outcomes: Poisson PPML

**Choice**: `ppmlhdfe` (Poisson maximum likelihood with absorbed FE) on
`count_all` for the headline event study and triple-diff. Linear OLS on
`log(count + 1)` is **not** used.

**Why**:
- Chen & Roth (2024, *QJE*) "Logs with zeros? Some problems and solutions" and
  Mullahy & Norton (2023) show that `log(y + c)` transformations lack a clean
  percentage-effect interpretation: the coefficient depends on the choice of
  `c` (1, 0.5, etc.) and on the units of `y`.
- With our balanced panel containing many synthetic zero-cells (firm × age ×
  yrke4 cells with no workers in some months), the Chen-Roth concern bites
  hard — there are real zeros, not just continuous count data.
- Poisson PPML handles zeros naturally in the likelihood, gives a clean
  log-point interpretation, and matches BCC/Kauhanen.

**Trade-off**: Poisson IRLS is iterative and slow on large absorbed-FE
panels. Mitigations: `tolerance(1e-3)` instead of default `1e-4`, `frtk_min_active`
filter, single sample (`headline_priv` only). See §7 below.

**Where**: scripts 6, 7.

---

## 2. Linear OLS alternatives for triangulation

For sensitivity / quick first-pass results while Poisson runs:

- **Per-capita rate (script 6c, 8c)**: `rate = count / N_(age, ym)`, where
  `N` is SSB Statistikkbanken population in the age cohort. Robust to
  demographic age-composition shifts, always defined (population > 0). Linear,
  weighted by population. **Recommended fast alternative**.
- **Count level (script 8b)**: linear OLS on `count_all` directly. Different
  interpretation (workers per cell, not log-points). Defensible but answers a
  different question.
- **Andreas's `log(count + 1)`**: explicitly **not** used here per the
  Chen-Roth argument. Andreas's data has min count = 5 (microdata.no
  confidentiality), so the `+1` perturbation is mild for him; still avoided
  here for principled consistency.

**Where**: scripts 6c, 8b, 8c.

---

## 3. Identification: BCC equation 4.1

**Choice**: firm × quintile FE (`α_{f,q}`) + firm × time FE (`β_{f,t}`).
Estimated separately by age bin for the event study; with age × time FE
added for the joint triple-diff.

**Why**:
- This is the central identification trick of Brynjolfsson, Chandar & Chen
  (2025). The firm × time FE absorbs all firm-level demand shocks, so
  identifying variation comes only from within-firm differential exposure
  responses.
- `paper/` cell-level pipeline cannot do this because the foretak dimension
  has been aggregated out before microdata.no exports the data. analysis-indiv
  exists specifically to add the firm dimension via individual-level access on
  SSB's secure server.

**Trade-off**: Within-firm-time identification narrows the effective sample
to firms with sufficient quintile mix. Firms with single-quintile occupational
profiles contribute only to FE absorption.

**Where**: scripts 6, 7.

---

## 4. Cell unit: foretak × age_bin × yrke4 × ym

**Choice**: panel granularity at four-way cell level. Exposure varies at
yrke4 level; quintile (`ai_q`) is determined by yrke4 via the Eloundou
mapping.

**Why**:
- yrke4 is the finest cross-walked level we have for STYRK-08.
  exposure_score and ai_q live at yrke4.
- Keeping yrke4 as a cell dimension lets us fill synthetic zeros at the right
  granularity (firm × age × yrke4 ever observed → all months filled). When
  collapsing to (firm × age × ai_q) for the BCC event study, we sum over
  yrke4-cells, which preserves the extensive-margin signal.
- For the triple-diff (script 7), exposure_std variation across yrke4
  *within* (firm × age × ym) is the source of identification for B. We do
  **not** collapse to ai_q for triple-diff — that would lose within-cell
  exposure variation.

**Where**: scripts 4, 7.

---

## 5. Foretak vs. virksomhet

**Choice**: `lopenr_foretak` (legal entity / enterprise level, str10) is the
"firm" dimension. Not `lopenr_virksomhet` (establishment / location level).

**Why**:
- BCC's "firm" in ADP data is the legal employer entity (= ADP client).
  Norwegian foretak is the analog. Virksomhet is finer (per location).
- Hiring/firing decisions and AI rollouts typically happen at the corporate
  HQ level. Virksomhet-FE would absorb these decisions if we aggregated by
  location, removing exactly the variation we want to identify.
- Kauhanen (2026, Finland) uses yritys (= foretak) for the same reason.

**Trade-off**: Multi-establishment foretak (chains) blend across locations.
Could re-run with virksomhet as a robustness check, but not done in current
pipeline.

**Where**: throughout — scripts 3 onward.

---

## 6. Activity threshold: `frtk_min_active = 20`

**Choice**: a foretak is included in the panel for a given month only if its
total employment in the age window 21-60 is ≥ 20 that month.

**Why**:
- Without a threshold, the balanced panel includes very small firms
  (1-5 workers) that contribute little to identification but a lot of
  singleton observations that ppmlhdfe drops anyway. With a threshold of 20,
  the panel is dominated by firms with enough mass for within-firm
  comparisons.
- 20 is a compromise between BCC's per-age threshold of 10 (which is at the
  age × firm level, more restrictive at age level but lets in smaller
  firms overall) and a permissive threshold of 5 that bloats the panel.
- Reduces ppmlhdfe runtime ~3-5x by avoiding singleton-heavy panels.

**Trade-off**: Drops smaller foretak. Not representative of the *full*
private-sector employment universe. Robustness with threshold = 5 or 10
possible by editing the global in `0_settings.R`.

**Where**: `0_settings.R`, `4_aggregate_cells.R`.

---

## 7. Balanced panel with synthetic zero-cells

**Choice**: for each (foretak, age_bin, yrke4) cell that ever has a positive
observation, fill all *active* foretak-months with that cell. Months where
the cell has no real observation get `count_all = 0` (synthetic).

**Why**:
- BCC's identification relies on extensive-margin variation: a firm reducing
  hiring in young-Q5 cells. With unbalanced data, an "exit" (cell drops from
  10 to 0 workers between months) is captured as a missing row, not as a
  zero. Firm × time FE then can't see the change.
- Synthetic zeros let firm × time FE see firm-cell exits as actual zeros,
  giving Poisson the right input for proportional-effect estimation.

**Important boundary**: cells *never* observed for a (foretak, age_bin, yrke4)
combination are NOT filled with zeros — they're absent from the panel.
A foretak that never had software developers shouldn't have invented zeros
for that yrke; that's not a real "exit", it's "never existed".

**Where**: `4_aggregate_cells.R` (Section 2.5).

---

## 8. Foretak existence: when is a foretak "active"?

**Choice**: a (foretak, ym) period is active when the foretak has ≥
`frtk_min_active = 20` workers in our age window 21-60 *that month*. Both
synthetic and original rows in inactive months are dropped.

**Why**:
- Avoids inventing zero-employment in months a foretak did not operate
  (e.g., before founding, after dissolution, brief operational pauses).
- The minimum threshold ensures we focus on operating foretak with enough
  workforce mass to support within-firm identification.

**Where**: `4_aggregate_cells.R` (Section 2.5).

---

## 9. Sample-weighted exposure standardization

**Choice**: `exposure_std` is computed as a z-score *weighted by employment*
in the balanced + active panel. Not a universe-based z-score over the 397
mapped occupations.

**Why**:
- Reader-natural interpretation of triple-diff coefficient B is "effect of one
  SD increase in *the employment-weighted exposure distribution*". An
  unweighted z-score over occupations would give a different reference SD.
- BCC and Kauhanen both standardize over the estimation sample (or
  sample-weighted) for the same reason.

**Where**: `4_aggregate_cells.R` (Section 2.6).

---

## 10. Cell weights in linear OLS (script 8)

**Choice**: `aw = count_all` (current cell count). Not pre-period count.

**Why**:
- Cell-mean OLS weighted by current cell size is mathematically equivalent
  to OLS fitted on the underlying individual-level data (each worker
  contributes one observation with the cell mean). This is the most
  defensible interpretation of OLS-on-cell-means.
- Pre-period weights (Andreas's convention) try to avoid endogenous-weight
  bias, but the bias is on efficiency, not consistency. The cost of using
  pre-period weights is that cells entering only post-period get weight 0,
  effectively dropping them from estimation.
- For per-capita-rate specs (6c, 8c), weight is `population` so that the
  regression effectively gives each individual in the cohort equal weight.

**Where**: `8_alt_outcomes_feols.R`, `8_alt_outcomes_feols.R (block 3)`, `6c_event_study_share_feols.R`.

---

## 11. Reference month: October 2022 (k = -1)

**Choice**: October 2022 is the omitted reference (k = -1) in event-study
dummies. November 2022 is the first treated month (k = 0).

**Why**:
- ChatGPT launched 30 November 2022. Last fully untreated month = October
  2022. First fully treated month = November 2022.
- BCC and Kauhanen use the same convention.

**Collapsed DiD and triple-diff reference the same baseline month.** The static
per-age DiD (7b, 7d, the cell-level `microdata_did_cell.R`) and the triple-diff
(7) do **not** pool the whole pre-period as the control. Each pre-month enters
as its own event-time level (`kk`) and all post-ChatGPT months collapse to
`"POST"`, with `k = -1` (Oct 2022) omitted -- so the POST coefficient is the
average post effect *relative to October 2022*, with pre-trends absorbed rather
than averaged into the baseline. A pooled-pre baseline (the earlier binary
`post`) is biased when pre-trends are present (they are; see the event-study
`pre_joint_p`). This matches the event study (6), the CA scripts (6e/7c) and
BCC.

**Where**: `0_settings.R` (`REF_Y/M`, `EVENT_ZERO_Y/M`, `YM_EVENT_ZERO`);
`kk` construction in `6/6c/7/7b/7d/8_*.R` and `analysis/06_figures/microdata_did_cell.R`.
The triple-diffs (7, 8) carry the interaction in `young_exposure_std` so the
POST coefficient `kk::POST:young_exposure_std` is read directly.

---

## 12. Age binning: four decade groups, 21-60

**Choice**: age_bin 1 = 21-30 (early career), 2 = 31-40, 3 = 41-50,
4 = 51-60 (senior). Workers below 21 or above 60 are dropped. `young` (the
binary cut used by the legacy triple-diff) = age_bin 1 = 21-30.

**Why**:
- Matches the AI-Norway cell-level analysis (`microdata.no` decade groups), so
  the firm-FE individual-level results validate the cell-level results on the
  same age partition.
- Decade groups are coarser than BCC's six bins (22-25, 26-30, 31-34, 35-40,
  41-49, 50-55) but align early-career (21-30) and senior (51-60) with the
  manuscript's framing. The earlier BCC binning is recoverable by reverting
  this section's mapping in `3_monthly_filtered.R` / `5b_population.R` and
  `age_min/max` in `0_settings.R`.

**Where**: `0_settings.R` (`age_min/max`, `young_max`,
`N_AGE_BINS`), `3_monthly_filtered.R`, `5b_population.R`. The R headline
scripts (6, 7, 7b) loop over `N_AGE_BINS`; the legacy Stata estimation/figure
scripts (5d, 6_bcc, 6b, 6c, 9, 10a) were updated to `forval 1/4` with decade
labels.

---

## 13. Cluster: foretak

**Choice**: standard errors clustered at `frtk_id` (= `lopenr_foretak`) for
all firm-FE specs. yrke4 cluster used only in the no-firm-FE reconciliation
spec in script 7 (ii).

**Why**:
- Treatment exposure is at yrke4 level, but firm-FE absorbed designs leave
  residual correlation primarily within firm. Firm-level clustering captures
  firm-time shocks correlated across yrker.
- BCC, Kauhanen cluster at firm. Standard for this design.
- ~10-40K foretak in the headline_priv sample → adequate for CRV1 asymptotics
  (well above the 50-cluster rule of thumb).

**Where**: scripts 6, 7, 8, 6c, 8b, 8c.

---

## 14. Eloundou exposure mapping

**Choice**: `styrk08_eloundou_beta_mapping.csv` from
`data/ai_exposure/`, built by `analysis/03_mappings/build_eloundou_mapping.py`
via the chain O\*NET-SOC 2018 → SOC 2010 → ISCO-08 = STYRK-08.

**Why over `andreas-sin-analyse/data/raw/styrk08_exposure.csv`**:
- The newer mapping covers 397 STYRK codes vs. Andreas's 365. The 32 missing
  in Andreas's file include large occupations: helsefagarbeidere (5321,
  7.3M worker-months), sykepleiere (2223, 4.2M), software developers (2512),
  systems analysts (2511), and others. Critical mass missing from his
  estimation sample.
- The newer build uses BLS crosswalks on the full O\*NET-SOC backing dataset,
  not just the published Eloundou tables.

**Manual maps**: 2223 (Sykepleiere) and 2224 (Vernepleiere) are mapped to
ISCO 2221 (Nursing professionals = US Registered Nurses). Defensible for
sykepleiere; vernepleiere is an imperfect proxy but better than dropping.
Flagged in `manual_map` column.

**Codes not covered (≈9, ≈0.5% of worker-months)**: military (0110, 0210),
clergy (3413), small specialty codes. Acceptable exclusions.

**Where**: `1_exposure.R`. Methodology: `data/ai_exposure/docs/mapping_methodology.md`.

---

## 15. Sample: `headline_priv` (private sector, all FT/PT)

**Choice**: regressions in scripts 6, 6c, 7, 8, 8b, 8c run only on
`in_headline_priv == 1` cells (private sector, FT and PT both).

**Why**:
- Matches BCC's "private + ADP-covered" sample.
- Other sample variants (in_ft, in_ft_priv, in_bcc_full) are still tagged
  in `cells_flagged.dta` and can be re-enabled in scripts 6-8 by changing
  `n_samples` and the flag locals — useful as robustness layers in a later run.

**Where**: `5_apply_restrictions.R` (defines flag), scripts 6 onward (uses).

---

## 16. Numeric IDs for `ppmlhdfe` / `reghdfe` factor variables

**Choice**: `frtk_id = group(lopenr_foretak)` and `yrke4_id = group(yrke4)`
as numeric IDs, used in `absorb()` and `cluster()`.

**Why**:
- `lopenr_foretak` is str10 and `yrke4` is str4. Older versions of `ppmlhdfe`
  (and `reghdfe` < v4) reject string variables as factor variables. Using
  numeric IDs is universally compatible.

**Where**: `4_aggregate_cells.R` (creates IDs), regressions in 6, 7, 8.

---

## 17. Wage rate cleaning: missing as missing

**Choice**: `lonn_time` (hourly wage rate) is set to missing — not zero —
when the original value is missing, negative, or the corresponding hours
count is implausibly high (>300/month). `lonn_overtid_timer` and `lonn_fast`
are still imputed to 0 because they are *counts* / *amounts*, not rates.

**Why**:
- A missing or negative hourly wage rate indicates "no hourly arrangement",
  not "rate is zero". Imputing 0 would bias downward any wage analysis that
  averages over `lonn_time`.
- Hours counts (`lonn_time_antall`, `lonn_overtid_timer`) where missing
  typically means "no such hours that month" → 0 is the right imputation.

**Where**: `3_monthly_filtered.R`.

---

## 18. Drop spells with `lonn_kontant ≤ 0`

**Choice**: spells where cash earnings are missing or non-positive are
dropped at the monthly filter stage.

**Why**:
- Matches BCC's ADP sample of "positive earnings" workers.
- Norwegian-specific complication: workers on parental leave (after employer
  obligation ends) and long sick leave have lonn_kontant = 0 but are still
  formally employed. These are dropped here, which means our employment
  count is *active employment* not *employment relationships*.
- Defensible: BCC also captures active employment, not relationship counts.
  A robustness check could keep zero-pay spells if formal-employment count
  is the parameter of interest.

**Upper tail (winsorization)**: the *lower* tail is dropped (≤ 0 above); the
*upper* tail is **winsorized**, because `lonn_kontant` occasionally carries
absurd data-error records (a single ~3×10⁹ kr value in yrke4 9112, 2023m7 — see
`A1b_wage_spike_diag.R`) that would otherwise inflate every wage outcome
(`m_wage_all` → 7b/7d/8 `log_wage`, 7c `z_wage`). Each spell's `lonn_kontant` is
capped at the `WINSOR_HI` (= 0.999) percentile **within (yrke4, month)** when the
occupation-month has ≥ `WINSOR_MINN` (= 1000) spells — so the percentile sits
below a lone giant — and at the pooled per-month percentile otherwise (where an
own-percentile would just equal the outlier). The median is unaffected
(diagnostic confirmed the spike was outliers, not a broad lump-sum month).

**Where**: `3_monthly_filtered.R` (at source, protects all wage outcomes);
constants `WINSOR_HI`/`WINSOR_MINN` in `0_settings.R`; `A1_bcc_descriptive_agg.R`
re-applies the same cap defensively for the BCC-appendix Fig 5.

---

## 19. Per-capita rate over share for linear specs

**Choice**: when implementing linear-OLS alternatives to Poisson, use
`rate = count / N_(age_bin, ym)` (per-capita based on SSB age cohort
population), not `share = count / firm_total`.

**Why**:
- Firm-internal share denominator is sensitive to firm-level age composition
  shifts: as firms age (more older workers), young-Q5 share falls *as a
  fraction of firm total* even if young-Q5 *count per young person* is
  stable. Demographic shifts contaminate the parameter.
- Per-age firm denominator (within firm-age share) avoids that bias but
  introduces division-by-zero whenever firm-age has no workers in a month
  (= cell drops from regression, losing the extensive margin we want).
- National per-capita rate avoids both problems: population in age cohort is
  always positive, and shifts in the cohort are explicitly part of the
  denominator (so cohort shrinking doesn't bias estimates).

**Trade-off**: Coefficient is in workers-per-inhabitant units, very small
numerically. Tables multiply by 100 000 for "per 100K inhabitants" scaling.

**Where**: `5b_population.R`, `6c_event_study_share_feols.R`, `8_alt_outcomes_feols.R (block 3)`.

---

## 20. Population data: SSB 07459, quarterly → monthly

**Choice**: SSB Statistikkbanken table 07459 (population by 1-year age,
annual snapshots) is interpolated to quarterly mid-points by
`data/macro/build_population_quarterly.py`. The resulting CSV is loaded by
`5b_population.R`, summed to age_bin and expanded to monthly (each month
within a quarter inherits its quarter's mid-point snapshot).

**Why**:
- Demographic data for our age bins isn't published monthly; quarterly is
  the finest tractable frequency.
- Population changes slowly enough (sub-1% per month for any age cohort)
  that within-quarter constancy is a small approximation.
- Linear interpolation between quarter mid-points to true monthly would be
  more precise but adds complexity; the current approach is simpler and
  introduces only minor noise at quarter boundaries.

**Where**: `5b_population.R`.

---

## 21. 1191 migration and the R-only pipeline

**Choice**: From June 2026 the pipeline runs on data universe **1191**
(`W:\1191\atid\ameld_statdata_{YYYY}_m{M}.dta`, coverage 2015m1–2026m2;
project files on `F:\1191\oysteimh\ai_norway_indiv\data\`) and is **R-only**:
the Stata prep scripts (1–5d) were ported to R and archived in
`scripts/stata_archive/`. Intermediates moved `.dta` → `.rds`. Only haven,
data.table and fixest are assumed on the server. Panel window: 2021m1 to the
data edge (2026m2), set centrally in `0_settings.R`.

**Why**:
- 1191's A-meldingen extends to 2026m2, making the individual analyses as
  current as the microdata.no cell analyses (which run through 2026m02).
- The estimation layer had already abandoned Stata (`ppmlhdfe` → fixest);
  porting the prep removes the two-language round trip, the .dta
  serialization, and one runtime dependency on the server.
- data.table joins/collapses replace `merge`/`collapse`/`joinby` 1:1; the
  per-month processing pattern (one ameld file in memory at a time,
  `col_select` on 12 columns) keeps peak memory at a few GB for prep and
  ~10–15 GB for the balancing step.

**Robustness rules baked into the port** (see `datadoc/inkonsekvenser_1191.md`):
- `faste_oppl.dta` names the person key `w19_0345_lopenr_person`;
  `read_faste_oppl()` in `0_settings.R` accepts either name and renames to
  `lopenr_person`. `ameld_statdata_*` keeps `lopenr_person` through 2026m2
  (verified in `datadoc/metadata_scan1191.csv`).
- Only canonical paths are ever referenced — never the same-named stale
  copies in `atid/old/`, `demo/Old/`, `*_bak/`.
- `_dryrun_validate.R` (run LOCALLY before every transfer) checks every
  (file, variable, type) reference against `datadoc/metadata_scan1191.csv`.
- Fail loudly: a missing month file or column stops the run (the Stata
  pipeline skipped with zeros); no tryCatch around core data operations.
- Transient I/O only is retried: `.dta` reads off the W: share occasionally
  abort a 2-hour run with "Unable to read from file" (share hiccup / lock / AV
  scan) at a random month. `read_dta_retry()` in `0_settings.R` retries the
  read `DTA_READ_TRIES` times with a `DTA_READ_WAIT`s backoff before giving up;
  all W: reads (`read_dta_cols`, `read_faste_oppl`, the script-3 header probes)
  route through it. A genuinely missing file (`file.exists` first) or renamed
  column (probe on the returned header) still fails loudly on the final try.
- `KMIN`/`KMAX` derive from the period constants instead of being hardcoded —
  a fixed `KMAX = 36` would have silently dropped 2025m12–2026m2 from the
  event studies.

**Where**: `0_settings.R`, `_dryrun_validate.R`, `1_exposure.R` …
`5d_sample_size_diagnostic.R`, `99_master.R`, `scripts/stata_archive/`.

---

## 22. Specification-comparison module (7b vs 7d)

**Choice**: A core purpose of the individual-level data is to test whether
the BCC firm-FE specification and the project's cell-level specification give
similar per-age DiD-Poisson estimates **on identical data**. Script
`7d_did_byage_cellspec.R` runs the cell spec (yrke4 + month FE, cluster
yrke4, Q3 reference — lifted from `analysis/06_figures/microdata_did_cell.R`)
on two samples, so that together with 7b and the published cell table the
chain decomposes into one factor at a time:

| Comparison | Isolates |
|---|---|
| 7b (firm spec) vs 7d `restricted` (cell spec) | **Specification** — same `in_headline_priv` data |
| 7d `restricted` vs 7d `unrestricted_priv` | **≥ FRTK_MIN_ACTIVE active-firm restriction + balancing** |
| 7d `unrestricted_priv` vs `coef_microdata_did_cell.csv` | **Data source** (register vs microdata.no) |

**Mechanics**:
- The unrestricted occupation aggregate (`occ_unrestricted_agg.rds`) is summed
  in script 4 from the per-month cells BEFORE the activity filter and
  balancing. Summing firm cells over foretak is exact for counts, and exact
  for the worker-level mean wage because every kept worker has
  `lonn_kontant > 0` (so `count_all * m_wage_all` is the exact wage sum).
- Identical-sample guard: 7b and 7d both write `sum_count_all` (total
  worker-months in the `in_headline_priv` slice per age_bin, computed before
  any collapsing) into their coefficient CSVs. Equality per age_bin is the
  mechanical check that the two specifications saw the same universe.
- Residual definitional gaps vs microdata.no (documented, not removable):
  spells without a foretak ID are dropped here but counted by microdata.no;
  the person universe is the cohort file rather than microdata.no's
  population; both sides inner-join the same Eloundou mapping.

**Event-study counterparts.** Each column of the collapsed-DiD comparison has a
dynamic gamma_{q,k} version on the same BCC reference (Q1, k = -1), so the same
decomposition can be read off the event-study paths:

| DiD column | Event study |
|---|---|
| 7b firm-FE | `6_event_study_fepois.R` (firm x q + firm x t FE) |
| 7d cell-spec (restricted, unrestricted_priv) | `6f_event_study_cellspec.R` (yrke4 + month FE) |
| published microdata.no cell | `analysis/06_figures/microdata_es_decade_q1_full*.R` |

`6f` reuses 7d's exact slices (so the restricted event study sits on the 7b/7d
sample) and script 6's coefficient harvesting, estimating the full k path
instead of collapsing to POST.

**Where**: `7d_did_byage_cellspec.R`, `7b_did_byage_fepois.R`,
`6f_event_study_cellspec.R`, `6_event_study_fepois.R`,
`4_aggregate_cells.R` (section 2.4), `analysis/06_figures/microdata_did_cell.R`.

---

## 23. Full estimation window through 2026m2

**Choice**: The DiD scripts estimate on the FULL panel (2021m1–2026m2). The
2025m4 "pre-agentic" cutoff that 7b and the cell-level run shared is dropped
on both sides (the local `microdata_did_cell.R` is re-aligned in the same
update).

**Why**: The cutoff existed to keep the published tables on the pre-agentic
period while the panels ended mid-2025 anyway. With data through 2026m2 the
project moves to reporting the full window; the agentic-AI timing question is
handled explicitly by the comparative-advantage scripts instead.

**Exception**: in `6e_ca_es_firmfe.R`/`7c_ca_did_firmfe.R` the **chatgpt**
timing window still ends 2025m4 BY DESIGN — there it defines the pre-agentic
estimation period, mirroring the cell-level interaction note. The **agentic**
window now runs to the data edge (`YM_PERIOD_END`), so its post period grows
with each delivery.

**Where**: `7b_did_byage_fepois.R`, `7d_did_byage_cellspec.R`,
`6e_ca_es_firmfe.R`, `7c_ca_did_firmfe.R`, `0_settings.R` (KMAX).

---

## 24. Quintile reference: Q1 (lowest exposure), following BCC

**Choice**: in every quintile spec -- the event study (6, 6c) and the
collapsed per-age DiD (7b, 7d, the cell-level `microdata_did_cell.R`) -- the
omitted reference category is `ai_q = 1` (lowest AI exposure). The reported
contrasts are Q2, Q3, Q4, Q5 each vs Q1.

**Why**:
- BCC use the least-exposed group as the control: the object of interest is how
  the *more* exposed quintiles move relative to the *least* exposed, so Q1 is
  the natural omitted baseline. Reporting against the median (Q3) mixes the
  high- and low-exposure deviations into the reference and obscures the
  monotone-in-exposure reading.
- The earlier Q3 choice was made to avoid Q1's winter-construction seasonality
  contaminating the reference. With month / firm x month FE in every spec and
  the `k = -1` baseline (§11), that seasonality is absorbed, so the BCC
  convention is recovered without the contamination concern.

**Trade-off**: coefficients are no longer centered on the median quintile; the
Q1 reference is a smaller, more seasonal group, so its sampling noise enters
every contrast. Mitigated by the FE structure and the large sample.

**Where**: `ref2 = "1"` in the `i(kk, ai_q, ...)` / `i(kshift, ai_q, ...)` calls
of `6_event_study_fepois.R`, `6c_event_study_share_feols.R`,
`7b_did_byage_fepois.R`, `7d_did_byage_cellspec.R`,
`analysis/06_figures/microdata_did_cell.R`.
