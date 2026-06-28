# =============================================================================
# 6_event_study_fepois.R : Poisson event-study per age bin
# =============================================================================
# R replacement for Stata 6_event_study_bcc.do, using fixest::fepois.
# BCC eq. 4.1 spec:
#
#   log E[y_{f,q,t}] = alpha_{f,q} + beta_{f,t}
#                   + sum_{q != 1, k != -1} gamma_{q,k} * 1{t=k} * 1{q'=q}
#
# Estimated separately per age_bin. Reference: q = 1 (lowest exposure, BCC
# convention), k = -1 (October 2022). Firm x month FE absorbs firm-level
# monthly shocks, but not differential within-firm seasonality across exposure
# quintiles.
# Standard errors clustered at foretak.
#
# Inputs:  $DATA/cells_flagged.rds
# Outputs: $output/coefficients/coef_event_study_fepois.csv
#          $output/coefficients/coef_event_study_fepois_summary.csv
#          $output/log_6_event_study_fepois.txt
#
# Why R + fixest: ppmlhdfe on 24M obs is impractical on the secure server.
# fixest::fepois uses Gaure-Berge demeaning + Newton-IRLS, multi-threaded,
# 10-30x faster and far lower memory.
# =============================================================================

# Source 0_settings.R from the scripts directory. Assumes the working
# directory is the scripts folder (cd before running Rscript).
if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}

req("fixest"); req("data.table")   # req() comes from 0_settings.R

# Tee all output to a log file so we can debug off-server.
# NB: on.exit at top level is ignored by R, so we close sinks via tryCatch's
# finally block (`run_main(...)` below).
log_path <- file.path(OUTPUT, "log_6_event_study_fepois.txt")
log_con  <- file(log_path, open = "wt")
sink(log_con, split = TRUE)
sink(log_con, type = "message")

close_log <- function() {
    try(sink(type = "message"), silent = TRUE)
    try(sink(),                 silent = TRUE)
    try(close(log_con),         silent = TRUE)
}

