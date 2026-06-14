* =============================================================================
* 1_exposure.do : load STYRK-08 exposure CSV, build quintile + standardized score
* =============================================================================
* Inputs:  $data\styrk08_eloundou_beta_mapping.csv (transferred from the main
*                                       project's data/ai_exposure/ directory;
*                                       built by analysis/03_mappings/build_eloundou_mapping.py)
* Outputs: $data\exposure.dta            (yrke4 + ai_q + exposure_std)
* Appends: §1 Run metadata + §2 Exposure construction; opens $RESULTS_MD fresh
*
* Mapping coverage: 397 STYRK-08 codes (vs 365 in andreas-sin-analyse's older
* file). Crosswalk: O*NET-SOC 2018 -> SOC 2010 -> ISCO-08 = STYRK-08 (4-digit).
* Manual maps: 2223 Sykepleiere <- 2221 Nursing professionals (RN proxy);
*              2224 Vernepleiere <- 2221 (imperfect RN proxy, flagged in manual_map).
* Codes not covered (~9, ~0.5% of worker-months): military 0110/0210, clergy 3413,
* small specialty codes 3439/4213/7133/8155/9613, plus missing-code 0000.
*
* The 7-digit -> 4-digit STYRK-08 reduction is done in script 3 by merging
* yrke7 against the Norwegian crosswalk file occupations_7digits_4digits.csv
* (loaded into Stata by 1b_load_styrk7_crosswalk.do). substr(yrke7, 1, 4)
* is NOT a valid shortcut: e.g. military "0111101" maps to "0310", not "0111".
*
* Design rationale: see DESIGN_CHOICES.md section 14 (Eloundou exposure
* mapping — why this file, not Andreas's older one).
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"


* =============================================================================
* Section 2: Load Eloundou exposure, build quintile + standardized score
* =============================================================================
* CSV columns: styrk08 (4-digit; numeric), eloundou_beta (continuous score),
* pctl_rank, quintile (precomputed 1-5, equal-occupation), n_soc_matched,
* has_partial_match, max_partial_fanout, manual_map. Comma-delimited.

import delimited "$data\styrk08_eloundou_beta_mapping.csv", clear varnames(1)
confirm variable styrk08
confirm variable eloundou_beta
confirm variable quintile

* yrke4 as zero-padded 4-character string for merging downstream
tostring styrk08, replace force
gen yrke4 = substr("0000" + strtrim(styrk08), -4, 4)

gen double exposure_score = eloundou_beta
drop if missing(exposure_score)

* Initial standardization over the occupation universe (mean 0, SD 1 across
* mapped STYRK codes). Script 4 overwrites exposure_std with an
* employment-weighted standardization computed on the balanced + active panel.
qui sum exposure_score
local x_mean = r(mean)
local x_sd   = r(sd)
gen double exposure_std = (exposure_score - `x_mean') / `x_sd'

* Quintiles (1 = least exposed, 5 = most). Equal-occupation, precomputed in the
* mapping file and matching the existing paper/ convention.
gen byte ai_q = quintile
assert inrange(ai_q, 1, 5)

* Quintile cutoff maxima for the markdown table
forval q = 1/5 {
    qui sum exposure_score if ai_q == `q', meanonly
    local q`q'_max : di %5.3f r(max)
}

keep yrke4 ai_q exposure_score exposure_std
order yrke4 ai_q exposure_score exposure_std
sort yrke4
duplicates drop yrke4, force
compress
save "$data\exposure", replace
local n_exp = _N
di "Exposure: `n_exp' STYRK-08 codes mapped"


* =============================================================================
* Section 3: Write per-section markdown fragments + rebuild master .md
* =============================================================================
* Three fragments:
*   section_00.md  header (title + open issues)
*   section_01.md  §1 Run metadata
*   section_02.md  §2 Exposure construction
* Then `_rebuild_results_md.do` reassembles $RESULTS_MD.

local rundate  "`c(current_date)' `c(current_time)'"
local stataver "`c(stata_version)'"

* --- section_00.md : header ---
file open mdfh using "$mdfrag\section_00.md", write replace text
file write mdfh "# AI-Norway: firm-FE triple-difference and event study" _n
file write mdfh "" _n
file write mdfh ///
    "Self-contained results document built by scripts/1_exposure.do through " ///
    "scripts/10_figures.do. All figures are in output/figures/; coefficient " ///
    "series in coefficients/coef_*.csv." _n
file write mdfh "" _n
file write mdfh "## Open issues for Hernæs / Kostøl" _n
file write mdfh "" _n
file write mdfh ///
    "1. Headline picks: which sample, which exposure, which age binning go in the " ///
    "manuscript headline." _n
file write mdfh ///
    "2. Public vs private split: report both, or only the all-sector headline?" _n
file write mdfh ///
    "3. Magnitude reconciliation: how to interpret any gap between the firm-FE " ///
    "Poisson estimate and Andreas's published cell-level linear-OLS-on-log(count+1) " ///
    "coefficient (functional forms differ)." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

* --- section_01.md : §1 Run metadata ---
local older_min = $young_max + 1
file open mdfh using "$mdfrag\section_01.md", write replace text
file write mdfh "## §1: Run metadata" _n
file write mdfh "" _n
file write mdfh "- Stata version: `stataver'" _n
file write mdfh "- Run date: `rundate'" _n
file write mdfh "- Period: $period_start_y m$period_start_m -- $period_end_y m$period_end_m" _n
file write mdfh "- Reference month: $ref_y m$ref_m (event time k = -1)" _n
file write mdfh "- Age window: $age_min -- $age_max" _n
file write mdfh ///
    "- Young / Older binary cut: $age_min -- $young_max vs `older_min' -- $age_max" _n
file write mdfh ///
    "- BCC restriction thresholds: ≥ $bcc_min_per_age workers per (firm, age) every " ///
    "month; Σ ≥ $bcc_min_total per (firm, q, age) cell" _n
file write mdfh "- Firm dimension: foretak (lopenr_foretak)" _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

* --- section_02.md : §2 Exposure construction ---
file open mdfh using "$mdfrag\section_02.md", write replace text
file write mdfh "## §2: Exposure construction" _n
file write mdfh "" _n
file write mdfh ///
    "Source: data/ai_exposure/styrk08_eloundou_beta_mapping.csv (Eloundou et al. GPT-4 beta, " ///
    "averaged through O*NET-SOC 2018 -> SOC 2010 -> ISCO-08 = STYRK-08). Quintiles: " ///
    "equal-occupation (each STYRK-08 4-digit code counts once), precomputed in the mapping " ///
    "file. Continuous exposure standardized to mean 0, SD 1 across mapped codes. " ///
    "Coverage: 397 STYRK-08 codes; ~9 codes (military, clergy, small specialty) " ///
    "without SOC analog are dropped (~0.5%% of worker-months)." _n
file write mdfh "" _n
file write mdfh "| Quantity | Value |" _n
file write mdfh "|---|---|" _n
file write mdfh "| STYRK-08 codes mapped | `n_exp' |" _n
file write mdfh "| Q1 cutoff (max exposure) | `q1_max' |" _n
file write mdfh "| Q2 cutoff (max exposure) | `q2_max' |" _n
file write mdfh "| Q3 cutoff (max exposure) | `q3_max' |" _n
file write mdfh "| Q4 cutoff (max exposure) | `q4_max' |" _n
file write mdfh "| Q5 cutoff (max exposure) | `q5_max' |" _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 1 complete. Wrote sections 00, 01, 02 to fragments; rebuilt $RESULTS_MD."
