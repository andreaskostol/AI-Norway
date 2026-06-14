# Kritisk evaluering av plan for 1191-migrering, hel-R pipeline og 7d-sammenligningsmodul

## Formål

Dette dokumentet er skrevet for en LLM som skal hjelpe med å implementere R-scripts i prosjektet. Det er ikke bare en generell vurdering av planen, men en implementeringskritikk: hvilke deler av planen som er gode, hvilke deler som er risikable, og hvilke krav som bør gjøres eksplisitte før koden skrives.

Dokumentet skal leses normativt. Når et punkt er merket **MÅ**, skal det behandles som et blokkerende krav før implementering eller merge. Når et punkt er merket **BØR**, er det en sterk anbefaling som reduserer risikoen for stille empiriske feil.

## Kort dom

Planen er solid som prosjektplan, men ikke tilstrekkelig presis som direkte instruks til en LLM som skal skrive analyse-scripts i R.

Den største styrken er at planen har riktig arkitektur: én felles `0_settings.R`, hel-R pipeline med `haven`, `data.table` og `fixest`, `.rds` mellomlagring, eksplisitt 1191-migrering, månedlig prosessering, ny 7d-modul og en planlagt mekanisk 7b↔7d-sjekk.

Den største svakheten er at planen ofte sier at R-koden skal være ekvivalent med eksisterende Stata-logikk, men uten å gjøre ekvivalensen tilstrekkelig maskinelt testbar. Det er farlig når en LLM skal implementere. En LLM kan skrive kode som ser ryddig ut, kjører uten feil og produserer plausible resultater, men som likevel avviker stille i padding, missing-håndtering, datoimport, vekter, dedup, sortering, aggregering, balansering eller `fixest`-dropping.

**Vurdering:**

- Som prosjektplan: **8/10**
- Som direkte LLM-instruks: **6.5/10**
- Etter anbefalte endringer under: **9/10 som LLM-instruks**

## Viktigste blokkerende endringer før LLM-implementering

### 1. MÅ: rett `pad0()`-spesifikasjonen

Planen spesifiserer en `pad0()`-helper og nevner `sprintf("%07s")`-lignende string-padding. Dette er et konkret risikopunkt. `%07s` er ikke en trygg måte å nullpadde strings på i R. For strings kan resultatet bli space-padding, ikke zero-padding.

Dette er alvorlig fordi yrkeskoder og crosswalks er sentrale i treatment- og celledefinisjoner. Feil padding kan gi feil mapping, feil `yrke4`, feil exposure og dermed feil estimater.

**Krav:** Implementer `pad0()` eksplisitt uten `sprintf("%0*s")` eller `sprintf("%07s")` for strings.

Foreslått implementering:

```r
pad0 <- function(x, width) {
  x_chr <- as.character(x)
  x_chr <- trimws(x_chr)
  out <- ifelse(
    is.na(x_chr),
    NA_character_,
    paste0(strrep("0", pmax(width - nchar(x_chr), 0L)), x_chr)
  )
  out
}
```

Obligatoriske tester:

```r
stopifnot(identical(pad0("111101", 7), "0111101"))
stopifnot(identical(pad0("0310", 4), "0310"))
stopifnot(identical(pad0("12345", 4), "12345"))
stopifnot(is.na(pad0(NA_character_, 7)))
```

### 2. MÅ: gjør Stata→R-ekvivalens testbar

Planen sier flere steder at R-portene skal følge Stata 1:1. Det er ikke nok for en LLM. Hvert script må ha eksplisitte kontrakter for input, output, keys, sortering, missing-policy, logging og asserts.

Typiske Stata→R-feller som må testes:

| Tema | Risiko i R-port |
|---|---|
| Missingverdier | `sum(x)` gir `NA` uten `na.rm=TRUE`; Stata summerer ofte over nonmissing |
| Collapse/aggregering | All-missing grupper kan bli `NaN`, `NA`, 0 eller droppes |
| Datoer | `haven` kan lese Stata-dato som `Date`, numeric eller labelled avhengig av metadata |
| Dedup | `unique(by=)` beholder første rad, men bare gitt riktig radrekkefølge |
| Sortering | `setkey()` sorterer og kan endre “første rad”-semantikk |
| Vekter | Stata `[aw=]` er ikke automatisk lik R-vekter |
| Factor-referanser | `fixest::i()` er sensitiv for type og levels |
| FE-dropping | `fixest` kan droppe observasjoner med singleton/perfect fit/nullutfall |

