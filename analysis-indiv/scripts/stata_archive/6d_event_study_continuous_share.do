* =============================================================================
* 6d_event_study_continuous_share.do : event-study, continuous exposure x young
*                                       triple, linear OLS on per-capita rate
* =============================================================================
* Event-study analogue of 8c (triple-diff with continuous exposure x young).
* Same FE, same sample, same outcome, but with event-time dummies replacing
* the binary post indicator. Gives a dynamic version of the 8c effect.
*
*   rate_{f,a,t} = a_{f,a} + b_{f,t} + l_{a,t}
*                + S_{k != -1} g_k * 1{t-T0=k} * Young * Exposure_std
*                + (necessary 2-way interactions) + e
*
*   y = count_all / N_{age_bin, ym}
*
* Coefficient g_k = differential rate effect at event time k for young workers
* per SD of exposure_std, relative to k = -1 (October 2022). Cells weighted by
* population. Clustered at foretak.
*
* Inputs:  $data\cells_flagged.dta
*          $data\population_by_agebin_ym.dta  (built by script 5b)
* Outputs: $data\coefs_event_study_continuous_share.dta
*          $data\coefs_event_study_continuous_share_summary.dta
*          $output\coefficients\coef_event_study_continuous_share.csv
*          $output\coefficients\coef_event_study_continuous_share_summary.csv
* Appends: §7d to $RESULTS_MD
*
* Design rationale: see DESIGN_CHOICES.md sections 2 (linear OLS alternatives),
* 19 (per-capita rate over share), 20 (population data quarterly -> monthly).
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

* Per-script log so we can diagnose failures even when 6d is run standalone
* (not via 99_master.do). Appended to master log if open; otherwise own file.
cap log close script6d
log using "$output\log_6d.txt", replace text name(script6d)

cap which reghdfe
if _rc {
    di as error "reghdfe not installed."
    cap log close script6d
    exit 111
}


* =============================================================================
* Section 1: Postfile setup
* =============================================================================

tempname pf_es pf_sum
tempfile f_es f_sum

postfile `pf_es' str20 sample int k double coef double se ///
    long n_obs long n_frtk ///
    using `f_es', replace

postfile `pf_sum' str20 sample double max_pre_abs double mean_post ///
    double pre_joint_p long n_obs long n_frtk ///
    using `f_sum', replace


* =============================================================================
* Section 2: Sample loop, fit triple-interaction event study
* =============================================================================

* Event-time bin width in months. 1 = monthly (~60 levels — OOM on 24M obs);
* 2 = 2-month bins (~28 levels — fits with compact + max_memory 128g).
local bin_w = 2

