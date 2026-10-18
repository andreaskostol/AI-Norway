# KI-indeksen — nettside (kiindeksen.no)

Statisk dashboard som viser dataene fra `dashboard/releases/<RELEASE>/`
(bygget av `dashboard/build_release.py`). Norsk parallell til Stanford
Canaries Dashboard.

## Struktur

```
site/
  prepare_data.py   # release-CSV -> public/data/dashboard.json,
                    # public/data/occupations.json (yrkesvelgeren) + nedlastbare CSV-er
  prepare_panels.py # sidene Yrker og Utdanning: public/data/yrker.json,
                    # utdanning.json (egen kadens, se under; ingen nedlastbare CSV-er)
  public/           # alt som serveres
    index.html      # KI-indeksen (flaggskipet, forsiden)
    yrker.html      # Yrker: hvor utsatt er jobben din, oppgaver, bruk over tid
    utdanning.html  # Utdanning: studievalget, oppgaver og jobber per faggruppe
    om.html
    en/             # engelske tvillinger: index, occupations, education, about
    app.js          # KI-indeksen: figurer (ECharts), kontroller, nedlastingsliste
    panels.js       # Yrker og Utdanning, ett script, språk fra <html lang>
    style.css
    vendor/echarts.min.js
    data/           # generert av prepare_data.py og prepare_panels.py
  Dockerfile        # nginx:alpine, serverer public/ på port 8080
  nginx.conf
  fly.toml          # app "kiindeksen", region arn (Stockholm)
```

## Landingsside og filmer (okt. 2026)

`/` (`index.html`, engelsk `en/index.html`) er en kort landingsside: to animerte
figurer (mest og minst eksponerte yrker, alle aldre og 21–30 år) med ChatGPT og
agentisk KI som hendelser og KI-indeksen regnet som i `app.js` (`landing.js`),
fire talltavler fra `headline_uncertainty_*`, knapp «Se hele indeksen her», tre
kort (Indeksen, Labben, Studio) og en filmblokk. Den fulle indekssiden er
`indeksen.html` / `en/the-index.html`; sidelenken «Indeksen» peker dit. Gamle
dyplenker (`/#data` osv.) sendes videre av et lite skript øverst i `index.html`.

**Filmer.** `landing.js` (forsiden) og `studio.js` (Studio, seksjonen `#filmer` /
`#films`) tegner filmene fra `public/data/videos.json`. Feltet `placement` sier hvor en
film vises (`landing`, `studio`). Bare `status: "publisert"` vises; med `?forhandsvis=1`
i adressen vises også utkast, til gjennomsyn før publisering. Uten engelsk fil vises den
norske på den engelske siden med `fallback_note`.

Leveransen fra Codex 18. oktober 2026 (`dashboard/video_delivery.json`, med SHA256 og
varigheter; overleveringen står i `dashboard/README.md`) ligger kopiert og
sjekksumkontrollert i `public/video/`:

| Fil | Innhold | Stemme |
|---|---|---|
| `kiindeksen-resultater-2026-10.mp4` | Norske resultater etter agentisk KI, data til og med juli 2026 (4:22) | stemmeklonen |
| `kiindeksen-resultater-2026-10-egen.mp4` | Samme film, egen innlesning 16. oktober (4:40). To innholdsflagg i `kiindeksen-resultatfilm-egen-ny-provenance.json` (elektrikere hos Mouchel ved 1:24, Codex-datoen ved 2:39) må avklares før publisering | egen innlesning |
| `kiindeksen-eksponering.mp4` | Fra arbeidsoppgaver til KI-eksponering (4:23) | stemmeklonen |
| `kiindeksen-studio-imas-schaal.mp4` | Imas og Schaal (2:33) | stemmeklonen |
| `kiindeksen-studio-anthropic-scenarioer.mp4` | Anthropics framtidsscenarioer (2:35) | stemmeklonen |

MP4-filene er ikke i git (`.gitignore`): de ligger i Dropbox og på Fly. Plakatene og
manifestet er i git. `.dockerignore` holder MP4-filene utenfor Fly-bygget til Andreas sier
publiser. Slik publiserer du:

1. Fjern linja `public/video/*.mp4` fra `dashboard/site/.dockerignore`.
2. Sett `status: "publisert"` på filmene som skal ut i `videos.json`, og `updated`.
3. Deploy. `nginx.conf` cacher `/video/` i en uke og `videos.json` aldri.

Nye filmer: legg MP4 og plakat i `public/video/` (plakat:
`ffmpeg -ss 3 -i FILM.mp4 -frames:v 1 -q:v 4 PLAKAT.jpg`), legg til en oppføring i
`videos.json` med `placement`, og kontroller sjekksummen mot leveransen.

Stemmer: norsk bruker stemmeklonen (ElevenLabs, godkjent uttale 18. oktober 2026; profil og
lydreferanse i det private repoet `andreas-stemme`, ikke i dette repoet og ikke på
nettstedet). Engelske filmer bruker alltid Fish Audio-klonen; ingen engelske filmer finnes
ennå. Filmkoden er Codex sin (PR 2, `dashboard/build_results_video.py` m.fl., se
`dashboard/README.md`).

## MCP-kobling (okt. 2026)

Dataene nettstedet publiserer er også tilgjengelige som verktøy for Claude og
egne script gjennom en MCP-server i `dashboard/mcp/` (egen Fly-app
`kiindeksen-mcp`, endepunkt `https://kiindeksen-mcp.fly.dev/mcp`). Den henter
JSON-filene fra `public/data/` på nettstedet ved oppstart og hver sjette time,
så den trenger ingen ny utrulling ved månedlig release. Se `dashboard/mcp/README.md`.
Siden `mcp.html` / `en/mcp.html` (tredje kort under Labben, 2026-10-15) forklarer
koblingen med verktøytabell og eksempel. `public/mcp/client_example.py` er en kopi
av `dashboard/mcp/client_example.py`; kopier på nytt når scriptet endres.

## Labben og Studio (okt. 2026)

Sidelenkene øverst er nå Indeksen | Labben | Studio | Om (engelsk:
Index, Lab, Studio). Yrker og Utdanning er uendret som sider, men ligger
under **Labben** (`labben.html`, `en/lab.html`): en kort side som sier
hva verktøyene skal, med lenker. Tredje kort er MCP-koblingen (`mcp.html`). På `yrker.html` og `utdanning.html`
er Labben aktiv i sidelenkene, og en undermeny (`.panel-subnav`) viser
hvilket verktøy som er åpent.

**Studio** (`studio.html`, `en/studio.html`) er under bygging:
podkaster, videoer og nyheter om ny forskning, medregnet nye funn fra
Anthropic. Siden har en
artikkelsporing: `studio.js` leser `public/data/studio_papers.json` og
fyller tabellen (dato, artikkel, kilde, status, plan), med knapper per
type (forskning, Anthropic, andre rapporter). Lista vedlikeholdes for hånd
i JSON-fila; feltene står i `_om` øverst i fila. Status: ny, notat, video,
podkast, publisert. Plan: notat, notat+video, podkast, ingen. Startlista (2026-10-14) er
bygget fra `literature/` og `literature/llm-selskapsrapporter/00-OVERSIKT.md`;
lenker og måneder som ikke var sjekket, er utelatt.

Nye sider må stå i `nginx.conf` (no-cache-regexene) og `sitemap.xml`.

## Sidene Yrker og Utdanning (sept. 2026)

KI-indeksen er forsiden og navnet på nettstedet. Yrker og Utdanning er
egne sider, med sidelenkene (`.panel-nav`) øverst til høyre i toppfeltet
på alle sider, på samme rad som språkveksleren.
Om-siden er én setning pluss de to som lager indeksen; metode og sitering
ligger på forsiden. Sidene drives av `panels.js` (språk fra `<html lang>`,
side fra `<body data-panel>`). Sammendragene skrives som løpende tekst fra
dataene, ikke som nøkkeltallsfliser. De to sidene oppdateres når kildene
oppdateres, ikke månedlig:

