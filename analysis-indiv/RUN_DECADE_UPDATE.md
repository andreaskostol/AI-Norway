# Kjøreinstruks: decade-rebinning + per-alder DiD (secure server)

> **HISTORISK** — denne runden ble kjørt 2026-06-02 på datauniverset 1183 med
> Stata-prep. Erstattet av [`RUN_1191_UPDATE.md`](RUN_1191_UPDATE.md)
> (1191, hel-R pipeline, data t.o.m. 2026m2). Beholdes som dokumentasjon av
> 1183-kjøringen; .do-filene den refererer ligger i `scripts/stata_archive/`.

Denne runden re-binner individanalysen til fire tiårsgrupper (21-30, 31-40,
41-50, 51-60) og legger til en ny per-aldersgruppe DiD (script 7b) med tre
utfall, slik at individresultatene validerer celle-analysen.

## Hva som er endret (lokalt, må overføres)

- `0_settings.do`, `0_settings.R`: age_min=21, age_max=60, young_max=30,
  N_AGE_BINS=4.
- `3_monthly_filtered.do`: age_bin = fire tiårsgrupper; laster nå `arb_start`
  og lager `ny_jobb` (spell-start denne måneden).
- `4_aggregate_cells.do`: nytt `count_new` (sum av ny_jobb) collapses og
  nullfylles i det balanserte panelet.
- `5b_population.do`: befolkning re-binnet til tiår.
- `6_event_study_fepois.R`: loop over `N_AGE_BINS`.
- `7b_did_byage_fepois.R` (NY): kollapset post × kvintil DiD per aldersgruppe,
  tre utfall (employment + new hires Poisson, log lønn OLS), firm-FE
  (`frtk_id^ai_q + frtk_id^ym`), cluster `frtk_id`, vindu t.o.m. 2025m4.
- `99_master.R`: kjører nå også 7b.
- Legacy Stata-scripts (5d, 6_bcc, 6b, 6c, 9, 10a): `forval 1/4` + tiårsetiketter.

## Overføring (til H:\Dokumenter\ai_norway_indiv\scripts\)

Alle endrede `scripts/*.do` og `scripts/*.R`. Ingen nye datafiler trengs
(arb_start ligger allerede i ameld på `W:\7020\atid\`; verifisert i
`datadoc/metadata_scan7020.csv`).

## Kjørerekkefølge på serveren

1. `do 99_master.do`  — bygger `cells_flagged.dta` på nytt (scripts 1-5) med
   tiårsgrupper og `count_new`, og kjører de legacy Stata-estimeringene.
   Kritisk: scripts 1-5 må kjøre helt igjennom; estimeringsscriptene etterpå
   påvirker ikke `cells_flagged.dta`.
2. `cd scripts` så `Rscript 99_master.R`  — kjører 6 (event study), 7
   (triple-diff) og 7b (ny per-alder DiD).

## Hva som synkes tilbake (hele from_secure_server\ som én enhet)

Nytt/oppdatert i `from_secure_server\coefficients\`:
- `coef_did_byage_fepois.csv`  (← den nye tabellen leses fra denne)
- `coef_event_study_fepois.csv` (+ summary), `coef_triplediff_fepois.csv`
- logger: `log_7b_did_byage_fepois.txt` m.fl.

## Lokalt etterpå

`python analysis/05_tables/make_did_firmfe_table.py` →
`analysis/output/tables/table4_did_firmfe.tex` (firm-FE-tabellen ved siden av
celle-tabellen `table3_did_cell.tex`).

## Merknader / ting å sjekke i loggene

- `assert !missing(age_bin)` i script 3 forutsetter at alle beholdte aldre
  (21-60) treffer en bin — sjekk at ingen rader faller utenfor.
- `ny_jobb`: `mofd(arb_start) == ym`. Hvis arb_start mangler systematisk i noen
  årganger, vil new-hires-tellingen bli for lav den måneden; sjekk
  frekvensen av missing arb_start i loggen.
- `plot_secure_server_results.py` må håndtere fire (ikke seks) aldersbånd når
  det tegner firm-FE event-study-rutenettet — verifiser panel-layout.
- Legacy figur-/note-strenger (10c, 7_triplediff_2age-kommentar) kan fortsatt
  nevne "22-25"; de er kommentarer/noter, ikke estimeringslogikk.
