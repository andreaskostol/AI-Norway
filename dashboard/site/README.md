# KI-indeksen — nettside (kiindeksen.no)

Statisk dashboard som viser dataene fra `dashboard/releases/<RELEASE>/`
(bygget av `dashboard/build_release.py`). Norsk parallell til Stanford
Canaries Dashboard.

## Struktur

```
site/
  prepare_data.py   # release-CSV -> public/data/dashboard.json + nedlastbare CSV-er
  public/           # alt som serveres
    index.html
    app.js          # figurer (ECharts), kontroller, nedlastingsliste
    style.css
    vendor/echarts.min.js
    data/           # generert av prepare_data.py (sjekkes ikke inn på nytt manuelt)
  Dockerfile        # nginx:alpine, serverer public/ på port 8080
  nginx.conf
  fly.toml          # app "kiindeksen", region arn (Stockholm)
```

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
