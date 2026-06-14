* =============================================================================
* 2_relevant_ids.do : people aged 22-55 in any month of the panel period
* =============================================================================
* Inputs:  $faste_oppl  (lopenr_person, foedselsaar, foedsels_aar_mnd; resolved in 0_settings.do)
* Outputs: $data\relevant_ids_2255.dta    (one row per person, with fm)
* Appends: §3 Sample IDs to $RESULTS_MD
*
* A person aged a in calendar year y if foedselsaar = y - a. So someone aged
* 22-55 in any month of $period_start_y..$period_end_y is born between
*   $period_start_y - $age_max  (would be 55 in $period_start_y) and
*   $period_end_y - $age_min    (would be 22 in $period_end_y).
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"


* =============================================================================
* Section 1: Load the demographic file and filter cohorts
* =============================================================================

* $faste_oppl is resolved in 0_settings.do (name varies: faste_opp_full /
* faste_oppl). If a variable below is missing, the new vintage renamed it;
* run `describe using "$faste_oppl"` on the server and report the names.
use lopenr_person foedselsaar foedsels_aar_mnd doeds_aar_mnd kjoenn ///
    using "$faste_oppl", clear

confirm variable lopenr_person
confirm variable foedselsaar
confirm variable foedsels_aar_mnd

destring foedselsaar foedsels_aar_mnd doeds_aar_mnd, replace

* Cohort range: born between (period_start_y - age_max) and (period_end_y - age_min)
local cohort_min = $period_start_y - $age_max
local cohort_max = $period_end_y   - $age_min
keep if inrange(foedselsaar, `cohort_min', `cohort_max')

* Keep only one row per person (faste_oppl can have duplicates)
sort lopenr_person foedsels_aar_mnd
by lopenr_person: keep if _n == 1

* Female indicator (kjoenn is "1"/"2" string)
gen byte kvinne = (kjoenn == "2")
drop kjoenn

* Birth month index for fast age-in-months calculation downstream:
*   fm = ym(foedselsaar, foedsels_aar_mnd - foedselsaar*100)
* age in months at calendar month ym:  am = ym - fm
gen birth_mo = foedsels_aar_mnd - foedselsaar * 100
* Drop persons with invalid birth-month codes (rare data errors / imputed dates)
* rather than asserting and crashing.
qui count if !inrange(birth_mo, 1, 12)
if r(N) > 0 {
    di as error "  Dropping `r(N)' persons with invalid birth_mo (out of [1,12])."
    drop if !inrange(birth_mo, 1, 12)
}
gen fm = ym(foedselsaar, birth_mo)
format %tm fm

keep lopenr_person foedselsaar birth_mo kvinne fm doeds_aar_mnd
compress
save "$data\relevant_ids_2255", replace

local n_rel = _N
di "Relevant IDs: `n_rel' persons (born `cohort_min' - `cohort_max')"


* =============================================================================
* Section 2: Cohort-size distribution for the markdown
* =============================================================================

preserve
contract foedselsaar
sort foedselsaar
tempfile cohort_counts
save `cohort_counts'
restore


* =============================================================================
* Section 3: Append §3 to $RESULTS_MD
* =============================================================================

file open mdfh using "$mdfrag\section_03.md", write replace text

file write mdfh "## §3: Sample IDs" _n
file write mdfh "" _n
file write mdfh ///
    "Persons with a chance of being aged ${age_min}--${age_max} in some month of the panel " ///
    "(born `cohort_min' -- `cohort_max'). Built once from " ///
    "${faste_oppl}; all monthly loads merge against this file." _n
file write mdfh "" _n
file write mdfh "| Birth year | N |" _n
file write mdfh "|---:|---:|" _n
preserve
use `cohort_counts', clear
forval i = 1/`=_N' {
    local yr = foedselsaar[`i']
    local n  = _freq[`i']
    local n_fmt : di %12.0fc `n'
    local n_fmt = strtrim("`n_fmt'")
    file write mdfh "| `yr' | `n_fmt' |" _n
}
restore
local n_rel_fmt : di %12.0fc `n_rel'
local n_rel_fmt = strtrim("`n_rel_fmt'")
file write mdfh "| **Total** | **`n_rel_fmt'** |" _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n

file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 2 complete. Wrote section_03 fragment; rebuilt $RESULTS_MD."
