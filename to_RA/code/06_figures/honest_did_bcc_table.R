# honest_did_bcc_table.R
#
# HonestDiD relative-magnitudes sensitivity for the 22-25 Brynjolfsson-style
# sample (Appendix B), on the SAME individual-level firm-FE Poisson event study
# as the rest of the appendix (A3_bcc_event_study.R: BCC eq. 4.1, ages 22-25,
# Q5 vs Q1) and with the same sensitivity spec as the main 21-30 table
# (honest_did_quintile_table.R: RM bound, Mbar grid {0.5,1,1.5,2}, quarterly
# aggregation, target = average over the full post period).
#
# A3 now exports the FULL clustered variance-covariance matrix of the Q5
# event-study coefficients, so this uses the EXACT sigma of the individual-level
# firm-FE event study -- not a diagonal approximation. If that vcov file is
# absent (e.g. the updated A3 has not yet been re-run on the server) it falls
# back to diag(se^2) with a warning, so the table still builds in the meantime.
#
# Inputs:  analysis-indiv/from_secure_server/coefficients/
#            coef_bcc_event_study.csv         (sample, age_bin, k, ai_q, coef, se)
#            coef_bcc_event_study_q5vcov.csv   (age_bin, k_i, k_j, cov) -- full Q5 vcov
#          age_bin 1 = ages 22-25, ai_q 5 = most-exposed quintile vs Q1, ref k = -1.
# Outputs: analysis/output/tables/table_honest_did_bcc.tex (tabular fragment)
#          analysis/output/coefficients/coef_honest_did_bcc.csv (numbers)
#
# Usage:  Rscript analysis/06_figures/honest_did_bcc_table.R   (from repo root)

suppressMessages({ library(data.table); library(HonestDiD) })

BASE <- getwd()                                       # repo root (run from here)
IN  <- file.path(BASE, "analysis-indiv", "from_secure_server", "coefficients",
                 "coef_bcc_event_study.csv")          # exported BCC event study
VC_IN <- file.path(BASE, "analysis-indiv", "from_secure_server", "coefficients",
                   "coef_bcc_event_study_q5vcov.csv") # full clustered Q5 vcov (A3)
OUT_TEX <- file.path(BASE, "analysis", "output", "tables", "table_honest_did_bcc.tex")
OUT_CSV <- file.path(BASE, "analysis", "output", "coefficients", "coef_honest_did_bcc.csv")

REF_YM  <- 2022L * 12L + 10L                           # October 2022 = k = -1
MBARVEC <- c(0.5, 1, 1.5, 2)                           # relative-magnitude grid (main spec)

# ---- read the Q5-vs-Q1 event study for the 22-25 sample --------------------
d <- fread(IN)                                         # exported coefficients
d <- d[sample == "in_bcc_full" & age_bin == 1L & ai_q == 5L]  # 22-25, Q5 vs Q1
setorder(d, k)                                         # order by event time
d <- d[k != -1L]                                       # drop the reference period

beta_m <- d$coef                                       # event-study point estimates
se_m   <- d$se                                         # their standard errors
ks     <- d$k                                          # event times (months)

# ---- aggregate months to quarters; diagonal sigma --------------------------
qof <- function(k) {                                  # quarter label for event time k
  ym <- (REF_YM + 1L) + k                             # absolute year*12+month
  yr <- (ym - 1L) %/% 12L; mo <- ((ym - 1L) %% 12L) + 1L  # calendar year / month
  sprintf("%dq%d", yr, (mo - 1L) %/% 3L + 1L)         # e.g. "2023q1"
}
qlab <- vapply(ks, qof, character(1))                 # quarter per coefficient
quarters <- unique(qlab)                              # ordered unique quarters
Bm <- matrix(0, nrow = length(quarters), ncol = length(ks),  # month -> quarter average
             dimnames = list(quarters, NULL))
for (i in seq_along(ks)) Bm[qlab[i], i] <- 1 / sum(qlab == qlab[i])  # equal within quarter

betahat <- as.numeric(Bm %*% beta_m)                  # quarterly coefficients

