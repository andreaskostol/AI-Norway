# =============================================================================
# 0_settings.R : paths, constants and shared helpers for the full R pipeline
# =============================================================================
# Sourced at the top of every script (prep 1-5d and estimation 6-8). This is
# the single source of truth for paths, the analysis period, thresholds, and
# the helper functions shared across scripts.
#
# Data universe: SSB project 1191 (W:\1191). The previous pipeline (archived
# in scripts/stata_archive/) ran on 1183/7020 with Stata for data prep; the
# whole pipeline is now R. Rationale for constants (age window, BCC
# thresholds, reference month, foretak activity threshold) and for the
# migration itself is documented in DESIGN_CHOICES.md (sections 12, 21-23).
#
# Required packages: haven, data.table, fixest. Nothing else is assumed to
# exist on the secure server. All package calls below are namespaced
# (haven::, data.table::) so sourcing this file never loads them implicitly;
# call check_packages() (done by 99_master.R) or req() per script.
# =============================================================================

# -----------------------------------------------------------------------------
# Test hook: AI_NORWAY_TEST_ROOT re-roots every path so the pipeline can run
# end-to-end on synthetic data locally (see _make_synthetic_test_data.R).
# AI_NORWAY_PERIOD_{START,END}_{Y,M} override the period the same way.
# Both are ignored on the secure server (env vars unset).
# -----------------------------------------------------------------------------
TEST_ROOT <- Sys.getenv("AI_NORWAY_TEST_ROOT", unset = "")

.env_int <- function(name, default) {
    v <- Sys.getenv(name, unset = "")
    if (nzchar(v)) as.integer(v) else as.integer(default)
}

# -----------------------------------------------------------------------------
# Paths. Raw register data is read from W:\1191 (read-only project disk);
# intermediates live on the user area F:\1191; scripts and everything that
# leaves the server live under H:\Dokumenter (same layout as before).
#
# IMPORTANT: only the constants below ever touch W:. The canonical raw files
# are directly under atid/ and demo/ -- NEVER the stale same-named copies in
# atid/old/ and demo/Old/ (see datadoc/inkonsekvenser_1191.md section 3).
# -----------------------------------------------------------------------------
if (nzchar(TEST_ROOT)) {
    PROSJEKTDATA <- TEST_ROOT                                  # contains atid/, demo/
    DATA         <- file.path(TEST_ROOT, "data")
    PROJECT      <- file.path(TEST_ROOT, "project")
} else {
    # AI_NORWAY_PROSJEKTDATA / _DATA / _PROJECT exist for ONE purpose: the
    # Stata-vs-R port validation ("trinn A" in kritisk_evaluering, see
    # RUN_1191_UPDATE.md) -- running this R pipeline against the OLD 1183/7020
    # delivery into a separate scratch area, then comparing cells_flagged
    # against the archived Stata output with _compare_1183_overlap.R.
    # Production runs leave all three unset.
    .env_path <- function(name, default) {
        v <- Sys.getenv(name, unset = ""); if (nzchar(v)) v else default
    }
    PROSJEKTDATA <- .env_path("AI_NORWAY_PROSJEKTDATA", "W:/1191")
    DATA         <- .env_path("AI_NORWAY_DATA", "F:/1191/oysteimh/ai_norway_indiv/data")
    PROJECT      <- .env_path("AI_NORWAY_PROJECT", "H:/Dokumenter/ai_norway_indiv")
}

AMELD_DIR       <- file.path(PROSJEKTDATA, "atid")
# faste_oppl: 1191 names the file faste_oppl.dta; the 7020 delivery used
# faste_oppl_full.dta (relevant only for trinn-A validation runs).
FASTE_OPPL_PATH <- if (file.exists(file.path(PROSJEKTDATA, "demo", "faste_oppl.dta")) ||
                       !file.exists(file.path(PROSJEKTDATA, "demo", "faste_oppl_full.dta"))) {
    file.path(PROSJEKTDATA, "demo", "faste_oppl.dta")
} else {
    file.path(PROSJEKTDATA, "demo", "faste_oppl_full.dta")
}

