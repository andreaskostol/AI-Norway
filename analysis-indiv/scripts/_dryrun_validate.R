# =============================================================================
# _dryrun_validate.R : validate every raw-data reference against the metadata
#                      scan of W:\1191 -- BEFORE transferring to the server
# =============================================================================
# Runs LOCALLY in the repo (recommended by datadoc/inkonsekvenser_1191.md):
#
#   Rscript analysis-indiv/scripts/_dryrun_validate.R
#
# Checks, against analysis-indiv/datadoc/metadata_scan1191.csv:
#   1. Every ameld_statdata month file of the panel exists at the CANONICAL
#      path (W:/1191/atid/, never atid/old/), with all 12 columns script 3
#      reads, with the expected types.
#   2. faste_oppl.dta exists at W:/1191/demo/ with the person key (either
#      lopenr_person or w19_0345_lopenr_person) and the demographic columns
#      script 2 reads.
#   3. Collision scan: target filenames that ALSO exist in old/Old/_bak dirs
#      (informational -- the pipeline always uses full canonical paths).
#   4. nobs sanity ranges (a truncated delivery should be caught here).
#
# Any FAIL stops with nonzero exit; the transfer should not happen until this
# script is all-PASS. Re-run after every new W:\1191 delivery (rescan with
# datadoc/scan_metadata.do on the server first).
#
# The period and column lists come from 0_settings.R, sourced with
# AI_NORWAY_TEST_ROOT pointed at a tempdir so no H:/F:/W: paths are touched
# locally. The canonical W:-path strings are pinned HERE -- this script is
# the contract between the pipeline's path constants and the actual delivery.
# =============================================================================

suppressMessages(library(data.table))

# --- Locate the repo (script lives in analysis-indiv/scripts/) ---------------
cmd_args   <- commandArgs(trailingOnly = FALSE)
file_arg   <- grep("^--file=", cmd_args, value = TRUE)
script_dir <- if (length(file_arg) > 0) {
    dirname(normalizePath(sub("^--file=", "", file_arg[1])))
} else {
    getwd()   # interactive use: assume wd = analysis-indiv/scripts
}

META_PATH <- normalizePath(file.path(script_dir, "..", "datadoc",
                                     "metadata_scan1191.csv"), mustWork = FALSE)
if (!file.exists(META_PATH))
    stop("metadata_scan1191.csv not found at ", META_PATH,
         " -- run this script from the repo (it is local-only).")

# --- Source settings without local side effects ------------------------------
Sys.setenv(AI_NORWAY_TEST_ROOT = file.path(tempdir(), "ai_norway_dryrun"))
source(file.path(script_dir, "0_settings.R"))
Sys.unsetenv("AI_NORWAY_TEST_ROOT")

# Canonical server-side locations (the contract being validated).
W_AMELD_DIR  <- "W:/1191/atid"
W_FASTE_OPPL <- "W:/1191/demo/faste_oppl.dta"

# Cross-check that 0_settings.R still points at the same universe.
settings_src <- readLines(file.path(script_dir, "0_settings.R"))
if (!any(grepl('"W:/1191"', settings_src, fixed = TRUE)))
    stop("0_settings.R no longer contains the literal \"W:/1191\" -- ",
         "update W_AMELD_DIR/W_FASTE_OPPL in this validator to match.")

# --- Load + normalize the metadata scan --------------------------------------
# fill=Inf: the scan contains a handful of malformed rows (the scanner's
# encoding-error fallback duplicates the fields unquoted, e.g. atmlto1992).
# Their first 8 fields are still the correct quoted values; extra columns are
# dropped below.
meta <- suppressWarnings(fread(META_PATH, encoding = "UTF-8", fill = Inf))
stopifnot(all(c("filepath", "filename", "nobs", "varname", "vartype", "format")
              %in% names(meta)))
meta <- meta[, .(filepath, filename, nobs, nvar, varname, vartype, format, varlabel)]
meta <- meta[grepl("^W:", filepath) & nzchar(varname)]
meta[, filepath := gsub("\\\\", "/", filepath)]
meta <- unique(meta, by = c("filepath", "varname"))   # scan contains duplicate blocks

# --- Expected types -----------------------------------------------------------
AMELD_TYPES <- c(
    lopenr_person      = "str10",  lopenr_foretak     = "str10",
    arb_yrke           = "str8",   frtk_sektor_2014   = "str4",
    lonn_kontant       = "double", arb_stillingspst   = "double",
    arb_arbeidstid     = "double", lonn_overtid_timer = "double",
    lonn_fast          = "double", lonn_time          = "double",
    lonn_time_antall   = "double", arb_start          = "long"
)
stopifnot(setequal(names(AMELD_TYPES), AMELD_COLS))
FASTE_TYPES <- c(
    foedselsaar = "str8", foedsels_aar_mnd = "str8",
    doeds_aar_mnd = "str8", kjoenn = "str2"
)

# --- Result collector ---------------------------------------------------------
results <- list()
add <- function(status, what, detail = "") {
    results[[length(results) + 1L]] <<- data.table(
        status = status, what = what, detail = detail)
    if (status != "PASS")
        cat(sprintf("%-4s %-55s %s\n", status, what, detail))
}

