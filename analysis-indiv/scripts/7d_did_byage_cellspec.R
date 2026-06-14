# =============================================================================
# 7d_did_byage_cellspec.R : the CELL-LEVEL DiD specification run on the
#                           secure-zone data, per decade age group
# =============================================================================
# Together with 7b_did_byage_fepois.R this is the specification-comparison
# module. The published cell analysis (analysis/06_figures/microdata_did_cell.R,
# on microdata.no aggregates) and the firm-FE individual analysis (7b) differ
# in three ways at once: data source, sample restriction, and specification.
# This script isolates them (DESIGN_CHOICES.md section 22):
#
#   7b  vs 7d variant "restricted"        -> SPECIFICATION (firm x quintile +
#       firm x month FE, cluster foretak   vs  yrke4 + month FE, cluster yrke4)
#       on IDENTICAL data (in_headline_priv: private, active-firm >= 20,
#       balanced). Equality of sum_count_all per age_bin across the two CSVs
#       is the mechanical identical-sample check.
#   7d "restricted" vs 7d "unrestricted_priv" -> the >= FRTK_MIN_ACTIVE
#       active-firm restriction + balancing (occ_unrestricted_agg.rds is built
#       from the same monthly cells BEFORE the activity filter).
#   7d "unrestricted_priv" vs coef_microdata_did_cell.csv -> DATA SOURCE
#       (register vs microdata.no; residual definitional gap: spells without
#       a foretak ID are dropped here but counted by microdata.no).
#
# Spec per (variant, age_bin, outcome) -- lifted from microdata_did_cell.R:
#   employment / new hires (Poisson, balanced yrke4 x ym grid, zero-filled):
#     log E[y_{j,t}] = alpha_j + beta_t + sum_{q != 3} delta_q * post_t * 1{ai_q(j)=q}
#   log wage (OLS, weighted by headcount, unbalanced):
#     log wbar_{j,t} = alpha_j + beta_t + sum_{q != 3} delta_q * post_t * 1{ai_q(j)=q}
#   j = 4-digit STYRK-08. Time reference is the baseline month k = -1 (Oct
#   2022): each pre-month is its own event-time level (kk) and all post months
#   collapse to "POST", so the POST x quintile coefficient is the average post
#   effect vs Oct 2022 -- NOT vs the pooled pre-period (same convention as 7b,
#   script 6 and 7c). Quintile reference ai_q = 1 (lowest exposure, BCC
#   convention), matching 7b. Cluster: yrke4. Window: full panel (no agentic
#   cutoff), matching 7b.
#
# Inputs:  $DATA/cells_flagged.rds         (variant "restricted")
#          $DATA/occ_unrestricted_agg.rds  (variant "unrestricted_priv")
#          $DIAG/sample_diag_7b.csv        (written by 7b; comparison input)
# Outputs: $output/coefficients/coef_did_byage_cellspec.csv
#            (schema: sample, variant, age_bin, outcome, ai_q, coef, se,
#                     p_value, n_obs, n_occ, sum_count_all, n_clusters,
#                     sum_count_all_model_sample, convergence_status)
#          $DIAG/sample_diag_7d_restricted.csv
#          $DIAG/7b_7d_sample_comparison.csv   (STOPS the run on mismatch)
#          $DIAG/fixest_diag_7d_did_byage_cellspec.csv
#          $output/log_7d_did_byage_cellspec.txt
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("fixest"); req("data.table")   # req() comes from 0_settings.R

