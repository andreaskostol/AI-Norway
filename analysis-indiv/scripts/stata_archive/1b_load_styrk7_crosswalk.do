* =============================================================================
* 1b_load_styrk7_crosswalk.do : load 7-digit STYRK -> 4-digit STYRK crosswalk
* =============================================================================
* Imports occupations_7digits_4digits.csv (semicolon-delimited) and saves it
* as a Stata file for script 3 to merge against. Replaces our previous
* substr(yrke7, 1, 4) shortcut, which is WRONG for codes where the Norwegian
* 7-digit hierarchy doesn't line up with the 4-digit STYRK-08 unit groups
* (e.g. military: 7-digit "0111101" maps to 4-digit "0310", not "0111").
*
* Inputs:  $data\occupations_7digits_4digits.csv   (transfer from local
*                                                    analysis-indiv/)
* Outputs: $data\styrk7_to_styrk4.dta              (yrke7, yrke4)
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

cap confirm file "$data\occupations_7digits_4digits.csv"
if _rc {
    di as error "occupations_7digits_4digits.csv not found in $data."
    di as error "Transfer the file from local analysis-indiv\."
    exit 198
}

import delimited "$data\occupations_7digits_4digits.csv", clear ///
    delimiter(";") varnames(1) stringcols(_all)

keep sourcecode targetcode
rename sourcecode yrke7
rename targetcode yrke4

replace yrke7 = strtrim(yrke7)
replace yrke4 = strtrim(yrke4)

* Sanity checks: every row should be a 7-digit -> 4-digit mapping.
qui count if strlen(yrke7) != 7
if r(N) > 0 {
    di as error "WARNING: `r(N)' rows have yrke7 not exactly 7 chars."
    list yrke7 yrke4 if strlen(yrke7) != 7, sep(0)
}
qui count if strlen(yrke4) != 4
if r(N) > 0 {
    di as error "WARNING: `r(N)' rows have yrke4 not exactly 4 chars."
    list yrke7 yrke4 if strlen(yrke4) != 4, sep(0)
}

duplicates drop yrke7, force
sort yrke7
compress
save "$data\styrk7_to_styrk4", replace

di _n "Crosswalk loaded: " _N " unique yrke7 -> yrke4 mappings saved to $data\styrk7_to_styrk4.dta"
