* =============================================================================
* 3_monthly_filtered.do : month-by-month filter of A-ordningen to ages 22-55
* =============================================================================
* For each month $period_start_y m$period_start_m through $period_end_y m$period_end_m,
* load minimal columns from the raw ameld file, filter to relevant persons +
* age 22-55 + positive earnings + valid 4-digit STYRK-08, save a small monthly
* file. Aggregation to cells happens in 4_aggregate_cells.do.
*
* Inputs:  $prosjektdata\atid\ameld_statdata_YYYY_mMM
*          $data\relevant_ids_2255.dta
* Outputs: $data\ameld_filt_YYYY_mMM.dta  (one per month)
*          $output\ameld_varlist.txt      (variable list of one ameld file)
* Appends: §4 Monthly filter to $RESULTS_MD
*
* Design rationale: see DESIGN_CHOICES.md sections 5 (foretak vs virksomhet),
* 12 (age binning), 17 (wage rate cleaning), 18 (drop lonn_kontant <= 0).
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"


* =============================================================================
* Section 1: Dump variable list of one ameld file (for the markdown reference)
* =============================================================================
* Loads only the first row to inspect names without paying the I/O cost of the
* full file. The list goes into $output\ameld_varlist.txt and is referenced
* from §4 of the markdown.

local probe_y = $period_start_y
local probe_m = $period_start_m
local probefile "$prosjektdata\atid\ameld_statdata_`probe_y'_m`probe_m'"