open_log("7d_did_byage_cellspec")
cat("== 7d_did_byage_cellspec.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Helpers (kept structurally identical to microdata_did_cell.R so the spec
# stays auditable against the published cell-level script)
# -----------------------------------------------------------------------------

# Hard-lock the quintile factor: any value outside 1:5 (or an NA produced by
# a bad join) must stop the run, never silently become a dropped level.
as_ai_q_factor <- function(x) {
    out <- factor(as.integer(as.character(x)), levels = 1:5)
    stopifnot(!anyNA(out))
    out
}

# Balance the count panel: every (yrke4 x ym) combination present within the
# slice; missing -> 0. ai_q attached from the occupation lookup (constant
# within yrke4 -- asserted by the caller). NOT used for the wage OLS.
balance_counts <- function(sub, value_col) {
    grid <- CJ(yrke4 = unique(sub$yrke4), ym = sort(unique(sub$ym)))
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4", all.x = TRUE)
    # kk = event-time level with each pre-month its own value, post collapsed
    # to "POST", ref = k = -1 (Oct 2022): baseline-month reference, not pooled
    # pre-period. k >= 0 <=> ym >= YM_EVENT_ZERO (Nov 2022).
    grid[, kk := fifelse(ym >= YM_EVENT_ZERO, "POST",
                         as.character(ym - YM_EVENT_ZERO))]
    src  <- sub[, .(val = get(value_col)), by = .(yrke4, ym)]
    out  <- merge(grid, src, by = c("yrke4", "ym"), all.x = TRUE)
    out[is.na(val), val := 0]
    out[, ai_q := as_ai_q_factor(ai_q)]
    out
}

fit_pois <- function(dt) {
    tryCatch(
        fepois(val ~ i(kk, ai_q, ref = "-1", ref2 = "1") | yrke4 + ym,
               data = dt, cluster = ~yrke4),
        error = function(e) { cat("  fepois failed:", conditionMessage(e), "\n"); NULL })
}

parse_did <- function(fit, sample, variant, a, outcome, n_obs, n_occ,
                      sum_count_all, diag) {
    if (is.null(fit)) return(NULL)
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    m  <- regmatches(ct$name, regexec("kk::POST:ai_q::([0-9]+)", ct$name))
    q  <- vapply(m, function(x) if (length(x) == 2L) as.integer(x[2]) else NA_integer_,
                 integer(1))
    keep <- !is.na(q)
    if (!any(keep)) return(NULL)
    data.table(
        sample = sample, variant = variant, age_bin = a, outcome = outcome,
        ai_q = q[keep],
        coef = ct[keep, "Estimate"], se = ct[keep, "Std. Error"],
        p_value = ct[keep, ncol(coeftable(fit))],
        n_obs = n_obs, n_occ = n_occ, sum_count_all = sum_count_all,
        n_clusters = diag$n_clusters_input,
        sum_count_all_model_sample = diag$y_sum_model_sample,
        convergence_status = diag$convergence
    )
}

# Run the three outcomes for one age slice already standardized to columns
# (yrke4, ai_q, ym, count, count_new, wbar, w). wbar = employment-weighted
# mean monthly wage per (yrke4, ym); w = headcount behind it.
run_age_slice <- function(slice, wage_panel, sample, variant, a, coef_rows) {
    stopifnot(slice[, uniqueN(ai_q), by = yrke4][, all(V1 == 1)])
    sum_ct <- slice[, sum(count)]
    cat(sprintf("\n--- variant = %s, age_bin = %d: sum_count_all = %s ---\n",
                variant, a, fmt_int(sum_ct)))

    # Employment (Poisson, balanced)
    bc <- balance_counts(slice, "count")
    fit_emp <- fit_pois(bc)
    dg <- fixest_diag_row(fit_emp, "7d", sprintf("%s_age%d_employment", variant, a),
                          nrow(bc), uniqueN(bc$yrke4))
    diag_rows[[length(diag_rows) + 1L]] <<- dg
    coef_rows[[length(coef_rows) + 1L]] <-
        parse_did(fit_emp, sample, variant, a, "employment",
                  nrow(bc), uniqueN(bc$yrke4), sum_ct, dg)

    # New hires (Poisson, balanced)
    bn <- balance_counts(slice, "count_new")
    fit_nh <- fit_pois(bn)
    dg <- fixest_diag_row(fit_nh, "7d", sprintf("%s_age%d_new_hires", variant, a),
                          nrow(bn), uniqueN(bn$yrke4))
    diag_rows[[length(diag_rows) + 1L]] <<- dg
    coef_rows[[length(coef_rows) + 1L]] <-
        parse_did(fit_nh, sample, variant, a, "new_hires",
                  nrow(bn), uniqueN(bn$yrke4), sum_ct, dg)

    # Log wage (weighted OLS, unbalanced)
    wage_panel[, ai_q := as_ai_q_factor(ai_q)]
    wage_panel[, kk := fifelse(ym >= YM_EVENT_ZERO, "POST",
                               as.character(ym - YM_EVENT_ZERO))]
    wage_panel[, lwage := log(wbar)]
    fit_wage <- tryCatch(
        feols(lwage ~ i(kk, ai_q, ref = "-1", ref2 = "1") | yrke4 + ym,
              data = wage_panel, weights = ~w, cluster = ~yrke4),
        error = function(e) { cat("  wage feols failed:", conditionMessage(e), "\n"); NULL })
    dg <- fixest_diag_row(fit_wage, "7d", sprintf("%s_age%d_log_wage", variant, a),
                          nrow(wage_panel), uniqueN(wage_panel$yrke4))
    diag_rows[[length(diag_rows) + 1L]] <<- dg
    coef_rows[[length(coef_rows) + 1L]] <-
        parse_did(fit_wage, sample, variant, a, "log_wage",
                  nrow(wage_panel), uniqueN(wage_panel$yrke4), sum_ct, dg)

    cat(sprintf("  emp n=%d, new_hires n=%d, wage n=%d, n_occ=%d\n",
                nrow(bc), nrow(bn), nrow(wage_panel), uniqueN(bc$yrke4)))
    coef_rows
}

coef_rows <- list()
diag_rows <- list()

# -----------------------------------------------------------------------------
# Variant "restricted": the 7b sample (in_headline_priv -- private sector,
# active-firm >= FRTK_MIN_ACTIVE, balanced panel), aggregated over foretak
# to (yrke4, ym) per age_bin. Synthetic zero rows add nothing to the sums;
# they only matter through the balancing, which balance_counts() redoes at
# the (yrke4, ym) level exactly as microdata_did_cell.R does.
# -----------------------------------------------------------------------------
d <- load_cells()
d <- d[in_headline_priv == 1L]
cat(sprintf("restricted: %s cell rows after in_headline_priv\n", fmt_int(nrow(d))))

# Identical-sample guard vs 7b: compute the SAME multi-granularity sample
# diagnostics (age_bin x ym x ai_q x post sums + unit counts) independently
# from this script's slice, and assert row-for-row equality with what 7b
# wrote. Equal age_bin totals alone would not catch a wrong post dummy, a
# wrong quintile join or a month missing from one side.
sd_7d <- sample_diag(d)
atomic_fwrite(sd_7d, file.path(DIAG, "sample_diag_7d_restricted.csv"))
sd_7b_path <- file.path(DIAG, "sample_diag_7b.csv")
if (file.exists(sd_7b_path)) {
    sd_7b <- fread(sd_7b_path)
    cmp <- merge(sd_7b, sd_7d, by = c("metric", "age_bin", "ym", "ai_q", "post"),
                 suffixes = c("_7b", "_7d"), all = TRUE)
    cmp[, equal := !is.na(value_7b) & !is.na(value_7d) & value_7b == value_7d]
    atomic_fwrite(cmp, file.path(DIAG, "7b_7d_sample_comparison.csv"))
    n_bad <- cmp[equal == FALSE, .N]
    cat(sprintf("7b/7d sample comparison: %d of %d diagnostic rows differ\n",
                n_bad, nrow(cmp)))
    if (n_bad > 0) {
        print(head(cmp[equal == FALSE], 20))
        stop("7b and 7d do not see the same in_headline_priv sample -- ",
             "fix before using the comparison (diagnostics/7b_7d_sample_comparison.csv).")
    }
} else {
    cat("NOTE: sample_diag_7b.csv not found (7b not run yet?); comparison skipped.\n")
}

for (a in 1:N_AGE_BINS) {
    da <- d[age_bin == a]
    if (nrow(da) == 0) { cat(sprintf("\n--- restricted age_bin %d: no rows, skip ---\n", a)); next }

    slice <- da[, .(count     = sum(count_all),
                    count_new = sum(count_new),
                    ai_q      = ai_q[1L]), by = .(yrke4, ym)]

    # Wage: employment-weighted mean over cells with valid wage (same drop
    # rule as 7b), collapsed to (yrke4, ym).
    dw <- da[count_all > 0 & !is.na(m_wage_all) & m_wage_all > 0]
    wage_panel <- dw[, .(wbar = weighted.mean(m_wage_all, count_all),
                         w    = sum(count_all),
                         ai_q = ai_q[1L]), by = .(yrke4, ym)]

    coef_rows <- run_age_slice(slice, wage_panel, "headline_priv", "restricted",
                               a, coef_rows)
}
rm(d); invisible(gc(verbose = FALSE))

# -----------------------------------------------------------------------------
# Variant "unrestricted_priv": private-sector occupation aggregate built in
# script 4 BEFORE the activity filter -- no firm-size restriction, no
# balancing at the firm level. wage_sum / count is the exact worker-level
# mean wage per (yrke4, age_bin, ym).
# -----------------------------------------------------------------------------
occ <- readRDS(file.path(DATA, "occ_unrestricted_agg.rds"))
setDT(occ)
occ <- occ[sekt == 3L]
cat(sprintf("\nunrestricted_priv: %s aggregate rows (private)\n", fmt_int(nrow(occ))))

for (a in 1:N_AGE_BINS) {
    ua <- occ[age_bin == a]
    if (nrow(ua) == 0) { cat(sprintf("\n--- unrestricted age_bin %d: no rows, skip ---\n", a)); next }

    slice <- ua[, .(yrke4, ym, ai_q, count, count_new)]

    wage_panel <- ua[count > 0 & wage_sum > 0,
                     .(yrke4, ym, ai_q, wbar = wage_sum / count, w = count)]

    coef_rows <- run_age_slice(slice, wage_panel, "all_priv", "unrestricted_priv",
                               a, coef_rows)
}

# -----------------------------------------------------------------------------
# Save
# -----------------------------------------------------------------------------
out <- rbindlist(Filter(Negate(is.null), coef_rows), fill = TRUE)
if (nrow(out) > 0) setorder(out, variant, age_bin, outcome, ai_q)
atomic_fwrite(out, file.path(COEFS, "coef_did_byage_cellspec.csv"))
cat(sprintf("\nSaved %d rows to coef_did_byage_cellspec.csv\n", nrow(out)))

atomic_fwrite(rbindlist(diag_rows),
              file.path(DIAG, "fixest_diag_7d_did_byage_cellspec.csv"))
cat("Wrote diagnostics/fixest_diag_7d_did_byage_cellspec.csv\n")

# Cross-check summary: sum_count_all per (variant, age_bin). The "restricted"
# column must equal sum_count_all in coef_did_byage_fepois.csv (7b) per
# age_bin -- check after every run.
if (nrow(out) > 0) {
    cat("\nsum_count_all per (variant, age_bin) -- compare 'restricted' to 7b:\n")
    print(unique(out[, .(variant, age_bin, sum_count_all)]))
}

cat("== 7d_did_byage_cellspec.R done ", format(Sys.time()), " ==\n")
close_log()
