# =============================================================================
# microdata_es_decade.R : Poisson event-study on the cell-level employment
#                         counts, by decade age group, private sector
#                         (Q1-REFERENCE BACKUP VARIANT)
# =============================================================================
# Decade-group / private-sector version of microdata_poisson_es.R, run on the
# new parsed file. Dynamic companion to the collapsed DiD in
# microdata_did_cell.R.
#
# Preferred headline spec uses Q3 as the reference quintile to avoid Q1's
# winter-construction seasonality, see microdata_es_decade_q3.R. This Q1-
# referenced version is retained for the backup figure
# (figure_microdata_poisson_es_grid.pdf) and side-by-side comparison.
#
# Spec (per decade age group a):
#   log E[count_{j,t}] = alpha_j + beta_t
#                     + sum_{q in 2..5, k != -1} gamma_{q,k} 1{ai_q(j)=q} 1{k(t)=k}
#   j = 4-digit STYRK-08; t = month; k = months since October 2022 (ref k=-1).
#   Cluster SE at occupation. Private sector, through 2026m2.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_es_decade.csv
#           (age_group, ai_q, k, coef, se, n_obs, n_occ)
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_es_decade.csv")

REF_YM_INT  <- 2022L * 12L + 10L          # October 2022
CUTOFF_DATE <- as.IDate("2026-02-16")     # through 2026m2
ALDER_KEEP  <- c("1", "2", "3", "4")

cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character", alder_gr = "character",
                                     sekt = "integer", variable = "character",
                                     value = "numeric"))
d <- d[variable == "count" & sekt == 2L & alder_gr %in% ALDER_KEEP]
d[, date := as.IDate(date)]
d <- d[date <= CUTOFF_DATE]
d[, ym_int := year(date) * 12L + month(date)]
d[, k := as.integer(ym_int - (REF_YM_INT + 1L))]   # Oct 2022 = k = -1
d <- d[, .(count = value, yrke4, alder_gr, k)]

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
exp[, yrke4 := sprintf("%04s", styrk08)]
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]
d <- merge(d, exp, by = "yrke4")

balance <- function(sub) {
    yrke4s <- unique(sub$yrke4); ks <- sort(unique(sub$k))
    grid <- CJ(yrke4 = yrke4s, k = ks)
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4", all.x = TRUE)
    out <- merge(grid, sub[, .(yrke4, k, count)], by = c("yrke4", "k"), all.x = TRUE)
    out[is.na(count), count := 0]
    out[, ai_q := factor(ai_q, levels = 1:5)]
    out
}

coef_rows <- list()
for (a in ALDER_KEEP) {
    sub <- balance(d[alder_gr == a])
    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("\n--- age group %s, n=%d, n_occ=%d ---\n", a, n_obs, n_occ))
    fit <- tryCatch(
        fepois(count ~ i(k, ai_q, ref = -1, ref2 = "1") | yrke4 + k,
               data = sub, cluster = ~yrke4),
        error = function(e) { cat("  fepois failed:", conditionMessage(e), "\n"); NULL })
    if (is.null(fit)) next
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    m <- regmatches(ct$name, regexec("k::(-?[0-9]+):ai_q::([0-9]+)", ct$name))
    parsed <- do.call(rbind, lapply(m, function(x)
        if (length(x) == 3) c(as.integer(x[2]), as.integer(x[3])) else c(NA, NA)))
    ct$k <- parsed[, 1]; ct$ai_q <- parsed[, 2]
    ct <- ct[!is.na(ct$k), ]
    cr <- data.table(age_group = as.integer(a), ai_q = ct$ai_q, k = ct$k,
                     coef = ct[, "Estimate"], se = ct[, "Std. Error"],
                     n_obs = n_obs, n_occ = n_occ)
    ref_rows <- data.table(age_group = as.integer(a), ai_q = 2:5, k = -1L,
                           coef = 0, se = 0, n_obs = n_obs, n_occ = n_occ)
    coef_rows[[a]] <- rbindlist(list(cr, ref_rows))
    cat(sprintf("  harvested %d coefs\n", nrow(cr)))
}

out <- rbindlist(coef_rows)
setorder(out, age_group, ai_q, k)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
