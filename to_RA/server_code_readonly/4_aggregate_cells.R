# =============================================================================
# 4_aggregate_cells.R : worker-month -> (frtk x sekt x age x yrke4 x month) cells
# =============================================================================
# For each month, load the filtered worker-month file, collapse to cell counts
# + cell means, attach ai_q/exposure via yrke4, save per-month cells. Then
# stack all months, filter to active foretak-months, and balance the panel.
#
# Inputs:  $DATA/ameld_filt_{y}_m{m}.rds   (one per month, from script 3)
#          $DATA/exposure.rds              (from script 1)
# Outputs: $DATA/cells_{y}_m{m}.rds        (one per month, intermediate)
#          $DATA/occ_unrestricted_agg.rds  (NEW: occupation aggregate BEFORE
#                                           the activity filter -- the bridge
#                                           to the microdata.no cell analysis,
#                                           used by 7d. See DESIGN_CHOICES.md
#                                           section 22.)
#          $DATA/cells.rds                 (balanced cell panel)
#          fragment section_05 + rebuilt SECURE_SERVER_RESULTS.md
#          log_4_aggregate_cells.txt
#
# cells.rds unit : (lopenr_foretak, sekt, age_bin, yrke4, ym)
#   Joined       : ai_q, exposure_score, exposure_std
#   Counts       : count_all, count_ft, count_new
#   Cell means   : m_wage_all/_ft, m_position_all/_ft, m_basehours_all/_ft,
#                  m_overtime_all/_ft  (means over workers; _ft = FT only)
#
# Panel is BALANCED at the (foretak, age_bin, yrke4) cell level: for each cell
# that ever has positive employment, all *active* months of its foretak are
# present (zero counts on synthetic rows). This lets firm x time FE see firm
# exits. A (foretak, ym) is active when total employment 21-60 >=
# FRTK_MIN_ACTIVE; months below are treated as foretak-not-operating.
#
# Design rationale: DESIGN_CHOICES.md sections 4 (cell unit), 6 (activity
# threshold), 7 (balanced panel), 8 (foretak activity), 9 (sample-weighted
# exposure standardization), 16 (numeric IDs).
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("data.table")

open_log("4_aggregate_cells")
cat("== 4_aggregate_cells.R starting ", format(Sys.time()), " ==\n")

expo <- readRDS(file.path(DATA, "exposure.rds"))
setDT(expo); setkey(expo, yrke4)
# Joining exposure AFTER the collapse (cheap) is only equivalent to the
# worker-level merge if exposure is unique per yrke4 -- assert it here, at
# the join, not only where the file is built.
stopifnot(anyDuplicated(expo$yrke4) == 0L)

mg <- month_grid()

# Means in Stata's collapse skip missings and give missing for all-missing
# groups; mean(na.rm = TRUE) gives NaN there -- normalize to NA.
nan_to_na <- function(x) fifelse(is.nan(x), NA_real_, x)

# -----------------------------------------------------------------------------
# Section 1: Per-month collapse (write per-month .rds)
# -----------------------------------------------------------------------------

