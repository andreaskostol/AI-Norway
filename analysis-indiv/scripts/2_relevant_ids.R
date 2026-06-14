# =============================================================================
# 2_relevant_ids.R : people who can be aged 21-60 in some month of the panel
# =============================================================================
# Inputs:  faste_oppl.dta (FASTE_OPPL_PATH; person key handled defensively --
#          the 1191 delivery names it w19_0345_lopenr_person, see
#          datadoc/inkonsekvenser_1191.md section 1)
# Outputs: $DATA/relevant_ids.rds   (one row per person, with fm)
#          fragment section_03 + rebuilt SECURE_SERVER_RESULTS.md
#          log_2_relevant_ids.txt
#
# A person is aged a in calendar year y if foedselsaar = y - a. So someone
# aged AGE_MIN-AGE_MAX in any month of the panel is born between
#   PERIOD_START_Y - AGE_MAX   (would be AGE_MAX in the first panel year) and
#   PERIOD_END_Y   - AGE_MIN   (would be AGE_MIN in the last panel year).
#
# (The 1183 pipeline called this file relevant_ids_2255.dta -- a stale name
# from the original 22-55 window; renamed in the R port.)
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("haven"); req("data.table")

open_log("2_relevant_ids")
cat("== 2_relevant_ids.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Section 1: Load the demographic file and filter cohorts
# -----------------------------------------------------------------------------

d <- read_faste_oppl(c("foedselsaar", "foedsels_aar_mnd", "doeds_aar_mnd", "kjoenn"))
cat(sprintf("faste_oppl loaded: %s rows\n", fmt_int(nrow(d))))

# Year/month fields are str8 in the 1191 delivery ("" = missing, e.g.
# doeds_aar_mnd for the living). Convert loudly: any NON-empty value that
# fails integer conversion is a data problem, not a missing.
to_int <- function(x, what) {
    x <- trimws(x)
    x[x == ""] <- NA
    out <- suppressWarnings(as.integer(x))
    n_bad <- sum(!is.na(x) & is.na(out))
    if (n_bad > 0)
        stop(n_bad, " non-empty values of ", what, " failed integer conversion.")
    out
}
d[, foedselsaar      := to_int(foedselsaar,      "foedselsaar")]
d[, foedsels_aar_mnd := to_int(foedsels_aar_mnd, "foedsels_aar_mnd")]
d[, doeds_aar_mnd    := to_int(doeds_aar_mnd,    "doeds_aar_mnd")]

# Cohort range: born between (period_start_y - age_max) and (period_end_y - age_min)
cohort_min <- PERIOD_START_Y - AGE_MAX
cohort_max <- PERIOD_END_Y   - AGE_MIN
d <- d[!is.na(foedselsaar) & foedselsaar >= cohort_min & foedselsaar <= cohort_max]

# One row per person (faste_oppl can have duplicates). Stata sorted on
# (lopenr_person, foedsels_aar_mnd) with missing LAST and kept the first row;
# na.last = TRUE replicates that.
setorder(d, lopenr_person, foedsels_aar_mnd, na.last = TRUE)
d <- unique(d, by = "lopenr_person")

# Female indicator (kjoenn is "1"/"2" string)
d[, kvinne := as.integer(trimws(kjoenn) == "2")]
d[, kjoenn := NULL]

# Birth month index for fast age-in-months calculation downstream:
#   fm = ym(foedselsaar, birth_mo);  age in months at calendar month t: t - fm
d[, birth_mo := foedsels_aar_mnd - foedselsaar * 100L]
n_bad_mo <- d[is.na(birth_mo) | birth_mo < 1 | birth_mo > 12, .N]
if (n_bad_mo > 0) {
    cat(sprintf("  Dropping %d persons with invalid birth_mo (outside [1,12]).\n", n_bad_mo))
    d <- d[!is.na(birth_mo) & birth_mo >= 1 & birth_mo <= 12]
}
d[, fm := ym(foedselsaar, birth_mo)]

d <- d[, .(lopenr_person, foedselsaar, birth_mo, kvinne, fm, doeds_aar_mnd)]
stopifnot(anyDuplicated(d$lopenr_person) == 0L)   # one row per person
atomic_saveRDS(d, file.path(DATA, "relevant_ids.rds"))

n_rel <- nrow(d)
cat(sprintf("Relevant IDs: %s persons (born %d - %d), saved to relevant_ids.rds\n",
            fmt_int(n_rel), cohort_min, cohort_max))

# -----------------------------------------------------------------------------
# Section 2: Fragment §3 -- cohort-size distribution
# -----------------------------------------------------------------------------

cohorts <- d[, .N, keyby = foedselsaar]
write_fragment("03", c(
    "## §3: Sample IDs",
    "",
    sprintf(paste("Persons with a chance of being aged %d--%d in some month of",
                  "the panel (born %d -- %d). Built once from %s; all monthly",
                  "loads join against this file."),
            AGE_MIN, AGE_MAX, cohort_min, cohort_max, FASTE_OPPL_PATH),
    "",
    "| Birth year | N |",
    "|---:|---:|",
    sprintf("| %d | %s |", cohorts$foedselsaar, fmt_int(cohorts$N)),
    sprintf("| **Total** | **%s** |", fmt_int(n_rel)),
    "",
    "---",
    ""
))
rebuild_results_md()

cat("Wrote section_03 fragment; rebuilt", RESULTS_MD, "\n")
cat("== 2_relevant_ids.R done ", format(Sys.time()), " ==\n")
close_log()
