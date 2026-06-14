# Norsk Canaries-dashboard: oversikt over Stanford-figurene og vaar replikasjon

Grunnlag for en norsk versjon av Stanford Digital Economy Lab / ADP
"Canaries Dashboard"
(https://digitaleconomy.stanford.edu/project/indicators/canaries-dashboard/).
Deres datapakker (release 2026-05) er arkivert i
`data/stanford_canaries/2026-05/`, en mappe per pakke med tidsserie-CSV,
avledede CSV-er og data dictionary. Siden oppdateres maanedlig fra slutten
av juni 2026.

## Stanfords konvensjoner

- Employment Index = 100 ved normaliseringsdatoen 2022-11-01, per serie.
- Maanedlig, rullerende 5-aarsvindu (naa mai 2021-april 2026). Vinduet
  foelger av utvalget: balansert panel av ~25 000 firmaer med ADP-loenn
  (4,6 mill. arbeidstakere), firmaer til stede hele perioden.
- AI-eksponering: Eloundou et al. (2024)-kvintiler, likevektet per yrke
  (ikke sysselsettingsvektet). Samme konstruksjon som vaar.
- Ingen sesongjustering, ingen befolkningsjustering. Raa headcount.
- Aldersgrupper: 22-25, 26-30, 31-34, 35-40, 41-49, 50+.
- Hver pakke: `{navn}.csv` (indeksserie), `{navn}_yoy_change.csv`,
  `{navn}_annualized.csv`, `{navn}_data_dictionary.md`.
- Avledninger (verifisert numerisk mot filene):
  yoy_t = indeks_t / indeks_{t-12} - 1 (publiseres naar 12 mnd historikk
  finnes); annualized_t = (indeks_t / 100)^(12/k) - 1, k = maaneder siden
  2022-11, publiseres fra k = 6. Begge lagres som desimalrater.
- Figurer: Flourish-linjediagrammer med direktelabels ved endepunktene,
  vertikal markering "ChatGPT Launch" 2022-11-30, aarstall paa x-aksen.
  Palett i kvintilrekkefoelge: #8C1515, #577590, #E54A2B, #E6A817,
  #401415 (vi har samme i `plot_canaries_style_*.py`).

## Figurene paa siden

| # | Figur | Pakke | Innhold |
|---|-------|-------|---------|
| 1 | Employment Index by AI Exposure | `by_exposure` | En linje per kvintil, alle aldre samlet. Filen har i tillegg `composition_E1..E5`: kvintilenes andel av samlet sysselsetting per maaned. |
| 2 | Employment Index by Age Group and AI Exposure | `age_by_exposure` | Fasett `exposure_quintile`, verdikolonner = aldersgrupper. I Flourish vises den med aldersgruppe som filter og kvintiler som linjer. |
| 3 | Employment Index by Age Group | `by_age` | En linje per aldersgruppe, alle yrker i utvalget samlet. |
| 4 | Composition (snapshot) | `composition` | Lang format: `Age Group`, `Exposure Group`, `Share` per 2022-11-01. Sammensetning ved normaliseringsdatoen. |
| 5-8 | Case studies: Software developers, Customer service representatives, Stock clerks, Home health aides | `software_developers` osv. | Indeks per aldersgruppe innen yrket. SOC-baserte yrkesdefinisjoner. |
| 9 | Usage patterns by age | `anthropic_usage_patterns_by_age` | Indeks der yrker er gruppert etter observert Claude-bruk (Anthropic Economic Index) i stedet for Eloundou: fasetter `usage_pattern` (Augmentation/Automation) og `age_bucket`, verdikolonner = brukskvintiler pluss `No usage`. |
| 10-11 | Augmentation/automation ratio composition | `anthropic_usage_*_ratio_composition` | Snapshot-andeler per aldersgruppe og bruksgruppe, som #4. |
| - | To infografikker (PNG) | - | Oppsummering av yoy og annualized per gruppe. Genereres fra de avledede filene. |

## Norsk replikasjon

### Datagrunnlag og avvik fra deres oppsett

- Kilde: A-ordningen via microdata.no, hele populasjonen av private
  loennstakere. Ikke balansert firmapanel; ingen utvalgsseleksjon.
  Dokumenteres som avvik, ikke svakhet.
- Periode: 2021m01-, fast startdato (ikke rullerende vindu; rullerende
  vindu er hos dem en konsekvens av panelbalanseringen).
- Aldersgrupper: 21-30, 31-40, 41-50, 51-60 (uttrekkene har
  decade-grupper; deres finere inndeling krever nytt uttrekk).
- "Canaries sample" = de 397 STYRK-08-kodene med Eloundou-score.
- Case-yrker (STYRK-08): software developers 2512-2514+2519, customer
  service 4222, stock clerks 4321, home health aides 5322. Baseline-N
  (nov 2022, privat, 21-60): 25 974 / 3 993 / 30 257 / 9 363. Merk at
  4222 har tynne celler for 41+, og at 5322 i Norge ogsaa har en stor
  offentlig del som holdes utenfor.
- Usage-figurene (#9-11): definisjon fra BCC (2025), figur 3 B/C.
  Yrker rangeres etter ANDELEN av yrkets Claude-foresporsler som er
  klassifisert som automative hhv. augmentative (automation_share /
  augmentation_share i `styrk08_handa_mapping.csv`), kvintiler
  likevektet per yrke. `No usage` = yrker i canaries-utvalget under
  Handas spoerringsterskel (45 av 397 koder). BCC slaar sammen
  automation-Q1 og Q2 fordi over 20 prosent av deres SOC-koder har
  andel 0; vaare STYRK-andeler har 16,5 prosent nuller og Q1-grense
  0,122, saa sammenslaaingen binder ikke. Gruppering bygges av
  `plot_canaries_style_usage.py` og lagres i
  `data/ai_exposure/styrk08_usage_groups.csv`.
- Befolkningsnevner for per capita: SSB 07459 via
  `data/macro/ssb_population_by_age_quarterly.csv`, interpolert til
  maaned (som i eksisterende per capita-figurer).

### Tilleggsdimensjonen: fire justeringsvarianter

Norske serier har sterk sesong og betydelig befolkningsvekst i enkelte
aldersgrupper, saa hver tidsserie publiseres i fire varianter:

| `adjustment` | Innhold |
|--------------|---------|
| `raw` | Headcount-indeks. Identisk metode som Stanford. |
| `sa` | Sesongjustert headcount. X-11-kjerne med frosne faktorer, jf. `analysis/docs/sesongjustering.md`. |
| `percap` | Headcount delt paa befolkningen i aldersgruppen. |
| `percap_sa` | Baade per capita og sesongjustert. Foretrukket visning. |

`adjustment` legges til som fasettkolonne i tidsserie-CSV-ene; skjemaet
er ellers identisk med deres, og `raw`-radene alene reproduserer deres
format eksakt. Yoy og annualized avledes per variant med formlene over.
Merk at yoy i praksis er sesongrobust (samme kalendermaaned), saa
raw-yoy og sa-yoy skal ligge naer hverandre; det er en innebygd
konsistenssjekk. Snapshot-pakkene (#4, #10-11) trenger ikke varianter.

### Filnavn og struktur

Som deres, med `_no`-suffiks paa pakkenavnet:

```
dashboard/releases/2026-06/
  canaries_no_by_exposure/
    canaries_no_by_exposure.csv            (med adjustment-kolonne)
    canaries_no_by_exposure_yoy_change.csv
    canaries_no_by_exposure_annualized.csv
    canaries_no_by_exposure_data_dictionary.md
  canaries_no_age_by_exposure/
  canaries_no_by_age/
  canaries_no_composition/
  canaries_no_software_developers/
  canaries_no_customer_service/
  canaries_no_stock_clerks/
  canaries_no_home_health_aides/
  canaries_no_usage_patterns_by_age/
  canaries_no_usage_augmentation_ratio_composition/
  canaries_no_usage_automation_ratio_composition/
```

Hver maanedlig release lagres som ny datert mappe og endres ikke i
ettertid (vintage-prinsippet; A-ordningen kan revidere ferske maaneder,
saa releasene dokumenterer hva vi visste naar). `build_release.py`
hopper over pakkemapper som finnes fra foer, saa nye pakketyper kan
legges til en eksisterende release uten aa roere de publiserte filene.

### Tilleggsutfall: nyansettelser og loenn (fra release 2026-06)

Utover sysselsetting (Stanford-paritet) bygges to ekstra utfall,
nyansettelser og FTE-justert loenn, med samme skjema og avledninger.
For hovedkuttene by_exposure, age_by_exposure og by_age, og fra release
2026-06 ogsaa for de fem yrkescasene og for usage_patterns_by_age (per
alder):

```
  canaries_no_hires_by_exposure / _age_by_exposure / _by_age
  canaries_no_wages_by_exposure / _age_by_exposure / _by_age
  canaries_no_{hires,wages}_software_developers / _customer_service /
    _stock_clerks / _home_health_aides / _electricians
  canaries_no_{hires,wages}_usage_patterns_by_age
```

- **Nyansettelser** (`hires_*`): antall jobber per gruppe med
  registrert startdato (ARBLONN_ARB_START) i vinduet mellom forrige og
  gjeldende statusdato; per celle = count x ny_jobb fra
  09f-uttrekket. Alle fire justeringsvarianter. Sterkt sesongpreget --
  sa eller yoy anbefales.
- **Loenn** (`wages_*`): FTE-justert gjennomsnittlig kontantloenn,
  sum(count x kontantlonn) / sum(count x stillingspst/100) over
  yrke-alder-cellene i gruppen, dvs. cellens snittloenn vektet opp til
  fulltidsekvivalent med cellens gjennomsnittlige stillingsprosent
  (09b/09c-uttrekkene). Nominell. Kun variantene raw og sa (per
  innbygger er ikke meningsfullt for loenn). FTE-justeringen
  korrigerer for deltid, men ikke for delmaanedsloenn hos nyansatte
  (liten, sesongstabil effekt; nevnt i data dictionary).
- Validering som for sysselsettingspakkene: 62 maaneder per serie,
  indeks 100 i basismaaneden, ingen manglende verdier (hovedkuttene er
  ogsaa strengt positive; case/usage-hires kan ha ekte nullmaaneder),
  raw-yoy vs sa-yoy-korrelasjon 1,000, og uavhengig rekonstruksjon fra
  raadata med avvik 0 (hires by_age 41-50, wages by_exposure Q5, og for
  de nye pakkene hires customer_service 51-60 og wages usage
  Augmentation Q5).
- Yrkescase og usage-grupper (fra release 2026-06): samme to utfall per
  alder. Loenn er robust overalt. Nyansettelser i de minste yrkene er
  tynne (4222 har ~13 per maaned i 51-60, med null i enkelte
  sommermaaneder), saa hires-pakkene for case/usage faar derived=False
  (ingen yoy/annualized), og sesongjusteringen er gjort robust mot
  nullmaaneder (faktorer fra positive observasjoner; en nullmaaned blir
  staaende som null). En by-alder hires-serie for en liten celle som
  4222/51-60 er dermed gyldig, men stoeyete; om den skal vises per alder
  paa siden er en presentasjonsvurdering.
- Nettsiden (kiindeksen.no) har en utfallsvelger for figur 1-3;
  yrkescase- og usage-figurene viser foreloepig bare sysselsetting. De
  nye hires/loenn-filene ligger i releasen og kan kobles paa figurene
  (prepare_data.py TS_PACKAGES + app.js) som et eget steg.

### Status (per release 2026-06)

Alle 11 pakker eksporteres av `dashboard/build_release.py` til
`dashboard/releases/2026-06/`. Figurer finnes for alle tidsserie-
pakkene: aggregat (`figure_canaries_style_aggregate.pdf`, fire
varianter side ved side), alder x eksponering
(`figure_canaries_style_{raw,percap,percap_sa}.pdf` og `grid4x4`),
yrkescase (`figure_canaries_style_occupations.pdf`,
`figure_consulting_hiring.pdf`) og usage
(`figure_canaries_style_usage_*.pdf`). Nettsidefigurene boer paa sikt
genereres fra release-filene, ikke fra pipelinen direkte, slik at
publiserte figurer og publiserte data alltid stemmer overens.

### Validering av release 2026-06

- Skjemaparitet: kolonnenavn identiske med Stanfords filer (pluss
  `adjustment`); raw-radene reproduserer deres format eksakt.
- Alle tidsserier: 62 maaneder per fasettkombinasjon, ingen manglende
  eller ikke-positive verdier, indeks = 100 i basismaaneden.
- Avledningsregler verifisert mot Stanfords filer numerisk: yoy fra
  forste maaned med 12 maaneders historikk, annualized fra k = 6.
- Uavhengig rekonstruksjon av by_age 41-50 (raw) fra raadata: avvik 0.
- Innebygd konsistenssjekk: raw-yoy og sa-yoy har korrelasjon 1,000 og
  maksavvik 0,0001 (sesong kansellerer i tolvmaanedersendringer);
  avvik her i fremtidige releaser indikerer feil i sesongfaktorene.
- Snapshot-pakkene summerer til 100,00 prosent.

### Kryssland-merknad: svaert ulik eksponeringssammensetning

Composition-pakkene avsloerer en strukturell forskjell som maa med i
alle sammenligninger med Stanford-dashboardet. Andel av samlet
sysselsetting per Eloundou-kvintil ved basismaaneden:

| | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|----|----|----|----|----|
| Norge (A-ordningen, privat, 21-60) | 21,1 | 16,7 | 21,8 | 19,9 | 20,6 |
| Stanford (ADP-panel) | 6,4 | 13,7 | 13,9 | 27,7 | 38,3 |

Norsk privat sysselsetting er tilnaermet jevnt fordelt over
kvintilene, mens ADP-panelet har to tredjedeler av sysselsettingen i
de to mest eksponerte kvintilene og bare 6 prosent i den minst
eksponerte. Tre konsekvenser: (1) deres aggregerte indeks domineres av
eksponerte yrker, vaar ikke; aggregatfigurene maaler dermed ulike
ting. (2) Likevektede kvintiler (samme definisjon hos begge) gir
sysselsettingsmessig svaert ulike grupper i de to landene; Q5-vs-Q1-
sammenligninger boer suppleres med composition-tallene. (3) Forskjellen
reflekterer baade reell naeringsstruktur og at ADP-panelet er et
selektert firmautvalg; populasjonsdekningen vaar er her en
substansiell fordel, ikke bare en metodisk fotnote.
