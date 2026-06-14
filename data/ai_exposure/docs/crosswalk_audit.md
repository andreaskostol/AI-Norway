# Audit av AI-eksponerings-crosswalker: STYRK-08 ↔ O*NET/SOC

*Dato: 2026-04-03. Oppdatert: 2026-04-03 (kvalitetsflagg, manuelle mappinger, tidslinje).*

## Bakgrunn

Vi bruker tre AI-eksponeringsmål mappet til norske STYRK-08-yrker:

| Mål | Kilde | Opprinnelig klassifisering | Vår dekning |
|---|---|---|---|
| Eloundou et al. (2024) | GPT-vurdering av oppgaveeksponering | O\*NET-SOC 2018 | 397 av 407 STYRK-koder (97.5%) |
| Handa et al. (2025) | Faktisk bruk fra Claude.ai-samtaler | O\*NET-SOC 2010 | 352 av 407 STYRK-koder (86.5%) |
| Felten AIOE (2021) | AI-applikasjoner koblet til oppgaver | SOC 2010 → ISCO-08 | Separat crosswalk |

Til sammenligning: Kauhanen (2026, Finland) mapper Handa-data via O\*NET 2019 → SOC 2018 → SOC 2010 → ISCO-08 og ender med **296 ISCO-08-koder** (ca. 67% dekning). Kostøl (2026, BI) bruker Eloundou, Handa og Felten, men har `null` for Eloundou/Handa for 26–30 av 391 STYRK-koder — trolig på grunn av strengere crosswalk.

---

## Crosswalk-kjede

Begge våre mappinger følger samme grunnstruktur:

```
O*NET-SOC (6-siffer) → SOC 2010 (6-siffer) → ISCO-08 (4-siffer) = STYRK-08 (4-siffer)
```

For Eloundou inkluderer vi også SOC 2018 → SOC 2010 som mellomsteg (kildedataene bruker SOC 2018-koder).

Kildene for crosswalker:
- SOC 2018→2010: Offisiell BLS-fil (november 2017)
- SOC 2010→ISCO-08: Offisiell BLS-fil (august 2012, oppdatert juni 2015)
- STYRK-08 = ISCO-08 ved 4-siffer: Dokumentert i SSB Notater 17/2011

Versjonsmessig er kjeden korrekt — ingen mismatch mellom SOC-versjoner.

---

## Identifiserte svakheter

### 1. Delvise matcher (`part`-kolonnen) ignoreres

BLS-crosswalken SOC→ISCO har en `part`-kolonne som markerer delvise matcher med `*`. **38.8% av radene er markert som delvise.** Våre scripts (`build_eloundou_mapping.py`, `build_handa_mapping.py`) leser aldri denne kolonnen — alle matcher behandles som fullstendige 1:1-koblinger.

**Konsekvens:** Når SOC 11-1021 (General and Operations Managers) mapper til 7 ulike ISCO-koder, får hver ISCO-kode den fulle SOC-scoren som om det var en komplett match. Dette inflaterer dekning og introduserer støy.

Kauhanen og andre har lavere dekning (296 vs. våre 350–395 koder). En mulig forklaring er at de filtrerer bort delvise matcher, men vi kan ikke verifisere dette — ingen av artiklene beskriver hvordan delvise matcher håndteres.

### 2. Uvektet gjennomsnitt — ingen sysselsettingsvekter

Når flere SOC-koder mapper til én STYRK-kode, bruker vi **simpelt (uvektet) gjennomsnitt**. En SOC-kode med 500 000 arbeidere teller like mye som én med 5 000.

Sysselsettingsvektet gjennomsnitt ville vært mer forsvarlig for arbeidsmarkedsanalyse, men krever at vi kobler på BLS-sysselsettingsdata per SOC-kode.

### 3. "Broadcasting" fra rest-kategorier skaper kunstig homogenitet

Mange-til-mange-mappinger fører til at én SOC-kodes score kopieres til flere STYRK-koder. Eksempler:

**Eloundou:**
- 25 beta-verdier dupliseres på tvers av flere STYRK-koder
- STYRK 2310 (universitetslærere) er gjennomsnittet av **35 ulike SOC-koder** (fra informatikklærer til kunstlærer) — all variasjon vaskes bort
- Beta=0.224 gis identisk til 5 ulike jordbruksyrker (6121–6221)
- Beta=0.462 gis identisk til 4 ulike lederyrker (1213, 1322, 1349, 1439)

**Handa:**
- 38 unike eksponeringsverdier kopieres til 90 STYRK-koder (26% av mappede koder)
- Fire helt ulike lederyrker får identisk score fra SOC 11-9199 "Managers, All Other"

### 4. Spesifikke anomalier