# =============================================================================
# Check 1: ameld month files
# =============================================================================
mg <- month_grid()
for (i in seq_len(nrow(mg))) {
    y <- mg$y[i]; m <- mg$m[i]
    path  <- sprintf("%s/ameld_statdata_%d_m%d.dta", W_AMELD_DIR, y, m)
    label <- sprintf("ameld %d m%-2d", y, m)
    fm    <- meta[filepath == path]

    if (nrow(fm) == 0) { add("FAIL", label, paste("not in scan:", path)); next }

    miss <- setdiff(AMELD_COLS, fm$varname)
    if (length(miss) > 0) {
        add("FAIL", label, paste("missing cols:", paste(miss, collapse = ", ")))
        next
    }
    ok <- TRUE
    for (v in AMELD_COLS) {
        vt <- fm[varname == v, vartype][1]
        if (vt != AMELD_TYPES[[v]]) {
            add("WARN", label, sprintf("%s is %s (expected %s)",
                                       v, vt, AMELD_TYPES[[v]]))
            ok <- FALSE
        }
    }
    fmtd <- fm[varname == "arb_start", format][1]
    if (!grepl("^%t?d", fmtd)) {
        add("WARN", label,
            sprintf("arb_start format is %s (expected %%d date) -- haven will NOT read it as Date", fmtd))
        ok <- FALSE
    }
    n <- fm$nobs[1]
    if (is.na(n) || n < 4e6 || n > 8e6) {
        add("WARN", label, sprintf("nobs = %s outside sanity range [4M, 8M]",
                                   format(n, big.mark = ",")))
        ok <- FALSE
    }
    if (ok) add("PASS", label, format(n, big.mark = ","))
}

# =============================================================================
# Check 2: faste_oppl
# =============================================================================
fo <- meta[filepath == W_FASTE_OPPL]
if (nrow(fo) == 0) {
    add("FAIL", "faste_oppl", paste("not in scan:", W_FASTE_OPPL))
} else {
    ids <- intersect(c("lopenr_person", "w19_0345_lopenr_person"), fo$varname)
    if (length(ids) == 0) {
        add("FAIL", "faste_oppl", "no person key (lopenr_person / w19_0345_lopenr_person)")
    } else {
        add("PASS", "faste_oppl person key", ids[1])
    }
    miss <- setdiff(names(FASTE_TYPES), fo$varname)
    if (length(miss) > 0) {
        add("FAIL", "faste_oppl", paste("missing cols:", paste(miss, collapse = ", ")))
    } else {
        for (v in names(FASTE_TYPES)) {
            vt <- fo[varname == v, vartype][1]
            if (vt != FASTE_TYPES[[v]])
                add("WARN", "faste_oppl", sprintf(
                    "%s is %s (expected %s) -- check the as.integer conversion in 2_relevant_ids.R",
                    v, vt, FASTE_TYPES[[v]]))
        }
        add("PASS", "faste_oppl columns", sprintf("nobs = %s", format(fo$nobs[1], big.mark = ",")))
    }
    n <- fo$nobs[1]
    if (is.na(n) || n < 9e6)
        add("WARN", "faste_oppl", sprintf("nobs = %s < 9M", format(n, big.mark = ",")))
}

# =============================================================================
# Check 3: collision scan -- our filenames in backup dirs (informational)
# =============================================================================
target_files <- c(sprintf("ameld_statdata_%d_m%d.dta", mg$y, mg$m), "faste_oppl.dta")
coll <- meta[filename %in% target_files &
             grepl("/old/|/Old/|_bak/", filepath),
             unique(filepath)]
if (length(coll) > 0) {
    add("INFO", "backup-dir collisions",
        sprintf("%d stale same-named file(s) exist (pipeline uses canonical paths): %s%s",
                length(coll), paste(head(coll, 3), collapse = "; "),
                if (length(coll) > 3) " ..." else ""))
}

# =============================================================================
# Check 4 (info): arb_yrke_styrk08 availability for the crosswalk cross-check
# =============================================================================
s08 <- meta[varname == "arb_yrke_styrk08" & grepl("ameld_statdata_", filename) &
            !grepl("/old/", filepath)]
if (nrow(s08) > 0) {
    yrs <- range(as.integer(gsub("^ameld_statdata_(\\d{4})_m\\d+\\.dta$", "\\1",
                                 s08$filename)))
    add("INFO", "arb_yrke_styrk08",
        sprintf("present in ameld %d-%d (log-only cross-check of the yrke7 crosswalk)",
                yrs[1], yrs[2]))
}

# =============================================================================
# Summary (also written as CSV next to the metadata scan it validated, as
# machine-readable evidence for the transfer)
# =============================================================================
res <- rbindlist(results)
res_path <- file.path(dirname(META_PATH), "dryrun_validate.csv")
fwrite(res, res_path)

n_fail <- sum(res$status == "FAIL")
n_warn <- sum(res$status == "WARN")
n_pass <- sum(res$status == "PASS")

cat(sprintf("\n== Dry-run validation: %d PASS, %d WARN, %d FAIL (of %d checks) ==\n",
            n_pass, n_warn, n_fail, nrow(res)))
cat(sprintf("   metadata: %s\n   results:  %s\n   period:   %dm%d - %dm%d (%d months)\n",
            META_PATH, res_path, PERIOD_START_Y, PERIOD_START_M,
            PERIOD_END_Y, PERIOD_END_M, nrow(mg)))

if (n_fail > 0) stop(n_fail, " FAIL -- do not transfer; fix the references or rescan the delivery.")
if (n_warn > 0) cat("WARNs above need a manual look before the server run.\n")
if (n_fail == 0 && n_warn == 0) cat("All clear -- safe to transfer.\n")
