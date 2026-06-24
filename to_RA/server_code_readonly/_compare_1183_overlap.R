# =============================================================================
# _compare_1183_overlap.R : Stata/1183-pipeline vs R/1191-pipeline overlap test
# =============================================================================
# SERVER-SIDE, run MANUALLY after the first full 1191 run (not part of
# 99_master.R). Compares the archived Stata pipeline's cells_flagged.dta
# (data universe 1183/7020, panel 2021m1-2025m7) with the new R pipeline's
# cells_flagged.rds (1191), restricted to the overlap window 2021m1-2025m7.
#
#   Rscript _compare_1183_overlap.R
#
# This separates the two changes bundled in this migration: differences here
# reflect (Stata->R port) + (7020->1191 delivery revisions) on the same
# window; the synthetic smoke test already verified the port logic in
# isolation, so material gaps point at delivery differences.
#
# What is comparable: distribution-level quantities (counts, sums, weighted
# means, per-(ym, age_bin, ai_q) checksums). What is NOT: identity-level
# joins -- lopenr_* scrambling differs between project deliveries, so firm
# IDs cannot be matched across the two files.
#
# Expectation: NOT exact equality. The §4 funnel showed ~0.01% raw-row
# differences between the 7020 and 1191 vintages; cells-level aggregates
# should agree to well under 1%. Investigate anything larger.
#
# Inputs:  OLD_CELLS (F:\1183\...\cells_flagged.dta -- edit below if moved)
#          $DATA/cells_flagged.rds
# Output:  $DIAG/stata_r_overlap_diff.csv          (headline metrics)
#          $DIAG/stata_r_overlap_checksums.csv     (per ym x age_bin x ai_q)
#          log_compare_1183_overlap.txt
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("haven"); req("data.table")

open_log("compare_1183_overlap")
cat("== _compare_1183_overlap.R starting ", format(Sys.time()), " ==\n")

OLD_CELLS <- "F:/1183/oysteimh/ai_norway_indiv/data/cells_flagged.dta"
OVERLAP_FROM <- ym(2021, 1)
OVERLAP_TO   <- ym(2025, 7)   # end of the 1183 panel

if (!file.exists(OLD_CELLS))
    stop(OLD_CELLS, " not found -- the 1183 area may have been cleaned up; ",
         "this comparison is then no longer possible.")

old <- as.data.table(haven::read_dta(OLD_CELLS))
new <- load_cells()
old <- old[ym >= OVERLAP_FROM & ym <= OVERLAP_TO]
new <- new[ym >= OVERLAP_FROM & ym <= OVERLAP_TO]
old[, yrke4 := pad0(as.character(yrke4), 4)]
cat(sprintf("Overlap window %d-%d: old %s rows, new %s rows\n",
            OVERLAP_FROM, OVERLAP_TO, fmt_int(nrow(old)), fmt_int(nrow(new))))

# -----------------------------------------------------------------------------
# Headline metrics
# -----------------------------------------------------------------------------
metrics <- function(d) {
    has_new <- "count_new" %in% names(d)
    pos <- d[count_all > 0]
    list(
        n_rows            = nrow(d),
        n_rows_positive   = nrow(pos),
        n_frtk            = uniqueN(d$lopenr_foretak),
        n_yrke4           = uniqueN(d$yrke4),
        n_ym              = uniqueN(d$ym),
        sum_count_all     = sum(d$count_all),
        sum_count_ft      = sum(d$count_ft),
        sum_count_new     = if (has_new) sum(d$count_new) else NA_real_,
        w_mean_wage       = pos[!is.na(m_wage_all),
                                weighted.mean(m_wage_all, count_all)],
        w_mean_basehours  = pos[!is.na(m_basehours_all),
                                weighted.mean(m_basehours_all, count_all)],
        n_headline        = d[in_headline == 1, .N],
        n_headline_priv   = d[in_headline_priv == 1, .N],
        n_ft              = d[in_ft == 1, .N],
        n_ft_priv         = d[in_ft_priv == 1, .N],
        n_bcc_full        = d[in_bcc_full == 1, .N]
    )
}
mo <- metrics(old); mn <- metrics(new)
diff <- data.table(
    metric    = names(mo),
    old_1183  = as.numeric(unlist(mo)),
    new_1191  = as.numeric(unlist(mn)))
diff[, rel_diff_pct := fifelse(old_1183 == 0, NA_real_,
                               100 * (new_1191 - old_1183) / old_1183)]
cat("\nHeadline comparison (old 1183/Stata vs new 1191/R, overlap window):\n")
print(diff, digits = 6)
atomic_fwrite(diff, file.path(DIAG, "stata_r_overlap_diff.csv"))

# -----------------------------------------------------------------------------
# Checksums per (ym, age_bin, ai_q): where in the panel do differences sit?
# -----------------------------------------------------------------------------
cks <- merge(
    old[, .(old_sum = sum(count_all)), by = .(ym, age_bin, ai_q)],
    new[, .(new_sum = sum(count_all)), by = .(ym, age_bin, ai_q)],
    by = c("ym", "age_bin", "ai_q"), all = TRUE)
cks[is.na(old_sum), old_sum := 0]
cks[is.na(new_sum), new_sum := 0]
cks[, rel_diff_pct := fifelse(old_sum == 0, NA_real_,
                              100 * (new_sum - old_sum) / old_sum)]
setorder(cks, -rel_diff_pct, na.last = TRUE)
atomic_fwrite(cks, file.path(DIAG, "stata_r_overlap_checksums.csv"))
cat(sprintf("\nChecksums: %d (ym, age_bin, ai_q) cells; |rel diff| > 1%% in %d cells\n",
            nrow(cks), cks[abs(rel_diff_pct) > 1, .N]))
cat("Largest deviations:\n")
print(head(cks[!is.na(rel_diff_pct)][order(-abs(rel_diff_pct))], 15))

cat("\nWrote diagnostics/stata_r_overlap_diff.csv + stata_r_overlap_checksums.csv\n")
cat("== _compare_1183_overlap.R done ", format(Sys.time()), " ==\n")
close_log()