SCRIPTS    <- file.path(PROJECT, "scripts")
OUTPUT     <- file.path(PROJECT, "from_secure_server")
COEFS      <- file.path(OUTPUT, "coefficients")
DIAG       <- file.path(OUTPUT, "diagnostics")
FIGS       <- file.path(OUTPUT, "figures")
MDFRAG     <- file.path(OUTPUT, "_md_fragments")
RESULTS_MD <- file.path(OUTPUT, "SECURE_SERVER_RESULTS.md")

for (d in c(DATA, OUTPUT, COEFS, DIAG, FIGS, MDFRAG)) {
    dir.create(d, showWarnings = FALSE, recursive = TRUE)
}

# -----------------------------------------------------------------------------
# Period covered. A-meldingen in 1191 runs 2015m1-2026m2; the analysis panel
# starts 2021m1 (matches the cell-level analysis and BCC) and ends at the
# data edge. DiD/event studies use the FULL window (DESIGN_CHOICES.md s.23).
# -----------------------------------------------------------------------------
PERIOD_START_Y <- .env_int("AI_NORWAY_PERIOD_START_Y", 2021)
PERIOD_START_M <- .env_int("AI_NORWAY_PERIOD_START_M", 1)
PERIOD_END_Y   <- .env_int("AI_NORWAY_PERIOD_END_Y",   2026)
PERIOD_END_M   <- .env_int("AI_NORWAY_PERIOD_END_M",   2)

# Reference month: October 2022 = event time k = -1.
# event_zero = November 2022 = k = 0 (ChatGPT launch Nov 30, 2022).
REF_Y        <- 2022
REF_M        <- 10
EVENT_ZERO_Y <- 2022
EVENT_ZERO_M <- 11

# Stata's ym() is (year - 1960)*12 + (month - 1). Every month index in the
# pipeline (kshift, post dummies, file loops, population) derives from this
# one function so R and the archived Stata pipeline agree exactly.
ym <- function(y, m) (y - 1960L) * 12L + (m - 1L)

YM_PERIOD_START <- ym(PERIOD_START_Y, PERIOD_START_M)
YM_PERIOD_END   <- ym(PERIOD_END_Y,   PERIOD_END_M)
YM_REF          <- ym(REF_Y,          REF_M)
YM_EVENT_ZERO   <- ym(EVENT_ZERO_Y,   EVENT_ZERO_M)

# Event-time window derived from the panel, NOT hardcoded: a fixed KMAX would
# silently drop the newest months from the event studies when the panel grows
# (the old KMAX = 36 would have cut 2025m12-2026m2). KMIN = -22, KMAX = +39
# with the 2021m1-2026m2 panel.
KMIN <- YM_PERIOD_START - YM_EVENT_ZERO
KMAX <- YM_PERIOD_END   - YM_EVENT_ZERO

# -----------------------------------------------------------------------------
# Age window: decade groups 1=21-30, 2=31-40, 3=41-50, 4=51-60.
# See DESIGN_CHOICES.md section 12.
# -----------------------------------------------------------------------------
AGE_MIN    <- 21
AGE_MAX    <- 60
YOUNG_MAX  <- 30      # triple-diff binary cut: young = age_bin 1 (21-30)
N_AGE_BINS <- 4

# -----------------------------------------------------------------------------
# Sample thresholds (rationale: DESIGN_CHOICES.md sections 6-8)
# -----------------------------------------------------------------------------
FRTK_MIN_ACTIVE <- 20    # foretak "operating" in a month: >= 20 workers 21-60
BCC_MIN_PER_AGE <- 10    # BCC: >= 10 FT workers per (firm, age) every month
BCC_MIN_TOTAL   <- 100   # BCC: sum_t count_ft >= 100 per (firm, q, age) cell

