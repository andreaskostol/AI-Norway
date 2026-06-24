# =============================================================================
# A1_bcc_descriptive_agg.R : BCC-appendix descriptive aggregates (FT, BCC bins)
# =============================================================================
# Builds the inputs for the BCC-replication appendix figures 1, 2, 3, 5 on
# Norwegian register data, matched to Brynjolfsson-Chandar-Chen (2025):
#   - FULL-TIME workers only (ft == 1), PRIVATE sector (sekt == 3)
#   - BCC's six age bins: 22-25, 26-30, 31-34, 35-40, 41-49, 50-55
#   - employment headcount and mean monthly cash wage, indexed locally to
#     Oct 2022 in the plotter
#
# This is a LIGHT re-aggregation of the cached worker-month spell files
# (ameld_filt_*.rds, which retain a_year and the ft flag) -- it does NOT touch
# the heavy script 3, and needs no firm balancing. The firm-FE Poisson event
# study (BCC Fig 4) is a separate, heavier script (A2/A3).
#
# Outputs (to $OUTPUT/coefficients/, transferred out and plotted locally by
# analysis-indiv/code/plot_bcc_appendix.py):
#   bcc_desc_employment.csv  measure,group,bcc_age,ym,count
#       measure in {eloundou, handa_usage, handa_auto, handa_augm}
#       group   in {1..5, "overall"}            -> Fig 2 (eloundou), Fig 3 (handa_*)
#   bcc_desc_wage.csv         group,bcc_age,ym,mean_wage,n   (eloundou q + overall) -> Fig 5
#   bcc_desc_occ.csv          yrke4,occ_label,bcc_age,ym,count                      -> Fig 1
#
# Inputs:  $DATA/ameld_filt_{y}_m{m}.rds, $DATA/exposure.rds,
#          data/ai_exposure/styrk08_handa_mapping.csv (transferred to $DATA-side
#          data dir; path via DATA_EXT below)
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("data.table")

open_log("A1_bcc_descriptive_agg")
cat("== A1_bcc_descriptive_agg.R starting ", format(Sys.time()), " ==\n")

# BCC's six age bins applied to 1-year age; NA outside [22, 55] (dropped).
bcc_age_bin <- function(a) {
    fcase(a >= 22 & a <= 25, 1L,
          a >= 26 & a <= 30, 2L,
          a >= 31 & a <= 34, 3L,
          a >= 35 & a <= 40, 4L,
          a >= 41 & a <= 49, 5L,
          a >= 50 & a <= 55, 6L,
          default = NA_integer_)
}

# WINSOR_HI / WINSOR_MINN come from 0_settings.R (shared with 3_monthly_filtered.R,
# which winsorizes lonn_kontant at source). A1 re-applies the same cap defensively
# in case it runs on a pre-winsorization ameld_filt; on winsorized data it is a
# near-no-op.

# Fig-1 occupations (STYRK-08 4-digit): BCC's Software Developers + Customer
# Service. Adjust here if the manuscript wants different codes.
OCC_FIG1 <- c("2512" = "Software developers",
              "4222" = "Customer service")

# -----------------------------------------------------------------------------
# Exposure (Eloundou ai_q) + Handa usage/automation/augmentation quintiles
# -----------------------------------------------------------------------------
expo <- readRDS(file.path(DATA, "exposure.rds"))[, .(yrke4, ai_q)]

handa_path <- file.path(DATA, "styrk08_handa_mapping.csv")
if (!file.exists(handa_path))
    stop(handa_path, " not found. Transfer it from data/ai_exposure/ (same as ",
         "the eloundou mapping).")
ha <- fread(handa_path, colClasses = c(styrk08 = "character"))
ha[, yrke4 := pad0(styrk08, 4)]
ha <- ha[, .(yrke4,
             handa_usage = as.integer(q_overall_exposure),
             handa_auto  = as.integer(q_automation_share),
             handa_augm  = as.integer(q_augmentation_share))]

mg <- month_grid()

# Fail loudly + early if the cached spell files aren't all present (script 3
# not run on this delivery, or the data area was cleared): name the gaps
# instead of a cryptic mid-loop "error reading the file".
mg_paths <- file.path(DATA, sprintf("ameld_filt_%d_m%d.rds", mg$y, mg$m))
miss <- mg_paths[!file.exists(mg_paths)]
if (length(miss) > 0)
    stop(sprintf("Missing %d of %d ameld_filt_*.rds (run script 3 first, or the data area was cleared): %s",
                 length(miss), nrow(mg), paste(basename(miss), collapse = ", ")))

emp_rows <- list(); wage_rows <- list(); occ_rows <- list()

