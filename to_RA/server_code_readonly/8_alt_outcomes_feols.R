# =============================================================================
# 8_alt_outcomes_feols.R : triple-diff regressions on alt outcomes (linear OLS)
# =============================================================================
# R replacement for Stata 8_alt_outcomes.do, 8b_alt_outcomes_count_level.do and
# 8c_share_triplediff.do, using fixest::feols. All three Stata scripts share
# the same triple-diff specification and FE structure, so they are bundled
# here in a single R run that loads cells_flagged.rds once.
#
# Spec (all blocks):
#   y_{f,a,e,t} = alpha_{f,a} + beta_{f,t} + lambda_{a,t}
#               + B * young * POST * exposure_std + (2-way) + e
#
# young = 1{age_bin == 1}. Time reference is the baseline month k = -1 (Oct
# 2022): each pre-month is its own event-time level (kk) interacted with
# exposure and all post months collapse to POST, so B is measured vs Oct 2022,
# NOT vs the pooled pre-period (matches 6/7/7b/7c). The triple interaction is
# carried by young_exposure_std = young * exposure_std, so i(kk, young_exposure_std)
# yields kk::POST:young_exposure_std = B. FE: foretak x age + foretak x time +
# age x time. Standard errors clustered at foretak.
#
# Block 1 (replaces 8_alt_outcomes.do) -- coef_alt.csv:
#   4 intensive-margin outcomes (cell-mean of underlying *_all variables),
#   cells weighted by count_all so OLS on cell means is equivalent to OLS on
#   individual-level data. Drop rows with missing outcome; for log outcomes,
#   drop cell means <= 0.
#     ln_wage:      ln(m_wage_all)
#     position:     m_position_all
#     ln_basehours: ln(m_basehours_all)
#     overtime:     m_overtime_all
#
# Block 2 (replaces 8b_alt_outcomes_count_level.do) -- coef_count_level.csv:
#   y = count_all (zero-filled by the balanced panel on synthetic cells).
#   Unweighted linear OLS.
#
# Block 3 (replaces 8c_share_triplediff.do) -- coef_share.csv:
#   y = count_all / N_{age_bin, ym}, where N is SSB age-cohort population.
#   Cells weighted by population.
#
# Inputs:  $DATA/cells_flagged.rds
#          $DATA/population_by_agebin_ym.rds  (block 3 only)
# Outputs: $output/coefficients/coef_alt.csv         (block 1, 4 outcomes x 4 coefs)
#          $output/coefficients/coef_count_level.csv (block 2, 4 coefs)
#          $output/coefficients/coef_share.csv       (block 3, 4 coefs)
#          $output/log_8_alt_outcomes_feols.txt
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}

req("fixest"); req("data.table")   # req() comes from 0_settings.R

log_path <- file.path(OUTPUT, "log_8_alt_outcomes_feols.txt")
log_con  <- file(log_path, open = "wt")
sink(log_con, split = TRUE)
sink(log_con, type = "message")
close_log <- function() {
    try(sink(type = "message"), silent = TRUE)
    try(sink(),                 silent = TRUE)
    try(close(log_con),         silent = TRUE)
}