# Monthly sigma: the FULL clustered vcov exported by A3 (exact), else diagonal.
if (file.exists(VC_IN)) {
  vc <- fread(VC_IN)[age_bin == 1L]                   # 22-25 Q5 vcov, long form
  sigma_m <- matrix(0, length(ks), length(ks))        # monthly vcov in `ks` order
  ii <- match(vc$k_i, ks); jj <- match(vc$k_j, ks)    # map (k_i, k_j) -> matrix index
  ok <- !is.na(ii) & !is.na(jj)
  sigma_m[cbind(ii[ok], jj[ok])] <- vc$cov[ok]
  if (max(abs(diag(sigma_m) - se_m^2)) > 1e-6 * max(se_m^2))   # diagonal must equal se^2
    warning("Exported vcov diagonal does not match the reported SEs -- check the A3 export.")
  cat("Using the FULL clustered variance-covariance matrix from the server (exact).\n")
} else {
  sigma_m <- diag(se_m^2)                             # fallback: diagonal (indicative)
  warning("coef_bcc_event_study_q5vcov.csv not found -- diagonal sigma (indicative). ",
          "Re-run the updated A3 on the server and sync from_secure_server for the exact table.")
}
sigma <- Bm %*% sigma_m %*% t(Bm)                     # quarterly vcov (linear transform)
sigma <- (sigma + t(sigma)) / 2                       # symmetrize against rounding

n_pre  <- sum(as.integer(sub("q.*", "", quarters)) * 4 +  # quarters strictly before 2022q4
                as.integer(sub(".*q", "", quarters)) < 2022 * 4 + 4)
n_post <- length(quarters) - n_pre                     # remaining quarters are post
l_vec  <- rep(1 / n_post, n_post)                      # target = average over all post quarters
cat(sprintf("Pre quarters: %d  Post quarters: %d\n", n_pre, n_post))

# ---- HonestDiD: original CI, RM grid, breakdown ----------------------------
orig <- HonestDiD::constructOriginalCS(betahat = betahat, sigma = sigma,
                                       numPrePeriods = n_pre, numPostPeriods = n_post,
                                       l_vec = l_vec)   # exact parallel trends CI
rm_at <- function(mb)                                   # RM CI at given Mbar value(s)
  as.data.table(HonestDiD::createSensitivityResults_relativeMagnitudes(
    betahat = betahat, sigma = sigma,
    numPrePeriods = n_pre, numPostPeriods = n_post,
    bound = "deviation from parallel trends",
    # Wider grid than the main 21-30 table: the 22-25 firm-FE event study is far
    # noisier, so the RM CIs widen quickly and would clip at +/-2 (M-bar = 2).
    Mbarvec = mb, l_vec = l_vec, gridPoints = 800L, grid.lb = -4, grid.ub = 4))

rm_main <- rm_at(MBARVEC)                               # CIs on the reported grid
fine    <- seq(0.25, 3, by = 0.25)                     # coarse breakdown grid (fast)
rm_fine <- rm_at(fine)                                  # RM CI at each fine value
excl0   <- rm_fine[lb > 0 | ub < 0]                     # rows excluding zero
breakdown <- if (nrow(excl0)) max(excl0$Mbar) else 0    # largest Mbar excluding zero
cat(sprintf("Original CI: [%+.4f, %+.4f]  Breakdown Mbar = %.2f\n",
            orig$lb, orig$ub, breakdown))

# ---- write the coefficient CSV and the LaTeX fragment ----------------------
csv <- rbindlist(list(
  data.table(restriction = "original", Mbar = 0,
             lb = as.numeric(orig$lb), ub = as.numeric(orig$ub)),
  data.table(restriction = "RM", Mbar = rm_main$Mbar,
             lb = as.numeric(rm_main$lb), ub = as.numeric(rm_main$ub)),
  data.table(restriction = "breakdown", Mbar = breakdown, lb = NA_real_, ub = NA_real_)))
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(csv, OUT_CSV)                                   # save the numbers

ci <- function(lb, ub) sprintf("[%+.3f, %+.3f]", lb, ub)
lines <- c(
  "\\begin{tabular}{lc}",
  "\\toprule",
  "Restriction & Robust 95\\% CI \\\\",
  "\\midrule",
  paste0("Original ($\\bar{M}=0$, parallel trends) & ", ci(orig$lb, orig$ub), " \\\\"),
  sapply(seq_len(nrow(rm_main)), function(i)
    sprintf("$\\bar{M}=%.1f$ & %s \\\\", rm_main$Mbar[i], ci(rm_main$lb[i], rm_main$ub[i]))),
  "\\midrule",
  sprintf("Breakdown $\\bar{M}$ & %.2f \\\\", breakdown),
  "\\bottomrule",
  "\\end{tabular}")
dir.create(dirname(OUT_TEX), showWarnings = FALSE, recursive = TRUE)
writeLines(lines, OUT_TEX)                              # write the fragment
cat(sprintf("Wrote %s and %s\n", OUT_TEX, OUT_CSV))
