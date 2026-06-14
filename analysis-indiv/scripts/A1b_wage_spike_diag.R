# =============================================================================
# A1b_wage_spike_diag.R : diagnose the 2023-07 cash-wage spike (BCC Fig 5)
# =============================================================================
# Fig 5 (mean monthly cash wage, lonn_kontant) shows an anomalous spike for
# full-time private workers aged 35-40 in the LOWEST exposure quintile (Q1) in
# JULY 2023 (index ~2.6 vs Oct 2022, n ~40k). lonn_kontant includes lump-sum
# payments (holiday pay / feriepenger, bonuses, back-pay), so this is almost
# certainly a holiday-pay month. This script tells us whether it is BROAD
# (median also jumps -> real lump-sum month) or OUTLIERS (only the mean jumps
# -> a few extreme values to winsorize), and which occupations drive it.
#
# Reads the cached spell files only (no heavy re-run). Edit the constants to
# probe a different cell.
#
# Inputs:  $DATA/ameld_filt_2023_m{6,7,8}.rds, $DATA/exposure.rds
# Outputs: $output/diagnostics/bcc_wage_spike_by_month.csv
#          $output/diagnostics/bcc_wage_spike_by_occ_2023m7.csv
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("data.table")

open_log("A1b_wage_spike_diag")
cat("== A1b_wage_spike_diag.R starting ", format(Sys.time()), " ==\n")

AGE_LO <- 35L; AGE_HI <- 40L     # the spiking age bin
Q_SPIKE <- 1L                    # the spiking quintile (Q1, least exposed)
YEAR <- 2023L; MONTHS <- 6:8     # June, July (spike), August for context

expo <- readRDS(file.path(DATA, "exposure.rds"))[, .(yrke4, ai_q)]

slice <- function(y, m) {
    f <- file.path(DATA, sprintf("ameld_filt_%d_m%d.rds", y, m))
    if (!file.exists(f)) stop("missing ", basename(f))
    d <- setDT(readRDS(f))
    d <- d[ft == 1L & sekt == 3L & a_year >= AGE_LO & a_year <= AGE_HI]
    merge(d, expo, by = "yrke4")[ai_q == Q_SPIKE]
}

# Month-level: mean vs median (+ tails) -- the broad-vs-outliers test.
rows <- list()
for (m in MONTHS) {
    d <- slice(YEAR, m)
    rows[[length(rows) + 1L]] <- data.table(
        year = YEAR, month = m, n = nrow(d),
        mean = mean(d$lonn_kontant),       median = as.numeric(median(d$lonn_kontant)),
        p90  = as.numeric(quantile(d$lonn_kontant, .90)),
        p99  = as.numeric(quantile(d$lonn_kontant, .99)),
        max  = max(d$lonn_kontant))
}
bym <- rbindlist(rows)
cat("\n-- lonn_kontant, FT-private, age 35-40, Q1, by month --\n")
print(bym)
cat("\nRead: if median jumps with the mean in m7 -> BROAD lump-sum (holiday pay);\n",
    "if only mean/max jump and median is flat -> a few OUTLIERS (winsorize).\n")
atomic_fwrite(bym, file.path(DIAG, "bcc_wage_spike_by_month.csv"))

# Which occupations drive July: mean lonn_kontant + the month-on-month jump.
d6 <- slice(YEAR, 6)[, .(mean_jun = mean(lonn_kontant), n = .N), by = yrke4]
d7 <- slice(YEAR, 7)[, .(mean_jul = mean(lonn_kontant), n = .N), by = yrke4]
byocc <- merge(d7, d6[, .(yrke4, mean_jun)], by = "yrke4", all.x = TRUE)
byocc[, jul_vs_jun := mean_jul / mean_jun]
setorder(byocc, -mean_jul)
cat("\n-- top 12 yrke4 by July mean cash wage (age 35-40, Q1) --\n")
print(head(byocc, 12))
atomic_fwrite(byocc, file.path(DIAG, "bcc_wage_spike_by_occ_2023m7.csv"))

cat("\n== A1b_wage_spike_diag.R done ", format(Sys.time()), " ==\n")
close_log()
