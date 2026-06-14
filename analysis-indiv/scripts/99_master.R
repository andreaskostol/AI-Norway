# =============================================================================
# 99_master.R : run the FULL pipeline (data prep + estimation) in order
# =============================================================================
# The whole pipeline is R (the Stata prep scripts are archived in
# scripts/stata_archive/). After a full run, $OUTPUT (from_secure_server\) is
# the single folder to transfer off-server.
#
# THREE WAYS TO RUN
#
#   A) Interactively (RStudio/R GUI on the server) -- the everyday mode:
#      open this file, run the SETUP block once (everything down to the
#      "KJØRELISTE" header), then mark and run the individual run_script()
#      lines you want, in any subset. Running the whole file = full pipeline.
#
#   B) Batch from a console:
#        cd H:\Dokumenter\ai_norway_indiv\scripts
#        Rscript 99_master.R                 # everything
#        Rscript 99_master.R prep            # group: data prep (1-5d)
#        Rscript 99_master.R est             # group: estimation (6-8, excl. 6e/7c)
#        Rscript 99_master.R heavy           # group: 6e + 7c (compute-heavy)
#        Rscript 99_master.R 7b 7d           # substring selectors
#        Rscript 99_master.R 6e fe=occ       # key=value args pass through
#      (Selectors make the non-matching run_script() lines no-ops.)
#
#   C) One script directly, bypassing the master entirely:
#        Rscript 7b_did_byage_fepois.R
#      Every script is self-contained given its inputs on $DATA. NB: direct
#      runs skip the master's manifest update and stale-output invalidation.
#
# HEAVY SCRIPTS (3, 4, 6, 7, 6e, 7c on real data): prefer Rscript in a
# separate Command Prompt (survives a remote-desktop disconnect) or an
# RStudio Background Job over the interactive console. 0_settings.R caps
# data.table/fixest at all-cores-minus-two (AI_NORWAY_THREADS overrides) so
# the session front-end stays responsive while they run. After a disconnect,
# check diagnostics/run_manifest.csv + the script's log before rerunning.
#
# Whichever way a script is run through run_script(), the master (1) deletes
# the script's declared outputs first (no stale CSVs can survive a failure),
# (2) records status in diagnostics/run_manifest.csv (rows for scripts not
# run are preserved), and (3) after a PREP failure refuses to run anything
# further (downstream would only cascade-fail).
#
# Logs: log_master_R.txt (batch mode only) + one log_<script>.txt per
# sub-script. No estimation output is valid without status ok in the manifest.
# =============================================================================

# =============================================================================
# SETUP -- run this whole block once before marking individual lines below
# =============================================================================

BATCH <- !interactive()

# Set working directory to the scripts folder so source("...") resolves no
# matter where Rscript was invoked from. Under AI_NORWAY_TEST_ROOT (local
# synthetic smoke test) the current wd is assumed to BE the scripts folder.
if (!nzchar(Sys.getenv("AI_NORWAY_TEST_ROOT", unset = ""))) {
    SCRIPTS_DIR <- "H:/Dokumenter/ai_norway_indiv/scripts"
    if (dir.exists(SCRIPTS_DIR)) {
        setwd(SCRIPTS_DIR)
    } else {
        warning(sprintf("SCRIPTS_DIR '%s' does not exist -- using current wd '%s'.",
                        SCRIPTS_DIR, getwd()))
    }
}

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else {
    stop(sprintf("Cannot locate 0_settings.R in %s.", getwd()))
}

check_packages()          # stops listing ALL missing of haven/data.table/fixest
run_settings_selftests()  # fixture tests of the settings API; writes
                          # diagnostics/settings_selftest.txt

