* =============================================================================
* 8c_share_triplediff.do : triple-diff on per-capita employment rate (linear OLS)
* =============================================================================
* Parallel to 7_triplediff_2age.do (Poisson on count) but with reghdfe on
* per-capita employment RATE. Robust to demographic age-composition shifts
* (the denominator is the national age cohort population, not firm-internal
* totals). Avoids both Poisson convergence time and log(count + 1) issues.
*
*   rate_{f,a,y,t} = count_{f,a,y,t} / N_{a,t}
*
* where N_{a,t} = SSB Statistikkbanken population in age_bin a, month t.
* Synthetic zero-cells contribute rate = 0 (no workers from that cohort).
*
*   rate_{f,a,y,t} = α_{f,a} + β_{f,t} + λ_{a,t}
*                  + B · Young · Post · Exposure_std + (2-way) + ε
*
* Coefficient B = change in (workers per inhabitant in age cohort) per SD
* increase in exposure, among young in the post-period. Multiply by 100 000
* for "per 100 000 inhabitants" interpretation.
*
* Inputs:  $data\cells_flagged.dta
*          $data\population_by_agebin_ym.dta  (built by script 5b)
* Outputs: $data\coefs_share.dta
*          $output\coefficients\coef_share.csv
* Appends: §9c to $RESULTS_MD
*
* Design rationale: see DESIGN_CHOICES.md sections 2 (linear OLS alternatives),
* 19 (per-capita rate vs share for demographic robustness), 20 (population
* data).
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

cap which reghdfe
if _rc {
    di as error "reghdfe not installed."
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
    di "TRIPLE-DIFF (share)  |  sample = `sample_name'"
    di "==========================================="

    use "$data\cells_flagged", clear
    keep if `sample_flag' == 1

    * Merge per-(age_bin, ym) population from script 5b
    cap confirm file "$data\population_by_agebin_ym.dta"
    if _rc {
        di as error "  population_by_agebin_ym.dta not found — run 5b_population.do first."
        exit 198
    }
    merge m:1 age_bin ym using "$data\population_by_agebin_ym", ///
        keep(master match) keepusing(population) nogen
    qui count if missing(population)
    if r(N) > 0 {
        di as error "  WARNING: `r(N)' rows have missing population (out of date range?); dropping."
        drop if missing(population)
    }

    gen double rate = count_all / population

    gen byte young = (age_bin == 1)
    gen byte post  = (ym >= ym($event_zero_y, $event_zero_m))

    qui count
    local n_obs = r(N)
    egen byte v_tag = tag(frtk_id)
    qui count if v_tag == 1
    local n_frtk = r(N)
    drop v_tag
    di "  n_obs=`n_obs'  n_frtk=`n_frtk'"

    * Weight by population so larger age cohorts contribute more (per-individual
    * interpretation). Without weight, each cell is weighted equally regardless
    * of cohort size.
    cap noisily reghdfe rate c.young##c.post##c.exposure_std [aw=population], ///
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
save "$data\coefs_share", replace
export delimited using "$output\coefficients\coef_share.csv", replace


* =============================================================================
* Section 4: Append §9c to $RESULTS_MD
* =============================================================================

file open mdfh using "$mdfrag\section_09c.md", write replace text
file write mdfh "## §9c: Triple-diff on per-capita employment rate (reghdfe, linear OLS)" _n
file write mdfh "" _n
file write mdfh ///
    "Triple-difference with per-capita employment RATE as outcome: " ///
    "rate = count_all / N_(age_bin, ym), where N is the SSB age-cohort " ///
    "population for that month (from $data/population_by_agebin_ym.dta, built " ///
    "by 5b_population.do). Robust to demographic age-composition shifts " ///
    "because the denominator is the national age cohort, not firm-internal " ///
    "totals. Linear OLS via reghdfe with the same FE structure as §8 (foretak " ///
    "x age + foretak x time + age x time), clustered at foretak, weighted by " ///
    "population so larger cohorts count more. Synthetic zero-cells contribute " ///
    "rate = 0 (correct: zero workers from that cohort in that cell). " ///
    "Faster than ppmlhdfe. Coefficient is in workers-per-inhabitant units; " ///
    "multiply by 100 000 for 'per 100 000 inhabitants' scaling." _n
file write mdfh "" _n
file write mdfh "| Sample | beta | SE | t | per 100k | N obs | N frtk |" _n
file write mdfh "|---|---:|---:|---:|---:|---:|---:|" _n

preserve
cap noisily use "$data\coefs_share", clear
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
        local b_p100k = `b' * 100000

        local b_f      : di %9.6f `b'
        local s_f      : di %9.6f `se_v'
        local t_f      : di %5.2f `tv'
        local b_100k_f : di %8.2f `b_p100k'
        local n_f      : di %12.0fc `nobs_v'
        local nv_f     : di %12.0fc `nv_v'
        foreach v in b_f s_f t_f b_100k_f n_f nv_f {
            local `v' = strtrim("``v''")
        }

        file write mdfh "| `samp_v' | `b_f' | `s_f' | `t_f' | `b_100k_f' | `n_f' | `nv_f' |" _n
    }
}
restore

file write mdfh "" _n
file write mdfh "Full coefficient set (4 coefs per sample) in " ///
    "coefficients/coef_share.csv." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 8c complete. Share-based triple-diff coefs saved; section_09c fragment + $RESULTS_MD rebuilt."
