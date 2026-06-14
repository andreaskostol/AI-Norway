* =============================================================================
* 99_master.do : run the full pipeline in order
* =============================================================================
* After this completes, $output\SECURE_SERVER_RESULTS.md is the single
* self-contained document to transfer off-server.
*
* To run a subset, comment out the lines you want to skip. Each script is
* self-contained and reads/writes saved .dta files, so you can re-run
* individual scripts after a pipeline run.
*
* If your scripts directory is somewhere other than the default, edit the
* fallback path on the next line (and the matching one in 0_settings.do).
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

* Capture full stdout/stderr to $output\run_log.txt so any errors, warnings,
* skipped coefs, etc. survive the run and can be inspected off-server. The
* log replaces any previous one; the §1 timestamp in SECURE_SERVER_RESULTS.md
* tells you which pipeline run produced this log.
cap log close _all
log using "$output\run_log.txt", replace text name(master_log)

di _n "==========================================="
di "MASTER : starting pipeline"
di "Run start : `c(current_date)' `c(current_time)'"
di "==========================================="

* --- Data preparation (heavy I/O, only re-run when raw data changes) ---
do "$scripts\1_exposure.do"
do "$scripts\1b_load_styrk7_crosswalk.do"
do "$scripts\2_relevant_ids.do"
do "$scripts\3_monthly_filtered.do"
do "$scripts\4_aggregate_cells.do"
do "$scripts\5_apply_restrictions.do"
do "$scripts\5b_population.do"
do "$scripts\5c_baseline_kref.do"
do "$scripts\5d_sample_size_diagnostic.do"

* --- Regressions (slowest step, save coefficients to disk) ---
* All linear OLS regression scripts moved to R/fixest (see 99_master.R):
*   6c_event_study_share.do          -> 6c_event_study_share_feols.R
*   6d_event_study_continuous_share.do -> 6d_event_study_continuous_share_feols.R
*   8_alt_outcomes.do  + 8b + 8c     -> 8_alt_outcomes_feols.R
* fixest::feols is multi-threaded with Gaure-Berge demeaning; ~10-30x faster
* than reghdfe on these high-dim FE structures. Run `Rscript 99_master.R`
* after this script completes.
*
* Poisson (ppmlhdfe) scripts likewise replaced by fixest::fepois in 99_master.R.
* do "$scripts\6_event_study_bcc.do"
* do "$scripts\6c_event_study_share.do"
* do "$scripts\6d_event_study_continuous_share.do"
* do "$scripts\7_triplediff_2age.do"
* do "$scripts\8_alt_outcomes.do"
* do "$scripts\8b_alt_outcomes_count_level.do"
* do "$scripts\8c_share_triplediff.do"
* 9_pretrend reads coefs from the disabled Poisson event-study (script 6).
* do "$scripts\9_pretrend.do"

* --- Figures: disabled. All publication figures are built locally in Python
*     (analysis-indiv/code/plot_secure_server_results.py) from the coef CSVs.
*     The Stata figure scripts still exist for in-document on-server previews
*     if needed, but section 11/12/13 of SECURE_SERVER_RESULTS.md are now
*     dropped from the rebuilt master .md (see _rebuild_results_md.do).
* do "$scripts\10a_fig_event_study.do"
* do "$scripts\10b_fig_alt_triplediff.do"
* do "$scripts\10c_fig_es_continuous_share.do"

di _n "==========================================="
di "MASTER : pipeline complete"
di "Run end : `c(current_date)' `c(current_time)'"
di "==========================================="
di ""
di "Single deliverable folder for transfer : $output"
di ""
di "Contents (already laid out to mirror local from_secure_server/):"
di "  $output\SECURE_SERVER_RESULTS.md  -- self-contained results document"
di "  $output\figures\                  -- PNG figures"
di "  $output\coefficients\             -- coefficient series CSVs"
di "  $output\diagnostics\              -- pre-trend diagnostics CSVs"
di "  $output\run_log.txt               -- full Stata log of this run"
di "==========================================="

cap log close master_log