| STYRK | Yrke | Problem |
|---|---|---|
| 3139 | Prosessoperatører, ikke nevnt annet sted | Eloundou beta=0.804 utelukkende fra "CNC Machine Tool Programmers" — et helt annet yrke enn den brede restkategorien |
| 2211 | Allmennpraktiserende leger | Inkluderer SOC 29-1069, en sekkekategori med 12 spesialisttyper (dermatologer, nevrologer, etc.) som ikke er allmennpraktiserende |
| 2310 | Universitetslærere | 35 SOC-koder (alle "XXX Teachers, Postsecondary") gjennomsnittet — informatikk og kunst får identisk AI-eksponering |

### 5. Norge-spesifikke STYRK-koder mangler helt

55 STYRK-koder har ingen Handa-mapping etter manuelle tillegg, inkludert:
- **5153 Vaktmestre** (25 707 ansatte) — ingen SOC-ekvivalent
- **9312 Hjelpearbeidere i anlegg** (19 191 ansatte)
- **0310 Menige** (13 499 ansatte) og andre militære yrker
- **3254 Optikere**, **3421 Idrettsutøvere**

Manuelle mappinger er lagt inn for de to største:
- **2223 Sykepleiere** (69 497 ansatte) ← 2221 Nursing professionals
- **2224 Vernepleiere** (24 406 ansatte) ← 2221 Nursing professionals

Disse er flagget med `manual_map`-kolonnen i CSV-filene.

### 6. Handa: Lav oppgavedekning

Handa-dataene har scorer for kun **3 364 av 18 428 O\*NET-oppgaver (18.3%)**. Per yrke er mediandekningen bare 20% av oppgavene. Rå `overall_exposure`-verdier er ubegrensede (0.002–7.5) og ufortolkbare — vi bruker persentiltransform for rangering.

### 7. Handa: `pct/n_soc`-delingen

Scriptet deler Handa-task-`pct` med antall SOC-koder som deler oppgaven. Dette behandler AI-bruk som en fast kake som fordeles mellom yrker. Alternativt burde hver SOC fått full `pct` (= "hvor mye AI-bruk er relevant for dette yrket"). I praksis er effekten liten fordi bare 1.4% av oppgavene deles mellom SOC-koder.

---

## Sammenligning med andres tilnærminger

| | Vår mapping | Kauhanen (2026) | Kostøl (2026) |
|---|---|---|---|
| Eloundou-dekning | 397 STYRK (97.5%) | — | ~365 STYRK (93%), 26 null |
| Handa-dekning | 352 STYRK (86.5%) | 296 ISCO (67%) | ~361 STYRK (92%), 30 null |
| Delvise matcher | Beholdes alle, flagget | Ikke beskrevet | Ikke beskrevet |
| Vekting | Uvektet gjennomsnitt | Ikke beskrevet | Ikke beskrevet |
| Manglende kilder | Ingen fallback | — | Bruker Felten alene som fallback |

Kostøl tar gjennomsnittet av tilgjengelige kilder per yrke. For 26 yrker (inkl. alle IT-yrker på toppen og leger) er kun Felten tilgjengelig — disse yrkene dominerer topp-rangeringene, noe som gir en systematisk skjevhet fordi Felten-scoren ikke "dras ned" av Eloundou/Handa.

### Reverse engineering av Kostøls mappinger

**Eloundou:** Korrelasjonen mellom Kostøls `eloundou_norm` og våre `eloundou_beta`-verdier er **0.989** for 365 matchede koder — nesten identisk. De 30 STYRK-kodene Kostøl mangler er nøyaktig de som krever SOC 2018→2010-broen:

- Alle IT-yrker (251x, 252x, 351x) — SOC 2018 bruker `15-12xx`, SOC 2010 brukte `15-11xx`
- Alle leger (2211, 2212) — SOC 2018 bruker `29-12xx`, SOC 2010 brukte `29-10xx`

**Mulig forklaring:** Mønsteret tyder på at Kostøl mapper Eloundous SOC 2018-koder **direkte** mot BLS SOC 2010→ISCO-crosswalken, uten mellomsteg via SOC 2018→2010-bro-tabellen. De 34 SOC-kodene som ble omnummerert i SOC 2018 ville da ikke finne match. Vi kan ikke verifisere dette uten Kostøls kode. Kostøls verdier for matchede koder er omtrent `our_beta / max(our_beta)`, dvs. min-max-normalisert til [0, 1].

**Handa/Anthropic:** Mye større avvik. Spearman-rankkorrelasjonen er bare **0.63**. Mest talende eksempel: **Dataregistrere (4132)** har `anthropic_norm = 1.0` hos Kostøl, men `overall_exposure = 0.01` i vår mapping. I Handa-paperet er "Data Entry Keyers" et av de mest eksponerte yrkene, men vår task-nivå-aggregering (med `pct/n_soc`-deling) gir dem lav score.

