* =============================================================================
* 5_apply_restrictions.do : tag cells for the four sample variants
* =============================================================================
* Reads cells.dta, adds binary flags for each sample, saves cells_flagged.dta.
*
* Inputs:  $data\cells.dta
* Output:  $data\cells_flagged.dta
*           Adds flags: in_headline, in_ft, in_ft_priv, in_bcc_full
* Appends: §6 Restriction-step counts to $RESULTS_MD
*
* Sample definitions
* ------------------
*   in_headline    : every cell with positive employment (count_all > 0).
*                    All sectors, all FT/PT statuses.
*
*   in_ft          : in_headline AND count_ft > 0 in the cell.
*                    Restricts to FT workers; cell mean uses count_ft denominator.
*
*   in_ft_priv     : in_ft AND sekt == 3 (private).
*                    BCC's "exclude part-time, private only" combo.
*
*   in_bcc_full    : in_ft_priv AND the BCC cell-presence rules:
*                      - For each (firm, age) pair: ≥ $bcc_min_per_age FT workers
*                        EVERY month of the panel (balanced firm-by-age presence).
*                      - For each (firm, q, age) cell: Σ_t count_ft ≥ $bcc_min_total.
*                    These rules are applied at the (firm, age, q) level (not
*                    per cell, since the rule is about firm-age presence across
*                    the panel and per-(firm,q,age) total mass).
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"


* =============================================================================
* Section 1: Load cells, attach flags
* =============================================================================

use "$data\cells", clear

* in_headline : every cell in the balanced panel.
gen byte in_headline = 1

* in_headline_priv : every private-sector cell in the balanced panel.
* This is the active "main" sample for the regressions in scripts 6-8: all
* workers (FT + PT) in private foretak. Sector restriction matches BCC.
gen byte in_headline_priv = (sekt == 3)

* in_ft : cell is in the FT-relevant universe — the (foretak, age_bin, yrke4)
* cell had at least one FT-positive observation at some point. This includes
* synthetic zero-FT cells in the balanced panel so that firm × time FE see
* exits from the FT margin as zeros, not as missing data. (Currently retained
* for future robustness layering; not used in scripts 6-8 main loops.)
bys lopenr_foretak age_bin yrke4: egen byte _ever_ft = max(count_ft > 0)
gen byte in_ft = _ever_ft
drop _ever_ft

* in_ft_priv : FT-relevant cell in private sector.
gen byte in_ft_priv = (in_ft == 1 & sekt == 3)


* =============================================================================
* Section 2: BCC-full restriction
* =============================================================================
* Two conditions, both applied to the FT/private subset:
*   (a) For each (firm, age_bin), ≥ bcc_min_per_age FT workers in EVERY month
*       of the panel (count of distinct months observed = panel length).
*   (b) Σ_t count_ft over t ≥ bcc_min_total per (firm, q, age_bin) cell.
*
* Compute panel length = number of distinct months in the data.
qui levelsof ym, local(allmonths)
local panel_length : word count `allmonths'
di "Panel length (distinct months in data): `panel_length'"