local kmin = -24
local kmax = 36
* signed bin index from monthly kshift = ym - ym(event_zero).
* bin = floor(k / bin_w). With bin_w=2: k in [-22,32] -> bin in [-11,16].
* Reference (k = -1) belongs to bin -1.
local bin_min   = floor(`kmin' / `bin_w')
local bin_max   = floor(`kmax' / `bin_w')
local bin_ref   = floor(-1 / `bin_w')
local k_offset  = -`bin_min'
local k_ref     = `bin_ref' + `k_offset'   // shifted reference bin index

local n_samples = 1
local sample_1 "headline_priv"
local flag_1   "in_headline_priv"

forval s = 1/`n_samples' {

    local sample_name "`sample_`s''"
    local sample_flag "`flag_`s''"

    di _n "==========================================="
    di "EVENT STUDY (continuous x young, rate)  |  sample = `sample_name'"
    di "==========================================="

    use "$data\cells_flagged", clear
    keep if `sample_flag' == 1
    * Drop columns we don't need for this regression to free memory.
    keep frtk_id age_bin ym count_all exposure_std `sample_flag'

    cap confirm file "$data\population_by_agebin_ym.dta"
    if _rc {
        di as error "  population_by_agebin_ym.dta not found - run 5b_population.do first."
        exit 198
    }
    merge m:1 age_bin ym using "$data\population_by_agebin_ym", ///
        keep(master match) keepusing(population) nogen
    qui count if missing(population)
    if r(N) > 0 {
        di as error "  WARNING: `r(N)' rows have missing population; dropping."
        drop if missing(population)
    }

    gen double rate = count_all / population
    gen byte young  = (age_bin == 1)
    drop count_all   // no longer needed
    compress         // shrink data types

    * Monthly distance from event zero, then bin to bin_w months and shift
    * to non-negative integers for factor-variable expansion.
    gen kmonth = ym - ym($event_zero_y, $event_zero_m)
    gen kshift = floor(kmonth / `bin_w') + `k_offset'
    keep if inrange(kshift, 0, `bin_max' + `k_offset')

    qui count
    local n_obs = r(N)
    egen byte v_tag = tag(frtk_id)
    qui count if v_tag == 1
    local n_frtk = r(N)
    drop v_tag
    di "  n_obs=`n_obs'  n_frtk=`n_frtk'"

    * `compact` option: reghdfe uses a more memory-efficient algorithm that
    * avoids materialising the full design matrix at once. Trades speed for
    * memory — necessary for the wide triple-interaction on 24M obs.
    cap noisily reghdfe rate ib`k_ref'.kshift##c.young##c.exposure_std [aw=population], ///
        absorb(frtk_id#age_bin frtk_id#ym age_bin#ym) ///
        cluster(frtk_id) compact
    local rc = _rc

    if `rc' {
        di as error "  reghdfe failed (rc=`rc'); skipping."
        continue
    }

    * --- Harvest triple-interaction coefficients per event-time bin ---
    * k saved to output = LAST calendar month of the bin, so the reference
    * bin (which contains month -1 = Oct 2022) saves as k = -1 — matching
    * the convention used by 6c (monthly) and the Python plotting code.
    local n_harvested = 0
    local missing_ks ""
    forval ks = 0 / `=`bin_max' + `k_offset'' {
        if `ks' == `k_ref' continue
        local kbcc = (`ks' - `k_offset' + 1) * `bin_w' - 1
        local cname "`ks'.kshift#c.young#c.exposure_std"
        local b = .
        local se_v = .
        cap local b = _b[`cname']
        cap local se_v = _se[`cname']
        if !missing(`b') {
            post `pf_es' ("`sample_name'") (`kbcc') ///
                (`b') (`se_v') (`n_obs') (`n_frtk')
            local n_harvested = `n_harvested' + 1
        }
        else {
            local missing_ks "`missing_ks' `kbcc'"
        }
    }
    di "  harvested `n_harvested' triple-interaction coefs (bin width = `bin_w' months)"
    if "`missing_ks'" != "" {
        di "  missing k (omitted/collinear from fit):`missing_ks'"
    }

    * --- Per-spec summary: max|pre|, mean post, joint pre-trend p ---
    local max_pre_abs = .
    local n_post = 0
    local sum_post = 0

    forval ks = 0 / `=`k_ref' - 1' {
        local b = .
        cap local b = _b[`ks'.kshift#c.young#c.exposure_std]
        if !missing(`b') {
            local ab = abs(`b')
            if missing(`max_pre_abs') | `ab' > `max_pre_abs' {
                local max_pre_abs = `ab'
            }
        }
    }
    forval ks = `k_offset' / `=`bin_max' + `k_offset'' {
        local b = .
        cap local b = _b[`ks'.kshift#c.young#c.exposure_std]
        if !missing(`b') {
            local sum_post = `sum_post' + `b'
            local n_post = `n_post' + 1
        }
    }
    local mean_post = .
    if `n_post' > 0 local mean_post = `sum_post' / `n_post'

    * Filter to coefs that actually exist - `test` errors on omitted/
    * collinear terms and `cap` would swallow that silently.
    local pre_test ""
    local n_pre_skipped = 0
    forval ks = 0 / `=`k_ref' - 1' {
        local cname "`ks'.kshift#c.young#c.exposure_std"
        local b = .
        cap local b = _b[`cname']
        if !missing(`b') {
            local pre_test "`pre_test' `cname'"
        }
        else {
            local n_pre_skipped = `n_pre_skipped' + 1
        }
    }
    local pre_joint_p = .
    if "`pre_test'" != "" {
        cap noisily test `pre_test'
        local test_rc = _rc
        if !`test_rc' {
            local pre_joint_p = r(p)
        }
        else {
            di as error "  pre-trend test failed (rc=`test_rc')"
        }
    }
    if `n_pre_skipped' > 0 {
        di "  pre-trend test: skipped `n_pre_skipped' missing pre-period coef(s)"
    }

    post `pf_sum' ("`sample_name'") (`max_pre_abs') (`mean_post') ///
        (`pre_joint_p') (`n_obs') (`n_frtk')
}

postclose `pf_es'
postclose `pf_sum'


* =============================================================================
* Section 3: Save coefficient files
* =============================================================================

use `f_es', clear
sort sample k
compress
save "$data\coefs_event_study_continuous_share", replace
export delimited using "$output\coefficients\coef_event_study_continuous_share.csv", replace

use `f_sum', clear
sort sample
compress
save "$data\coefs_event_study_continuous_share_summary", replace
export delimited using "$output\coefficients\coef_event_study_continuous_share_summary.csv", replace


* =============================================================================
* Section 4: Append §7d to $RESULTS_MD
* =============================================================================

file open mdfh using "$mdfrag\section_07d.md", write replace text
file write mdfh "## §7d: Event-study, continuous exposure x young (reghdfe, linear OLS)" _n
file write mdfh "" _n
file write mdfh ///
    "Event-study analogue of §9c (triple-diff with continuous exposure x " ///
    "young). Outcome: per-capita employment rate. Same FE structure as §8 " ///
    "(foretak x age + foretak x time + age x time), weighted by population, " ///
    "clustered at foretak. Coefficient gamma_k = differential rate effect at " ///
    "event time k for young workers per SD of exposure_std, relative to " ///
    "k = -1 (October 2022). Coefficients are in workers-per-inhabitant units; " ///
    "multiply by 100 000 for 'per 100 000 inhabitants per SD exposure' " ///
    "interpretation." _n
file write mdfh "" _n
* 2-month bin output: bin's reported k is the LAST month of the bin, so post
* k values are 1, 3, 5, 7, ..., 31. Show every-3rd bin (~ every 6 months).
file write mdfh ///
    "| Sample | k=1 | k=7 | k=13 | k=19 | k=25 | max abs pre | joint pre-trend p | N obs | N frtk |" _n
file write mdfh "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|" _n

local samp_name "headline_priv"

foreach kval of numlist 1 7 13 19 25 {
    local r`kval' "."
    preserve
    cap noisily use "$data\coefs_event_study_continuous_share", clear
    if !_rc {
        qui keep if sample == "`samp_name'" & k == `kval'
        if _N == 1 {
            local cv = coef[1]
            if !missing(`cv') {
                local r`kval' : di %9.6f `cv'
                local r`kval' = strtrim("`r`kval''")
            }
        }
    }
    restore
}

local rmp "."
local rpp "."
local rno "."
local rnv "."
preserve
cap noisily use "$data\coefs_event_study_continuous_share_summary", clear
if !_rc {
    qui keep if sample == "`samp_name'"
    if _N == 1 {
        local mp = max_pre_abs[1]
        local pp = pre_joint_p[1]
        local no = n_obs[1]
        local nv = n_frtk[1]
        if !missing(`mp') local rmp : di %9.6f `mp'
        if !missing(`pp') local rpp : di %6.3f `pp'
        if !missing(`no') local rno : di %12.0fc `no'
        if !missing(`nv') local rnv : di %12.0fc `nv'
        foreach v in rmp rpp rno rnv {
            local `v' = strtrim("``v''")
        }
    }
}
restore

file write mdfh ///
    "| `samp_name' | `r1' | `r7' | `r13' | `r19' | `r25' | `rmp' | `rpp' | `rno' | `rnv' |" _n

file write mdfh "" _n
file write mdfh "Full event-time coefficient series in " ///
    "coefficients/coef_event_study_continuous_share.csv; per-spec summary in " ///
    "coefficients/coef_event_study_continuous_share_summary.csv." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 6d complete. Continuous-exposure event-study coefs saved; section_07d fragment + $RESULTS_MD rebuilt."

cap log close script6d
