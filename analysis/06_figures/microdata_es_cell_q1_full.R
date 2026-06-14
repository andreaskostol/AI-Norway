# =============================================================================
# microdata_es_cell_q1_full.R : raw cell-spec event study on microdata.no
# =============================================================================
# Event-study (full gamma_{q,k} path) analog of microdata_did_cell.R, on the
# SAME spec as the register cell event study 6f_event_study_cellspec.R:
#   log E[count_{j,t}] = alpha_j + beta_t
#                      + sum_{q != 1, k != -1} gamma_{q,k} 1{ai_q(j)=q} 1{t-t0=k}
#   j = yrke4; yrke4 + month FE; cluster yrke4; reference q = 1 (BCC),
#   k = -1 (Oct 2022); FULL window; employment (count).
#
# This is the microdata.no column of the event-study comparison (DESIGN_CHOICES
# section 22): raw Poisson, NOT seasonally adjusted, so it overlays apples-to-
# apples with the raw register event studies 6 (firm-FE) and 6f (cell-spec).
# For the SA / bootstrapped microdata path see microdata_es_decade_q1_full_preseas_boot.R.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_es_cell_q1_full.csv
#         (schema: sector, age_group, ai_q, k, coef, se, n_obs, n_occ)
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE      <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure", "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_es_cell_q1_full.csv")
stopifnot(file.exists(DATA_FILE), file.exists(EXP_FILE))

REF_YM_INT  <- 2022L * 12L + 10L            # October 2022 = k = -1
EVENT_ZERO  <- REF_YM_INT + 1L              # November 2022 = k = 0
CUTOFF_DATE <- as.IDate("2026-02-16")
ALDER_KEEP  <- c("1", "2", "3", "4")
SECTORS     <- c(2L, 1L)                    # 2 = private (main), 1 = public

# ---- Load + reshape ---------------------------------------------------------
cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character", alder_gr = "character",
                                     sekt = "integer", variable = "character",
                                     value = "numeric"))
d[, date := as.IDate(date)]
d <- d[date <= CUTOFF_DATE & alder_gr %in% ALDER_KEEP]
w <- dcast(d, date + yrke4 + alder_gr + sekt ~ variable, value.var = "value")
w[, ym_int := year(date) * 12L + month(date)]

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
exp[, yrke4 := sprintf("%04s", styrk08)]
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]
w <- merge(w, exp, by = "yrke4")            # inner join (drops unmapped)

# ---- Balance (yrke4 x ym) within a slice, zero-fill, add event time ---------
balance_counts <- function(sub) {
    grid <- CJ(yrke4 = unique(sub$yrke4), ym_int = sort(unique(sub$ym_int)))
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4", all.x = TRUE)
    src  <- sub[, .(val = count), by = .(yrke4, ym_int)]
    out  <- merge(grid, src, by = c("yrke4", "ym_int"), all.x = TRUE)
    out[is.na(val), val := 0]
    out[, ai_q   := factor(ai_q, levels = 1:5)]
    out[, kshift := as.integer(ym_int - EVENT_ZERO)]
    out
}

parse_kq <- function(nm) {
    m <- regmatches(nm, regexec("kshift::(-?[0-9]+):ai_q::([0-9]+)", nm))
    out <- do.call(rbind, lapply(m, function(x)
        if (length(x) == 3) c(as.integer(x[2]), as.integer(x[3]))
        else c(NA_integer_, NA_integer_)))
    colnames(out) <- c("k", "ai_q"); as.data.table(out)
}

# ---- Estimate: sector x age group -------------------------------------------
rows <- list()
for (sec in SECTORS) {
    for (a in ALDER_KEEP) {
        bc <- balance_counts(w[sekt == sec & alder_gr == a])
        fit <- tryCatch(
            fepois(val ~ i(kshift, ai_q, ref = -1, ref2 = "1") | yrke4 + ym_int,
                   data = bc, cluster = ~yrke4),
            error = function(e) { cat(sprintf("  sec %d age %s failed: %s\n",
                                              sec, a, conditionMessage(e))); NULL })
        if (is.null(fit)) next
        ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
        kq <- parse_kq(ct$name); ct$k <- kq$k; ct$ai_q <- kq$ai_q
        ct <- ct[!is.na(ct$k), ]
        rows[[length(rows) + 1L]] <- data.table(
            sector = sec, age_group = as.integer(a), ai_q = ct$ai_q, k = ct$k,
            coef = ct[, "Estimate"], se = ct[, "Std. Error"],
            n_obs = nrow(bc), n_occ = uniqueN(bc$yrke4))
        cat(sprintf("  sec %d age %s: %d coefs, %d occ\n",
                    sec, a, nrow(ct), uniqueN(bc$yrke4)))
    }
}

out <- rbindlist(rows, fill = TRUE)
setorder(out, sector, age_group, ai_q, k)
fwrite(out, OUT_CSV)
cat(sprintf("Saved %d rows to %s\n", nrow(out), OUT_CSV))