**Krav:** For hvert script må LLM-en få en kontrakt med disse feltene:

```text
Script:
Formål:
Inputfiler:
Outputfiler:
Required columns in output:
Keys / uniqueness constraints:
Sorteringskrav:
Missing-policy:
Dato-policy:
Vekte-policy:
Logging:
Assertions:
Acceptance tests:
Ikke tillatt:
```

### 3. MÅ: innfør Stata-vs-R overlap-test

Planen har dry-run og syntetisk røyk-test. Det er bra, men ikke nok. Dry-run tester metadata, ikke empirisk ekvivalens. Syntetisk data tester bare de tilfellene man har plantet.

Det bør legges inn en egen overlap-test der gammel Stata-pipeline og ny R-pipeline kjøres på samme dataperiode og sammenlignes.

Anbefalt valideringsdesign:

| Trinn | Formål | Forventning |
|---|---|---|
| A. R-port på gammelt 1183-vindu | Tester Stata→R-porten | Skal være identisk eller nesten identisk |
| B. 1191 på overlapp 2021m1–2025m7 | Tester datauniversbyttet | Skal være nært, men kan avvike pga. leveranseforskjeller |
| C. 1191 fullt vindu til 2026m2 | Tester tidsutvidelsen | Skal gi plausibel kontinuitet |
| D. 7d-modul | Tester vitenskapelig sammenligning | Avvik skal kunne dekomponeres |

Minimumssammenligninger for Stata-vs-R overlap:

```text
- n rows in cells
- n firms
- n yrke4
- n firm × yrke4 × age_bin × ym cells
- sum(count_all)
- sum(count_new)
- weighted mean wage
- weighted mean hours
- n in_headline
- n in_headline_priv
- n in_ft
- n in_ft_priv
- n in_bcc_full
- exposure coverage
- checksum per ym × age_bin × ai_q
```

Skriv differansene til:

```text
diagnostics/stata_r_overlap_diff.csv
```

### 4. MÅ: hindre stale output etter feil

Planen lar estimering fortsette etter feil. Det kan være praktisk, men farlig. Dersom et estimat feiler og gammel CSV fortsatt ligger i outputmappen, kan senere tabellbygging lese gamle resultater og gi inntrykk av komplett kjøring.

**Krav:** Bruk enten timestampet run-directory eller autoritativ manifestfil. Beste løsning er begge.

Anbefalt struktur:

```text
from_secure_server/runs/YYYY-MM-DD_HHMM_1191_full/
  logs/
  coefficients/
  diagnostics/
  fragments/
  manifest.csv
```

Minimumsfelter i `manifest.csv`:

```text
script
status
started_at
ended_at
input_files
output_files
n_rows_main_output
checksum_or_summary_hash
error_message
```

Downstream scripts skal nekte å bygge tabeller dersom nødvendige steg ikke har `status == "success"`.

### 5. MÅ: utvid 7b↔7d-sjekken

Planen sier at 7b og 7d skal skrive `sum_count_all` per `age_bin`, beregnet på samme `in_headline_priv`-slice før kollaps. Dette er nyttig, men for svakt alene.

Lik totalsum per aldersgruppe fanger ikke nødvendigvis:

- feil fordeling over måneder
- feil `post`
- feil `ai_q`
- ulik nullfylling
- ulik observasjonsdropping i `fixest`
- feil lønnsvekter
- ulik cluster-count
- ulik yrke4-dekning

Obligatoriske sammenligninger mellom 7b og 7d-restricted før modell:

```text
age_bin: sum_count_all
age_bin × ym: sum_count_all
age_bin × ai_q: sum_count_all
age_bin × post × ai_q: sum_count_all
age_bin × ym: n_yrke4
age_bin: n_foretak
age_bin: n_yrke4
```

Obligatorisk modelldiagnostikk per estimat:

```text
n_obs_model
n_clusters
n_fe_firm_or_yrke4
n_fe_ym
n_dropped_obs
n_dropped_fe
sum_count_all_model_sample
convergence_status
fixest_notes_or_warnings
```

