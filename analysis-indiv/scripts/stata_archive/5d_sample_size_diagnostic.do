* =============================================================================
* 5d_sample_size_diagnostic.do : how much of the cohort does headline_priv catch
* =============================================================================
* Counts unique persons at the reference month (October 2022) under
* increasingly restrictive sample filters, so we can see how much of the
* cohort population is excluded at each step. Output is a small CSV the
* local analyst pulls back to interpret the headline_priv baseline rates.
*
* Stages:
*   01_all_22_55         all employed in [age_min, age_max] (any sector)
*   02_sekt3_private     + sekt = 3 (private)
*   03_sekt3_frtk_min    + foretak has >= $frtk_min_active workers
*                          (in 22-55) at the reference month
*   04_headline_priv     in_headline_priv (panel-balanced foretak that
*                          survives the 2021m1-2025m7 activity window)
*   05_hp_mapped         + person has at least one spell with yrke4 in
*                          Eloundou exposure mapping (= regression sample)
*   06_hp_yrke0000       headline_priv persons with NO mapped spell,
*                          at least one spell where yrke4 == "0000"
*                          (missing/unknown occupation)
*   07_hp_other_unmapped headline_priv persons with NO mapped spell,
*                          NO 0000 spell, only unmapped non-zero yrke4
*                          (military, clergy, very small specialties)
*
* Stages 05+06+07 sum to stage 04.
*
* Inputs:  $data\ameld_filt_$ref_y_m$ref_m.dta         (per-month from script 3)
*          $data\cells_flagged.dta                      (post script 4)
*          $data\population_by_agebin_ym.dta            (post script 5b)
* Outputs: $output\diagnostics\sample_size_diagnostic.csv
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

local refy = $ref_y
local refm = $ref_m
local refym = ym(`refy', `refm')

cap confirm file "$data\ameld_filt_`refy'_m`refm'.dta"
if _rc {
    di as error "ameld_filt_`refy'_m`refm' not found; rerun 3_monthly_filtered.do."
    exit 198
}
cap confirm file "$data\population_by_agebin_ym.dta"
if _rc {
    di as error "population_by_agebin_ym.dta not found; rerun 5b_population.do."
    exit 198
}

* --- Cohort populations at reference month ---
preserve
use "$data\population_by_agebin_ym", clear
keep if ym == `refym'
keep age_bin population
tempfile pop
save `pop'
restore

* --- Foretak IDs that are in in_headline_priv (panel-balanced) ---
preserve
use "$data\cells_flagged", clear
keep if in_headline_priv == 1
keep lopenr_foretak
duplicates drop
tempfile headline_firms
save `headline_firms'
restore


tempname pf
tempfile fout
postfile `pf' str30 stage byte age_bin long n_persons using `fout', replace


* =============================================================================
* Stage 1: all employed 22-55 at reference month
* =============================================================================

use "$data\ameld_filt_`refy'_m`refm'", clear

* Deduplicate to one row per (person, age_bin). A person could have multiple
* spells (jobs in multiple foretak) — count them once.
preserve
bys lopenr_person age_bin: keep if _n == 1
gen byte one = 1
collapse (sum) n_persons = one, by(age_bin)
forval a = 1/4 {
    qui sum n_persons if age_bin == `a', meanonly
    if r(N) > 0 post `pf' ("01_all_22_55") (`a') (r(mean))
}
restore


* =============================================================================
* Stage 2: + sekt = 3 (private)
* =============================================================================

preserve
keep if sekt == 3
bys lopenr_person age_bin: keep if _n == 1
gen byte one = 1
collapse (sum) n_persons = one, by(age_bin)
forval a = 1/4 {
    qui sum n_persons if age_bin == `a', meanonly
    if r(N) > 0 post `pf' ("02_sekt3_private") (`a') (r(mean))
}
restore


* =============================================================================
* Stage 3: + foretak has >= frtk_min_active workers (in 22-55) at ref month
* =============================================================================

