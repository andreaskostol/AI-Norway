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
`v=20260907d` (bump i alle HTML-filer og i `V` i panels.js ved endring).

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
