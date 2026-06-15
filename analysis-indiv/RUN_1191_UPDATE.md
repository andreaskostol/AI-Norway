# Kjøreinstruks: 1191-migrering + hel-R pipeline + individ/celle-sammenligning

Denne runden flytter individanalysen til datauniverset **1191** (A-meldingen
t.o.m. **2026m2** — like oppdatert som celle-analysene), gjør hele pipelinen
om til **R**, og legger til sammenligningsmodulen **7d** som kjører
celle-spesifikasjonen på nøyaktig samme data som firm-FE-spesifikasjonen (7b).
Se `DESIGN_CHOICES.md` §21–23 for begrunnelser.

## Hva som er endret (lokalt, må overføres)

- **Alle prep-scripts er nå R**: `1_exposure.R`, `1b_load_styrk7_crosswalk.R`,
  `2_relevant_ids.R`, `3_monthly_filtered.R`, `4_aggregate_cells.R`,
  `5_apply_restrictions.R`, `5b_population.R`, `5c_baseline_kref.R`,
  `5d_sample_size_diagnostic.R`. De gamle `.do`-filene ligger fryst i
  `scripts/stata_archive/` og skal ikke kjøres.
- **`0_settings.R`**: stier til 1191 (`W:/1191/atid`, `W:/1191/demo/faste_oppl.dta`,
  `F:/1191/oysteimh/ai_norway_indiv/data`), periode 2021m1–**2026m2**,
  KMIN/KMAX avledet av perioden (−22/+39), alle delte hjelpere.
- **Mellomfiler er .rds** (exposure.rds, relevant_ids.rds, ameld_filt_*.rds,
  cells.rds, cells_flagged.rds, population_by_agebin_ym.rds + NY
  occ_unrestricted_agg.rds).
- **`7b_did_byage_fepois.R`**: 2025m4-kuttet fjernet (fullt vindu); ny kolonne
  `sum_count_all` (kryssjekk mot 7d); Q3-referansen riktig dokumentert.
- **NY `7d_did_byage_cellspec.R`**: celle-spesifikasjonen (yrke4+måned-FE,
  cluster yrke4, Q3-ref) per aldersgruppe og tre utfall, på (i) samme
  restrikterte utvalg som 7b og (ii) det urestrikterte private aggregatet
  (bro mot microdata.no). → `coef_did_byage_cellspec.csv`.
- **`6e`/`7c`**: agentic-vinduet går nå til dataslutt; chatgpt-vinduet slutter
  fortsatt 2025m4 **med vilje** (pre-agentisk definisjon).
- **`99_master.R`**: kjører ALT (prep + estimering); gruppe-alias
  `prep`/`est`/`heavy`; prep-feil stopper kjøringen.

## Pre-flight (lokalt, FØR overføring)

```
Rscript analysis-indiv/scripts/_dryrun_validate.R
```
Må være **all-PASS** (validerer alle fil-/variabelreferanser mot
`datadoc/metadata_scan1191.csv`). Kjør på nytt etter hver ny leveranse
(rescan først med `datadoc/scan_metadata.do` på serveren).

## Overføring

