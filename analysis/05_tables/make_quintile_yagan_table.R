# make_quintile_yagan_table.R
#
# Table 4: cross-sectional Yagan employment-hysteresis change by AI-exposure
# quintile, seasonally adjusted, October 2022 -> February 2026, ages 21-60,
# private sector. One occupation = one observation, weighted by its October 2022
# headcount so the quintile means reproduce the kiindeksen.no headcount index.
#
# This is the R twin of analysis/06_figures/microdata_change_lastmonth.py, but it
# reports only the seasonally adjusted basis and lays the table out the way the
# paper wants: a top row of employment-weighted mean changes (no SE), and a
# bottom "difference vs Q1" row holding the double differences Q2..Q5 - Q1 with
# heteroskedasticity-robust (HC1) standard errors (Q1 is the base, left blank).
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/tables/table_quintile_yagan.tex  (tabular fragment only)
#
# Usage:  Rscript analysis/05_tables/make_quintile_yagan_table.R

suppressMessages({                                   # quiet package banners
  library(sandwich)                                  # HC1 robust covariance matrix
})

base_dir <- "."                                      # run this script from the repo root
source(file.path(base_dir, "analysis", "06_figures", "seasonal.R"))  # seasonal_adjust()

parsed   <- file.path(base_dir, "microdata-output",  # parsed cell aggregates
                      "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
exp_file <- file.path(base_dir, "data", "ai_exposure",   # occupation -> quintile
                      "styrk08_eloundou_beta_mapping.csv")
out_file <- file.path(base_dir, "analysis", "output", "tables",
                      "table_quintile_yagan.tex")    # output LaTeX fragment

ref_date  <- "2022-10-16"                             # October 2022 baseline month
seas_from <- "2021-01-16"; seas_to <- "2024-12-16"    # SA factor-estimation window
age_keep  <- c("1", "2", "3", "4")                    # decade age groups 21-30..51-60
private   <- 2                                        # sector code 2 = private

# ---- build the cross-section: one row per occupation ------------------------
df <- read.csv(parsed, colClasses = c(yrke4 = "character",   # read parsed aggregates
                                      alder_gr = "character",
                                      date = "character"))
df <- df[df$variable == "count" &                    # employment counts only
         df$sekt == private &                        # private sector only
         df$alder_gr %in% age_keep, ]                # ages 21-60

# Collapse to one headcount series per occupation x month (sum over age groups).
occ <- aggregate(value ~ yrke4 + date, data = df, FUN = sum)  # occ x month headcount
names(occ)[names(occ) == "value"] <- "emp"           # rename to emp

# Attach the Eloundou exposure quintile (same mapping the figures use).
exp <- read.csv(exp_file, colClasses = c(styrk08 = "character"))  # read mapping
exp <- exp[!is.na(exp$quintile), c("styrk08", "quintile")]       # drop unmapped
names(exp) <- c("yrke4", "ai_q")                     # rename keys
occ <- merge(occ, exp, by = "yrke4")                 # inner join -> kept occupations

last_date <- max(occ$date)                           # last month present (2026-02-16)
cat(sprintf("Reference: %s  Last: %s\n", ref_date, last_date))  # show endpoints

codes <- sort(unique(occ$yrke4))                     # occupation codes to loop over
rows  <- list()                                      # collect one record per occupation
for (oid in codes) {                                 # one occupation at a time
  s <- occ[occ$yrke4 == oid, ]                       # this occupation's series
  s <- s[order(s$date), ]                            # in date order
  if (!(ref_date %in% s$date) || !(last_date %in% s$date)) next  # need both endpoints
  base_raw <- s$emp[s$date == ref_date]              # Oct 2022 headcount
  last_raw <- s$emp[s$date == last_date]             # last-month headcount
  if (base_raw <= 0 || last_raw <= 0) next           # need positive headcount at both ends
  sa <- seasonal_adjust(s$date, s$emp, seas_from, seas_to)  # seasonally adjust series
  base_sa <- sa[s$date[order(s$date)] == ref_date]   # SA Oct 2022 level
  last_sa <- sa[s$date[order(s$date)] == last_date]  # SA last-month level
  rows[[length(rows) + 1]] <- data.frame(            # store this occupation's record
    yrke4 = oid,                                     # occupation code
    ai_q = as.integer(s$ai_q[1]),                    # exposure quintile
    base_emp = base_raw,                             # Oct 2022 headcount = regression weight
    change_sa = last_sa / base_sa - 1)               # SA proportional (Yagan) change
}
cs <- do.call(rbind, rows)                           # cross-section: one row per occupation
cat(sprintf("Occupations with both endpoints: %d\n", nrow(cs)))  # report size

# ---- weighted regression of the change on quintile dummies -----------------
cs$ai_q <- factor(cs$ai_q, levels = 1:5)             # quintile as a 5-level factor
fit <- lm(change_sa ~ 0 + ai_q, data = cs, weights = base_emp)  # WLS; coefs = wtd means
V   <- vcovHC(fit, type = "HC1")                     # HC1 heteroskedasticity-robust vcov
b   <- coef(fit)                                     # the five quintile mean changes
names(b) <- names(V[, 1]) <- rownames(V) <- paste0("Q", 1:5)  # tidy names Q1..Q5

# Double differences Qk - Q1 (k = 2..5) with their robust standard errors.
dd  <- sapply(2:5, function(k) b[k] - b[1])          # point estimates Qk - Q1
dds <- sapply(2:5, function(k)                       # SE = sqrt(V_kk + V_11 - 2 V_k1)
  sqrt(V[k, k] + V[1, 1] - 2 * V[k, 1]))
names(dd) <- names(dds) <- paste0("Q", 2:5)          # label by quintile

stars <- function(est, se) {                         # significance stars from |z|
  if (se <= 0) return("")                            # guard against a zero SE
  z <- abs(est / se)                                 # robust z-statistic
  if (z > 2.576) return("$^{***}$")                  # 1% two-sided
  if (z > 1.96)  return("$^{**}$")                   # 5% two-sided
  if (z > 1.645) return("$^{*}$")                    # 10% two-sided
  ""                                                 # not significant
}

# ---- assemble the LaTeX tabular fragment -----------------------------------
mean_cells <- sprintf("%+.2f", 100 * b)              # quintile means in percent (no SE)
dd_cells   <- c("---",                               # Q1 is the base: no double difference
                sapply(2:5, function(k)              # Q2..Q5: percent change vs Q1 + stars
                  sprintf("%+.2f%s", 100 * dd[paste0("Q", k)],
                          stars(dd[paste0("Q", k)], dds[paste0("Q", k)]))))
se_cells   <- c("",                                  # no SE under the Q1 base cell
                sapply(2:5, function(k)              # robust SE in percent, in parentheses
                  sprintf("(%.2f)", 100 * dds[paste0("Q", k)])))

lines <- c(
  "\\begin{tabular}{lccccc}",                        # one label column + Q1..Q5
  "\\toprule",
  " & Q1 & Q2 & Q3 & Q4 & Q5 \\\\",                  # column header
  "\\midrule",
  paste0("Average change (\\%) & ", paste(mean_cells, collapse = " & "), " \\\\"),
  "\\addlinespace",
  paste0("Difference vs.\\ Q1 (\\%) & ", paste(dd_cells, collapse = " & "), " \\\\"),
  paste0(" & ", paste(se_cells, collapse = " & "), " \\\\"),
  "\\midrule",
  paste0("Occupations & \\multicolumn{5}{c}{", nrow(cs), "} \\\\"),  # N footer
  "\\bottomrule",
  "\\end{tabular}")

dir.create(dirname(out_file), showWarnings = FALSE, recursive = TRUE)  # ensure out dir
writeLines(lines, out_file)                          # write the tabular fragment
cat(sprintf("Wrote %s\n", out_file))                 # progress message
print(round(rbind(mean = 100 * b,                    # echo numbers for a sanity check
                  dd = c(NA, 100 * dd),
                  dd_se = c(NA, 100 * dds)), 3))
