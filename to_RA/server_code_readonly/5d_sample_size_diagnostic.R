# =============================================================================
# 5d_sample_size_diagnostic.R : how much of the cohort does headline_priv catch
# =============================================================================
# Counts unique persons at the reference month (October 2022) under
# increasingly restrictive sample filters, so the local analyst can see how
# much of the cohort population is excluded at each step.
#
# Stages:
#   01_all_21_60         all employed in [AGE_MIN, AGE_MAX] (any sector)
#   02_sekt3_private     + sekt = 3 (private)
#   03_sekt3_frtk_min    + foretak has >= FRTK_MIN_ACTIVE unique workers
#                          at the reference month
#   04_headline_priv     + foretak in in_headline_priv (balanced panel)
#   05_hp_mapped         + person has >= 1 spell with Eloundou-mapped yrke4
#                          (= the regression sample)
#   06_hp_yrke0000       headline_priv persons with NO mapped spell, >= 1
#                          spell with yrke4 == "0000" (unknown occupation)
#   07_hp_other_unmapped headline_priv persons with NO mapped spell, no 0000,
#                          only unmapped non-zero yrke4 (military, clergy, ...)
#
# Stages 05+06+07 sum to stage 04 (asserted).
#
# Inputs:  $DATA/ameld_filt_{REF_Y}_m{REF_M}.rds   (from script 3)
#          $DATA/cells_flagged.rds                  (from script 5)
#          $DATA/population_by_agebin_ym.rds        (from 5b)
#          $DATA/exposure.rds                       (from script 1)
# Outputs: $DIAG/sample_size_diagnostic.csv
#          log_5d_sample_size_diagnostic.txt
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("data.table")

open_log("5d_sample_size_diagnostic")
cat("== 5d_sample_size_diagnostic.R starting ", format(Sys.time()), " ==\n")

filt_path <- file.path(DATA, sprintf("ameld_filt_%d_m%d.rds", REF_Y, REF_M))
if (!file.exists(filt_path))
    stop(filt_path, " not found; rerun 3_monthly_filtered.R.")

w <- readRDS(filt_path); setDT(w)

pop <- load_population()[ym == YM_REF, .(age_bin, population)]

headline_firms <- unique(load_cells()[in_headline_priv == 1L, .(lopenr_foretak)])

expo <- readRDS(file.path(DATA, "exposure.rds")); setDT(expo)

# Count unique persons per age_bin (a person has one age_bin per month but
# possibly several spells).
count_stage <- function(dt, stage) {
    u <- unique(dt[, .(lopenr_person, age_bin)])
    u[, .(stage = stage, n_persons = .N), keyby = age_bin]
}

rows <- list()

# --- Stage 1: all employed 21-60 at reference month ---------------------------
rows[["01"]] <- count_stage(w, "01_all_21_60")

# --- Stage 2: + private sector -------------------------------------------------
w3 <- w[sekt == 3L]
rows[["02"]] <- count_stage(w3, "02_sekt3_private")

# --- Stage 3: + foretak with >= FRTK_MIN_ACTIVE unique workers this month -----
# (a person can hold several spells in the same foretak -- count persons once)
frtk_size <- w3[, .(n_pers = uniqueN(lopenr_person)), by = lopenr_foretak]
big_firms <- frtk_size[n_pers >= FRTK_MIN_ACTIVE, .(lopenr_foretak)]
rows[["03"]] <- count_stage(w3[big_firms, on = "lopenr_foretak", nomatch = NULL],
                            "03_sekt3_frtk_min")

# --- Stage 4: + foretak in the balanced headline_priv panel --------------------
w4 <- w3[headline_firms, on = "lopenr_foretak", nomatch = NULL]
rows[["04"]] <- count_stage(w4, "04_headline_priv")

# --- Stages 5-7: split headline_priv persons by Eloundou-mapping coverage ----
w4[, mapped  := as.integer(yrke4 %chin% expo$yrke4)]
w4[, is_0000 := as.integer(yrke4 == "0000")]

per_pers <- w4[, .(any_mapped = max(mapped), any_0000 = max(is_0000),
                   age_bin = age_bin[1L]), by = lopenr_person]
per_pers[, category := fcase(any_mapped == 1L,                  1L,
                             any_mapped == 0L & any_0000 == 1L, 2L,
                             default = 3L)]
stopifnot(!anyNA(per_pers$category))

rows[["05"]] <- per_pers[category == 1L,
                         .(stage = "05_hp_mapped", n_persons = .N), keyby = age_bin]
rows[["06"]] <- per_pers[category == 2L,
                         .(stage = "06_hp_yrke0000", n_persons = .N), keyby = age_bin]
rows[["07"]] <- per_pers[category == 3L,
                         .(stage = "07_hp_other_unmapped", n_persons = .N), keyby = age_bin]

out <- rbindlist(rows, use.names = TRUE)

# Stages 05+06+07 must reproduce stage 04 exactly, per age_bin.
chk <- merge(
    out[stage %in% c("05_hp_mapped", "06_hp_yrke0000", "07_hp_other_unmapped"),
        .(n_split = sum(n_persons)), by = age_bin],
    out[stage == "04_headline_priv", .(age_bin, n_04 = n_persons)],
    by = "age_bin"
)
stopifnot(all(chk$n_split == chk$n_04))

# --- Merge population, compute rate, export -----------------------------------
out[pop, on = "age_bin", population := i.population]
out[, rate := n_persons / population]
setorder(out, stage, age_bin)
setcolorder(out, c("stage", "age_bin", "n_persons", "population", "rate"))

cat(sprintf("\nSample-size diagnostic at ym = %d (%dm%d):\n", YM_REF, REF_Y, REF_M))
print(out, nrows = 200)

fwrite(out, file.path(DIAG, "sample_size_diagnostic.csv"))
cat("\nScript 5d complete. Diagnostic written to diagnostics/sample_size_diagnostic.csv.\n")
cat("== 5d_sample_size_diagnostic.R done ", format(Sys.time()), " ==\n")
close_log()
