# =============================================================================
# 6f_event_study_cellspec.R : cell-spec event study (yrke4 + month FE) per age
# =============================================================================
# Event-study counterpart to 7d_did_byage_cellspec.R: instead of collapsing the
# post period to a single POST dummy, estimate the full event-time path
# gamma_{q,k}, so the cell-spec has a dynamic figure alongside the firm-FE event
# study (script 6) and the published microdata.no cell event study
# (analysis/06_figures/microdata_es_decade_q1_full*.R). Together those four give
# the event-study version of the 7b/7d/cell DiD comparison (DESIGN_CHOICES.md
# section 22), all on the BCC reference (Q1, k = -1).
#
# Spec (per variant, age_bin, outcome), mirroring microdata_did_cell.R's FE:
#   employment / new hires (Poisson, balanced yrke4 x ym grid, zero-filled):
#     log E[y_{j,t}] = alpha_j + beta_t
#                    + sum_{q != 1, k != -1} gamma_{q,k} 1{ai_q(j)=q} 1{t-t0=k}
#   log wage (OLS, weighted by headcount, unbalanced): same RHS.
#   j = yrke4; reference q = 1 (lowest exposure, BCC), k = -1 (Oct 2022).
#   Event window k in [KMIN, KMAX]. Cluster: yrke4.
#
# Two register variants, built EXACTLY as in 7d (same slices, so the restricted
# event study sits on the same sample as 7b/7d):
#   restricted        : in_headline_priv, aggregated over foretak to (yrke4, ym)
#   unrestricted_priv : occ_unrestricted_agg.rds (sekt == 3), pre-activity-filter
#
# Inputs:  $DATA/cells_flagged.rds, $DATA/occ_unrestricted_agg.rds
# Outputs: $output/coefficients/coef_es_byage_cellspec.csv
#            (sample, variant, age_bin, outcome, ai_q, k, coef, se, n_obs, n_occ)
#          $output/coefficients/coef_es_byage_cellspec_summary.csv
#            (sample, variant, age_bin, outcome, max_pre_abs, mean_post_q5,
#             pre_joint_p, n_obs, n_occ)
#          $output/diagnostics/fixest_diag_6f_event_study_cellspec.csv
#          $output/log_6f_event_study_cellspec.txt
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}

req("fixest"); req("data.table")   # req() comes from 0_settings.R