# -----------------------------------------------------------------------------
# Script groups (selector aliases + the prep-abort rule)
# -----------------------------------------------------------------------------
GROUPS <- list(
    # Data prep (heavy I/O; re-run only when raw data or thresholds change).
    prep = c(
        "1_exposure.R",                 # Eloundou mapping -> exposure.rds
        "1b_load_styrk7_crosswalk.R",   # yrke7 -> yrke4 crosswalk
        "2_relevant_ids.R",             # cohort filter on faste_oppl
        "3_monthly_filtered.R",         # per-month A-ordningen filter
        "4_aggregate_cells.R",          # cells + balancing + bridge aggregate
        "5_apply_restrictions.R",       # sample flags -> cells_flagged.rds
        "5b_population.R",              # SSB population denominators
        "5c_baseline_kref.R",           # baseline rates at k = -1
        "5d_sample_size_diagnostic.R"   # cohort-coverage funnel
    ),
    # Estimation (each independent given cells_flagged.rds).
    est = c(
        "6_event_study_fepois.R",       # Poisson event-study per age bin
        "6c_event_study_share_feols.R", # OLS per-capita rate event-study
        "6d_event_study_continuous_share_feols.R",  # continuous x young ES
        "6f_event_study_cellspec.R",    # cell-spec ES (ES counterpart of 7d)
        "7_triplediff_fepois.R",        # young x post x exposure triple
        "7b_did_byage_fepois.R",        # firm-FE DiD per age (BCC spec)
        "7d_did_byage_cellspec.R",      # cell-spec DiD per age (comparison)
        "8_alt_outcomes_feols.R"        # alt outcomes triple-diffs
    ),
    # Comparative-advantage firm-FE replication. COMPUTE-HEAVY (full firm x
    # month panel); run standalone with outcome/timing/fe args to parallelise.
    heavy = c(
        "6e_ca_es_firmfe.R",            # CA event study (chapter 1)
        "7c_ca_did_firmfe.R"            # CA pooled DiD (chapter 2)
    ),
    # BCC-replication appendix: FT-private, BCC's 6 age bins, re-aggregated from
    # the cached ameld_filt (no script-3 re-run). A1 descriptive (Figs 1/2/3/5),
    # A2 BCC-binned balanced panel, A3 Poisson event study (Fig 4).
    bcc = c(
        "A1_bcc_descriptive_agg.R",     # Figs 1,2,3,5 inputs
        "A2_bcc_panel.R",               # BCC-binned FT-private balanced panel
        "A3_bcc_event_study.R"          # Fig 4 Poisson firm-FE event study
    )
)
all_scripts <- unlist(GROUPS, use.names = FALSE)

# Declared outputs per script (relative to $OUTPUT). These are DELETED before
# the script runs, so a failed script can never leave a stale CSV from an
# earlier run masquerading as a fresh result. Prep intermediates on $DATA are
# not invalidated: a prep failure halts everything downstream anyway.
OUTPUTS <- list(
    "5c_baseline_kref.R" = c("coefficients/baseline_kref_by_age_q.csv",
                             "coefficients/baseline_kref_by_age.csv"),
    "5d_sample_size_diagnostic.R" = "diagnostics/sample_size_diagnostic.csv",
    "6_event_study_fepois.R" = c("coefficients/coef_event_study_fepois.csv",
                                 "coefficients/coef_event_study_fepois_summary.csv",
                                 "diagnostics/fixest_diag_6_event_study_fepois.csv"),
    "6c_event_study_share_feols.R" = c("coefficients/coef_event_study_share.csv",
                                       "coefficients/coef_event_study_share_summary.csv",
                                       "diagnostics/fixest_diag_6c_event_study_share_feols.csv"),
    "6d_event_study_continuous_share_feols.R" =
        c("coefficients/coef_event_study_continuous_share.csv",
          "coefficients/coef_event_study_continuous_share_summary.csv",
          "diagnostics/fixest_diag_6d_event_study_continuous_share.csv"),
    "6f_event_study_cellspec.R" = c("coefficients/coef_es_byage_cellspec.csv",
                                    "coefficients/coef_es_byage_cellspec_summary.csv",
                                    "diagnostics/fixest_diag_6f_event_study_cellspec.csv"),
    "7_triplediff_fepois.R" = c("coefficients/coef_triplediff_fepois.csv",
                                "diagnostics/fixest_diag_7_triplediff_fepois.csv"),
    "7b_did_byage_fepois.R" = c("coefficients/coef_did_byage_fepois.csv",
                                "diagnostics/sample_diag_7b.csv",
                                "diagnostics/fixest_diag_7b_did_byage_fepois.csv"),
    "7d_did_byage_cellspec.R" = c("coefficients/coef_did_byage_cellspec.csv",
                                  "diagnostics/sample_diag_7d_restricted.csv",
                                  "diagnostics/7b_7d_sample_comparison.csv",
                                  "diagnostics/fixest_diag_7d_did_byage_cellspec.csv"),
    "8_alt_outcomes_feols.R" = c("coefficients/coef_alt.csv",
                                 "coefficients/coef_count_level.csv",
                                 "coefficients/coef_share.csv",
                                 "diagnostics/fixest_diag_8_alt_outcomes_feols.csv"),
    "6e_ca_es_firmfe.R" = c("coefficients/coef_ca_es_firmfe.csv",
                            "diagnostics/fixest_diag_6e_ca_es_firmfe.csv"),
    "7c_ca_did_firmfe.R" = c("coefficients/coef_ca_did_firmfe.csv",
                             "coefficients/coef_ca_did_firmfe_modelstats.csv",
                             "diagnostics/fixest_diag_7c_ca_did_firmfe.csv"),
    "A1_bcc_descriptive_agg.R" = c("coefficients/bcc_desc_employment.csv",
                                   "coefficients/bcc_desc_wage.csv",
                                   "coefficients/bcc_desc_occ.csv"),
    # A2 writes cells_bcc.rds to $DATA (not $OUTPUT) -> nothing to invalidate here.
    "A3_bcc_event_study.R" = c("coefficients/coef_bcc_event_study.csv",
                               "coefficients/coef_bcc_event_study_summary.csv",
                               "diagnostics/fixest_diag_A3_bcc_event_study.csv")
)

