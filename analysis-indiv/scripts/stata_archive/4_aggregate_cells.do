* =============================================================================
* 4_aggregate_cells.do : worker-month -> (frtk × sekt × age × yrke4 × month) cells
* =============================================================================
* For each month, load the filtered worker-month file, attach ai_q and
* exposure_std via yrke4, and collapse to cell counts + cell means. Save the
* collapsed cells to a per-month .dta. After the loop, append all per-month
* files into one cell-level dataset.
*
* Inputs:  $data\ameld_filt_YYYY_mMM.dta   (one per month, from script 3)
*          $data\exposure.dta              (from script 1)
* Outputs: $data\cells_YYYY_mMM.dta        (one per month, intermediate)
*          $data\cells.dta                 (final appended cell-level dataset)
*
* Cells.dta unit  : (lopenr_foretak, sekt, age_bin, yrke4, ym)
*  Joined        : ai_q, exposure_score, exposure_std
*  Counts        : count_all, count_ft
*  Cell means
*    m_wage_all  / m_wage_ft       (lonn_kontant)
*    m_position_all / m_position_ft (arb_stillingspst)
*    m_basehours_all / m_basehours_ft
*    m_overtime_all / m_overtime_ft
*
* Panel is BALANCED at (foretak, age_bin, yrke4) cell level: for each cell
* that ever has a positive-employment observation, all months are present
* (zero counts on synthetic rows). This lets firm × time FE see firm exits.
*
* Design rationale: see DESIGN_CHOICES.md sections 4 (cell unit), 6 (activity
* threshold), 7 (balanced panel), 8 (foretak activity), 9 (sample-weighted
* exposure standardization), 16 (numeric IDs).
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"


* =============================================================================
* Section 1: Per-month collapse (write to per-month .dta)
* =============================================================================
* Each month is independent. No tempfile-append-save round trip — that pattern
* O(months^2) on disk I/O. Instead, save one .dta per month, then append in a
* single pass at the end.

