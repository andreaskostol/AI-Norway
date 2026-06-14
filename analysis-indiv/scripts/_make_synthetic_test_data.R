# =============================================================================
# _make_synthetic_test_data.R : build a miniature 1191-world for a local
#                               end-to-end smoke test of the pipeline
# =============================================================================
# LOCAL ONLY -- never run on the secure server. Creates, under
# AI_NORWAY_TEST_ROOT (default: <tempdir>/ai_norway_test):
#
#   atid/ameld_statdata_{y}_m{m}.dta   synthetic A-meldingen months
#   demo/faste_oppl.dta                synthetic demographics, WITH the 1191
#                                      quirks (w19_0345_lopenr_person key,
#                                      str8 year fields, duplicate persons,
#                                      one invalid birth month)
#   data/                              the three real input CSVs, copied in
#   project/                           output tree (created by 0_settings.R)
#
# A treatment effect is PLANTED: from event zero (Nov 2022), worker-months in
# quintile 5 x age_bin 1 (21-30) are dropped with 30% probability. The smoke
# test passes when 7b and 7d both recover a negative Q5(-vs-Q3) employment
# coefficient for age_bin 1, and their sum_count_all per age_bin agree.
#
# Usage (from analysis-indiv/scripts/):
#   AI_NORWAY_TEST_ROOT=<dir> AI_NORWAY_PERIOD_START_Y=2022 \
#   AI_NORWAY_PERIOD_START_M=6 AI_NORWAY_PERIOD_END_Y=2023 \
#   AI_NORWAY_PERIOD_END_M=3 Rscript _make_synthetic_test_data.R
# then, with the SAME env vars:  Rscript 99_master.R
# =============================================================================

suppressMessages({ library(data.table); library(haven) })

if (!nzchar(Sys.getenv("AI_NORWAY_TEST_ROOT", unset = "")))
    Sys.setenv(AI_NORWAY_TEST_ROOT = file.path(tempdir(), "ai_norway_test"))
source("0_settings.R")   # re-rooted paths + period from env

set.seed(1191)

