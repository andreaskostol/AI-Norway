* =============================================================================
* 6c_event_study_share.do : event-study on per-capita employment rate (linear OLS)
* =============================================================================
* Parallel to 6_event_study_bcc.do (Poisson on count) but with reghdfe on
* per-capita employment RATE. Robust to demographic age-composition shifts
* (denominator is the national age cohort population from SSB 07459, not
* firm-internal totals). Linear, fast, no log transform.
*
*   rate_{f,q,t} = count_{f,q,t} / N_{a,t}    [estimated separately by age_bin a]
*
* where N_{a,t} = SSB Statistikkbanken population in age_bin a, month t.
*
*   rate_{f,q,t} = α_{f,q} + β_{f,t}
*                + Σ_{q'≠1} Σ_{j≠-1} γ_{q',j} · 1{t=j} · 1{q'=q} + ε
*
* Estimated separately by age_bin. Reference: q = 1, k = -1 (October 2022).
* Standard errors clustered at foretak. Cells weighted by population.
*
* Inputs:  $data\cells_flagged.dta
*          $data\population_by_agebin_ym.dta  (built by script 5b)
* Outputs: $data\coefs_event_study_share.dta            (per (k, q) coef + SE)
*          $data\coefs_event_study_share_summary.dta    (per spec summary)
*          $output\coefficients\coef_event_study_share.csv
*          $output\coefficients\coef_event_study_share_summary.csv
* Appends: §7c to $RESULTS_MD
*
* Design rationale: see DESIGN_CHOICES.md sections 2 (linear OLS alternatives),
* 19 (per-capita rate over share), 20 (population data quarterly → monthly).
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

tempname pf_es pf_sum
tempfile f_es f_sum

postfile `pf_es' str20 sample byte age_bin int k byte ai_q ///
    double coef double se long n_obs long n_frtk ///
    using `f_es', replace

postfile `pf_sum' str20 sample byte age_bin double max_pre_abs ///
    double mean_post_q5 double pre_joint_p long n_obs long n_frtk ///
    using `f_sum', replace


* =============================================================================
* Section 2: Sample × age × estimate event study
* =============================================================================

local kmin = -24
local kmax = 36
local k_offset = -`kmin'
local k_ref    = `k_offset' - 1

local n_samples = 1
local sample_1 "headline_priv"
local flag_1   "in_headline_priv"

forval s = 1/`n_samples' {

    local sample_name "`sample_`s''"
    local sample_flag "`flag_`s''"

    di _n "==========================================="
    di "EVENT STUDY (share)  |  sample = `sample_name'"
    di "==========================================="

    * Aggregate to (frtk, age, q, ym) cells; merge in (age_bin, ym) population;
    * compute rate = count / population. Each (age, ym) row gets the same
    * national population, so rate is comparable across firms within a cohort.
    use "$data\cells_flagged", clear
    keep if `sample_flag' == 1

    collapse (sum) y_count = count_all, by(frtk_id age_bin ai_q ym)

    cap confirm file "$data\population_by_agebin_ym.dta"
    if _rc {
        di as error "  population_by_agebin_ym.dta not found — run 5b_population.do first."
        exit 198
    }
    merge m:1 age_bin ym using "$data\population_by_agebin_ym", ///
        keep(master match) keepusing(population) nogen
    qui count if missing(population)
    if r(N) > 0 {
        di as error "  WARNING: `r(N)' rows have missing population; dropping."
        drop if missing(population)
    }

    gen double rate = y_count / population

    gen kshift = ym - ym($event_zero_y, $event_zero_m) + `k_offset'
    keep if inrange(kshift, 0, `kmax' + `k_offset')

    tempfile sample_data
    compress
    save `sample_data', replace

    forval a = 1/4 {

        use `sample_data', clear
        keep if age_bin == `a'

        qui count
        local n_obs = r(N)
        local n_frtk = 0
        if `n_obs' > 0 {
            egen byte v_tag = tag(frtk_id)
            qui count if v_tag == 1
            local n_frtk = r(N)
            drop v_tag
        }
        di _n "--- age_bin = `a' (n_obs = `n_obs', n_frtk = `n_frtk') ---"

        * Reference quintile: Q3 (median exposure); Q1 dominated by
        * winter-construction seasonality.
        cap noisily reghdfe rate ib`k_ref'.kshift##ib3.ai_q [aw=population], ///
            absorb(frtk_id#ai_q frtk_id#ym) ///
            cluster(frtk_id)
        local rc = _rc

        if `rc' {
            di as error "  reghdfe failed (rc=`rc'); skipping age_bin `a'."
            continue
        }

        * --- Harvest (k, q) coefficients (skip q = 3, the reference) ---
        forval ks = 0 / `=`kmax' + `k_offset'' {
            if `ks' == `k_ref' continue
            local kbcc = `ks' - `k_offset'
            forval q = 1/5 {
                if `q' == 3 continue   // reference q = 3 omitted
                local cname "`ks'.kshift#`q'.ai_q"
                local b = .
                local se_v = .
                cap local b = _b[`cname']
                cap local se_v = _se[`cname']
                if !missing(`b') {
                    post `pf_es' ("`sample_name'") (`a') (`kbcc') (`q') ///
                        (`b') (`se_v') (`n_obs') (`n_frtk')
                }
            }
        }

        * --- Per-spec summary: max|pre|, mean post Q5, joint pre-trend p ---
        local max_pre_abs = .
        local n_post = 0
        local sum_post = 0

        forval ks = 0 / `=`k_ref' - 1' {
            local b = .
            cap local b = _b[`ks'.kshift#5.ai_q]
            if !missing(`b') {
                local ab = abs(`b')
                if missing(`max_pre_abs') | `ab' > `max_pre_abs' {
                    local max_pre_abs = `ab'
                }
            }
        }
        forval ks = `k_offset' / `=`kmax' + `k_offset'' {
            local b = .
            cap local b = _b[`ks'.kshift#5.ai_q]
            if !missing(`b') {
                local sum_post = `sum_post' + `b'
                local n_post = `n_post' + 1
            }
        }
        local mean_post = .
        if `n_post' > 0 local mean_post = `sum_post' / `n_post'

        * Filter to coefs that actually exist — `test` errors on omitted/
        * collinear terms and `cap` would swallow that silently.
        local pre_test ""
        local n_pre_skipped = 0
        forval ks = 0 / `=`k_ref' - 1' {
            local cname "`ks'.kshift#5.ai_q"
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
                di as error "  pre-trend test failed (rc=`test_rc') for age_bin `a'"
            }
        }
        if `n_pre_skipped' > 0 {
            di "  pre-trend test for age_bin `a': skipped `n_pre_skipped' missing pre-period coef(s)"
        }

        post `pf_sum' ("`sample_name'") (`a') (`max_pre_abs') (`mean_post') ///
            (`pre_joint_p') (`n_obs') (`n_frtk')
    }
}

postclose `pf_es'
postclose `pf_sum'


* =============================================================================
* Section 3: Save coefficient files
* =============================================================================

use `f_es', clear
sort sample age_bin ai_q k
compress
save "$data\coefs_event_study_share", replace
export delimited using "$output\coefficients\coef_event_study_share.csv", replace

use `f_sum', clear
sort sample age_bin
compress
save "$data\coefs_event_study_share_summary", replace
export delimited using "$output\coefficients\coef_event_study_share_summary.csv", replace


* =============================================================================
* Section 4: Append §7c to $RESULTS_MD
* =============================================================================

file open mdfh using "$mdfrag\section_07c.md", write replace text
file write mdfh "## §7c: Event-study on per-capita employment rate (reghdfe, linear OLS)" _n
file write mdfh "" _n
file write mdfh ///
    "Linear OLS analogue to §7 (Poisson). Outcome: workers per inhabitant in " ///
    "the cohort: rate = count / N_(age_bin, ym), where N is SSB age-cohort " ///
    "population. Robust to demographic age-composition shifts. Estimated " ///
    "separately by age_bin with foretak x q + foretak x time FE; weighted by " ///
    "population. Coefficient = γ_{Q5, k}: change in Q5 employment rate " ///
    "relative to Q3 (median exposure), at event time k vs k = -1 (October 2022). Coefficients " ///
    "are in workers-per-inhabitant units; very small numerically — multiply " ///
    "by 100 000 for 'per 100 000 inhabitants' interpretation." _n
file write mdfh "" _n
file write mdfh ///
    "| Age bin | k=0 | k=6 | k=12 | k=18 | k=24 | max abs pre | joint pre-trend p | N obs | N frtk |" _n
file write mdfh "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|" _n

forval a = 1/4 {

    local age_label "?"
    if `a' == 1 local age_label "21-30"
    if `a' == 2 local age_label "31-40"
    if `a' == 3 local age_label "41-50"
    if `a' == 4 local age_label "51-60"

    foreach kval of numlist 0 6 12 18 24 {
        local r`kval' "."
        preserve
        cap noisily use "$data\coefs_event_study_share", clear
        if !_rc {
            qui keep if sample == "headline_priv" & ai_q == 5 & age_bin == `a' & k == `kval'
            if _N == 1 {
                local cv = coef[1]
                if !missing(`cv') {
                    local r`kval' : di %7.4f `cv'
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
    cap noisily use "$data\coefs_event_study_share_summary", clear
    if !_rc {
        qui keep if sample == "headline_priv" & age_bin == `a'
        if _N == 1 {
            local mp = max_pre_abs[1]
            local pp = pre_joint_p[1]
            local no = n_obs[1]
            local nv = n_frtk[1]
            if !missing(`mp') local rmp : di %7.4f `mp'
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
        "| `age_label' | `r0' | `r6' | `r12' | `r18' | `r24' | `rmp' | `rpp' | `rno' | `rnv' |" _n
}

file write mdfh "" _n
file write mdfh "Full event-time x quintile coefficient series in " ///
    "coefficients/coef_event_study_share.csv; per-spec summary in " ///
    "coefficients/coef_event_study_share_summary.csv." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 6c complete. Share-based event-study coefs saved; section_07c fragment + $RESULTS_MD rebuilt."
