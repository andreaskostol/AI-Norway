# KI-indeksen — nettside (kiindeksen.no)

Statisk dashboard som viser dataene fra `dashboard/releases/<RELEASE>/`
(bygget av `dashboard/build_release.py`). Norsk parallell til Stanford
Canaries Dashboard.

## Struktur

```
site/
  prepare_data.py   # release-CSV -> public/data/dashboard.json,
                    # public/data/occupations.json (yrkesvelgeren) + nedlastbare CSV-er
  prepare_panels.py # panelene: public/data/yrker.json, utdanning.json, bruk.json
                    # + public/data/panels/*.csv (egen kadens, se under)
  public/           # alt som serveres
    index.html      # KI-indeksen (flaggskipet, forsiden)
    yrker.html      # panel: automatisering/augmentering yrke for yrke
    utdanning.html  # panel: institusjoner, fagfelt, toppyrker
    bruk.html       # panel: KI-bruk per land, tokens og brukere
    om.html
    en/             # engelske tvillinger: index, occupations, education, usage, about
    app.js          # KI-indeksen: figurer (ECharts), kontroller, nedlastingsliste
    panels.js       # de tre panelene, ett script, språk fra <html lang>
    style.css
    vendor/echarts.min.js
    data/           # generert av prepare_data.py og prepare_panels.py
  Dockerfile        # nginx:alpine, serverer public/ på port 8080
  nginx.conf
  fly.toml          # app "kiindeksen", region arn (Stockholm)
```

## Panelene (Arbeidsmarkedet, sept. 2026)

Nettstedet heter Arbeidsmarkedet. KI-indeksen er fortsatt forsiden og
flaggskipet. Panelnavigasjonen (`.panel-nav`) ligger under toppfeltet på
alle sider. De tre panelene oppdateres når kildene oppdateres, ikke
månedlig:

- **Yrker** (`yrker.html`, data `yrker.json`): Anthropic Economic Index,
  tabellen O*NET-oppgave × interaksjonstype, koblet til STYRK-08 med samme
  kjede som Handa-målet. Kjede for ny utgivelse:
  `analysis/03_mappings/extract_aei_release_slices.py <råfil ...>` (last ned
  fra Hugging Face med `curl -L` først) →
  `analysis/03_mappings/build_aei_collaboration_mapping.py` →
  `dashboard/site/prepare_panels.py`. Automatisering = directive + feedback
  loop (Anthropics regel). Forsidens bruksgrupper bruker fortsatt bare
  directive og det opprinnelige Handa-utvalget.
- **Utdanning** (`utdanning.html`, data `utdanning.json`): Edutech-pipelinen
  (`AI-research/Edutech/education-analysis/`), utdata kopiert til
  `data/education_analysis/`. Seks institusjoner i første versjon.
- **KI-bruk per land** (`bruk.html`, data `bruk.json`): landfilene fra
  Anthropic (`data/ai_usage_cross_platform/` + ukesutvalgene i
  `data/ai_exposure/handa/aei_releases/usage_by_country_*` og
  `collaboration_by_country_*`).

Ny side eller ny JSON må også inn i `nginx.conf` (no-cache) og
`sitemap.xml`. Cache-parameteren på `style.css` og `panels.js` er
`v=20260907a`.

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