Skriv dette til:

```text
diagnostics/7b_7d_sample_comparison.csv
diagnostics/fixest_model_diagnostics.csv
```

## Styrker i planen

### Riktig sentralisering i `0_settings.R`

At `0_settings.R` skal eie stier, `ym()`, `KMIN/KMAX`, `month_grid()`, `ameld_path()`, `read_dta_cols()`, `read_faste_oppl()`, `load_cells()`, `load_population()`, `stata_aw_sd()`, logging og test-root er riktig arkitektur.

Men `0_settings.R` må behandles som et API. Det skal ikke bare være “første script”. Det må være låst og testet før andre scripts skrives.

Anbefalt intern struktur:

```r
# 1. Constants and paths
# 2. I/O helpers
# 3. Stata-compatibility helpers
# 4. Logging and manifest helpers
# 5. Selftests
```

Anbefalt selvtest-hook:

```r
if (identical(Sys.getenv("AI_NORWAY_RUN_SELFTESTS"), "1")) {
  run_settings_selftests()
}
```

### God datadisiplin rundt 1191

Planen er tydelig på filstier, filnavn, ikke-nullpaddede måneder, `lopenr_person`, `w19_0345_lopenr_person`, `str8`-felter i `faste_oppl`, duplikater og `old/Old`-feller. Dette reduserer risikoen for at LLM-en gjetter feil.

Krav til LLM: ikke hardkod alternative stier. Alle stier skal gå via `0_settings.R`.

### Fornuftig minnestrategi

Script 3 med månedlig lesing, tidlig inner join og `.rds` per måned er fornuftig. Script 4 med collapse før exposure-join er også fornuftig dersom exposure kun avhenger av `yrke4`.

Men minneestimatene må behandles som hypoteser. R kan kopiere store objekter under joins, `rbindlist`, faktor-konvertering og modellklargjøring.

Obligatorisk minnelogging i tunge scripts:

```r
log_size <- function(x, name) {
  message(sprintf("%s: %s", name, format(object.size(x), units = "GB")))
}
```

Bruk etter store steg:

```r
log_size(stack, "stack_after_rbind")
log_size(outcomes_unbal, "outcomes_unbal")
log_size(frtk_active, "frtk_active")
log_size(cell_keys, "cell_keys")
log_size(cells_balanced, "cells_balanced")
```

Script 4 bør også støtte en diagnostisk modus, for eksempel:

```text
AI_NORWAY_MAX_MONTHS=3
```

### God vitenskapelig idé i 7d-modulen

7d-modulen er metodisk godt motivert fordi den dekomponerer forskjeller i:

1. spesifikasjon: firm-FE 7b vs yrke4+måned-FE 7d-restricted
2. restriksjon: 7d-restricted vs 7d-unrestricted
3. datakilde: 7d-unrestricted vs microdata.no

Dette gjør resultatforskjeller tolkbare. Men 7d må skrives sist, etter at `cells_flagged.rds`, 7b og sample-diagnostikk er validert.

## Krav til LLM-implementering

### Generelle regler

LLM-en skal følge disse reglene for hvert script:

```text
1. Skriv kun scriptet som er bedt om.
2. Ikke endre andre filer uten eksplisitt instruks.
3. Bruk bare base R, haven, data.table og fixest.
4. Alle stier og konstanter skal komme fra 0_settings.R.
5. Ikke hardkod Windows-stier utenom 0_settings.R.
6. Ikke bruk silent tryCatch rundt kjerneoperasjoner.
7. Store filtre skal logge n før og etter.
8. Store objekter skal logge object.size.
9. Output skal skrives atomisk: først tempfil, deretter file.rename().
10. Output skal leses tilbake eller skjemasjekkes etter skriving.
11. Alle warnings som kan påvirke estimater skal logges.
12. Ingen estimeringsoutput er gyldig uten manifest-status success.
```

### Script-mal for LLM

Bruk denne malen når LLM-en får én implementeringsoppgave:

```text
Du skal skrive kun <scriptnavn>.

Formål:
<input>

Tillatte pakker:
- base R
- haven
- data.table
- fixest, bare hvis scriptet estimerer modeller

Krav:
- source("0_settings.R") først
- bruk kun helpers fra 0_settings.R for stier, logging og I/O
- ikke hardkod paths
- ikke endre andre scripts
- skriv output atomisk
- legg inn asserts som spesifisert
- logg alle før/etter-rader for filtre

Inputfiler:
<liste>

Outputfiler:
<liste>

Required output schema:
<kolonner og typer>

Keys:
<unique constraints>

Sorteringskrav:
<krav>

Missing-policy:
<krav>

Acceptance tests:
<tester>

Ikke tillatt:
<negative krav>
```

## Per-script kontrakter som bør legges til planen

### `0_settings.R`

MÅ inneholde:

```text
check_packages()
ym(y, m)
month_grid()
ameld_path(y, m)
pad0(x, width)
read_dta_cols(path, cols)
read_faste_oppl()
load_cells()
load_population()
stata_aw_sd(x, w)
open_log()
close_log()
write_fragment()
rebuild_results_md()
write_manifest_entry()
atomic_saveRDS()
atomic_fwrite()
run_settings_selftests()
```

MÅ teste:

```r
stopifnot(ym(2022, 11) == 754)
stopifnot(PERIOD_END == ym(2026, 2))
stopifnot(KMAX == 39)
stopifnot(pad0("111101", 7) == "0111101")
stopifnot(!grepl("old", tolower(ameld_path(2021, 1))))
```

BØR teste `stata_aw_sd()` mot en håndlaget fasit.

### `1_exposure.R`

MÅ sjekke:

```text
- styrk08 er character etter import
- pad0(styrk08, 4) brukes
- ai_q er kun 1:5
- én rad per yrke4 i sluttoutput
- forventet exposure-dekning logges
```

### `1b_load_styrk7_crosswalk.R`

MÅ sjekke:

```text
- 7117 mappinger, hvis dette er fast forventning
- IKKE bruk substr for å lage yrke4
- militærkode 0111101 → 0310 testes eksplisitt
- ingen dupliserte yrke7-keys i crosswalk
```

Test:

```r
stopifnot(crosswalk[yrke7 == "0111101", yrke4] == "0310")
```

### `2_relevant_ids.R`

MÅ sjekke:

```text
- defensiv rename fra w19_0345_lopenr_person til lopenr_person
- str8-felter konverteres eksplisitt med as.integer
- duplikater håndteres deterministisk
- kohortfilter 1961–2005 logges før/etter
- output heter relevant_ids.rds
- output har unik lopenr_person
```

### `3_monthly_filtered.R`

MÅ sjekke:

```text
- missing månedsfil gir stop(), ikke skip
- hver måned leser kun nødvendige kolonner
- ym i output matcher måneden i filnavnet
- yrke7 nullpaddes til 7 tegn
- yrke4 kommer fra crosswalk, ikke substr
- Date-import av arb_start valideres eksplisitt
- stillingspst-cap 200 beholdes
- overtid cap 80 / >300 → NA beholdes nøyaktig som i Stata
- n_unmapped_yrke7 og n_missing_arb_start logges per måned
```

Edge cases i syntetisk test:

```text
- yrke7 som trenger venstre-nullpadding
- militærkode 0111101
- missing arb_start
- overtid >300
- overtid mellom 80 og 300
- stillingspst >200
```

### `4_aggregate_cells.R`

MÅ sjekke:

```text
- exposure-join etter collapse er bare tillatt dersom exposure er unik per yrke4
- broaggregat occ_unrestricted_agg.rds skrives før aktivitetsfilter
- balansert grid har forventet omfang
- counts nullfylles på syntetiske rader
- means forblir NA på syntetiske rader
- dedup matcher Stata: kronologisk stack før unique(by=)
- setorder skjer etter dedup hvis det kan påvirke første-rad-semantikk
```

Obligatoriske asserts:

```r
stopifnot(!anyDuplicated(exposure[, .(yrke4)]))
stopifnot(all(c("count_all", "count_new") %in% names(cells_balanced)))
stopifnot(all(cells_balanced$count_all >= 0, na.rm = TRUE))
stopifnot(all(cells_balanced$count_new >= 0, na.rm = TRUE))
```

Logg:

```text
n rows monthly collapsed
n rows stacked
n rows unrestricted aggregate
n rows balanced grid
n synthetic rows
n missing exposure before/after join
n distinct firms
n distinct yrke4
n distinct age_bin
n distinct ym
```