# lonn_kontant upper-tail winsorization (DESIGN_CHOICES.md section 18): cap at
# the WINSOR_HI percentile WITHIN (yrke4, month) when the occupation-month has
# >= WINSOR_MINN spells (so the percentile sits below a lone data-error record,
# e.g. the ~3e9 kr value in yrke4 9112, 2023m7); otherwise the pooled per-month
# cap. Guards every wage outcome (m_wage_all -> 7b/7d/8/7c) against stray giants.
WINSOR_HI   <- 0.999
WINSOR_MINN <- 1000L

# -----------------------------------------------------------------------------
# A-meldingen: file naming and the columns script 3 needs.
# Pattern ameld_statdata_{YYYY}_m{M}.dta with month NOT zero-padded
# (..._2021_m1.dta, ..., ..._2021_m12.dta). lopenr_person is the person key
# in every ameld_statdata vintage through 2026m2 (verified in
# datadoc/metadata_scan1191.csv; the w19_0345_ rename hit other file families).
# -----------------------------------------------------------------------------
AMELD_COLS <- c(
    "lopenr_person", "lopenr_foretak", "arb_yrke", "frtk_sektor_2014",
    "lonn_kontant", "arb_stillingspst", "arb_arbeidstid",
    "lonn_overtid_timer", "lonn_fast", "lonn_time", "lonn_time_antall",
    "arb_start"
)

ameld_path <- function(y, m) {
    file.path(AMELD_DIR, sprintf("ameld_statdata_%d_m%d.dta", y, m))
}

# All (year, month) pairs of the panel, in chronological order.
# Diagnostic mode: AI_NORWAY_MAX_MONTHS=<n> caps the grid to the first n
# months (for limited-scope test runs of the heavy prep scripts).
month_grid <- function() {
    yms  <- YM_PERIOD_START:YM_PERIOD_END
    maxm <- Sys.getenv("AI_NORWAY_MAX_MONTHS", unset = "")
    if (nzchar(maxm)) yms <- head(yms, as.integer(maxm))
    data.frame(y  = yms %/% 12L + 1960L,
               m  = yms %% 12L + 1L,
               ym = yms)
}

# -----------------------------------------------------------------------------
# Package handling
# -----------------------------------------------------------------------------
req <- function(pkg) {
    if (!require(pkg, character.only = TRUE, quietly = TRUE))
        stop(sprintf("Package '%s' not installed.", pkg))
}

# Verify all required packages up front (99_master.R calls this once).
check_packages <- function() {
    missing <- Filter(function(p) !requireNamespace(p, quietly = TRUE),
                      c("haven", "data.table", "fixest"))
    if (length(missing) > 0)
        stop("Missing required package(s): ", paste(missing, collapse = ", "),
             ". The pipeline needs haven, data.table and fixest.")
    invisible(TRUE)
}

# Thread cap for data.table and fixest. Default: all cores MINUS TWO, so the
# remote-desktop/RStudio front-end stays responsive while the heavy fits run
# (an R process saturating every core starves the session connection -- the
# "disconnected, only one connection at a time" symptom). Override with
# AI_NORWAY_THREADS=<n>; wall-time cost of leaving two cores free is small.
set_threads <- function() {
    nc <- tryCatch(parallel::detectCores(), error = function(e) NA_integer_)
    if (is.na(nc) || nc < 1L) nc <- 4L
    threads <- .env_int("AI_NORWAY_THREADS", max(1L, nc - 2L))
    if (requireNamespace("data.table", quietly = TRUE))
        data.table::setDTthreads(threads)
    if (requireNamespace("fixest", quietly = TRUE))
        try(fixest::setFixest_nthreads(threads), silent = TRUE)
    invisible(threads)
}
N_THREADS <- set_threads()   # applied on every source() of this file

# -----------------------------------------------------------------------------
# String helpers
# -----------------------------------------------------------------------------
# Left-pad with zeros to width w. NOT sprintf("%07s", x): that pads with
# SPACES in R. NA stays NA. Used for yrke7 (7 chars) and yrke4 (4 chars) so
# codes like "0111101" keep their leading zero.
pad0 <- function(x, w) {
    x <- trimws(as.character(x))
    ifelse(is.na(x), NA_character_,
           paste0(strrep("0", pmax(0L, w - nchar(x))), x))
}