preserve
keep if sekt == 3
* Count UNIQUE persons per foretak (a person can have multiple "arbeidsforhold"
* spells in the same foretak in a month — multiple positions / contracts).
bys lopenr_foretak lopenr_person: gen byte _first = (_n == 1)
bys lopenr_foretak: egen long _frtk_size = total(_first)
keep if _frtk_size >= $frtk_min_active
drop _frtk_size _first
bys lopenr_person age_bin: keep if _n == 1
gen byte one = 1
collapse (sum) n_persons = one, by(age_bin)
forval a = 1/4 {
    qui sum n_persons if age_bin == `a', meanonly
    if r(N) > 0 post `pf' ("03_sekt3_frtk_min") (`a') (r(mean))
}
restore


* =============================================================================
* Stage 4: in_headline_priv (panel-balanced foretak)
* =============================================================================

preserve
keep if sekt == 3
merge m:1 lopenr_foretak using `headline_firms', keep(match) nogen
bys lopenr_person age_bin: keep if _n == 1
gen byte one = 1
collapse (sum) n_persons = one, by(age_bin)
forval a = 1/4 {
    qui sum n_persons if age_bin == `a', meanonly
    if r(N) > 0 post `pf' ("04_headline_priv") (`a') (r(mean))
}
restore


* =============================================================================
* Stages 5-7: split headline_priv by Eloundou-mapping coverage of yrke4
* =============================================================================

preserve
keep if sekt == 3
merge m:1 lopenr_foretak using `headline_firms', keep(match) nogen

* Flag each spell as mapped / 0000 / other-unmapped
cap confirm file "$data\exposure.dta"
if _rc {
    di as error "exposure.dta not found; rerun 1_exposure.do first."
    exit 198
}
merge m:1 yrke4 using "$data\exposure", keep(master match) keepusing(ai_q) nogen
gen byte _mapped  = !missing(ai_q)
gen byte _is_0000 = (yrke4 == "0000")
gen byte _other_unmapped = (!_mapped & !_is_0000)

* Per person: any-mapped is the priority classification
bys lopenr_person: egen byte any_mapped         = max(_mapped)
bys lopenr_person: egen byte any_0000           = max(_is_0000)
bys lopenr_person: egen byte any_other_unmapped = max(_other_unmapped)

* Assign disjoint category (priority: mapped > 0000 > other-unmapped)
gen byte category = .
replace category = 1 if any_mapped == 1
replace category = 2 if any_mapped == 0 & any_0000 == 1
replace category = 3 if any_mapped == 0 & any_0000 == 0 & any_other_unmapped == 1
assert !missing(category)

bys lopenr_person age_bin: keep if _n == 1

* Stage 5: mapped (= regression sample)
forval a = 1/4 {
    qui count if category == 1 & age_bin == `a'
    if r(N) > 0 post `pf' ("05_hp_mapped") (`a') (r(N))
}

* Stage 6: yrke4 = 0000 only
forval a = 1/4 {
    qui count if category == 2 & age_bin == `a'
    if r(N) > 0 post `pf' ("06_hp_yrke0000") (`a') (r(N))
}

* Stage 7: other unmapped (military, clergy, etc.)
forval a = 1/4 {
    qui count if category == 3 & age_bin == `a'
    if r(N) > 0 post `pf' ("07_hp_other_unmapped") (`a') (r(N))
}
restore

postclose `pf'


* =============================================================================
* Assemble, merge population, compute rate, export
* =============================================================================

use `fout', clear
merge m:1 age_bin using `pop', keep(master match) nogen
gen double rate = n_persons / population
sort stage age_bin

di _n "Sample-size diagnostic at ym = `refym' (October 2022):"
list stage age_bin n_persons population rate, sepby(stage) noobs

export delimited using "$output\diagnostics\sample_size_diagnostic.csv", replace

di _n "Script 5d complete. Diagnostic written to diagnostics\sample_size_diagnostic.csv."
