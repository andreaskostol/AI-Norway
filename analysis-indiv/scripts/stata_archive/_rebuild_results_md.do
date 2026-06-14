* =============================================================================
* _rebuild_results_md.do : reassemble $RESULTS_MD from per-section fragments
* =============================================================================
* Each script that writes a section first writes its fragment to
*   $mdfrag\section_NN.md   (with `replace`, idempotent)
* and then `do`-calls this helper, which concatenates all currently-existing
* fragments in numerical order into $RESULTS_MD (with `replace`).
*
* Effect: re-running any single script updates only its fragment, then the
* master .md is rebuilt cleanly. No duplicated sections from partial reruns.
* Fragments from scripts that haven't been re-run keep their previous content
* (so a partial rerun produces a coherent document with mixed-vintage sections;
* the §1 "Run metadata" timestamp tells the reader which run produced what).
*
* Fragment naming convention:
*   section_00.md  header (title + open issues), written by script 1
*   section_01.md  §1 Run metadata,              written by script 1
*   section_02.md  §2 Exposure,                  written by script 1
*   section_03.md  §3 Sample IDs,                written by script 2
*   section_04.md  §4 Monthly filter,            written by script 3
*   section_05.md  §5 Cell-level dataset,        written by script 4
*   section_06.md  §6 Restriction-step counts,   written by script 5
*   section_07.md  §7 Event-study (Poisson),       written by script 6
*   section_07c.md §7c Event-study (share OLS),    written by script 6c
*   section_07d.md §7d Event-study (cont. x young),written by script 6d
*   section_08.md  §8 Triple-diff (Poisson),       written by script 7
*   section_09.md  §9 Alt outcomes (linear OLS),   written by script 8
*   section_09b.md §9b Count level (reghdfe),      written by script 8b
*   section_09c.md §9c Triple-diff share (reghdfe),written by script 8c
*   section_10.md  §10 Pre-trend / placebo,        written by script 9
*
* Figure fragments (11, 12, 13) are intentionally dropped from the rebuild:
* publication figures live locally in analysis-indiv/code/plot_secure_server_results.py.
* The corresponding Stata figure scripts (10a/10b/10c) are commented out in
* 99_master.do.
* =============================================================================

quietly {

    file open _master_md_h using "$RESULTS_MD", write replace text

    foreach frag in 00 01 02 03 04 05 06 07 07c 07d 08 09 09b 09c 10 {

        local fpath "$mdfrag\section_`frag'.md"

        cap confirm file "`fpath'"
        if !_rc {
            file open _frag_h using "`fpath'", read text
            file read _frag_h line
            while r(eof) == 0 {
                file write _master_md_h `"`macval(line)'"' _n
                file read _frag_h line
            }
            file close _frag_h
        }
    }

    file close _master_md_h
}