# Integer with thousands separator, for markdown tables / logs.
fmt_int <- function(x) formatC(round(x), big.mark = ",", format = "d")

# Log the in-memory size of a big object (memory-budget tracking in the
# heavy prep scripts).
log_size <- function(x, name) {
    cat(sprintf("  [mem] %s: %s\n", name,
                format(utils::object.size(x), units = "GB")))
}

# -----------------------------------------------------------------------------
# Defensive .dta readers
# -----------------------------------------------------------------------------
# Reads off the W: secure-project share occasionally fail mid-run with a
# transient "Unable to read from file" (share hiccup / file lock / AV scan) and
# abort an otherwise-fine 2-hour run -- a different month each time. Retry a few
# times with a short backoff before giving up. A genuinely missing file or
# renamed column still fails: file.exists() is checked first, and the column
# probe runs on the returned header, so this only papers over transient I/O.
DTA_READ_TRIES <- 5L
DTA_READ_WAIT  <- 15      # seconds between attempts

read_dta_retry <- function(path, ...) {
    for (attempt in seq_len(DTA_READ_TRIES)) {
        d <- tryCatch(haven::read_dta(path, ...), error = function(e) e)
        if (!inherits(d, "error")) return(d)
        if (attempt == DTA_READ_TRIES)
            stop(sprintf("Failed reading %s after %d attempts: %s",
                         path, DTA_READ_TRIES, conditionMessage(d)))
        cat(sprintf("  [retry] read failed (attempt %d/%d): %s -- waiting %gs\n",
                    attempt, DTA_READ_TRIES, conditionMessage(d), DTA_READ_WAIT))
        flush.console()
        Sys.sleep(DTA_READ_WAIT)
    }
}

# Read exactly `cols` from a .dta file. Probes the header first (n_max = 1 is
# cheap) and stops with the full list of missing columns -- a renamed variable
# in a new delivery should fail loudly here, not produce NAs downstream.
# Returns a data.table. Both reads go through read_dta_retry (W:-share I/O).
read_dta_cols <- function(path, cols) {
    if (!file.exists(path)) stop("File not found: ", path)
    have <- names(read_dta_retry(path, n_max = 1))
    miss <- setdiff(cols, have)
    if (length(miss) > 0)
        stop("Missing column(s) in ", path, ": ", paste(miss, collapse = ", "))
    d <- read_dta_retry(path, col_select = tidyselect::all_of(cols))
    data.table::setDT(d)
    d
}

# faste_oppl.dta: the person key is `w19_0345_lopenr_person` in the current
# 1191 delivery (was `lopenr_person` in 7020 and in demo/Old). Accept either
# name, return a data.table that always has `lopenr_person`
# (see datadoc/inkonsekvenser_1191.md section 1).
read_faste_oppl <- function(vars) {
    have <- names(read_dta_retry(FASTE_OPPL_PATH, n_max = 1))
    id   <- intersect(c("lopenr_person", "w19_0345_lopenr_person"), have)
    if (length(id) == 0)
        stop("Neither lopenr_person nor w19_0345_lopenr_person found in ",
             FASTE_OPPL_PATH)
    miss <- setdiff(vars, have)
    if (length(miss) > 0)
        stop("Missing column(s) in ", FASTE_OPPL_PATH, ": ",
             paste(miss, collapse = ", "))
    d <- read_dta_retry(FASTE_OPPL_PATH,
                         col_select = tidyselect::all_of(c(id[1], vars)))
    data.table::setDT(d)
    if (id[1] != "lopenr_person")
        data.table::setnames(d, id[1], "lopenr_person")
    d
}

