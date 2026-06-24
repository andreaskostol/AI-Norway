# =============================================================================
# 7c_ca_did_firmfe.R : comparative-advantage POOLED DiD on individual-level
#                      (firm-FE) data — firm-FE analogue of chapter 2 of
#                      analysis/output/interaction_results.tex
# =============================================================================
# PURPOSE
#   Pooled post-treatment counterpart to 6e_ca_es_firmfe.R, mirroring the
#   cell-level note's §2 tables (table_ca_did_combined*). For each timing
#   (ChatGPT / agentic), outcome (employment, new hires) and decade age bin we
#   fit three NESTED Poisson models:
#
#     M1 (exp) : log E[y] = a_j + b_{f,t} + d_exp  z(exp)  Post
#     M2 (wage): log E[y] = a_j + b_{f,t} + d_wage z(lnw)  Post
#     M3 (full): log E[y] = a_j + b_{f,t} + d_exp z(exp)Post + d_wage z(lnw)Post
#                                         + d_int (z(exp) z(lnw)) Post
#
#   where a_j = firm x exposure-cell FE and b_{f,t} = firm x month FE
#   (frtk_id^ym) -- the BCC eq. 4.1 structure. TWO exposure-cell variants are run
#   (arg fe=occ|quint|both): fe=occ uses firm x occupation (frtk_id^yrke4, the
#   continuous-treatment-faithful cell, subsumes a plain occupation FE); fe=quint
#   uses firm x quintile (frtk_id^ai_q, BCC-literal coarse cell, more power but
#   leaves within-quintile occupation levels unabsorbed; see 6e header for the
#   trade-off). As in the cell-level note's DiD, Post is NOT a single dummy:
#   each pre-period month enters as its own control level and all post months
#   collapse to "POST", with the reference month (k = -1) omitted, so the POST
#   coefficient is the average post-period effect relative to the reference
#   month. (Implemented via the kk factor, exactly as ca_did_stdexp.R.)
#
#   Identification and measurement: see 6e_ca_es_firmfe.R header and
#   DESIGN_CHOICES.md §3 (BCC eq 4.1 firm x time FE). z_exp pooled (identical to
#   the note); z_wage native to the secure private sample, within age.
#
# Inputs : $DATA/cells_flagged.rds
#          $DATA/styrk08_eloundou_beta_mapping.csv
# Outputs: $output/coefficients/coef_ca_did_firmfe.csv
#            (timing, outcome, fe, age_bin, model, term, coef, se, n_obs, n_frtk)
#          $output/coefficients/coef_ca_did_firmfe_modelstats.csv
#            (timing, outcome, fe, age_bin, model, nobs, n_frtk, pr2)
#            fe in {occ, quint}; nobs = fepois estimation N (after
#            singleton/all-zero drops); n_frtk = distinct foretak in the pre-fit
#            sub-sample (>= SE clusters)
#          $output/log_7c_ca_did_firmfe.txt
#
# Usage  : cd H:\Dokumenter\ai_norway_indiv\scripts ; Rscript 7c_ca_did_firmfe.R
#          optional NAMED args (any order; all default to both):
#            outcome=count|nyjobb|both  timing=chatgpt|agentic|both
#            fe=occ|quint|both
#          e.g. Rscript 7c_ca_did_firmfe.R outcome=count timing=chatgpt fe=occ
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}

req("fixest"); req("data.table")   # req() comes from 0_settings.R

