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

## Runde 2 (2026-09-07, etter Andreas' tilbakemelding «not good enough»)

- **KI-bruk per land er fjernet** fra nettstedet (sider, nav, sitemap, nginx,
  JSON). Notatene og dataene ligger fortsatt i `data/ai_usage_cross_platform/`
  og `aei_releases/`.
- **Yrker:** «Velg yrker selv»-grensesnittet (søk, inntil seks chips, nedlasting)
  ligger øverst, som figur 9 på forsiden. Første chip er hovedyrket. Figuren
  viser sysselsetting eller lønn fra februar 2023 (to år før Claude Code).
  Deretter skårkort, femtype-stolper per utvalg for hovedyrket, de tre nærmeste
  yrkene med «felles» O*NET-aktiviteter, oppgaver, over tid, 30 største, chat mot
  API. Metodeteksten forklarer automatisering/augmentering i dybden og
  O*NET-likheten (profiler, ikke oppgavetekster; z-skår; cosinus; kryssgang).
- **Utdanning:** utvidet til alle læresteder med ≥ 50 kandidater i 2025 (35).
  Pipeline i repoet: `analysis/07_education/fetch_dbh.py` (DBH-API, alle
  institusjoner) → `build_institutions.py` (trenger utdanning.no-koblingsfilene i
  Edutech-mappa, `EDUTECH_DIR`) → `data/education_analysis/` →
  `prepare_panels.py`. Siden har fagfelt × nivå-velger (nasjonalt, med
  toppyrker og «hvem utdanner flest»), institusjonsvelger (kort, fagfelt × nivå-
  tabell, toppyrker), oversikt over alle 35 og metode i tre trinn
  (utdanningskode, fagfelt/nivå, institusjon).
- Ledige stillinger: venter, som Andreas ba om. Innsamleren ble startet på nytt
  da NAV-blokken slapp; leveres når/hvis den fullfører.

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

## Runde 3 (2026-09-07, Andreas: «more user friendly», «looks very
## dashboard standard, AI generated», «drop the title Arbeidsmarkedet»)

- **Navnet Arbeidsmarkedet er borte.** Nettstedet heter KI-indeksen igjen.
  Titler, toppfelt, tagline, meta, footere, README, nginx-kommentar og
  docstrings er tilbake til KI-indeksen. Lenkeraden under toppfeltet er
  hvit og stille: KI-indeksen · Yrker · Utdanning · Om. «Ny»-merkene er
  fjernet; sidene er faste deler av nettstedet.
- **Om-siden** er én setning om indeksen, en lenkelinje (metode og
  sitering på forsiden, artikkelen, kontakt) og de to som lager den, med
  bilde og kort beskrivelse. Metodeteksten som lå der finnes på forsiden
  (`#metode`). Biografiene er skrevet av Claude og må sjekkes av Andreas.
- **Yrker** er bygget rundt ett spørsmål: hvor utsatt er jobben din?
  Søkefeltet er starten. Sammendraget for hovedyrket er tre avsnitt skrevet
  fra dataene (størrelse og eksponering; hvordan Claude brukes; endring i
  sysselsetting og lønn siden Claude Code, regnet fra `occupations.json`),
  ikke sju nøkkeltallsfliser. Overskriftene navngir yrket. Yrker som ligner
  er en liste, ikke kort. O*NET-aktivitetene har norske navn (`ONET_NO` i
  panels.js). Sju seksjoner er blitt seks, uten nummer. Nedlasting er en
  liste. Metodedetaljene er lukket som standard.
- **Utdanning** er bygget rundt to spørsmål: hvilke jobber fører
  utdanningen til, og hvordan skiller lærestedene seg? Fagfelt, nivå og
  eksponeringsmål er nedtrekksmenyer som i kontrollinja på forsiden, ikke
  knapperader. Sammendragene for fagfelt × nivå og for lærestedet er tekst.
  Fagfelt × nivå-tabellen viser tre typiske yrker, hele lista i title.