# -----------------------------------------------------------------------------
# Loaders for the pipeline's own intermediates (.rds), with schema checks so
# a stale or half-built file fails at load, not mid-regression.
# -----------------------------------------------------------------------------
.load_rds <- function(file, required_cols) {
    path <- file.path(DATA, file)
    if (!file.exists(path))
        stop(path, " not found -- run the prep scripts (99_master.R prep) first.")
    d <- readRDS(path)
    data.table::setDT(d)
    miss <- setdiff(required_cols, names(d))
    if (length(miss) > 0)
        stop(file, " is missing column(s): ", paste(miss, collapse = ", "),
             " -- rerun the prep scripts.")
    d
}

load_cells <- function() {
    .load_rds("cells_flagged.rds", c(
        "lopenr_foretak", "frtk_id", "yrke4", "yrke4_id", "sekt", "age_bin",
        "ym", "ai_q", "exposure_score", "exposure_std",
        "count_all", "count_ft", "count_new",
        "m_wage_all", "m_wage_ft", "m_position_all", "m_position_ft",
        "m_basehours_all", "m_basehours_ft", "m_overtime_all", "m_overtime_ft",
        "in_headline", "in_headline_priv", "in_ft", "in_ft_priv", "in_bcc_full"
    ))
}

load_population <- function() {
    .load_rds("population_by_agebin_ym.rds", c("age_bin", "ym", "population"))
}

# -----------------------------------------------------------------------------
# Stata [aw=] summarize semantics, for the employment-weighted exposure
# standardization in script 4 (DESIGN_CHOICES.md section 9): drop rows with
# missing/non-positive weight, normalize weights to sum to N, variance with
# denominator N - 1 on the normalized weights.
# -----------------------------------------------------------------------------
stata_aw_sd <- function(x, w) {
    keep <- !is.na(x) & !is.na(w) & w > 0
    # Coerce to double BEFORE arithmetic: with integer w (count_all) and n in
    # the millions, integer w * n and sum(w) overflow 32-bit and silently
    # return NA -- which made exposure_std all-NA in the first real 1191 run.
    x <- as.numeric(x[keep]); w <- as.numeric(w[keep])
    n  <- length(x)
    wn <- w * n / sum(w)
    m  <- sum(wn * x) / n
    v  <- sum(wn * (x - m)^2) / (n - 1)
    out <- list(mean = m, sd = sqrt(v), n = n)
    stopifnot(is.finite(out$mean), is.finite(out$sd))
    out
}

# -----------------------------------------------------------------------------
# Atomic writes: write to a tempfile in the same directory, then rename over
# the target. An interrupted run can then never leave a half-written
# cells_flagged.rds or coefficient CSV that downstream code would silently
# trust.
# -----------------------------------------------------------------------------
.atomic_move <- function(tmp, path) {
    if (file.exists(path)) file.remove(path)   # Windows rename won't overwrite
    if (!file.rename(tmp, path))
        stop("Atomic rename failed: ", tmp, " -> ", path)
    invisible(path)
}

atomic_saveRDS <- function(object, path, compress = TRUE) {
    tmp <- paste0(path, ".tmp")
    saveRDS(object, tmp, compress = compress)
    .atomic_move(tmp, path)
}

atomic_fwrite <- function(dt, path) {
    tmp <- paste0(path, ".tmp")
    data.table::fwrite(dt, tmp)
    .atomic_move(tmp, path)
}

# -----------------------------------------------------------------------------
# Diagnostics helpers for the estimation scripts
# -----------------------------------------------------------------------------
# One row of fixest model diagnostics: estimation N, input N, dropped obs
# (singletons / only-0 FE), cluster count on the input slice, the y-sum over
# the rows fixest actually used (via y = fitted + response residuals), and
# convergence. Written per script to $DIAG/fixest_diag_<script>.csv so we can
# see when fixest silently changes the estimation sample.
fixest_diag_row <- function(fit, script, label, n_input, n_clusters_input) {
    if (is.null(fit)) {
        return(data.table::data.table(
            script = script, label = label, n_input = n_input,
            n_obs_model = NA_integer_, n_dropped_obs = NA_integer_,
            n_clusters_input = n_clusters_input,
            y_sum_model_sample = NA_real_, convergence = "fit_failed"))
    }
    y_sum <- tryCatch(sum(predict(fit) + resid(fit, type = "response")),
                      error = function(e) NA_real_)
    conv <- tryCatch({
        cs <- fit$convStatus
        if (is.null(cs)) "n/a" else as.character(isTRUE(cs))
    }, error = function(e) "n/a")
    data.table::data.table(
        script = script, label = label, n_input = n_input,
        n_obs_model = fit$nobs, n_dropped_obs = n_input - fit$nobs,
        n_clusters_input = n_clusters_input,
        y_sum_model_sample = y_sum, convergence = conv)
}