log_path <- file.path(OUTPUT, "log_7c_ca_did_firmfe.txt")
log_con  <- file(log_path, open = "wt")
sink(log_con, split = TRUE)
sink(log_con, type = "message")
close_log <- function() {
    try(sink(type = "message"), silent = TRUE)
    try(sink(),                 silent = TRUE)
    try(close(log_con),         silent = TRUE)
}
cat("== 7c_ca_did_firmfe.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Arguments
# -----------------------------------------------------------------------------
# Named args (key=value); robust to 99_master.R script-selector tokens.
args <- commandArgs(trailingOnly = TRUE)
getarg <- function(key, choices, default) {
    hit <- sub(paste0("^", key, "="), "",
               args[grepl(paste0("^", key, "="), args)])
    if (length(hit) && tolower(hit[1]) %in% choices) tolower(hit[1]) else default
}
OUTCOME_ARG <- getarg("outcome", c("count", "nyjobb", "both"), "both")
TIMING_ARG  <- getarg("timing",  c("chatgpt", "agentic", "both"), "both")
FE_ARG      <- getarg("fe",      c("occ", "quint", "both"), "both")
OUTCOMES <- if (OUTCOME_ARG == "both") c("count", "nyjobb") else OUTCOME_ARG
TIMINGS  <- if (TIMING_ARG  == "both") c("chatgpt", "agentic") else TIMING_ARG
FE_SPECS <- if (FE_ARG == "both") c("occ", "quint") else FE_ARG
YVAR <- c(count = "count_all", nyjobb = "count_new")
FE_CELL <- c(occ = "frtk_id^yrke4", quint = "frtk_id^ai_q")
cat(sprintf("Outcomes: %s | Timings: %s | FE: %s\n",
            paste(OUTCOMES, collapse = ","), paste(TIMINGS, collapse = ","),
            paste(FE_SPECS, collapse = ",")))

# ChatGPT window ends 2025m4 BY DESIGN (pre-agentic period, matching the
# cell-level note); the agentic window runs to the data edge (0_settings.R).
CONFIGS <- list(
    chatgpt = list(ref_ym = ym(2022, 10), from = ym(2021, 1), to = ym(2025, 4)),
    agentic = list(ref_ym = ym(2025,  4), from = ym(2023, 7), to = YM_PERIOD_END)
)

# -----------------------------------------------------------------------------
# z_exp (pooled) and cells, identical to 6e_ca_es_firmfe.R
# -----------------------------------------------------------------------------
beta <- fread(file.path(DATA, "styrk08_eloundou_beta_mapping.csv"),
              colClasses = c(styrk08 = "character"))
beta[, yrke4 := sprintf("%04d", as.integer(styrk08))]
beta <- beta[!is.na(eloundou_beta), .(yrke4, b = as.numeric(eloundou_beta))]
beta <- unique(beta, by = "yrke4")
beta[, z_exp := (b - mean(b)) / sd(b)]
zexp <- beta[, .(yrke4, z_exp)]

d <- load_cells()
cat(sprintf("Loaded %d rows from cells_flagged.rds\n", nrow(d)))
d <- d[in_headline_priv == 1]
# yrke4 is a plain zero-padded character in cells_flagged.rds; re-pad
# defensively (see 6e) so the styrk08 inner join cannot silently mismatch.
d[, yrke4 := pad0(yrke4, 4)]
cat(sprintf("After in_headline_priv: %d rows, %d distinct yrke4\n",
            nrow(d), uniqueN(d$yrke4)))

YM_PRE <- ym(2022, 10)
pre <- d[ym <= YM_PRE & count_all > 0 &
         !is.na(m_wage_all) & m_wage_all > 0 &
         !is.na(m_position_all) & m_position_all >= 10]
wage <- pre[, .(wbar   = sum(count_all * m_wage_all)     / sum(count_all),
                posbar = sum(count_all * m_position_all) / sum(count_all)),
            by = .(yrke4, age_bin)]
wage[, fte := wbar * 100 / posbar]
wage <- wage[is.finite(fte) & fte > 0]
wage[, ln_wage := log(fte)]
wage[, z_wage := (ln_wage - mean(ln_wage)) / sd(ln_wage), by = age_bin]
zwage <- wage[, .(yrke4, age_bin, z_wage)]
cat(sprintf("z_exp: %d occ; z_wage: %d (yrke4 x age) cells\n",
            nrow(zexp), nrow(zwage)))

# -----------------------------------------------------------------------------
# Harvest the POST coefficient for one variable (handles either coef name order)
# -----------------------------------------------------------------------------
harv <- function(fit, var) {
    if (is.null(fit)) return(c(NA_real_, NA_real_))
    ct <- as.data.frame(coeftable(fit))
    cand <- c(paste0("kk::POST:", var), paste0(var, ":kk::POST"))
    hit <- cand[cand %in% rownames(ct)]
    if (length(hit) == 0) return(c(NA_real_, NA_real_))
    c(ct[hit[1], "Estimate"], ct[hit[1], "Std. Error"])
}

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
rows <- list(); stat_rows <- list(); diag_rows <- list()
for (oc in OUTCOMES) {
    yv <- YVAR[[oc]]
    cat(sprintf("\n################ OUTCOME = %s (%s) ################\n", oc, yv))
    dd <- d[, .(y = sum(.SD[[1L]]), ai_q = first(ai_q)),
            by = .(frtk_id, yrke4, age_bin, ym), .SDcols = yv]
    dd <- merge(dd, zexp, by = "yrke4")

    for (tm in TIMINGS) {
        cfg <- CONFIGS[[tm]]
        if (nrow(dd) == 0)
            stop("Empty panel after z_exp merge — check yrke4 vs styrk08 padding.")
        dt <- dd[ym >= cfg$from & ym <= cfg$to]
        dt[, k := as.integer(ym - (cfg$ref_ym + 1L))]
        dt <- dt[k >= KMIN & k <= KMAX]
        if (nrow(dt) == 0) {
            cat(sprintf("\n=== %s / %s : window empty within the panel, skip ===\n",
                        oc, tm))
            next
        }
        # kk: each pre-month its own level, all post collapsed to POST,
        # k = -1 reference. POST coef = avg post effect vs reference month.
        dt[, kk := ifelse(k >= 0L, "POST", as.character(k))]
        cat(sprintf("\n=== %s / %s : k %d..%d, %d post-months, %d rows ===\n",
                    oc, tm, min(dt$k), max(dt$k),
                    uniqueN(dt[k >= 0L, k]), nrow(dt)))

        for (a in 1:N_AGE_BINS) {
            sub <- dt[age_bin == a]
            zw_a <- zwage[age_bin == a, .(yrke4, z_wage)]
            sub <- merge(sub, zw_a, by = "yrke4")
            sub[, z_expwage := z_exp * z_wage]
            n_obs <- nrow(sub); n_frtk <- uniqueN(sub$frtk_id)
            if (n_obs == 0 || !("-1" %in% sub$kk)) {
                cat(sprintf("  age %d: no rows or no reference level, skip\n", a))
                next
            }

            for (fe in FE_SPECS) {
                fe_rhs <- paste("|", FE_CELL[[fe]], "+ frtk_id^ym")
                est <- function(rhs) tryCatch(
                    fepois(as.formula(paste("y ~", rhs, fe_rhs)),
                           data = sub, cluster = ~frtk_id),
                    error = function(e) {
                        cat("  fit failed:", conditionMessage(e), "\n"); NULL })
                t0 <- Sys.time()
                fits <- list(
                    m1 = est("i(kk, z_exp, ref = \"-1\")"),
                    m2 = est("i(kk, z_wage, ref = \"-1\")"),
                    m3 = est(paste("i(kk, z_exp, ref = \"-1\")",
                                   "+ i(kk, z_wage, ref = \"-1\")",
                                   "+ i(kk, z_expwage, ref = \"-1\")")))
                cat(sprintf("  age %d fe=%-5s: n=%d n_frtk=%d fit %.1fs\n",
                            a, fe, n_obs, n_frtk,
                            as.numeric(Sys.time() - t0, units = "secs")))

                add <- function(fit, model, var, term) {
                    v <- harv(fit, var)
                    data.table(timing = tm, outcome = oc, fe = fe, age_bin = a,
                               model = model, term = term, coef = v[1],
                               se = v[2], n_obs = n_obs, n_frtk = n_frtk)
                }
                rows[[length(rows) + 1]] <- rbindlist(list(
                    add(fits$m1, "m1", "z_exp",     "exp"),
                    add(fits$m2, "m2", "z_wage",    "wage"),
                    add(fits$m3, "m3", "z_exp",     "exp"),
                    add(fits$m3, "m3", "z_wage",    "wage"),
                    add(fits$m3, "m3", "z_expwage", "exp_x_wage")))

                for (mm in c("m1", "m2", "m3")) {
                    fit <- fits[[mm]]
                    diag_rows[[length(diag_rows) + 1]] <- fixest_diag_row(
                        fit, "7c", sprintf("%s_%s_%s_age%d_%s", tm, oc, fe, a, mm),
                        n_obs, n_frtk)
                    if (is.null(fit)) next
                    pr2 <- tryCatch(as.numeric(r2(fit, "pr2")),
                                    error = function(e) NA_real_)
                    stat_rows[[length(stat_rows) + 1]] <- data.table(
                        timing = tm, outcome = oc, fe = fe, age_bin = a,
                        model = mm, nobs = nobs(fit), n_frtk = n_frtk, pr2 = pr2)
                }
            }
        }
    }
    rm(dd); gc()
}

out <- rbindlist(rows, use.names = TRUE, fill = TRUE)
if (nrow(out) > 0) setorder(out, timing, outcome, fe, age_bin, model, term)
atomic_fwrite(out, file.path(COEFS, "coef_ca_did_firmfe.csv"))
cat(sprintf("\nSaved %d rows to coef_ca_did_firmfe.csv\n", nrow(out)))

stats <- rbindlist(stat_rows, use.names = TRUE, fill = TRUE)
if (nrow(stats) > 0) setorder(stats, timing, outcome, fe, age_bin, model)
atomic_fwrite(stats, file.path(COEFS, "coef_ca_did_firmfe_modelstats.csv"))
cat(sprintf("Saved %d rows to coef_ca_did_firmfe_modelstats.csv\n", nrow(stats)))

atomic_fwrite(rbindlist(diag_rows),
              file.path(DIAG, "fixest_diag_7c_ca_did_firmfe.csv"))
cat("Wrote diagnostics/fixest_diag_7c_ca_did_firmfe.csv\n")
cat("== 7c_ca_did_firmfe.R done ", format(Sys.time()), " ==\n")
close_log()
