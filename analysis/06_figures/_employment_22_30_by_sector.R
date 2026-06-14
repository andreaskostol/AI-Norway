user_lib <- "C:/Users/Øystein M. Hernæs/R/win-library/4.1"
if (dir.exists(user_lib)) .libPaths(c(user_lib, .libPaths()))
suppressMessages(library(data.table))

BASE <- getwd()
d <- fread(file = file.path(BASE,
        "data/04_occ_agem_sector_count_2021_2026.csv"))

# sekt codes: SSB institusjonell sektor (per CLAUDE.md):
#   1: state (1110, 1120, 6100) — collapsed to 1
#   2: municipal (1510, 1520, 6500) — collapsed to 2
#   3: private (alt annet)
# alder_gr: 1 = <=21, 2 = 22-25, 3 = 26-30, 4 = 31-34, 5 = 35-40, 6 = 41-49,
#   7 = 50-59, 8 = 60-69, 9 = 70+

d <- d[variable == "count"]
d[, value := as.integer(value)]
d[, sekt := as.integer(sekt)]
d[, alder_gr := as.integer(alder_gr)]
d <- d[alder_gr %in% c(2, 3)]   # 22-25 and 26-30
d <- d[!is.na(sekt)]

# Aggregate over yrke4 to get total employment per (sekt, alder_gr, month)
tot <- d[, .(emp = sum(value, na.rm = TRUE)),
         by = .(date, sekt, alder_gr)]

SEKT_LBL <- c("1" = "state (1)", "2" = "municipal (2)", "3" = "private (3)")
AGE_LBL  <- c("2" = "22-25", "3" = "26-30")

# Average across months in panel
avg <- tot[, .(mean_emp = round(mean(emp))),
           by = .(sekt, alder_gr)]
avg[, sektor := SEKT_LBL[as.character(sekt)]]
avg[, age    := AGE_LBL[as.character(alder_gr)]]
setorder(avg, sekt, alder_gr)
cat("\n=== Mean monthly employment by sector and age group (2021m1..2026m2) ===\n")
print(avg[, .(sektor, age, mean_emp)])

# Pooled across the two age groups
pooled <- tot[, .(emp = sum(emp)), by = .(date, sekt)
              ][, .(mean_emp_22_30 = round(mean(emp))), by = sekt]
pooled[, sektor := SEKT_LBL[as.character(sekt)]]
setorder(pooled, sekt)
cat("\n=== Pooled 22-30 mean monthly employment by sector ===\n")
print(pooled[, .(sektor, mean_emp_22_30)])

# Wide format for easy reading
wide <- dcast(avg, sektor ~ age, value.var = "mean_emp")
wide[, total_22_30 := `22-25` + `26-30`]
wide[, share_22_25 := round(`22-25` / total_22_30, 3)]
cat("\n=== Wide format ===\n")
print(wide)