# Multi-granularity sample diagnostics for the 7b/7d identical-sample check
# (kritisk_evaluering: equality of totals per age_bin is too weak -- compare
# the distribution over months, quintiles and post as well). Input: the
# in_headline_priv cell slice BEFORE any collapsing (needs age_bin, ym, ai_q,
# count_all, lopenr_foretak, yrke4). Output: long (metric, age_bin, ym, ai_q,
# post, value); both 7b and 7d compute this independently from their own
# slice and the comparison asserts row-for-row equality.
sample_diag <- function(dt) {
    p <- function(ymv) as.integer(ymv > YM_REF)
    rbind(
        dt[, .(metric = "sum_count_all", ym = NA_integer_, ai_q = NA_integer_,
               post = NA_integer_, value = sum(count_all)), by = age_bin],
        dt[, .(metric = "sum_count_all_by_ym", ai_q = NA_integer_,
               post = NA_integer_, value = sum(count_all)), by = .(age_bin, ym)],
        dt[, .(metric = "sum_count_all_by_aiq", ym = NA_integer_,
               post = NA_integer_, value = sum(count_all)), by = .(age_bin, ai_q)],
        dt[, .(metric = "sum_count_all_by_post_aiq", ym = NA_integer_,
               value = sum(count_all)), by = .(age_bin, post = p(ym), ai_q)],
        dt[, .(metric = "n_yrke4", ym = NA_integer_, ai_q = NA_integer_,
               post = NA_integer_, value = uniqueN(yrke4)), by = age_bin],
        dt[, .(metric = "n_yrke4_by_ym", ai_q = NA_integer_,
               post = NA_integer_, value = uniqueN(yrke4)), by = .(age_bin, ym)],
        dt[, .(metric = "n_frtk", ym = NA_integer_, ai_q = NA_integer_,
               post = NA_integer_, value = uniqueN(lopenr_foretak)), by = age_bin],
        use.names = TRUE, fill = TRUE
    )[order(metric, age_bin, ym, ai_q, post)]
}

# -----------------------------------------------------------------------------
# Per-script logging: every script tees its output to
# $OUTPUT/log_<scriptname>.txt (the pattern the estimation scripts already
# used, factored out). open_log()/close_log() manage one sink at a time.
# -----------------------------------------------------------------------------
.log_env <- new.env(parent = emptyenv())

open_log <- function(name) {
    path <- file.path(OUTPUT, sprintf("log_%s.txt", name))
    con  <- file(path, open = "wt")
    sink(con, split = TRUE)
    sink(con, type = "message")
    .log_env$con <- con
    invisible(path)
}

close_log <- function() {
    try(sink(type = "message"), silent = TRUE)
    try(sink(),                 silent = TRUE)
    if (!is.null(.log_env$con)) {
        try(close(.log_env$con), silent = TRUE)
        .log_env$con <- NULL
    }
    invisible(NULL)
}

# -----------------------------------------------------------------------------
# Markdown fragment system (R port of stata_archive/_rebuild_results_md.do).
# Each prep script writes its section(s) to $MDFRAG/section_<id>.md and then
# calls rebuild_results_md(), which concatenates all currently-existing
# fragments in order into SECURE_SERVER_RESULTS.md. Re-running one script
# refreshes only its fragment; the master .md is rebuilt cleanly each time.
#
# Sections 00-06 are written by the prep scripts (1, 2, 3, 4, 5). The legacy
# Stata estimation sections (07-10) are kept in the order so old fragments
# still assemble; the R estimation scripts deliver coefficient CSVs + logs
# instead of fragments.
# -----------------------------------------------------------------------------
FRAGMENT_ORDER <- c("00", "01", "02", "03", "04", "05", "06",
                    "07", "07c", "07d", "08", "09", "09b", "09c", "10")

