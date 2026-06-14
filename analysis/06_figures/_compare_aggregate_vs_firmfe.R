user_lib <- "C:/Users/Øystein M. Hernæs/R/win-library/4.1"
if (dir.exists(user_lib)) .libPaths(c(user_lib, .libPaths()))
suppressMessages(library(data.table))

BASE <- getwd()  # invoke from project root

agg  <- fread(file = file.path(BASE,
        "analysis/output/coefficients/coef_microdata_poisson_es_R.csv"))
firm <- fread(file = file.path(BASE,
        "analysis-indiv/from_secure_server/coefficients/coef_event_study_fepois.csv"))

# firm has columns: sample, age_bin, k, ai_q, coef, se, n_obs, n_frtk
# agg  has columns: age_bin, ai_q, k, coef, se, n_obs, n_occ
firm <- firm[, .(age_bin, ai_q, k, coef, se, n_obs, n_unit = n_frtk)]
agg  <- agg [, .(age_bin, ai_q, k, coef, se, n_obs, n_unit = n_occ)]

firm[, model := "firm_FE_indiv"]
agg [, model := "aggregate_microdata"]

both <- rbindlist(list(agg, firm))

AGE_LABELS <- c("22-25","26-30","31-34","35-40","41-49","50+")

cat("\n=================================================================\n")
cat("PANEL DIMENSIONS\n")
cat("=================================================================\n")
print(both[, .(n_obs = mean(n_obs), n_units = mean(n_unit),
               k_min = min(k), k_max = max(k)),
           by = .(model, age_bin)])

cat("\n=================================================================\n")
cat("MEAN POST-PERIOD Q5 COEFFICIENT (log-points x 100)\n")
cat("=================================================================\n")
summ <- both[ai_q == 5 & k > -1,
             .(mean_post_q5_pct = round(mean(coef) * 100, 2),
               mean_post_q5_se  = round(sqrt(mean(se^2)) * 100, 2),
               k_range          = paste0(min(k), "..", max(k))),
             by = .(model, age_bin)]
summ[, age_label := AGE_LABELS[age_bin]]
setorder(summ, age_bin, model)
print(summ[, .(age_bin, age_label, model, k_range,
               mean_post_q5_pct, mean_post_q5_se)])

cat("\n=================================================================\n")
cat("Q5 vs Q1 EVENT-STUDY COEFS AT k = 0, 6, 12, 18, 24 (log-points x 100)\n")
cat("=================================================================\n")
snap <- both[ai_q == 5 & k %in% c(0, 6, 12, 18, 24),
             .(model, age_bin, k, coef_pct = round(coef * 100, 2),
               se_pct = round(se * 100, 2))]
snap[, age_label := AGE_LABELS[age_bin]]
setorder(snap, age_bin, k, model)
print(snap)

cat("\n=================================================================\n")
cat("HEADLINE TABLE: PER-AGE-BIN Q vs Q1 IN COMMON POST WINDOW (k = 1..32)\n")
cat("=================================================================\n")
# Common k window: analysis-indiv runs to ym = 2025m7 => k_max = 33
# aggregate runs to ym = 2026m2 => k_max = 39
COMMON_K_MAX <- 33L
table_rows <- both[k > 0 & k <= COMMON_K_MAX,
                   .(coef_pct = round(mean(coef) * 100, 2),
                     se_pct   = round(sqrt(mean(se^2)) * 100, 2)),
                   by = .(model, age_bin, ai_q)]
wide <- dcast(table_rows, age_bin + ai_q ~ model, value.var = c("coef_pct","se_pct"))
wide[, age_label := AGE_LABELS[age_bin]]
setcolorder(wide, c("age_bin","age_label","ai_q"))
print(wide)
