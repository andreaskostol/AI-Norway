# KI-indeksen (kiindeksen.no) — redigerings- og deploy-guide

Kort innføring for Øystein: hvordan du **endrer** og **publiserer** dashbordet.
Detaljert teknisk dokumentasjon ligger i [`site/README.md`](site/README.md).

Live: <https://kiindeksen.no> (engelsk versjon: <https://kiindeksen.no/en/>).
Hostes som Fly.io-appen **`kiindeksen`** (region `arn`, Stockholm),
eier-konto `andreas.r.kostol@gmail.com`.

---

## 1. Engangs-oppsett (gjør én gang per maskin)

Du trenger `flyctl` (Fly.io sitt CLI) for å deploye, og Python 3 for å
forhåndsvise / bygge data.

```bash
# Installer flyctl (macOS)
brew install flyctl

# Logg inn på Fly-kontoen som eier appen
flyctl auth login        # bruk andreas.r.kostol@gmail.com
flyctl apps list         # du skal se "kiindeksen" i lista
```

Hvis du bare skal **se på** koden trenger du ingenting — alt ligger som
vanlige filer i `dashboard/site/public/`.

---

## 2. Hvor ting ligger

```
dashboard/
  site/
    public/              ← ALT som vises på nettsiden ligger her
      index.html         ← norsk forside (tekst, seksjoner, struktur)
      om.html            ← norsk metode-/om-side
      en/index.html      ← engelsk forside
      en/about.html      ← engelsk om-side
      app.js             ← ALL figur- og interaktivitetslogikk (ECharts).
                            Felles for norsk og engelsk; språk velges
                            automatisk fra <html lang>.
      style.css          ← all styling (farger, layout)
      data/dashboard.json← GENERERT — ikke rediger for hånd (se pkt. 5)
      data/occupations.json ← GENERERT, yrkesvelgeren (figur 9)
      assets/            ← logoer, teambilder
    Dockerfile, nginx.conf, fly.toml  ← server-/deploy-config (rør sjelden)
  build_release.py       ← bygger en ny datavintage fra mikrodata (månedlig)
  releases/<YYYY-MM>/    ← ferdige datareleaser (uforanderlige)
  backups/               ← sikkerhetskopier + tilbakerullings-instrukser
```

**Tommelfingerregel:** vil du endre **tekst** → rediger HTML-filene.
Vil du endre **en figur eller en knapp** → `app.js`. Vil du endre
**farger/utseende** → `style.css`.

---

## 3. Rediger lokalt og forhåndsvis

1. Rediger filene under `site/public/`.
2. Start en lokal server og åpne i nettleser:

   ```bash
   cd "dashboard/site/public"
   python3 -m http.server 8431
   # åpne http://localhost:8431  (engelsk: http://localhost:8431/en/)
   ```

3. Sjekk at endringen ser riktig ut **både** på norsk og engelsk.

> **Tips:** Hard-refresh i nettleseren (Cmd-Shift-R) hvis du ikke ser
> endringen — gammel CSS/JS kan ligge i cache.

---

## 4. Deploy (publiser til kiindeksen.no)

Når du er fornøyd lokalt:

```bash
cd "dashboard/site"
flyctl deploy
```

Det tar ~1–2 minutter. `flyctl deploy` bygger Docker-imaget på nytt og
bytter live-siden når den er klar. Du trenger **ikke** røre DNS eller
sertifikater — det er allerede satt opp.

### Gikk noe galt? Rull tilbake

Hver deploy får en versjon. List dem og rull tilbake til forrige:

```bash
flyctl releases --app kiindeksen           # se versjonshistorikk
flyctl deploy --app kiindeksen --image registry.fly.io/kiindeksen:deployment-<ID>
```

Eldre fulle sikkerhetskopier av hele `site/` ligger i `dashboard/backups/`
(med egne `REVERT_*.md`-instrukser).

---

## 5. Månedlig dataoppdatering (ny måned med tall)

Dette gjøres bare når det finnes et nytt mikrodata-uttrekk. Rekkefølge:

```bash
# 1) Bygg ny datavintage (eksempel: juli 2026)
python dashboard/build_release.py 2026-07

# 2) Rekjør bootstrap-usikkerhetsbåndet for hovedtallet: bump LAST_CUT
#    (linje ~52) til siste måned i releasen, så kjør scriptet (~1 min)
python analysis/06_figures/recursive_kiindeks_headline.py

# 3) Konverter siste release til nettside-data (plukker nyeste automatisk;
#    leser også siste rad i coef_recursive_kiindeks_headline.csv)
python dashboard/site/prepare_data.py

# 4) Rett de hardkodede tallene i «Hovedfunn» (om.html) og «Key findings»
#    (en/about.html), bump cache-parameteren, forhåndsvis (pkt. 3), deploy (pkt. 4)
cd "dashboard/site" && flyctl deploy
```

Releaser er **uforanderlige vintages** — en eksisterende `releases/<YYYY-MM>/`
endres ikke; en ny måned blir en ny mappe.

---

## 6. Fallgruver (les disse før du publiserer)

- **Cache-parameter:** når du endrer `app.js` eller `style.css`, bump
  versjonsstrengen `?v=YYYYMMDD` i HTML-filene og i `fetch(...)` i
  `app.js` (nå `v=20260902d`).
  Ellers ser brukerne en gammel cachet versjon.
- **Hardkodede hovedtall:** «Hovedfunn» i `om.html` og «Key findings» i
  `en/about.html` har tall skrevet rett inn i teksten. De oppdateres
  **ikke** automatisk ved ny release — rett dem manuelt begge steder.
- **Norsk ↔ engelsk i takt:** `app.js` er felles og leser samme element-
  ID-er på begge språk. Hvis du endrer en ID eller struktur i `index.html`,
  gjør samme endring i `en/index.html` (og `om.html` ↔ `en/about.html`).
- **`dashboard.json` redigeres aldri for hånd** — den genereres av
  `prepare_data.py`. Vil du endre data, endre kilden og kjør scriptet.
- **Forfattere i bunnteksten:** Øystein Hernæs (Frischsenteret) og
  Andreas R. Kostøl (BI) skal stå begge steder — ikke fjern.

---

## 7. Vanlige småoppgaver — hvor?

| Jeg vil…                                   | Fil |
|--------------------------------------------|-----|
| Rette en setning / overskrift              | `index.html` (+ `en/index.html`) |
| Endre metodeteksten                        | `om.html` (+ `en/about.html`) |
| Endre en figur (akse, farge, etikett)      | `app.js` |
| Bytte fargepalett / layout                 | `style.css` |
| Oppdatere et teambilde / logo              | `public/assets/` |
| Legge inn nye månedstall                   | pkt. 5 |

Spør gjerne hvis noe er uklart — Andreas / Claude kan hjelpe med
`app.js`-logikken, som er den eneste virkelig tekniske biten.
