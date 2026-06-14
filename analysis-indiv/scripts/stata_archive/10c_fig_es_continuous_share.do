* =============================================================================
* 10c_fig_es_continuous_share.do : event-study figure for the continuous-exposure
*                                   x young triple (linear OLS on per-capita rate)
* =============================================================================
* Reads pre-saved coef file from script 6d. Self-contained: makes the figure,
* writes section_13.md, then rebuilds the master markdown. Re-running this
* script does NOT require re-running any regression.
*
* Inputs:  $data\coefs_event_study_continuous_share.dta
*          $data\coefs_event_study_continuous_share_summary.dta
* Outputs: $output\figures\fig_es_continuous_share.png
* Appends: §13 to $RESULTS_MD
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

cap mkdir "$output\figures"


* =============================================================================
* Section 1: Load coefficients, scale to per-100k, add k = -1 reference row
* =============================================================================

cap confirm file "$data\coefs_event_study_continuous_share.dta"
if _rc {
    di as error "  $data\coefs_event_study_continuous_share.dta not found; figure step aborted."
    exit 0
}

use "$data\coefs_event_study_continuous_share", clear
keep if sample == "headline_priv"

qui count
if r(N) == 0 {
    di as error "  no rows in coefs_event_study_continuous_share; figure step aborted."
    exit 0
}

* Scale to "per 100 000 inhabitants per SD exposure" so the y-axis is readable.
gen double coef_p100k = coef * 100000
gen double se_p100k   = se   * 100000
gen double lo = coef_p100k - 1.96 * se_p100k
gen double hi = coef_p100k + 1.96 * se_p100k

* Reference row (k = -1, omitted from regression) so the line crosses zero at -1.
local nk = _N
set obs `=`nk' + 1'
replace k          = -1   in `=`nk' + 1'
replace coef_p100k = 0    in `=`nk' + 1'
replace lo         = 0    in `=`nk' + 1'
replace hi         = 0    in `=`nk' + 1'

sort k


* =============================================================================
* Section 2: Pull pre-trend p and N for the figure note
* =============================================================================

local pp_str ""
local nobs_str ""
local nfrtk_str ""
preserve
cap noisily use "$data\coefs_event_study_continuous_share_summary", clear
if !_rc {
    qui keep if sample == "headline_priv"
    if _N == 1 {
        local pp = pre_joint_p[1]
        local no = n_obs[1]
        local nv = n_frtk[1]
        if !missing(`pp') {
            local pp_str : di %5.3f `pp'
            local pp_str = strtrim("`pp_str'")
        }
        if !missing(`no') {
            local nobs_str : di %12.0fc `no'
            local nobs_str = strtrim("`nobs_str'")
        }
        if !missing(`nv') {
            local nfrtk_str : di %12.0fc `nv'
            local nfrtk_str = strtrim("`nfrtk_str'")
        }
    }
}
restore


* =============================================================================
* Section 3: Plot
* =============================================================================

local note1 "Sample: private-sector foretak (sekt = 3), Norwegian register data."
local note2 "Reference: k = -1 (October 2022, omitted from regression)."
local note3 "Specification: reghdfe rate = count/N(age,month) on i.k##c.young##c.exposure_std,"
local note4 "absorb foretak x age + foretak x month + age x month, weighted by population, clustered at foretak."
local note5 "Coefficient: differential rate change at event-time k for young (ages 22-25) per SD increase in"
local note6 "Eloundou exposure, in workers per 100 000 cohort inhabitants. 95% CI shown."
local note7 ""
local note8 "Joint pre-trend p = `pp_str'.  N obs = `nobs_str',  N foretak = `nfrtk_str'."

cap noisily twoway ///
    (rarea lo hi k, color(navy%25) lwidth(none)) ///
    (line  coef_p100k k, lcolor(navy) lwidth(medthick)) ///
    , legend(off) ///
      title("Differential young-cohort employment by AI exposure", ///
            size(medlarge) color(black)) ///
      subtitle("Continuous-exposure event study, per-capita employment rate (linear OLS)", ///
               size(medium) color(gs5)) ///
      ytitle("Workers per 100 000 inhabitants in cohort, per SD exposure", ///
             size(medium)) ///
      xtitle("Months from October 2022", size(medium)) ///
      ylabel(, angle(horizontal) format(%5.1f) labsize(medium) glcolor(gs14)) ///
      xlabel(-24(6)36, labsize(medium)) ///
      xline(-1, lp(shortdash) lcolor(gs8)) ///
      yline(0,  lp(solid)     lcolor(black) lwidth(thin)) ///
      note("`note1'" "`note2'" "`note3'" "`note4'" "`note5'" "`note6'" "`note7'" "`note8'", ///
           size(small) color(gs5) margin(medium)) ///
      graphregion(color(white) margin(medium)) ///
      plotregion(color(white) lcolor(black) lwidth(thin)) ///
      xsize(13) ysize(8) ///
      name(es_cont, replace)
local rc = _rc

if !`rc' cap noisily graph export "$output\figures\fig_es_continuous_share.png", ///
    replace width(3200)
if `rc' di as error "  continuous-exposure event-study figure failed (rc=`rc'); continuing"
graph drop _all


* =============================================================================
* Section 4: Append §13 to $RESULTS_MD
* =============================================================================

file open mdfh using "$mdfrag\section_13.md", write replace text
file write mdfh "## §13: Continuous-exposure event-study figure" _n
file write mdfh "" _n
file write mdfh "Event-study analogue of §9c (triple-diff with continuous exposure x " ///
    "young). Coefficient gamma_k = differential employment rate at event time k for " ///
    "young workers per SD of Eloundou exposure, scaled to workers per 100 000 cohort " ///
    "inhabitants. Built by 10c_fig_es_continuous_share.do from " ///
    "coefficients/coef_event_study_continuous_share.csv." _n
file write mdfh "" _n
file write mdfh "![](figures/fig_es_continuous_share.png)" _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 10c complete. Continuous-exposure event-study figure saved; section_13 fragment + $RESULTS_MD rebuilt."
