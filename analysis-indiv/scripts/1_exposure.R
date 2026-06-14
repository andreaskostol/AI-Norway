# =============================================================================
# 1_exposure.R : load STYRK-08 exposure CSV, build quintile + standardized score
# =============================================================================
# Inputs:  $DATA/styrk08_eloundou_beta_mapping.csv (transferred from the main
#                                       project's data/ai_exposure/ directory;
#                                       built by analysis/03_mappings/build_eloundou_mapping.py)
# Outputs: $DATA/exposure.rds            (yrke4, ai_q, exposure_score, exposure_std)
#          fragments section_00/01/02 + rebuilt SECURE_SERVER_RESULTS.md
#          log_1_exposure.txt
#
# Mapping coverage: 397 STYRK-08 codes. Crosswalk: O*NET-SOC 2018 -> SOC 2010
# -> ISCO-08 = STYRK-08 (4-digit). Manual maps: 2223 Sykepleiere <- ISCO 2221
# (RN proxy); 2224 Vernepleiere <- 2221 (imperfect proxy, flagged manual_map).
# Codes not covered (~9, ~0.5% of worker-months): military 0110/0210, clergy
# 3413, small specialty codes, plus missing-code 0000.
#
# The 7-digit -> 4-digit STYRK-08 reduction happens in script 3 via the
# Norwegian crosswalk (loaded by 1b_load_styrk7_crosswalk.R). substr(yrke7,
# 1, 4) is NOT a valid shortcut (military "0111101" -> "0310", not "0111").
#
# Design rationale: DESIGN_CHOICES.md section 14 (why this mapping file).
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("data.table")

