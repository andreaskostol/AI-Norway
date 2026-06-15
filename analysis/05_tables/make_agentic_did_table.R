# make_agentic_did_table.R
#
# Agentic-AI results by age, laid out like Table 7 (age groups as rows): the
# post-April-2025 employment effect of each AI-exposure quintile (Q2..Q5)
# relative to Q1, by decade age group, private sector. It is the agentic-window
# analog of the main cell-level difference-in-differences (microdata_did_cell.R),
# differing only in the reference period: April 2025 (k = -1) is the last
# pre-agentic month and all later months collapse to the post-period.
#
# Spec (per age group a): Poisson, occupation and month fixed effects,
#   log E[count_{j,t}] = alpha_j + beta_t + sum_{q in 2..5} delta_q * POST_t * 1{ai_q(j)=q},
# clustered at occupation; Q1 is the reference quintile.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/tables/table_agentic_did.tex (tabular fragment)
#
# Usage:  Rscript analysis/05_tables/make_agentic_did_table.R   (from repo root)

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()                                       # repo root (run from here)
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure", "styrk08_eloundou_beta_mapping.csv")
OUT_TEX   <- file.path(BASE, "analysis", "output", "tables", "table_agentic_did.tex")

REF_YM   <- 2025L * 12L + 4L                           # April 2025 = last pre-agentic month
AGES     <- c("1", "2", "3", "4")                     # decade age groups 21-30..51-60
AGE_LAB  <- c("1" = "Early career (21--30)", "2" = "31--40",
              "3" = "41--50", "4" = "Senior (51--60)")
PRIVATE  <- 2L                                         # sector code 2 = private

# ---- load counts, attach quintile, define the agentic POST dummy -----------
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character", alder_gr = "character",
                                     sekt = "integer", variable = "character",
                                     value = "numeric"))
d <- d[variable == "count" & sekt == PRIVATE & alder_gr %in% AGES]  # private employment counts
d[, ym_int := year(as.IDate(date)) * 12L + month(as.IDate(date))]   # year*12 + month index

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))       # exposure mapping
exp <- exp[!is.na(quintile), .(yrke4 = styrk08, ai_q = as.integer(quintile))]
d <- merge(d, exp, by = "yrke4")                       # inner join -> mapped occupations

# Event-time level: each pre-month its own value, all post-April-2025 -> "POST".
d[, kk := fifelse(ym_int > REF_YM, "POST", as.character(ym_int - REF_YM - 1L))]

# Balance the occupation x month panel within an age slice (missing cells -> 0).
balance <- function(sub) {
  grid <- CJ(yrke4 = unique(sub$yrke4), ym_int = sort(unique(sub$ym_int)))  # full grid
  grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4")          # re-attach quintile
  grid[, kk := fifelse(ym_int > REF_YM, "POST", as.character(ym_int - REF_YM - 1L))]
  out <- merge(grid, sub[, .(yrke4, ym_int, count = value)],               # bring counts in
               by = c("yrke4", "ym_int"), all.x = TRUE)
  out[is.na(count), count := 0]                        # absent cell -> zero employment
  out[, ai_q := factor(ai_q, levels = 1:5)]            # quintile factor, Q1 = reference
  out
}

stars <- function(p) ifelse(p < 0.01, "$^{***}$", ifelse(p < 0.05, "$^{**}$",
                     ifelse(p < 0.1, "$^{*}$", "")))   # significance stars from p-value

# ---- estimate the agentic DiD per age group --------------------------------
rows_est <- list()                                     # per-age coefficient tables
n_occ <- integer(0); n_obs <- integer(0)               # footer counts per age
for (a in AGES) {
  bc  <- balance(d[alder_gr == a])                     # balanced panel for this age
  fit <- fepois(count ~ i(kk, ai_q, ref = "-1", ref2 = "1") | yrke4 + ym_int,
                data = bc, cluster = ~yrke4, warn = FALSE, notes = FALSE)
  ct  <- as.data.frame(coeftable(fit))                 # coefficient table
  ct$name <- rownames(ct)
  est <- setNames(rep(NA_real_, 4), 2:5)               # Q2..Q5 estimates
  se  <- est; pv <- est                                # matching SE and p-value
  for (q in 2:5) {                                     # pull POST x quintile q vs Q1
    nm <- sprintf("kk::POST:ai_q::%d", q)
    if (nm %in% ct$name) {
      est[as.character(q)] <- ct[nm, "Estimate"]
      se[as.character(q)]  <- ct[nm, "Std. Error"]
      pv[as.character(q)]  <- ct[nm, ncol(coeftable(fit))]  # last col = Pr(>|z|)
    }
  }
  rows_est[[a]] <- list(est = est, se = se, pv = pv)    # stash for this age
  n_occ <- c(n_occ, uniqueN(bc$yrke4)); n_obs <- c(n_obs, nrow(bc))
  cat(sprintf("age %s: Q5 = %+.4f (se %.4f)\n", a, est["5"], se["5"]))
}

# ---- assemble the LaTeX tabular: age rows x quintile (Q2..Q5) columns -------
lines <- c("\\begin{tabular}{lcccc}", "\\toprule",
           " & Q2 & Q3 & Q4 & Q5 \\\\",
           " & (vs Q1) & (vs Q1) & (vs Q1) & (vs Q1) \\\\",
           "\\midrule")
for (a in AGES) {                                      # one age group per (two-line) row
  e <- rows_est[[a]]
  coefs <- sapply(2:5, function(q) sprintf("%+.4f%s", e$est[as.character(q)],
                                           stars(e$pv[as.character(q)])))
  ses   <- sapply(2:5, function(q) sprintf("(%.4f)", e$se[as.character(q)]))
  lines <- c(lines,
             paste0(AGE_LAB[[a]], " & ", paste(coefs, collapse = " & "), " \\\\"),
             paste0(" & ", paste(ses, collapse = " & "), " \\\\"))
}
lines <- c(lines, "\\midrule",
           paste0("Occupations & \\multicolumn{4}{c}{",
                  paste(range(n_occ), collapse = "--"), "} \\\\"),
           paste0("Observations & \\multicolumn{4}{c}{",
                  format(min(n_obs), big.mark = ","), "--",
                  format(max(n_obs), big.mark = ","), "} \\\\"),
           "\\bottomrule", "\\end{tabular}")

dir.create(dirname(OUT_TEX), showWarnings = FALSE, recursive = TRUE)
writeLines(lines, OUT_TEX)                             # write the tabular fragment
cat(sprintf("Wrote %s\n", OUT_TEX))