cat("== 8_alt_outcomes_feols.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Coefficient harvester: keep the 4 triple-diff terms, rename to Stata-style.
# With the baseline-month (kk) parameterization the four terms have fixed,
# exact fixest names, so we match by name (no ambiguity):
#   c.exposure_std                -> "exposure_std"                  (slope at k=-1)
#   c.young#c.exposure_std        -> "young_exposure_std"            (young slope at k=-1)
#   c.post#c.exposure_std         -> "kk::POST:exposure_std"         (post x exposure vs k=-1)
#   c.young#c.post#c.exposure_std -> "kk::POST:young_exposure_std"   (triple-diff B vs k=-1)
# The output coef_name labels are unchanged, so downstream tables still parse.
# -----------------------------------------------------------------------------
harvest_coefs <- function(fit, sample_name, outcome_label,
                          n_obs, n_frtk, include_outcome = TRUE) {
    if (is.null(fit)) return(NULL)
    ct <- as.data.frame(coeftable(fit))
    ct$name <- rownames(ct)

    rows <- list()
    add_row <- function(cn_stata, fit_name) {
        i <- which(ct$name == fit_name)
        if (length(i) == 0) {
            return(invisible(NULL))
        }
        b  <- ct[i[1], "Estimate"]
        # Skip collinearity-dropped (NA) estimates: downstream code expects only
        # successful estimates in the CSV (matches Stata `if !missing(b)`).
        if (is.na(b)) {
            return(invisible(NULL))
        }
        se <- ct[i[1], "Std. Error"]
        t  <- if (!is.na(se) && se > 0) b / se else NA_real_
        rows[[length(rows) + 1L]] <<- data.table(
            outcome   = outcome_label,
            sample    = sample_name,
            coef_name = cn_stata,
            estimate  = b,
            se        = se,
            t_stat    = t,
            n_obs     = n_obs,
            n_frtk    = n_frtk
        )
    }

    add_row("c.exposure_std",                "exposure_std")
    add_row("c.young#c.exposure_std",        "young_exposure_std")
    add_row("c.post#c.exposure_std",         "kk::POST:exposure_std")
    add_row("c.young#c.post#c.exposure_std", "kk::POST:young_exposure_std")

    out <- rbindlist(rows, fill = TRUE)
    if (!include_outcome && nrow(out) > 0) out[, outcome := NULL]
    out
}

# -----------------------------------------------------------------------------
# Load cells once and prepare shared regressors
# -----------------------------------------------------------------------------
d <- load_cells()
cat(sprintf("Loaded %d rows from cells_flagged.rds\n", nrow(d)))

d <- d[in_headline_priv == 1]
cat(sprintf("After in_headline_priv filter: %d rows\n", nrow(d)))

d[, age_bin := as.integer(age_bin)]
d[, ym      := as.integer(ym)]
d[, young   := as.integer(age_bin == 1)]
# kk = event-time level (each pre-month its own value, post -> "POST", ref k=-1
# = Oct 2022); young_exposure_std carries the triple interaction. See header.
d[, kk      := fifelse(ym >= YM_EVENT_ZERO, "POST", as.character(ym - YM_EVENT_ZERO))]
d[, young_exposure_std := young * exposure_std]

n_frtk_full <- uniqueN(d$frtk_id)

# =============================================================================
# Block 1: intensive-margin outcomes (replaces 8_alt_outcomes.do)
# =============================================================================
cat("\n========== Block 1: intensive-margin outcomes ==========\n")

# label | m_var          | log? | extra-drop (TRUE = require y > 0)
outcomes <- list(
    list(label = "ln_wage",      m_var = "m_wage_all",      log = TRUE),
    list(label = "position",     m_var = "m_position_all",  log = FALSE),
    list(label = "ln_basehours", m_var = "m_basehours_all", log = TRUE),
    list(label = "overtime",     m_var = "m_overtime_all",  log = FALSE)
)

block1_rows <- list()
diag_rows   <- list()

for (o in outcomes) {
    label  <- o$label
    m_var  <- o$m_var
    do_log <- o$log
    cat(sprintf("\n--- outcome = %s (source = %s, log = %s) ---\n",
                label, m_var, do_log))

    if (!m_var %in% names(d)) {
        cat(sprintf("  WARNING: variable %s not in cells_flagged.rds; skipping.\n", m_var))
        next
    }

    # Subset to cells with a valid outcome. For log outcomes also require > 0.
    if (do_log) {
        idx <- !is.na(d[[m_var]]) & d[[m_var]] > 0
    } else {
        idx <- !is.na(d[[m_var]])
    }
    da <- d[idx]
    if (do_log) {
        da[, y := log(get(m_var))]
    } else {
        da[, y := get(m_var)]
    }
    n_o <- nrow(da)
    nf_o <- uniqueN(da$frtk_id)
    cat(sprintf("  n_obs = %d  n_frtk = %d\n", n_o, nf_o))
    if (n_o == 0) { cat("  no rows, skipping\n"); next }

    t0 <- Sys.time()
    fit <- tryCatch(
        feols(y ~ exposure_std + young_exposure_std
                + i(kk, exposure_std,       ref = "-1")
                + i(kk, young_exposure_std, ref = "-1") |
                    frtk_id^age_bin + frtk_id^ym + age_bin^ym,
              data = da, weights = ~count_all, cluster = ~frtk_id),
        error = function(e) {
            cat("  feols failed:", conditionMessage(e), "\n"); NULL
        }
    )
    cat(sprintf("  fit time: %.1f s\n",
                as.numeric(Sys.time() - t0, units = "secs")))

    block1_rows[[length(block1_rows) + 1L]] <-
        harvest_coefs(fit, "headline_priv", label, n_o, nf_o)
    diag_rows[[length(diag_rows) + 1L]] <-
        fixest_diag_row(fit, "8", sprintf("block1_%s", label), n_o, nf_o)
}

block1 <- rbindlist(Filter(Negate(is.null), block1_rows), fill = TRUE)
if (nrow(block1) > 0) setorder(block1, outcome, sample, coef_name)
atomic_fwrite(block1, file.path(COEFS, "coef_alt.csv"))
cat(sprintf("Block 1: saved %d rows to coef_alt.csv\n", nrow(block1)))

# =============================================================================
# Block 2: count-level triple-diff (replaces 8b_alt_outcomes_count_level.do)
# =============================================================================
cat("\n========== Block 2: count-level triple-diff ==========\n")

n_b2  <- nrow(d)
nf_b2 <- n_frtk_full
cat(sprintf("  n_obs = %d  n_frtk = %d\n", n_b2, nf_b2))

t0 <- Sys.time()
fit_b2 <- tryCatch(
    feols(count_all ~ exposure_std + young_exposure_std
                    + i(kk, exposure_std,       ref = "-1")
                    + i(kk, young_exposure_std, ref = "-1") |
                       frtk_id^age_bin + frtk_id^ym + age_bin^ym,
          data = d, cluster = ~frtk_id),
    error = function(e) {
        cat("  feols failed:", conditionMessage(e), "\n"); NULL
    }
)
cat(sprintf("  fit time: %.1f s\n",
            as.numeric(Sys.time() - t0, units = "secs")))

block2 <- harvest_coefs(fit_b2, "headline_priv", "count_all",
                       n_b2, nf_b2, include_outcome = FALSE)
diag_rows[[length(diag_rows) + 1L]] <-
    fixest_diag_row(fit_b2, "8", "block2_count_level", n_b2, nf_b2)
if (is.null(block2)) block2 <- data.table()
if (nrow(block2) > 0) setorder(block2, sample, coef_name)
atomic_fwrite(block2, file.path(COEFS, "coef_count_level.csv"))
cat(sprintf("Block 2: saved %d rows to coef_count_level.csv\n", nrow(block2)))

# =============================================================================
# Block 3: per-capita rate triple-diff (replaces 8c_share_triplediff.do)
# =============================================================================
cat("\n========== Block 3: per-capita rate triple-diff ==========\n")

pop_path <- file.path(DATA, "population_by_agebin_ym.rds")
if (!file.exists(pop_path)) {
    cat("  WARNING: population_by_agebin_ym.rds not found; skipping block 3.\n")
} else {
    pop <- load_population()[, .(age_bin, ym, population)]
    pop[, age_bin := as.integer(age_bin)]
    pop[, ym      := as.integer(ym)]

    dc <- merge(d, pop, by = c("age_bin", "ym"), all.x = TRUE)
    n_missing <- dc[, sum(is.na(population))]
    if (n_missing > 0) {
        cat(sprintf("  WARNING: %d rows missing population; dropping.\n", n_missing))
        dc <- dc[!is.na(population)]
    }
    dc[, rate := count_all / population]

    n_b3  <- nrow(dc)
    nf_b3 <- uniqueN(dc$frtk_id)
    cat(sprintf("  n_obs = %d  n_frtk = %d\n", n_b3, nf_b3))

    t0 <- Sys.time()
    fit_b3 <- tryCatch(
        feols(rate ~ exposure_std + young_exposure_std
                   + i(kk, exposure_std,       ref = "-1")
                   + i(kk, young_exposure_std, ref = "-1") |
                      frtk_id^age_bin + frtk_id^ym + age_bin^ym,
              data = dc, weights = ~population, cluster = ~frtk_id),
        error = function(e) {
            cat("  feols failed:", conditionMessage(e), "\n"); NULL
        }
    )
    cat(sprintf("  fit time: %.1f s\n",
                as.numeric(Sys.time() - t0, units = "secs")))

    block3 <- harvest_coefs(fit_b3, "headline_priv", "rate",
                           n_b3, nf_b3, include_outcome = FALSE)
    diag_rows[[length(diag_rows) + 1L]] <-
        fixest_diag_row(fit_b3, "8", "block3_rate", n_b3, nf_b3)
    if (is.null(block3)) block3 <- data.table()
    if (nrow(block3) > 0) setorder(block3, sample, coef_name)
    atomic_fwrite(block3, file.path(COEFS, "coef_share.csv"))
    cat(sprintf("Block 3: saved %d rows to coef_share.csv\n", nrow(block3)))
}

atomic_fwrite(rbindlist(diag_rows),
              file.path(DIAG, "fixest_diag_8_alt_outcomes_feols.csv"))
cat("Wrote diagnostics/fixest_diag_8_alt_outcomes_feols.csv\n")

cat("\n== 8_alt_outcomes_feols.R done ", format(Sys.time()), " ==\n")

close_log()