invalidate_outputs <- function(s) {
    outs <- OUTPUTS[[s]]
    if (is.null(outs)) return(invisible(NULL))
    paths <- file.path(OUTPUT, outs)
    removed <- paths[file.exists(paths)]
    if (length(removed) > 0) {
        file.remove(removed)
        cat(sprintf("    invalidated %d stale output file(s) of %s\n",
                    length(removed), s))
    }
    invisible(NULL)
}

# -----------------------------------------------------------------------------
# Batch selectors. Plain command-line args select: group aliases
# (prep/est/heavy) first, then substring match. key=value args are NOT
# selectors -- they fall through to the sub-scripts. No plain args (or
# interactive use) -> everything is selected; you choose by marking lines.
# -----------------------------------------------------------------------------
SELECTED <- NULL   # NULL = all
if (BATCH) {
    sel <- commandArgs(trailingOnly = TRUE)
    sel <- sel[!grepl("=", sel)]
    if (length(sel) > 0) {
        matched <- unique(unlist(lapply(sel, function(p) {
            if (p %in% names(GROUPS)) return(GROUPS[[p]])
            all_scripts[grepl(p, all_scripts, fixed = TRUE)]
        })))
        if (length(matched) == 0)
            stop("No scripts matched selector(s): ", paste(sel, collapse = ", "),
                 "\nGroups: ", paste(names(GROUPS), collapse = ", "),
                 "\nScripts: ", paste(all_scripts, collapse = ", "))
        SELECTED <- matched
        cat(sprintf("Selective run (%d of %d): %s\n",
                    length(SELECTED), length(all_scripts),
                    paste(all_scripts[all_scripts %in% SELECTED], collapse = ", ")))
    }
}

# -----------------------------------------------------------------------------
# Master log (batch mode only; interactively the console + per-script logs
# carry the output)
# -----------------------------------------------------------------------------
if (BATCH) {
    log_master_con <- file(file.path(OUTPUT, "log_master_R.txt"), open = "wt")
    sink(log_master_con, split = TRUE)
    sink(log_master_con, type = "message")
}
close_master_log <- function() {
    if (!BATCH) return(invisible(NULL))
    try(sink(type = "message"), silent = TRUE)
    try(sink(),                 silent = TRUE)
    try(close(log_master_con),  silent = TRUE)
}

cat("==================================================================\n")
cat("== 99_master.R setup done ", format(Sys.time()), "\n")
cat("==================================================================\n")

