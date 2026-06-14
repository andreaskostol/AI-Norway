# =============================================================================
# ca_int_variants.R : extended-M3 comparative-advantage model where the two
#   linear gradients are kept free and ONLY the interaction term is redefined.
# =============================================================================
#   log E[y] = a_j + b_t + d1 z(exp) Post + d2 z(lnw) Post + d3 INT Post
#
# Five INT variants (all occ x age constant; main effect absorbed by occ FE):
#   prod     : z(exp) * z(lnw)                         (current M3, saddle)
#   rect0    : max{z(exp),0} * max{z(lnw),0}           (both above mean)
#   rect1    : max{z(exp)-1,0} * max{z(lnw)-1,0}       (both above +1 SD: tail)
#   corner75 : 1{z(exp) >= p75 AND z(lnw) >= p75}      (joint upper-quartile)
#   corner80 : 1{z(exp) >= p80 AND z(lnw) >= p80}      (joint upper-quintile)
#
# z(exp) pooled across occupations (matches ES scripts); z(lnw) and the
# percentile cuts are within age group. For each timing (ChatGPT, agentic) and
# age group we run, per variant, BOTH:
#   ES  : i(k, .)  terms, k = -1 reference  -> event-study paths
#   DiD : i(kk, .) terms, POST collapsed, pre-months individual, k=-1 reference
# Private sector; occ + month FE; SE clustered at occupation; Poisson PPML.
#
# Output (analysis/output/coefficients/):
#   coef_ca_int_es[_<outcome>].csv     (timing,age,variant,term,k,coef,se,sd_int)
#   coef_ca_int_did[_<outcome>].csv    (timing,age,variant,term,coef,se,sd_int,n_occ)
#   coef_ca_int_did[_<outcome>]_modelstats.csv (timing,age,variant,nobs,n_clusters,pr2)
#   term in {exp, wage, int}.  Display per-SD: int effect = coef * sd_int.
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

args <- commandArgs(trailingOnly = TRUE)
OUTCOME <- if (length(args) >= 1) args[1] else "count"
stopifnot(OUTCOME %in% c("count", "nyjobb"))
SUF <- if (OUTCOME == "count") "" else paste0("_", OUTCOME)
MIN_COUNT <- 10L

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
WAGE_FILE <- file.path(BASE, "analysis", "output",
                       "occ_age_exp_wage_prechatgpt.csv")
CDIR <- file.path(BASE, "analysis", "output", "coefficients")
OUT_ES   <- file.path(CDIR, paste0("coef_ca_int_es",  SUF, ".csv"))
OUT_DID  <- file.path(CDIR, paste0("coef_ca_int_did", SUF, ".csv"))
OUT_STAT <- file.path(CDIR, paste0("coef_ca_int_did", SUF, "_modelstats.csv"))

ALDER_KEEP <- c("1", "2", "3", "4")
CONFIGS <- list(
    chatgpt = list(ref_ym = 2022L * 12L + 10L,
                   from = as.IDate("1900-01-01"), to = as.IDate("2025-04-16")),
    agentic = list(ref_ym = 2025L * 12L + 4L,
                   from = as.IDate("2023-07-16"), to = as.IDate("2100-01-01")))
INT_VARS <- c("prod", "rect0", "rect1", "corner75", "corner80")

cat(sprintf("OUTCOME = %s\n", OUTCOME))
vars_keep <- if (OUTCOME == "nyjobb") c("count", "ny_jobb") else "count"
raw <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                       alder_gr = "character",
                                       sekt = "integer",
                                       variable = "character",
                                       value = "numeric"))
raw <- raw[sekt == 2L & alder_gr %in% ALDER_KEEP & variable %in% vars_keep]
raw[, date := as.IDate(date)]
if (OUTCOME == "count") {
    dy <- raw[variable == "count", .(date, yrke4, alder_gr, y = value)]
} else {
    dw <- dcast(raw, date + yrke4 + alder_gr ~ variable, value.var = "value")
    dw <- dw[!is.na(count) & count >= MIN_COUNT & !is.na(ny_jobb)]
    dy <- dw[, .(date, yrke4, alder_gr, y = as.integer(round(count * ny_jobb)))]
}

beta <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
beta[, yrke4 := sprintf("%04d", as.integer(styrk08))]
beta <- beta[!is.na(eloundou_beta), .(yrke4, beta = as.numeric(eloundou_beta))]
beta <- unique(beta, by = "yrke4")
beta[, z_exp := (beta - mean(beta)) / sd(beta)]    # pooled

wage <- fread(WAGE_FILE, colClasses = c(yrke4 = "character",
                                        alder_gr = "character"))
wage <- wage[, .(yrke4, alder_gr, ln_wage = as.numeric(ln_wage))]
wage[, yrke4 := sprintf("%04d", as.integer(yrke4))]

balance <- function(sub, occvars) {
    grid <- CJ(yrke4 = occvars$yrke4, k = sort(unique(sub$k)))
    grid <- merge(grid, occvars, by = "yrke4", all.x = TRUE)
    out <- merge(grid, sub[, .(yrke4, k, y)], by = c("yrke4", "k"), all.x = TRUE)
    out[is.na(y), y := 0]
    out[, kk := ifelse(k >= 0L, "POST", as.character(k))]
    out
}

