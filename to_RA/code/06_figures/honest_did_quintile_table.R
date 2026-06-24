# honest_did_quintile_table.R
#
# HonestDiD (Rambachan-Roth 2023) relative-magnitudes sensitivity analysis for
# the Q5-vs-Q1 cell-level Poisson event study, ages 21-30, private sector. This
# is the table behind Section "Robust Inference": it asks how large a post-period
# violation of parallel trends would have to be to overturn the estimated
# exposure gradient, using the pre-period violations to set the scale.
#
# It uses the same cell-level Poisson event study as Section 4.2 (occupation and
# month fixed effects, NO seasonal offset, cluster-robust vcov), but: (i) compares
# Q5 to Q1 (the paper's contrast) rather than
# Q5 to Q3; (ii) uses the relative-magnitude bound as the MAIN restriction, on
# the grid Mbar in {0.5, 1, 1.5, 2}; (iii) adds the conventional ("original") CI,
# which corresponds to exact parallel trends (Mbar = 0); and (iv) computes the
# BREAKDOWN value -- the largest Mbar for which the robust CI still excludes zero.
#
# Reference month = October 2022 (k = -1), the same baseline as the rest of the
# paper. Target = the average post-ChatGPT effect over the FULL post period
# (Nov 2022-Feb 2026), matching the POST dummy of microdata_did_cell.R (Sec 4.2).
#
# Output: analysis/output/tables/table_honest_did.tex (tabular fragment)
#         analysis/output/coefficients/coef_honest_did_quintile.csv (numbers)
#
# Usage:  Rscript analysis/06_figures/honest_did_quintile_table.R   (from repo root)

suppressMessages({ library(data.table); library(fixest); library(HonestDiD) })

BASE <- getwd()                                       # repo root (run from here)
DATA_FILE <- file.path(BASE, "microdata-output",      # parsed cell aggregates
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",   # occupation -> Eloundou quintile
                       "styrk08_eloundou_beta_mapping.csv")
OUT_TEX <- file.path(BASE, "analysis", "output", "tables", "table_honest_did.tex")
OUT_CSV <- file.path(BASE, "analysis", "output", "coefficients",
                     "coef_honest_did_quintile.csv")

AGE      <- "1"                                        # decade age group 1 = 21-30
REF_YM   <- 2022L * 12L + 10L                          # October 2022 reference (k = -1)
SEAS_FROM <- as.IDate("2021-01-16")                   # SA factor-estimation window start
SEAS_TO   <- as.IDate("2024-12-16")                   # SA factor-estimation window end
MBARVEC  <- c(0.5, 1, 1.5, 2)                          # relative-magnitude grid (main spec)

# ---- load and prepare the cell panel ---------------------------------------
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character", alder_gr = "character",
                                     sekt = "integer", variable = "character",
                                     value = "numeric"))
d <- d[variable == "count" & sekt == 2L & alder_gr == AGE]   # private, ages 21-30, counts
d[, date := as.IDate(date)]                           # parse the status date
d[, ym_int := year(date) * 12L + month(date)]         # year*12 + month integer index
d[, k := as.integer(ym_int - (REF_YM + 1L))]          # event time: k = -1 is October 2022
d[, t := as.integer(ym_int - REF_YM)]                 # 1-based month index (for pre-fit)
d[, cal_month := month(date)]                         # calendar month (for seasonal FE)

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))   # exposure mapping
exp <- exp[!is.na(quintile), .(yrke4 = styrk08, ai_q = as.integer(quintile))]  # tidy
d <- merge(d, exp, by = "yrke4")                      # attach quintile to each occupation

t_to_calm <- unique(d[, .(t, k, cal_month, date)])    # lookup from t to k/month/date

# Balance the occupation x month panel, filling absent cells with zero counts.
balance <- function(sub) {
  grid <- CJ(yrke4 = unique(sub$yrke4), t = sort(unique(sub$t)))  # full occ x t grid
  grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4")  # re-attach quintile
  grid <- merge(grid, t_to_calm, by = "t")            # re-attach k / calendar month
  out  <- merge(grid, sub[, .(yrke4, t, count)], by = c("yrke4", "t"), all.x = TRUE)
  out[is.na(count), count := 0]                       # absent cell -> zero employment
  out[, q_m_key := paste0(ai_q, "_", cal_month)]      # quintile x calendar-month key
  out[, ai_q_f := factor(ai_q, levels = 1:5)]         # quintile as a factor
  out
}
d[, count := value]                                   # name the outcome 'count'

# ---- the event study (Q5 vs Q1), no seasonal offset (matches Section 4.2) ---
sub <- balance(d)                                     # full-window balanced panel
fit <- fepois(count ~ i(k, ai_q_f, ref = -1, ref2 = "1") | yrke4 + k,  # Q5 vs Q1 by k
              data = sub, cluster = ~yrke4, warn = FALSE, notes = FALSE)

kvec <- sort(unique(sub$k))                           # event-time points present
nm <- sprintf("k::%d:ai_q_f::5", kvec)                # Q5-vs-Q1 coefficient names
nm <- nm[nm %in% names(coef(fit))]                    # keep those actually estimated
ks <- as.integer(sub("k::(-?[0-9]+):.*", "\\1", nm))  # event times for those coefs
beta_m  <- coef(fit)[nm]                              # event-study coefficient vector
sigma_m <- vcov(fit)[nm, nm]                          # its clustered variance-covariance

