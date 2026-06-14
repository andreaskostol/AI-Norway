# =============================================================================
# A2_bcc_panel.R : BCC-binned, full-time-private balanced firm panel (for Fig 4)
# =============================================================================
# Lean clone of 4_aggregate_cells.R's balancing (§2.5) + the in_bcc_full flag
# from 5_apply_restrictions.R, but on BCC's six age bins (22-25 .. 50-55) read
# off a_year in the cached ameld_filt_*.rds. Produces the balanced foretak ×
# bcc_age × yrke4 × ym panel + the in_bcc_full restriction flag, which
# A3_bcc_event_study.R uses for the BCC Fig-4 Poisson event study.
#
# Same conventions as the decade pipeline: active foretak-month = >= FRTK_MIN_ACTIVE
# workers (here in the 22-55 window) that month; balanced cells with synthetic
# zeros; exposure_std re-standardized employment-weighted on this panel.
# in_bcc_full = FT-private AND >= BCC_MIN_PER_AGE FT per (firm, bcc_age) every
# month AND sum_t count_ft >= BCC_MIN_TOTAL per (firm, ai_q, bcc_age).
#
# Inputs:  $DATA/ameld_filt_{y}_m{m}.rds, $DATA/exposure.rds
# Outputs: $DATA/cells_bcc.rds  (balanced panel + frtk_id + in_bcc_full)
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("data.table")

open_log("A2_bcc_panel")
cat("== A2_bcc_panel.R starting ", format(Sys.time()), " ==\n")

# BCC's six age bins on 1-year age; NA outside [22, 55] (dropped).
bcc_age_bin <- function(a) {
    fcase(a >= 22 & a <= 25, 1L, a >= 26 & a <= 30, 2L, a >= 31 & a <= 34, 3L,
          a >= 35 & a <= 40, 4L, a >= 41 & a <= 49, 5L, a >= 50 & a <= 55, 6L,
          default = NA_integer_)
}

expo <- readRDS(file.path(DATA, "exposure.rds"))[, .(yrke4, ai_q, exposure_score)]
mg <- month_grid()

# Fail loudly + early if the cached spell files aren't all present (script 3
# not run on this delivery, or the data area was cleared).
mg_paths <- file.path(DATA, sprintf("ameld_filt_%d_m%d.rds", mg$y, mg$m))
miss <- mg_paths[!file.exists(mg_paths)]
if (length(miss) > 0)
    stop(sprintf("Missing %d of %d ameld_filt_*.rds (run script 3 first, or the data area was cleared): %s",
                 length(miss), nrow(mg), paste(basename(miss), collapse = ", ")))

# -----------------------------------------------------------------------------
# Per-month collapse to (foretak, sekt, bcc_age, yrke4, ym) with BCC bins
# -----------------------------------------------------------------------------
cells_list <- vector("list", nrow(mg))
for (i in seq_len(nrow(mg))) {
    y <- mg$y[i]; m <- mg$m[i]
    f <- file.path(DATA, sprintf("ameld_filt_%d_m%d.rds", y, m))
    cat(sprintf("  %d m%d\n", y, m))
    d <- tryCatch(readRDS(f),
                  error = function(e) stop(sprintf("Failed reading %s: %s",
                                                   basename(f), conditionMessage(e))))
    setDT(d)
    d[, age_bin := bcc_age_bin(a_year)]
    d <- d[!is.na(age_bin)]
    cells <- d[, .(count_all = .N, count_ft = sum(ft), count_new = sum(ny_jobb)),
               by = .(lopenr_foretak, sekt, age_bin, yrke4, ym)]
    cells[expo, on = "yrke4",
          `:=`(ai_q = i.ai_q, exposure_score = i.exposure_score)]
    cells <- cells[!is.na(ai_q)]
    cells_list[[i]] <- cells
    rm(d, cells)
}
stacked <- rbindlist(cells_list, use.names = TRUE)
rm(cells_list); invisible(gc(verbose = FALSE))
cat(sprintf("Stacked BCC-binned cells: %s rows\n", fmt_int(nrow(stacked))))

