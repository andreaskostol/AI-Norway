# =============================================================================
# 6d_event_study_continuous_share_feols.R : event-study, continuous exposure
#                                            x young triple, linear OLS on
#                                            per-capita rate
# =============================================================================
# R replacement for Stata 6d_event_study_continuous_share.do, using
# fixest::feols. Event-time analogue of 8c (triple-diff with continuous
# exposure x young): same FE, same sample, same outcome, but with event-time
# bin dummies replacing the binary post indicator.
#
#   rate_{f,a,t} = alpha_{f,a} + beta_{f,t} + lambda_{a,t}
#                + sum_{k != ref} gamma_k * 1{bin(t)=k} * young * exposure_std
#                + (necessary 2-way interactions) + e
#
# rate = count_all / N_{age_bin, ym}. Cells weighted by population, clustered
# at foretak. young = 1{age_bin == 1}. Event-time bins are BIN_W = 2 months
# wide (~28-30 levels) to match the Stata version. Reference bin = floor(-1 /
# BIN_W) = -1, covers months [-2, -1] (October 2022 is k = -1).
#
# Output: each fitted bin's reported k is the LAST month of the bin so the
# reference (bin -1) saves as k = -1 in the CSV - matching 6c's monthly
# k and the Python plotting convention.
#
# Inputs:  $DATA/cells_flagged.rds
#          $DATA/population_by_agebin_ym.rds  (built by 5b_population.R)
# Outputs: $output/coefficients/coef_event_study_continuous_share.csv
#          $output/coefficients/coef_event_study_continuous_share_summary.csv
#          $output/log_6d_event_study_continuous_share_feols.txt
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}

req("fixest"); req("data.table")   # req() comes from 0_settings.R

log_path <- file.path(OUTPUT, "log_6d_event_study_continuous_share_feols.txt")
log_con  <- file(log_path, open = "wt")
sink(log_con, split = TRUE)
sink(log_con, type = "message")
close_log <- function() {
    try(sink(type = "message"), silent = TRUE)
    try(sink(),                 silent = TRUE)
    try(close(log_con),         silent = TRUE)
}