- **Datafeil rettet:** «de tre nærmeste» viste to yrker for 45 yrker fordi
  naboer uten Claude-data manglet i `yrker.json`. `prepare_panels.py`
  skriver nå `extra` (navn, størrelse, kvintil) for slike naboer.
- Cache `v=20260907d`. Fortsatt ikke deployet, merget eller pushet.

## Runde 4 (2026-09-07 ~13:00, Andreas: «yrker must have figures smoothed»,
## «too much text, make more text expandable», «histogram of most recent,
## then click on change in use relative to a date the user can choose»)

- **Glatting.** Sysselsettings- og lønnsfiguren på Yrker glattes nå som på
  forsiden: etterslepende glidende snitt (`movingAverage`, standard 6 mnd,
  velger over figuren med Ingen/3/6), deretter skalert så feb. 2025 er 100
  (`indexSeries`). Endringen i sammendraget regnes fra samme glattede serie
  (`changeSince`). Nedlastingen av valgte yrker er fortsatt uglattet.
- **Mindre tekst.** Hvert sammendrag er nå tre korte setninger (`.pick-lead`,
  ordlagt fra kvintil, automatiseringsandel og sysselsettingsendring) med
  tallene bak «Tallene bak» (`details.more`). Alle figurintroer er én
  setning; forklaringene ligger bak «Mer om figuren» / «Hva de fem typene
  betyr» / «Slik måles likhet». Fotnoter forkortet. Samme på Utdanning
  (fagfelt × nivå og lærested har lead + «Tallene bak»; «Om tallene»,
  «Om eksponeringsmålet», «Mer om inndelingen» er lukkede details).
- **Slik brukes Claude:** de sju stablede radene er byttet ut med et
  søylediagram over de fem typene for siste utvalg (`renderTypes`), med
  plattformvalg og nedtrekksmenyen «Vis»: «Bare siste utvalg» eller
  «Endring siden …» for hvert tidligere utvalg på plattformen
  (`fillCompareSelect`, `state.typesCompare`). I endringsmodus viser
  søylene prosentpoeng med nullinje, og noten gir automatisering før → nå.

## Runde 5 (2026-09-07 ~14:00, Andreas: Utdanning bygget om rundt
## studievalget; lærestedene ut; bestilling på Om)

- **Utdanning = studievalget.** Velg nivå (bachelor som standard) og fag på
  tresifret NUS-nivå (faggruppe, 56 per nivå, 215 grupper med ≥ 100
  sysselsatte). For valget: én setning med tallene bak, de ti vanligste
  oppgavene i jobbene utdanningen fører til (O*NET 30.1, viktighet × andel
  som gjør oppgaven, normalisert innen yrket, vektet med yrkesandel, maks tre
  per yrke), hver med Eloundou-etikett (E1 = stor, E2 = delvis, E0 = ingen)
  og automatiseringsandel fra Anthropic (siste utvalg, chat), klikk på en
  oppgave → fem typer for chat og API, og til slutt de vanligste jobbene
  (alle / nyutdannede). Tittelen står på én linje (`.hero-title-wide`).
- **Ny pipeline:** `analysis/07_education/build_majors.py` →
  `data/education_analysis/majors.json` (+ tre CSV-er) →
  `prepare_panels.build_utdanning()` (ren gjennomkopiering) →
  `public/data/utdanning.json` (1,4 MB). Nye inndata i repoet:
  `data/ai_exposure/onet_relational/Task Statements.txt` og
  `Task Ratings IM RT.txt` (O*NET 30.1, lastet ned 2026-09-07; bare IM- og
  RT-radene), `data/education_analysis/inputs/nus2000_klass.csv`.
  Registerkoblingen leses fortsatt fra Edutech-mappa (`EDUTECH_DIR`).
- **Lærestedene er tatt ut** av siden, nedlastingene og JSON-en.
  `build_institutions.py` og CSV-ene ligger urørt i `data/education_analysis/`;
  `prepare_panels.build_institutions_json()` er beholdt for en egen analyse
  senere.
