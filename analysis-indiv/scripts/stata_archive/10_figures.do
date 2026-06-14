* =============================================================================
* 10_figures.do : DEPRECATED — split into 10a and 10b
* =============================================================================
* The figure logic has been split into two self-contained scripts so that you
* can re-run any one figure without touching the regressions:
*
*   10a_fig_event_study.do      Six-panel Poisson event-study (uses coefs_event_study.dta)
*   10b_fig_alt_triplediff.do   Triple-diff intensive-margin plot (uses coefs_alt.dta)
*
* This file is left as a thin wrapper so any old invocation of
* `do 10_figures.do` still works.
* =============================================================================

if "${scripts}" == "" global scripts "H:\Dokumenter\ai_norway_indiv\scripts"
do "$scripts\0_settings.do"

di _n "10_figures.do is deprecated; running 10a and 10b instead."

do "$scripts\10a_fig_event_study.do"
do "$scripts\10b_fig_alt_triplediff.do"
