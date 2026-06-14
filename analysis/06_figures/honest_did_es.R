# =============================================================================
# honest_did_es.R : Rambachan-Roth honest CI PER POST-KVARTAL (HonestDiD)
#                   langs den kvartalsaggregerte event-study-banen,
#                   Q5 vs Q3, per decade age group.
# =============================================================================
# Som honest_did_full_preseas.R (samme estimering, aggregering og to
# design), men l_vec = enhetsvektor per post-kvartal, slik at honest-
# settene kan tegnes langs ES-banen:
#   chatgpt : ref okt 2022, pre 2021q1..2022q3, post 2022q4..2026q1 (14).
#             Delta^SDRM Mbar = 0 (ren lineaer trendvidereforing).
#   agentic : re-anket april 2025, pre 2023q3..2025q1, post 4 kvartaler.
#             Delta^SDRM Mbar = 0 og 1.
# I tillegg lagres den kvartalsaggregerte banen (coef, se) for plotting.
#
# CLI args: args[1] = age_group (1..4, default alle)
# Output: analysis/output/coefficients/coef_honest_did_es.csv
#   delta = "path"     : kvartalsbane (alle kvartaler; Mbar = NA)
#   delta = "original" : konvensjonelt 95%-KI per post-kvartal
#   delta = "SDRM"     : honest CI per post-kvartal og Mbar
# =============================================================================

suppressMessages({ library(data.table); library(fixest); library(HonestDiD) })

args <- commandArgs(trailingOnly = TRUE)
ALDER_KEEP <- if (length(args) >= 1) args[1] else c("1", "2", "3", "4")

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_honest_did_es.csv")

REF_YM_INT <- 2022L * 12L + 10L
SEAS_FROM  <- as.IDate("2021-01-16")
SEAS_TO    <- as.IDate("2024-12-16")

cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                     alder_gr = "character",
                                     sekt = "integer",
                                     variable = "character",
                                     value = "numeric"))
d <- d[variable == "count" & sekt == 2L & alder_gr %in% c("1","2","3","4")]
d[, date := as.IDate(date)]
d[, ym_int := year(date) * 12L + month(date)]
d[, k := as.integer(ym_int - (REF_YM_INT + 1L))]
d[, t := as.integer(ym_int - REF_YM_INT)]
d[, cal_month := month(date)]
d <- d[, .(count = value, date, yrke4, alder_gr, k, t, cal_month)]

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
stopifnot(all(nchar(exp$styrk08) == 4L))
exp <- exp[!is.na(quintile), .(yrke4 = styrk08, ai_q = as.integer(quintile))]
d <- merge(d, exp, by = "yrke4")

t_to_calm <- unique(d[, .(t, k, cal_month, date)])

balance <- function(sub) {
    grid <- CJ(yrke4 = unique(sub$yrke4), t = sort(unique(sub$t)))
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4")
    grid <- merge(grid, t_to_calm, by = "t")
    out <- merge(grid, sub[, .(yrke4, t, count)],
                 by = c("yrke4", "t"), all.x = TRUE)
    out[is.na(count), count := 0]
    out[, q_m_key := paste0(ai_q, "_", cal_month)]
    out[, ai_q_f := factor(ai_q, levels = 1:5)]
    out
}

kvec <- c(-22:-2, 0:39)
k_dates <- seq(as.Date("2021-01-16"), as.Date("2026-02-16"), by = "month")
kd <- data.table(date = k_dates)
kd[, k := as.integer(format(date, "%Y")) * 12L +
         as.integer(format(date, "%m")) - (REF_YM_INT + 1L)]
kd <- kd[k %in% kvec]
kd[, quarter := paste0(format(date, "%Y"), "q",
                       (as.integer(format(date, "%m")) - 1L) %/% 3L + 1L)]

agg_matrix <- function(kd_sub) {
    qs <- unique(kd_sub$quarter)
    Bm <- matrix(0, nrow = length(qs), ncol = length(kvec),
                 dimnames = list(qs, paste0("k", kvec)))
    for (i in seq_len(nrow(kd_sub))) {
        Bm[kd_sub$quarter[i], paste0("k", kd_sub$k[i])] <-
            1 / sum(kd_sub$quarter == kd_sub$quarter[i])
    }
    Bm
}

designs <- list(
    chatgpt = list(kd_sub = kd, n_pre = 7L, n_post = 14L,
                   reanchor_k = NA_integer_, Mbarvec = c(0),
                   grid_lim = 1.5),
    agentic = list(kd_sub = kd[date >= as.Date("2023-07-16") & k != 29L],
                   n_pre = 7L, n_post = 4L,
                   reanchor_k = 29L, Mbarvec = c(0, 1),
                   grid_lim = 0.75))

