# =============================================================================
# 1b_load_styrk7_crosswalk.R : 7-digit STYRK -> 4-digit STYRK-08 crosswalk
# =============================================================================
# Imports occupations_7digits_4digits.csv (semicolon-delimited) and saves it
# as .rds for script 3 to join against. Replaces the substr(yrke7, 1, 4)
# shortcut, which is WRONG for codes where the Norwegian 7-digit hierarchy
# doesn't line up with the 4-digit STYRK-08 unit groups (e.g. military:
# 7-digit "0111101" maps to 4-digit "0310", not "0111").
#
# Inputs:  $DATA/occupations_7digits_4digits.csv  (transfer from local
#                                                  analysis-indiv/)
# Outputs: $DATA/styrk7_to_styrk4.rds             (yrke7, yrke4)
#          log_1b_load_styrk7_crosswalk.txt
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("data.table")

open_log("1b_load_styrk7_crosswalk")
cat("== 1b_load_styrk7_crosswalk.R starting ", format(Sys.time()), " ==\n")

csv_path <- file.path(DATA, "occupations_7digits_4digits.csv")
if (!file.exists(csv_path))
    stop(csv_path, " not found. Transfer the file from local analysis-indiv\\.")

# Columns in the CSV: sourceCode;sourceName;targetCode;targetName (camelCase --
# Stata's import delimited lowercased them, fread does not).
cw <- fread(csv_path, sep = ";", colClasses = "character")
setnames(cw, tolower(names(cw)))
stopifnot(all(c("sourcecode", "targetcode") %in% names(cw)))

cw <- cw[, .(yrke7 = trimws(sourcecode), yrke4 = trimws(targetcode))]

# Sanity checks: every row should be a 7-digit -> 4-digit mapping. Warn and
# show the offending rows rather than stop (matches the Stata script; the
# current file is clean).
bad7 <- cw[nchar(yrke7) != 7]
if (nrow(bad7) > 0) {
    cat(sprintf("WARNING: %d rows have yrke7 not exactly 7 chars:\n", nrow(bad7)))
    print(bad7)
}
bad4 <- cw[nchar(yrke4) != 4]
if (nrow(bad4) > 0) {
    cat(sprintf("WARNING: %d rows have yrke4 not exactly 4 chars:\n", nrow(bad4)))
    print(bad4)
}

cw <- unique(cw, by = "yrke7")
setorder(cw, yrke7)

# The reason this crosswalk exists at all: codes where substr(yrke7, 1, 4)
# is wrong. Verify the canonical example explicitly.
stopifnot(cw[yrke7 == "0111101", yrke4] == "0310")
stopifnot(anyDuplicated(cw$yrke7) == 0L)

atomic_saveRDS(cw, file.path(DATA, "styrk7_to_styrk4.rds"))
cat(sprintf("Crosswalk loaded: %d unique yrke7 -> yrke4 mappings saved to styrk7_to_styrk4.rds\n",
            nrow(cw)))
cat("== 1b_load_styrk7_crosswalk.R done ", format(Sys.time()), " ==\n")
close_log()
