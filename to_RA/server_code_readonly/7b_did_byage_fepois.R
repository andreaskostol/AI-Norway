# =============================================================================
# 7b_did_byage_fepois.R : Collapsed (static) DiD per decade age group,
#                         firm-FE, for three outcomes
# =============================================================================
# Individual-level (firm-FE) counterpart to the cell-level
# analysis/06_figures/microdata_did_cell.R. The event-study path of script 6
# is collapsed to a single post-October-2022 dummy interacted with the
# Eloundou quintile, estimated separately per age group, for three outcomes.
#
# Spec (per age_bin a, outcome y):
#   employment / new hires (Poisson):
#     log E[y_{f,q,t}] = alpha_{f,q} + beta_{f,t}
#                      + sum_{q in 2..5} delta_q * post_t * 1{ai_q = q}
#   log wage (OLS, weighted by headcount):
#     log wbar_{f,q,t} = alpha_{f,q} + beta_{f,t}
#                      + sum_{q in 2..5} delta_q * post_t * 1{ai_q = q}
#   Time reference is the BASELINE MONTH k = -1 (October 2022), not the pooled
#   pre-period: each pre-month enters as its own event-time level (kk) and all
#   post-ChatGPT months collapse to "POST", so the POST x quintile coefficient
#   is the average post effect vs October 2022 (BCC convention, matching the
#   event study in script 6 and the CA DiD in 7c). Quintile reference: ai_q = 1
#   (lowest exposure -- BCC convention; the winter-construction seasonality in
#   Q1 is absorbed by the firm x month FE and the k = -1 baseline).
#   FE: firm x quintile + firm x month. Cluster: foretak.
#
# Treatment contrasts: Q2, Q3, Q4, Q5 each vs Q1 -> four coefficients per cell.
# Window: the FULL panel (through PERIOD_END; the 2025m4 pre-agentic cutoff
# was dropped along with the cell-level run -- DESIGN_CHOICES.md section 23).
# Sample: in_headline_priv == 1 (private sector).
#
# sum_count_all = total worker-months in the in_headline_priv slice per
# age_bin, computed BEFORE collapsing. 7d_did_byage_cellspec.R reports the
# same quantity from the same slice; equality is the mechanical check that
# the firm spec (here) and the cell spec (7d) see identical data.
#
# Inputs:  $DATA/cells_flagged.rds
# Outputs: $output/coefficients/coef_did_byage_fepois.csv
#            (schema: sample, age_bin, outcome, ai_q, coef, se, p_value,
#                     n_obs, n_frtk, sum_count_all)
#          $output/log_7b_did_byage_fepois.txt
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}

req("fixest"); req("data.table")   # req() comes from 0_settings.R

log_path <- file.path(OUTPUT, "log_7b_did_byage_fepois.txt")
log_con  <- file(log_path, open = "wt")
sink(log_con, split = TRUE)
sink(log_con, type = "message")
close_log <- function() {
    try(sink(type = "message"), silent = TRUE)
    try(sink(),                 silent = TRUE)
    try(close(log_con),         silent = TRUE)
}