- **Om:** skjema «Bestill en tilrettelagt rapport eller presentasjon» (navn,
  virksomhet, e-post, format, ønsket fokus, målgruppe, tidspunkt, sted,
  varighet, annet). Knappen bygger en `mailto:` til andreas.r.kostol@bi.no
  med feltene i teksten; ingenting sendes fra nettstedet. Begge språk.
- **Sjekk mot TMT-dekket:** BI-andelen i topp kvintil er 50 → 68 % både i
  dekket og i (den forrige) lærestedsvisningen; avviket Andreas så var
  landstallet 48 % øverst på siden.

## Runde 6 (2026-09-07 ~14:30): fagsøk og «Automatisering over tid»

- **Fag-menyen er et søkefelt** (`#u-search`, `.control-search`): klikk gir
  lista over faggrupper på valgt nivå, skriving søker i faggruppene og i
  navnene på 2 423 enkeltutdanninger fra registeret (`names` i majors.json:
  NUS6, navn, kortnavn, engelsk navn fra `inputs/nus_codes_utdanning_no.csv`,
  antall). Stoppord og synonymer i panels.js (`STOP`, `SYN`: jurist →
  rettsvitenskap, lege → medisin, sykepleier → sykepleie …). Treff setter
  både nivå og gruppe, så «master i rettsvitenskap» går rett til 737.
  Testet med `tmp/test_search.js` mot datafilen.
- **«Automatisering over tid»** på Yrker har fått en grå stiplet referanse
  (alle yrker, sysselsettingsvektet) og en note om at første punkt er Handa
  (flere uker), de neste én uke hver. Samlet chat-automatisering: 35 %
  (Handa, des. 2024–jan. 2025) → 56 % (aug. 2025) → 46 % (nov. 2025) → 45 %
  (feb. 2026), sysselsettingsvektet over STYRK; globalt fra råfilene
  52 → 47 → 46 %. API: 87 → 85 → 81 %, med «not classified» opp fra 12 til
  18 %. Fallet etter aug. 2025 er altså reelt i Anthropics tall, men lite
  mot hoppet fra Handa til aug. 2025, og for enkeltyrker dominerer
  utvalgsstøy (Spearman 0,6–0,75 mellom utvalg).

### Seleksjon i oppgavene (Andreas' innvending, testet 2026-09-07)

Andreas: når automatisering gjør at oppgaver faller bort fra chatten, vil
automatiseringsandelen falle av seg selv. Test (`tmp/selection_test.py`,
oppgavenivå, aug. 2025 → feb. 2026, oppgaver med ≥ 30 samtaler i begge):

- **Chat:** de mest automatiserte oppgavene (øverste kvartil, 66 %
  automatisering i aug.) mistet 18 % av sin andel av all chat-bruk innen
  feb.; nederste kvartil vant. Vektet korrelasjon mellom automatisering i
  aug. og endring i bruksandel: −0,18. Av fallet i bruksvektet
  automatisering over felles oppgaver (51,7 → 45,9 %) er om lag halvparten
  sammensetning (−3,7 pp) og halvparten endring innen oppgavene (−3,6 pp).
- **API:** ingen sammensetningseffekt (+0,1 pp); hele fallet (−5,6 pp) er
  innen oppgavene, og «not classified» steg fra 12 til 18 %.
- Dataene skiller ikke mellom oppgaver som flyttes til API/agenter og
  oppgaver som slutter å bli gjort: Anthropic publiserer ikke volum per
  plattform, bare faste utvalg.

Konsekvens for nettstedet: automatiseringsandelen er betinget på at
oppgaven fortsatt brukes i kanalen, og undervurderer automatisering der
den lykkes. Metodeteksten bør si dette. En bedre indikator på siden er
yrkets andel av all chat-bruk over tid (`u` per utvalg finnes allerede i
yrker.json) ved siden av automatiseringsandelen. Bygget i runde 7 (`#tid`).

