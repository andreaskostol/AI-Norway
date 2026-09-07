# Arbeidsmarkedet: KI-indeksen pluss tre paneler

Status per 2026-09-07. Bygget på branch `arbeidsmarkedet-panels` etter Andreas'
beskjed samme morgen: KI-indeksen forblir flaggskipet, nettstedet får tittelen
Arbeidsmarkedet, og det får et utdanningspanel og et eget yrkespanel. I tillegg
et panel med notatene om tokens og brukere på tvers av leverandører.
Planleggingsnotatet som lå til grunn: `OCCUPATION-TAB-PLAN-kiindeksen.md`
(2026-09-06) i repo-roten.

**Ikke deployet.** Alt ligger på branchen. Deploy krever Andreas' OK:
`cd dashboard/site && flyctl deploy` etter merge til main. Siste live-image
før dette er `deployment-01M1PR22GBGNJ67KJAMB94CKWD` (v=20260904i).

## Hva som er bygget

| Del | Fil | Status |
|---|---|---|
| Tittel og navigasjon | `index.html`, `om.html`, `en/index.html`, `en/about.html`, `style.css` | Ferdig. `<title>` er «Arbeidsmarkedet — …», `.site-name` i toppfeltet, `.panel-nav` under. |
| Yrker | `yrker.html`, `en/occupations.html`, `panels.js`, `data/yrker.json` | Ferdig. Fire figurer: 30 største yrker (stablet, fem typer), chat mot API (scatter), yrkesvelger over tid, oppgavene i ett yrke. |
| Utdanning | `utdanning.html`, `en/education.html`, `data/utdanning.json` | Ferdig for seks institusjoner. Fire figurer og en tabell. |
| KI-bruk per land | `bruk.html`, `en/usage.html`, `data/bruk.json` | Ferdig. Tre figurer, Norge-tabell, notater om Anthropic, OpenAI, OpenRouter. |
| Data-pipeline | `analysis/03_mappings/extract_aei_release_slices.py`, `build_aei_collaboration_mapping.py`, `dashboard/site/prepare_panels.py` | Ferdig, kjørt. |
| nginx, sitemap, README | `nginx.conf`, `sitemap.xml`, `dashboard/site/README.md` | Oppdatert. |

Verifisert lokalt 2026-09-07 med `python3 -m http.server 8431` og headless
Chrome: alle åtte sider tegner figurene, ingen feilstatus, tekstene fylles
fra data på begge språk.

## Augmentering/automatisering: hva som er nytt

1. **Ingen ny Anthropic-rapport eller -datasett etter 26. juni 2026** («Cadences»).
   Juni-utgivelsen har kategoriene `soc_occupation` og `onet`, men krysser dem
   aldri med interaksjonstype. Overvåkingsjobben `anthropic-economic-index-watch`
   (Hermes, daglig 09:00) hadde ikke kjørt da dette ble sjekket.
2. **Tre utgivelser nyere enn Handa-utvalget har tabellen oppgave × interaksjonstype**,
   globalt, for Claude.ai og API hver for seg: august 2025 (release 2025-09-15),
   november 2025 (release 2026-01-15, i `data/intermediate/`) og februar 2026
   (release 2026-03-24). Disse var ikke i repoet. Nå ligger de små uttrekkene i
   `data/ai_exposure/handa/aei_releases/` (ca. 10 MB), og STYRK-08-tabellen i
   `data/ai_exposure/styrk08_aei_collaboration.csv` (300–320 yrker per utvalg)
   og `styrk08_aei_tasks.csv` (15 oppgaver per yrke).
3. **Definisjonsavvik.** Anthropic regner directive + feedback loop som
   automatisering. `build_handa_mapping.py`, `styrk08_handa_mapping.csv`,
   forsidens bruksgrupper og arbeidsnotatets tekst regner bare directive.
   Norges egne tall bekrefter Anthropics regel (feb. 2026: 27,0 + 13,5 ≈ 40,5 %
   av klassifiserte, mot 41,3 % «automation» i juni-landfilen for mai). Den nye
   tabellen har begge: `automation_share` (Anthropic) og `directive_share`.
   Forsiden er ikke endret. Andreas må avgjøre om bruksgruppene skal bygges om.
4. **Rangeringen er ustabil.** Spearman mellom Handa-rangeringen og de nye
   Claude.ai-utvalgene er 0,2–0,3 for alle yrker, 0,5–0,6 for yrker med minst
   tusen samtaler. Utvalg mot utvalg (aug. 2025 → feb. 2026): 0,6–0,75. API-et
   ligger på 87–90 % directive for nesten alle yrker. Kjeden er verifisert:
   bruksandelen korrelerer 0,81–0,85 med Handa-målets `overall_exposure`.
5. Metodeteksten på `om.html` og `en/about.html` er skrevet om (den sa at ingen
   oppdatering på yrkesnivå fantes).