# -----------------------------------------------------------------------------
# The runner. Each call: invalidate declared outputs -> source the script in
# an isolated env -> unwind any sink it left open on error -> update the run
# manifest (preserving rows for scripts not run). After a PREP failure all
# later calls are no-ops (reset with ABORTED <- FALSE if you know better).
# -----------------------------------------------------------------------------
results  <- list()
manifest <- list()
ABORTED  <- FALSE
manifest_path <- file.path(DIAG, "run_manifest.csv")

write_manifest <- function() {
    # cur is ONE data.table (a list of columns), so it must be wrapped as a
    # single list element -- list(prev, cur), NOT c(list(prev), cur), which
    # would splay cur into its loose column vectors and feed them to rbindlist
    # as separate tables. (The original code passed `manifest`, already a
    # list-of-tables, so c() was correct there.)
    # The manifest is a plain CSV log; column types are cosmetic. fread infers
    # types from the file (a date string -> IDate/POSIXct, an all-blank column
    # -> logical NA), so we also force everything to character on both sides
    # to rule out any residual class mismatch. rbindlist drops the NULL prev.
    cur <- data.table::rbindlist(manifest, fill = TRUE)
    for (col in names(cur))
        data.table::set(cur, j = col, value = as.character(cur[[col]]))
    prev <- if (file.exists(manifest_path)) {
        p <- data.table::fread(manifest_path, colClasses = "character")
        p[!p$script %in% names(manifest)]
    } else NULL
    atomic_fwrite(data.table::rbindlist(list(prev, cur), fill = TRUE),
                  manifest_path)
}

run_script <- function(s) {
    if (!s %in% all_scripts)
        warning(s, " is not in GROUPS -- selectors and the prep-abort rule ",
                "don't know it; add it there too.")
    if (!is.null(SELECTED) && !s %in% SELECTED) return(invisible("not selected"))
    if (ABORTED) {
        cat(sprintf(">>> %s SKIPPED (a prep script failed earlier)\n", s))
        return(invisible("skipped"))
    }

    cat(sprintf("\n>>> sourcing %s\n", s))
    invalidate_outputs(s)
    t0 <- Sys.time()
    n_sink_out <- sink.number()
    n_sink_msg <- sink.number(type = "message")
    status <- tryCatch({
        source(s, local = new.env())   # isolated env so script vars don't leak
        "ok"
    }, error = function(e) conditionMessage(e))
    # A sub-script that errors mid-run leaves its sink open -- unwind to our
    # own sink level before reporting.
    if (sink.number(type = "message") > n_sink_msg) sink(type = "message")
    while (sink.number() > n_sink_out) sink()
    if (status != "ok") cat(sprintf("\n*** %s failed: %s\n", s, status))
    t1 <- Sys.time()
    dt <- as.numeric(t1 - t0, units = "secs")
    cat(sprintf("<<< %s finished in %.1f s (status: %s)\n", s, dt, status))

    results[[s]]  <<- list(status = status, seconds = dt)
    manifest[[s]] <<- data.table::data.table(
        script = s,
        status = if (status == "ok") "ok" else "failed",
        started_at = format(t0, "%Y-%m-%d %H:%M:%S"),
        ended_at   = format(t1, "%Y-%m-%d %H:%M:%S"),
        seconds = round(dt, 1),
        outputs_declared = paste(OUTPUTS[[s]], collapse = "; "),
        error_message = if (status == "ok") "" else status)
    write_manifest()

    if (status != "ok" && s %in% GROUPS$prep) {
        ABORTED <<- TRUE
        cat(sprintf("\nABORTING further scripts: prep script %s failed; downstream would only cascade-fail.\n", s))
    }
    invisible(status)
}

# =============================================================================
# KJØRELISTE -- marker linjene du vil kjøre, eller kjør hele fila for alt
# =============================================================================

# --- Data prep (1-5d): kjøres på nytt bare når rådata/terskler endres --------
run_script("1_exposure.R")
run_script("1b_load_styrk7_crosswalk.R")
run_script("2_relevant_ids.R")
run_script("3_monthly_filtered.R")
run_script("4_aggregate_cells.R")
run_script("5_apply_restrictions.R")
run_script("5b_population.R")
run_script("5c_baseline_kref.R")
run_script("5d_sample_size_diagnostic.R")