- **Yrker** (`yrker.html`, data `yrker.json`): Anthropic Economic Index,
  tabellen O*NET-oppgave × interaksjonstype, koblet til STYRK-08 med samme
  kjede som Handa-målet. Kjede for ny utgivelse:
  `analysis/03_mappings/extract_aei_release_slices.py <råfil ...>` (last ned
  fra Hugging Face med `curl -L` først) →
  `analysis/03_mappings/build_aei_collaboration_mapping.py` →
  `dashboard/site/prepare_panels.py`. Automatisering = directive + feedback
  loop (Anthropics regel). Forsidens bruksgrupper bruker fortsatt bare
  directive og det opprinnelige Handa-utvalget. «Velg et yrke» øverst på siden
  bruker i tillegg `styrk08_task_neighbours.csv`
  (`analysis/03_mappings/build_occupation_task_similarity.py`, O*NET-profiler)
  og, ved «Sammenlign arbeidsmarkedet», `occupations.json` pluss
  `vacancies.json` (NAV, se `data/nav_vacancies/README.md`; bygges av
  `prepare_panels.py` bare når `nav_vacancies_by_styrk.csv` finnes).
- **Utdanning** (`utdanning.html`, data `utdanning.json`): studievalget.
  Per NUS-faggruppe (nivå + tosifret fag) de ti vanligste oppgavene i
  jobbene utdanningen fører til, med Eloundou-etikett og Claude-bruk per
  oppgave, og de vanligste jobbene. `analysis/07_education/build_majors.py`
  (trenger utdanning.no-koblingsfilene i Edutech-mappa, `EDUTECH_DIR`; O*NET
  30.1-filene ligger i `data/ai_exposure/onet_relational/`) →
  `data/education_analysis/majors.json` → `prepare_panels.py`.
  Lærestedsvisningen (`build_institutions.py`, DBH) er tatt av siden og
  ventes som egen analyse.

Ny side eller ny JSON må også inn i `nginx.conf` (no-cache) og
`sitemap.xml`. Cache-parameteren på `style.css` og `panels.js` er
`v=20261015a` (bump i alle HTML-filer og i `V` i panels.js ved endring).

## Månedlig oppdatering

1. Bygg ny datarelease (krever nytt microdata-uttrekk i
   `microdata-output/`):
   `python dashboard/build_release.py 2026-07`
2. Regenerer nettsidedata (plukker automatisk siste release):
   `python dashboard/site/prepare_data.py`
3. Se over lokalt:
   `cd dashboard/site/public && python3 -m http.server 8431`
4. Deploy:
   `cd dashboard/site && flyctl deploy`

## Domene

Appen heter `kiindeksen` på Fly.io. For å koble kiindeksen.no:

```
flyctl certs add kiindeksen.no -a kiindeksen
flyctl certs add www.kiindeksen.no -a kiindeksen
```

og pek DNS hos registraren: A-post `@` -> appens IPv4, AAAA-post `@` ->
appens IPv6 (`flyctl ips list -a kiindeksen`), CNAME `www` ->
`kiindeksen.fly.dev`.

## Innstillinger i frontend

- Utfallsvelger (sysselsetting / nyansettelser / lønn FTE-justert)
  gjelder hovedfigurene 1–3 og bytter mellom pakkene `by_*`,
  `hires_*` og `wages_*` (`OUTCOMES`/`corePkg` i `app.js`).
  Yrkescasene og bruksfigurene viser bare sysselsetting.
- Justeringsvarianter (`raw`/`sa`/`percap`/`percap_sa`) ligger som
  fasett i dataene; standardvisningen er `percap_sa`. Lønnspakkene
  har bare `raw`/`sa`: percap-valgene deaktiveres når lønn er valgt,
  og visningen faller ned til nærmeste variant (`adjFor` i `app.js`).
- Glidende snitt (3/6 mnd, bakoverskuende) beregnes i nettleseren
  (`movingAverage` i `app.js`).
- Norske etiketter for engelske kolonnenavn: `NO_LABELS` i `app.js`.
- Yrkesvelgeren (figur 9) leser `data/occupations.json` etter at
  `dashboard.json` er lastet (`initOccupations` i `app.js`). Valget
  ligger i URL-en som `?yrker=2512,4110`; maks 6 yrker; nedlasting av
  valgte yrker bygges som CSV i nettleseren.
