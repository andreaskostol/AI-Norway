* =============================================================================
* 10b_fig_alt_triplediff.do : intensive-margin triple-diff coefficient plot
* =============================================================================
* Reads pre-saved coefs from script 8. Self-contained: makes the figure,
* writes section_12.md, then rebuilds the master markdown. Re-running this
* script does NOT require re-running any regression.
*
* Inputs:  $data\coefs_alt.dta
* Outputs: $output\figures\fig_alt_triplediff.png
* Appends: §12 to $RESULTS_MD
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

cap mkdir "$output\figures"


* =============================================================================
* Section 1: Load coefficient series
* =============================================================================

cap confirm file "$data\coefs_alt.dta"
if _rc {
    di as error "  $data\coefs_alt.dta not found; figure step aborted."
    exit 0
}

use "$data\coefs_alt", clear
keep if coef_name == "c.young#c.post#c.exposure_std"

qui count
if r(N) == 0 {
    di as error "  no triple-diff coefs in coefs_alt; figure step aborted."
    exit 0
}

gen lo = estimate - 1.96 * se
gen hi = estimate + 1.96 * se


* =============================================================================
* Section 2: Outcome ordering on x-axis
* =============================================================================

gen byte out_ord = .
replace out_ord = 1 if outcome == "ln_wage"
replace out_ord = 2 if outcome == "position"
replace out_ord = 3 if outcome == "ln_basehours"
replace out_ord = 4 if outcome == "overtime"

* Drop any row whose outcome string didn't match (defensive — protects against
* unexpected labels causing empty plots).
drop if missing(out_ord)
qui count
if r(N) == 0 {
    di as error "  no rows with recognized outcome labels; figure step aborted."
    exit 0
}

gen double xpos = out_ord


* =============================================================================
* Section 3: Coefficient plot (point + 95% CI whisker)
* =============================================================================

cap noisily twoway ///
    (rcap lo hi xpos, lcolor(gs5) lwidth(thin)) ///
    (scatter estimate xpos, mcolor(navy) ms(O) msize(large)) ///
    , legend(off) ///
      ylabel(, format(%6.3f) labsize(medium) angle(horizontal) glcolor(gs14)) ///
      xlabel(1 "log monthly wage" 2 "Position pct" 3 "log base hours" 4 "Overtime hours", ///
             labsize(medium) noticks) ///
      xtitle("") ytitle("Triple-interaction coefficient (Young x Post x Exposure)", ///
                       size(medium)) ///
      yline(0, lp(solid) lcolor(black) lwidth(thin)) ///
      title("Intensive-margin outcomes: triple-difference estimates", ///
            size(large) color(black)) ///
      subtitle("Linear OLS with foretak x age + foretak x month + age x month FE", ///
               size(medium) color(gs5)) ///
      note("Sample: private-sector foretak (sekt = 3), all FT/PT. " ///
           "95% confidence intervals shown, clustered at foretak. " ///
           "Source: coefficients/coef_alt.csv.", size(small) color(gs5)) ///
      graphregion(color(white) margin(medium)) ///
      plotregion(color(white) lcolor(black) lwidth(thin)) ///
      xsize(11) ysize(7)
local rc = _rc

if !`rc' cap noisily graph export "$output\figures\fig_alt_triplediff.png", ///
    replace width(2800)
if `rc' di as error "  alt-outcome figure step failed (rc=`rc'); continuing"


* =============================================================================
* Section 4: Append §12 to $RESULTS_MD
* =============================================================================

file open mdfh using "$mdfrag\section_12.md", write replace text
file write mdfh "## §12: Triple-diff intensive-margin figure" _n
file write mdfh "" _n
file write mdfh "Triple-difference (young x post x exposure) on intensive-margin " ///
    "outcomes (log monthly wage, position pct, log base hours, overtime hours). " ///
    "Built by 10b_fig_alt_triplediff.do from coefficients/coef_alt.csv." _n
file write mdfh "" _n
file write mdfh "![](figures/fig_alt_triplediff.png)" _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n
file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 10b complete. Alt-outcomes figure saved; section_12 fragment + $RESULTS_MD rebuilt."