## Runde 7 (2026-09-07 ~14:55): norske oppgavetekster, oppgavehistorikk og
## «Claude-bruk over tid»

- **Norske oppgavetekster.** `data/ai_exposure/onet_task_translations_no.csv`
  (task, task_no, source). Første batch: 386 rader, alle oppgavene på
  Utdanning-siden og 86 av Yrker-sidens, oversatt i sesjonen.
  `analysis/07_education/translate_tasks.py` oversetter resten via API
  (`ANTHROPIC_API_KEY`, `--dry-run` teller). `prepare_panels.py` skriver
  `t_no` per oppgave i `yrker.json`, `build_majors.py` skriver `text_no`
  i `majors.json`. Siden viser norsk der det finnes, ellers engelsk.
- **Oppgavehistorikk.** `prepare_panels.build_yrker()` legger `v` på hver
  oppgave: femtypeandeler, n og bruksandel for hvert utvalg (råuttrekkene
  i `aei_releases/` pluss Handa), så «Slik brukes Claude på oppgaven» kan
  vise endring siden et tidligere utvalg (`task-compare`, `renderTaskChart`).
- **«Claude-bruk over tid»** (`#tid`): knapper for yrkets andel av all
  Claude-bruk (`u`) eller automatiseringsandel, per plattform. Noten sier
  at når begge faller, forlater de automatiserte oppgavene kanalen
  (seleksjonspoenget over).

## Runde 8 (2026-09-07 ~17:00, Andreas: «show top 5 tasks, simplify the
## exposition of how claude is used (just call it automation, and refer to
## the histogram below)… Make histogram of the tasks»)

- **Alle 2 341 oppgavetekster har norsk tekst.** 1 955 nye oversettelser
  laget av ti parallelle Claude-agenter i sesjonen (ingen API-nøkkel var
  satt), samme stil som første batch, kilde «manual 2026-09-07».
  QA: 0 manglende, 0 med engelske restord, alle med stor forbokstav og
  punktum. `yrker.json`: 4 252 oppgaverader, 0 uten `t_no`.
- **«Slik brukes Claude på oppgavene»** er bygget om. Tabellen med 15
  oppgaver og fem farger er byttet ut med et liggende søylediagram over
  de fem oppgavene med mest bruk (`renderTasks`, `#chart-tasks`): stolpe =
  andel av all Claude-bruk på plattformen, mørk del = automatisering, lys
  = augmentering, etikett «17 % automatisering». Klikk på stolpe eller
  oppgavetekst velger oppgaven for femtype-figuren under. Introen er tre
  setninger og peker til figurene under; «Hva de fem typene betyr» ligger
  nå ved figuren for hele yrket. JSON-en har fortsatt 15 oppgaver per
  yrke og plattform (nedlastingen er uendret).
- **Engelsk side:** O*NET-tekstene vises med stor forbokstav (`cap`), og
  oppgaveoverskriften holder seg engelsk (viste norsk ved en feil).
- **Smale skjermer:** radhøyde etter lengste etikett, fast aksesteg
  (`step`, to merker under 700 px), kort etikett («17 %»), legende til
  høyre. Femtype-figurenes kategorietiketter dimensjoneres etter
  figurbredden (`typeLabelWidth`) i alle tre figurene, også på Utdanning.
- Cache `v=20260907e`. Verifisert headless (1200 og 420 px) på begge
  språk. Ikke committet, merget eller deployet. Runde 3–8 ligger
  ucommittet på branchen `arbeidsmarkedet-panels`.
- Merk: ved 420 px kutter headless-skjermbildet teksten i høyre kant, og
  det gjør også skjermbildet fra kl. 11:51. Sjekk på ekte mobil om siden
  har horisontal overflow (kandidat: `white-space: nowrap` i
  seksjonsnavigasjonen, `style.css` linje 108).

## Runde 9 (2026-09-07 ~17:50, Andreas: «la bruker utvide fra topp 5 til
## topp 10 oppgaver. La også bruker endre fra nivå til endring i omfang av
## oppgaver»)