open_log("6f_event_study_cellspec")
cat("== 6f_event_study_cellspec.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Helpers (quintile guard from 7d; (k, q) parse + joint pre-trend test from 6)
# -----------------------------------------------------------------------------
as_ai_q_factor <- function(x) {
    out <- factor(as.integer(as.character(x)), levels = 1:5)
    stopifnot(!anyNA(out))
    out
}

parse_kq <- function(nm) {
    if (length(nm) == 0) return(data.table(k = integer(0), ai_q = integer(0)))
    m <- regmatches(nm, regexec("kshift::(-?[0-9]+):ai_q::([0-9]+)", nm))
    out <- do.call(rbind, lapply(m, function(x)
        if (length(x) == 3) c(as.integer(x[2]), as.integer(x[3]))
        else c(NA_integer_, NA_integer_)))
    colnames(out) <- c("k", "ai_q")
    as.data.table(out)
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

# Balance the count panel on (yrke4 x ym) within a slice, zero-fill, attach the
# event-time index and trim to [KMIN, KMAX]. Same balancing as 7d/microdata.
balance_counts <- function(sub, value_col) {
    grid <- CJ(yrke4 = unique(sub$yrke4), ym = sort(unique(sub$ym)))
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4", all.x = TRUE)
    src  <- sub[, .(val = get(value_col)), by = .(yrke4, ym)]
    out  <- merge(grid, src, by = c("yrke4", "ym"), all.x = TRUE)
    out[is.na(val), val := 0]
    out[, ai_q   := as_ai_q_factor(ai_q)]
    out[, kshift := as.integer(ym - YM_EVENT_ZERO)]
    out[kshift >= KMIN & kshift <= KMAX]
}

coef_rows    <- list()
summary_rows <- list()
diag_rows    <- list()

# Harvest (k, q) coefficients + the Q5 pre-trend summary from one fit.
harvest_es <- function(fit, sample, variant, a, outcome, n_obs, n_occ) {
    diag_rows[[length(diag_rows) + 1L]] <<-
        fixest_diag_row(fit, "6f", sprintf("%s_age%d_%s", variant, a, outcome),
                        n_obs, n_occ)
    if (is.null(fit)) return(invisible(NULL))
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    kq <- parse_kq(ct$name); ct$k <- kq$k; ct$ai_q <- kq$ai_q
    ct <- ct[!is.na(ct$k), ]
    if (nrow(ct) == 0) return(invisible(NULL))
    cr <- data.table(sample = sample, variant = variant, age_bin = a,
                     outcome = outcome, ai_q = ct$ai_q, k = ct$k,
                     coef = ct[, "Estimate"], se = ct[, "Std. Error"],
                     n_obs = n_obs, n_occ = n_occ, name = ct$name)
    coef_rows[[length(coef_rows) + 1L]] <<-
        cr[, .(sample, variant, age_bin, outcome, ai_q, k, coef, se, n_obs, n_occ)]

    q5_pre  <- cr[ai_q == 5 & k < -1]
    q5_post <- cr[ai_q == 5 & k > -1]
    summary_rows[[length(summary_rows) + 1L]] <<- data.table(
        sample = sample, variant = variant, age_bin = a, outcome = outcome,
        max_pre_abs  = if (nrow(q5_pre)  > 0) max(abs(q5_pre$coef)) else NA_real_,
        mean_post_q5 = if (nrow(q5_post) > 0) mean(q5_post$coef)    else NA_real_,
        pre_joint_p  = joint_wald_p(fit, q5_pre$name),
        n_obs = n_obs, n_occ = n_occ)
    invisible(NULL)
}

# Run the three outcomes for one age slice (columns yrke4, ai_q, ym, count,
# count_new + a wage_panel with wbar/w), mirroring 7d's run_age_slice.
run_age_slice <- function(slice, wage_panel, sample, variant, a) {
    cat(sprintf("\n--- variant = %s, age_bin = %d ---\n", variant, a))

    bc <- balance_counts(slice, "count")
    fit_emp <- tryCatch(
        fepois(val ~ i(kshift, ai_q, ref = -1, ref2 = "1") | yrke4 + ym,
               data = bc, cluster = ~yrke4),
        error = function(e) { cat("  emp fepois failed:", conditionMessage(e), "\n"); NULL })
    harvest_es(fit_emp, sample, variant, a, "employment", nrow(bc), uniqueN(bc$yrke4))

    bn <- balance_counts(slice, "count_new")
    fit_nh <- tryCatch(
        fepois(val ~ i(kshift, ai_q, ref = -1, ref2 = "1") | yrke4 + ym,
               data = bn, cluster = ~yrke4),
        error = function(e) { cat("  new_hires fepois failed:", conditionMessage(e), "\n"); NULL })
    harvest_es(fit_nh, sample, variant, a, "new_hires", nrow(bn), uniqueN(bn$yrke4))

    wp <- copy(wage_panel)
    wp[, ai_q   := as_ai_q_factor(ai_q)]
    wp[, kshift := as.integer(ym - YM_EVENT_ZERO)]
    wp <- wp[kshift >= KMIN & kshift <= KMAX]
    wp[, lwage := log(wbar)]
    fit_wage <- tryCatch(
        feols(lwage ~ i(kshift, ai_q, ref = -1, ref2 = "1") | yrke4 + ym,
              data = wp, weights = ~w, cluster = ~yrke4),
        error = function(e) { cat("  wage feols failed:", conditionMessage(e), "\n"); NULL })
    harvest_es(fit_wage, sample, variant, a, "log_wage", nrow(wp), uniqueN(wp$yrke4))
    invisible(NULL)
}

# -----------------------------------------------------------------------------
# Variant "restricted": the 7b/7d sample, aggregated over foretak to (yrke4, ym)
# -----------------------------------------------------------------------------
d <- load_cells()
d <- d[in_headline_priv == 1L]
cat(sprintf("restricted: %s cell rows after in_headline_priv\n", fmt_int(nrow(d))))

for (a in 1:N_AGE_BINS) {
    da <- d[age_bin == a]
    if (nrow(da) == 0) { cat(sprintf("\n--- restricted age_bin %d: no rows, skip ---\n", a)); next }
    slice <- da[, .(count     = sum(count_all),
                    count_new = sum(count_new),
                    ai_q      = ai_q[1L]), by = .(yrke4, ym)]
    dw <- da[count_all > 0 & !is.na(m_wage_all) & m_wage_all > 0]
    wage_panel <- dw[, .(wbar = weighted.mean(m_wage_all, count_all),
                         w    = sum(count_all),
                         ai_q = ai_q[1L]), by = .(yrke4, ym)]
    run_age_slice(slice, wage_panel, "headline_priv", "restricted", a)
}
rm(d); invisible(gc(verbose = FALSE))

# -----------------------------------------------------------------------------
# Variant "unrestricted_priv": private occupation aggregate (script 4), pre-filter
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
    run_age_slice(slice, wage_panel, "all_priv", "unrestricted_priv", a)
}

# -----------------------------------------------------------------------------
# Save
# -----------------------------------------------------------------------------
out_coefs   <- rbindlist(Filter(Negate(is.null), coef_rows),    fill = TRUE)
out_summary <- rbindlist(Filter(Negate(is.null), summary_rows), fill = TRUE)
if (nrow(out_coefs)   > 0) setorder(out_coefs,   variant, age_bin, outcome, ai_q, k)
if (nrow(out_summary) > 0) setorder(out_summary, variant, age_bin, outcome)

atomic_fwrite(out_coefs,   file.path(COEFS, "coef_es_byage_cellspec.csv"))
atomic_fwrite(out_summary, file.path(COEFS, "coef_es_byage_cellspec_summary.csv"))
atomic_fwrite(rbindlist(diag_rows),
              file.path(DIAG, "fixest_diag_6f_event_study_cellspec.csv"))

cat(sprintf("\nSaved %d rows to coef_es_byage_cellspec.csv\n", nrow(out_coefs)))
cat(sprintf("Saved %d rows to coef_es_byage_cellspec_summary.csv\n", nrow(out_summary)))
cat("== 6f_event_study_cellspec.R done ", format(Sys.time()), " ==\n")
close_log()
