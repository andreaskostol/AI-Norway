* =============================================================================
* 6b_event_study_linear.do : linear-OLS analogue of script 6
* =============================================================================
* Same BCC eq 4.1 design as 6_event_study_bcc.do but with reghdfe (linear OLS)
* on log(count + 1) instead of ppmlhdfe (Poisson). Matches Andreas's spec
* (real_frontier_event_study.py) and runs ~10x faster than Poisson.
*
*   y_{f,q,t} = log(count_{f,q,t} + 1)
*   y_{f,q,t} = α_{f,q} + β_{f,t}
*             + Σ_{q'≠1} Σ_{j≠-1} γ_{q',j} · 1{t = j} · 1{q' = q} + ε
*
* Estimated separately by age_bin. Reference: q = 1, k = -1 (October 2022).
* Standard errors clustered at foretak.
*
* Inputs:  $data\cells_flagged.dta
* Outputs: $data\coefs_event_study_lin.dta            (per (k, q) coef + SE)
*          $data\coefs_event_study_lin_summary.dta    (per spec summary)
*          $output\coefficients\coef_event_study_lin.csv
*          $output\coefficients\coef_event_study_lin_summary.csv
* Appends: §7b to $RESULTS_MD
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
local k_offset = -`kmin'                     // = 24
local k_ref    = `k_offset' - 1              // = 23 corresponds to k = -1

* Sample loop (currently single sample; left as a loop for easy extension).
local n_samples = 1
local sample_1 "headline_priv"
local flag_1   "in_headline_priv"
local out_1    "count_all"

forval s = 1/`n_samples' {

    local sample_name "`sample_`s''"
    local sample_flag "`flag_`s''"
    local outcome_var "`out_`s''"

    di _n "==========================================="
    di "EVENT STUDY (LINEAR)  |  sample = `sample_name'  |  outcome = `outcome_var'"
    di "==========================================="

    * Aggregate to (frtk, age, q, ym) cells for this sample
    use "$data\cells_flagged", clear
    keep if `sample_flag' == 1

    collapse (sum) y_count = `outcome_var', by(lopenr_foretak age_bin ai_q ym)
    egen long frtk_id = group(lopenr_foretak)
    gen double y = ln(y_count + 1)
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
        egen byte v_tag = tag(frtk_id)
        qui count if v_tag == 1
        local n_frtk = r(N)
        drop v_tag
        di _n "--- age_bin = `a' (n_obs = `n_obs', n_frtk = `n_frtk') ---"

        * --- Estimation: BCC eq 4.1, linear OLS on log(count + 1) ---
        * Reference quintile: Q3 (median exposure); Q1 dominated by
        * winter-construction seasonality.
        cap noisily reghdfe y ib`k_ref'.kshift##ib3.ai_q, ///
            absorb(frtk_id#ai_q frtk_id#ym) ///
            cluster(frtk_id)
        local rc = _rc

        if `rc' {
            di as error "  reghdfe failed (rc=`rc'); skipping."
            continue
        }

        * --- Harvest (k, q) coefficients (skip q = 3, the reference) ---
        forval ks = 0 / `=`kmax' + `k_offset'' {

            if `ks' == `k_ref' continue   // reference k = -1 omitted

            local kbcc = `ks' - `k_offset'

            forval q = 1/5 {

                if `q' == 3 continue   // reference q = 3 omitted

                local cname "`ks'.kshift#`q'.ai_q"
                local b = .
                local s = .
                cap local b = _b[`cname']
                cap local s = _se[`cname']

                if !missing(`b') {
                    post `pf_es' ("`sample_name'") (`a') (`kbcc') (`q') ///
                        (`b') (`s') (`n_obs') (`n_frtk')
                }
            }
        }

        * --- Per-spec summary: max|pre| (Q5), mean post Q5, joint pre-trend p ---
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

        * Joint Wald test of pre-trend (Q5 only): all γ_{q=5, k<-1} = 0
        local pre_test ""
        forval ks = 0 / `=`k_ref' - 1' {
            local pre_test "`pre_test' `ks'.kshift#5.ai_q"
        }
        local pre_joint_p = .
        cap test `pre_test'
        if !_rc local pre_joint_p = r(p)

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
save "$data\coefs_event_study_lin", replace
export delimited using "$output\coefficients\coef_event_study_lin.csv", replace

use `f_sum', clear
sort sample age_bin
compress
save "$data\coefs_event_study_lin_summary", replace
export delimited using "$output\coefficients\coef_event_study_lin_summary.csv", replace


* =============================================================================
* Section 4: Append §7b to $RESULTS_MD
* =============================================================================
* Build by direct lookup (mirrors §7 in script 6, robust to sparse cells).

file open mdfh using "$mdfrag\section_07b.md", write replace text
file write mdfh "## §7b: Event-study coefficients (linear OLS, log(count + 1))" _n
file write mdfh "" _n
file write mdfh ///
    "BCC equation 4.1 with linear OLS via reghdfe on log(count + 1), " ///
    "matching Andreas's spec. Same FE structure as §7 (frtk x ai_q + frtk x time). " ///
    "Standard errors clustered at foretak. Sample: private-sector foretak. " ///
    "Coefficient = gamma_{Q5, k}: log(count + 1) in the most-exposed quintile " ///
    "relative to Q3 (median exposure), at event time k, relative to k = -1 (October 2022)." _n
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
        cap noisily use "$data\coefs_event_study_lin", clear
        if !_rc {
            qui keep if sample == "headline_priv" & ai_q == 5 & age_bin == `a' & k == `kval'
            if _N == 1 {
                local cv = coef[1]
                if !missing(`cv') {
                    local r`kval' : di %6.3f `cv'
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
    cap noisily use "$data\coefs_event_study_lin_summary", clear
    if !_rc {
        qui keep if sample == "headline_priv" & age_bin == `a'
        if _N == 1 {
            local mp = max_pre_abs[1]
            local pp = pre_joint_p[1]
            local no = n_obs[1]
            local nv = n_frtk[1]
            if !missing(`mp') local rmp : di %6.3f `mp'
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
file write mdfh ///
    "Full event-time x quintile coefficient series in " ///
    "coefficients/coef_event_study_lin.csv; per-spec summary in " ///
    "coefficients/coef_event_study_lin_summary.csv." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 6b complete. Linear event-study coefs saved; section_07b fragment + $RESULTS_MD rebuilt."
