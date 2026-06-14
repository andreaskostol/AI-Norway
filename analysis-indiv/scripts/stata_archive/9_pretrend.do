* =============================================================================
* 9_pretrend.do : pre-trend joint Wald test (Q5 only) per (sample, age bin)
* =============================================================================
* The pre-trend Wald p-values are already computed in script 6 and saved in
* coefs_event_study_summary.dta. This script re-packages them into a single
* diagnostics file and writes §10 of the markdown.
*
* Inputs:  $data\coefs_event_study_summary.dta
* Outputs: $data\diagnostics.dta
*          $output\diagnostics\diagnostics.csv
* Appends: §10 to $RESULTS_MD
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"


* =============================================================================
* Section 1: Diagnostics postfile
* =============================================================================

tempname pf
tempfile f_diag

postfile `pf' str20 diagnostic str20 sample byte age_bin ///
    double estimate long n_obs ///
    using `f_diag', replace


* =============================================================================
* Section 2: Carry forward pre-trend Wald p-values from script 6 summary
* =============================================================================

use "$data\coefs_event_study_summary", clear

forval i = 1/`=_N' {
    local samp = sample[`i']
    local a    = age_bin[`i']
    local mp   = max_pre_abs[`i']
    local pp   = pre_joint_p[`i']
    local nobs = n_obs[`i']

    post `pf' ("pretrend_max_abs") ("`samp'") (`a') (`mp') (`nobs')
    post `pf' ("pretrend_joint_p") ("`samp'") (`a') (`pp') (`nobs')
}

postclose `pf'


* =============================================================================
* Section 3: Save diagnostics file
* =============================================================================

use `f_diag', clear
sort diagnostic sample age_bin
compress
save "$data\diagnostics", replace
export delimited using "$output\diagnostics\diagnostics.csv", replace


* =============================================================================
* Section 4: Append §10 to $RESULTS_MD
* =============================================================================

file open mdfh using "$mdfrag\section_10.md", write replace text
file write mdfh "## §10: Pre-trend diagnostics" _n
file write mdfh "" _n
file write mdfh ///
    "Pre-trend joint Wald test (event-study Q5 dummies in [-24, -2] = 0) per " ///
    "(sample, age bin), carried forward from §7. Private-sector sample shown below; " ///
    "all samples in diagnostics/diagnostics.csv." _n
file write mdfh "" _n
file write mdfh "| Age bin | Max abs pre-coef | Joint pre-trend p |" _n
file write mdfh "|---|---:|---:|" _n

preserve
use "$data\coefs_event_study_summary", clear
keep if sample == "headline_priv"
sort age_bin

forval i = 1/`=_N' {
    local a  = age_bin[`i']
    local mp = max_pre_abs[`i']
    local pp = pre_joint_p[`i']

    local age_label "?"
    if `a' == 1 local age_label "21-30"
    if `a' == 2 local age_label "31-40"
    if `a' == 3 local age_label "41-50"
    if `a' == 4 local age_label "51-60"

    local mp_f : di %6.3f `mp'
    local pp_f : di %6.3f `pp'
    local mp_f = strtrim("`mp_f'")
    local pp_f = strtrim("`pp_f'")

    file write mdfh "| `age_label' | `mp_f' | `pp_f' |" _n
}
restore

file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 9 complete. Pre-trend diagnostics saved; section_10 fragment + $RESULTS_MD rebuilt."