## Velg et yrke (lagt til samme dag, etter Andreas' beskjed)

Yrkessiden fikk en ny toppseksjon `#velg`: søk eller «Trekk et tilfeldig yrke»
→ skårkort (Eloundou-β og kvintil, Mouchel og kvintil, andel av Claude-bruk,
automatisering chat og API, klassifiserte samtaler) → de tre nærmeste yrkene i
arbeidsinnhold → knappen «Sammenlign arbeidsmarkedet» med sysselsetting og
lønn (seriene fra `occupations.json`, indeks 100 feb. 2025) og ledige
stillinger fra NAV. Figur 3 og 4 følger valget. `?yrke=2512&sammenlign=1`
åpner alt direkte.

- **Nærhet:** `analysis/03_mappings/build_occupation_task_similarity.py` →
  `data/ai_exposure/styrk08_task_neighbours.csv`. Rene O*NET-oppgavetekster
  ga nesten ingen overlapp (de er skrevet per SOC-yrke), så likheten er cosinus
  mellom z-skårede profiler over 41 arbeidsaktiviteter + 35 ferdigheter
  (O*NET IM), gjennom samme SOC→ISCO→STYRK-kjede som Eloundou. 392 yrker.
  Eksempel: 2512 → 2519, 2529, 2521; 4110 → 4225, 3313, 4311; 7411 → 7119,
  7127, 9622. Yrker med samme SOC-sett (2221/2223/2224) får likhet 1.
- **NAV-stillinger, datakontrakt:** `data/nav_vacancies/README.md`. Innsamler
  `dashboard/collect_nav_vacancies.py` (åpen søke-API, fylke for fylke pga.
  10 000-taket, dedup på uuid, STYRK-navn → kode). Mac Mini-agenten kan kjøre
  skriptet eller levere `snapshots/nav_ads_YYYY-MM-DD.csv` i samme format;
  `prepare_panels.py build_vacancies()` lager `vacancies.json` når serien
  finnes, ellers viser panelet en «under innsamling»-note. **Ingen eksisterende
  innsamling ble funnet** i Dropbox/Deling/Hermes, så serien starter her. NAV
  svarer 429 ved rask polling og blokkerte denne adressen i over ti minutter
  etter første kjøring (0,3 s mellom forespørsler). Skriptet går nå med 3 s
  som standard. **Første øyeblikksbilde er ikke levert ennå**; kjør
  `python dashboard/collect_nav_vacancies.py` når blokken er borte, deretter
  `prepare_panels.py`.
- Avvik fra ordlyden i bestillingen: «pick the three closest occupations in
  terms of ONET tasks» er løst med O*NET-profiler, ikke oppgavetekster, av
  grunnen over.

## Åpne beslutninger for Andreas

- **Mac Mini-agenten** må settes opp til å kjøre
  `python dashboard/collect_nav_vacancies.py` ukentlig (eller levere filer i
  kontrakten). Andreas må gi den beskjeden; ingenting her sender noe.

- **Deploy?** Se over branchen, så `flyctl deploy`. Ta backup av `public/` først
  (`dashboard/backups/`), som ved tidligere runder.
- **Bruksgruppene på forsiden**: beholde directive-only fra Handa-utvalget, eller
  bytte til Anthropics inndeling og nyeste utvalg? Bytte flytter figur 10–12 og
  punkt 4 i hurtigoppsummeringen. Arbeidsnotatet beskriver directive-only.
- **Utdanning: utvide fra 6 til alle DBH-institusjoner** (Spor A i planen).
  Mekanisk: `data/dbh/fetch_dbh.py` i Edutech-mappa, kjør 01→05, kopier
  `institutions_*.csv` til `data/education_analysis/`, kjør `prepare_panels.py`.
- **«Hvilke andre yrker»** (Spor B del 3): ikke bygget, som planen anbefalte.
  To metoder å velge mellom: oppgaveoverlapp (kosinuslikhet på O*NET-oppgaver via
  SOC) eller likhet i interaksjonsprofil. Data finnes lokalt for begge.
- **Engelsk navn**: `Arbeidsmarkedet` står som merkenavn også på /en/. Alternativ:
  «The Labour Market».
- **Fargene i panelnavigasjonen**: «ny»-merket på de tre panelene bør fjernes
  etter en måned.

## Rutine ved ny Anthropic-utgivelse

```
curl -L -o /tmp/x.csv https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/<release>/data/<fil>
python analysis/03_mappings/extract_aei_release_slices.py /tmp/x.csv ...
python analysis/03_mappings/build_aei_collaboration_mapping.py
python dashboard/site/prepare_panels.py
```

Legg det nye tidspunktet inn i `VINTAGES` i `prepare_panels.py`. Landfilene
(månedlige) legges i `data/ai_usage_cross_platform/` og leses av `build_bruk()`.
Bump `v=` på `panels.js` og `style.css` i HTML-filene ved endring.