rows <- list()
for (a in ALDER_KEEP) {
    cat(sprintf("\n=== age group %s ===\n", a))
    sub_seas <- balance(d[alder_gr == a & date >= SEAS_FROM & date <= SEAS_TO])
    fit_pre <- fepois(count ~ i(ai_q_f, t, ref = "3") | yrke4 + t + q_m_key,
                      data = sub_seas, warn = FALSE, notes = FALSE)
    seas_fe <- fixef(fit_pre)[["q_m_key"]]
    seas_dt <- data.table(q_m_key = names(seas_fe), seas = as.numeric(seas_fe))
    seas_dt[, q := sub("_.*", "", q_m_key)]
    seas_dt[, seas := seas - mean(seas), by = q]

    sub <- balance(d[alder_gr == a])
    sub <- merge(sub, seas_dt[, .(q_m_key, seas)], by = "q_m_key",
                 all.x = TRUE, sort = FALSE)
    fit <- fepois(count ~ i(k, ai_q_f, ref = -1, ref2 = "3") | yrke4 + k,
                  data = sub, offset = ~seas, cluster = ~yrke4,
                  warn = FALSE, notes = FALSE)

    nm <- sprintf("k::%d:ai_q_f::5", kvec)
    beta_m  <- coef(fit)[nm]
    sigma_m <- vcov(fit)[nm, nm]

    for (dn in names(designs)) {
        ds <- designs[[dn]]
        Bm <- agg_matrix(ds$kd_sub)
        if (!is.na(ds$reanchor_k)) {
            Bm[, paste0("k", ds$reanchor_k)] <-
                Bm[, paste0("k", ds$reanchor_k)] - 1
        }
        betahat <- as.numeric(Bm %*% beta_m)
        sigma   <- Bm %*% sigma_m %*% t(Bm)
        sigma   <- (sigma + t(sigma)) / 2
        qs <- rownames(Bm)
        stopifnot(length(qs) == ds$n_pre + ds$n_post)

        rows[[paste(a, dn, "path")]] <- data.table(
            age_group = as.integer(a), design = dn, quarter = qs,
            post_idx = c(rep(NA_integer_, ds$n_pre), seq_len(ds$n_post)),
            delta = "path", Mbar = NA_real_,
            lb = betahat - 1.96 * sqrt(diag(sigma)),
            ub = betahat + 1.96 * sqrt(diag(sigma)),
            coef = betahat)

        for (i in seq_len(ds$n_post)) {
            l_vec <- rep(0, ds$n_post); l_vec[i] <- 1
            qlab <- qs[ds$n_pre + i]
            orig <- HonestDiD::constructOriginalCS(
                betahat = betahat, sigma = sigma,
                numPrePeriods = ds$n_pre, numPostPeriods = ds$n_post,
                l_vec = l_vec)
            rows[[paste(a, dn, qlab, "orig")]] <- data.table(
                age_group = as.integer(a), design = dn, quarter = qlab,
                post_idx = i, delta = "original", Mbar = NA_real_,
                lb = as.numeric(orig$lb), ub = as.numeric(orig$ub),
                coef = NA_real_)

            res <- tryCatch(
                HonestDiD::createSensitivityResults_relativeMagnitudes(
                    betahat = betahat, sigma = sigma,
                    numPrePeriods = ds$n_pre, numPostPeriods = ds$n_post,
                    bound = "deviation from linear trend",
                    Mbarvec = ds$Mbarvec, l_vec = l_vec,
                    gridPoints = 400L,
                    grid.lb = -ds$grid_lim, grid.ub = ds$grid_lim),
                error = function(e) {
                    cat(sprintf("  [%s %s] SDRM failed: %s\n",
                                dn, qlab, conditionMessage(e))); NULL })
            if (is.null(res)) next
            res <- as.data.table(res)
            rows[[paste(a, dn, qlab, "SDRM")]] <- data.table(
                age_group = as.integer(a), design = dn, quarter = qlab,
                post_idx = i, delta = "SDRM", Mbar = as.numeric(res$Mbar),
                lb = as.numeric(res$lb), ub = as.numeric(res$ub),
                coef = NA_real_)
            cat(sprintf("  [%s %s] ok\n", dn, qlab))
        }
    }
}

out <- rbindlist(rows, fill = TRUE)
setorder(out, age_group, design, post_idx, delta, Mbar, na.last = FALSE)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
