* =============================================================================
* 7_triplediff_2age.do : binary-age triple-difference, Poisson, with firm × time FE
* =============================================================================
* Equation 1:
*
*   log E[y_{v,q,a,t}] = α_{v,a} + β_{v,t} + λ_{a,t}
*                      + β · Young · Post · Exposure_std + (2-way) + ε
*
* Estimated with `ppmlhdfe`, absorb(frtk#age_bin frtk#ym age_bin#ym),
* cluster at foretak. The β_{v,t} (firm × time) FE is the central
* addition over the cell-level pipeline. Young = (age_bin == 1) = ages 22-25;
* Older = age_bin in 2..6 = ages 26-55.
*
* For each sample variant, run TWO specifications:
*   (i)  with frtk FE in absorb()       (firm-FE specification, headline)
*   (ii) without frtk in absorb()       (cell-level reconciliation; data first
*        re-collapsed to (yrke4, age_bin, ym), no firm dimension, mirrors
*        Andreas's pipeline structure)
*
* The gap between (i) and (ii) within the same outcome and sample quantifies
* what firm fixed effects add. (Note: Andreas's published number uses
* feols on log(count+1); the within-pipeline Poisson reconciliation here is
* not a direct comparison against that — the functional form differs.)
*
* Inputs:  $data\cells_flagged.dta
* Outputs: $data\coefs_triplediff.dta
*          $output\coefficients\coef_triplediff.csv
* Appends: §8 to $RESULTS_MD
*
* Design rationale: see DESIGN_CHOICES.md sections 1 (Poisson PPML), 3
* (BCC eq 4.1 identification), 4 (cell unit and exposure_std variation
* across yrke4), 13 (cluster), 15 (sample = headline_priv).
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

cap which ppmlhdfe
if _rc {
    di as error "ppmlhdfe not installed. Install via: ssc install ppmlhdfe"
    exit 111
}


* =============================================================================
* Section 1: Postfile setup
* =============================================================================

tempname pf
tempfile f_td

postfile `pf' str20 sample str14 spec str30 coef_name ///
    double estimate double se double t_stat long n_obs long n_frtk ///
    using `f_td', replace


* =============================================================================
* Section 2: Sample × spec loop
* =============================================================================

* Headline run is the private-sector all-worker sample. Other variants
* (ft, ft_priv, bcc_full) remain available in cells_flagged.dta.
local n_samples = 1
local sample_1 "headline_priv"
local flag_1   "in_headline_priv"
local out_1    "count_all"

forval s = 1/`n_samples' {

    local sample_name "`sample_`s''"
    local sample_flag "`flag_`s''"
    local outcome_var "`out_`s''"

    di _n "==========================================="
    di "TRIPLE-DIFF | sample = `sample_name' | outcome = `outcome_var'"
    di "==========================================="


    * --- (i) With firm × time FE ---

    use "$data\cells_flagged", clear
    keep if `sample_flag' == 1
    gen byte young = (age_bin == 1)
    gen byte post  = (ym >= ym($event_zero_y, $event_zero_m))

    qui count
    local n_obs = r(N)
    egen byte v_tag = tag(frtk_id)
    qui count if v_tag == 1
    local n_frtk = r(N)
    drop v_tag
    di "  spec=with_frtk_fe  n_obs=`n_obs'  n_frtk=`n_frtk'"

    cap noisily ppmlhdfe `outcome_var' c.young##c.post##c.exposure_std, ///
        absorb(frtk_id#age_bin frtk_id#ym age_bin#ym) ///
        cluster(frtk_id) tolerance(1e-3)
    local rc = _rc

    if !`rc' {
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
                post `pf' ("`sample_name'") ("with_frtk_fe") ("`cn'") ///
                    (`b') (`s') (`t') (`n_obs') (`n_frtk')
            }
        }
    }
    else {
        di as error "  ppmlhdfe failed (rc=`rc'); skipping spec (i)"
    }


    * --- (ii) Cell-level reconciliation: drop frtk dimension ---
    * Re-collapse to (yrke4, age_bin, ym), then run the same spec without
    * firm FE.

    use "$data\cells_flagged", clear
    keep if `sample_flag' == 1

    collapse (sum) `outcome_var' (mean) exposure_std, by(yrke4 age_bin ym)
    * Numeric yrke4 ID for ppmlhdfe (older versions reject string factors)
    egen long yrke4_id = group(yrke4)
    gen byte young = (age_bin == 1)
    gen byte post  = (ym >= ym($event_zero_y, $event_zero_m))

    qui count
    local n_obs2 = r(N)
    egen byte y_tag = tag(yrke4_id)
    qui count if y_tag == 1
    local n_yrke4 = r(N)
    drop y_tag
    di "  spec=no_frtk_fe (yrke4-level)  n_obs=`n_obs2'  n_yrke4=`n_yrke4'"

    cap noisily ppmlhdfe `outcome_var' c.young##c.post##c.exposure_std, ///
        absorb(yrke4_id#age_bin age_bin#ym) ///
        cluster(yrke4_id) tolerance(1e-3)
    local rc = _rc

    if !`rc' {
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
                post `pf' ("`sample_name'") ("no_frtk_fe") ("`cn'") ///
                    (`b') (`s') (`t') (`n_obs2') (`n_yrke4')
            }
        }
    }
    else {
        di as error "  ppmlhdfe failed (rc=`rc'); skipping spec (ii)"
    }
}

