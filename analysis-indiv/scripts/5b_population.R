# =============================================================================
# 5b_population.R : SSB population data aggregated to (age_bin, ym)
# =============================================================================
# Loads ssb_population_by_age_quarterly.csv (1-year ages, quarterly snapshots
# from SSB Statistikkbanken table 07459) and produces population summed to the
# four decade age_bins, expanded to monthly. Each month within a quarter
# inherits that quarter's population (population changes slowly enough that
# this is fine). See DESIGN_CHOICES.md section 20.
#
# Used by 6c/6d (and 5c/5d) as the denominator for per-capita rates.
#
# Inputs:  $DATA/ssb_population_by_age_quarterly.csv
# Outputs: $DATA/population_by_agebin_ym.rds   (age_bin, ym, population)
#          log_5b_population.txt
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("data.table")

open_log("5b_population")
cat("== 5b_population.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Section 1: Load population CSV
# -----------------------------------------------------------------------------

csv_path <- file.path(DATA, "ssb_population_by_age_quarterly.csv")
if (!file.exists(csv_path))
    stop(csv_path, " not found. Transfer it from data/macro/.")

pop <- fread(csv_path, colClasses = c(date = "character"))
stopifnot(all(c("date", "age", "population") %in% names(pop)))

# date column has format "YYYY-Qn", e.g. "2021-Q1"
pop[, yr := as.integer(substr(date, 1, 4))]
pop[, q  := as.integer(substr(date, 7, 7))]
stopifnot(!anyNA(pop$yr), all(pop$q %in% 1:4))

# -----------------------------------------------------------------------------
# Section 2: Map ages to age_bin (same convention as script 3 / 0_settings.R)
# -----------------------------------------------------------------------------
#   1: 21-30   2: 31-40   3: 41-50   4: 51-60. Other ages dropped.

pop[, age := as.integer(age)]
pop[, age_bin := fcase(age >= 21 & age <= 30, 1L,
                       age >= 31 & age <= 40, 2L,
                       age >= 41 & age <= 50, 3L,
                       age >= 51 & age <= 60, 4L,
                       default = NA_integer_)]
pop <- pop[!is.na(age_bin)]

# -----------------------------------------------------------------------------
# Section 3: Aggregate to (age_bin, year, quarter), expand to monthly
# -----------------------------------------------------------------------------
# Each (age_bin, yr, q) row produces 3 monthly rows: mo = (q-1)*3 + 1..3.

pop <- pop[, .(population = sum(population)), by = .(age_bin, yr, q)]

pop3 <- pop[rep(seq_len(.N), each = 3L)]
pop3[, mo_in_q := rep(1:3, times = nrow(pop))]
pop3[, mo := (q - 1L) * 3L + mo_in_q]
pop3[, ym := ym(yr, mo)]

pop3 <- pop3[, .(age_bin, ym, population)]
setorder(pop3, age_bin, ym)

stopifnot(anyDuplicated(pop3, by = c("age_bin", "ym")) == 0L)
stopifnot(!anyNA(pop3$population), all(pop3$population >= 0))

atomic_saveRDS(pop3, file.path(DATA, "population_by_agebin_ym.rds"))

cat(sprintf("Population dataset: %d (age_bin x ym) rows saved to population_by_agebin_ym.rds\n",
            nrow(pop3)))
cat(sprintf("  population range: %s to %s\n",
            fmt_int(min(pop3$population)), fmt_int(max(pop3$population))))
cat(sprintf("  unique months: %d, unique age_bins: %d\n",
            uniqueN(pop3$ym), uniqueN(pop3$age_bin)))
cat("== 5b_population.R done ", format(Sys.time()), " ==\n")
close_log()
