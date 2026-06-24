# =============================================================================
# 7_triplediff_fepois.R : triple-diff Poisson (young x post x exposure)
# =============================================================================
# R replacement for Stata 7_triplediff_2age.do, using fixest::fepois.
#
#   log E[y_{f,a,e,t}] = alpha_{f,a} + beta_{f,t} + lambda_{a,t}
#                       + B * Young * POST * Exposure_std + 2-way + e
#
# y = count_all over cells (frtk, age_bin, yrke4, ym). Cells weighted naturally
# by their count (Poisson). Time reference is the BASELINE MONTH k = -1 (Oct
# 2022): each pre-month enters as its own event-time level (kk) interacted with
# exposure and all post months collapse to POST, so B = Young x POST x Exposure
# is measured vs Oct 2022, NOT vs the pooled pre-period (BCC convention,
# matching 6/7b/7c). Exposure enters continuously (z-score); no quintile
# reference involved. Standard errors clustered at foretak.
#
# Inputs:  $DATA/cells_flagged.rds
# Outputs: $output/coefficients/coef_triplediff_fepois.csv
#          $output/log_7_triplediff_fepois.txt
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}

req("fixest"); req("data.table")   # req() comes from 0_settings.R

log_path <- file.path(OUTPUT, "log_7_triplediff_fepois.txt")
log_con  <- file(log_path, open = "wt")
sink(log_con, split = TRUE)
sink(log_con, type = "message")

# on.exit at top level is ignored by R — close sinks explicitly at script end
# and before any early stop() exit.
close_log <- function() {
    try(sink(type = "message"), silent = TRUE)
    try(sink(),                 silent = TRUE)
    try(close(log_con),         silent = TRUE)
}

cat("== 7_triplediff_fepois.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Load + prepare
# -----------------------------------------------------------------------------
d <- load_cells()
cat(sprintf("Loaded %d rows from cells_flagged.rds\n", nrow(d)))

d <- d[in_headline_priv == 1]
cat(sprintf("After in_headline_priv filter: %d rows\n", nrow(d)))

d[, young := as.integer(age_bin == 1)]
# kk = event-time level: each pre-month its own value, all post months -> "POST",
# ref = k = -1 (Oct 2022). The triple-diff B is then measured vs the baseline
# month, not the pooled pre-period. young_exposure_std carries the triple
# interaction so i(kk, young_exposure_std) yields kk::POST:young_exposure_std = B.
d[, kk := fifelse(ym >= YM_EVENT_ZERO, "POST", as.character(ym - YM_EVENT_ZERO))]
d[, young_exposure_std := young * exposure_std]

# Slim down to the columns fepois needs
d <- d[, .(frtk_id, age_bin, ym, count_all, exposure_std, young_exposure_std, kk)]
gc()
cat(sprintf("Slimmed dataset: %d rows, %d unique foretak\n",
            nrow(d), uniqueN(d$frtk_id)))

# -----------------------------------------------------------------------------
# Fit
# -----------------------------------------------------------------------------
t0 <- Sys.time()
fit <- tryCatch(
    fepois(count_all ~ exposure_std + young_exposure_std
                     + i(kk, exposure_std,       ref = "-1")
                     + i(kk, young_exposure_std, ref = "-1") |
                          frtk_id^age_bin + frtk_id^ym + age_bin^ym,
           data = d, cluster = ~frtk_id),
    error = function(e) {
        cat("fepois failed:", conditionMessage(e), "\n"); NULL
    }
)
cat(sprintf("Fit time: %.1f s\n", as.numeric(Sys.time() - t0, units = "secs")))
atomic_fwrite(fixest_diag_row(fit, "7", "triplediff_pooled",
                              nrow(d), uniqueN(d$frtk_id)),
              file.path(DIAG, "fixest_diag_7_triplediff_fepois.csv"))
if (is.null(fit)) {
    # stop(), NEVER quit(): quit() kills the whole R process, which when this
    # script is source()d takes down the master run AND the interactive
    # RStudio session (that was the mysterious "disconnected" in the first
    # real run). stop() still gives Rscript a nonzero exit and lets
    # run_script() record the failure.
    close_log()
    stop("fepois failed -- see log_7_triplediff_fepois.txt")
}

# -----------------------------------------------------------------------------
# Harvest interaction coefficients involving exposure_std
# -----------------------------------------------------------------------------
ct <- as.data.frame(coeftable(fit))
ct$name <- rownames(ct)

# Keep coefficients that involve exposure (young main, the age/time/firm shocks
# are absorbed by the foretak x age + foretak x time + age x time FE structure).
ct <- ct[grepl("exposure_std", ct$name, fixed = TRUE), ]
# Drop the pre-period event-time controls (kk::-2 ... kk::-22 x exposure); keep
# the baseline-level slopes (exposure_std, young_exposure_std) and the POST
# terms: kk::POST:exposure_std = post x exposure, and kk::POST:young_exposure_std
# = the triple-diff B -- both measured vs the baseline month k = -1.
ct <- ct[!grepl("kk::", ct$name, fixed = TRUE) |
             grepl("kk::POST", ct$name, fixed = TRUE), ]

# coeftable column 3 is "z value" for fepois, "t value" for OLS. Some
# fixest versions/settings may label it differently — use position access
# instead of name access to stay robust.
out <- data.table(
    sample    = "headline_priv",
    coef_name = ct$name,
    estimate  = ct[, 1],     # Estimate
    se        = ct[, 2],     # Std. Error
    t_stat    = ct[, 3],     # t / z value
    n_obs     = fit$nobs,
    n_frtk    = uniqueN(d$frtk_id)
)

# Order: main, 2-ways, then 3-way. Determined by number of ":" in the name.
out[, n_colons := lengths(regmatches(coef_name, gregexpr(":", coef_name)))]
setorder(out, n_colons, coef_name)
out[, n_colons := NULL]

atomic_fwrite(out, file.path(COEFS, "coef_triplediff_fepois.csv"))

cat(sprintf("\nSaved %d coefficient rows to coef_triplediff_fepois.csv\n",
            nrow(out)))
print(out)

cat("== 7_triplediff_fepois.R done ", format(Sys.time()), " ==\n")

close_log()
