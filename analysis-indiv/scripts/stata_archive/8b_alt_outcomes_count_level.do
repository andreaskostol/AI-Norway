* =============================================================================
* 8b_alt_outcomes_count_level.do : triple-diff on count level (linear OLS)
* =============================================================================
* Same triple-diff design as 7_triplediff_2age.do (Poisson via ppmlhdfe), but
* with reghdfe on count_all directly — no log transform, no log(count + 1).
* Uses synthetic zero-cells from the balanced panel. Gives an effect in
* "workers per cell" units rather than a proportional effect.
*
*   y_{f,a,e,t} = α_{f,a} + β_{f,t} + λ_{a,t}
*               + B · Young · Post · Exposure_std + (2-way) + ε
*
*   y = count_all  (zero-filled by balance for unobserved cell-months)
*
* Faster than ppmlhdfe; useful as a cross-check while Poisson is running.
* Synthetic zero cells DO have an exposure value (inherited from their yrke4),
* so the regression sees them as "no workers in a high-exposure cell" etc.
*
* Inputs:  $data\cells_flagged.dta
* Outputs: $data\coefs_count_level.dta
*          $output\coefficients\coef_count_level.csv
* Appends: §9b to $RESULTS_MD
*
* Design rationale: see DESIGN_CHOICES.md sections 1-2 (why not log(count+1)),
* 7 (zero-cells in balanced panel — they carry exposure values from their
* yrke4), 13 (cluster), 15 (sample).
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
tempfile f

postfile `pf' str20 sample str30 coef_name ///
    double estimate double se double t_stat long n_obs long n_frtk ///
    using `f', replace


* =============================================================================
* Section 2: Sample loop (currently single sample; structured for extension)
* =============================================================================

local n_samples = 1
local sample_1 "headline_priv"
local flag_1   "in_headline_priv"

forval s = 1/`n_samples' {

    local sample_name "`sample_`s''"
    local sample_flag "`flag_`s''"

    di _n "==========================================="
    di "TRIPLE-DIFF (count level)  |  sample = `sample_name'"
    di "==========================================="

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
    di "  n_obs=`n_obs'  n_frtk=`n_frtk'"

    cap noisily reghdfe count_all c.young##c.post##c.exposure_std, ///
        absorb(frtk_id#age_bin frtk_id#ym age_bin#ym) ///
        cluster(frtk_id)
    local rc = _rc

    if !`rc' {
        foreach cn in c.exposure_std c.young#c.exposure_std ///
                      c.post#c.exposure_std c.young#c.post#c.exposure_std {
            local b = .
            local se_v = .
            cap local b = _b[`cn']
            cap local se_v = _se[`cn']
            local t = .
            if !missing(`b') & !missing(`se_v') & `se_v' > 0 {
                local t = `b' / `se_v'
            }
            if !missing(`b') {
                post `pf' ("`sample_name'") ("`cn'") ///
                    (`b') (`se_v') (`t') (`n_obs') (`n_frtk')
            }
        }
    }
    else {
        di as error "  reghdfe failed (rc=`rc'); skipping"
    }
}

postclose `pf'


* =============================================================================
* Section 3: Save coefficient file
* =============================================================================

use `f', clear
sort sample coef_name
compress
save "$data\coefs_count_level", replace
export delimited using "$output\coefficients\coef_count_level.csv", replace


* =============================================================================
* Section 4: Append §9b to $RESULTS_MD
* =============================================================================

file open mdfh using "$mdfrag\section_09b.md", write replace text
file write mdfh "## §9b: Triple-diff on count level (reghdfe, linear OLS)" _n
file write mdfh "" _n
file write mdfh ///
    "Triple-difference on count_all directly (no log transform, no log(count + 1)). " ///
    "Same FE structure as §8: foretak x age + foretak x time + age x time, " ///
    "clustered at foretak. Uses balanced panel including synthetic zero-cells " ///
    "(each zero-cell carries the exposure value of its yrke4, so high-exposure " ///
    "cells with count = 0 contribute negatively to the triple-interaction). " ///
    "Gives an effect in absolute workers-per-cell units rather than a " ///
    "proportional effect — interpret with care; not directly comparable to " ///
    "Poisson coefficients in §8 (they are in log points)." _n
file write mdfh "" _n
file write mdfh "| Sample | beta | SE | t | N obs | N frtk |" _n
file write mdfh "|---|---:|---:|---:|---:|---:|" _n

preserve
cap noisily use "$data\coefs_count_level", clear
if !_rc {
    keep if coef_name == "c.young#c.post#c.exposure_std"
    sort sample
    forval i = 1/`=_N' {
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

        file write mdfh "| `samp_v' | `b_f' | `s_f' | `t_f' | `n_f' | `nv_f' |" _n
    }
}
restore

file write mdfh "" _n
file write mdfh "Full coefficient set (4 coefs per sample) in " ///
    "coefficients/coef_count_level.csv." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 8b complete. Count-level triple-diff coefs saved; section_09b fragment + $RESULTS_MD rebuilt."