for (i in seq_len(nrow(mg))) {
    y <- mg$y[i]; m <- mg$m[i]
    f <- file.path(DATA, sprintf("ameld_filt_%d_m%d.rds", y, m))
    cat(sprintf("  %d m%d\n", y, m))
    d <- tryCatch(readRDS(f),
                  error = function(e) stop(sprintf("Failed reading %s: %s",
                                                   basename(f), conditionMessage(e))))
    setDT(d)
    d <- d[ft == 1L & sekt == 3L]                 # full-time, private
    d[, bcc_age := bcc_age_bin(a_year)]
    d <- d[!is.na(bcc_age)]
    ymv <- d$ym[1L]

    # --- Fig 1: two named occupations, by age (all mapped or not) ---
    o <- d[yrke4 %in% names(OCC_FIG1), .(count = .N), by = .(yrke4, bcc_age)]
    if (nrow(o) > 0) { o[, ym := ymv]; occ_rows[[length(occ_rows) + 1L]] <- o }

    # --- Eloundou: employment + wage by quintile, and pooled "overall" ---
    # Winsorize lonn_kontant within (yrke4, month) at WINSOR_HI -- wage scales
    # are occupation-specific, so a lone giant (the 3e9 kr cleaner record) is
    # judged against its own occupation. Small occ-months (< WINSOR_MINN, where
    # an own percentile would just equal the outlier) fall back to the pooled
    # per-month cap. See A1b_wage_spike_diag.R.
    de <- merge(d, expo, by = "yrke4")            # inner: keep mapped
    pool_cap <- as.numeric(quantile(de$lonn_kontant, WINSOR_HI, names = FALSE))
    caps <- de[, .(n_om = .N,
                   q = as.numeric(quantile(lonn_kontant, WINSOR_HI, names = FALSE))),
               by = yrke4]
    caps[, cap := fifelse(n_om >= WINSOR_MINN, q, pool_cap)]
    de[caps, on = "yrke4", cap := i.cap]
    de[, lk_w := pmin(lonn_kontant, cap)]
    e_q <- de[, .(count = .N, mw = sum(lk_w), nw = .N), by = .(bcc_age, ai_q)]
    e_all <- de[, .(ai_q = 99L, count = .N, mw = sum(lk_w), nw = .N),
                by = .(bcc_age)]
    eb <- rbind(e_q, e_all)
    eb[, ym := ymv]
    emp_rows[[length(emp_rows) + 1L]] <- eb[, .(
        measure = "eloundou",
        group = fifelse(ai_q == 99L, "overall", as.character(ai_q)),
        bcc_age, ym, count)]
    wage_rows[[length(wage_rows) + 1L]] <- eb[, .(
        group = fifelse(ai_q == 99L, "overall", as.character(ai_q)),
        bcc_age, ym, mean_wage = mw / nw, n = nw)]

    # --- Handa: employment by usage/auto/augm quintile + pooled overall ---
    dh <- merge(d, ha, by = "yrke4")
    for (meas in c("handa_usage", "handa_auto", "handa_augm")) {
        h_q <- dh[!is.na(get(meas)),
                  .(count = .N), by = c("bcc_age", meas)]
        setnames(h_q, meas, "q")
        h_all <- dh[!is.na(get(meas)), .(q = 99L, count = .N), by = .(bcc_age)]
        hb <- rbind(h_q, h_all); hb[, ym := ymv]
        emp_rows[[length(emp_rows) + 1L]] <- hb[, .(
            measure = meas,
            group = fifelse(q == 99L, "overall", as.character(q)),
            bcc_age, ym, count)]
    }
    rm(d, de, dh); invisible(gc(verbose = FALSE))
}

emp  <- rbindlist(emp_rows,  use.names = TRUE)
wage <- rbindlist(wage_rows, use.names = TRUE)
occ  <- rbindlist(occ_rows,  use.names = TRUE)
occ[, occ_label := OCC_FIG1[yrke4]]

# Event time so the plotter indexes to k = -1 (Oct 2022) and plots calendar
# dates without needing the ym epoch (k = 0 = YM_EVENT_ZERO = Nov 2022).
emp[,  k := ym - YM_EVENT_ZERO]
wage[, k := ym - YM_EVENT_ZERO]
occ[,  k := ym - YM_EVENT_ZERO]

setorder(emp,  measure, group, bcc_age, ym)
setorder(wage, group, bcc_age, ym)
setorder(occ,  yrke4, bcc_age, ym)

atomic_fwrite(emp,  file.path(COEFS, "bcc_desc_employment.csv"))
atomic_fwrite(wage, file.path(COEFS, "bcc_desc_wage.csv"))
atomic_fwrite(occ,  file.path(COEFS, "bcc_desc_occ.csv"))
cat(sprintf("Wrote bcc_desc_employment.csv (%d), bcc_desc_wage.csv (%d), bcc_desc_occ.csv (%d)\n",
            nrow(emp), nrow(wage), nrow(occ)))
cat("== A1_bcc_descriptive_agg.R done ", format(Sys.time()), " ==\n")
close_log()