forval y = $period_start_y / $period_end_y {
forval m = 1 / 12 {

    if (`y' == $period_start_y & `m' < $period_start_m) continue
    if (`y' == $period_end_y   & `m' > $period_end_m  ) continue

    local infile  "$data\ameld_filt_`y'_m`m'"
    local outfile "$data\cells_`y'_m`m'"

    di _n "=== Aggregating `y' m`m' ==="

    use "`infile'", clear

    * --- Attach exposure (drops worker-months with no exposure score) ---
    merge m:1 yrke4 using "$data\exposure", ///
        keepusing(ai_q exposure_score exposure_std) keep(match) nogen

    * --- FT-conditional outcome columns (missing for non-FT) so that
    *     `(mean) m_x_ft = x_ft` averages over FT workers only.
    gen wage_ft       = lonn_kontant       if ft == 1
    gen position_ft   = arb_stillingspst   if ft == 1
    gen basehours_ft  = basehours          if ft == 1
    gen overtime_ft   = lonn_overtid_timer if ft == 1

    * --- Numeric one-counter for (count) statistic (lopenr_person is string) ---
    gen byte _one = 1

    * --- Collapse to (frtk, sekt, age_bin, yrke4, ym) ---
    collapse ///
        (count) count_all      = _one ///
        (sum)   count_ft       = ft ///
        (sum)   count_new      = ny_jobb ///
        (mean)  m_wage_all     = lonn_kontant ///
                m_position_all = arb_stillingspst ///
                m_basehours_all = basehours ///
                m_overtime_all = lonn_overtid_timer ///
        (mean)  m_wage_ft      = wage_ft ///
                m_position_ft  = position_ft ///
                m_basehours_ft = basehours_ft ///
                m_overtime_ft  = overtime_ft ///
        (first) ai_q exposure_score exposure_std ///
        , by(lopenr_foretak sekt age_bin yrke4 ym)

    compress
    save "`outfile'", replace
}
}


* =============================================================================
* Section 2: Append all per-month cell files
* =============================================================================

clear
forval y = $period_start_y / $period_end_y {
forval m = 1 / 12 {
    if (`y' == $period_start_y & `m' < $period_start_m) continue
    if (`y' == $period_end_y   & `m' > $period_end_m  ) continue
    append using "$data\cells_`y'_m`m'"
}
}

* Sanity checks (before balancing, all rows have positive employment)
assert inrange(ai_q, 1, 5)
assert count_all > 0


* =============================================================================
* Section 2.5: Filter inactive months + balance the panel
* =============================================================================
* (a) Identify (foretak, ym) where the foretak is operating: total employment
*     in the age window (22-55) >= $frtk_min_active. Months below the threshold
*     are treated as "foretak not operating" and removed entirely (no original
*     rows, no synthetic rows). Avoids inventing zero-employment in months a
*     foretak did not exist.
*
* (b) For each (foretak, age_bin, yrke4) cell with positive-employment in
*     some active month, fill zero-employment rows for the foretak's other
*     active months. This lets firm × time fixed effects see firm exits from
*     a (q, age) cell as a zero count rather than as missing data.

* Save unbalanced outcomes only (without cell attributes) to avoid duplicate-variable
* errors at merge. sekt is treated as constant within (foretak, age_bin, yrke4); in
* the rare case of a sektor change within the panel, the first observed sekt
* applies throughout.
preserve
keep lopenr_foretak age_bin yrke4 ym count_all count_ft count_new ///
     m_wage_all m_wage_ft m_position_all m_position_ft ///
     m_basehours_all m_basehours_ft m_overtime_all m_overtime_ft
duplicates drop lopenr_foretak age_bin yrke4 ym, force
tempfile cells_unbal_outcomes
save `cells_unbal_outcomes'
restore

di _n "Computing (foretak, ym) activity ..."
preserve
collapse (sum) _frtk_total = count_all, by(lopenr_foretak ym)
keep if _frtk_total >= $frtk_min_active
keep lopenr_foretak ym
tempfile frtk_active
save `frtk_active'
qui count
di "  Active (foretak, ym) periods: `r(N)'"
restore

* Unique cell keys with their constant attributes
preserve
keep lopenr_foretak sekt age_bin yrke4 ai_q exposure_score exposure_std
duplicates drop lopenr_foretak age_bin yrke4, force
tempfile cell_keys
save `cell_keys'
qui count
di "  Unique cells: `r(N)'"
restore

* Build balanced grid: each cell crossed with all active months for its foretak.
di "Building balanced grid (cell x active months) ..."
use `cell_keys', clear
joinby lopenr_foretak using `frtk_active'

* Merge in observed outcomes; synthetic (cell × month) rows get missing, then 0.
merge 1:1 lopenr_foretak age_bin yrke4 ym using `cells_unbal_outcomes', ///
    keep(master match) nogen
replace count_all = 0 if missing(count_all)
replace count_ft  = 0 if missing(count_ft)
replace count_new = 0 if missing(count_new)
* Intensive-margin cell means (m_wage_*, m_position_*, m_basehours_*, m_overtime_*)
* are left missing on synthetic rows; script 8 drops missings before OLS.

qui count
di "  Balanced active panel size: `r(N)' rows"


* =============================================================================
* Section 2.6: Sample-weighted standardization of exposure_score
* =============================================================================
* Replace the universe-based standardization from script 1 (mean, SD over all
* mapped occupations) with one weighted by employment in the balanced + active
* panel. β coefficients then read as "effect of one SD increase in
* employment-weighted exposure distribution".

qui sum exposure_score [aw=count_all]
local sw_mean = r(mean)
local sw_sd   = r(sd)
di _n "Sample-weighted exposure: mean = `sw_mean', SD = `sw_sd'"
replace exposure_std = (exposure_score - `sw_mean') / `sw_sd'


* Numeric IDs for ppmlhdfe / reghdfe absorb() — older ppmlhdfe versions reject
* string factor variables. Cluster identity is unchanged: same group structure.
egen long frtk_id  = group(lopenr_foretak)
egen long yrke4_id = group(yrke4)

sort lopenr_foretak sekt age_bin yrke4 ym
compress
save "$data\cells", replace


* =============================================================================
* Section 3: Diagnostics for the markdown
* =============================================================================

local n_cells = _N
qui count if count_all > 0
local n_pos = r(N)
local n_synth = `n_cells' - `n_pos'

* Cell-size distribution conditional on count_all > 0 (so synthetic zeros do
* not pull the stats down). Useful for understanding typical cell richness.
qui sum count_all if count_all > 0, detail
local mean_ct = r(mean)
local p50_ct  = r(p50)
local p90_ct  = r(p90)
local p99_ct  = r(p99)

qui count if count_all == 1
local n_singleton = r(N)

* Count distinct foretak without stuffing them into a macro
egen byte v_tag = tag(lopenr_foretak)
qui count if v_tag == 1
local n_frtk = r(N)
drop v_tag

di _n "Cell file: `n_cells' rows (`n_pos' positive, `n_synth' synthetic-zero) over `n_frtk' foretak."
di "  count_all (cells with count_all > 0) : mean = `mean_ct', median = `p50_ct', p90 = `p90_ct', p99 = `p99_ct'"
di "  Singleton cells (count_all == 1) : `n_singleton'"


* =============================================================================
* Section 4: Append §5 to $RESULTS_MD
* =============================================================================

local n_cells_fmt     : di %14.0fc `n_cells'
local n_pos_fmt       : di %14.0fc `n_pos'
local n_synth_fmt     : di %14.0fc `n_synth'
local n_frtk_fmt      : di %14.0fc `n_frtk'
local n_singleton_fmt : di %14.0fc `n_singleton'
local mean_ct_fmt     : di %6.2f   `mean_ct'
local p50_ct_fmt      : di %6.0f   `p50_ct'
local p90_ct_fmt      : di %6.0f   `p90_ct'
local p99_ct_fmt      : di %6.0f   `p99_ct'

foreach v in n_cells_fmt n_pos_fmt n_synth_fmt n_frtk_fmt n_singleton_fmt ///
             mean_ct_fmt p50_ct_fmt p90_ct_fmt p99_ct_fmt {
    local `v' = strtrim("``v''")
}

file open mdfh using "$mdfrag\section_05.md", write replace text

file write mdfh "## §5: Cell-level dataset" _n
file write mdfh "" _n
file write mdfh "Unit of observation: foretak x sektor x age_bin x yrke4 x month. " ///
    "Panel is BALANCED at the (foretak, age_bin, yrke4) cell level: for each cell that " ///
    "ever had positive employment, all *active* months for the foretak are present, with " ///
    "count_all = count_ft = 0 on synthetic rows. A (foretak, ym) period is active when " ///
    "total foretak employment in the age window 22-55 is at least " ///
    "$frtk_min_active workers (configurable in 0_settings.do); months below this " ///
    "threshold are treated as foretak-not-operating and dropped. " ///
    "Intensive-margin cell means are missing on synthetic rows." _n
file write mdfh "" _n
file write mdfh "| Quantity | Value |" _n
file write mdfh "|---|---:|" _n
file write mdfh "| Total cell rows | `n_cells_fmt' |" _n
file write mdfh "| Cells with count_all > 0 | `n_pos_fmt' |" _n
file write mdfh "| Synthetic zero-employment rows | `n_synth_fmt' |" _n
file write mdfh "| Distinct foretak | `n_frtk_fmt' |" _n
file write mdfh "| Singleton cells (count_all = 1) | `n_singleton_fmt' |" _n
file write mdfh "| Mean cell size (count_all > 0 only) | `mean_ct_fmt' |" _n
file write mdfh "| Median (p50, count_all > 0) | `p50_ct_fmt' |" _n
file write mdfh "| 90th percentile (count_all > 0) | `p90_ct_fmt' |" _n
file write mdfh "| 99th percentile (count_all > 0) | `p99_ct_fmt' |" _n
file write mdfh "" _n
file write mdfh "**Joined columns** (from exposure.dta via yrke4): ai_q (1--5), " ///
    "exposure_score (Eloundou GPT-4 β), exposure_std (z-score, " ///
    "employment-weighted standardization over the balanced + active panel)." _n
file write mdfh "" _n
file write mdfh "**Outcome columns** (cell means; suffix _all = all workers in cell, " ///
    "_ft = full-time only): m_wage, m_position, m_basehours, m_overtime, plus " ///
    "count_all, count_ft. Script 8 weights cell-mean OLS by current count_all / " ///
    "count_ft so the regression is equivalent to fitting on individual-level data." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n

file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 4 complete. Cells dataset saved; section_05 fragment + $RESULTS_MD rebuilt."
