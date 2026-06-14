# Data Documentation Project

## What this is

This folder contains tools for documenting and exploring the register data available in SSB project 1191 (`W:\1191` on the secure server).

## Files

- `metadata_1191.csv` — 59,185 rows, one per variable per .dta file. Columns: filepath, filename, nobs, nvar, varname, vartype, format, varlabel. Scanned from `W:\1191` with depth 3. Generated April 2026.
- `scan_metadata.do` — Stata program that generates the CSV. Location on secure server: `H:\metadata_scan\scan_metadata.do`. Scans `W:\1191` recursively (3 levels), writes to `H:\metadata_scan\metadata_1191.csv`.
- `variabel_lookup.csv` — **Primary lookup file.** 2,179 unique variables from metadata_1191 enriched with SSB descriptions. Columns: varname, description, varlabel, ssb_beskrivelse, vartype, n_files, example_file, ssb_kilde, definisjon, kodeliste. Use `description` column for the best available label (SSB description if available, otherwise Stata varlabel). 520 variables have SSB descriptions, 1048 have Stata labels only, 611 have no description.
- `variabel_beskrivelser.csv` — 6,505 rows from SSB variabellister. All variables SSB documents for researcher data access, including variables not in project 1191. Columns: variabelnavn_ssb, beskrivelse, definisjon, kodeliste, fra_aar, til_aar, kilde_fil, varname_normalized.
- `variabellister_ssb/` — 29 original Excel files downloaded from SSB's variabellister page (April 2026). Cover: a-ordningen, aksjonærregisteret, arbeidskonflikter, atlto, barnevern, befolkning, bof, boforhold, elhub, FD-Trygd, FDI, fob, helsepersonell, inntekt, introduksjonsordningen, kapitaldatabasen, kontantstøtte, krim, lønn, piaac, regnskap, skjermingsfradrag, struktur, sykefravær, sysselsetting, UFATS, utdanning, utenrikshandel, valg.
- `build_variable_lookup.py` — Script that parses all Excel files and builds the lookup CSVs. Run to regenerate after adding new variabellister.
- `fd_trygd_forlopsfiler.md` — **Viktig**: bruksanvisning for FD-Trygd forløpsfiler (f_aap, f_rehab, f_attf osv.). Beskriver oppstartslinje/avslutningslinje-strukturen, sensurering, tidsdekning per register, og spesielt at attføring 2002–2010 må hentes fra sofastat (ikke f_attf). Les denne før du bygger analyser på FD-Trygd.

## Key data sources in W:\1191