cat("== 6_event_study_fepois.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Load + aggregate cells_flagged to (frtk, age, q, ym)
# -----------------------------------------------------------------------------
d <- load_cells()
cat(sprintf("Loaded %d rows from cells_flagged.rds\n", nrow(d)))

d <- d[in_headline_priv == 1]
cat(sprintf("After in_headline_priv filter: %d rows\n", nrow(d)))

d_agg <- d[, .(y_count = sum(count_all)),
           by = .(frtk_id, age_bin, ai_q, ym)]
rm(d); gc()
cat(sprintf("After collapse to (frtk, age, q, ym): %d rows\n", nrow(d_agg)))

d_agg[, kshift := ym - YM_EVENT_ZERO]
d_agg <- d_agg[kshift >= KMIN & kshift <= KMAX]
cat(sprintf("Event-time window [%d, %d]: %d rows\n", KMIN, KMAX, nrow(d_agg)))

# -----------------------------------------------------------------------------
# Helper: parse fixest i() interaction names of the form "kshift::-22:ai_q::5"
# into integer (k, q) pairs. Returns NA when the name doesn't match.
# -----------------------------------------------------------------------------
parse_kq <- function(nm) {
    if (length(nm) == 0) {
        return(data.table(k = integer(0), ai_q = integer(0)))
    }
    m <- regmatches(nm, regexec("kshift::(-?[0-9]+):ai_q::([0-9]+)", nm))
    out <- do.call(rbind, lapply(m, function(x) {
        if (length(x) == 3) c(as.integer(x[2]), as.integer(x[3]))
        else                 c(NA_integer_, NA_integer_)
    }))
    colnames(out) <- c("k", "ai_q")
    as.data.table(out)
}

# Helper: joint Wald test (manual chi-square) on a named subset of coefs.
# Robust to non-invertible vcov via Moore-Penrose pseudo-inverse.
# Robust to fixest dropping some names (collinearity) — intersects with
# names(coef(fit)) first to avoid vcov subscript errors.
joint_wald_p <- function(fit, names_keep) {
    names_keep <- intersect(names_keep, names(coef(fit)))
    if (length(names_keep) == 0) return(NA_real_)
    b <- coef(fit)[names_keep]
    if (any(is.na(b))) {
        names_keep <- names_keep[!is.na(b)]
        b <- b[names_keep]
    }
    if (length(names_keep) == 0) return(NA_real_)
    V <- vcov(fit)[names_keep, names_keep, drop = FALSE]
    chi2 <- tryCatch(as.numeric(t(b) %*% solve(V) %*% b),
                     error = function(e) {
                         if (!requireNamespace("MASS", quietly = TRUE))
                             return(NA_real_)
                         as.numeric(t(b) %*% MASS::ginv(V) %*% b)
                     })
    if (!is.finite(chi2)) return(NA_real_)
    pchisq(chi2, df = length(names_keep), lower.tail = FALSE)
}

# -----------------------------------------------------------------------------
# Per age_bin: fit fepois, harvest (k, q) coefficients
# -----------------------------------------------------------------------------
coef_rows    <- list()
summary_rows <- list()
diag_rows    <- list()

for (a in 1:N_AGE_BINS) {

    d_a <- d_agg[age_bin == a]
    n_a      <- nrow(d_a)
    n_frtk_a <- uniqueN(d_a$frtk_id)
    cat(sprintf("\n--- age_bin = %d, n=%d, n_frtk=%d ---\n", a, n_a, n_frtk_a))

    if (n_a == 0) { cat("  no rows, skipping\n"); next }

    # Force ai_q to a proper factor with explicit levels and Q1 (lowest
    # exposure) as the reference, following BCC. Firm x month FE absorbs
    # firm-level monthly shocks, but not differential within-firm seasonality
    # across exposure quintiles.
    d_a[, ai_q := factor(ai_q, levels = c(1, 2, 3, 4, 5))]

    t0 <- Sys.time()
    fit <- tryCatch(
        fepois(y_count ~ i(kshift, ai_q, ref = -1, ref2 = "1") |
                           frtk_id^ai_q + frtk_id^ym,
               data = d_a, cluster = ~frtk_id),
        error = function(e) {
            cat("  fepois failed:", conditionMessage(e), "\n"); NULL
        }
    )
    cat(sprintf("  fit time: %.1f s\n",
                as.numeric(Sys.time() - t0, units = "secs")))
    diag_rows[[length(diag_rows) + 1L]] <-
        fixest_diag_row(fit, "6", sprintf("age%d_employment_es", a), n_a, n_frtk_a)
    if (is.null(fit)) next

    # Build a long data.table of (k, q, coef, se) from the i() interactions
    ct <- as.data.frame(coeftable(fit))
    ct$name <- rownames(ct)
    n_total_names <- length(ct$name)
    if (a == 1) {
        cat("  First 5 coef names (for parse_kq diagnostics):\n")
        cat(paste("    ", head(ct$name, 5), collapse = "\n"), "\n")
    }
    kq <- parse_kq(ct$name)
    ct$k    <- kq$k
    ct$ai_q <- kq$ai_q
    ct <- ct[!is.na(ct$k), ]
    if (a == 1) {
        cat(sprintf("  Matched %d / %d coef names to (k, ai_q) pairs\n",
                    nrow(ct), n_total_names))
    }

    cr <- data.table(
        sample  = "headline_priv",
        age_bin = a,
        k       = ct$k,
        ai_q    = ct$ai_q,
        coef    = ct[, "Estimate"],
        se      = ct[, "Std. Error"],
        n_obs   = n_a,
        n_frtk  = n_frtk_a,
        name    = ct$name
    )
    coef_rows[[as.character(a)]] <- cr[, .(sample, age_bin, k, ai_q, coef, se, n_obs, n_frtk)]

    # Per-spec summary: max|pre| Q5, mean post Q5, joint pre-trend p (Q5 only)
    pre_names <- cr[ai_q == 5 & k < -1, name]
    q5_pre    <- cr[ai_q == 5 & k < -1]
    q5_post   <- cr[ai_q == 5 & k >  -1]

    max_pre_abs  <- if (nrow(q5_pre)  > 0) max(abs(q5_pre$coef)) else NA_real_
    mean_post_q5 <- if (nrow(q5_post) > 0) mean(q5_post$coef)    else NA_real_
    pre_joint_p  <- joint_wald_p(fit, pre_names)

    summary_rows[[as.character(a)]] <- data.table(
        sample       = "headline_priv",
        age_bin      = a,
        max_pre_abs  = max_pre_abs,
        mean_post_q5 = mean_post_q5,
        pre_joint_p  = pre_joint_p,
        n_obs        = n_a,
        n_frtk       = n_frtk_a
    )

    cat(sprintf("  harvested %d coefs; max|pre|_Q5=%s mean_post_Q5=%s pre p=%s\n",
                nrow(cr),
                format(max_pre_abs,  digits = 4),
                format(mean_post_q5, digits = 4),
                format(pre_joint_p,  digits = 4)))
}

# -----------------------------------------------------------------------------
# Save
# -----------------------------------------------------------------------------
out_coefs   <- rbindlist(coef_rows,    fill = TRUE)
out_summary <- rbindlist(summary_rows, fill = TRUE)

# Guard against the degenerate case where every age_bin's fepois failed —
# rbindlist(list()) yields a 0-row 0-col data.table and setorder would
# complain that the sort columns don't exist.
if (nrow(out_coefs) > 0)   setorder(out_coefs,   age_bin, ai_q, k)
if (nrow(out_summary) > 0) setorder(out_summary, age_bin)

atomic_fwrite(out_coefs,   file.path(COEFS, "coef_event_study_fepois.csv"))
atomic_fwrite(out_summary, file.path(COEFS, "coef_event_study_fepois_summary.csv"))
atomic_fwrite(rbindlist(diag_rows),
              file.path(DIAG, "fixest_diag_6_event_study_fepois.csv"))

cat(sprintf("\nSaved %d rows to coef_event_study_fepois.csv\n",       nrow(out_coefs)))
cat(sprintf("Saved %d rows to coef_event_study_fepois_summary.csv\n", nrow(out_summary)))
cat("== 6_event_study_fepois.R done ", format(Sys.time()), " ==\n")

close_log()