# --- Estimering (alle leser cells_flagged.rds; uavhengige av hverandre) ------
# Aktiv kjerne: firm-FE ES (6), celle-ES (6f), per-alder DiD (7b firm, 7d celle).
# Resten er kommentert ut (ikke i bruk nå) -- avkommenter ved behov; de ligger
# fortsatt i GROUPS, så selektorene kjenner dem.
run_script("6_event_study_fepois.R")
# run_script("6c_event_study_share_feols.R")             # per-capita rate ES
# run_script("6d_event_study_continuous_share_feols.R")  # continuous x young ES
run_script("6f_event_study_cellspec.R")   # cell-spec ES (pairs with 7d)
# run_script("7_triplediff_fepois.R")                    # young x post x exposure
run_script("7b_did_byage_fepois.R")
run_script("7d_did_byage_cellspec.R")   # kjør ETTER 7b (leser sample_diag_7b.csv)
# run_script("8_alt_outcomes_feols.R")                   # wage/position/hours/overtime (winsorized log_wage)

# --- Komparativt fortrinn (TUNGE; kan subsettes med outcome=/timing=/fe=) ----
# Kommentert ut (ikke i bruk nå; ~3 t kombinert). Avkommenter ved behov, eller
# kjør standalone: Rscript 6e_ca_es_firmfe.R / 7c_ca_did_firmfe.R
# run_script("6e_ca_es_firmfe.R")
# run_script("7c_ca_did_firmfe.R")

# --- BCC-replication appendix (FT-private, BCC's 6 age bins) ------------------
# A1 descriptive (light); A2 balances the BCC-binned panel; A3 reads A2's
# cells_bcc.rds, so run A2 before A3. NB: needs styrk08_handa_mapping.csv on $DATA.
run_script("A1_bcc_descriptive_agg.R")
run_script("A2_bcc_panel.R")
run_script("A3_bcc_event_study.R")

# =============================================================================
# Summary
# =============================================================================
if (length(results) > 0) {
    cat("\n==================================================================\n")
    cat("== 99_master.R done ", format(Sys.time()), "\n")
    cat("==================================================================\n")
    cat("\nScript summary:\n")
    for (s in names(results)) {
        cat(sprintf("  %-42s %8.1f s   %s\n",
                    s, results[[s]]$seconds, results[[s]]$status))
    }
    cat("\nDeliverables in", OUTPUT, ":\n")
    cat("  SECURE_SERVER_RESULTS.md (prep sections 1-6)\n")
    cat("  coefficients/coef_event_study_fepois.csv (+ _summary.csv)\n")
    cat("  coefficients/coef_event_study_share.csv  (+ _summary.csv)\n")
    cat("  coefficients/coef_event_study_continuous_share.csv (+ _summary.csv)\n")
    cat("  coefficients/coef_triplediff_fepois.csv\n")
    cat("  coefficients/coef_did_byage_fepois.csv      <- firm spec (7b)\n")
    cat("  coefficients/coef_did_byage_cellspec.csv    <- cell spec (7d); check\n")
    cat("      sum_count_all (restricted) == 7b's sum_count_all per age_bin\n")
    cat("  coefficients/coef_alt.csv, coef_count_level.csv, coef_share.csv\n")
    cat("  coefficients/coef_ca_es_firmfe.csv, coef_ca_did_firmfe.csv (+ _modelstats)\n")
    cat("  coefficients/baseline_kref_by_age{,_q}.csv\n")
    cat("  diagnostics/run_manifest.csv, settings_selftest.txt,\n")
    cat("  diagnostics/sample_diag_7b.csv + 7b_7d_sample_comparison.csv,\n")
    cat("  diagnostics/fixest_diag_*.csv, sample_size_diagnostic.csv,\n")
    cat("  diagnostics/monthly_filter_funnel.csv, aggregate_cell_counts.csv,\n")
    cat("  diagnostics/restriction_funnel.csv\n")
    cat("  log_master_R.txt + per-script log_*.txt\n")
}

close_master_log()

# Nonzero exit when anything failed, so calling shells/schedulers see it.
if (BATCH) {
    n_failed <- sum(vapply(results, function(r) r$status != "ok", logical(1)))
    if (n_failed > 0) quit(save = "no", status = 1)
}
