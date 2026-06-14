# honest_did_bcc_table.R
#
# HonestDiD relative-magnitudes sensitivity for the 22-25 Brynjolfsson-style
# sample (Appendix B). Unlike the main 21-30 table, the individual-level firm-FE
# event study is estimated on the secure server and only its point estimates and
# standard errors are exported -- not the full variance-covariance matrix. We
# therefore approximate sigma as DIAGONAL (sigma = diag(se^2)), which ignores the
# correlation across event-study coefficients. The result is indicative, not
# exact, and is flagged as such in the paper.
#
# Input:  analysis-indiv/from_secure_server/coefficients/coef_bcc_event_study.csv
#         (sample, age_bin, k, ai_q, coef, se, ...); age_bin 1 = ages 22-25,
#         ai_q 5 = most-exposed quintile relative to Q1, reference k = -1.
# Output: analysis/output/tables/table_honest_did_bcc.tex (tabular fragment)
#
# Usage:  Rscript analysis/06_figures/honest_did_bcc_table.R   (from repo root)

suppressMessages({ library(data.table); library(HonestDiD) })

BASE <- getwd()                                       # repo root (run from here)
IN  <- file.path(BASE, "analysis-indiv", "from_secure_server", "coefficients",
                 "coef_bcc_event_study.csv")          # exported BCC event study
OUT_TEX <- file.path(BASE, "analysis", "output", "tables", "table_honest_did_bcc.tex")

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
sigma   <- Bm %*% diag(se_m^2) %*% t(Bm)              # quarterly vcov from DIAGONAL monthly
sigma   <- (sigma + t(sigma)) / 2                     # symmetrize against rounding

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
    Mbarvec = mb, l_vec = l_vec, gridPoints = 200L, grid.lb = -1.5, grid.ub = 1.5))

rm_main <- rm_at(MBARVEC)                               # CIs on the reported grid
fine    <- seq(0.25, 3, by = 0.25)                     # coarse breakdown grid (fast)
rm_fine <- rm_at(fine)                                  # RM CI at each fine value
excl0   <- rm_fine[lb > 0 | ub < 0]                     # rows excluding zero
breakdown <- if (nrow(excl0)) max(excl0$Mbar) else 0    # largest Mbar excluding zero
cat(sprintf("Original CI: [%+.4f, %+.4f]  Breakdown Mbar = %.2f\n",
            orig$lb, orig$ub, breakdown))

# ---- write the LaTeX fragment ----------------------------------------------
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
cat(sprintf("Wrote %s\n", OUT_TEX))