| Directory / prefix | Contents | Years |
|---|---|---|
| `aksjer_`, `aksjonaerer_` | Shareholder registry (aksjonaerregisteret) | 2004-2022 |
| `ameld_statdata_` | A-melding (monthly employer reports, wages). Path: `W:\1191\atid\`. File pattern: `ameld_statdata_{YYYY}_m{M}.dta`. Key vars: `lopenr_person`, `arb_yrke` (7-sifret yrkeskatalog/STYRK-98, substr 1-4 gir 4-sifret), `arb_komm_nr` (arbeidsstedskommune), `arb_arbeidstid` (avtalt timer/uke), `arb_stillingspst` (stillingsprosent), `pers_sum_arbeidstid` (samlet timer for personen), `pers_sum_stillingspst` (samlet stillingspst for personen), `arb_hovedarbeid` (hoved/bi-arbeidsforhold), `arb_syss` (sysselsettingsklassifikasjon), `virk_komm_nr` (virksomhetens kommune). NB: arb_yrke følger yrkeskatalogen (STYRK-98), IKKE STYRK-08 — bruk konkordanstabell for mapping. | 2015-2023 |
| `atmlto` | Arbeidstakerregisteret (employee register). Path: `W:\1191\atid\`. File pattern: `atmlto{YYYY}.dta`. Key vars: `lopenr_person`, `yrk_kode` (yrkeskode/stillingskode), `kommnr` (foretakets skattekommune), `arb_komm` (arbeidsstedskommune), `korr_tim` (arbeidstid timer/uke), `b_dager` (beregnede dager), `nace_nar` (næringskode SN07). NB: Yrkeskodeinformasjonen er mangelfull ca 2003-2007. | 1992-2014 |
| `bof` | Bedrifts- og foretaksregisteret | 1995-2015 |
| `formue` | Wealth/asset data from tax returns | 1994-2015 |
| `formueskatt_g2004g2018` | Wealth tax data (pooled) | 2004-2018 |
| `formuesvariabler` | Wealth variables (pooled across years). Path: `W:\1191\innt\formuesvariabler.dta`. År-identifikator: `aargang` (str4 — `"2020"`, ikke `2020`). Nøkkelvariabler: `sum_gjeld`, `studiegjeld`, `usikret_gjeld`, `bankinnskudd`, `prim_mark` (beregnet markedsverdi primærbolig), `sek_mark`, `ber_nettoformue`, `ber_bruttoformue`, `brutto_finanskapital`. **NB:** fila har flere rader per `lopenr_person` også innen samme `aargang` — collapse (f.eks. `collapse (max) prim_mark, by(lopenr_person)`) før 1:1- eller m:1-merge. | — |
| `fravaer_` | Sickness absence registry | 2007-2021 |
| `hush_fam_` | Household/family composition. Path: `W:\1191\demo\`. To jevnlige versjoner per år: `hush_fam_{YYYY}.dta` (flere rader per person — en per familiemedlemskap) og `hush_fam_{YYYY}_nodup.dta` (én rad per person, samme variabler). **Bruk `_nodup`-varianten ved 1:1-merge på `lopenr_person`.** | 2005-2023 |
| `inntekt` | Income registry | 1993-2022 |
| `lign_`, `pers_`, `kort_` | Tax assessment data (ligningsdata) | varies |
| `selvangivelse` | Tax returns (skattemelding) | 1991-2018 |
| `sofa` | Employment statistics (monthly) | 2018-2022 |
| `sofastat` | Employment statistics (annual) | 1989-2018 |
| `syk_teller_` | Sickness benefit spells (quarterly) | 2000-2022 |
| `vof_foretak_`, `vof_roller_` | Business registry (VoF) | 2016-2023 |
| `lonnsstat` | Wage statistics. Path: `W:\1191\innt\`. File pattern: `lonnsstat{YYYY}.dta`. Key vars: `lopenr_person`, `styrk` (STYRK yrkeskode, 4-sifret), `bu_nus2000` (NUS-kode for utdanning), `arb_yrke` + `arb_yrke_isco` (fra 2015). Nyttig fordi den har både yrke og utdanning i samme fil. | 1997-2018 |
| `regnsk`, `regn_fore_` | Company accounts (regnskap) | 1993-2022 |
| `roller_` | Board/ownership roles | 2002-2016 |
| `utd`, `iutd` | Education registry. Path: `W:\1191\utd\`. `f_utd_demografi.dta` er hovedfilen — hendelseshistorikk med key vars: `lopenr_person`, `bu` (6-sifret NUS-2000 kode for høyeste utdanning, str6), `kommnr` (bostedskommune 1. okt, str4), `bu_kltrinn` (klassetrinn). NUS-koden: 1. siffer = nivå (0-2 grunnskole, 3 påbegynt vgo, 4-5 fullført vgo, 6 bachelor, 7 master, 8 PhD), 2. siffer = fagfelt (0 allmenn, 5 naturvit/teknikk, 6 helse/sosial). `f_utd_kurs.dta` har løpende utdanningsaktivitet med `nus2000`. | 1980-2018 |
| `kurs` | Karakter- og prøvedata på elev × skole-nivå. Path: `W:\1191\kurs\`. `tab_kar_grs.dta` (grunnskolekarakterer, ~20 mill rader, én rad per elev × fag ved 10.-klasseavgang) har `lopenr_person`, `lopenr_orgnr` (skole-ID), `skolekom`, `fagkode`, `skr` (skriftlig kar.), `mun` (muntlig kar.), `avgdato` (str6). `nasjonale_prover.dta` har 5./8./9.-trinns prøver fra 2007 med `lopenr_avgiverskole_orgnr`, `aargang`, `prove`, `mestringsnivaa`. Begge er hovedkilder for skole×år-panelet (n_jt, A_jt) brukt i dgp_skolesegregering. | varies |
| `faste_oppl` | Fixed personal characteristics. Path: `W:\1191\demo\faste_oppl.dta`. Key vars: `lopenr_person`, `foedselsaar`, `foedsels_aar_mnd`, `doeds_aar_mnd`, `kjoenn`, `fodeland`, `invkat` (innvandringskategori), `landbak3gen`, `lopenr_mor`, `lopenr_far`. Tidsinvariant — én rad per person. | — |
| `kommnr` | Bostedskommune per år. Path: `W:\1191\demo\kommnr.dta`. Vars: `lopenr_person`, `bostedskommune_01_01_{YYYY}` for hvert år 1975-2023+. Bruk dette for å plassere personer i kommune over tid. | 1975-2023 |
| `bosatt` | Bosatt-status per dato. Path: `W:\1191\demo\bosatt19920101_20190101.dta`. | 1992-2019 |
| `mor_far_snr`, `slekt` | Parent-child links. Path: `W:\1191\demo\`. | — |
| `sivilstand` | Marital status. Path: `W:\1191\demo\`. Flere filer: `sivilstand_1975_2023.dta`, `sivilstand1992_2019.dta`, `sivilstand_2019_2022.dta`. | 1975-2023 |
| `familienr_sivilstand` | Family ID + marital status. Path: `W:\1191\demo\`. | — |
| `arv_gaver` | Inheritance and gifts | — |

## Avledede filer i `F:\1191\simenm\dataverktøy\`

Ferdigbygde hjelpefiler brukt på tvers av prosjekter (demand_disability, robek_aap, m.fl.). Ligger på F-disken, ikke W-disken.

| Fil | Innhold | Nøkkelvariabler | Dekning |
|---|---|---|---|
| `iutd197401_202210.dta` | Utdanningsdeltakelse som person-måned panel. Hver rad = "personen var i utdanning den måneden". Bruk dette i stedet for å tolke `f_utd_kurs.dta` direkte — det er allerede renset for åpne spells og kjent-gode kilder. Produseres av `F:\1191\simenm\dataverktøy\iutd.do` — kjør det skriptet hvis fila er borte. | `lopenr_person`, `year`, `month` | 1974-01 til 2022-10 |
| `kommunenøkkel.dta` | Mapping av historiske kommunenumre til 2022-standard. Konverteres til lang form via `forbered_kommnr_noekkel` (se `00_hjelpeprogrammer.do` i demand_disability/robek_aap). | kommunenr-kolonner per år | 1976-2022 |

Typisk bruk for `iutd`: for å sjekke om en person er i utdanning en gitt måned, `keep if year == Y & month == M` og merge på `lopenr_person`. Fraværet av en rad = ikke i utdanning.

## Common data linkage patterns

All person-level files link on `lopenr_person` (str10). Typical combinations:

- **Person + demographics**: merge any file with `faste_oppl.dta` for age (`foedselsaar`), gender (`kjoenn`), birth country (`fodeland`), parents (`lopenr_mor`/`lopenr_far`).
- **Person + kommune over tid**: merge with `kommnr.dta` using `bostedskommune_01_01_{YYYY}` for the relevant year.
- **Person + utdanning**: merge with `f_utd_demografi.dta` for `bu` (NUS-kode). Filen er hendelseshistorikk — for tverrsnitt, ta siste registrering per person: `bysort lopenr_person (bu): keep if _n == _N`.
- **Sysselsetting + yrke**: `ameld_statdata` (2015+) har `arb_yrke`, `atmlto` (1992-2014) har `yrk_kode`. Begge er STYRK 4-sifret. NB: atmlto 2003-2007 har mangelfull yrkeskodeinformasjon.
- **Sysselsetting + utdanning + yrke i én fil**: `lonnsstat{YYYY}.dta` har både `styrk` og `bu_nus2000`.

## How to use the data documentation

No microdata here — only metadata (variable names, types, labels, file paths, obs counts). Safe outside the secure zone.

### Typical workflow: "What data do we have for X?"

1. **Search variabel_lookup.csv** for variable names or descriptions matching your topic. The `description` column has the best available label.
2. **Check n_files and example_file** to see how widespread the variable is and which files contain it.
3. **Cross-reference metadata_1191.csv** for full detail: which specific .dta files contain the variable, observation counts, variable types.
4. **Check variabel_beskrivelser.csv** for SSB's full documentation including definitions and code lists — this also includes variables NOT in project 1191 that you might want to request.

### Example queries (in any tool that reads CSV):

Find all variables related to "formue" with descriptions:
```python
import pandas as pd
df = pd.read_csv('variabel_lookup.csv', encoding='utf-8-sig')
df[df.description.str.contains('formue', case=False, na=False)]
```

Find all files containing a specific variable:
```
grep ",lopenr_person," metadata_1191.csv | cut -d',' -f2 | sort -u
```

Find all variables in a specific file:
```
grep "selvangivelse2018" metadata_1191.csv
```

Check what SSB documents for a data area you don't have yet:
```python
df = pd.read_csv('variabel_beskrivelser.csv', encoding='utf-8-sig')
df[df.kilde_fil == 'SSB_variabelliste_barnevern.xlsx']
```

## Kjøreregler for empiriske prosjekter

Disse instruksjonene gjelder når vi bygger empiriske analyser basert på registerdata i prosjekt 1191.

### Overordnet arbeidsflyt

1. **Avklar forskningsdesign** — Simen skisserer forskningsspørsmål, populasjon, utfallsvariabler og analyseperiode.
2. **Gjennomgang av datakilder** — Før noe kodes, gjør vi en felles gjennomgang. Claude slår opp i datadokumentasjonen og presenterer en oversikt over aktuelle kilder: hvilke variabler de inneholder, hvilke år de dekker, kjente komplikasjoner — og konkret hva hver kilde skal brukes til i prosjektet (f.eks. "inntektsregisteret brukes til å måle utfallsvariabelen yrkesinntekt", "faste_oppl brukes til å hente kjønn og fødselsår for aldersavgrensning"). Simen vurderer og korrigerer før vi går videre. Databygging er hoveddelen av arbeidet — estimeringen er oppløpssiden.
3. **Bygg populasjonsfil** — Lag en minimal fil med `lopenr_person` (evt. × år) som definerer hvem som inngår i analysen. Lagres som .dta. All videre databygging bruker denne til å kutte ned store datafiler.
4. **Bygg analysefil** — Åpne populasjonsfilen, merge mot hver datakilde med `keep(1 3) keepusing(...) nogenerate`. Ta kun med variabler vi faktisk trenger.
5. **Deskriptiv statistikk** — Før noe estimeres: dokumenter samplet grundig. Tabeller for N per år, fordelinger av utfall og nøkkelvariabler, samplingskriterier med antall som faller fra i hvert steg.
6. **Estimering** — Først når vi er trygge på at datasettet er riktig.

### Mappestruktur

```
Utenfor sikker sone (kode skrives her):
  prosjekt/code/              <- alle .do-filer

