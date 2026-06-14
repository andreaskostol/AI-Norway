# =============================================================================
# 5c_baseline_kref.R : baseline cohort employment rates at k = -1
# =============================================================================
# Computes the cohort employment share at the reference month (October 2022)
# so the local figure script can rescale event-study coefficients from 6c/6d
# into "% of baseline cohort employment".
#
# For 6c (per age_bin x ai_q): baseline_rate = workers in (age_bin, ai_q)
# cells at k = -1 / cohort population. For 6d (continuous x young):
# baseline_rate per age_bin, summed over q & yrke4.
#
# Inputs:  $DATA/cells_flagged.rds
#          $DATA/population_by_agebin_ym.rds   (from 5b)
# Outputs: $COEFS/baseline_kref_by_age_q.csv
#          $COEFS/baseline_kref_by_age.csv
#          log_5c_baseline_kref.txt
#
# No regression -- a sum + divide on cells at one month. Fast.
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("data.table")

open_log("5c_baseline_kref")
cat("== 5c_baseline_kref.R starting ", format(Sys.time()), " ==\n")

d   <- load_cells()
pop <- load_population()

d <- d[in_headline_priv == 1L & ym == YM_REF]
cat(sprintf("Cells in headline_priv at reference month: %s\n", fmt_int(nrow(d))))

d[pop, on = c("age_bin", "ym"), population := i.population]
n_nopop <- d[is.na(population), .N]
if (n_nopop > 0) {
    cat(sprintf("  WARNING: %d rows have missing population; dropping.\n", n_nopop))
    d <- d[!is.na(population)]
}

# --- Per (age_bin, ai_q) baseline rate ---------------------------------------
by_age_q <- d[, .(total_count = sum(count_all), population = population[1L]),
              keyby = .(age_bin, ai_q)]
by_age_q[, baseline_rate := total_count / population]

cat("\nBaseline employment shares per (age_bin, ai_q) at k = -1:\n")
print(by_age_q)
fwrite(by_age_q, file.path(COEFS, "baseline_kref_by_age_q.csv"))

# --- Per age_bin baseline rate (aggregated over q & yrke4) --------------------
by_age <- d[, .(total_count = sum(count_all), population = population[1L]),
            keyby = age_bin]
by_age[, baseline_rate := total_count / population]

cat("\nBaseline employment shares per age_bin at k = -1:\n")
print(by_age)
fwrite(by_age, file.path(COEFS, "baseline_kref_by_age.csv"))

cat("\nScript 5c complete. Baselines saved to coefficients/.\n")
cat("== 5c_baseline_kref.R done ", format(Sys.time()), " ==\n")
close_log()
