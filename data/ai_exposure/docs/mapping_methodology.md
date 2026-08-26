# Mapping av AI-eksponeringsmål til norske yrkeskoder

*Arbeidsdokument, april 2026*

## Oversikt

Vi mapper tre AI-eksponeringsmål til norske STYRK-08 yrkeskoder:

1. **Eloundou et al. (2024):** Ekspertvurdering av GPT-4s potensial til å påvirke oppgaver i hvert yrke (teoretisk kapabilitet). [Artikkel (arXiv)](https://arxiv.org/abs/2303.10130). [Kildedatasett (`eloundou_occ_level.csv`)](data/ai_exposure/eloundou_occ_level.csv).

2. **Handa et al. (2025):** Observert andel av Claude.ai-samtaler som relaterer seg til oppgaver i hvert yrke (faktisk bruk). [Artikkel (arXiv)](https://arxiv.org/abs/2503.04761). [Datasett (HuggingFace)](https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/release_2025_03_27).

3. **Felten et al. (2021):** AI-kapabilitet koblet til yrkesevner via O\*NET. [Felten-artikkel (SMJ)](https://doi.org/10.1002/smj.3286). [Data (GitHub)](https://github.com/AIOE-Data/AIOE).

Eloundou og Handa har sin opprinnelse i O\*NET-oppgavedatabasen og crosswalkes via SOC 2010 → ISCO-08, deretter til overlappende STYRK-08-koder. Felten bruker O\*NET-evner (abilities) og crosswalkes tilsvarende.

---

## 1. Crosswalk-kjeden

### 1.1 Eloundou: SOC 2018 → SOC 2010 → ISCO-08 → STYRK-08

```
  Eloundou GPT-4 β-scorer (798 SOC 2018-koder)
         │
         ▼  BLS SOC 2018→2010-crosswalk
  SOC 2010-koder (778 matchet)
         │
         ▼  BLS SOC 2010→ISCO-08-crosswalk
  ISCO-08 4-siffer-koder
         │
         ▼  Kodefilter mot STYRK-08 (overlappende 4-sifferkoder)
  STYRK-08 4-siffer-koder (397 mappet, 97,5 % av alle STYRK-koder)
```

### 1.2 Handa: O\*NET-oppgaver → SOC 2010 → ISCO-08 → STYRK-08

```
  Handa task_pct (3 365 oppgaver med Claude-bruksandel)
         │
         ▼  Matching til O*NET Task Statements (19 530 oppgave–yrke-par)
  SOC 2010-koder (588 med eksponering > 0)
         │
         ▼  BLS SOC 2010→ISCO-08-crosswalk
  ISCO-08 4-siffer-koder
         │
         ▼  Kodefilter mot STYRK-08 (overlappende 4-sifferkoder)
  STYRK-08 4-siffer-koder (352 mappet, 86,5 % av alle STYRK-koder)
```

**Forskjell fra Kauhanen (2026):** Kauhanen beskriver en 3-stegs kjede fra «O\*NET 2019»-koder. Filen `onet_task_statements.csv` fra Handa et al.s HuggingFace-release (release_2025_03_27) bruker imidlertid **SOC 2010**-koder — kode 15-1131 «Computer Programmers» (pensjonert i SOC 2018) er til stede, mens erstatningen 15-1252 ikke finnes. Vi vet ikke hvilken release Kauhanen brukte — det er mulig at de hadde tilgang til en annen versjon av oppgavedataene, eller at de tolket SOC 2010-kodene som O\*NET-SOC 2019. Vår direkte SOC 2010 → ISCO-08-kjede er basert på den verifiserte kodeversjonen i dataene vi har tilgang til.

### 1.3 Crosswalk-kilder

| Steg | Kilde | Dato | Lenke |
|------|-------|------|-------|
| SOC 2018 → 2010 | BLS offisiell crosswalk | November 2017 | [BLS](https://www.bls.gov/soc/2018/soc_2010_to_2018_crosswalk.xlsx) |
| SOC 2010 → ISCO-08 | BLS offisiell crosswalk | August 2012, oppdatert juni 2015 | [BLS](https://www.bls.gov/soc/isco_soc_crosswalk.xls) |
| ISCO-08 → STYRK-08 | SSB klassifikasjon | Overlappende 4-sifferkoder matches etter kode; STYRK-08 har norske tilpasninger | [SSB](https://www.ssb.no/klass/klassifikasjoner/7) |
| O\*NET Task Statements | O\*NET Database v20.1 | 2015 | [O\*NET](https://www.onetcenter.org/database.html) |
| Handa task_pct_v2 | Anthropic Economic Index | Mars 2025 | [HuggingFace](https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/release_2025_03_27) |

---

## 2. Eloundou-mappingen: Gjennomgått eksempel

### 2.1 Ren match: Programvareutviklere

```
SOC 2018: 15-1252 "Software Developers" (β = 0,87)
  ├─→ SOC 2010: 15-1132 "Software Developers, Applications"
  │     └─→ ISCO/STYRK: 2512 "Programvareutviklere" (full match)
  └─→ SOC 2010: 15-1133 "Software Developers, Systems Software"
        └─→ ISCO/STYRK: 2512 "Programvareutviklere" (full match)

Resultat: STYRK 2512 får β = 0,87, full match, fan-out = 0
```

Begge SOC 2010-koder konvergerer til samme STYRK-kode. Mappingen er utvetydig.

### 2.2 Problematisk match: General Managers

```
SOC 2010: 11-1021 "General and Operations Managers" (β = 0,46)
  ├─→ ISCO 1112 "Toppledere i offentlig administrasjon"  (delvis, fan-out = 7)
  ├─→ ISCO 1114 "Toppledere i interesseorganisasjoner"   (delvis)
  ├─→ ISCO 1120 "Administrerende direktører"             (delvis)
  ├─→ ISCO 1343 "Ledere innen eldreomsorg"               (delvis)
  ├─→ ISCO 1346 "Ledere i bank og forsikring"            (delvis)
  ├─→ ISCO 1420 "Varehandelssjefer"                      (delvis)
  └─→ ISCO 5221 "Innehavere av kiosk/liten butikk"       (delvis)

Resultat: Alle 7 STYRK-koder får identisk β = 0,46
```

Ett amerikansk yrke (General Managers) splittes over 7 ulike norske yrker — fra toppledere i statsforvaltningen til kioskinnehavere. Alle får identisk eksponeringsverdi, noe som åpenbart er for høyt for kioskinnehavere og muligens for lavt for toppledere.

### 2.3 Aggregering

Når flere SOC-koder mapper til samme STYRK-kode, bruker vi **uvektet gjennomsnitt** av β-scorene. Eksempel:

```
STYRK 2310 "Universitets- og høyskolelektorer" mottar scorer fra 35 SOC-koder:
  25-1011 "Business Teachers, Postsecondary"     β = 0,75
  25-1021 "Computer Science Teachers, Postsecon." β = 0,75
  25-1032 "Engineering Teachers, Postsecondary"   β = 0,75
  ...
  25-1121 "Art, Drama, Music Teachers, Postsecon." β = 0,75

Resultat: β = 0,75 (identisk fordi Eloundou ga alle universitetslærere
          den samme teoretiske eksponeringsvurderingen)
```

---

## 3. Handa-mappingen: Gjennomgått eksempel

### 3.1 Oppgavenivå-data

Handa-målet starter fra 3 365 O\*NET-oppgavebeskrivelser ([`task_pct_v2.csv`](https://huggingface.co/datasets/Anthropic/EconomicIndex/blob/main/release_2025_03_27/task_pct_v2.csv)), hver med:
- **task_pct:** Andel av alle Claude.ai-samtaler som relaterer seg til oppgaven (summerer til 100 %)
- **Automasjon/augmentering-fordeling:** Fra [`automation_vs_augmentation_by_task.csv`](https://huggingface.co/datasets/Anthropic/EconomicIndex/blob/main/release_2025_03_27/automation_vs_augmentation_by_task.csv)

**Topp-oppgaver etter Claude-bruk:**

| Andel | Oppgavebeskrivelse |
|-------|-------------------|
| 6,65 % | Modify existing software to correct errors, to adapt it to new hardware... |
| 2,82 % | Diagnose, troubleshoot, and resolve hardware, software, or other network... |
| 2,68 % | Modify existing software to correct errors, allow it to adapt to new hardware... |
| 2,46 % | Correct errors by making appropriate changes and rechecking the program... |
| 2,40 % | Write, update, and maintain computer programs or software packages... |

Programvarerelaterte oppgaver dominerer — de 7 største oppgavene utgjor ~22 % av all Claude-bruk.

### 3.2 Fra oppgaver til yrker

Hver oppgave er koblet til ett eller flere SOC 2010-yrker via O\*NET ([`onet_task_statements.csv`](https://huggingface.co/datasets/Anthropic/EconomicIndex/blob/main/release_2025_03_27/onet_task_statements.csv)). Når en oppgave tilhorer flere yrker, deler vi `task_pct` likt mellom dem:

```
Oppgave: "Modify existing software to correct errors..." (pct = 2,68 %)
  Tilhorer: 15-1131, 15-1132, 15-1133 (3 yrker)
  Hvert yrke mottar: 2,68 % / 3 = 0,89 %
```

Vi summerer deretter over alle oppgaver per yrke for å få `overall_exposure`:

**Eksempel: SOC 15-1132 "Software Developers, Applications"**

| Oppgave (forkortet) | pct | Auto | Augm |
|---------------------|-----|------|------|
| Modify existing software to correct errors... | 2,68 % | 0,26 | 0,73 |
| Analyze user needs and software requirements... | 0,34 % | 0,18 | 0,74 |
| Design, develop and modify software systems... | 0,31 % | 0,34 | 0,65 |
| Analyze information to determine computer specifications... | 0,11 % | 0,17 | 0,79 |
| Store, retrieve, and manipulate data... | 0,10 % | 0,20 | 0,78 |
| Consult with customers about software system design... | 0,08 % | 0,16 | 0,78 |
| *6 oppgaver til med pct < 0,05 %* | ... | ... | ... |
| **Totalt** | **~3,7 %** | **0,27** | **0,73** |

`automation_share` og `augmentation_share` per yrke beregnes som eksponeringsvektede gjennomsnitt av oppgavenivå-andelene.

### 3.3 Oppgavedekning

En viktig begrensning: Kun 3 364 av 18 428 unike O\*NET-oppgaver (18,3 %) finnes i `task_pct`. Mediandekningen per yrke er bare 13 %.

**Eksempel:** SOC 15-1132 (Software Developers) har 15 oppgaver totalt, hvorav 10 matcher task_pct. Dekning: 67 % — godt.

**Eksempel:** SOC 37-2011 (Janitors and Cleaners) har 23 oppgaver, hvorav **0** matcher. Dekning: 0 %. Ingen spor Claude om å moppe gulv, tomme soppel eller blande rengjoringsmidler. Oppgavene er fysiske og har null relevans for en språkmodell.

### 3.4 Automasjon vs. augmentering

Hver matchet oppgaves Claude-samtaler klassifiseres i interaksjonsmonstre:

| Monster | Kategori | Beskrivelse |
|---------|----------|-------------|
| Directive | **Automasjon** | AI utforer direkte med minimalt menneskelig input |
| Feedback loop | **Augmentering** | Iterativ forbedring basert på tilbakemelding |
| Task iteration | **Augmentering** | Samarbeidende foredling av arbeid |
| Validation | **Augmentering** | Verifisering og kvalitetssjekk |
| Learning | **Augmentering** | Kunnskapstilegnelse |
| Filtered | (ekskludert) | Uklassifiserbar |

Programvareutviklingsoppgaver er overveiende augmentative (~73 %), mens dataregistrering og kontoroppgaver tenderer mot automasjon (~60-100 %).

---

## 4. Felten-mappingen

### 4.1 Felten AIOE: Konstruksjon

Felten et al. (2021) måler AI Occupational Exposure (AIOE) i tre steg:

1. **10 AI-applikasjoner** fra EFF AI Progress Measurement: abstrakte strategispill, sanntidsvideospill, bildegjenkjenning, visuell sporsmålsbesvaring, bildegenerering, leseforståelse, språkmodellering, oversettelse, talegjenkjenning, musikkgjenkjenning.

2. **Kobling til 52 O\*NET-evner** via crowdsourcing (Amazon Mechanical Turk): Hvor relevant er hver AI-applikasjon for hver menneskelig evne (f.eks. muntlig forståelse, induktiv resonnering)?

3. **Aggregering til yrkesnivå** via O\*NET-vekter:
```
AIOE_i = SUM_j(A_j * L_ij * I_ij) / SUM_j(L_ij * I_ij)
```
der A_j er evnenivå-AI-eksponering, L_ij og I_ij er O\*NET-nivå og -viktighet for evne j i yrke i.

Resultatet er standardisert (gjennomsnitt ≈ 0, standardavvik ≈ 1). Hoye verdier indikerer yrker som krever evner der AI har gjort mest fremskritt.

### 4.2 Varianter

Vi inkluderer tre Felten-baserte mål:

| Mål | Kilde | Beskrivelse | Koder |
|-----|-------|-------------|-------|
| `aioe` | Felten et al. (2021) | Samlet AIOE (alle 10 applikasjoner) | 390 |
| `aioe_lm` | Felten et al. (2023) | Språkmodellering-AIOE (GenAI-spesifikk) | 390 |
| `aioe_ig` | Felten et al. (2023) | Bildegenerering-AIOE (GenAI-spesifikk) | 390 |

[Felten AIOE-data](https://github.com/AIOE-Data/AIOE) bruker SOC 2010-koder (774 stk) og crosswalkes via SOC 2010 → ISCO-08 og deretter til overlappende STYRK-08-koder, som i Eloundou/Handa-kjeden.

### 4.3 Crosswalk

```
Felten AIOE (774 SOC 2010-koder)
       │
       ▼  BLS SOC 2010→ISCO-08 crosswalk
ISCO-08 4-siffer-koder
       │
       ▼  Kodefilter mot STYRK-08 (overlappende 4-sifferkoder)
STYRK-08 (390 koder, 95,8 % av STYRK-koder med data)
```

### 4.4 Validering

**Korrelasjon med andre mål (Spearman ρ):**

| Mål 1 | Mål 2 | ρ |
|-------|-------|---|
| Felten AIOE | Eloundou β | 0,889 |
| Felten AIOE-LM | Eloundou β | 0,867 |
| Felten AIOE | Handa overall | 0,623 |

Den hoye korrelasjonen mellom AIOE og Eloundou (ρ = 0,89) bekrefter at begge fanger lignende konstrukter (kognitive yrker med hoy AI-relevans), men med ulike metoder. Den lavere korrelasjonen med Handa (ρ = 0,62) gjenspeiler at faktisk bruk (Handa) skiller seg fra teoretisk kapabilitet (Felten/Eloundou).

### 4.5 Felten-spesifikke begrensninger

**Statisk mål:** Felten AIOE reflekterer AI-kapabilitet på ett tidspunkt (2021). Den fanger ikke den raske utviklingen i generativ AI etter 2022.

**Evne-basert, ikke oppgave-basert:** Felten kobler AI til 52 brede *evner* (abilities), ikke til spesifikke *oppgaver*. Dette gir bredere dekning men mindre presisjon enn Eloundou (som vurderer hver oppgave direkte) eller Handa (som matcher faktiske samtaler til oppgaver).

**Klonede verdier:** 35 av 401 STYRK-koder (8,7 %) deler identisk AIOE-score med minst en annen kode, typisk fra SOC rest-kategorier som mapper til flere STYRK-koder. Lavere enn Handa (26 %) fordi Felten har mindre variasjon mellom beslektede yrker.

**Manglende koder:** Kun 5 store yrker (>1000 ansatte) mangler: militære yrker (011x, 021x, 031x), religiose yrker (3413) og politikere (1111).

---

## 5. Kvalitetsflagg

Begge mapping-filer inneholder kvalitetsindikatorer for hver STYRK-08-kode:

### 4.1 Felles flagg (begge mål)

| Kolonne | Beskrivelse |
|---------|-------------|
| `n_soc_matched` | Antall SOC 2010-koder som bidrar til denne STYRK-koden |
| `has_partial_match` | 1 hvis minst en SOC→ISCO-kobling er markert delvis (`*`) i BLS-crosswalken |
| `max_partial_fanout` | Storste fan-out blant delvise bidragsytere (0 = alle fulle matcher) |
| `manual_map` | Kilde-STYRK-kode hvis manuelt mappet (f.eks. «2221» for sykepleiere) |

### 4.2 Handa-spesifikke flagg

| Kolonne | Beskrivelse |
|---------|-------------|
| `n_tasks_matched` | O\*NET-oppgaver med match i task_pct > 0 |
| `n_tasks_total` | Totalt antall O\*NET-oppgaver for bidragende SOC-koder |
| `task_coverage` | n_tasks_matched / n_tasks_total |

### 4.3 Fordeling av kvalitetsflagg

**Delvis match fan-out (hvor mange ISCO-koder en enkelt SOC-kode delvis mapper til):**

| Fan-out | Handa-koder | Eloundou-koder | Tolkning |
|---------|-------------|----------------|----------|
| 0 (full match) | 165 (47 %) | 168 (42 %) | Ren mapping |
| 2 | 63 (18 %) | 83 (21 %) | Liten tvetydighet |
| 3–5 | 51 (14 %) | 65 (16 %) | Moderat stoy |
| 6+ | 73 (21 %) | 81 (20 %) | Betydelig broadcasting |

**Handa oppgavedekning:**

| Dekning | Koder | Tolkning |
|---------|-------|----------|
| 0 % | 7 | Alle oppgaver er fysiske/manuelle — null Claude-bruk er genuint |
| 1–10 % | 82 | Hovedsakelig ikke-kognitive yrker med 1–2 marginale oppgavematcher |
| 10–50 % | 192 | Moderat dekning — scorene er informative men stoyete |
| 50 %+ | 71 | God dekning — pålitelige scorer |

---

## 6. Manuelle mappinger

To norskspesifikke STYRK-koder mappes manuelt til sin ISCO-forelder:

| STYRK | Yrke | Ansatte (okt 2022) | Kilde | Begrunnelse |
|-------|------|-----|--------|-------------|
| 2223 | Sykepleiere | 69 497 | 2221 (Nursing professionals) | Norsk underkode av ISCO 2221 |
| 2224 | Vernepleiere | 24 406 | 2221 (Nursing professionals) | Norsk underkode av ISCO 2221 |

Disse er flagget med `manual_map = 2221` i CSV-filene.

To overlappende 4-sifferkoder behandles ogsa manuelt fordi SSBs detaljerte
yrkestitler viser at den norske STYRK-koden ikke dekker samme yrke som
BLS/ISCO-koden med samme nummer:

| STYRK | Norsk innhold | Baseline-kilde | Begrunnelse |
|-------|---------------|----------------|-------------|
| 2267 | Ergoterapeuter | SOC `29-1122` Occupational Therapists | SSBs detaljerte titler for 2267 er ergoterapeuter, mens BLS/ISCO 2267 gjelder optometrists/ophthalmic opticians. |
| 2269 | Kiropraktorer mv. | SOC `29-1011` Chiropractors | SSBs detaljerte titler for 2269 er kiropraktorer og osteopater; vi bruker chiropractors som naermeste SOC-kilde i baseline. |

Disse radene erstatter den automatiske same-code-mappingen i Eloundou-,
Handa- og Felten-filene og flagges som `manual_map = SOC:29-1122` og
`manual_map = SOC:29-1011`. Anthropic job-exposure-filen bygges med samme
overstyring, men beholder sitt tre-kolonne output-format. Vi legger ikke inn
en egen optometrist-mapping i baseline; norske optikere/optometrister bor
klassifiseres separat i registeret.

To andre STYRK-koder i registerlisten finnes heller ikke som 4-sifferkoder i
BLS' SOC→ISCO-crosswalk:

| STYRK | Yrke | Behandling | Omfang |
|-------|------|------------|--------|
| 0000 | Uoppgitt / yrker som ikke kan identifiseres | Ingen eksponeringsscore; ekskluderes fra eksponeringskvintiler | 35 828 worker-months i analyseaggregatene for alder 21--60, 0,023 % av worker-months på tvers av de to analysesektorene; finnes bare jan.--mars 2021 |
| 3439 | Andre yrker innen estetiske fag | Foreløpig umappet | 112 319 worker-months i analyseaggregatene for alder 21--60, 0,073 % av worker-months |

For 3439 er den nærmeste internasjonale kandidaten ISCO `3435` "Other
artistic and cultural associate professionals". BLS-crosswalken gir
SOC-bidrag til 3435 (bl.a. artists/performers/media/entertainment
all-other-kategorier), så en mulig robusthetssjekk er å legge inn en
eksplisitt manuell mapping `3439 <- 3435` med eget flagg. Vi bruker den ikke
i baseline fordi 3439 er en liten norsk restkategori, og en slik mapping ville
arve nettopp den typen brede "all other"-SOC-kategorier som crosswalk-auditen
ellers advarer mot.

Andre store umappede yrker (5153 Vaktmestre, 9312 Hjelpearbeidere) mappes **ikke** manuelt. For Handa-målet er fraværet genuint: SOC 37-2011 (Janitors and Cleaners) mapper korrekt til ISCO 5153 i BLS-crosswalken, men alle 23 O\*NET-oppgaver for dette yrket har null Claude-bruk. Ingen spor Claude om å feie gulv eller tomme soppel.

---

## 7. Kjente skjevheter og begrensninger

### 6.1 Generaliststraff i Handa-målet

Yrker med **brede, generalistiske** oppgavebeskrivelser får systematisk lavere eksponeringsscorer enn spesialistyrker som utforer tilsvarende arbeid.

**Eksempel:** Et sporsmål som «hvordan fikser jeg en varmepumpe?» blir matchet til SOC 49-9021 (Heating, Air Conditioning, and Refrigeration Mechanics) i stedet for SOC 37-2011 (Janitors and Cleaners) — selv om vaktmestre rutinemessig utforer mindre VVS-reparasjoner. Matchingsalgoritmen tildeler hver samtale til det **mest spesifikke** yrket, noe som straffer generalister.

Dette betyr at yrker som vaktmestre, driftsteknikere og «All Other»-restkategorier systematisk underteller sin faktiske AI-relevans.

### 6.2 Spesifikke anomalier fra crosswalken

Noen enkelttilfeller illustrerer hvordan crosswalken kan gi misvisende resultater:

| STYRK | Yrke | Problem |
|-------|------|---------|
| 3139 | Prosessoperatører, ikke nevnt annet sted | Eloundou β = 0,804 kommer utelukkende fra SOC 51-4012 «CNC Machine Tool Programmers» — et helt annet yrke enn den brede restkategorien |
| 2211 | Allmennpraktiserende leger | Inkluderer SOC 29-1069 «Physicians and Surgeons, All Other» — en sekkekategori med 12 spesialisttyper (235 oppgaver, 42 med Claude-bruk) som blandes med allmennpraktikere |
| 2310 | Universitets- og hoyskolelektorer | 35 SOC-koder (alle «XXX Teachers, Postsecondary») gjennomsnittet — informatikklærere og kunstlærere får identisk AI-eksponering |
| 2267/2269 | Ergoterapeuter; kiropraktorer mv. | Same-code-treffene er overstyrt etter sammenligning av SSBs detaljerte yrkestitler med BLS-titler: 2267 henter SOC 29-1122 og 2269 henter SOC 29-1011. |

### 6.3 Broadcasting fra restkategorier

SOC-koder som ender på «9» eller «99» (f.eks. 11-9199 «Managers, All Other») er brede sekkekategorier som mapper til flere ISCO-koder. Eksponeringsscoren **kopieres identisk** til flere urelaterte norske yrker:

```
SOC 11-9199 "Managers, All Other" → STYRK 1213 (Strategiledere)
                                   → STYRK 1322 (Ledere i gruvedrift)
                                   → STYRK 1349 (Andre produksjonsledere)
                                   → STYRK 1439 (Andre daglige ledere)
```

Alle fire mottar identiske eksponeringsscorer til tross for at de representerer svært ulike yrker.

**Omfang:** 90 av 352 Handa-koder (26 %) deler sin eksakte eksponeringsverdi med minst en annen kode.

### 6.4 Ingen sysselsettingsvekting

Når flere SOC-koder mapper til en STYRK-kode, tar vi **uvektet gjennomsnitt** uavhengig av hvor mange arbeidere hver SOC-kode representerer. En SOC-kode med 500 000 arbeidere teller like mye som en med 500.

Sysselsettingsvektet gjennomsnitt (fra BLS OES) ville vært mer forsvarlig, men yrkesnivå BLS-data var ikke inkludert i Handa-releasene tilgjengelig for Brynjolfsson et al. (2025) og Kauhanen (2026).

### 6.5 task_pct-dekningen er konsentrert

Kun 18,3 % av O\*NET-oppgaver finnes i Handas task_pct-data. Disse er overveiende **kognitive, datamaskinbaserte** oppgaver. De resterende 81,7 % — fysiske, mellommenneskelige, utendors oppgaver — har null dekning. Dette er et trekk ved målet (det fanger *faktisk* AI-bruk), men betyr at automasjon/augmentering-forholdet beregnes fra et smalt og ikke-representativt utvalg av hvert yrkes arbeidsoppgaver.

### 6.6 Fordelingssporsmal ved delte oppgaver (Handa)

Når en O\*NET-oppgave tilhorer flere SOC-koder, deler vi `task_pct` likt mellom dem (`pct / n_soc`). Dette behandler AI-bruk som en fast kake som fordeles mellom yrker. Alternativt kunne hver SOC fått full `pct` (= «hvor mye AI-bruk er *relevant* for dette yrket»). I praksis er effekten liten fordi bare 1,4 % av oppgavene deles mellom SOC-koder, men prinsipielt er det et designvalg som bor nevnes.

### 6.7 Ubegrensede råverdier (Handa)

`overall_exposure` summerer prosentpoeng over oppgaver og varierer fra 0,002 til 7,5. Dette er **ikke** en andel eller sannsynlighet — verdien 7,5 betyr at 7,5 % av alle Claude-samtaler relaterer seg til oppgaver i dette yrket. Persentiltransformen (som vi bruker for kvintilinndelingen) redder oss for rangering, men råverdiene er ufortolkbare som nivå.

### 6.8 Eloundou-scorene er fra for ChatGPT

Eloundou et al. (2024) β-scorene reflekterer ekspertvurderinger av GPT-4s potensial utfort i 2023 — for utbredt adopsjon. De måler **teoretisk kapabilitet**, ikke faktisk bruk. Korrelasjonen med Handas **observerte bruk** er moderat (Spearman ρ ≈ 0,55 på STYRK-nivå), noe som gjenspeiler at kapabilitet og adopsjon er ulike konstrukter.

### 6.9 Delvise matcher i BLS-crosswalken

BLS' SOC 2010→ISCO-08-crosswalk markerer 38,8 % av radene med `*` som indikerer delvis match (en SOC-kode som splittes over flere ISCO-koder, eller omvendt). Vår kode behandler alle matcher likt. En strengere tilnærming ville ekskludere delvise matcher, men redusere dekningen til ~46 % av sysselsettingen.

Kolonnen `max_partial_fanout` muliggjor robusthetssjekker på ulike strenghetsnivåer.

---

## 8. Sammenligning med andre studier

### 7.1 Tidslinje for datatilgjengelighet

| Dato | Hendelse |
|------|----------|
| Feb 2025 | Anthropic publiserer oppgavenivå-data ([release_2025_02_10](https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/release_2025_02_10)) |
| Mar 2025 | Handa et al. [arXiv:2503.04761](https://arxiv.org/abs/2503.04761) + [release_2025_03_27](https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/release_2025_03_27) |
| Sep 2025 | [release_2025_09_15](https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/release_2025_09_15) — geografisk data, preprosesseringskode |
| **Nov 2025** | **Brynjolfsson et al. publisert** |
| **Jan 2026** | **Kauhanen & Rouvinen publisert** |
| Mar 2026 | [labor_market_impacts](https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/labor_market_impacts) — `job_exposure.csv` (yrkesnivå, SOC 2019) |

Basert på publiseringsdatoene hadde trolig verken Brynjolfsson eller Kauhanen tilgang til den forhåndsaggregerte `job_exposure.csv` (mars 2026). Begge siterer kun Handa et al.s arXiv-artikkel fra mars 2025. Vi kan imidlertid ikke utelukke at de hadde tilgang til upubliserte data direkte fra Anthropic — ingen av artiklene spesifiserer hvilken datafil eller release de brukte.

### 7.2 Sammenligning av tilnærminger

| | Vår mapping | Kauhanen (2026) | Brynjolfsson (2025) |
|---|---|---|---|
| Handa-datakilde | task_pct_v2.csv | task_pct (release uklar) | task_pct |
| Handa startkoder | 775 SOC 2010 | «749 O\*NET-SOC» | Ikke oppgitt |
| Handa crosswalk | SOC 2010 → ISCO-08 (1 steg) | «O\*NET 2019 → SOC 2018 → SOC 2010 → ISCO-08» (3 steg) | SOC 2010 direkte (ADP-data) |
| Handa sluttkoder | 352 STYRK-08 (86 %) | 296 ISCO-08 (79 %) | ~500 SOC (US-data) |
| Delvise matcher | Alle inkludert, flagget | Ikke beskrevet | N/A (US-data) |
| Kvalitetsflagg | Ja (fan-out, oppgavedekning) | Ikke beskrevet | Ikke beskrevet |

*Merk:* Tabellen over viser hva artiklene *beskriver*. Kauhanen og Brynjolfsson gir begrenset metodisk detalj om crosswalk-håndteringen, så kolonnene for deres tilnærminger inneholder usikkerhet. Kauhanens «749 O\*NET-SOC»-koder og 3-stegs crosswalk er direkte sitert fra artikkelen, men vi vet ikke hvordan de håndterte delvise matcher, aggregering, eller manglende koder.

### 7.3 Sammenligning med Kostol (2026)

Kostol ([andreaskostol.no/ai](https://andreaskostol.no/ai/)) publiserer AI-eksponeringsscorer for norske STYRK-08-yrker basert på Eloundou, Handa og Felten.

**Eloundou:** Korrelasjonen mellom Kostols `eloundou_norm` og våre `eloundou_beta`-verdier er **0,989** for 365 matchede koder — nesten identisk. De 30 STYRK-kodene Kostol mangler er de som krever SOC 2018→2010-broen (alle IT-yrker 251x/252x/351x og leger 2211/2212). Dette tyder på at Kostol mapper Eloundous SOC 2018-koder direkte mot BLS' SOC 2010→ISCO-crosswalk uten mellomsteg — men vi kan ikke verifisere dette uten tilgang til koden.

**Handa:** Storre avvik. Spearman ρ = 0,63. Mest talende eksempel: Dataregistrere (4132) har `anthropic_norm = 1,0` hos Kostol, men `overall_exposure = 0,01` i vår mapping. Dette tyder på at Kostol bruker et annet aggregeringsnivå enn vår task_pct-summering — muligens forhåndsaggregerte yrkesnivå-scorer fra `job_exposure.csv` eller lignende.

Kostol tar gjennomsnittet av tilgjengelige kilder per yrke. For 26 yrker (inkl. alle IT-yrker og leger) er kun Felten tilgjengelig — disse yrkene dominerer topp-rangeringene.

### 7.4 `job_exposure.csv`-målet er et annet mål

Anthropics mars 2026-release inneholder [`job_exposure.csv`](https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/labor_market_impacts) med forhåndsaggregerte `observed_exposure`-scorer per yrke. Dette er et **annet mål** enn vår task_pct-aggregering:

```
observed_exposure = Σ(w_t × r̃_t) / Σ(w_t)

der:
  w_t  = O*NET tidsfraksjon per oppgave (fra Tamkin & McCrory, 2025)
  r̃_t  = 1{ArbeidsbrukAntall ≥ 100} × 1{Eloundou β ≥ 0,5} × α_t
  α_t  = ½ + ½ × AutomasjonsAndel_t  (automasjon vektes tyngre)
```

Dette inkorporerer tidsvekter, minimumsterskler for bruk, Eloundou-gjennomforbarhetsporter og halv vekt for augmenterende bruk — ingen av disse finnes i de rå task_pct-dataene. Spearman rangkorrelasjon mellom vår task_pct-aggregering og `observed_exposure` er ρ ≈ 0,70 på STYRK-nivå.

Gitt at `job_exposure.csv` ble publisert etter begge artiklene, er det sannsynlig at vår task_pct-baserte tilnærming ligger nærmere det Brynjolfsson og Kauhanen faktisk brukte. Vi kan imidlertid ikke verifisere dette uten tilgang til deres kode.

---

## 9. Samlet vurdering

**Er mappingen vår for lite streng?** Det kan innvendes:

1. **97,5 % Eloundou-dekning** er betydelig hoyere enn sammenlignbare studier og vanskelig å forsvare uten eksplisitt diskusjon
2. **Alle delvise matcher beholdes** — en enkel forbedring ville være å filtrere eller nedvekte `part`-rader
3. **Uvektet gjennomsnitt** gir uforholdsmessig innflytelse til små nisje-SOC-koder

**Motargumenter:**

- Hoy dekning betyr færre droppede observasjoner i analysen
- Crosswalk-problemet er universelt for alle studier som bruker O\*NET-mål utenfor USA — ingen har en perfekt losning
- Persentiltransformen demper effekten av enkeltstående anomalier
- Vi bruker kvintiler, ikke kontinuerlige verdier, noe som gjor analysen mer robust mot mapping-stoy
- Kvalitetsflaggene muliggjor transparente robusthetssjekker

**Anbefaling:** Diskuter dette som en begrensning i paperet. Vis i robusthetssjekker at resultatene holder med strengere mappinger (f.eks. kun fulle matcher, minimum dekning). Sensitivitetsfigurene S1–S3 viser at hovedresultatene er stabile under restriksjonene.

---

## 10. Robusthetsspesifikasjoner

Kvalitetsflaggene muliggjor tre robusthetsterskler:

| Spesifikasjon | Filter | Eloundou | Handa | Sysselsetting |
|---------------|--------|----------|-------|---------------|
| **Hoved** | Alle koder | 397 koder | 352 koder | ~96–99 % |
| **Moderat** | Fan-out ≤ 5 | 316 koder | 279 koder | ~77–80 % |
| **Streng** | Fan-out ≤ 2 | 251 koder | 228 koder | ~69–70 % |

For Handa krever den moderate spesifikasjonen i tillegg `task_coverage ≥ 10 %`.

Kvintiler **tildeles på nytt innenfor hvert restrikerte utvalg** for å sikre balanserte grupper.

---

## 11. Output-filer

| Fil | Plassering | Innhold |
|-----|-----------|---------|
| `styrk08_eloundou_beta_mapping.csv` | [`data/ai_exposure/`](data/ai_exposure/) | 397 STYRK-koder med β, kvintil, kvalitetsflagg |
| `styrk08_handa_mapping.csv` | [`data/ai_exposure/`](data/ai_exposure/) | 352 STYRK-koder med eksponering, auto/augm, kvalitetsflagg |
| `build_eloundou_mapping.py` | [`analysis/03_mappings/`](../../../analysis/03_mappings/build_eloundou_mapping.py) | Eloundou-mappingbygger |
| `build_handa_mapping.py` | [`analysis/03_mappings/`](../../../analysis/03_mappings/build_handa_mapping.py) | Handa-mappingbygger |
| `styrk08_felten_mapping.csv` | [`data/ai_exposure/`](data/ai_exposure/) | STYRK-koder med AIOE, AIOE-LM, AIOE-IG, kvalitetsflagg |
| `build_felten_mapping.py` | [`analysis/03_mappings/`](../../../analysis/03_mappings/build_felten_mapping.py) | Felten-mappingbygger |
| `plot_felten.py` | [`analysis/06_figures/`](../../../analysis/06_figures/plot_felten.py) | Felten-figurer 8–9 |
| `plot_sensitivity.py` | [`analysis/06_figures/`](../../../analysis/06_figures/plot_sensitivity.py) | Sensitivitetsfigurer S1–S3 |

### 11.1 Handa CSV-kolonner

```
styrk08, overall_exposure, pctl_overall_exposure, q_overall_exposure,
automation_share, pctl_automation_share, q_automation_share,
augmentation_share, pctl_augmentation_share, q_augmentation_share,
n_soc_matched, n_tasks_matched, n_tasks_total, task_coverage,
has_partial_match, max_partial_fanout, manual_map
```

### 11.2 Eloundou CSV-kolonner

```
styrk08, eloundou_beta, pctl_rank, quintile,
n_soc_matched, has_partial_match, max_partial_fanout, manual_map
```

### 11.3 Felten CSV-kolonner

```
styrk08,
aioe, pctl_aioe, q_aioe,
aioe_lm, pctl_aioe_lm, q_aioe_lm,
aioe_ig, pctl_aioe_ig, q_aioe_ig,
n_soc_matched, has_partial_match, max_partial_fanout, manual_map
```