write_fragment <- function(frag_id, lines) {
    writeLines(lines, file.path(MDFRAG, sprintf("section_%s.md", frag_id)))
    invisible(NULL)
}

rebuild_results_md <- function() {
    paths <- file.path(MDFRAG, sprintf("section_%s.md", FRAGMENT_ORDER))
    paths <- paths[file.exists(paths)]
    out   <- unlist(lapply(paths, readLines))
    writeLines(out, RESULTS_MD)
    invisible(RESULTS_MD)
}

# -----------------------------------------------------------------------------
# Selftests: the settings layer is the API everything else builds on, so its
# helpers are verified by fixture before any run. 99_master.R calls this once
# (writes diagnostics/settings_selftest.txt); set AI_NORWAY_RUN_SELFTESTS=1 to
# run them on every source().
# -----------------------------------------------------------------------------
run_settings_selftests <- function(write_file = TRUE) {
    stopifnot(ym(2022, 11) == 754L)
    stopifnot(KMIN == YM_PERIOD_START - YM_EVENT_ZERO)
    stopifnot(KMAX == YM_PERIOD_END   - YM_EVENT_ZERO)
    stopifnot(identical(pad0("111101", 7), "0111101"))
    stopifnot(identical(pad0("0310", 4), "0310"))
    stopifnot(identical(pad0("12345", 4), "12345"))
    stopifnot(is.na(pad0(NA_character_, 7)))
    p1 <- ameld_path(2021, 1)
    stopifnot(grepl("atid", p1, fixed = TRUE),
              !grepl("/old/|/Old/|_bak", p1))
    # stata_aw_sd against a hand-computed fixture:
    # x=(1,2,3), w=(1,1,2): wn=(.75,.75,1.5), mean=2.25, var=2.0625/2=1.03125
    s <- stata_aw_sd(c(1, 2, 3, NA), c(1, 1, 2, 5))
    stopifnot(s$n == 3L, abs(s$mean - 2.25) < 1e-12,
              abs(s$sd - sqrt(1.03125)) < 1e-12)
    # ... and against integer-overflow weights (caught a real bug: integer
    # count_all x millions of cells overflowed w * n and sum(w) -> all-NA).
    # Equal weights 1e9 -> wn = 1 each -> mean 2, sd 1.
    s2 <- stata_aw_sd(c(1, 2, 3), c(1000000000L, 1000000000L, 1000000000L))
    stopifnot(s2$n == 3L, abs(s2$mean - 2) < 1e-12, abs(s2$sd - 1) < 1e-12)
    g <- month_grid()
    stopifnot(nrow(g) >= 1, g$ym[1] == YM_PERIOD_START,
              all(diff(g$ym) == 1L))
    if (write_file)
        writeLines(c("settings selftests: ALL PASS",
                     sprintf("run at %s", format(Sys.time())),
                     sprintf("period %dm%d-%dm%d, k in [%d, %d]",
                             PERIOD_START_Y, PERIOD_START_M,
                             PERIOD_END_Y, PERIOD_END_M, KMIN, KMAX)),
                   file.path(DIAG, "settings_selftest.txt"))
    invisible(TRUE)
}
if (identical(Sys.getenv("AI_NORWAY_RUN_SELFTESTS"), "1")) run_settings_selftests()

message(sprintf(
    "0_settings.R loaded. DATA=%s, OUTPUT=%s, period %dm%d-%dm%d (k in [%d, %d]), %d threads%s",
    DATA, OUTPUT, PERIOD_START_Y, PERIOD_START_M, PERIOD_END_Y, PERIOD_END_M,
    KMIN, KMAX, N_THREADS,
    if (nzchar(TEST_ROOT)) sprintf(" [TEST_ROOT=%s]", TEST_ROOT) else ""
))