postclose `pf'


* =============================================================================
* Section 3: Save coefficient file
* =============================================================================

use `f_td', clear
sort sample spec coef_name
compress
save "$data\coefs_triplediff", replace
export delimited using "$output\coefficients\coef_triplediff.csv", replace


* =============================================================================
* Section 4: Append §8 to $RESULTS_MD
* =============================================================================
* Show only the headline triple-interaction coefficient
* (c.young#c.post#c.exposure_std), per sample × spec.

preserve
keep if coef_name == "c.young#c.post#c.exposure_std"
sort sample spec
tempfile td_main
save `td_main'
restore

preserve
use `td_main', clear

file open mdfh using "$mdfrag\section_08.md", write replace text
file write mdfh "## §8: Triple-diff coefficients (Poisson, employment count)" _n
file write mdfh "" _n
file write mdfh ///
    "Equation 1: log E[y_{v,q,a,t}] = alpha_{v,a} + beta_{v,t} + lambda_{a,t} + " ///
    "B * Young * Post * Exposure_std + 2-way + e. Standard errors clustered at " ///
    "foretak (or at yrke4 in the cell-level reconciliation row)." _n
file write mdfh "" _n
file write mdfh ///
    "Triple-interaction coefficient B = c.young#c.post#c.exposure_std. " ///
    "with_frtk_fe = main spec (firm × age + firm × time + age × time FE). " ///
    "no_frtk_fe = data re-collapsed to (yrke4, age, ym), no firm dimension; " ///
    "the gap with the firm-FE row indicates what firm fixed effects add." _n
file write mdfh "" _n
file write mdfh "| Sample | Spec | beta | SE | t | N obs | N frtk / yrke4 |" _n
file write mdfh "|---|---|---:|---:|---:|---:|---:|" _n

forval i = 1/`=_N' {
    local samp_v   = sample[`i']
    local spec_v   = spec[`i']
    local b        = estimate[`i']
    local se_v     = se[`i']
    local tv       = t_stat[`i']
    local nobs_v   = n_obs[`i']
    local nv_v     = n_frtk[`i']

    local b_f  : di %7.4f `b'
    local s_f  : di %7.4f `se_v'
    local t_f  : di %5.2f `tv'
    local n_f  : di %12.0fc `nobs_v'
    local nv_f : di %12.0fc `nv_v'

    foreach v in b_f s_f t_f n_f nv_f {
        local `v' = strtrim("``v''")
    }

    file write mdfh "| `samp_v' | `spec_v' | `b_f' | `s_f' | `t_f' | `n_f' | `nv_f' |" _n
}

file write mdfh "" _n
file write mdfh ///
    "Full coefficient set (4 coefs × sample × spec) in coefficients/coef_triplediff.csv." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

restore

do "$scripts\_rebuild_results_md.do"

di _n "Script 7 complete. Triple-diff coefs saved; section_08 fragment + $RESULTS_MD rebuilt."