Til `H:\Dokumenter\ai_norway_indiv\scripts\`:
- alle `scripts/*.R`

Til `F:\1191\<bruker>\ai_norway_indiv\data\` (NB: ny disk — F:\1191, ikke F:\1183):
- `data/ai_exposure/styrk08_eloundou_beta_mapping.csv`
- `data/ai_exposure/styrk08_handa_mapping.csv` (kreves av A1 — BCC-appendiks)
- `data/macro/ssb_population_by_age_quarterly.csv`
- `analysis-indiv/occupations_7digits_4digits.csv`

Første gang: slett gamle `_md_fragments\` i `from_secure_server\` på serveren
(fragmentene fra 1183-kjøringen blandes ellers inn i den nye rapporten —
spesielt de gamle estimeringsseksjonene 07–10 som ikke lenger produseres).

## Kjøring på serveren

**Interaktivt (RStudio — anbefalt arbeidsflyt):** åpne `99_master.R`, kjør
SETUP-blokken én gang (alt over `KJØRELISTE`-banneret), og marker så de
`run_script()`-linjene du vil kjøre — én, noen eller alle. Hvert kall sletter
scriptets gamle outputs først og oppdaterer `run_manifest.csv`, så delkjøringer
er trygge. (Merk: kjør 7d etter 7b — den leser `sample_diag_7b.csv`.)

**Batch (alt eller grupper):**
```
cd H:\Dokumenter\ai_norway_indiv\scripts
Rscript 99_master.R            # alt (prep -> estimering -> heavy)
Rscript 99_master.R prep       # bare databygging (1-5d)
Rscript 99_master.R est        # bare estimering (6-8 inkl. 7b/7d)
Rscript 99_master.R heavy      # bare 6e + 7c
Rscript 99_master.R 7b 7d      # substring-utvalg
```
6e/7c kan parallelliseres standalone: `Rscript 6e_ca_es_firmfe.R fe=occ` osv.

**Tunge kjøringer og frakobling.** De tunge fitene (3, 4, 6, 7, 6e, 7c på
ekte data) kan tidligere mette alle CPU-kjernene slik at fjernsesjonen mistet
kontakten («disconnected — bare én tilkobling om gangen» er klienten som
kolliderer med sin egen gamle tilkobling ved gjenoppkobling). To mottiltak:

1. `0_settings.R` begrenser nå data.table/fixest til **alle kjerner minus to**
   (overstyr med `AI_NORWAY_THREADS=<n>`), så front-enden forblir responsiv.
2. Kjør likevel timelange jobber utenfor RStudio-konsollen: åpne et eget
   **Command Prompt**-vindu og kjør `Rscript 99_master.R est` der (prosessen
   overlever at fjernskrivebordet kobles fra, så lenge du ikke logger ut), eller
   bruk RStudios *Background Jobs*-panel. RStudio-konsollen er grei til de
   raske scriptene og delkjøringer.

**Etter en frakobling:** ikke anta at kjøringen døde. Sjekk
`diagnostics/run_manifest.csv` (status per script) og halen av
`log_<script>.txt` — står sluttlinjen «done» der, fullførte scriptet i
bakgrunnen. Hvis ikke: kjør bare det scriptet på nytt (invalideringen sørger
for at halvgamle outputs ikke overlever).

## Hva som synkes tilbake (hele from_secure_server\ som én enhet)

- `SECURE_SERVER_RESULTS.md` (§1–§6 prep-dokumentasjon)
- `coefficients/`: `coef_did_byage_fepois.csv` (7b, firm-spec) og
  **`coef_did_byage_cellspec.csv`** (7d, celle-spec — den nye tabellen),
  pluss event-study-/triple-diff-/alt-/CA-CSV-ene og baseline_kref.
- `diagnostics/`:
  - `run_manifest.csv` — status per script; **ingen estimeringsoutput er
    gyldig uten status ok her** (master sletter dessuten et scripts deklarerte
    outputs FØR det kjører, så gamle CSV-er kan ikke overleve en feilet
    kjøring)
  - `settings_selftest.txt` (fixture-tester av settings-API-et)
  - `monthly_filter_funnel.csv`, `aggregate_cell_counts.csv`,
    `restriction_funnel.csv` (maskinlesbare motstykker til §4–§6)
  - `sample_diag_7b.csv`, `sample_diag_7d_restricted.csv`,
    `7b_7d_sample_comparison.csv` (granulær identisk-utvalg-sjekk; 7d
    **stopper** ved avvik)
  - `fixest_diag_*.csv` (n_obs, droppede obs, clustre, konvergens per fit)
  - `sample_size_diagnostic.csv`
- `log_master_R.txt` + `log_*.txt` per script

## Sjekkliste i loggene etter kjøring

1. **§4-trakten** (SECURE_SERVER_RESULTS.md / log_3): per-måned-tallene for
   2021m1–2025m7 skal ligge innenfor ~1 % av forrige kjøring
   (leveranseforskjeller 7020 vs 1191); 2025m8–2026m2 er nye rader med
   plausibel kontinuitet. Ingen måned skal mangle (scriptet stopper hardt).
2. **Crosswalk/eksponering**: `n_unmapped_yrke7` stabil over måneder;
   `arb_yrke_styrk08`-kryssjekken (2023+) skal vise lav mismatch-andel;
   eksponeringen dekker 397 yrke4 (§2).
3. **Missing arb_start** (§4-kolonnen): hopp i andelen i enkelte årganger
   betyr undertelling av `count_new` den måneden.
4. **§5**: balansert panel ~33–34M rader over 62 måneder (29,98M over 55 i
   1183-kjøringen); ~24k foretak; lignende andel syntetiske nuller.
5. **§6**: utvalgsstørrelser i samme størrelsesorden som før.
6. **fepois-konvergens** i log_6/log_7b/log_7d; event-koeffisienter til
   k = +39 (ikke +36 — KMAX er nå periodeavledet).
7. **KRYSSJEKK 7b ↔ 7d**: håndheves nå automatisk på to nivåer:
   (i) 7d sammenligner granulære utvalgsdiagnostikker (sum per age_bin × ym ×
   ai_q × post, antall yrke4/foretak) mot 7b sine og **stopper** ved avvik
   (`diagnostics/7b_7d_sample_comparison.csv` viser raden(e) som avviker);
   (ii) `sum_count_all`-kolonnen i begge koeffisient-CSV-ene skal være
   identisk per age_bin. Sjekk også `fixest_diag_*.csv`: droppede
   observasjoner (singletons/null-FE) og konvergens per fit.
8. **Valgfritt, første 1191-kjøring**: `Rscript _compare_1183_overlap.R`
   sammenligner gammel Stata/1183-`cells_flagged.dta` med ny R/1191 på
   overlappvinduet 2021m1–2025m7 (fordelingsnivå; foretaks-ID-er kan ikke
   matches på tvers av leveranser). Skriver
   `diagnostics/stata_r_overlap_diff.csv` + `_checksums.csv`. Forvent avvik
   godt under 1 %; større avvik skal kunne forklares av leveranseforskjeller.
9. **Valgfritt, ren port-test (trinn A i evalueringsdokumentet)**: kjør
   R-pipelinen på den GAMLE 7020-leveransen i et eget skrapeområde, og
   sammenlign mot den arkiverte Stata-outputen — da testes Stata→R-porten på
   identiske rådata (forvent ~eksakt likhet), isolert fra leveransebyttet:
   ```
   set AI_NORWAY_PROSJEKTDATA=W:/7020
   set AI_NORWAY_DATA=F:/1191/oysteimh/ai_norway_indiv/data_7020_porttest
   set AI_NORWAY_PROJECT=H:/Dokumenter/ai_norway_indiv_porttest
   set AI_NORWAY_PERIOD_END_Y=2025
   set AI_NORWAY_PERIOD_END_M=7
   Rscript 99_master.R prep
   ```
   (0_settings.R plukker automatisk `faste_oppl_full.dta` på 7020.) Rediger
   deretter `OLD_CELLS`/`load_cells`-kilden i `_compare_1183_overlap.R` til
   skrapeområdet og kjør den. Krever at W:\7020 fortsatt er montert.

## Lokalt etterpå

- `analysis/06_figures/microdata_did_cell.R`: kuttet er flyttet til fullt
  vindu (2026m2) i samme oppdatering, så celle-tabellen er sammenlignbar med
  7b/7d-tallene.
- Sammenlignings-tabell/-figur (7b vs 7d vs publisert celle) bygges lokalt fra
  de tre CSV-ene når resultatene er ute (egen runde).