for (i in seq_len(nrow(mg))) {
    y <- mg$y[i]; m <- mg$m[i]
    infile  <- file.path(DATA, sprintf("ameld_filt_%d_m%d.rds", y, m))
    outfile <- file.path(DATA, sprintf("cells_%d_m%d.rds", y, m))

    cat(sprintf("=== Aggregating %d m%d ===\n", y, m))
    d <- readRDS(infile)
    setDT(d)

    # FT-conditional outcome columns (NA for non-FT) so the cell mean
    # averages over FT workers only.
    d[, `:=`(wage_ft      = fifelse(ft == 1L, lonn_kontant,       NA_real_),
             position_ft  = fifelse(ft == 1L, arb_stillingspst,   NA_real_),
             basehours_ft = fifelse(ft == 1L, basehours,          NA_real_),
             overtime_ft  = fifelse(ft == 1L, lonn_overtid_timer, NA_real_))]

    cells <- d[, .(
        count_all       = .N,
        count_ft        = sum(ft),
        count_new       = sum(ny_jobb),
        m_wage_all      = mean(lonn_kontant),
        m_position_all  = mean(arb_stillingspst,   na.rm = TRUE),
        m_basehours_all = mean(basehours,          na.rm = TRUE),
        m_overtime_all  = mean(lonn_overtid_timer, na.rm = TRUE),
        m_wage_ft       = mean(wage_ft,            na.rm = TRUE),
        m_position_ft   = mean(position_ft,        na.rm = TRUE),
        m_basehours_ft  = mean(basehours_ft,       na.rm = TRUE),
        m_overtime_ft   = mean(overtime_ft,        na.rm = TRUE)
    ), by = .(lopenr_foretak, sekt, age_bin, yrke4, ym)]

    mcols <- grep("^m_", names(cells), value = TRUE)
    cells[, (mcols) := lapply(.SD, nan_to_na), .SDcols = mcols]

    # Attach exposure; drop cells (= worker-months) without an exposure score.
    # Exposure is keyed on yrke4 alone, so joining after the collapse is
    # exactly equivalent to the worker-level keep(match) merge in the Stata
    # pipeline, at a fraction of the cost.
    cells[expo, on = "yrke4",
          `:=`(ai_q = i.ai_q, exposure_score = i.exposure_score,
               exposure_std = i.exposure_std)]
    cells <- cells[!is.na(ai_q)]

    atomic_saveRDS(cells, outfile)
    rm(d, cells); invisible(gc(verbose = FALSE))
}

# -----------------------------------------------------------------------------
# Section 2: Stack all per-month cell files (chronological order matters:
# first-occurrence dedups below replicate Stata's append order)
# -----------------------------------------------------------------------------

stacked <- rbindlist(
    lapply(seq_len(nrow(mg)), function(i)
        readRDS(file.path(DATA, sprintf("cells_%d_m%d.rds", mg$y[i], mg$m[i])))),
    use.names = TRUE
)
cat(sprintf("\nStacked cells: %s rows over %d months\n",
            fmt_int(nrow(stacked)), nrow(mg)))
log_size(stacked, "stacked_after_rbind")

# Sanity (before balancing all rows have positive employment)
stopifnot(all(stacked$ai_q %in% 1:5))
stopifnot(all(stacked$count_all > 0))
stopifnot(all(stacked$count_new >= 0), all(stacked$count_ft >= 0))

# -----------------------------------------------------------------------------
# Section 2.4: Unrestricted occupation aggregate (the microdata.no bridge)
# -----------------------------------------------------------------------------
# Summed over foretak BEFORE the activity filter and balancing, so it carries
# no >= FRTK_MIN_ACTIVE restriction. Because every kept worker has
# lonn_kontant > 0 (script 3), count_all * m_wage_all is the exact wage sum,
# and wage_sum / count below recovers the worker-level mean wage per cell.
# 7d runs the cell-level DiD spec on this (variant "unrestricted_priv").

stopifnot(!anyNA(stacked$m_wage_all))
occ_unrest <- stacked[, .(
    count     = sum(count_all),
    count_new = sum(count_new),
    wage_sum  = sum(count_all * m_wage_all),
    ai_q      = ai_q[1L]                     # constant within yrke4
), by = .(yrke4, age_bin, sekt, ym)]
atomic_saveRDS(occ_unrest, file.path(DATA, "occ_unrestricted_agg.rds"))
cat(sprintf("Unrestricted occupation aggregate: %s rows saved to occ_unrestricted_agg.rds\n",
            fmt_int(nrow(occ_unrest))))

# -----------------------------------------------------------------------------
# Section 2.5: Filter inactive foretak-months + balance the panel
# -----------------------------------------------------------------------------

# Outcome columns of the unbalanced cells (without cell attributes). sekt is
# treated as constant within (foretak, age_bin, yrke4): in the rare case of a
# sector change over the panel, the first observed sekt applies throughout
# (carried by cell_keys below); the dedup here is a safety net.
outcome_cols <- c("count_all", "count_ft", "count_new",
                  "m_wage_all", "m_wage_ft", "m_position_all", "m_position_ft",
                  "m_basehours_all", "m_basehours_ft",
                  "m_overtime_all", "m_overtime_ft")
outcomes_unbal <- stacked[, c("lopenr_foretak", "age_bin", "yrke4", "ym",
                              outcome_cols), with = FALSE]
