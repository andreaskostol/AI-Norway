* =============================================================================
* 5b_population.do : load SSB population data, aggregate to (age_bin, ym)
* =============================================================================
* Loads ssb_population_by_age_quarterly.csv (1-year ages, quarterly snapshots
* interpolated from SSB Statistikkbanken table 07459) and produces a Stata
* dataset with population summed to our six age_bins, expanded to monthly.
*
* Each month within a quarter inherits that quarter's mid-quarter population
* (small approximation; population changes slowly enough that this is fine).
*
* Used by 6c_event_study_share.do and 8c_share_triplediff.do as the denominator
* for per-capita rate normalization (rate = count / population).
*
* Inputs:  $data\ssb_population_by_age_quarterly.csv
* Outputs: $data\population_by_agebin_ym.dta  (age_bin, ym, population)
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"


* =============================================================================
* Section 1: Load population CSV
* =============================================================================

cap confirm file "$data\ssb_population_by_age_quarterly.csv"
if _rc {
    di as error "  $data\ssb_population_by_age_quarterly.csv not found. Aborting."
    exit 198
}

import delimited "$data\ssb_population_by_age_quarterly.csv", ///
    clear varnames(1) stringcols(1)

confirm variable date
confirm variable age
confirm variable population

* date column has format "YYYY-Qn", e.g. "2021-Q1"
gen long yr = real(substr(date, 1, 4))
gen byte q  = real(substr(date, 7, 1))
assert inrange(q, 1, 4)
assert !missing(yr)


* =============================================================================
* Section 2: Map ages to age_bin (matches script 3 / 0_settings.do convention)
* =============================================================================
*   1: 21-30   2: 31-40   3: 41-50   4: 51-60
* age_bin is missing for ages < 21 or > 60; those rows are dropped.

destring age, replace
gen byte age_bin = .
replace age_bin = 1 if inrange(age, 21, 30)
replace age_bin = 2 if inrange(age, 31, 40)
replace age_bin = 3 if inrange(age, 41, 50)
replace age_bin = 4 if inrange(age, 51, 60)
keep if !missing(age_bin)


* =============================================================================
* Section 3: Aggregate to (age_bin, year, quarter)
* =============================================================================

collapse (sum) population, by(age_bin yr q)


* =============================================================================
* Section 4: Expand to monthly
* =============================================================================
* Each (age_bin, yr, q) row produces 3 monthly rows: month_in_quarter = 1, 2, 3.
* Month index = (q - 1) * 3 + month_in_quarter.

expand 3
bys age_bin yr q: gen byte mo_in_q = _n
gen byte mo = (q - 1) * 3 + mo_in_q
gen ym = ym(yr, mo)
format %tm ym

keep age_bin ym population
sort age_bin ym
order age_bin ym population

compress
save "$data\population_by_agebin_ym", replace

qui count
di _n "Population dataset: `r(N)' (age_bin x ym) rows."
qui sum population
di "  population range: `r(min)' to `r(max)'"
qui levelsof ym, local(allmonths)
di "  unique months: " `: word count `allmonths''
qui levelsof age_bin, local(allbins)
di "  unique age_bins: " `: word count `allbins''


* =============================================================================
* Section 5: Append to §6 markdown so the run log notes the population step
* =============================================================================
* Note: this script runs after 5_apply_restrictions.do which writes section_06.md
* with replace. We append a short note rather than rewriting that section.

di _n "Script 5b complete. Population dataset saved to $data\population_by_agebin_ym.dta."
