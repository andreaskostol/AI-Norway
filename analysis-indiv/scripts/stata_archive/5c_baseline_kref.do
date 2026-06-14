* =============================================================================
* 5c_baseline_kref.do : baseline cohort employment rates at k = -1
* =============================================================================
* Computes the cohort employment share at the regression reference month
* (October 2022 = ym($ref_y, $ref_m)) so the local Python figure script can
* rescale event-study coefficients from 6c/6d into "% of baseline cohort
* employment" instead of "workers per 100 000 inhabitants".
*
* For 6c (Q5 vs Q1 per age_bin):
*   baseline_rate[age_bin, ai_q] = sum of workers in cells at k = -1 in that
*   (age_bin, ai_q) bucket / cohort population in that age_bin at k = -1.
*   The Python figure divides gamma_{Q5,k} by baseline_rate[age_bin, q=5].
*
* For 6d (continuous x young triple):
*   baseline_rate[age_bin] = total workers in age_bin at k = -1 (summed over
*   q & yrke4) / cohort population. The Python figure divides gamma_k by
*   baseline_rate[age_bin=1] (the young cohort).
*
* Inputs:  $data\cells_flagged.dta
*          $data\population_by_agebin_ym.dta  (built by 5b)
* Outputs: $output\coefficients\baseline_kref_by_age_q.csv
*          $output\coefficients\baseline_kref_by_age.csv
*
* No regression — just a sum + divide on cells at one month. Fast.
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

cap confirm file "$data\population_by_agebin_ym.dta"
if _rc {
    di as error "  population_by_agebin_ym.dta not found - run 5b_population.do first."
    exit 198
}

use "$data\cells_flagged", clear
keep if in_headline_priv == 1
keep if ym == ym($ref_y, $ref_m)

qui count
di _n "Cells in headline_priv at reference month: `r(N)'"

merge m:1 age_bin ym using "$data\population_by_agebin_ym", ///
    keep(master match) keepusing(population) nogen
qui count if missing(population)
if r(N) > 0 {
    di as error "  WARNING: `r(N)' rows have missing population; dropping."
    drop if missing(population)
}


* =============================================================================
* Section 1: Per (age_bin, ai_q) baseline rate
* =============================================================================

preserve
collapse (sum) total_count = count_all (first) population, by(age_bin ai_q)
gen double baseline_rate = total_count / population
sort age_bin ai_q

di _n "Baseline employment shares per (age_bin, ai_q) at k = -1:"
list age_bin ai_q total_count population baseline_rate, sepby(age_bin) noobs

export delimited using "$output\coefficients\baseline_kref_by_age_q.csv", replace
restore


* =============================================================================
* Section 2: Per age_bin baseline rate (aggregated over q & yrke4)
* =============================================================================

collapse (sum) total_count = count_all (first) population, by(age_bin)
gen double baseline_rate = total_count / population
sort age_bin

di _n "Baseline employment shares per age_bin at k = -1:"
list age_bin total_count population baseline_rate, noobs

export delimited using "$output\coefficients\baseline_kref_by_age.csv", replace

di _n "Script 5c complete. Baselines saved to:"
di "  baseline_kref_by_age_q.csv (per age_bin x ai_q)"
di "  baseline_kref_by_age.csv   (per age_bin, for continuous spec)"