n_before <- nrow(outcomes_unbal)
outcomes_unbal <- unique(outcomes_unbal,
                         by = c("lopenr_foretak", "age_bin", "yrke4", "ym"))
if (nrow(outcomes_unbal) < n_before)
    cat(sprintf("  NOTE: dropped %s duplicate (frtk, age, yrke4, ym) outcome rows\n",
                fmt_int(n_before - nrow(outcomes_unbal))))

# (a) Active (foretak, ym): total employment in the age window >= threshold.
frtk_active <- stacked[, .(tot = sum(count_all)), by = .(lopenr_foretak, ym)]
frtk_active <- frtk_active[tot >= FRTK_MIN_ACTIVE, .(lopenr_foretak, ym)]
cat(sprintf("  Active (foretak, ym) periods: %s\n", fmt_int(nrow(frtk_active))))

# (b) Unique cell keys with their constant attributes (first occurrence wins).
cell_keys <- unique(
    stacked[, .(lopenr_foretak, sekt, age_bin, yrke4,
                ai_q, exposure_score, exposure_std)],
    by = c("lopenr_foretak", "age_bin", "yrke4")
)
cat(sprintf("  Unique cells: %s\n", fmt_int(nrow(cell_keys))))
log_size(outcomes_unbal, "outcomes_unbal")
log_size(cell_keys, "cell_keys")

rm(stacked); invisible(gc(verbose = FALSE))

# Balanced grid: each cell crossed with all active months of its foretak
# (data.table equivalent of Stata's joinby).
cat("Building balanced grid (cell x active months) ...\n")
bal <- cell_keys[frtk_active, on = "lopenr_foretak",
                 allow.cartesian = TRUE, nomatch = NULL]

# Merge in observed outcomes; synthetic (cell x month) rows get NA -> counts 0.
bal[outcomes_unbal, on = c("lopenr_foretak", "age_bin", "yrke4", "ym"),
    (outcome_cols) := mget(paste0("i.", outcome_cols))]
setnafill(bal, fill = 0L, cols = c("count_all", "count_ft", "count_new"))
# Intensive-margin cell means stay NA on synthetic rows; scripts 7b/7d/8 drop
# missings before the weighted OLS.

cat(sprintf("  Balanced active panel size: %s rows\n", fmt_int(nrow(bal))))
log_size(bal, "cells_balanced")
stopifnot(all(bal$count_all >= 0), all(bal$count_ft >= 0),
          all(bal$count_new >= 0))
stopifnot(!anyNA(bal$ai_q))   # synthetic rows must inherit ai_q from cell_keys

# -----------------------------------------------------------------------------
# Section 2.6: Sample-weighted standardization of exposure_score
# -----------------------------------------------------------------------------
# Replace the universe standardization from script 1 with one weighted by
# employment in the balanced + active panel (Stata [aw=count_all] semantics;
# synthetic zero rows carry zero weight). Coefficients on exposure_std then
# read as "per SD of the employment-weighted exposure distribution".

sw <- stata_aw_sd(bal$exposure_score, bal$count_all)
cat(sprintf("\nSample-weighted exposure: mean = %.6f, SD = %.6f\n", sw$mean, sw$sd))
stopifnot(is.finite(sw$mean), is.finite(sw$sd), sw$sd > 0)
bal[, exposure_std := (exposure_score - sw$mean) / sw$sd]
stopifnot(!anyNA(bal$exposure_std))   # all-NA here broke 6d/7/8 in the first
                                      # real run -- fail HERE, not mid-estimation

# Numeric IDs for fixed-effect absorption. as.integer(factor()) numbers the
# groups in sort order, like Stata's egen group().
bal[, frtk_id  := as.integer(factor(lopenr_foretak))]
bal[, yrke4_id := as.integer(factor(yrke4))]

setorder(bal, lopenr_foretak, sekt, age_bin, yrke4, ym)
atomic_saveRDS(bal, file.path(DATA, "cells.rds"))
cat("cells.rds saved.\n")

# -----------------------------------------------------------------------------
# Section 3: Diagnostics + fragment §5
# -----------------------------------------------------------------------------