es_rows <- list(); did_rows <- list(); stat_rows <- list()
for (cfg_name in names(CONFIGS)) {
    cfg <- CONFIGS[[cfg_name]]
    d <- dy[date >= cfg$from & date <= cfg$to]
    d[, ym_int := year(date) * 12L + month(date)]
    d[, k := as.integer(ym_int - (cfg$ref_ym + 1L))]
    cat(sprintf("\n=== %s : k %d..%d ===\n", cfg_name, min(d$k), max(d$k)))

    for (a in ALDER_KEEP) {
        sub <- d[alder_gr == a]
        occ <- merge(unique(sub[, .(yrke4)]), beta, by = "yrke4")
        occ <- merge(occ, wage[alder_gr == a, .(yrke4, ln_wage)], by = "yrke4")
        occ <- occ[is.finite(ln_wage)]
        occ[, z_wage := (ln_wage - mean(ln_wage)) / sd(ln_wage)]
        occ[, prod  := z_exp * z_wage]
        occ[, rect0 := pmax(z_exp, 0) * pmax(z_wage, 0)]
        occ[, rect1 := pmax(z_exp - 1, 0) * pmax(z_wage - 1, 0)]
        te <- quantile(occ$z_exp, 0.75); tw <- quantile(occ$z_wage, 0.75)
        occ[, corner75 := as.integer(z_exp >= te & z_wage >= tw)]
        te8 <- quantile(occ$z_exp, 0.80); tw8 <- quantile(occ$z_wage, 0.80)
        occ[, corner80 := as.integer(z_exp >= te8 & z_wage >= tw8)]
        occvars <- occ[, c("yrke4", "z_exp", "z_wage", INT_VARS), with = FALSE]

        bal <- balance(sub[yrke4 %in% occvars$yrke4], occvars)
        n_occ <- uniqueN(bal$yrke4)
        sd_int <- vapply(INT_VARS, function(v) sd(occvars[[v]]), numeric(1))

        for (v in INT_VARS) {
            # ---- event study ----
            f_es <- as.formula(paste0(
                "y ~ i(k,z_exp,ref=-1)+i(k,z_wage,ref=-1)+i(k,", v,
                ",ref=-1) | yrke4 + k"))
            fit_es <- tryCatch(fepois(f_es, bal, cluster = ~yrke4),
                error = function(e) { cat("  ES fail", v, ":",
                                          conditionMessage(e), "\n"); NULL })
            if (!is.null(fit_es)) {
                ct <- as.data.frame(coeftable(fit_es)); ct$name <- rownames(ct)
                ct$k <- as.integer(sub("\\D*k::(-?[0-9]+).*", "\\1", ct$name))
                ct$term <- ifelse(grepl(v, ct$name, fixed = TRUE), "int",
                            ifelse(grepl("z_wage", ct$name), "wage",
                            ifelse(grepl("z_exp",  ct$name), "exp", NA)))
                ct <- ct[!is.na(ct$k) & !is.na(ct$term), ]
                es_rows[[length(es_rows) + 1]] <- data.table(
                    timing = cfg_name, age_group = as.integer(a), variant = v,
                    term = ct$term, k = ct$k, coef = ct[, "Estimate"],
                    se = ct[, "Std. Error"], sd_int = sd_int[[v]])
            }
            es_rows[[length(es_rows) + 1]] <- data.table(
                timing = cfg_name, age_group = as.integer(a), variant = v,
                term = c("exp", "wage", "int"), k = -1L, coef = 0, se = 0,
                sd_int = sd_int[[v]])

            # ---- pooled DiD ----
            f_did <- as.formula(paste0(
                "y ~ i(kk,z_exp,ref=\"-1\")+i(kk,z_wage,ref=\"-1\")+i(kk,", v,
                ",ref=\"-1\") | yrke4 + k"))
            fit_did <- tryCatch(fepois(f_did, bal, cluster = ~yrke4),
                error = function(e) { cat("  DiD fail", v, ":",
                                          conditionMessage(e), "\n"); NULL })
            if (!is.null(fit_did)) {
                ctt <- as.data.frame(coeftable(fit_did))
                harv <- function(var) {
                    cand <- c(paste0("kk::POST:", var), paste0(var, ":kk::POST"))
                    hit <- cand[cand %in% rownames(ctt)]
                    if (length(hit) == 0) c(NA, NA)
                    else c(ctt[hit[1], "Estimate"], ctt[hit[1], "Std. Error"])
                }
                for (tt in list(c("exp", "z_exp"), c("wage", "z_wage"),
                                c("int", v))) {
                    vv <- harv(tt[2])
                    did_rows[[length(did_rows) + 1]] <- data.table(
                        timing = cfg_name, age_group = as.integer(a),
                        variant = v, term = tt[1], coef = vv[1], se = vv[2],
                        sd_int = sd_int[[v]], n_occ = n_occ)
                }
                pr2 <- tryCatch(as.numeric(r2(fit_did, "pr2")),
                                error = function(e) NA_real_)
                stat_rows[[length(stat_rows) + 1]] <- data.table(
                    timing = cfg_name, age_group = as.integer(a), variant = v,
                    nobs = nobs(fit_did),
                    n_clusters = as.integer(fit_did$fixef_sizes[["yrke4"]]),
                    pr2 = pr2)
            }
        }
        cat(sprintf("  age %s: n_occ=%d  sd_int(corner75)=%.3f\n",
                    a, n_occ, sd_int[["corner75"]]))
    }
}

dir.create(CDIR, showWarnings = FALSE, recursive = TRUE)
es <- rbindlist(es_rows);  setorder(es, timing, age_group, variant, term, k)
fwrite(es, OUT_ES);   cat(sprintf("\nSaved %d ES rows -> %s\n", nrow(es), OUT_ES))
did <- rbindlist(did_rows); fwrite(did, OUT_DID)
cat(sprintf("Saved %d DiD rows -> %s\n", nrow(did), OUT_DID))
st <- rbindlist(stat_rows); fwrite(st, OUT_STAT)
cat(sprintf("Saved %d modelstat rows -> %s\n", nrow(st), OUT_STAT))