* (a) Firm-age presence with ≥ bcc_min_per_age FT workers every period.
*     Aggregate count_ft to the (firm, age_bin, ym) level first (sum over yrke4
*     and quintile within firm-age-month), then check minimum across months.
preserve
keep if in_ft_priv == 1
collapse (sum) count_ft_fa = count_ft, by(lopenr_foretak age_bin ym)
* For each (firm, age) : minimum count_ft_fa across observed months
bys lopenr_foretak age_bin: egen long min_ft_fa  = min(count_ft_fa)
bys lopenr_foretak age_bin: egen long n_months_fa = count(ym)
gen byte fa_pass = (min_ft_fa >= $bcc_min_per_age & n_months_fa == `panel_length')
keep lopenr_foretak age_bin fa_pass
duplicates drop lopenr_foretak age_bin, force
tempfile fa_flag
save `fa_flag'
restore
merge m:1 lopenr_foretak age_bin using `fa_flag', keep(master match) nogen
replace fa_pass = 0 if missing(fa_pass)

* (b) Per (firm, q, age) cell: Σ_t count_ft ≥ bcc_min_total
preserve
keep if in_ft_priv == 1
collapse (sum) sum_ft = count_ft, by(lopenr_foretak age_bin ai_q)
gen byte fqa_pass = (sum_ft >= $bcc_min_total)
keep lopenr_foretak age_bin ai_q fqa_pass
tempfile fqa_flag
save `fqa_flag'
restore
merge m:1 lopenr_foretak age_bin ai_q using `fqa_flag', keep(master match) nogen
replace fqa_pass = 0 if missing(fqa_pass)

* Final BCC-full flag : passes both rules and is in the FT-private sample.
gen byte in_bcc_full = (in_ft_priv == 1 & fa_pass == 1 & fqa_pass == 1)

drop fa_pass fqa_pass


* =============================================================================
* Section 3: Save and report
* =============================================================================

compress
save "$data\cells_flagged", replace

* Sample-size counts: at cell level, at firm level, at firm-age-q level.
qui count if in_headline == 1
local n_cells_h = r(N)
qui count if in_headline_priv == 1
local n_cells_hp = r(N)
qui count if in_ft == 1
local n_cells_ft = r(N)
qui count if in_ft_priv == 1
local n_cells_ftp = r(N)
qui count if in_bcc_full == 1
local n_cells_bcc = r(N)

* Distinct-foretak count via egen tag (avoids stuffing IDs into a local).
foreach s in headline headline_priv ft ft_priv bcc_full {
    preserve
    keep if in_`s' == 1
    egen byte v_tag = tag(lopenr_foretak)
    qui count if v_tag == 1
    local n_v_`s' = r(N)
    restore
}
local n_v_h   = `n_v_headline'
local n_v_hp  = `n_v_headline_priv'
local n_v_ft  = `n_v_ft'
local n_v_ftp = `n_v_ft_priv'
local n_v_bcc = `n_v_bcc_full'

* Total worker-months per sample.
preserve
keep if in_headline == 1
qui sum count_all
local n_wm_h = r(sum)
restore

preserve
keep if in_headline_priv == 1
qui sum count_all
local n_wm_hp = r(sum)
restore

preserve
keep if in_ft == 1
qui sum count_ft
local n_wm_ft = r(sum)
restore

preserve
keep if in_ft_priv == 1
qui sum count_ft
local n_wm_ftp = r(sum)
restore

preserve
keep if in_bcc_full == 1
qui sum count_ft
local n_wm_bcc = r(sum)
restore


* =============================================================================
* Section 4: Append §6 to $RESULTS_MD
* =============================================================================

local fmt_h     : di %14.0fc `n_cells_h'
local fmt_hp    : di %14.0fc `n_cells_hp'
local fmt_ft    : di %14.0fc `n_cells_ft'
local fmt_ftp   : di %14.0fc `n_cells_ftp'
local fmt_bcc   : di %14.0fc `n_cells_bcc'

local fmt_v_h   : di %14.0fc `n_v_h'
local fmt_v_hp  : di %14.0fc `n_v_hp'
local fmt_v_ft  : di %14.0fc `n_v_ft'
local fmt_v_ftp : di %14.0fc `n_v_ftp'
local fmt_v_bcc : di %14.0fc `n_v_bcc'

local fmt_wm_h   : di %14.0fc `n_wm_h'
local fmt_wm_hp  : di %14.0fc `n_wm_hp'
local fmt_wm_ft  : di %14.0fc `n_wm_ft'
local fmt_wm_ftp : di %14.0fc `n_wm_ftp'
local fmt_wm_bcc : di %14.0fc `n_wm_bcc'

foreach m in fmt_h fmt_hp fmt_ft fmt_ftp fmt_bcc ///
             fmt_v_h fmt_v_hp fmt_v_ft fmt_v_ftp fmt_v_bcc ///
             fmt_wm_h fmt_wm_hp fmt_wm_ft fmt_wm_ftp fmt_wm_bcc {
    local `m' = strtrim("``m''")
}

file open mdfh using "$mdfrag\section_06.md", write replace text

file write mdfh "## §6: Restriction-step counts" _n
file write mdfh "" _n
file write mdfh "Sample variants. The current main run uses headline_priv " ///
    "(all FT/PT in private foretak). Other variants are still tagged in " ///
    "cells_flagged.dta and can be re-enabled in scripts 6-8 for robustness." _n
file write mdfh "" _n
file write mdfh "| Sample | Cells | Distinct foretak | Worker-months |" _n
file write mdfh "|---|---:|---:|---:|" _n
file write mdfh "| Headline (all sectors, FT+PT) | `fmt_h' | `fmt_v_h' | `fmt_wm_h' |" _n
file write mdfh "| **Headline x private (main run)** | **`fmt_hp'** | **`fmt_v_hp'** | **`fmt_wm_hp'** |" _n
file write mdfh "| FT only | `fmt_ft' | `fmt_v_ft' | `fmt_wm_ft' |" _n
file write mdfh "| FT + private only | `fmt_ftp' | `fmt_v_ftp' | `fmt_wm_ftp' |" _n
file write mdfh "| BCC full (FT + priv + ≥$bcc_min_per_age every period + Σ ≥ $bcc_min_total) " ///
    "| `fmt_bcc' | `fmt_v_bcc' | `fmt_wm_bcc' |" _n
file write mdfh "" _n
file write mdfh "Worker-months counts use count_all for headline samples and count_ft for " ///
    "the FT-based samples." _n
file write mdfh "" _n
file write mdfh "---" _n
file write mdfh "" _n

file close mdfh

do "$scripts\_rebuild_results_md.do"

di _n "Script 5 complete. Sample flags attached; section_06 fragment + $RESULTS_MD rebuilt."