### `5_apply_restrictions.R`

MÅ sjekke nested-relasjoner der konseptuelt riktig:

```r
stopifnot(all(in_headline_priv <= in_headline, na.rm = TRUE))
stopifnot(all(in_ft_priv <= in_ft, na.rm = TRUE))
```

Hvis `in_bcc_full` skal være subset av et annet flagg, må dette spesifiseres eksplisitt før implementering.

### `5b_population.R`

MÅ sjekke:

```text
- kvartal→måned-transformasjon er eksplisitt
- output key: age_bin × ym
- ingen dupliserte age_bin × ym
- population er nonmissing og ikke-negativ
```

### `5c_baseline_kref.R` og `5d_sample_size_diagnostic.R`

MÅ ikke bare være “mekaniske porter”. De må ha eksplisitte outputskjemaer og forventede summer.

### Estimeringsscripts `6`, `6c`, `6d`, `7`, `7b`, `8`, `6e`, `7c`

MÅ sjekke:

```text
- alle bruker load_cells()
- ingen leser cells_flagged.dta
- periode kommer fra settings
- KMIN/KMAX kommer fra settings
- Q3-referanse dokumenteres hvis ref2="3" brukes
- modelldiagnostikk skrives til diagnostics/fixest_model_diagnostics.csv
```

### `7d_did_byage_cellspec.R`

MÅ implementere tre diagnostiske nivåer:

```text
1. raw sample diagnostics før kollaps
2. collapsed yrke4 × ym diagnostics
3. fixest model diagnostics
```

MÅ hardlåse `ai_q`:

```r
as_ai_q_factor <- function(x) {
  out <- factor(as.integer(as.character(x)), levels = 1:5)
  stopifnot(!any(is.na(out)))
  out
}
```

Før modell:

```r
dt[, ai_q := as_ai_q_factor(ai_q)]
stopifnot(identical(levels(dt$ai_q), as.character(1:5)))
```

MÅ skrive output med minst:

```text
sample
variant
age_bin
outcome
ai_q
coef
se
p_value
n_obs
n_occ
n_clusters
sum_count_all
sum_count_all_model_sample
convergence_status
```

### `99_master.R`

MÅ:

```text
- skrive manifest
- bruke timestampet run-dir eller invalidere output før scriptstart
- abortere ved prep-feil
- tillate estimeringsfeil bare dersom status skrives tydelig
- returnere nonzero exit code hvis nødvendige scripts feiler
- skrive statusoppsummering til slutt
```

BØR støtte:

```text
Rscript 99_master.R group=prep
Rscript 99_master.R group=est
Rscript 99_master.R group=heavy
Rscript 99_master.R from=3 to=4
Rscript 99_master.R only=7d
```

## Syntetisk testdata: anbefalte edge cases

Den syntetiske røyk-testen bør ikke bare teste happy path. Den bør inkludere edge cases som er målrettet mot typiske LLM-feil.

MÅ inkludere:

```text
- yrke7 som trenger venstre-nullpadding
- militærkode 0111101 → 0310
- duplikat i faste_oppl
- str8-felter i faste_oppl
- missing arb_start
- spell med missing lopenr_foretak
- overtid >300 som skal bli NA
- overtid mellom 80 og 300 for å teste asymmetrien
- stillingspst >200
- all-missing lønnsgruppe
- cell med count_all=0 etter balansering
- Q5/ung plantet effekt med kjent fortegn
```

MÅ teste etter full syntetisk kjøring:

```text
- 99_master.R fullfører
- alle forventede outputfiler finnes
- manifest har status success for nødvendige scripts
- 7b og 7d-restricted matcher på sample-diagnostikk
- plantet effekt har riktig fortegn
- militærkode er mappet riktig
- zero-filled counts er 0
- synthetic-row means er NA
```

## Prioritert risikoliste

