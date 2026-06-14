# make_aug_auto_table.R
#
# Augmentation-vs-automation table: seasonally adjusted private-sector employment
# change from February 2025 to February 2026 (the "agentic year"), by Handa et al.
# exposure quintile, ages 21-60. Panel A ranks occupations by augmentation share,
# Panel B by automation share. Each panel reports the employment-weighted mean
# change by quintile and the difference relative to Q1 (the base). The final row
# is the TRIPLE DIFFERENCE: the automation Q5-Q1 gradient minus the augmentation
# Q5-Q1 gradient, which tests whether automation exposure predicts a steeper
# decline than augmentation exposure.
#
# The two gradients are estimated jointly on a stacked occupation-level data set
# (each occupation enters once for augmentation and once for automation) with
# standard errors clustered at the occupation, so the triple-difference SE
# correctly accounts for the same occupation appearing in both rankings.
#
# Input:  microdata-output/09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_handa_mapping.csv
# Output: analysis/output/tables/table_aug_auto.tex  (tabular fragment only)
#
# Usage:  Rscript analysis/05_tables/make_aug_auto_table.R   (from the repo root)

suppressMessages({                                   # quiet package banners
  library(sandwich)                                  # clustered covariance (vcovCL)
})

base_dir <- "."                                      # run this script from the repo root
source(file.path(base_dir, "analysis", "06_figures", "seasonal.R"))  # seasonal_adjust()

parsed   <- file.path(base_dir, "microdata-output",  # parsed cell aggregates
                      "09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv")
exp_file <- file.path(base_dir, "data", "ai_exposure",   # occupation -> Handa quintiles
                      "styrk08_handa_mapping.csv")
out_file <- file.path(base_dir, "analysis", "output", "tables",
                      "table_aug_auto.tex")          # output LaTeX fragment

ref_date  <- "2025-02-16"                            # February 2025 baseline (pre-agentic)
end_date  <- "2026-02-16"                            # February 2026 endpoint
seas_from <- "2021-01-16"; seas_to <- "2024-12-16"   # SA factor-estimation window
age_keep  <- c("1", "2", "3", "4")                   # decade age groups 21-30..51-60
private   <- 2                                       # sector code 2 = private

# ---- build the cross-section: one row per occupation ------------------------
df <- read.csv(parsed, colClasses = c(yrke4 = "character",   # read parsed aggregates
                                      alder_gr = "character",
                                      date = "character"))
df <- df[df$variable == "count" &                    # employment counts only
         df$sekt == private &                        # private sector only
         df$alder_gr %in% age_keep, ]                # ages 21-60

occ <- aggregate(value ~ yrke4 + date, data = df, FUN = sum)  # occ x month headcount
names(occ)[names(occ) == "value"] <- "emp"           # rename to emp

# Attach the Handa automation and augmentation quintiles (1 = least, 5 = most).
exp <- read.csv(exp_file, colClasses = c(styrk08 = "character"))   # read mapping
exp <- exp[, c("styrk08", "q_automation_share", "q_augmentation_share")]  # keep quintiles
names(exp) <- c("yrke4", "auto_q", "aug_q")          # rename columns
exp <- exp[!is.na(exp$auto_q) & !is.na(exp$aug_q), ] # drop occupations missing a quintile
occ <- merge(occ, exp, by = "yrke4")                 # inner join -> kept occupations

codes <- sort(unique(occ$yrke4))                     # occupation codes to loop over
rows  <- list()                                      # collect one record per occupation
for (oid in codes) {                                 # one occupation at a time
  s <- occ[occ$yrke4 == oid, ]                       # this occupation's series
  s <- s[order(s$date), ]                            # in date order
  if (!(ref_date %in% s$date) || !(end_date %in% s$date)) next  # need both endpoints
  base_raw <- s$emp[s$date == ref_date]              # Feb 2025 headcount
  end_raw  <- s$emp[s$date == end_date]              # Feb 2026 headcount
  if (base_raw <= 0 || end_raw <= 0) next            # need positive headcount at both ends
  sa <- seasonal_adjust(s$date, s$emp, seas_from, seas_to)  # seasonally adjust series
  base_sa <- sa[s$date[order(s$date)] == ref_date]   # SA Feb 2025 level
  end_sa  <- sa[s$date[order(s$date)] == end_date]   # SA Feb 2026 level
  rows[[length(rows) + 1]] <- data.frame(            # store this occupation's record
    yrke4 = oid,                                     # occupation code
    auto_q = as.integer(s$auto_q[1]),               # automation quintile
    aug_q  = as.integer(s$aug_q[1]),                # augmentation quintile
    base_emp = base_raw,                            # Feb 2025 headcount = regression weight
    change_sa = end_sa / base_sa - 1)               # SA proportional change Feb25->Feb26
}
cs <- do.call(rbind, rows)                           # cross-section: one row per occupation
cat(sprintf("Occupations with both endpoints: %d\n", nrow(cs)))  # report size