På sikker sone (kode importeres hit):
  H:\prosjektnavn\code\       <- importert kode
  H:\prosjektnavn\code\output\<- resultater som eksporteres ut
  F:\1191\simenm\prosjektnavn\ <- mellomlagring (populasjonsfil, analysefil)
```

### Masterfil og programstruktur

Masterfilen heter `00_master.do` (eller `0_master.do`) og ligger øverst i mappen. Den:
- Definerer globale stier (`$datapath`, `$codepath`, `$output`, `$rawdata`)
- Kjører alle sub-programmer i riktig rekkefølge
- Sub-programmer kan nummereres, men nummereringen trenger ikke være perfekt — det viktige er at master-filen dokumenterer rekkefølgen

Eksempel:
```stata
* 00_master.do
clear all
set more off

global rawdata  "W:\1191"
global datapath "F:\1191\simenm\prosjektnavn"
global codepath "H:\prosjektnavn\code"
global output   "H:\prosjektnavn\code\output"

do "$codepath/01_populasjon.do"
do "$codepath/02_data.do"
do "$codepath/03_deskriptiv.do"
do "$codepath/04_analyse.do"
```

### Kode- og mergestil

- **Merge-mønster**: Start fra populasjonsfilen, merge mot datakilder.
  ```stata
  use "$datapath/populasjon.dta", clear
  merge 1:1 lopenr_person using "$rawdata/innt/inntekt2018.dta", ///
      keep(1 3) keepusing(wyrkinnt wlonn) nogenerate
  ```
- **Alltid `keepusing`**: Spesifiser eksplisitt hvilke variabler som hentes fra hver fil — aldri merge inn hele filer.
- **Alltid `nogenerate`**: Med mindre vi eksplisitt trenger merge-indikatoren.
- **Verifiser mot datadok**: Før du skriver kode, slå opp variabelnavn i `variabel_lookup.csv` og sjekk at variabelen finnes i filen du refererer til via `metadata_1191.csv`.

### Deskriptiv statistikk — obligatorisk

Etter at analysefilen er bygget, produser alltid:
- **Samplingstabell**: Vis utgangspopulasjon og antall som faller fra i hvert filtreringssteg
- **N per år** (for paneldata)
- **Fordeling av utfallsvariabler** (gjennomsnitt, standardavvik, min/max, evt. histogram)
- **Fordeling av sentrale høyresidevariable og kontrollvariabler**
- **Missing-sjekk**: Tabuler manglende verdier for alle nøkkelvariabler

### Output og datasikkerhet

**ALDRI eksporter individ- eller bedriftsdata.** All output som legges i `$output`-mappen skal være anonyme aggregater:
- Logfiler (.log) med deskriptiv statistikk og estimeringsresultater
- CSV- eller .dta-filer med aggregerte tabeller (for figurer/tabeller utenfor sikker sone)
- Estimeringstabeller via `esttab` e.l.

### Feilhåndtering — ikke bruk `capture` for å skjule feil

Koden skal stoppe hvis noe går galt. Stille feil er verre enn høylytte feil.

- **Aldri `capture` rundt merge, collapse, reshape, append** eller andre sentrale dataoperasjoner. Feil der betyr at noe fundamentalt er galt og må fikses.
- **Tillatt bruk av `capture`**: `capture confirm file` (sjekk om fil eksisterer), `capture drop` (variabel som kanskje ikke finnes), og lignende sjekker der vi genuint ikke vet tilstanden og håndterer begge utfall eksplisitt.
- Generelt: foretrekk kode som feiler tydelig fremfor kode som kjører ferdig med feil resultat.

### Krevende datakilder — spør først

Noen datakilder har kjente komplikasjoner (overlappende spells, manglende datoer, definisjonsbrudd). Når Claude møter en slik kilde for første gang, skal han:
1. Spørre Simen om kjente fallgruver
2. Dokumentere erfaringene i denne CLAUDE.md-filen under "Key data sources" slik at kunnskapen akkumuleres

Kjente eksempler:
- `ameld_statdata`: `arb_yrke` er kodet i yrkeskatalogen (STYRK-98), IKKE STYRK-08. Bruk `substr(arb_yrke, 1, 4)` for 4-sifret kode. Konkordanstabell kreves for mapping til STYRK-08.
- `ameld_statdata`: `pers_sum_arbeidstid` (avtalt arbeidstid) kan være > 0 uten at personen er faktisk avlønnet (foreldrepermisjon, permittering uten lønn, ubetalt fravær). Bruk **både** timer og `lonn_kontant > 0` når du vil identifisere "faktisk avlønnet arbeid" — timer alene er ikke nok.
- `atmlto`: Yrkeskodeinformasjonen (`yrk_kode`) er mangelfull ca 2003-2007.

## Technical notes for scan_metadata.do

- Runs on Stata 19 on the secure server
- Norwegian characters (ae, oe, aa) in variable labels are transliterated to ASCII
- If a variable or label causes an encoding error, it writes "(encoding error)" and continues
- Uses `file read` / `while` loop instead of recursive program calls (Stata can't pass paths with special characters as program arguments)
- The `capture` on each variable means individual encoding failures don't crash the whole scan
- To rescan: copy `scan_metadata.do` to `H:\metadata_scan\` and run `do "H:\metadata_scan\scan_metadata.do"`

## Connection to the wealth tax project

This data documentation supports the wealth tax and savings project in the parent folder (`formuesskatt_sparing/`). The main data files used in that project are constructed from:
- `selvangivelse` / `lign_` / `pers_` / `kort_` — tax return data (wealth components, tax liabilities)
- `formue` — wealth variables
- `aksjonaerer_` — shareholder data (for portfolio composition)
- `inntekt` — income data
- `faste_oppl` — demographics (age, gender, education)
- `mor_far_snr` / `slekt` — parent-child links (for family shifting analysis)
- `hush_fam_` — household/family structure (for couple-level analysis)