cat("== 6d_event_study_continuous_share_feols.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Binning parameters
# -----------------------------------------------------------------------------
BIN_W   <- 2L                       # 2-month bins
BIN_REF <- as.integer(floor(-1 / BIN_W))  # = -1, the bin containing month -1
BIN_MIN <- as.integer(floor(KMIN / BIN_W))
BIN_MAX <- as.integer(floor(KMAX / BIN_W))

# Helper: reported k for a fitted bin = LAST month of that bin.
#   kbin = floor(kshift / BIN_W). The bin spans months kbin*BIN_W .. (kbin+1)*BIN_W - 1.
#   So the last month of bin K is (K+1) * BIN_W - 1. This makes the reference
#   bin (-1 with BIN_W=2) report as k = -1, matching 6c's monthly convention.
reported_k <- function(kbin) (kbin + 1L) * BIN_W - 1L

# -----------------------------------------------------------------------------
# Joint Wald test helper (copied from 6_event_study_fepois.R for consistency)
# -----------------------------------------------------------------------------
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
# Load cells + population
# -----------------------------------------------------------------------------
d <- load_cells()
cat(sprintf("Loaded %d rows from cells_flagged.rds\n", nrow(d)))

d <- d[in_headline_priv == 1]
cat(sprintf("After in_headline_priv filter: %d rows\n", nrow(d)))

# Slim to columns this regression needs. Cell-level (frtk x sekt x age x yrke4
# x ym) - we do NOT aggregate; exposure_std varies by yrke4 within (frtk, age,
# ym), and that variation identifies the kbin x young x exposure interaction
# after the firm x age, firm x ym, age x ym FE.
d <- d[, .(frtk_id, age_bin, ym, count_all, exposure_std)]
gc()

pop <- load_population()[, .(age_bin, ym, population)]

d  [, age_bin := as.integer(age_bin)]
d  [, ym      := as.integer(ym)]
pop[, age_bin := as.integer(age_bin)]
pop[, ym      := as.integer(ym)]

d <- merge(d, pop, by = c("age_bin", "ym"), all.x = TRUE)
n_missing <- d[, sum(is.na(population))]
if (n_missing > 0) {
    cat(sprintf("  WARNING: %d rows missing population; dropping.\n", n_missing))
    d <- d[!is.na(population)]
}
d[, rate := count_all / population]
d[, count_all := NULL]
gc()

d[, young  := as.integer(age_bin == 1)]
d[, kshift := as.integer(ym - YM_EVENT_ZERO)]
d[, kbin   := as.integer(floor(kshift / BIN_W))]
d <- d[kbin >= BIN_MIN & kbin <= BIN_MAX]
cat(sprintf("Event-time bin window [%d, %d]: %d rows\n", BIN_MIN, BIN_MAX, nrow(d)))

# Derived 2-way young x exposure_std product. fixest i() can interact a factor
# with a single continuous variable, not with a product expression, so we
# build the product and pass it as the second arg of i() to obtain the
# triple-interaction coefficients.
d[, ye := young * exposure_std]

# -----------------------------------------------------------------------------
# Fit
# -----------------------------------------------------------------------------
# Spec: kbin ## c.young ## c.exposure_std with kbin reference = BIN_REF (= -1).
# Expansion (matching Stata's ## triple-interaction):
#   main:  i(kbin, ref=BIN_REF), young, exposure_std
#   2-way: i(kbin, young),  i(kbin, exposure_std),  young:exposure_std (= ye)
#   3-way: i(kbin, ye)                                       <- TARGET
# Several lower-order terms are absorbed by the FE (kbin main by frtk^ym,
# kbin:young by age^ym, etc.) - fixest drops them silently.
n_obs  <- nrow(d)
n_frtk <- uniqueN(d$frtk_id)
cat(sprintf("  n_obs=%d  n_frtk=%d\n", n_obs, n_frtk))

t0 <- Sys.time()
fit <- tryCatch(
    feols(rate ~
              young + exposure_std + ye +
              i(kbin, ref = BIN_REF) +
              i(kbin, young,        ref = BIN_REF) +
              i(kbin, exposure_std, ref = BIN_REF) +
              i(kbin, ye,           ref = BIN_REF) |
              frtk_id^age_bin + frtk_id^ym + age_bin^ym,
          data = d, weights = ~population, cluster = ~frtk_id),
    error = function(e) {
        cat("  feols failed:", conditionMessage(e), "\n"); NULL
    }
)
cat(sprintf("  fit time: %.1f s\n",
            as.numeric(Sys.time() - t0, units = "secs")))
atomic_fwrite(fixest_diag_row(fit, "6d", "continuous_share_es_pooled",
                              n_obs, n_frtk),
              file.path(DIAG, "fixest_diag_6d_event_study_continuous_share.csv"))
if (is.null(fit)) {
    # This script has exactly one fit; a failed fit means no results at all.
    # Fail loudly (status "failed" in the manifest) instead of finishing "ok"
    # with empty CSVs, as happened in the first real run.
    close_log()
    stop("6d feols failed -- see log_6d_event_study_continuous_share_feols.txt")
}

# -----------------------------------------------------------------------------
# Harvest 3-way coefs: names of form "kbin::N:ye"
# -----------------------------------------------------------------------------
es_rows  <- data.table(sample = character(0), k = integer(0),
                       coef = numeric(0), se = numeric(0),
                       n_obs = integer(0), n_frtk = integer(0))
sum_rows <- data.table(sample = character(0), max_pre_abs = numeric(0),
                       mean_post = numeric(0), pre_joint_p = numeric(0),
                       n_obs = integer(0), n_frtk = integer(0))

if (!is.null(fit)) {
    ct <- as.data.frame(coeftable(fit))
    ct$name <- rownames(ct)
    cat("  Sample of triple-interaction coef names:\n")
    triple_idx <- grepl("kbin::-?[0-9]+:ye$", ct$name)
    cat(paste("    ", head(ct$name[triple_idx], 5), collapse = "\n"), "\n")

    m <- regmatches(ct$name, regexec("^kbin::(-?[0-9]+):ye$", ct$name))
    kbin_vals <- vapply(m, function(x) if (length(x) == 2L) as.integer(x[2]) else NA_integer_,
                        integer(1))
    keep <- !is.na(kbin_vals)
    ct_kept <- ct[keep, , drop = FALSE]
    kbin_kept <- kbin_vals[keep]

    if (nrow(ct_kept) > 0) {
        es_rows <- data.table(
            sample = "headline_priv",
            k      = reported_k(kbin_kept),
            coef   = ct_kept[, "Estimate"],
            se     = ct_kept[, "Std. Error"],
            n_obs  = n_obs,
            n_frtk = n_frtk,
            name   = ct_kept$name
        )
        setorder(es_rows, k)

        # Pre-period bins: kbin < BIN_REF. Post: kbin > BIN_REF.
        pre_dt   <- es_rows[k < reported_k(BIN_REF)]   # k < -1
        post_dt  <- es_rows[k > reported_k(BIN_REF)]   # k > -1
        max_pre  <- if (nrow(pre_dt)  > 0) max(abs(pre_dt$coef)) else NA_real_
        mean_pst <- if (nrow(post_dt) > 0) mean(post_dt$coef)    else NA_real_

        pre_joint_p <- joint_wald_p(fit, pre_dt$name)

        sum_rows <- data.table(
            sample      = "headline_priv",
            max_pre_abs = max_pre,
            mean_post   = mean_pst,
            pre_joint_p = pre_joint_p,
            n_obs       = n_obs,
            n_frtk      = n_frtk
        )

        cat(sprintf("  harvested %d triple-interaction coefs\n", nrow(es_rows)))
        cat(sprintf("  max|pre|=%s  mean_post=%s  pre p=%s\n",
                    format(max_pre,  digits = 4),
                    format(mean_pst, digits = 4),
                    format(pre_joint_p, digits = 4)))

        es_rows[, name := NULL]
    } else {
        cat("  WARNING: no triple-interaction coefs matched the expected name pattern.\n")
    }
}

# -----------------------------------------------------------------------------
# Save
# -----------------------------------------------------------------------------
atomic_fwrite(es_rows,  file.path(COEFS, "coef_event_study_continuous_share.csv"))
atomic_fwrite(sum_rows, file.path(COEFS, "coef_event_study_continuous_share_summary.csv"))

cat(sprintf("\nSaved %d rows to coef_event_study_continuous_share.csv\n", nrow(es_rows)))
cat(sprintf("Saved %d rows to coef_event_study_continuous_share_summary.csv\n", nrow(sum_rows)))
cat("== 6d_event_study_continuous_share_feols.R done ", format(Sys.time()), " ==\n")

close_log()