open_log("1_exposure")
cat("== 1_exposure.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Section 1: Load Eloundou exposure, build quintile + standardized score
# -----------------------------------------------------------------------------
# CSV columns: styrk08 (4-digit, leading zeros!), eloundou_beta, pctl_rank,
# quintile (precomputed 1-5, equal-occupation), n_soc_matched,
# has_partial_match, max_partial_fanout, manual_map.

csv_path <- file.path(DATA, "styrk08_eloundou_beta_mapping.csv")
if (!file.exists(csv_path))
    stop(csv_path, " not found. Transfer it from data/ai_exposure/.")

exp <- fread(csv_path, colClasses = c(styrk08 = "character"))
stopifnot(all(c("styrk08", "eloundou_beta", "quintile") %in% names(exp)))

# yrke4 as zero-padded 4-character string for merging downstream
exp[, yrke4 := pad0(styrk08, 4)]

exp[, exposure_score := eloundou_beta]
exp <- exp[!is.na(exposure_score)]

# Initial standardization over the occupation universe (mean 0, SD 1 across
# mapped STYRK codes). Script 4 overwrites exposure_std with an
# employment-weighted standardization computed on the balanced + active panel.
exp[, exposure_std := (exposure_score - mean(exposure_score)) / sd(exposure_score)]

# Quintiles (1 = least exposed, 5 = most). Equal-occupation, precomputed in
# the mapping file and matching the existing paper/ convention.
exp[, ai_q := as.integer(quintile)]
stopifnot(all(exp$ai_q %in% 1:5))

# Quintile cutoff maxima for the markdown table
q_max <- exp[, .(max_exp = max(exposure_score)), keyby = ai_q]

exp <- exp[, .(yrke4, ai_q, exposure_score, exposure_std)]
setorder(exp, yrke4)
exp <- unique(exp, by = "yrke4")
stopifnot(anyDuplicated(exp$yrke4) == 0L)   # exposure must be unique per yrke4
                                            # (script 4 joins on it post-collapse)

atomic_saveRDS(exp, file.path(DATA, "exposure.rds"))
n_exp <- nrow(exp)
cat(sprintf("Exposure: %d STYRK-08 codes mapped, saved to exposure.rds\n", n_exp))

# -----------------------------------------------------------------------------
# Section 2: Write markdown fragments 00/01/02 + rebuild master .md
# -----------------------------------------------------------------------------

# --- section_00.md : header ---
write_fragment("00", c(
    "# AI-Norway: firm-FE triple-difference and event study",
    "",
    paste("Self-contained results document built by scripts/1_exposure.R through",
          "scripts/8_alt_outcomes_feols.R (R-only pipeline on data universe 1191).",
          "Coefficient series in coefficients/coef_*.csv; per-script logs in log_*.txt."),
    "",
    "## Open issues for Hernæs / Kostøl",
    "",
    paste("1. Headline picks: which sample, which exposure, which age binning",
          "go in the manuscript headline."),
    "2. Public vs private split: report both, or only the all-sector headline?",
    paste("3. Specification reconciliation: interpret the gaps decomposed by 7d",
          "(firm-FE vs cell spec on identical data; ≥20-restriction; data source",
          "vs microdata.no) -- see coef_did_byage_cellspec.csv."),
    "",
    "---",
    ""
))

# --- section_01.md : §1 Run metadata ---
pkg_ver <- function(p) as.character(utils::packageVersion(p))
write_fragment("01", c(
    "## §1: Run metadata",
    "",
    sprintf("- %s; haven %s, data.table %s, fixest %s",
            R.version.string, pkg_ver("haven"), pkg_ver("data.table"),
            pkg_ver("fixest")),
    sprintf("- Run date: %s", format(Sys.time(), "%Y-%m-%d %H:%M:%S")),
    sprintf("- Data universe: 1191 (raw A-meldingen at %s)", AMELD_DIR),
    sprintf("- Period: %dm%d -- %dm%d", PERIOD_START_Y, PERIOD_START_M,
            PERIOD_END_Y, PERIOD_END_M),
    sprintf("- Reference month: %dm%d (event time k = -1); event window k in [%d, %d]",
            REF_Y, REF_M, KMIN, KMAX),
    sprintf("- Age window: %d -- %d (decade bins)", AGE_MIN, AGE_MAX),
    sprintf("- Young / Older binary cut: %d -- %d vs %d -- %d",
            AGE_MIN, YOUNG_MAX, YOUNG_MAX + 1, AGE_MAX),
    sprintf(paste("- BCC restriction thresholds: ≥ %d workers per (firm, age)",
                  "every month; Σ ≥ %d per (firm, q, age) cell"),
            BCC_MIN_PER_AGE, BCC_MIN_TOTAL),
    "- Firm dimension: foretak (lopenr_foretak)",
    "",
    "---",
    ""
))

# --- section_02.md : §2 Exposure construction ---
write_fragment("02", c(
    "## §2: Exposure construction",
    "",
    paste("Source: data/ai_exposure/styrk08_eloundou_beta_mapping.csv (Eloundou",
          "et al. GPT-4 beta, averaged through O*NET-SOC 2018 -> SOC 2010 ->",
          "ISCO-08 = STYRK-08). Quintiles: equal-occupation (each STYRK-08",
          "4-digit code counts once), precomputed in the mapping file.",
          "Continuous exposure standardized to mean 0, SD 1 across mapped codes",
          "(re-standardized employment-weighted in script 4). Coverage: 397",
          "STYRK-08 codes; ~9 codes (military, clergy, small specialty) without",
          "SOC analog are dropped (~0.5% of worker-months)."),
    "",
    "| Quantity | Value |",
    "|---|---|",
    sprintf("| STYRK-08 codes mapped | %d |", n_exp),
    sprintf("| Q%d cutoff (max exposure) | %.3f |", q_max$ai_q, q_max$max_exp),
    "",
    "---",
    ""
))

rebuild_results_md()
cat("Wrote sections 00, 01, 02; rebuilt", RESULTS_MD, "\n")
cat("== 1_exposure.R done ", format(Sys.time()), " ==\n")
close_log()
