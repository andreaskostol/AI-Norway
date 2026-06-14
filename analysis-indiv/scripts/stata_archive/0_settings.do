* =============================================================================
* 0_settings.do : paths, globals, constants for the AI-Norway firm-FE pipeline
* =============================================================================
* Sourced at the top of every script. The paths mirror the existing
* aldersgrense_stillingsvern project, with the project name substituted to
* `ai_norway_indiv`. Edit if your server layout differs.
*
* Rationale for the constants below (age window, BCC thresholds, reference
* month, foretak activity threshold) is documented in DESIGN_CHOICES.md.
* =============================================================================

* === Paths ===
global prosjektdata "W:\7020\"
global project      "H:\Dokumenter\ai_norway_indiv\"
global data         "F:\1183\oysteimh\ai_norway_indiv\data\"
global scripts      "$project\scripts"

* === Demographic "faste opplysninger" file ===
global faste_oppl "${prosjektdata}demo\faste_oppl_full"

* === Output directory mirrors the local from_secure_server/ tree ===
* When the run is finished, copy $output\ as-is into the local from_secure_server/ folder.
global output     "$project\from_secure_server\"
global RESULTS_MD "$output\SECURE_SERVER_RESULTS.md"
global mdfrag     "$output\_md_fragments"

* Make sure project + output subdirectories exist (idempotent). Stata's mkdir
* only creates one level at a time; create the parent first to be safe.
cap mkdir "$project"
cap mkdir "$output"
cap mkdir "$output\figures"
cap mkdir "$output\coefficients"
cap mkdir "$output\diagnostics"
cap mkdir "$mdfrag"
cap mkdir "$data"

* === Period covered (data on secure zone currently runs through 2025m7) ===
global period_start_y = 2021
global period_start_m = 1
global period_end_y   = 2025
global period_end_m   = 7

* === Reference month (event time k = -1) ===
* October 2022 = ym(2022, 10). Post starts at ym($event_zero_y, $event_zero_m) = Nov 2022.
global ref_y         = 2022
global ref_m         = 10
global event_zero_y  = 2022
global event_zero_m  = 11

* === Age window ===
* Decade age groups (21-30, 31-40, 41-50, 51-60) for the AI-Norway paper.
* See DESIGN_CHOICES.md section 12.
global age_min = 21
global age_max = 60

* === Triple-diff binary age cut: Young in [age_min, young_max] ===
* Young = early-career decade group (21-30) = age_bin 1.
global young_max = 30

* === Foretak existence threshold (used for panel balancing in script 4) ===
* In months where a foretak has fewer than this many workers in our age window
* (22-55), the foretak is treated as not operating. Both original and synthetic
* rows in those (foretak, ym) periods are dropped. Reduces panel size and
* avoids inventing zero-employment in months the foretak did not exist.
global frtk_min_active = 20

* === BCC sample restriction thresholds ===
global bcc_min_per_age = 10    // ≥ 10 workers per age group every month
global bcc_min_total   = 100   // Σ_t y_{f,q,a,t} ≥ 100 per (firm, q, age) cell

* === Display / graph defaults (match existing aldersgrense_stillingsvern) ===
graph set window fontface "Times New Roman"
set more off

* === Memory ceiling: needed for wide event-study regressions on the full
* cells panel (~24M obs x ~210 design columns). Raise to whatever the secure
* server allows; reghdfe will use less but allocates a large temp matrix.
* `cap` because the upper limit on set max_memory is licensed-edition-dependent.
cap set max_memory 128g
