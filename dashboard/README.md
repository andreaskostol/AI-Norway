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
#    Åtte kjøringer: 2 mål x 2 referanser x 2 aldersgrupper. Uten
#    _young-kjøringene blir standardfeilen på unge-raden stående på
#    forrige måneds tall.
python analysis/06_figures/recursive_kiindeks_headline.py
python analysis/06_figures/recursive_kiindeks_headline.py mouchel   # målvelgeren
python analysis/06_figures/recursive_kiindeks_headline.py eloundou claudecode   # referanse Claude Code
python analysis/06_figures/recursive_kiindeks_headline.py mouchel claudecode
python analysis/06_figures/recursive_kiindeks_headline.py eloundou chatgpt young
python analysis/06_figures/recursive_kiindeks_headline.py mouchel chatgpt young
python analysis/06_figures/recursive_kiindeks_headline.py eloundou claudecode young
python analysis/06_figures/recursive_kiindeks_headline.py mouchel claudecode young

# 3) Konverter siste release til nettside-data (plukker nyeste automatisk;
#    leser også siste rad i coef_recursive_kiindeks_headline.csv)
python dashboard/site/prepare_data.py

# 4) Det finnes ikke lenger hardkodede tall på nettsiden: om.html og
#    en/about.html er én setning pluss forfatterne (siden 2026-09-07), og
#    hovedtallet, kvintiltallene, oppsummeringen og release-etiketten
#    skrives av app.js fra dashboard.json. Standardreferansen på forsiden
#    er ChatGPT fra 2026-09-25 (var Claude Code 2026-09-04 til
#    2026-09-25); planen er agentisk KI som standard igjen fra november
#    2026. Ta backup av public/ til dashboard/backups/, bump
#    cache-parameteren (v=YYYYMMDDa) i alle HTML-filene, forhåndsvis, deploy
cd "dashboard/site" && flyctl deploy
```

Releaser er **uforanderlige vintages** — en eksisterende `releases/<YYYY-MM>/`
endres ikke; en ny måned blir en ny mappe.

---

## 6. Fallgruver (les disse før du publiserer)

- **Cache-parameter:** når du endrer `app.js` eller `style.css`, bump
  versjonsstrengen `?v=YYYYMMDD` i HTML-filene og i `fetch(...)` i
  `app.js` (nå `v=20260904h`).
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

## Automatiserte filmer (15. oktober 2026)

Videokoden ligger i denne mappen. Den bruker penn-og-tusj-motoren fra Suveren Intelligens,
med egne scener og rullende tekst. `video_ink.js` er en uendret kopi av tegnemotoren.
Norske filmer bruker nå Andreas sin stemmeklone fra ElevenLabs.
`video_voice.json` er gjeldende kilde for stemme, dialekt og uttale. Kristine finnes bare i eldre prøveversjoner.

### Folder context

Dette er en del av AI-Norway og kiindeksen.no, ikke Suveren-nettstedet.
Andreas har valgt eksisterende AI-Norway i Dropbox for filer, og dette GitHub-repoet for koden.
Videokoden ligger i eksisterende `dashboard/`. Ferdige lokale gjennomgangsfiler ligger i prosjektroten.
Midlertidige bilder lages i systemets midlertidige mappe og fjernes etter rendering.
Ingen ny prosjektmappe ble opprettet. Ingen film er publisert.

### Kjør etter en dataoppdatering

Bygg først nettstedets data med den vanlige releaserutinen. Resultatfilmen leser
`site/public/data/dashboard.json`, ikke presentasjonens gamle tall.
Den beregner hovedindeksen som forholdet mellom vekstfaktorene for Q5 og Q1, minus én.
Referansen er gjennomsnittet august–oktober 2022, sammenlignet med de siste tre månedene.
Hovedtallet er prosent, ikke forskjellen mellom to prosentvise vekstrater i prosentpoeng.
Yrkeseksemplene viser derimot per-innbygger-serier med november 2022 lik 100.

Krav: Python 3, Node.js, ffmpeg, ffprobe og Playwright med Chromium.
Fra dashboard-mappen installeres den fastsatte nettleseravhengigheten med `npm install`
og Chromium med `npx playwright install chromium`. En eksisterende Chrome kan brukes
med `CHROME_CHANNEL=chrome`. `PLAYWRIGHT_MODULE` kan peke på en eksisterende installasjon.
Python-koden bruker standardbiblioteket.

Kjør fra repoets rot. OUTPUT må være en eksisterende mappe:

```sh
python3 dashboard/build_results_video.py --out OUTPUT
python3 dashboard/build_results_video.py --out OUTPUT --synthesize --render
python3 dashboard/build_research_video.py imas --out OUTPUT --synthesize --render
python3 dashboard/build_research_video.py anthropic --out OUTPUT --synthesize --render
KI_VIDEO_DATA=dashboard/site/public/data/dashboard.json python3 dashboard/test_results_video.py
```

Uten `--synthesize` skjer ingen overføring til stemmetjenesten. `--synthesize` sender
manus til ElevenLabs og bruker kontoen som er konfigurert med `ELEVENLABS_API_KEY`
eller lokal nøkkelfil `~/.config/elevenlabs/key`. Nøkler lagres aldri i repoet.
Uendrede lydopptak gjenbrukes etter kontroll av tekst og stemmeinnstillinger.
Ord følger tidsstemplene fra lydtjenesten. Et annet transkript stopper byggingen.
Allerede lagrede lydfiler kan brukes med `--audio OUTPUT/kiindeksen-resultatfilm-lyd`.

Byggingen stopper ved manglende tall, ulike datamåneder, endret referanse eller
usikkerhetsmål fra en annen måned. Konklusjonen velges fra det gjeldende intervallet,
slik at et nytt resultat ikke arver en gammel påstand om null eller nedgang.
Researchfilmene er redaksjonelle manus. De oppdateres ikke automatisk ved nye norske tall.
Kildene og datoen for kildekontroll ligger i manusmodulen og hvert filmmanifest.

MP4, manus, HTML, manifest og kontrollrapport får samme filstamme.
`kiindeksen-resultatfilm` er resultatfilmen, `kiindeksen-imas-film` er forskningsoversikten,
og `kiindeksen-anthropic-film` forklarer scenarioene for USA.
De siste filmene er på norsk. Anslag fra scenarioverktøyet er ikke norske prognoser.
HTML er en bilde- og tekstforhåndsvisning. MP4 inneholder lydsporet.

### Kontroll og publisering

Gjennomgangsutkast merkes «KI-assistert · venter på menneskelig kontroll».
Andreas har bedt om merket «AI-assisted, human-validated» på den godkjente utgaven.
Det skal først brukes når en person faktisk har kontrollert innholdet.
Da oppdateres sluttbildet og sluttsetningen, og de berørte opptakene bygges på nytt.
Filmen sier at helt menneskeskapt materiale planlegges dersom prosjektet får finansiering.

Renderer kontrollerer tekstbredden og dekoder hele eksporten. Lytt til navn, tall og uttale
før publisering. Modell- og datatolkningen må også kontrolleres av et menneske.
Kommandoene publiserer ikke, laster ikke opp filmer og endrer ikke nettstedet.
Git-commit og innsending venter på Andreas' gjennomgang etter prosjektets AGENTS.md.

Resultatfilm, revidert manus 15. oktober: kortere kanarifuglsekvens og ingen gjentatt konklusjon.
Agentisk sammenligning bruker november 2024–januar 2025 som referanse, begge eksponeringsmål og begge aldersutvalg.
Revidert manus ligger i `kiindeksen-resultatfilm-revidert-manus.txt`. Eksisterende MP4 er fortsatt forrige versjon.
Ny lyd venter på godkjenning av manusoverføring til ElevenLabs etter automatisk avvisning.

Norske filmer er hovedversjonen. `video_voice.json` velger Andreas-klonen og Eleven v4.
Felles stemmeregler for norsk og engelsk: https://github.com/andreaskostol/andreas-stemme (privat).
Den norske profilen her skal samsvare med `norsk.json` i stemmerepoet.
I lydmanuset endres vi → me, ikke → ikkje og bruker → bruge. Bøyningsendelsen -er uttales -e gjennom eksplisitte ordregler. Ingen -er → -a.
Andreas sier mye, aldri mykje. Behold mye i både manus og tale. Ikke gjør andre ord om til nynorsk.
KI uttales kå-Í, med åpen Å, trykk på I og fyldig klang fra magen. Det gjelder også KI-indeksen.
`video_voice.json` styrer uttalestavingen. `synthesize_video.py` bruker den før hver syntese.
`-talemanus.txt` inneholder ordene stemmen leser. `-manus.txt` og bildeteksten beholder bokmål.
Den tidligere IPA-prøven ble senere avvist: den hørtes ut som KO-I. Referansen er Andreas sin egen innlesning fra 16. oktober.
Send `kå-Í` til Eleven v4 for KI, og `kå-Í-indeksen` for KI-indeksen. Uttalen må kontrolleres i eksportert lyd.
Dette er uttaleinstruksjon til stemmen. Vis alltid KI og KI-indeksen i skjermteksten.
Bildeteksten beholdes på bokmål og kobles til tidsstemplene for de tilsvarende talte ordene.
Manuell innlesning beholdes som egen versjon. Originalopptak endres aldri.

Animasjonene i resultatfilmen følger ordtidene i hvert lydspor. Åpningen har bevegelige objekter og oppgaveark. Kodearbeid, sammenligningsperiode og yrkesgrupper bygges opp under forklaringen. Usikkerhetsintervallene tegnes fra anslaget til de faktiske grensene. Anslagene flyttes ikke. Rendereren tar flere bilder under bevegelsene og beholder teksttimingen.

### Ny innlesning og yrkeseksempler, 16. oktober 2026

Lesemanus: `../kiindeksen-nytt-lesemanus.html`. Visuelt utkast uten lyd: `../kiindeksen-resultatfilm-nye-figurer.html`. Yrkeseksempler og kurver kommer før gruppeforklaringen. Q1-eksempler er 7126 og 9112, Q5-eksempler er 2512 og 2411, kontrollert mot begge mappingfilene. Elektrikerkurven er merket Q1 hos Eloundou og Q2 hos Mouchel. Blyantkonturer og ny fugletegning bruker eksisterende tegnemotor. Blåfarge og skriftfamilie følger `site/public/style.css`. Dagens innlesning finnes i kiindeksen-resultatfilm-egen-ny.mp4. Studio viser denne ved siden av kloneversjonen. Ingen publisering.

Uttaleregler oppdatert 16. oktober 2026: flere, aldri fleire. KI-indeksen og kiindeksen bruker samme åpne Å og trykk på I.
Ord med -er som ikke er en bøyningsendelse, som her og mer, skal ikke endres automatisk.

### Bygg resultatfilm med gjeldende stemmeregler

`rebuild_results_clone.py` bruker et godkjent resultatmanus og `video_voice.json`.
Velg en eksisterende arbeidsmappe med `--out` og resultatmanifestet med `--source`.
`--synthesize --render` lager ny tale, klipper pauser og gjengir filmen med bokmålstekst.
Originale innlesninger endres ikke. Kommandoen publiserer ikke filmen.

### Filmfarge kontrollert mot nettstedet 16. oktober 2026

Filmene skal bruke #002B7E, fra `.brand h1` og `.tagline` i nettstedets `style.css`.
#0F4C81 er nettstedets aksentfarge, ikke den valgte filmfargen. Burgunder skal ikke brukes.
Kontroller også eksporterte videobilder. En endring i HTML alene oppdaterer ikke en MP4.