dir.create(AMELD_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(dirname(FASTE_OPPL_PATH), showWarnings = FALSE, recursive = TRUE)

# -----------------------------------------------------------------------------
# Real input CSVs -> TEST_ROOT/data (exposure mapping, crosswalk, population)
# -----------------------------------------------------------------------------
repo_root <- normalizePath(file.path(getwd(), "..", ".."))
src <- c(file.path(repo_root, "data", "ai_exposure", "styrk08_eloundou_beta_mapping.csv"),
         file.path(repo_root, "data", "macro", "ssb_population_by_age_quarterly.csv"),
         file.path(repo_root, "analysis-indiv", "occupations_7digits_4digits.csv"))
stopifnot(all(file.exists(src)))
invisible(file.copy(src, DATA, overwrite = TRUE))

# -----------------------------------------------------------------------------
# Occupation pool: yrke7 codes from the REAL crosswalk whose yrke4 is in the
# REAL Eloundou mapping -- 3 occupations per quintile
# -----------------------------------------------------------------------------
cw <- fread(file.path(DATA, "occupations_7digits_4digits.csv"),
            sep = ";", colClasses = "character")
setnames(cw, tolower(names(cw)))
cw <- unique(cw[, .(yrke7 = trimws(sourcecode), yrke4 = trimws(targetcode))], by = "yrke7")

expo <- fread(file.path(DATA, "styrk08_eloundou_beta_mapping.csv"),
              colClasses = c(styrk08 = "character"))
expo[, yrke4 := pad0(styrk08, 4)]

pool <- merge(cw, expo[, .(yrke4, quintile)], by = "yrke4")[!is.na(quintile)]
occ <- pool[, .SD[!duplicated(yrke4)][seq_len(min(3L, sum(!duplicated(yrke4))))],
            by = quintile]
# Force the canonical crosswalk edge case into the pool: military 7-digit
# "0111101" maps to "0310", NOT substr "0111".
occ <- unique(rbind(occ, pool[yrke7 == "0111101"]), by = "yrke7")
stopifnot(uniqueN(occ$quintile) == 5L, "0111101" %in% occ$yrke7)
cat(sprintf("Occupation pool: %d yrke7 over %d yrke4, all 5 quintiles\n",
            nrow(occ), uniqueN(occ$yrke4)))

# -----------------------------------------------------------------------------
# Persons + firms
# -----------------------------------------------------------------------------
N_PERS  <- 4000L
N_FIRMS <- 14L

pers <- data.table(
    lopenr_person = sprintf("P%09d", seq_len(N_PERS)),
    foedselsaar   = sample(1963:2001, N_PERS, replace = TRUE),
    birth_mo      = sample(1:12, N_PERS, replace = TRUE),
    kjoenn        = sample(c("1", "2"), N_PERS, replace = TRUE),
    # person's fixed job: firm + occupation (occupations spread over firms so
    # every firm employs several quintiles -> firm x quintile FE identified)
    firm_i        = sample(seq_len(N_FIRMS), N_PERS, replace = TRUE),
    occ_i         = sample(seq_len(nrow(occ)), N_PERS, replace = TRUE)
)

firms <- data.table(
    firm_i         = seq_len(N_FIRMS),
    lopenr_foretak = sprintf("F%09d", seq_len(N_FIRMS)),
    # 12 private firms, 1 stat (6100), 1 kommune (1510); two private firms are
    # tiny (< FRTK_MIN_ACTIVE) to exercise the activity filter
    frtk_sektor_2014 = c(rep("2100", N_FIRMS - 2L), "6100", "1510")
)
small_firms <- firms$lopenr_foretak[c(1L, 2L)]
pers[firm_i %in% c(1L, 2L) & seq_len(.N) %% 20 != 0, firm_i := 3L]  # shrink firms 1-2

pers <- merge(pers, firms, by = "firm_i")
pers[, `:=`(yrke7 = occ$yrke7[occ_i], quintile = occ$quintile[occ_i])]

# -----------------------------------------------------------------------------
# faste_oppl.dta -- with the 1191 quirks
# -----------------------------------------------------------------------------
fo <- pers[, .(
    w19_0345_lopenr_person = lopenr_person,                       # the w19 key
    foedselsaar      = sprintf("%d", foedselsaar),                # str8
    foedsels_aar_mnd = sprintf("%d%02d", foedselsaar, birth_mo),  # str8
    doeds_aar_mnd    = "",                                        # alive
    kjoenn           = kjoenn
)]
fo <- rbind(fo, fo[1:5])                       # duplicate persons (dedup path)
fo$foedsels_aar_mnd[3] <- paste0(fo$foedselsaar[3], "13")  # invalid birth month
write_dta(fo, FASTE_OPPL_PATH)
cat(sprintf("faste_oppl.dta: %d rows (incl. 5 duplicates, 1 invalid birth_mo)\n",
            nrow(fo)))

# -----------------------------------------------------------------------------
# Monthly ameld files with the planted effect
# -----------------------------------------------------------------------------
mg <- month_grid()
base_wage <- exp(rnorm(N_PERS, mean = 10.6, sd = 0.3))   # ~40k NOK

for (i in seq_len(nrow(mg))) {
    y <- mg$y[i]; m <- mg$m[i]; ym_i <- mg$ym[i]

    d <- pers[, .(lopenr_person, lopenr_foretak, frtk_sektor_2014, yrke7,
                  quintile, foedselsaar, birth_mo)]
    d[, a_year := (ym_i - ym(foedselsaar, birth_mo)) %/% 12L]

    # PLANTED EFFECT: post-Nov-2022, Q5 x age 21-30 worker-months vanish with
    # 30% probability (relative employment decline in young x most-exposed).
    if (ym_i >= YM_EVENT_ZERO) {
        hit <- d$quintile == 5L & d$a_year >= 21L & d$a_year <= 30L &
               runif(nrow(d)) < 0.30
        d <- d[!hit]
    }

    n <- nrow(d)
    out <- data.table(
        lopenr_person      = d$lopenr_person,
        lopenr_foretak     = d$lopenr_foretak,
        arb_yrke           = d$yrke7,
        frtk_sektor_2014   = d$frtk_sektor_2014,
        lonn_kontant       = base_wage[match(d$lopenr_person, pers$lopenr_person)] *
                                 exp(rnorm(n, 0, 0.05)),
        arb_stillingspst   = sample(c(100, 100, 100, 50), n, replace = TRUE),
        arb_arbeidstid     = 37.5,
        lonn_overtid_timer = pmax(0, rnorm(n, 2, 3)),
        lonn_fast          = 30000,
        lonn_time          = NA_real_,
        lonn_time_antall   = 0,
        # ~3% new hires: spell started this month; rest started 2018-01-15
        arb_start          = as.Date(ifelse(runif(n) < 0.03,
                                            as.Date(sprintf("%d-%02d-10", y, m)),
                                            as.Date("2018-01-15")),
                                     origin = "1970-01-01")
    )
    # --- Planted edge cases targeting the cleaning rules in script 3 ---
    idx <- function(p) runif(nrow(out)) < p
    out[idx(0.05), arb_start := as.Date(NA)]               # missing arb_start
    out[idx(0.02) & grepl("^0", arb_yrke),                 # lost leading zeros
        arb_yrke := sub("^0+", "", arb_yrke)]              #   -> pad0 must fix
    out[idx(0.01),  lonn_time_antall   := 350]             # > 300 -> NA
    out[idx(0.02),  lonn_overtid_timer := 150]             # 80-300 -> capped 80
    out[idx(0.005), lonn_overtid_timer := 400]             # > 300 -> capped 80
    out[idx(0.01),  arb_stillingspst   := 250]             # > 200 -> capped 200
    out[idx(0.01),  arb_stillingspst   := -5]              # <= 0  -> NA, ft = 0
    out[idx(0.005), lopenr_foretak     := ""]              # missing -> dropped

    # a few extra columns so col_select has something to ignore
    out[, arb_yrke_styrk08 := substr(pad0(arb_yrke, 7), 1, 4)]
    out[, virk_nace1_sn07 := "62.010"]
    write_dta(out, ameld_path(y, m))
}
cat(sprintf("ameld: %d months written (%dm%d - %dm%d), planted Q5 x young drop from %dm%d\n",
            nrow(mg), mg$y[1], mg$m[1], mg$y[nrow(mg)], mg$m[nrow(mg)],
            EVENT_ZERO_Y, EVENT_ZERO_M))
cat(sprintf("\nTest world ready under %s\nNow run (same env vars): Rscript 99_master.R\n",
            Sys.getenv("AI_NORWAY_TEST_ROOT")))