**Mulig forklaring:** Den lave korrelasjonen og det avvikende mønsteret for enkeltyrker tyder på at Kostøl bruker en annen aggregering enn vår task_pct-summering — muligens forhåndsaggregerte yrkesnivå-scorer (`job_exposure.csv` fra mars 2026, eller data direkte fra Handa-paperets appendiks). Vi kan ikke verifisere dette uten tilgang til koden. Kostøl har 128 STYRK-koder med `anthropic_norm = 0.0`, og de 29 kodene vi mapper men han ikke har, kan skyldes manglende SOC 2018→2010-bro.

---

## Vurdering

**Er mappingen vår for lite streng?** Ja, det kan innvendes:

1. **97% dekning** er betydelig høyere enn sammenlignbare studier og vanskelig å forsvare uten eksplisitt diskusjon
2. **Alle delvise matcher beholdes** — en enkel forbedring ville være å filtrere eller nedvekte `part`-rader
3. **Uvektet gjennomsnitt** gir uforholdsmessig innflytelse til små nisje-SOC-koder

**Motargumenter:**
- Høy dekning betyr færre droppede observasjoner i analysen
- Crosswalk-problemet er universelt for alle studier som bruker O\*NET-mål utenfor USA
- Persentiltransformen demper effekten av enkeltstående anomalier
- Vi bruker kvintiler, ikke kontinuerlige verdier, noe som gjør analysen mer robust mot mapping-støy

**Anbefaling:** Diskuter dette som en begrensning i paperet. Vis i robusthetssjekker at resultatene holder med strengere mappinger (f.eks. kun fulle matcher, minimum 2 SOC-koder per STYRK).

---

## Kvalitetsflagg i CSV-filene

Begge mapping-filer (`styrk08_eloundou_beta_mapping.csv`, `styrk08_handa_mapping.csv`) inneholder nå kvalitetsflagg:

| Kolonne | Beskrivelse | Kun Handa |
|---|---|---|
| `n_soc_matched` | Antall SOC-koder som bidrar til denne STYRK-koden | |
| `has_partial_match` | 1 hvis minst én SOC→ISCO-kobling er delvis (`*` i BLS-crosswalk) | |
| `manual_map` | Kilde-STYRK-kode hvis manuelt mappet (f.eks. "2221" for 2223 Sykepleiere) | |
| `n_tasks_matched` | Antall O\*NET-oppgaver med match i task_pct | ✓ |
| `n_tasks_total` | Totalt antall O\*NET-oppgaver for de bidragende SOC-kodene | ✓ |
| `task_coverage` | n_tasks_matched / n_tasks_total | ✓ |

### Oppsummering kvalitetsflagg

**Eloundou (397 koder):**
- 229 (57.7%) har minst én delvis SOC→ISCO-match
- 2 er manuelt mappet (2223, 2224)

**Handa (352 koder):**
- 187 (53.1%) har minst én delvis SOC→ISCO-match
- 89 (25.3%) har <10% oppgavedekning
- 90 (25.6%) deler identisk overall_exposure med minst én annen kode
- 2 er manuelt mappet (2223, 2224)

---

## Tidslinje: Anthropic Economic Index-data

| Dato | Hendelse |
|---|---|
| Feb 2025 | HuggingFace `release_2025_02_10` — task_pct_v1, ava |
| Mar 2025 | Handa et al. arXiv:2503.04761 + `release_2025_03_27` — task_pct_v2 |
| Sep 2025 | `release_2025_09_15` — geografisk data, preprosesseringskode |
| **Nov 2025** | **Brynjolfsson et al. publisert** — siterer Handa arXiv |
| **Jan 2026** | **Kauhanen & Rouvinen publisert** — siterer Handa arXiv |
| Mar 2026 | `labor_market_impacts/` — job_exposure.csv (756 SOC 2019-koder), task_penetration.csv |

Basert på publiseringsdatoene hadde trolig verken Brynjolfsson eller Kauhanen tilgang til `job_exposure.csv` (mars 2026). Begge siterer kun Handa et al.s arXiv-artikkel. Vi kan ikke utelukke at de hadde tilgang til upubliserte data fra Anthropic.

`job_exposure.csv` (`observed_exposure`) er et annet mål enn vår `overall_exposure`: det er et tids-vektet gjennomsnitt av oppgave-eksponering med innbakt automasjonsgradering (Anthropic "Labor market impacts" mars 2026). Korrelasjonen med vår task_pct-aggregering er Spearman ρ ≈ 0.70 på STYRK-08-nivå.

---

## Referanser

- Eloundou, T., Manning, S., Mishkin, P., & Rock, D. (2023). GPTs are GPTs: An early look at the labor market impact potential of large language models.
- Handa, K., et al. (2025). The Anthropic Economic Index.
- Felten, E. W., Raj, M., & Seamans, R. (2021). Occupational, industry, and geographic exposure to artificial intelligence: A novel dataset and its potential uses. *Strategic Management Journal*.
- Kauhanen, P. (2026). AI has not impacted the youth labor market in Finland.
- Kostøl, A. (2026). KI-eksponering i norsk arbeidsliv. https://andreaskostol.no/ai/