# -----------------------------------------------------------------------------
# Active foretak-months + balance (mirrors 4_aggregate_cells.R §2.5)
# -----------------------------------------------------------------------------
cnt <- c("count_all", "count_ft", "count_new")
outcomes_unbal <- unique(stacked[, c("lopenr_foretak", "age_bin", "yrke4", "ym", cnt),
                                 with = FALSE],
                         by = c("lopenr_foretak", "age_bin", "yrke4", "ym"))
frtk_active <- stacked[, .(tot = sum(count_all)), by = .(lopenr_foretak, ym)]
frtk_active <- frtk_active[tot >= FRTK_MIN_ACTIVE, .(lopenr_foretak, ym)]
cell_keys <- unique(stacked[, .(lopenr_foretak, sekt, age_bin, yrke4, ai_q, exposure_score)],
                    by = c("lopenr_foretak", "age_bin", "yrke4"))
rm(stacked); invisible(gc(verbose = FALSE))

bal <- cell_keys[frtk_active, on = "lopenr_foretak",
                 allow.cartesian = TRUE, nomatch = NULL]
bal[outcomes_unbal, on = c("lopenr_foretak", "age_bin", "yrke4", "ym"),
    (cnt) := mget(paste0("i.", cnt))]
setnafill(bal, fill = 0L, cols = cnt)
log_size(bal, "cells_bcc_balanced")
cat(sprintf("Balanced BCC panel: %s rows\n", fmt_int(nrow(bal))))
stopifnot(all(bal$count_all >= 0), all(bal$count_ft >= 0), !anyNA(bal$ai_q))

# Sample-weighted exposure_std (employment-weighted on this panel).
sw <- stata_aw_sd(bal$exposure_score, bal$count_all)
bal[, exposure_std := (exposure_score - sw$mean) / sw$sd]
stopifnot(!anyNA(bal$exposure_std))
bal[, frtk_id := as.integer(factor(lopenr_foretak))]

# -----------------------------------------------------------------------------
# in_bcc_full restriction flag (mirrors 5_apply_restrictions.R §2)
# -----------------------------------------------------------------------------
bal[, in_ft := as.integer(any(count_ft > 0)), by = .(lopenr_foretak, age_bin, yrke4)]
bal[, in_ft_priv := as.integer(in_ft == 1L & sekt == 3L)]
panel_length <- uniqueN(bal$ym)
ftp <- bal[in_ft_priv == 1L]

fa <- ftp[, .(c = sum(count_ft)), by = .(lopenr_foretak, age_bin, ym)]
fa <- fa[, .(fa_pass = as.integer(min(c) >= BCC_MIN_PER_AGE & .N == panel_length)),
         by = .(lopenr_foretak, age_bin)]
bal[fa, on = c("lopenr_foretak", "age_bin"), fa_pass := i.fa_pass]
bal[is.na(fa_pass), fa_pass := 0L]

fqa <- ftp[, .(s = sum(count_ft)), by = .(lopenr_foretak, age_bin, ai_q)]
fqa[, fqa_pass := as.integer(s >= BCC_MIN_TOTAL)]
bal[fqa, on = c("lopenr_foretak", "age_bin", "ai_q"), fqa_pass := i.fqa_pass]
bal[is.na(fqa_pass), fqa_pass := 0L]

bal[, in_bcc_full := as.integer(in_ft_priv == 1L & fa_pass == 1L & fqa_pass == 1L)]
cat(sprintf("in_bcc_full cells: %s of %s (%s foretak)\n",
            fmt_int(bal[in_bcc_full == 1L, .N]), fmt_int(nrow(bal)),
            fmt_int(bal[in_bcc_full == 1L, uniqueN(lopenr_foretak)])))

atomic_saveRDS(bal, file.path(DATA, "cells_bcc.rds"))
cat("== A2_bcc_panel.R done ", format(Sys.time()), " ==\n")
close_log()
