user_lib <- "C:/Users/Øystein M. Hernæs/R/win-library/4.1"
if (dir.exists(user_lib)) .libPaths(c(user_lib, .libPaths()))
suppressMessages(library(data.table))

BASE <- getwd()

emp <- fread(file = file.path(BASE,
        "data/04_occ_agem_sector_count_2021_2026.csv"))
pop <- fread(file = file.path(BASE,
        "data/macro/ssb_population_by_age_quarterly.csv"))

# ---- Employment by (sekt, alder_gr, date) -----------------------------------
emp <- emp[variable == "count"]
emp[, value := as.integer(value)]
emp[, sekt := as.integer(sekt)]
emp[, alder_gr := as.integer(alder_gr)]
emp <- emp[alder_gr %in% c(2, 3)]
emp <- emp[!is.na(sekt)]
emp[, date := as.IDate(date)]
emp[, ym := paste0(year(date), "-Q",
                   ceiling(month(date) / 3))]

# Aggregate over yrke4 to monthly (date, sekt, alder_gr) ...
emp_msa <- emp[, .(emp = sum(value, na.rm = TRUE)),
               by = .(date, ym, sekt, alder_gr)]
# ... then average across months within quarter
emp_sa <- emp_msa[, .(emp = mean(emp)),
                  by = .(ym, sekt, alder_gr)]
# Pool over sectors for the all-sectors total
emp_ma <- emp[, .(emp = sum(value, na.rm = TRUE)),
              by = .(date, ym, alder_gr)]
emp_a  <- emp_ma[, .(emp = mean(emp)),
                 by = .(ym, alder_gr)]
emp_a[, sekt := 0L]   # 0 = all sectors

emp_all <- rbindlist(list(emp_sa, emp_a), use.names = TRUE)

# ---- Population by alder_gr (sum 1-year ages within bin) --------------------
# alder_gr definition: 2 = 22-25, 3 = 26-30
pop[, ages := as.integer(age)]
pop[, alder_gr := fifelse(ages %in% 22:25, 2L,
                  fifelse(ages %in% 26:30, 3L, NA_integer_))]
pop <- pop[!is.na(alder_gr)]

pop_agg <- pop[, .(pop = sum(population)), by = .(date, alder_gr)]
setnames(pop_agg, "date", "ym")

# ---- Merge, compute share ---------------------------------------------------
m <- merge(emp_all, pop_agg, by = c("ym", "alder_gr"))
m[, share := emp / pop]

SEKT_LBL <- c("0" = "all sectors", "1" = "state",
              "2" = "municipal", "3" = "private")
AGE_LBL  <- c("2" = "22-25", "3" = "26-30")

# Average across quarters
avg <- m[, .(emp_avg = round(mean(emp)),
             pop_avg = round(mean(pop)),
             share   = round(mean(share), 3)),
         by = .(sekt, alder_gr)]
avg[, sektor := SEKT_LBL[as.character(sekt)]]
avg[, age    := AGE_LBL[as.character(alder_gr)]]
setorder(avg, sekt, alder_gr)

cat("\n=== Mean quarterly employment vs population, by sector and age ===\n")
print(avg[, .(sektor, age, emp_avg, pop_avg, share)])

# Pooled 22-30
m_pooled <- m[, .(emp = sum(emp), pop = sum(pop)),
              by = .(ym, sekt)]
m_pooled[, share := emp / pop]
avg_p <- m_pooled[, .(emp_avg = round(mean(emp)),
                      pop_avg = round(mean(pop)),
                      share   = round(mean(share), 3)),
                  by = sekt]
avg_p[, sektor := SEKT_LBL[as.character(sekt)]]
setorder(avg_p, sekt)
cat("\n=== Pooled 22-30, mean quarterly emp vs pop ===\n")
print(avg_p[, .(sektor, emp_avg, pop_avg, share)])
