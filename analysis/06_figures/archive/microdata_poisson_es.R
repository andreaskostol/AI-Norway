# =============================================================================
# microdata_poisson_es.R : Poisson event-study on the microdata.no cell-level
#                         employment counts, by age bin
# =============================================================================
# R counterpart to plot_microdata_poisson_es.py. Same data, same spec, same
# reference, same cluster — written in fixest::fepois so it lines up with the
# firm-FE Poisson estimator in analysis-indiv/scripts/6_event_study_fepois.R.
#
# Spec (per age bin a):
#   log E[count_{j,t}] = alpha_j + beta_t
#                     + sum_{q in {2..5}, k != -1} gamma_{q,k}
#                       * 1{ai_q(j) = q} * 1{k(t) = k}
#   j = 4-digit STYRK-08 occupation; t = month; k = months since October 2022
#   Reference: ai_q = 1, k = -1. Cluster SE at occupation.
#
# Input:  data/01_occ_agemonth_count_2021_2026.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_poisson_es_R.csv
# =============================================================================

# Make sure user library is on path (Windows R 4.1)
user_lib <- "C:/Users/Øystein M. Hernæs/R/win-library/4.1"
if (dir.exists(user_lib)) .libPaths(c(user_lib, .libPaths()))

suppressMessages({
    library(data.table)
    library(fixest)
})

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
BASE <- getwd()
if (!file.exists(file.path(BASE, "data", "01_occ_agemonth_count_2021_2026.csv"))) {
    BASE <- "c:/Frischsenteret Dropbox/Øystein Hernæs/Research Hernaes/AI-Norway"
}
DATA_FILE <- file.path(BASE, "data", "01_occ_agemonth_count_2021_2026.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_poisson_es_R.csv")

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
# alder_gr -> age_bin (50+ = alder_gr 7 + 8; matches Python script)
ALDER_GR_TO_BIN <- c("2"=1, "3"=2, "4"=3, "5"=4, "6"=5, "7"=6, "8"=6)

REF_K       <- -1L                  # October 2022 = k = -1
REF_YM_INT  <- 2022L * 12L + 10L    # ym integer for Oct 2022
QUINTILES   <- 2:5                  # Q1 omitted as reference

# -----------------------------------------------------------------------------
# Load + prep
# -----------------------------------------------------------------------------
cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                     alder_gr = "character"))
d[, date := as.IDate(date)]
d[, ym_int := year(date) * 12L + month(date)]
d[, k := as.integer(ym_int - (REF_YM_INT + 1L))]
d[, age_bin := ALDER_GR_TO_BIN[alder_gr]]
d <- d[!is.na(age_bin)]
d[, age_bin := as.integer(age_bin)]

cat("Loading exposure mapping\n")
exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
exp[, yrke4 := sprintf("%04s", styrk08)]
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]

d <- merge(d, exp, by = "yrke4")
# Sum the alder_gr 7 and 8 rows that now both fall into age_bin 6
d <- d[, .(count = sum(count)),
       by = .(yrke4, ai_q, age_bin, k)]

cat(sprintf("Panel: %d rows, %d occupations, k range %d..%d\n",
            nrow(d), uniqueN(d$yrke4), min(d$k), max(d$k)))

# -----------------------------------------------------------------------------
# Balance panel within age bin: every (yrke4, k) cell present, missing -> 0
# -----------------------------------------------------------------------------
balance <- function(sub) {
    yrke4s <- unique(sub$yrke4)
    ks     <- sort(unique(sub$k))
    grid   <- CJ(yrke4 = yrke4s, k = ks)
    qmap   <- unique(sub[, .(yrke4, ai_q)])
    grid   <- merge(grid, qmap, by = "yrke4", all.x = TRUE)
    out    <- merge(grid, sub[, .(yrke4, k, count)],
                    by = c("yrke4", "k"), all.x = TRUE)
    out[is.na(count), count := 0L]
    out
}

# -----------------------------------------------------------------------------
# Per age bin: fit fepois, harvest interaction coefficients
# -----------------------------------------------------------------------------
coef_rows <- list()
for (a in sort(unique(d$age_bin))) {
    sub <- balance(d[age_bin == a])
    sub[, ai_q := factor(ai_q, levels = c(1, 2, 3, 4, 5))]
    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("\n--- age_bin = %d, n = %d, n_occ = %d ---\n",
                a, n_obs, n_occ))

    t0 <- Sys.time()
    fit <- tryCatch(
        fepois(count ~ i(k, ai_q, ref = REF_K, ref2 = "1") | yrke4 + k,
               data = sub, cluster = ~yrke4),
        error = function(e) {
            cat("  fepois failed:", conditionMessage(e), "\n"); NULL
        }
    )
    cat(sprintf("  fit time: %.1f s\n",
                as.numeric(Sys.time() - t0, units = "secs")))
    if (is.null(fit)) next

    ct <- as.data.frame(coeftable(fit))
    ct$name <- rownames(ct)
    m <- regmatches(ct$name, regexec("k::(-?[0-9]+):ai_q::([0-9]+)", ct$name))
    parsed <- do.call(rbind, lapply(m, function(x) {
        if (length(x) == 3) c(as.integer(x[2]), as.integer(x[3]))
        else                 c(NA_integer_, NA_integer_)
    }))
    ct$k    <- parsed[, 1]
    ct$ai_q <- parsed[, 2]
    ct <- ct[!is.na(ct$k), ]

    cr <- data.table(
        age_bin = a,
        ai_q    = ct$ai_q,
        k       = ct$k,
        coef    = ct[, "Estimate"],
        se      = ct[, "Std. Error"],
        n_obs   = n_obs,
        n_occ   = n_occ
    )

    # Reference row k=-1 with coef=0, se=0 for cleaner plotting
    ref_rows <- data.table(age_bin = a, ai_q = QUINTILES, k = REF_K,
                           coef = 0, se = 0, n_obs = n_obs, n_occ = n_occ)
    coef_rows[[as.character(a)]] <- rbindlist(list(cr, ref_rows))

    cat(sprintf("  harvested %d interaction coefs\n", nrow(cr)))
}

out <- rbindlist(coef_rows)
setorder(out, age_bin, ai_q, k)

dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