| Prioritet | Risiko | Hvorfor alvorlig | Tiltak |
|---:|---|---|---|
| 1 | Feil `pad0()` | Kan ødelegge yrkeskoder, crosswalk og treatment | Erstatt `sprintf`, legg inn tester |
| 2 | Stata→R missing-/collapse-avvik | Gir stille empiriske endringer | Mini-fixtures + Stata-vs-R overlap-test |
| 3 | Stale output etter failed estimation | Kan gi falskt komplett resultatsett | Timestampet run-dir + manifest |
| 4 | For svak 7b↔7d-sjekk | Lik totalsum fanger ikke fordelingsfeil | Sjekk `age_bin × ym × ai_q × post` |
| 5 | `fixest` dropper observasjoner ulikt | Kan endre estimat uten tydelig feil | Logg nobs, clusters, FE-levels og dropped obs |
| 6 | Script 4 minnebruk undervurdert | Kan feile sent på server | Diagnostic mode + minnelogging |
| 7 | LLM improviserer struktur | Gir uensartet kode og skjulte avvik | Én scriptkontrakt per oppgave |
| 8 | 1191-migrering og R-port blandes | Vanskelig å forklare resultatendringer | Valider i fire trinn |

## Anbefalt rekkefølge for LLM-arbeidet

Ikke gi LLM-en hele planen og be den implementere alt. Bruk review-gates.

### Gate 1: `0_settings.R`

LLM skriver kun `0_settings.R`.

Review må fokusere på:

```text
ym()
month_grid()
ameld_path()
pad0()
read_dta_cols()
read_faste_oppl()
stata_aw_sd()
load_cells()
logging
manifest
atomic writes
test-root
selftests
```

Ingen andre scripts før denne er låst.

### Gate 2: syntetisk testdata

LLM skriver `_make_synthetic_test_data.R` før de tunge produksjonsscriptene. Dette tvinger frem kontrakter og edge cases tidlig.

### Gate 3: små scripts

Implementer og test:

```text
1_exposure.R
1b_load_styrk7_crosswalk.R
2_relevant_ids.R
5b_population.R
```

### Gate 4: `3_monthly_filtered.R`

Dette er første store datarisiko. Kjør på syntetisk data og deretter begrenset månedsutvalg.

### Gate 5: `4_aggregate_cells.R`

Behandle som eget delprosjekt. Her ligger størst risiko for minne, aggregering, balansering og Stata-avvik.

### Gate 6: restriksjoner og eksisterende estimater

Først når `cells_flagged.rds` er validert.

### Gate 7: `7d_did_byage_cellspec.R`

Skriv 7d sist, etter at 7b er oppdatert og sample-diagnostikken er stabil.

### Gate 8: `99_master.R` og dokumentasjon

Master-script og dokumentasjon ferdigstilles etter at alle underliggende kontrakter og outputskjemaer er stabile.

## Akseptansekriterier for full kjøring

En full kjøring skal ikke regnes som godkjent før disse filene finnes og er konsistente:

```text
logs/log_master_R.txt
logs/log_*.txt for hvert script
diagnostics/run_manifest.csv
diagnostics/settings_selftest.txt
diagnostics/dryrun_validate.csv
diagnostics/monthly_filter_funnel.csv
diagnostics/aggregate_cell_counts.csv
diagnostics/restriction_funnel.csv
diagnostics/7b_7d_sample_comparison.csv
diagnostics/fixest_model_diagnostics.csv
diagnostics/stata_r_overlap_diff.csv, hvis overlap-test kjøres
coefficients/*.csv
```

Kjøringen skal feile dersom:

```text
- en nødvendig inputfil mangler
- en nødvendig variabel mangler
- en outputfil har feil skjema
- manifest mangler success for nødvendig prep-script
- 7b og 7d-restricted ikke matcher på avtalte sample-diagnostikker
- ai_q har verdier utenfor 1:5
- yrke4 mangler exposure i analytisk sample
- KMAX ikke matcher periodeavledet verdi
- stale output oppdages
```

## Endelig anbefaling

Planen bør brukes, men ikke som én stor prompt til en LLM. Den bør først omformes til kontrakter og gates. De fem viktigste endringene er:

```text
1. Rett og test pad0() før noe annet.
2. Legg inn eksplisitte input/output-kontrakter per script.
3. Legg til Stata-vs-R overlap-test på gammel periode.
4. Utvid 7b↔7d-sjekken fra totalsum til fordelingssjekker.
5. Innfør timestampet run-dir og manifest som hindrer stale output.
```

Med disse endringene blir planen robust nok til at en LLM kan bidra effektivt uten å få for stort rom til å produsere plausible, stille feil.
