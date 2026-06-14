# =============================================================================
# 5_apply_restrictions.R : tag cells for the sample variants
# =============================================================================
# Reads cells.rds, adds binary flags for each sample, saves cells_flagged.rds.
#
# Inputs:  $DATA/cells.rds
# Outputs: $DATA/cells_flagged.rds
#          fragment section_06 + rebuilt SECURE_SERVER_RESULTS.md
#          log_5_apply_restrictions.txt
#
# Sample definitions
# ------------------
#   in_headline      : every cell in the balanced panel. All sectors, FT+PT.
#   in_headline_priv : in_headline AND sekt == 3 (private). The MAIN sample
#                      for scripts 6-8 and the 7b/7d comparison.
#   in_ft            : the (foretak, age_bin, yrke4) cell had at least one
#                      FT-positive observation at some point (incl. synthetic
#                      zero-FT rows, so firm x time FE see FT exits as zeros).
#   in_ft_priv       : in_ft AND private.
#   in_bcc_full      : in_ft_priv AND the BCC cell-presence rules:
#                        (a) per (firm, age): >= BCC_MIN_PER_AGE FT workers
#                            EVERY month of the panel;
#                        (b) per (firm, q, age): sum_t count_ft >= BCC_MIN_TOTAL.
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("data.table")

open_log("5_apply_restrictions")
cat("== 5_apply_restrictions.R starting ", format(Sys.time()), " ==\n")

d <- readRDS(file.path(DATA, "cells.rds"))
setDT(d)
cat(sprintf("cells.rds: %s rows\n", fmt_int(nrow(d))))

# -----------------------------------------------------------------------------
# Section 1: Headline and FT flags
# -----------------------------------------------------------------------------

d[, in_headline := 1L]
d[, in_headline_priv := as.integer(sekt == 3L)]

d[, in_ft := as.integer(any(count_ft > 0)),
  by = .(lopenr_foretak, age_bin, yrke4)]
d[, in_ft_priv := as.integer(in_ft == 1L & sekt == 3L)]

# -----------------------------------------------------------------------------
# Section 2: BCC-full restriction (both rules on the FT/private subset)
# -----------------------------------------------------------------------------

panel_length <- uniqueN(d$ym)
cat(sprintf("Panel length (distinct months in data): %d\n", panel_length))

ftp <- d[in_ft_priv == 1L]

# (a) Firm-age presence with >= BCC_MIN_PER_AGE FT workers every period.
#     Sum count_ft to (firm, age_bin, ym) first, then check the minimum and
#     that the firm-age is present in all panel months.
fa <- ftp[, .(count_ft_fa = sum(count_ft)), by = .(lopenr_foretak, age_bin, ym)]
fa <- fa[, .(fa_pass = as.integer(min(count_ft_fa) >= BCC_MIN_PER_AGE &
                                  .N == panel_length)),
         by = .(lopenr_foretak, age_bin)]
d[fa, on = c("lopenr_foretak", "age_bin"), fa_pass := i.fa_pass]
d[is.na(fa_pass), fa_pass := 0L]

# (b) Per (firm, q, age) cell: sum_t count_ft >= BCC_MIN_TOTAL.
fqa <- ftp[, .(sum_ft = sum(count_ft)), by = .(lopenr_foretak, age_bin, ai_q)]
fqa[, fqa_pass := as.integer(sum_ft >= BCC_MIN_TOTAL)]
d[fqa, on = c("lopenr_foretak", "age_bin", "ai_q"), fqa_pass := i.fqa_pass]
d[is.na(fqa_pass), fqa_pass := 0L]

d[, in_bcc_full := as.integer(in_ft_priv == 1L & fa_pass == 1L & fqa_pass == 1L)]
d[, c("fa_pass", "fqa_pass") := NULL]
rm(ftp, fa, fqa); invisible(gc(verbose = FALSE))

# Nesting relations that hold by construction -- verify them.
stopifnot(all(d$in_headline_priv <= d$in_headline))
stopifnot(all(d$in_ft_priv       <= d$in_ft))
stopifnot(all(d$in_bcc_full      <= d$in_ft_priv))

# -----------------------------------------------------------------------------
# Section 3: Save and report
# -----------------------------------------------------------------------------

atomic_saveRDS(d, file.path(DATA, "cells_flagged.rds"))
cat("cells_flagged.rds saved.\n")

# Per sample: cells, distinct foretak, worker-months (count_all for the
# headline samples, count_ft for the FT-based samples).
sample_stats <- function(flag, count_col) {
    s <- d[get(flag) == 1L]
    list(cells = nrow(s), frtk = uniqueN(s$lopenr_foretak),
         wm = sum(s[[count_col]]))
}
st_h   <- sample_stats("in_headline",      "count_all")
st_hp  <- sample_stats("in_headline_priv", "count_all")
st_ft  <- sample_stats("in_ft",            "count_ft")
st_ftp <- sample_stats("in_ft_priv",       "count_ft")
st_bcc <- sample_stats("in_bcc_full",      "count_ft")

# Machine-readable counterpart of the §6 fragment.
atomic_fwrite(data.table(
    sample = c("headline", "headline_priv", "ft", "ft_priv", "bcc_full"),
    cells = c(st_h$cells, st_hp$cells, st_ft$cells, st_ftp$cells, st_bcc$cells),
    n_frtk = c(st_h$frtk, st_hp$frtk, st_ft$frtk, st_ftp$frtk, st_bcc$frtk),
    worker_months = c(st_h$wm, st_hp$wm, st_ft$wm, st_ftp$wm, st_bcc$wm)
), file.path(DIAG, "restriction_funnel.csv"))
cat("Wrote diagnostics/restriction_funnel.csv\n")

row_md <- function(label, st, bold = FALSE) {
    f <- if (bold) function(x) sprintf("**%s**", fmt_int(x)) else fmt_int
    sprintf("| %s | %s | %s | %s |", label, f(st$cells), f(st$frtk), f(st$wm))
}

write_fragment("06", c(
    "## §6: Restriction-step counts",
    "",
    paste("Sample variants. The main run uses headline_priv (all FT/PT in",
          "private foretak). Other variants are tagged in cells_flagged.rds",
          "and can be re-enabled in scripts 6-8 for robustness."),
    "",
    "| Sample | Cells | Distinct foretak | Worker-months |",
    "|---|---:|---:|---:|",
    row_md("Headline (all sectors, FT+PT)", st_h),
    row_md("**Headline x private (main run)**", st_hp, bold = TRUE),
    row_md("FT only", st_ft),
    row_md("FT + private only", st_ftp),
    row_md(sprintf("BCC full (FT + priv + ≥%d every period + Σ ≥ %d)",
                   BCC_MIN_PER_AGE, BCC_MIN_TOTAL), st_bcc),
    "",
    paste("Worker-months use count_all for headline samples and count_ft for",
          "the FT-based samples."),
    "",
    "---",
    ""
))
rebuild_results_md()

cat("\nScript 5 complete. Sample flags attached; section_06 fragment rebuilt.\n")
cat("== 5_apply_restrictions.R done ", format(Sys.time()), " ==\n")
close_log()
