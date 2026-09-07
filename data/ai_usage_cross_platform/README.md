# AI-bruk på tvers av leverandører — Norge og sammenligningsland

Liten database bygget 2026-09-06 som svar på: finnes det token- og brukertall for Norge og
land vi liker å sammenligne oss med, fra Anthropic, OpenAI og OpenRouter?

## Kort svar

**Bare Anthropic publiserer land-nivå tall som er brukbare til en tidsserie.** OpenAI og
OpenRouter har enten ingen Norge-spesifikke tall, eller bare enkeltstående presseomtaler uten
et nedlastbart datasett.

## 1. Anthropic Economic Index (brukt her)

Kilde: [huggingface.co/datasets/Anthropic/EconomicIndex](https://huggingface.co/datasets/Anthropic/EconomicIndex),
release `2026_06_26` ("Cadences"-rapporten). CC-BY-lisensiert, ekte mikrodata aggregert til
måned × land × kategori, ikke en pressemelding.

**Fil:** `anthropic_aei_country_usage_2026-04_2026-05.csv` — 10 land (Norge, Sverige, Danmark,
Finland, Island, Tyskland, UK, USA, Nederland, Sveits) × 2 måneder (april, mai 2026) × 10
metrikker fra kategorien `overall` (alle samtaler samlet, ingen yrkes-/oppgavebrudd).

Kolonner:
- `usage_pct` — landets andel av global Claude.ai-bruk (%)
- `usage_per_capita_index` — Anthropic Usage Index (AUI): bruksandel delt på andel av
  verdens arbeidsføre befolkning. 1.0 = proporsjonalt med befolkning.
- `use_case_work_pct` / `_personal_pct` / `_coursework_pct` — andel av samtaler klassifisert
  som hhv. arbeid, privat, skolearbeid
- `collaboration_bucket_automation_pct` / `_augmentation_pct` — automation vs. augmentation
  (se kiindeksen.no sin egen diskusjon av denne klassifiseringen i `om.html`/`en/about.html`)
- `ai_autonomy_mean` — grad av AI-autonomi, skala 1–5
- `ai_education_years_mean` / `human_education_years_mean` — estimert utdanningsnivå i
  hhv. Claudes svar og brukerens prompt, i år

**Viktig begrensning:** dette er `claude_ai`-kilden (chat + Cowork), IKKE 1P API eller Claude
Code. Anthropic publiserer 1P API-tall bare på globalt nivå, ikke per land — så vi ser ikke
Norges API-/agentbruk her.

**Norge i disse to månedene:** lav absolutt andel av global bruk (0,32–0,35%, som forventet
gitt befolkningen), men høy per capita (AUI 3,9–4,0 — på linje med Sveits og Island, godt
over Tyskland). Augmentation-andelen er høyere enn i sammenligningslandene (58,7% i mai, mot
50,4% i USA), og coursework-andelen er påfallende høy og stigende (21%→26% april→mai) —
trolig eksamensperiode-effekt, verdt å sjekke mot neste måneds data før man tolker det som
trend.

**Hvordan hente en oppdatert versjon:** nye HF-releaser dukker opp under
`release_<YYYY_MM_DD>/data/aei_claude_ai_<dato>.csv`. Filene er store (150–250 MB), last ned
med `curl -L`, filtrer i Python/pandas på `geo_level=="country"`, `category_name=="overall"`
og ønskede `geo_id` (ISO 3166-1 alpha-3) og `metric_id`. Full metrikkliste og skjema i
`data_documentation.md` i samme HF-mappe.

## 2. OpenRouter — "State of AI 2025" (100 trillion token study, des. 2025)

Kilde: [openrouter.ai/state-of-ai](https://openrouter.ai/state-of-ai). Ekte token-tall, men
**ingen egen Norge-rad** — landetabellen viser bare topp 10 (USA, Singapore, Tyskland, Kina,
Sør-Korea, Nederland, UK, Canada, Japan, India), Norge havner i "Others (60+ countries,
16,76%)" og er ikke brutt ut. Geografi er dessuten basert på **fakturaland**, ikke
brukslokasjon — mindre egnet for en Norge-sammenligning uansett. Ikke inkludert i CSV-en.

## 3. OpenAI — ingen brukbar land-nivå datakilde

OpenAI publiserer ikke et nedlastbart datasett med land- eller tokenoppdeling tilsvarende
Anthropics. Det som finnes om Norge er enkeltstående presseomtaler uten tallgrunnlag man kan
bygge en tidsserie av:
- ["Introducing Stargate Norway"](https://openai.com/index/introducing-stargate-norway/)
  (OpenAI, 2026): "antall ukentlige aktive ChatGPT-brukere har firedoblet seg det siste året"
  i Norge — ingen absolutt tall, ingen dato for datauttrekk.
- Tredjeparts trafikkestimater (Similarweb via adaptworldwide.com) anslår Norge til 56%
  generativ-KI-adopsjon blant enkeltpersoner (høyest i Europa), men dette er
  spørreundersøkelsesbasert adopsjon, ikke plattform-token/bruksdata, og ikke fra OpenAI selv.

**Konklusjon:** ingen OpenAI-kilde er sammenlignbar med Anthropics måned×land-datasett.
Databasen her er derfor bygget utelukkende på Anthropic Economic Index.

## Videre vedlikehold

- Anthropic har annonsert fremtidige releaser ("future release schedules to be announced")
  — sjekk HF-repoet for nye `release_<dato>/`-mapper etterhvert.
- Overvåkingsjobben `anthropic-economic-index-watch` (kjører daglig 09:00, opprettet
  2026-09-06) varsler når en ny Economic Index-rapport publiseres; den sjekker foreløpig
  ikke automatisk om HF-datasettet har fått en ny country-level release — vurder å utvide den
  eller lage en egen sjekk hvis dette skal holdes løpende oppdatert.
