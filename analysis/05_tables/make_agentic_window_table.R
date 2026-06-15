# make_agentic_window_table.R
#
# Appendix table around the agentic-coding transition (Claude Code and peers,
# early-to-mid 2025). For each decade age group (and pooled over ages 21-60), it
# reports the most-exposed-minus-least-exposed (Q5 - Q1) seasonally adjusted
# employment gap averaged over two three-month windows:
#   - "before": February-April 2025, the last three months before the agentic
#               tools, ending at the April 2025 reference used in Section 4.6;
#   - "last":   December 2025-February 2026, the last three months of data;
# and the change between them. A negative change means the most-exposed quintile
# lost ground relative to the least-exposed over the agentic window.
#
# Series are private-sector headcount by (age, quintile), seasonally adjusted
# with the shared X-11 core and indexed to October 2022 = 1, so a Q5 - Q1 gap is
# in index points (reported here in percentage points).
#
# Input:  microdata-output/09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/tables/table_agentic_window.tex (tabular fragment)
#
# Usage:  Rscript analysis/05_tables/make_agentic_window_table.R   (from repo root)

base_dir <- "."                                      # run from the repo root
source(file.path(base_dir, "analysis", "06_figures", "seasonal.R"))  # seasonal_adjust()

parsed   <- file.path(base_dir, "microdata-output",
                      "09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv")
exp_file <- file.path(base_dir, "data", "ai_exposure", "styrk08_eloundou_beta_mapping.csv")
out_file <- file.path(base_dir, "analysis", "output", "tables", "table_agentic_window.tex")

norm_date <- "2022-10-16"                            # October 2022 = 1.0 index base
seas_from <- "2021-01-16"; seas_to <- "2024-12-16"   # SA factor-estimation window
private   <- 2                                       # sector code 2 = private
before_w  <- c("2025-02-16", "2025-03-16", "2025-04-16")  # three months before agentic
last_w    <- c("2025-12-16", "2026-01-16", "2026-02-16")  # last three months of data
ages      <- c("1", "2", "3", "4")                   # decade age groups 21-30..51-60
age_lab   <- c("1" = "Early career (21--30)", "2" = "31--40",
               "3" = "41--50", "4" = "Senior (51--60)")

# ---- load counts, attach quintile ------------------------------------------
df <- read.csv(parsed, colClasses = c(yrke4 = "character", alder_gr = "character",
                                      date = "character"))
df <- df[df$variable == "count" & df$sekt == private & df$alder_gr %in% ages, ]
exp <- read.csv(exp_file, colClasses = c(styrk08 = "character"))
exp <- exp[!is.na(exp$quintile), c("styrk08", "quintile")]
names(exp) <- c("yrke4", "ai_q")
exp$ai_q <- as.integer(exp$ai_q)
df <- merge(df, exp, by = "yrke4")                   # inner join -> mapped occupations

# Seasonally adjusted, Oct-2022-indexed employment for one (age subset, quintile).
sa_index <- function(sub) {
  agg <- aggregate(value ~ date, data = sub, FUN = sum)  # headcount per month
  agg <- agg[order(agg$date), ]                          # date order
  v   <- seasonal_adjust(agg$date, agg$value, seas_from, seas_to)  # SA series
  base <- v[agg$date == norm_date]                       # October 2022 level
  data.frame(date = agg$date, idx = v / base)            # indexed to Oct 2022 = 1
}

# Q5 - Q1 gap (in index points) averaged over a set of months, for an age subset.
gap_in_window <- function(age_rows, months) {
  q1 <- sa_index(age_rows[age_rows$ai_q == 1, ])         # least-exposed index
  q5 <- sa_index(age_rows[age_rows$ai_q == 5, ])         # most-exposed index
  m1 <- mean(q1$idx[q1$date %in% months])                # Q1 mean over the window
  m5 <- mean(q5$idx[q5$date %in% months])                # Q5 mean over the window
  m5 - m1                                                # Q5 - Q1 gap
}

# ---- build one row per age group, plus a pooled (all ages) row -------------
groups <- c(as.list(ages), list(ages))                 # each age, then all ages
labels <- c(age_lab[ages], "All ages (21--60)")        # row labels
rows <- character(0)                                    # collected LaTeX lines
for (i in seq_along(groups)) {
  sub <- df[df$alder_gr %in% groups[[i]], ]             # this age group (or all)
  g_before <- gap_in_window(sub, before_w)              # Q5-Q1 gap, before window
  g_last   <- gap_in_window(sub, last_w)                # Q5-Q1 gap, last window
  rows <- c(rows, sprintf("%s & %+.2f & %+.2f & %+.2f \\\\",
                          labels[i], 100 * g_before, 100 * g_last,
                          100 * (g_last - g_before)))   # values in percentage points
  cat(sprintf("%-22s before %+.3f  last %+.3f  change %+.3f\n",
              labels[i], 100 * g_before, 100 * g_last, 100 * (g_last - g_before)))
}

# ---- assemble the LaTeX tabular fragment -----------------------------------
lines <- c(
  "\\begin{tabular}{lccc}",
  "\\toprule",
  " & \\multicolumn{2}{c}{Q5$-$Q1 gap (pp)} & \\\\",
  "\\cmidrule(lr){2-3}",
  " & Before & Last three & Change \\\\",
  " & (Feb--Apr 2025) & (Dec 2025--Feb 2026) & \\\\",
  "\\midrule",
  rows[1:4],                                           # the four decade age groups
  "\\addlinespace",
  rows[5],                                             # the pooled all-ages row
  "\\bottomrule",
  "\\end{tabular}")

dir.create(dirname(out_file), showWarnings = FALSE, recursive = TRUE)
writeLines(lines, out_file)                            # write the tabular fragment
cat(sprintf("Wrote %s\n", out_file))
