# =============================================================================
# honest_did_full_preseas.R : Rambachan-Roth (2023) honest DiD (HonestDiD-
#                             pakken) paa full-vindu preseas-justert ES,
#                             Q5 vs Q3, per decade age group.
# =============================================================================
# Motivasjon: default Delta^RM tillater at bruddet paa parallelle trender
# bytter fortegn fritt fra foerste post-periode. Vi bruker derfor
# Delta^SDRM (bound = "deviation from linear trend"): kontrafaktisk bane
# = videreFOERT lineaer pre-trend, avvik begrenses relativt til stoerste
# pre-periode andre-differanse. Mbar = 0 gir ren lineaer ekstrapolering.
#
# To design fra SAMME estimerte ES (re-anking via delta-metoden):
#   chatgpt : ref okt 2022. Pre 2021q1..2022q3 (7 kv), post 2022q4..2026q1
#             (14 kv). Target: snitt 2023q1..2025q1 ("mid"). Med bratt
#             pre-trend kumulerer helningsusikkerheten over horisonten -
#             brede baand ER det aerlige svaret her.
#   agentic : re-anket til april 2025 (beta'_k = beta_k - beta_{apr25}).
#             Pre = stabil mellomperiode 2023q3..2025q1 (7 kv), post =
#             2025q2' (mai-jun), 2025q3, 2025q4, 2026q1 (4 kv). Target:
#             snitt av alle 4. Flat pre-trend og lav krumning gjoer
#             Delta^SDRM informativ for akkurat trendbruddet vi ser.
#
# Estimering som microdata_es_decade_q3_full_preseas.R (s2124-offset),
# med full cluster-vcov for Q5 x k. Kvartalsaggregering og re-anking er
# lineaere transformasjoner av (beta, vcov).
#
# CLI args: args[1] = age_group (1..4, default alle)
# Output: analysis/output/coefficients/coef_honest_did_full_preseas.csv
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
                       "coef_honest_did_full_preseas.csv")

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

# Aggregeringsmatrise over et utvalg maaneder: snitt innen kvartal.
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

# Design-definisjoner.
designs <- list(
    chatgpt = list(
        kd_sub = kd,                              # alle 61 maaneder
        n_pre = 7L, n_post = 14L,
        reanchor_k = NA_integer_,
        targets = list(mid = { l <- rep(0, 14); l[2:10] <- 1/9; l }),
        Mbarvec = c(0, 0.5, 1),
        grid_lim = 1.0),
    agentic = list(
        kd_sub = kd[date >= as.Date("2023-07-16") & k != 29L],
        n_pre = 7L, n_post = 4L,
        reanchor_k = 29L,                          # april 2025
        targets = list(post = { l <- rep(0, 4); l[1:4] <- 1/4; l }),
        Mbarvec = c(0, 0.5, 1, 2),
        grid_lim = 0.5))

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
    stopifnot(all(nm %in% names(coef(fit))))
    beta_m  <- coef(fit)[nm]
    sigma_m <- vcov(fit)[nm, nm]

    for (dn in names(designs)) {
        ds <- designs[[dn]]
        Bm <- agg_matrix(ds$kd_sub)
        if (!is.na(ds$reanchor_k)) {
            # Re-anking: beta'_k = beta_k - beta_{ref}; rad i Bm trekker
            # fra referansemaaneden (lineaer transformasjon).
            Bm[, paste0("k", ds$reanchor_k)] <-
                Bm[, paste0("k", ds$reanchor_k)] - 1
        }
        betahat <- as.numeric(Bm %*% beta_m)
        sigma   <- Bm %*% sigma_m %*% t(Bm)
        sigma   <- (sigma + t(sigma)) / 2
        stopifnot(nrow(Bm) == ds$n_pre + ds$n_post)

        for (tgt in names(ds$targets)) {
            l_vec <- ds$targets[[tgt]]
            orig <- HonestDiD::constructOriginalCS(
                betahat = betahat, sigma = sigma,
                numPrePeriods = ds$n_pre, numPostPeriods = ds$n_post,
                l_vec = l_vec)
            rows[[paste(a, dn, tgt, "orig")]] <- data.table(
                age_group = as.integer(a), design = dn, target = tgt,
                delta = "original", Mbar = NA_real_,
                lb = as.numeric(orig$lb), ub = as.numeric(orig$ub))
            cat(sprintf("  [%s/%s] original CI: [%+.4f, %+.4f]\n",
                        dn, tgt, orig$lb, orig$ub))

            for (bnd in c("deviation from linear trend",
                          "deviation from parallel trends")) {
                lab <- ifelse(bnd == "deviation from linear trend",
                              "SDRM", "RM")
                mb <- if (lab == "RM") setdiff(ds$Mbarvec, 0) else ds$Mbarvec
                res <- tryCatch(
                    HonestDiD::createSensitivityResults_relativeMagnitudes(
                        betahat = betahat, sigma = sigma,
                        numPrePeriods = ds$n_pre, numPostPeriods = ds$n_post,
                        bound = bnd, Mbarvec = mb, l_vec = l_vec,
                        gridPoints = 400L,
                        grid.lb = -ds$grid_lim, grid.ub = ds$grid_lim),
                    error = function(e) {
                        cat(sprintf("  [%s/%s] %s failed: %s\n",
                                    dn, tgt, lab, conditionMessage(e)))
                        NULL })
                if (is.null(res)) next
                res <- as.data.table(res)
                rows[[paste(a, dn, tgt, lab)]] <- data.table(
                    age_group = as.integer(a), design = dn, target = tgt,
                    delta = lab, Mbar = as.numeric(res$Mbar),
                    lb = as.numeric(res$lb), ub = as.numeric(res$ub))
                for (i in seq_len(nrow(res)))
                    cat(sprintf("  [%s/%s] %s Mbar=%.1f: [%+.4f, %+.4f]\n",
                                dn, tgt, lab, res$Mbar[i],
                                res$lb[i], res$ub[i]))
            }
        }
    }
}

out <- rbindlist(rows, fill = TRUE)
setorder(out, age_group, design, target, delta, Mbar, na.last = FALSE)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