- **Topp 5 / Topp 10** (`tasks-count-buttons`, `state.taskCount`). JSON-en
  har 15 per yrke og plattform, så ingen ny databygging.
- **«Vis»-menyen** (`tasks-compare`, `state.tasksCompare`,
  `fillTasksCompare`): «Nivå, siste utvalg» eller «Endring siden …» for
  hvert tidligere utvalg på plattformen der minst én av oppgavene har
  data, inkludert Handa for chat. Endring = prosent endring i oppgavens
  andel av all Claude-bruk på plattformen (`v[key][6]`, samme skala i alle
  utvalg: summen over alle oppgaver er ca. 80 % i hvert), rekkefølgen er
  fortsatt etter nivå i siste utvalg. Én stolpe per oppgave, nullinje,
  etikett til høyre («+52 %», for negative rett til høyre for nullinja).
  Oppgaver uten data i det valgte utvalget får ingen stolpe, og noten
  teller dem. Tooltip viser andel før → nå, endring og automatisering nå.
- **Dyplenker:** `?oppgaver=10` og `?endring=claude_ai|2025-08-04` (også
  brukt til headless-testing, siden nettleserautomatisering ikke finnes
  lokalt). Eksempel: `yrker.html?yrke=2411&oppgaver=10&endring=claude_ai%7C2025-08-04`.
- Intro oppdatert (fire setninger), begge språk. Verifisert headless på
  desktop og 420 px: nivå 5/10, endring siden aug. 2025 og siden Handa,
  engelsk. Fortsatt ikke committet.
- Tolkning: for 2411 (revisorer) vokser de fleste av de ti største
  oppgavene 50–170 % i andel siden aug. 2025 i chat; siden Handa er
  bildet blandet (−66 % til +251 %). Rangeringen er ustabil mellom
  utvalg (Spearman 0,6–0,75), så enkeltoppgaver bør leses med det i
  mente; noten sier ikke dette ennå.

## Runde 10 (2026-09-07 ~18:00, Andreas: «ikke la folk laste ned data for
## yrke og utdanning»)

- **Nedlastingene er borte** på Yrker og Utdanning, begge språk:
  `#data`-seksjonene, lenkene til dem i seksjonsnavigasjonen, CSV-knappen
  for valgte yrker (`download()` i panels.js) og setningen om
  «nedlastingsfilen» i metodeteksten. Kildelenkene (Anthropic, O*NET,
  utdanning.no, Eloundou) står igjen som én linje nederst i metodeseksjonen.
- `prepare_panels.py` kopierer ikke lenger CSV-er til `public/data/panels/`.
  nginx svarer 404 på `/data/panels/`. README oppdatert.
- **Ikke slettet:** de sju filene som lå i `public/data/panels/` (fire
  sporet i git, tre nye). `rm` er sperret i `.claude/settings.json`, så
  slett dem selv: `rm -r dashboard/site/public/data/panels`. Forsidens
  nedlastinger (`#data` på index.html, `prepare_data.py`) er uendret.

## Runde 11 (2026-09-07 ~18:15, Andreas: «flytte KI-indeksen Yrker
## Utdanning Om til øverst, til høyre for logo, men stilt mot høyre endepunkt»)

- Lenkeraden under toppfeltet er borte. Sidelenkene ligger nå i
  toppfeltets høyrekolonne (`.brand`), øverst, på samme rad som
  språkveksleren (`.brand-top`), høyrestilt; taglinen nederst som før.
  Alle åtte sider. På smale skjermer (< 980 px) kommer kolonnen rett under
  logoen, før seksjonslenkene (`order` i CSS).
- Cache `v=20260907f`.

## Runde 12 (2026-09-07 ~19:10, Andreas: «legge til betydningen av hver
## oppgave for yrket i forhold til standarder», «hva betyr andel av all
## claude bruk? Er det per yrke?»)