# ---- aggregate months to quarters; target = average over 2023q1-2025q1 -----
qof <- function(k) {                                  # quarter label for event time k
  ym <- (REF_YM + 1L) + k                             # absolute year*12+month for this k
  yr <- (ym - 1L) %/% 12L                             # calendar year
  mo <- ((ym - 1L) %% 12L) + 1L                       # calendar month
  sprintf("%dq%d", yr, (mo - 1L) %/% 3L + 1L)         # e.g. "2023q1"
}
qlab <- vapply(ks, qof, character(1))                 # quarter label per coefficient
quarters <- unique(qlab)                              # ordered unique quarters
Bm <- matrix(0, nrow = length(quarters), ncol = length(ks),  # months -> quarter-average
             dimnames = list(quarters, NULL))
for (i in seq_along(ks)) Bm[qlab[i], i] <- 1 / sum(qlab == qlab[i])  # equal within quarter

betahat <- as.numeric(Bm %*% beta_m)                  # quarterly event-study coefficients
sigma   <- Bm %*% sigma_m %*% t(Bm)                   # quarterly vcov (linear transform)
sigma   <- (sigma + t(sigma)) / 2                     # symmetrize against rounding

pre_q  <- quarters[as.integer(sub("q.*", "", quarters)) * 4 +   # quarters strictly pre-ref
                     as.integer(sub(".*q", "", quarters)) <
                   2022 * 4 + 4]                       # before 2022q4
n_pre  <- length(pre_q)                                # number of pre-period quarters
n_post <- length(quarters) - n_pre                     # number of post-period quarters
l_vec  <- rep(1 / n_post, n_post)                      # target = average over ALL post quarters
                                                       # (full Nov 2022-Feb 2026 window, matching
                                                       # the POST dummy of microdata_did_cell.R)
cat(sprintf("Pre quarters: %d  Post quarters: %d  Target quarters: %d\n",
            n_pre, n_post, sum(l_vec > 0)))

# ---- HonestDiD: original CI, RM grid, and the breakdown value ---------------
orig <- HonestDiD::constructOriginalCS(betahat = betahat, sigma = sigma,
                                       numPrePeriods = n_pre, numPostPeriods = n_post,
                                       l_vec = l_vec)   # conventional CI = exact parallel trends
cat(sprintf("Original CI: [%+.4f, %+.4f]\n", orig$lb, orig$ub))

rm_at <- function(mb) {                                # RM CI at one or more Mbar values
  HonestDiD::createSensitivityResults_relativeMagnitudes(
    betahat = betahat, sigma = sigma,
    numPrePeriods = n_pre, numPostPeriods = n_post,
    bound = "deviation from parallel trends",          # relative-magnitudes restriction
    Mbarvec = mb, l_vec = l_vec, gridPoints = 300L,
    grid.lb = -2, grid.ub = 2)
}
rm_main <- as.data.table(rm_at(MBARVEC))               # CIs on the reported grid
for (i in seq_len(nrow(rm_main)))                      # echo each grid point
  cat(sprintf("RM Mbar=%.1f: [%+.4f, %+.4f]\n",
              rm_main$Mbar[i], rm_main$lb[i], rm_main$ub[i]))

# Breakdown: largest Mbar on a grid for which the robust CI excludes zero.
fine <- seq(0.25, 3, by = 0.25)                        # breakdown search grid (0.25 steps)
rm_fine <- as.data.table(rm_at(fine))                  # RM CI at each fine value
excl0 <- rm_fine[lb > 0 | ub < 0]                      # rows whose interval excludes zero
breakdown <- if (nrow(excl0)) max(excl0$Mbar) else 0   # 0 if even the smallest Mbar includes 0
cat(sprintf("Breakdown Mbar = %.2f\n", breakdown))

# ---- write the coefficient CSV and the LaTeX fragment ----------------------
csv <- rbindlist(list(
  data.table(restriction = "original", Mbar = 0, lb = orig$lb, ub = orig$ub),
  data.table(restriction = "RM", Mbar = rm_main$Mbar, lb = rm_main$lb, ub = rm_main$ub),
  data.table(restriction = "breakdown", Mbar = breakdown, lb = NA_real_, ub = NA_real_)))
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(csv, OUT_CSV)                                   # save the numbers

ci <- function(lb, ub) sprintf("[%+.3f, %+.3f]", lb, ub)   # format a CI as [lb, ub]
lines <- c(
  "\\begin{tabular}{lc}",                              # restriction column + CI column
  "\\toprule",
  "Restriction & Robust 95\\% CI \\\\",
  "\\midrule",
  paste0("Original ($\\bar{M}=0$, parallel trends) & ", ci(orig$lb, orig$ub), " \\\\"),
  sapply(seq_len(nrow(rm_main)), function(i)           # one row per reported Mbar
    sprintf("$\\bar{M}=%.1f$ & %s \\\\", rm_main$Mbar[i], ci(rm_main$lb[i], rm_main$ub[i]))),
  "\\midrule",
  sprintf("Breakdown $\\bar{M}$ & %.2f \\\\", breakdown),   # breakdown value row
  "\\bottomrule",
  "\\end{tabular}")
dir.create(dirname(OUT_TEX), showWarnings = FALSE, recursive = TRUE)
writeLines(lines, OUT_TEX)                             # write the tabular fragment
cat(sprintf("Wrote %s and %s\n", OUT_TEX, OUT_CSV))