cat("== 7b_did_byage_fepois.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Load + restrict (full panel window -- no agentic cutoff)
# -----------------------------------------------------------------------------
d <- load_cells()
cat(sprintf("Loaded %d rows from cells_flagged.rds\n", nrow(d)))

d <- d[in_headline_priv == 1]
d[, post := as.integer(ym > YM_REF)]   # YM_REF = ym(2022,10); Oct 2022 = pre
cat(sprintf("After in_headline_priv: %d rows\n", nrow(d)))

# Multi-granularity sample diagnostics of the slice (age_bin x ym x ai_q x
# post sums + unit counts). 7d computes the same independently from its own
# slice and asserts row-for-row equality -- the identical-sample guard.
atomic_fwrite(sample_diag(d), file.path(DIAG, "sample_diag_7b.csv"))
cat("Wrote diagnostics/sample_diag_7b.csv\n")

# -----------------------------------------------------------------------------
# Coefficient harvesting helper
# -----------------------------------------------------------------------------
parse_did <- function(fit, a, outcome, n_obs, n_frtk, sum_count_all) {
    if (is.null(fit)) return(NULL)
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    m  <- regmatches(ct$name, regexec("kk::POST:ai_q::([0-9]+)", ct$name))
    q  <- vapply(m, function(x) if (length(x) == 2L) as.integer(x[2]) else NA_integer_,
                 integer(1))
    keep <- !is.na(q)
    if (!any(keep)) return(NULL)
    data.table(
        sample = "headline_priv", age_bin = a, outcome = outcome, ai_q = q[keep],
        coef = ct[keep, "Estimate"], se = ct[keep, "Std. Error"],
        p_value = ct[keep, ncol(coeftable(fit))],
        n_obs = n_obs, n_frtk = n_frtk, sum_count_all = sum_count_all
    )
}

# -----------------------------------------------------------------------------
# Per age_bin x outcome
# -----------------------------------------------------------------------------
coef_rows <- list()
diag_rows <- list()
for (a in 1:N_AGE_BINS) {
    da <- d[age_bin == a]
    if (nrow(da) == 0) { cat(sprintf("\n--- age_bin %d: no rows, skip ---\n", a)); next }
    cat(sprintf("\n--- age_bin = %d ---\n", a))

    # Cross-check quantity: total worker-months in this slice BEFORE any
    # collapsing. Must equal the same number in 7d's restricted variant.
    sum_ct <- da[, sum(count_all)]
    cat(sprintf("  sum_count_all = %s (cross-check vs 7d)\n", fmt_int(sum_ct)))

    # Collapse to (frtk, ai_q, ym) for the count outcomes. kk = event-time
    # level with each pre-month its own value and post collapsed to "POST",
    # ref = k = -1 (Oct 2022); k >= 0 <=> ym >= YM_EVENT_ZERO (Nov 2022).
    emp <- da[, .(y = sum(count_all)), by = .(frtk_id, ai_q, ym, post)]
    nh  <- da[, .(y = sum(count_new)), by = .(frtk_id, ai_q, ym, post)]
    for (dt in list(emp, nh)) {
        dt[, ai_q := factor(ai_q, levels = 1:5)]
        dt[, kk := fifelse(ym >= YM_EVENT_ZERO, "POST",
                           as.character(ym - YM_EVENT_ZERO))]
    }

    n_obs <- nrow(emp); n_frtk <- uniqueN(emp$frtk_id)

    fit_emp <- tryCatch(
        fepois(y ~ i(kk, ai_q, ref = "-1", ref2 = "1") | frtk_id^ai_q + frtk_id^ym,
               data = emp, cluster = ~frtk_id),
        error = function(e) { cat("  emp fepois failed:", conditionMessage(e), "\n"); NULL })
    coef_rows[[length(coef_rows) + 1L]] <-
        parse_did(fit_emp, a, "employment", n_obs, n_frtk, sum_ct)
    diag_rows[[length(diag_rows) + 1L]] <-
        fixest_diag_row(fit_emp, "7b", sprintf("age%d_employment", a), n_obs, n_frtk)

    fit_nh <- tryCatch(
        fepois(y ~ i(kk, ai_q, ref = "-1", ref2 = "1") | frtk_id^ai_q + frtk_id^ym,
               data = nh, cluster = ~frtk_id),
        error = function(e) { cat("  new_hires fepois failed:", conditionMessage(e), "\n"); NULL })
    coef_rows[[length(coef_rows) + 1L]] <-
        parse_did(fit_nh, a, "new_hires", nrow(nh), uniqueN(nh$frtk_id), sum_ct)
    diag_rows[[length(diag_rows) + 1L]] <-
        fixest_diag_row(fit_nh, "7b", sprintf("age%d_new_hires", a),
                        nrow(nh), uniqueN(nh$frtk_id))

    # Log wage: employment-weighted mean cell wage over non-missing cells,
    # collapsed to (frtk, ai_q, ym); weighted OLS (unbalanced).
    dw <- da[!is.na(m_wage_all) & m_wage_all > 0 & count_all > 0]
    wage <- dw[, .(wbar = weighted.mean(m_wage_all, count_all), w = sum(count_all)),
               by = .(frtk_id, ai_q, ym, post)]
    wage[, ai_q := factor(ai_q, levels = 1:5)]
    wage[, kk := fifelse(ym >= YM_EVENT_ZERO, "POST",
                         as.character(ym - YM_EVENT_ZERO))]
    wage[, lwage := log(wbar)]
    fit_wage <- tryCatch(
        feols(lwage ~ i(kk, ai_q, ref = "-1", ref2 = "1") | frtk_id^ai_q + frtk_id^ym,
              data = wage, weights = ~w, cluster = ~frtk_id),
        error = function(e) { cat("  wage feols failed:", conditionMessage(e), "\n"); NULL })
    coef_rows[[length(coef_rows) + 1L]] <-
        parse_did(fit_wage, a, "log_wage", nrow(wage), uniqueN(wage$frtk_id), sum_ct)
    diag_rows[[length(diag_rows) + 1L]] <-
        fixest_diag_row(fit_wage, "7b", sprintf("age%d_log_wage", a),
                        nrow(wage), uniqueN(wage$frtk_id))

    cat(sprintf("  emp n=%d, new_hires n=%d, wage n=%d, n_frtk=%d\n",
                n_obs, nrow(nh), nrow(wage), n_frtk))
}

out <- rbindlist(Filter(Negate(is.null), coef_rows), fill = TRUE)
if (nrow(out) > 0) setorder(out, age_bin, outcome, ai_q)
atomic_fwrite(out, file.path(COEFS, "coef_did_byage_fepois.csv"))
cat(sprintf("\nSaved %d rows to coef_did_byage_fepois.csv\n", nrow(out)))

atomic_fwrite(rbindlist(diag_rows),
              file.path(DIAG, "fixest_diag_7b_did_byage_fepois.csv"))
cat("Wrote diagnostics/fixest_diag_7b_did_byage_fepois.csv\n")
cat("== 7b_did_byage_fepois.R done ", format(Sys.time()), " ==\n")
close_log()
