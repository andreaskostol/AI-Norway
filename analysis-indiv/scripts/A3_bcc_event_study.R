# =============================================================================
# A3_bcc_event_study.R : BCC Fig-4 Poisson firm-FE event study (BCC bins, FT)
# =============================================================================
# Clone of 6_event_study_fepois.R on the BCC-appendix panel: BCC's six age bins,
# full-time employment (count_ft) on the in_bcc_full sample (FT-private + BCC's
# >=10/>=100 cell-presence rules), BCC eq. 4.1 spec:
#   log E[y_{f,q,t}] = alpha_{f,q} + beta_{f,t}
#                    + sum_{q != 1, k != -1} gamma_{q,k} 1{q'=q} 1{t-t0=k}
# Reference q = 1 (lowest exposure, BCC), k = -1 (Oct 2022), cluster foretak.
#
# Inputs:  $DATA/cells_bcc.rds (from A2_bcc_panel.R)
# Outputs: $output/coefficients/coef_bcc_event_study.csv
#          $output/coefficients/coef_bcc_event_study_summary.csv
#          $output/diagnostics/fixest_diag_A3_bcc_event_study.csv
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("fixest"); req("data.table")

open_log("A3_bcc_event_study")
cat("== A3_bcc_event_study.R starting ", format(Sys.time()), " ==\n")

N_BCC_BINS <- 6L
BCC_AGE_LAB <- c("22-25", "26-30", "31-34", "35-40", "41-49", "50-55")

parse_kq <- function(nm) {
    if (length(nm) == 0) return(data.table(k = integer(0), ai_q = integer(0)))
    m <- regmatches(nm, regexec("kshift::(-?[0-9]+):ai_q::([0-9]+)", nm))
    out <- do.call(rbind, lapply(m, function(x)
        if (length(x) == 3) c(as.integer(x[2]), as.integer(x[3]))
        else c(NA_integer_, NA_integer_)))
    colnames(out) <- c("k", "ai_q"); as.data.table(out)
}

joint_wald_p <- function(fit, names_keep) {
    names_keep <- intersect(names_keep, names(coef(fit)))
    if (length(names_keep) == 0) return(NA_real_)
    b <- coef(fit)[names_keep]
    if (any(is.na(b))) { names_keep <- names_keep[!is.na(b)]; b <- b[names_keep] }
    if (length(names_keep) == 0) return(NA_real_)
    V <- vcov(fit)[names_keep, names_keep, drop = FALSE]
    chi2 <- tryCatch(as.numeric(t(b) %*% solve(V) %*% b),
                     error = function(e) {
                         if (!requireNamespace("MASS", quietly = TRUE)) return(NA_real_)
                         as.numeric(t(b) %*% MASS::ginv(V) %*% b)
                     })
    if (!is.finite(chi2)) return(NA_real_)
    pchisq(chi2, df = length(names_keep), lower.tail = FALSE)
}

# -----------------------------------------------------------------------------
# Load BCC panel, restrict to in_bcc_full, collapse to (frtk, age, q, ym)
# -----------------------------------------------------------------------------
d <- readRDS(file.path(DATA, "cells_bcc.rds"))
setDT(d)
d <- d[in_bcc_full == 1L]
cat(sprintf("in_bcc_full rows: %s (%s foretak)\n",
            fmt_int(nrow(d)), fmt_int(uniqueN(d$frtk_id))))

d_agg <- d[, .(y_count = sum(count_ft)), by = .(frtk_id, age_bin, ai_q, ym)]
rm(d); gc()
d_agg[, kshift := ym - YM_EVENT_ZERO]
d_agg <- d_agg[kshift >= KMIN & kshift <= KMAX]

coef_rows <- list(); summary_rows <- list(); diag_rows <- list()
for (a in 1:N_BCC_BINS) {
    d_a <- d_agg[age_bin == a]
    n_a <- nrow(d_a); n_frtk_a <- uniqueN(d_a$frtk_id)
    cat(sprintf("\n--- bcc_age %d (%s): n=%d, n_frtk=%d ---\n",
                a, BCC_AGE_LAB[a], n_a, n_frtk_a))
    if (n_a == 0) { cat("  no rows, skipping\n"); next }
    d_a[, ai_q := factor(ai_q, levels = 1:5)]

    fit <- tryCatch(
        fepois(y_count ~ i(kshift, ai_q, ref = -1, ref2 = "1") |
                           frtk_id^ai_q + frtk_id^ym,
               data = d_a, cluster = ~frtk_id),
        error = function(e) { cat("  fepois failed:", conditionMessage(e), "\n"); NULL })
    diag_rows[[length(diag_rows) + 1L]] <-
        fixest_diag_row(fit, "A3", sprintf("bcc_age%d_employment_ft", a), n_a, n_frtk_a)
    if (is.null(fit)) next

    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    kq <- parse_kq(ct$name); ct$k <- kq$k; ct$ai_q <- kq$ai_q
    ct <- ct[!is.na(ct$k), ]
    cr <- data.table(sample = "in_bcc_full", age_bin = a, k = ct$k, ai_q = ct$ai_q,
                     coef = ct[, "Estimate"], se = ct[, "Std. Error"],
                     n_obs = n_a, n_frtk = n_frtk_a, name = ct$name)
    coef_rows[[length(coef_rows) + 1L]] <-
        cr[, .(sample, age_bin, k, ai_q, coef, se, n_obs, n_frtk)]

    q5_pre <- cr[ai_q == 5 & k < -1]; q5_post <- cr[ai_q == 5 & k > -1]
    summary_rows[[length(summary_rows) + 1L]] <- data.table(
        sample = "in_bcc_full", age_bin = a,
        max_pre_abs  = if (nrow(q5_pre)  > 0) max(abs(q5_pre$coef)) else NA_real_,
        mean_post_q5 = if (nrow(q5_post) > 0) mean(q5_post$coef)    else NA_real_,
        pre_joint_p  = joint_wald_p(fit, q5_pre$name),
        n_obs = n_a, n_frtk = n_frtk_a)
}

out_coefs   <- rbindlist(coef_rows,    fill = TRUE)
out_summary <- rbindlist(summary_rows, fill = TRUE)
if (nrow(out_coefs)   > 0) setorder(out_coefs,   age_bin, ai_q, k)
if (nrow(out_summary) > 0) setorder(out_summary, age_bin)

atomic_fwrite(out_coefs,   file.path(COEFS, "coef_bcc_event_study.csv"))
atomic_fwrite(out_summary, file.path(COEFS, "coef_bcc_event_study_summary.csv"))
atomic_fwrite(rbindlist(diag_rows),
              file.path(DIAG, "fixest_diag_A3_bcc_event_study.csv"))
cat(sprintf("\nSaved %d rows to coef_bcc_event_study.csv\n", nrow(out_coefs)))
cat("== A3_bcc_event_study.R done ", format(Sys.time()), " ==\n")
close_log()