n_cells     <- nrow(bal)
n_pos       <- bal[count_all > 0, .N]
n_synth     <- n_cells - n_pos
n_singleton <- bal[count_all == 1, .N]
n_frtk      <- uniqueN(bal$lopenr_foretak)
ct          <- bal[count_all > 0, count_all]

cat(sprintf("\nCell file: %s rows (%s positive, %s synthetic-zero) over %s foretak.\n",
            fmt_int(n_cells), fmt_int(n_pos), fmt_int(n_synth), fmt_int(n_frtk)))
cat(sprintf("  count_all (positive cells): mean = %.2f, median = %.0f, p90 = %.0f, p99 = %.0f\n",
            mean(ct), median(ct), quantile(ct, 0.90), quantile(ct, 0.99)))
cat(sprintf("  Singleton cells (count_all == 1): %s\n", fmt_int(n_singleton)))

# Machine-readable counterpart of the §5 fragment, for run-to-run comparison.
atomic_fwrite(data.table(
    quantity = c("n_cells", "n_positive", "n_synthetic", "n_singleton",
                 "n_frtk", "n_yrke4", "n_age_bin", "n_ym",
                 "n_rows_unrestricted_agg", "sum_count_all", "sum_count_new"),
    value = c(n_cells, n_pos, n_synth, n_singleton,
              n_frtk, uniqueN(bal$yrke4), uniqueN(bal$age_bin), uniqueN(bal$ym),
              nrow(occ_unrest), sum(bal$count_all), sum(bal$count_new))
), file.path(DIAG, "aggregate_cell_counts.csv"))
cat("  Wrote diagnostics/aggregate_cell_counts.csv\n")

write_fragment("05", c(
    "## §5: Cell-level dataset",
    "",
    sprintf(paste("Unit of observation: foretak x sektor x age_bin x yrke4 x",
                  "month. Panel is BALANCED at the (foretak, age_bin, yrke4)",
                  "cell level: for each cell that ever had positive employment,",
                  "all *active* months for the foretak are present, with",
                  "count_all = count_ft = count_new = 0 on synthetic rows. A",
                  "(foretak, ym) period is active when total foretak employment",
                  "in the age window %d-%d is at least %d workers (configurable",
                  "in 0_settings.R); months below this threshold are treated as",
                  "foretak-not-operating and dropped. Intensive-margin cell",
                  "means are missing on synthetic rows."),
            AGE_MIN, AGE_MAX, FRTK_MIN_ACTIVE),
    "",
    "| Quantity | Value |",
    "|---|---:|",
    sprintf("| Total cell rows | %s |", fmt_int(n_cells)),
    sprintf("| Cells with count_all > 0 | %s |", fmt_int(n_pos)),
    sprintf("| Synthetic zero-employment rows | %s |", fmt_int(n_synth)),
    sprintf("| Distinct foretak | %s |", fmt_int(n_frtk)),
    sprintf("| Singleton cells (count_all = 1) | %s |", fmt_int(n_singleton)),
    sprintf("| Mean cell size (count_all > 0 only) | %.2f |", mean(ct)),
    sprintf("| Median (p50, count_all > 0) | %.0f |", median(ct)),
    sprintf("| 90th percentile (count_all > 0) | %.0f |", quantile(ct, 0.90)),
    sprintf("| 99th percentile (count_all > 0) | %.0f |", quantile(ct, 0.99)),
    "",
    paste("**Joined columns** (from exposure.rds via yrke4): ai_q (1-5),",
          "exposure_score (Eloundou GPT-4 beta), exposure_std (z-score,",
          "employment-weighted standardization over the balanced + active",
          "panel)."),
    "",
    paste("**Side output** occ_unrestricted_agg.rds: (yrke4, age_bin, sekt, ym)",
          "aggregate of the same per-month cells BEFORE the activity filter and",
          "balancing -- the bridge to the microdata.no cell analysis, estimated",
          "by 7d (variant unrestricted_priv)."),
    "",
    "---",
    ""
))
rebuild_results_md()

cat("\nScript 4 complete. cells.rds + occ_unrestricted_agg.rds saved; section_05 fragment rebuilt.\n")
cat("== 4_aggregate_cells.R done ", format(Sys.time()), " ==\n")
close_log()