- **Betydning per oppgave fra O*NET 30.1** (samme filer og vekt som
  `build_majors.py`): `prepare_panels.py` legger `im` (Importance 1–5),
  `rt` (andel av utøverne oppgaven gjelder for), `rk`/`nt` (rang blant
  yrkets vurderte oppgaver etter IM × RT) på hver oppgave i `yrker.json`.
  Kobling: AEI-oppgavens SOC 2010-kode (11-1011) mot O*NET 11-1011.00,
  så spesialiteter, så omskrevet tekst i samme yrke (difflib ≥ 0,9), så
  samme tekst under et annet yrke (snitt, uten rang). Dekning: 2 665
  eksakt + 263 uklar + 768 bare tekst av 4 252 rader; 556 uten treff, av
  dem 111 i yrker O*NET ikke vurderer (f.eks. politikere).
- **På siden:** grå linje under hver stolpe, «Betydning for yrket 4,2 av
  5 · nr. 7 av 12 oppgaver» (`impLine`, `graphic`-tekster plassert fra
  gridgeometrien; rik tekst i akseetiketten ga ECharts-feil og brutte
  etiketter). Tooltip har også RT. Intro har fått én setning.
- **«Andel av all Claude-bruk»** er oppgavens andel av *alle* samtaler i
  Anthropics utvalg på plattformen, alle yrker og land, delt likt mellom
  O*NET-yrkene som deler oppgaven (Handa-regelen, `pct / n` i
  `build_aei_collaboration_mapping.py`). Ikke andel av yrkets bruk.
  Aksenavn, tooltip og fotnote sier nå dette. Yrkets `usage_pct` i
  «Claude-bruk over tid» er summen av yrkets oppgaveandeler.
  Endringsmodusens tooltip viser nå de delte nivåene (`k = pct / u`).
- Mulig neste steg (ikke gjort): stolpe = andel av *yrkets* Claude-bruk
  (`pct / usage_pct`), som gir lesbare tall (17 % i stedet for 0,13 %).
- Ny hjelper for feilsøking: `tmp/console.sh <url>` skriver ut
  konsollfeil fra headless Chrome.

## Runde 13 (2026-09-07 ~19:30, Andreas: «Topp 10 virker ikke», «kun to
## farger», «30 største: kun automatisering og augmentering», «utdanning:
## tydeligere at en oppgave hører til flere yrker»)

- **Topp 10:** ikke reprodusert. Klikktest via DevTools-protokollen
  (`tmp/cdp_click.mjs`, Node 26 med innebygd WebSocket) viser at knappen
  virker: noten skifter til «de ti oppgavene», figuren vokser 526 → 956 px,
  ingen feil. Trolig testet i minuttene 19:04–19:06 da figuren var blank
  (rik-tekst-feilen i runde 12). Cache bumpet til `v=20260907g`.