# ---- stacked joint regression: aug and auto gradients together -------------
# Long form: each occupation appears twice, once per exposure measure, so a
# single clustered regression yields both panels AND the triple-difference SE.
long <- rbind(
  data.frame(yrke4 = cs$yrke4, y = cs$change_sa, w = cs$base_emp,   # augmentation rows
             measure = "aug", q = cs$aug_q),
  data.frame(yrke4 = cs$yrke4, y = cs$change_sa, w = cs$base_emp,   # automation rows
             measure = "auto", q = cs$auto_q))
long$grp <- factor(paste0(long$measure, long$q),     # 10 group labels: aug1..aug5, auto1..auto5
                   levels = c(paste0("aug", 1:5), paste0("auto", 1:5)))

fit <- lm(y ~ 0 + grp, data = long, weights = w)     # WLS; coefficients = the 10 group means
V   <- vcovCL(fit, cluster = long$yrke4, type = "HC1")  # SE clustered at occupation
b   <- coef(fit)                                     # group mean changes
names(b) <- names(V[, 1]) <- rownames(V) <- levels(long$grp)  # tidy names

# Helper: estimate and SE of a linear contrast c'b given the clustered vcov V.
contrast <- function(cvec) {                          # cvec indexed like names(b)
  est <- sum(cvec * b)                                # point estimate c'b
  se  <- sqrt(as.numeric(t(cvec) %*% V %*% cvec))     # standard error sqrt(c'Vc)
  c(est = est, se = se)                               # return both
}
zero <- setNames(rep(0, length(b)), names(b))         # zero contrast template

stars <- function(est, se) {                          # significance stars from |z|
  if (se <= 0) return("")                             # guard against a zero SE
  z <- abs(est / se)                                  # robust z-statistic
  if (z > 2.576) return("$^{***}$")                   # 1% two-sided
  if (z > 1.96)  return("$^{**}$")                    # 5% two-sided
  if (z > 1.645) return("$^{*}$")                     # 10% two-sided
  ""                                                  # not significant
}

# Build one panel (mean row + difference-vs-Q1 row) for a given measure prefix.
panel_lines <- function(prefix, title) {              # prefix = "aug" or "auto"
  keys <- paste0(prefix, 1:5)                         # group keys for Q1..Q5
  means <- sprintf("%+.2f", 100 * b[keys])            # quintile means in percent (no SE)
  dd_cells <- "---"; se_cells <- ""                   # Q1 is the base: blank
  for (k in 2:5) {                                    # Q2..Q5: difference vs Q1
    cv <- zero; cv[paste0(prefix, k)] <- 1; cv[paste0(prefix, 1)] <- -1  # Qk - Q1
    r <- contrast(cv)                                 # estimate + clustered SE
    dd_cells <- c(dd_cells, sprintf("%+.2f%s", 100 * r["est"], stars(r["est"], r["se"])))
    se_cells <- c(se_cells, sprintf("(%.2f)", 100 * r["se"]))
  }
  c(paste0("\\multicolumn{6}{l}{\\textit{", title, "}} \\\\"),  # panel heading
    paste0("\\quad Average change (\\%) & ", paste(means, collapse = " & "), " \\\\"),
    paste0("\\quad Difference vs.\\ Q1 (\\%) & ", paste(dd_cells, collapse = " & "), " \\\\"),
    paste0(" & ", paste(se_cells, collapse = " & "), " \\\\"))
}

# Triple difference: (auto Q5 - auto Q1) - (aug Q5 - aug Q1).
tcv <- zero                                           # build the triple-difference contrast
tcv["auto5"] <-  1; tcv["auto1"] <- -1               # + automation Q5-Q1 gradient
tcv["aug5"]  <- -1; tcv["aug1"]  <-  1               # - augmentation Q5-Q1 gradient
td <- contrast(tcv)                                   # triple difference + clustered SE

# ---- assemble the LaTeX tabular fragment -----------------------------------
lines <- c(
  "\\begin{tabular}{lccccc}",                         # one label column + Q1..Q5
  "\\toprule",
  " & Q1 & Q2 & Q3 & Q4 & Q5 \\\\",                   # column header
  "\\midrule",
  panel_lines("aug",  "Panel A. Augmentation"),       # augmentation panel
  "\\addlinespace",
  panel_lines("auto", "Panel B. Automation"),         # automation panel
  "\\midrule",
  paste0("Triple difference (\\%) & \\multicolumn{5}{c}{",  # auto - aug, Q5-Q1
         sprintf("%+.2f%s", 100 * td["est"], stars(td["est"], td["se"])),
         "} \\\\"),
  paste0(" & \\multicolumn{5}{c}{(", sprintf("%.2f", 100 * td["se"]), ")} \\\\"),
  paste0("Occupations & \\multicolumn{5}{c}{", nrow(cs), "} \\\\"),  # N footer
  "\\bottomrule",
  "\\end{tabular}")

dir.create(dirname(out_file), showWarnings = FALSE, recursive = TRUE)  # ensure out dir
writeLines(lines, out_file)                           # write the tabular fragment
cat(sprintf("Wrote %s\n", out_file))                  # progress message
cat(sprintf("Triple difference (auto-aug, Q5-Q1): %+.3f pp  (SE %.3f)\n",
            100 * td["est"], 100 * td["se"]))         # echo the headline number
