* =============================================================================
* 8_alt_outcomes.do : intensive-margin outcomes (linear OLS) with firm × time FE
* =============================================================================
* Same triple-difference structure as 7_triplediff_2age.do, but with `reghdfe`
* (linear OLS) on cell-mean intensive-margin outcomes:
*
*   Outcome           Transformation                   Source
*   ----------------  -------------------------------  -------------------
*   log monthly wage  ln(m_wage)                       lonn_kontant
*   position pct      m_position                       arb_stillingspst
*   log base hours    ln(m_basehours), m_basehours > 0  arb_arbeidstid
*   overtime hours    m_overtime                       lonn_overtid_timer
*
* For each outcome × sample, run with firm × age + firm × time + age × time FE,
* clustered at foretak. No "no_frtk_fe" reconciliation here; that lives in
* script 7 for the count outcome only.
*
* Cell weights: current cell count (count_all / count_ft). With cell-mean
* outcomes weighted by cell count, OLS is equivalent to fitting on the
* underlying individual-level data: a cell with N workers contributes the
* same as N individual rows would. Synthetic cells (count_all = 0) get weight
* 0 and drop out — correct, since no workers existed in that cell × month.
*
* Inputs:  $data\cells_flagged.dta
* Outputs: $data\coefs_alt.dta
*          $output\coefficients\coef_alt.csv
* Appends: §9 to $RESULTS_MD
*
* Design rationale: see DESIGN_CHOICES.md sections 10 (current count weight,
* not pre-period), 13 (cluster), 15 (sample), 17 (wage rate handling).
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

cap which reghdfe
if _rc {
    di as error "reghdfe not installed. Install via: ssc install reghdfe"
    exit 111
}


* =============================================================================
* Section 1: Postfile setup
* =============================================================================

tempname pf
tempfile f_alt

postfile `pf' str20 outcome str20 sample str30 coef_name ///
    double estimate double se double t_stat long n_obs long n_frtk ///
    using `f_alt', replace


* =============================================================================
* Section 2: Outcome × sample loop
* =============================================================================
* For headline sample, intensive-margin outcomes use the *_all variants;
* for FT-based samples, use the *_ft variants.

* outcome   m_var          ln_transform   weight_var (cell N)
local n_outs = 4
local out_1_label "ln_wage"
local out_1_var   "m_wage"
local out_1_log   1
local out_2_label "position"
local out_2_var   "m_position"
local out_2_log   0
local out_3_label "ln_basehours"
local out_3_var   "m_basehours"
local out_3_log   1
local out_4_label "overtime"
local out_4_var   "m_overtime"
local out_4_log   0

* Headline run: private-sector cells, all FT/PT (m_*_all variants).
local n_samples = 1
local sample_1   "headline_priv"
local flag_1     "in_headline_priv"
local m_suffix_1 "all"
local w_1        "count_all"

forval o = 1/`n_outs' {

    local out_label "`out_`o'_label'"
    local out_var   "`out_`o'_var'"
    local out_log   = `out_`o'_log'

    forval s = 1/`n_samples' {

        local sample_name "`sample_`s''"
        local sample_flag "`flag_`s''"
        local m_suffix    "`m_suffix_`s''"
        local weight_var  "`w_`s''"

        local outcome_var "`out_var'_`m_suffix'"

        di _n "==========================================="
        di "ALT  |  outcome = `out_label'  |  sample = `sample_name'  |  cell var = `outcome_var'"
        di "==========================================="

        use "$data\cells_flagged", clear
        keep if `sample_flag' == 1

        * Drop cells with missing outcome (no observations supporting the mean)
        drop if missing(`outcome_var')

        * For log-outcomes : drop non-positive cell means
        if `out_log' == 1 {
            drop if `outcome_var' <= 0
            gen double y = ln(`outcome_var')
        }
        else {
            gen double y = `outcome_var'
        }

        * Triple-diff regressors
        gen byte young = (age_bin == 1)
        gen byte post  = (ym >= ym($event_zero_y, $event_zero_m))

        qui count
        local n_obs = r(N)
        egen byte v_tag = tag(frtk_id)
        qui count if v_tag == 1
        local n_frtk = r(N)
        drop v_tag

        cap noisily reghdfe y c.young##c.post##c.exposure_std [aw = `weight_var'], ///
            absorb(frtk_id#age_bin frtk_id#ym age_bin#ym) ///
            cluster(frtk_id)
        local rc = _rc

        if `rc' {
            di as error "  reghdfe failed (rc=`rc'); skipping"
            continue
        }

        foreach cn in c.exposure_std c.young#c.exposure_std ///
                      c.post#c.exposure_std c.young#c.post#c.exposure_std {
            local b = .
            local s = .
            cap local b = _b[`cn']
            cap local s = _se[`cn']
            local t = .
            if !missing(`b') & !missing(`s') & `s' > 0 {
                local t = `b' / `s'
            }
            if !missing(`b') {
                post `pf' ("`out_label'") ("`sample_name'") ("`cn'") ///
                    (`b') (`s') (`t') (`n_obs') (`n_frtk')
            }
        }
    }
}

postclose `pf'


* =============================================================================
* Section 3: Save coefficient file
* =============================================================================

use `f_alt', clear
sort outcome sample coef_name
compress
save "$data\coefs_alt", replace
export delimited using "$output\coefficients\coef_alt.csv", replace


* =============================================================================
* Section 4: Append §9 to $RESULTS_MD
* =============================================================================
* Show triple-interaction coefficient per outcome × sample.

preserve
keep if coef_name == "c.young#c.post#c.exposure_std"
sort outcome sample
tempfile alt_main
save `alt_main'
restore

preserve
use `alt_main', clear

file open mdfh using "$mdfrag\section_09.md", write replace text
file write mdfh "## §9: Alt outcomes (linear OLS, with firm x time FE)" _n
file write mdfh "" _n
file write mdfh ///
    "Triple-difference (Equation 1) with linear OLS via reghdfe. Same FE " ///
    "structure as §8: frtk x age + frtk x time + age x time, clustered at " ///
    "foretak. Cells weighted by current cell count (count_all for headline, " ///
    "count_ft for FT-based samples) so OLS on cell means is equivalent to OLS " ///
    "on individual-level data." _n
file write mdfh "" _n
file write mdfh "| Outcome | Sample | beta | SE | t | N obs | N frtk |" _n
file write mdfh "|---|---|---:|---:|---:|---:|---:|" _n

forval i = 1/`=_N' {
    local out_v  = outcome[`i']
    local samp_v = sample[`i']
    local b      = estimate[`i']
    local se_v   = se[`i']
    local tv     = t_stat[`i']
    local nobs_v = n_obs[`i']
    local nv_v   = n_frtk[`i']

    local b_f  : di %8.4f `b'
    local s_f  : di %8.4f `se_v'
    local t_f  : di %5.2f `tv'
    local n_f  : di %12.0fc `nobs_v'
    local nv_f : di %12.0fc `nv_v'
    foreach v in b_f s_f t_f n_f nv_f {
        local `v' = strtrim("``v''")
    }

    file write mdfh "| `out_v' | `samp_v' | `b_f' | `s_f' | `t_f' | `n_f' | `nv_f' |" _n
}

file write mdfh "" _n
file write mdfh "Full set of 4 coefficients per spec in coefficients/coef_alt.csv." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

restore

do "$scripts\_rebuild_results_md.do"

di _n "Script 8 complete. Alt-outcome coefs saved; section_09 fragment + $RESULTS_MD rebuilt."