- **To farger overalt:** `AUTO_COLOR` (#401415) for direkte delegering og
  tilbakemeldingssløyfe, `AUG_COLOR` (#d3cec2) for de tre andre, i
  `TYPE_COLORS`, så «Slik brukes Claude på oppgaven» og «Alle oppgavene i
  yrket samlet» er tofargede. Histogrammet bruker de samme konstantene.
- **De 30 største yrkene:** `stackedTypeOption` stabler nå bare
  automatisering og augmentering; de fem typene ligger i tooltipen. Intro
  oppdatert på begge språk.
- **Utdanning, yrker per oppgave:** `build_majors.py` skriver `occs`
  (inntil seks yrker i gruppen som har oppgaven, med andel av oppgavens
  vekt) og `n_occ` per oppgave; kjørt mot Edutech-mappa (standardstien
  finnes). Tabellkolonnen heter «Yrker», viser inntil tre navn pluss «+N»,
  hele lista med andeler i `title` (hover). Intro og fotnote sier at en
  oppgave ofte hører til flere yrker. Snitt 1,7 yrker per oppgave.
  `utdanning.json` 2,6 MB. `td.num` brekker ikke lenger.
- Verifisert headless: ingen konsollfeil på Yrker og Utdanning, figurer og
  tabell tegnet. Fortsatt ikke committet.
- «Claude-bruk over tid»: aksetittelen «Andel av all Claude-bruk (%)» lå i
  kanten av tegneflaten rett under knappene og ble kuttet (Andreas ~19:35).
  Grid top 24 → 40 px, `nameGap` 16. Verifisert desktop og 500 px.

## Runde 14 (2026-09-07 ~19:40, Andreas: «for mye informasjon med API. Bruk
## API kun i Chat mot API. I utdanning, bruk kun Chat, og oppdater fargebruk»)

- **Yrker:** plattformknappene er fjernet fra oppgavehistogrammet,
  «Slik brukes Claude på oppgaven», «Alle oppgavene i yrket samlet»,
  «Claude-bruk over tid» og «De 30 største yrkene». Alle viser Claude.ai;
  `state.*Platform` står på `claude_ai`, og `makeButtons` hopper over
  manglende elementer. API-et finnes bare i «Chat mot API», der introen
  nå forklarer hva API-et er. Forklaringen i «Hva de fem typene betyr»
  sier at tallene gjelder chat. Tekster med «på plattformen» er skrevet
  om til «Claude.ai». Metodeteksten nevner fortsatt API-utvalgene og at
  API-et varierer lite (bakgrunn for «Chat mot API»).
- **Utdanning:** «Slik brukes Claude på oppgaven» viser bare Claude.ai,
  som én serie med de fem typene i `TYPE_COLORS` (automatisering mørk,
  augmentering lys), samme som Yrker. `PLAT_COLOR` fjernet. Noten og
  metodesetningen sier chat. Dataene (`t.api`) ligger fortsatt i
  `utdanning.json`.
- Cache `v=20260907h`. Ingen konsollfeil på de fire sidene. Fortsatt
  ikke committet.

## Slik bør forsidens augmentering/automatisering oppdateres

Bruksgruppene (figur 10–12 og punkt 4 i hurtigoppsummeringen) bygger på
`data/ai_exposure/styrk08_usage_groups.csv`: kvintiler av
`augmentation_share` og `automation_share` fra Handa-utvalget
(des. 2024–jan. 2025), der bare *directive* regnes som automatisering.
Gruppene tildeles yrkene lokalt i `dashboard/build_release.py` (pakkene
`usage_patterns_by_age` og hires-/wages-variantene), på toppen av
yrke × alder-uttrekket fra microdata.no. **Et bytte krever derfor ingen ny
kjøring på microdata.no.** Rutinen:

1. Lag ny gruppefil fra `styrk08_aei_collaboration.csv`, siste chat-utvalg
   (feb. 2026), med Anthropics inndeling (`automation_share` = directive +
   feedback loop, `augmentation_share` = de tre andre). Samme regel som i
   `plot_canaries_style_usage.build_groups()`: kvintiler likevektet per yrke
   over Eloundou-universet, «No usage» for yrker uten data. Skriv til
   `styrk08_usage_groups.csv` (ta vare på den gamle som
   `..._handa_2025.csv`).
2. `python dashboard/build_release.py <release>` → `prepare_data.py` →
   deploy. Figur 10–12 og punkt 4 følger med automatisk.
3. Oppdater teksten: metodeavsnittene på forsiden og i om/… som i dag sier
   «bare directive» og «Handa-utvalget», og datafilenes data dictionary
   (`build_release.py` linje ~404 og ~556).
4. Valg å ta: (a) fast utvalg (feb. 2026) eller alltid nyeste, som flytter
   gruppene ved hver Anthropic-utgivelse; anbefaling: fast utvalg per
   release, oppgi dato i figurnoten. (b) Chat alene eller chat + API;
   anbefaling: chat, API har nesten ingen variasjon mellom yrker (87–90 %
   directive). (c) Rangeringen er ustabil mellom utvalg (Spearman 0,6–0,75),
   så en robusthetsfigur med Handa-gruppene bør ligge i appendiks.

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
