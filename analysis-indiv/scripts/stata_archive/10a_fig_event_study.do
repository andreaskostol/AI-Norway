* =============================================================================
* 10a_fig_event_study.do : six-panel Poisson event-study figure
* =============================================================================
* Reads pre-saved coef files from script 6. Self-contained: makes the figure,
* writes section_11.md, then rebuilds the master markdown. Re-running this
* script does NOT require re-running any regression.
*
* Inputs:  $data\coefs_event_study.dta
* Outputs: $output\figures\fig_event_study_q5_by_age.png
* Appends: §11 to $RESULTS_MD
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

cap mkdir "$output\figures"


* =============================================================================
* Section 1: Load coefficient series and add reference (k = -1)
* =============================================================================

cap confirm file "$data\coefs_event_study.dta"
if _rc {
    di as error "  $data\coefs_event_study.dta not found; figure step aborted."
    exit 0
}

use "$data\coefs_event_study", clear
keep if sample == "headline_priv" & ai_q == 5

qui count
if r(N) == 0 {
    di as error "  no Q5 coefs in headline_priv; figure step aborted."
    exit 0
}

gen lo = coef - 1.96 * se
gen hi = coef + 1.96 * se

* Add the reference (k = -1) row with coef = 0 so the line crosses the omitted point.
preserve
keep age_bin
duplicates drop
gen k = -1
gen coef = 0
gen se   = .
gen lo   = 0
gen hi   = 0
tempfile ref0
save `ref0'
restore

append using `ref0'
sort age_bin k


* =============================================================================
* Section 2: Per-panel plots, one per age bin
* =============================================================================

foreach a in 1 2 3 4 {
    if `a' == 1 local age_lab "Ages 21--30"
    if `a' == 2 local age_lab "Ages 31--40"
    if `a' == 3 local age_lab "Ages 41--50"
    if `a' == 4 local age_lab "Ages 51--60"

    * Capture row count to a local; r(N) can be reset by graphics/regression
    * commands further down, so don't trust it across boundaries.
    qui count if age_bin == `a'
    local n_a = r(N)
    local panel_rc = 0

    if `n_a' > 0 {
        cap noisily twoway (rarea lo hi k if age_bin == `a', color(navy%25) lwidth(none)) ///
               (line  coef k if age_bin == `a', lcolor(navy) lwidth(medthick)) ///
            , legend(off) ///
              title("`age_lab'", size(medlarge) color(black)) ///
              ytitle("") xtitle("") ///
              ylabel(, angle(horizontal) format(%4.2f) labsize(medium) glcolor(gs14)) ///
              xlabel(-24(12)36, labsize(medium)) ///
              xline(-1, lp(shortdash) lcolor(gs8)) ///
              yline(0,  lp(solid)     lcolor(black) lwidth(thin)) ///
              graphregion(color(white) margin(medium)) ///
              plotregion(color(white) lcolor(black) lwidth(thin)) ///
              name(panel_`a', replace) nodraw
        local panel_rc = _rc
    }

    if `n_a' == 0 | `panel_rc' {
        di as error "  panel `a' has no plottable data (n=`n_a', rc=`panel_rc'); using empty placeholder"
        cap noisily twoway scatteri 0 0, msymbol(none) ///
            title("`age_lab' (no data)", size(medlarge) color(gs8)) ///
            ytitle("") xtitle("") ///
            xlabel(-24(12)36, labsize(medium)) ///
            graphregion(color(white) margin(medium)) ///
            plotregion(color(white) lcolor(black) lwidth(thin)) ///
            name(panel_`a', replace) nodraw
        local placeholder_rc = _rc
        if `placeholder_rc' {
            di as error "  placeholder for panel `a' also failed (rc=`placeholder_rc')"
        }
    }
}


* =============================================================================
* Section 3: Combine and export
* =============================================================================

cap noisily graph combine panel_1 panel_2 panel_3 panel_4 panel_5 panel_6, ///
    rows(2) cols(3) imargin(medium) ///
    title("Employment of Q5 vs. Q3 occupations, by age bin", ///
          size(large) color(black)) ///
    subtitle("Private-sector sample, Poisson with foretak x q and foretak x month FE", ///
             size(medium) color(gs5)) ///
    b1title("Months from October 2022", size(medium)) ///
    l1title("Coefficient on Q5 dummy (log)", size(medium)) ///
    note("Reference: q = 3 (median exposure), k = -1 (October 2022). Shaded bands are " ///
         "95% confidence intervals, clustered at foretak.", size(small) color(gs5)) ///
    graphregion(color(white) margin(medium)) ///
    name(es_combined, replace)
local rc = _rc
if !`rc' cap noisily graph export "$output\figures\fig_event_study_q5_by_age.png", ///
    replace width(2800)
if `rc' di as error "  event-study figure step failed (rc=`rc'); continuing"
graph drop _all


* =============================================================================
* Section 4: Append §11 to $RESULTS_MD
* =============================================================================

file open mdfh using "$mdfrag\section_11.md", write replace text
file write mdfh "## §11: Event-study figure" _n
file write mdfh "" _n
file write mdfh "BCC equation 4.1, Q5 vs. Q3 employment by age bin, private-sector sample. " ///
    "Reference quintile: Q3 (median exposure); Q1 dominated by winter-construction seasonality. " ///
    "Built by 10a_fig_event_study.do from coefficients/coef_event_study.csv." _n
file write mdfh "" _n
file write mdfh "![](figures/fig_event_study_q5_by_age.png)" _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 10a complete. Event-study figure saved; section_11 fragment + $RESULTS_MD rebuilt."