preserve
cap qui use in 1 using "`probefile'", clear
if _rc {
    di as error "  could not load probe file `probefile' (rc=`_rc'); skipping varlist dump"
    local probe_vlist ""
}
else {
    qui ds
    local probe_vlist `r(varlist)'
}
restore

file open vfh using "$output\ameld_varlist.txt", write replace text
file write vfh "Variable list of " "`probefile'" _n _n
if "`probe_vlist'" == "" {
    file write vfh "  (probe file not readable; see run log)" _n
}
else {
    foreach v of local probe_vlist {
        file write vfh "  `v'" _n
    }
}
file close vfh

di "Variable list saved to $output\ameld_varlist.txt"


* =============================================================================
* Section 2: Per-month build loop
* =============================================================================
* Each month is independent. Pattern matches existing 2_outcomes.do : load
* minimum columns, merge against relevant_ids_2255 to drop ~half the rows
* immediately, then clean and save.
*
* `postfile` collects per-month diagnostics into one file for the markdown.

tempname mc
tempfile monthly_counts
postfile `mc' int year int month long n_raw long n_after_id long n_after_age long n_kept ///
    using `monthly_counts', replace

forval y = $period_start_y / $period_end_y {
forval m = 1 / 12 {

    if (`y' == $period_start_y & `m' < $period_start_m) continue
    if (`y' == $period_end_y   & `m' > $period_end_m  ) continue

    local rawfile "$prosjektdata\atid\ameld_statdata_`y'_m`m'"
    local outfile "$data\ameld_filt_`y'_m`m'"

    di _n "=== Processing `y' m`m' ==="

    * --- Load minimum columns; skip month if file/variable missing ---
    cap confirm file "`rawfile'.dta"
    if _rc cap confirm file "`rawfile'"
    if _rc {
        di as error "  ameld file `rawfile' not found; skipping `y' m`m'"
        post `mc' (`y') (`m') (0) (0) (0) (0)
        continue
    }
    cap noisily use lopenr_person lopenr_foretak arb_yrke frtk_sektor_2014 ///
        lonn_kontant arb_stillingspst arb_arbeidstid lonn_overtid_timer ///
        lonn_fast lonn_time lonn_time_antall arb_start ///
        using "`rawfile'", clear
    if _rc {
        di as error "  failed to load `rawfile' (rc=`_rc'); skipping `y' m`m'"
        post `mc' (`y') (`m') (0) (0) (0) (0)
        continue
    }

    qui count
    local n_raw = r(N)

    * --- Restrict to relevant persons (drops most rows immediately) ---
    merge m:1 lopenr_person using "$data\relevant_ids_2255", ///
        keep(match) keepusing(fm kvinne foedselsaar) nogen

    qui count
    local n_after_id = r(N)

    * --- Compute exact age in years and filter to [age_min, age_max] ---
    gen ym = ym(`y', `m')
    format %tm ym
    gen am = ym - fm
    gen a_year = floor(am / 12)
    keep if inrange(a_year, $age_min, $age_max)

    qui count
    local n_after_age = r(N)

    * --- Drop spells with missing/non-positive cash earnings ---
    drop if missing(lonn_kontant) | lonn_kontant <= 0

    * --- Clean position and contracted hours: cap or set to missing, keep spell ---
    replace arb_stillingspst = 200 if !missing(arb_stillingspst) & arb_stillingspst > 200
    replace arb_stillingspst = .   if !missing(arb_stillingspst) & arb_stillingspst <= 0
    replace arb_arbeidstid   = .   if !missing(arb_arbeidstid)   & arb_arbeidstid   <= 0

    * --- Clean wage and hour components ---
    * Hour counts: missing or negative -> 0 (no hours of this type that month).
    replace lonn_time_antall   = 0 if missing(lonn_time_antall)   | lonn_time_antall   < 0
    replace lonn_overtid_timer = 0 if missing(lonn_overtid_timer) | lonn_overtid_timer < 0
    * Cap implausibly large hour counts (data errors): set the count to missing.
    replace lonn_time_antall   = . if lonn_time_antall   > 300
    replace lonn_overtid_timer = 80 if lonn_overtid_timer > 80
    * Wage rates: keep missing as missing (no hourly arrangement); negative -> missing.
    * No one has a true zero hourly rate, so zero-imputation is wrong.
    replace lonn_time = . if !missing(lonn_time) & lonn_time < 0
    * Fixed pay component: missing or negative -> 0 (no fixed pay reported).
    replace lonn_fast = 0 if missing(lonn_fast) | lonn_fast < 0

    * --- Map 7-digit STYRK to 4-digit STYRK-08 via crosswalk ---
    * substr(yrke7, 1, 4) is WRONG for codes where the Norwegian 7-digit
    * hierarchy does not line up with the 4-digit STYRK-08 unit groups
    * (e.g. military: "0111101" -> "0310", not "0111"). The crosswalk file
    * is comprehensive and contains no 0000 / invalid 4-digit codes.
    cap confirm string variable arb_yrke
    if _rc {
        * arb_yrke is numeric — convert to zero-padded 7-character string so
        * codes like "0111101" (military) keep their leading zero before merge.
        tostring arb_yrke, replace force format(%07.0f)
    }
    replace arb_yrke = strtrim(arb_yrke)
    rename arb_yrke yrke7
    * Left-pad with zeros if shorter than 7 chars (defensive — guards against
    * any upstream step that lost leading zeros).
    replace yrke7 = substr("0000000" + yrke7, -7, 7) if !missing(yrke7) & yrke7 != ""
    cap confirm file "$data\styrk7_to_styrk4.dta"
    if _rc {
        di as error "styrk7_to_styrk4.dta not found; run 1b_load_styrk7_crosswalk.do first."
        exit 198
    }
    merge m:1 yrke7 using "$data\styrk7_to_styrk4", keep(master match) keepusing(yrke4)
    qui count if _merge == 1
    local n_unmapped = r(N)
    drop if _merge == 1
    drop _merge
    di "  yrke7 -> yrke4 crosswalk: dropped `n_unmapped' spells with unmapped yrke7"
    drop if missing(yrke4) | yrke4 == "" | strlen(yrke4) < 4

    * --- Drop spells with missing foretak ID ---
    drop if missing(lopenr_foretak)

    * --- Sector classification (1/2/3 = stat / kommune / private) ---
    gen byte sekt = 3
    replace sekt = 1 if inlist(frtk_sektor_2014, "1110", "1120", "6100")
    replace sekt = 2 if inlist(frtk_sektor_2014, "1510", "1520", "6500")

    * --- Full-time flag (≥ 100% position) ---
    gen byte ft = (arb_stillingspst >= 100 & !missing(arb_stillingspst))

    * --- Base hours = contracted weekly * 4.33 if available, else lonn_time_antall ---
    gen double basehours = cond(!missing(arb_arbeidstid), arb_arbeidstid * 4.33, lonn_time_antall)
    gen double basepay   = lonn_fast + lonn_time

    * --- Decade age bins (AI-Norway paper; see DESIGN_CHOICES.md section 12) ---
    *   1: 21-30 (early career)
    *   2: 31-40
    *   3: 41-50
    *   4: 51-60 (senior)
    gen byte age_bin = .
    replace age_bin = 1 if inrange(a_year, 21, 30)
    replace age_bin = 2 if inrange(a_year, 31, 40)
    replace age_bin = 3 if inrange(a_year, 41, 50)
    replace age_bin = 4 if inrange(a_year, 51, 60)
    assert !missing(age_bin)

    * --- Triple-diff binary age cut ---
    gen byte young = inrange(a_year, $age_min, $young_max)

    * --- New hire: employment relationship started this calendar month ---
    * arb_start is a daily date ("Startdato for arbeidsforholdet"); a new hire
    * is a spell whose start month equals the status month. Matches the
    * cell-level ny_jobb definition (microdata.no ARBLONN_ARB_START).
    gen byte ny_jobb = (mofd(arb_start) == ym) if !missing(arb_start)
    replace ny_jobb = 0 if missing(ny_jobb)

    * --- Keep only what 4_aggregate_cells.do needs ---
    keep lopenr_person lopenr_foretak ym yrke4 sekt ft young age_bin a_year ///
         lonn_kontant arb_stillingspst basehours basepay lonn_overtid_timer ///
         ny_jobb kvinne

    qui count
    local n_kept = r(N)

    compress
    save "`outfile'", replace

    di "  raw=`n_raw'  after-id-filter=`n_after_id'  after-age=`n_after_age'  kept=`n_kept'"
    post `mc' (`y') (`m') (`n_raw') (`n_after_id') (`n_after_age') (`n_kept')
}
}
postclose `mc'


* =============================================================================
* Section 3: Append §4 to $RESULTS_MD
* =============================================================================

use `monthly_counts', clear
sort year month

file open mdfh using "$mdfrag\section_04.md", write replace text

file write mdfh "## §4: Monthly filter" _n
file write mdfh "" _n
file write mdfh "Per-month row counts after filtering A-ordningen to ages " ///
    "$age_min--$age_max with positive lonn_kontant, valid 4-digit STYRK-08, and " ///
    "non-missing lopenr_foretak. Full ameld variable list in " ///
    "output/ameld_varlist.txt." _n
file write mdfh "" _n
file write mdfh "| Month | Raw rows | After ID filter | After age filter | Kept |" _n
file write mdfh "|---|---:|---:|---:|---:|" _n

forval i = 1/`=_N' {
    local y_i  = year[`i']
    local m_i  = month[`i']
    local r_v  = n_raw[`i']
    local i_v  = n_after_id[`i']
    local a_v  = n_after_age[`i']
    local k_v  = n_kept[`i']
    local r_f : di %14.0fc `r_v'
    local i_f : di %14.0fc `i_v'
    local a_f : di %14.0fc `a_v'
    local k_f : di %14.0fc `k_v'
    local r_f = strtrim("`r_f'")
    local i_f = strtrim("`i_f'")
    local a_f = strtrim("`a_f'")
    local k_f = strtrim("`k_f'")
    file write mdfh "| `y_i'm`m_i' | `r_f' | `i_f' | `a_f' | `k_f' |" _n
}

file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n

file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 3 complete. Per-month files saved; section_04 fragment + $RESULTS_MD rebuilt."
