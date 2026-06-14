* =============================================================================
* 6_event_study_bcc.do : BCC equation 4.1 event study, run by age bin × sample
* =============================================================================
* For each (sample variant) × (age bin), run
*
*   log E[y_{v,q,t}] = α_{v,q} + β_{v,t}
*                    + Σ_{q'≠1} Σ_{j≠-1} γ_{q',j} · 1{t = j} · 1{q' = q} + ε
*
* with `ppmlhdfe`, absorbing frtk × q (α) and frtk × t (β). This is exactly
* BCC equation 4.1 ; the firm × time fixed effect β_{v,t} is the central
* addition over the cell-level pipeline. Reference: q = 1, k = -1 (October
* 2022). Standard errors clustered at foretak.
*
* Inputs:  $data\cells_flagged.dta
* Outputs: $data\coefs_event_study.dta            (per (k, q) coef + SE)
*          $data\coefs_event_study_summary.dta   (per spec: max pre / mean post / joint p)
*          $output\coefficients\coef_event_study.csv
*          $output\coefficients\coef_event_study_summary.csv
* Appends: §7 to $RESULTS_MD
*
* Performance: with absorb(frtk#ai_q frtk#ym), the FE dimensions are
* (n_frtk × 5) and (n_frtk × n_months). For the headline (broader) sample
* this is large. Each ppmlhdfe call may take minutes; the BCC-restricted
* samples are much smaller and faster.
*
* Design rationale: see DESIGN_CHOICES.md sections 1 (Poisson PPML), 3
* (BCC eq 4.1 identification), 11 (reference month), 13 (cluster level),
* 15 (sample = headline_priv).
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
* Two postfiles:
*  - per (k, q) coef and SE
*  - per-spec summary (max |pre|, mean post Q5, joint pre-trend p, N)

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

* Event window. Uses BCC's [-24, +36] in months (extends beyond data range
* gracefully via the `inrange(kshift, ...)` filter below).
local kmin = -24
local kmax = 36
local k_offset = -`kmin'                     // = 24
local k_ref    = `k_offset' - 1              // = 23 corresponds to k = -1

* Sample x outcome
* For the headline run we restrict to private-sector foretak (sekt == 3) with
* all workers (FT + PT). Other samples (ft, ft_priv, bcc_full) are still
* defined in cells_flagged.dta and can be re-enabled here for robustness.
local n_samples = 1
local sample_1 "headline_priv"
local flag_1   "in_headline_priv"
local out_1    "count_all"

forval s = 1/`n_samples' {

    local sample_name "`sample_`s''"
    local sample_flag "`flag_`s''"
    local outcome_var "`out_`s''"

    di _n "==========================================="
    di "EVENT STUDY  |  sample = `sample_name'  |  outcome = `outcome_var'"
    di "==========================================="

    * Aggregate to (frtk, age, q, ym) cells for this sample
    use "$data\cells_flagged", clear
    keep if `sample_flag' == 1

    collapse (sum) y = `outcome_var', by(lopenr_foretak age_bin ai_q ym)
    * Numeric foretak ID for ppmlhdfe absorb (older versions reject string factors)
    egen long frtk_id = group(lopenr_foretak)
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

        * --- Estimation: BCC eq 4.1 with firm × q + firm × time FE ---
        * Reference quintile: Q3 (median exposure). Q1 is dominated by
        * winter-construction seasonality that would otherwise leak into the
        * relative differences; Q3 is the cleaner baseline.
        * tolerance(1e-3) is loose enough to converge in fewer iterations on
        * thick BCC-style panels; default 1e-4 is overly precise for this scale.
        cap noisily ppmlhdfe y ib`k_ref'.kshift##ib3.ai_q, ///
            absorb(frtk_id#ai_q frtk_id#ym) ///
            cluster(frtk_id) tolerance(1e-3)
        local rc = _rc

        if `rc' {
            di as error "  ppmlhdfe failed (rc=`rc'); skipping."
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

        * Joint Wald test of pre-trend (Q5 only): all γ_{q=5, k<-1} = 0.
        * Filter to coefs that actually exist in the fit — `test` errors on
        * omitted/collinear terms and `cap` would silently swallow that,
        * leaving pre_joint_p as missing for the whole age bin.
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
save "$data\coefs_event_study", replace
export delimited using "$output\coefficients\coef_event_study.csv", replace

use `f_sum', clear
sort sample age_bin
compress
save "$data\coefs_event_study_summary", replace
export delimited using "$output\coefficients\coef_event_study_summary.csv", replace


* =============================================================================
* Section 4: Append §7 to $RESULTS_MD
* =============================================================================
* Compact summary table: for the headline sample only, by age bin, show Q5
* coefficients at key event times + max |pre| + joint pre-trend p.

* Build §7 markdown table by directly looking up each (age_bin, k) cell from
* coefs_event_study, plus summary stats from coefs_event_study_summary. The
* lookup-loop approach avoids reshape wide, which can fail with conformability
* errors when the data is sparse (some (age_bin, k) cells absent because the
* regression failed to identify that coefficient).

file open mdfh using "$mdfrag\section_07.md", write replace text
file write mdfh "## §7: Event-study coefficients (Poisson, employment count)" _n
file write mdfh "" _n
file write mdfh ///
    "BCC equation 4.1, separately by age bin. Absorb: frtk x ai_q + frtk x time. " ///
    "Standard errors clustered at foretak. Sample: private-sector foretak (sekt = 3), all FT/PT. Coefficient = " ///
    "gamma_{Q5, k}: log-employment in the most-exposed quintile relative to Q3 (median exposure), " ///
    "at event time k, relative to k = -1 (October 2022)." _n
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

    * --- Coefficients at each k for headline x Q5 x age_bin ---
    foreach kval of numlist 0 6 12 18 24 {
        local r`kval' "."
        preserve
        cap noisily use "$data\coefs_event_study", clear
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

    * --- Pre-trend / sample-size summary ---
    local rmp "."
    local rpp "."
    local rno "."
    local rnv "."
    preserve
    cap noisily use "$data\coefs_event_study_summary", clear
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
    "Full event-time x quintile coefficient series for all samples in " ///
    "coefficients/coef_event_study.csv; per-spec summary in " ///
    "coefficients/coef_event_study_summary.csv." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 6 complete. Event-study coefs saved; section_07 fragment + $RESULTS_MD rebuilt."
