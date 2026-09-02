# Plan: yrkesvelger på kiindeksen.no («Velg yrker selv»)

Fra Andreas (med Claude), 2. september 2026. Bygger på e-posttråden
«KIindeksen mai + juni» samme dag.

## Status 2026-09-02 kveld: Del B ferdig og publisert (Andreas)

Yrkesvelgeren er live som figur 9 på kiindeksen.no og /en/ (Fly-image
`deployment-01M1HTRXMGJ47BAPXC4V837Y8P`, commit etter `4471180`).
Sjekklista fra Del A er gjennomgått: 358 yrker og 66 måneder i begge
pakker, yoy for fem yrker × to justeringer stemmer med egen omregning
(avvik maks 5e-5, ren avrunding), tom kvintil (3 yrker) og æ/ø/å (136
navn) håndteres, og nedlastingsmanifestet plukket opp de to kortene.
Renummerert: KI-bruk 10–12, offentlig sektor 13–16. Nedlastingskortene
er gruppert i fem sammenleggbare grupper. Paperlenken (RFBerlin 179/26,
ny tittel) er inne i siteringsblokken, paper-ref, om.html og
en/about.html. Engelske yrkesnavn kom samme kveld: SSBs offisielle
engelske STYRK-08-navn fra Klass API (klassifikasjon 7, language=en),
lagret i `data/ai_exposure/styrk08_names_en.csv` med to manuelle
rettelser (2221 Specialist nurses, 2267 Occupational therapists).
ISCO-08-titler ble forkastet: STYRK-08 avviker fra ISCO for enkelte
koder (2267 er ergoterapeuter i STYRK, optikere i ISCO). Søket på /en/
treffer både engelsk og norsk navn. Ikke gjort: nyansettelser per yrke,
offentlig sektor per yrke.

## Status 2026-09-02: Del A ferdig (Øystein)

`canaries_no_occupations` og `canaries_no_wages_occupations` ligger i
`releases/2026-09/` (commit `f71efa1`). Som avtalt: terskel minst 30 i
alle måneder, nyansettelser venter, bare raw/sa, norske navn + kode.

Ett avvik fra planen: **358 yrker, ikke 359.** Planens opptelling slapp
gjennom kode 0000 (uoppgitt yrke), som bare finnes i 3 av 66 måneder —
den krevde min ≥ 30 uten å kreve tilstedeværelse i alle måneder. 0000
mangler basismåneden og kan ikke indekseres, så den er riktig ute.

QA: 47 256 rader per pakke (358 × 66 × 2), ingen NaN i `sa`,
basismåneden er nøyaktig 100, pooled råindeks reproduserer uavhengig
for 4222/4321/5322/7411, feriepengehoppet synlig i lønn (median
juni/mai = 1,18). 3 yrker har tom `exposure_quintile` (mangler
Eloundou-skår). Kolonner: `observation_date`, `adjustment`, `styrk08`,
`occupation`, `Employment Index`/`Wage Index`, `n_base`,
`exposure_quintile`. Del B kan starte.

Rettelse samme dag (commit `d5032d9`): planens antakelse om at
`write_package` kunne brukes rett fram med
`facet_cols=["styrk08", "occupation"]` holdt ikke — `derive()` lagger
12 *rader* innenfor fasettene, så uten `adjustment` i fasettlisten ble
yoy-lagget 6 måneder med raw/sa blandet. Fasettene er nå
`["adjustment", "styrk08", "occupation"]`. Hovedfilene er
byte-identiske med første bygging; bare yoy- (fra 2022-01, 38 664
rader) og annualized-filene (radrekkefølge) er endret. Verifisert med
20 + 10 stikkprøver per pakke mot eksakt omregning fra indeksen.

**Til Andreas før Del B kobles på:** ta en egen sjekk av pakkene, ikke
stol blindt på QA-en over. Konkret: (1) 358 yrker og 66 måneder i
begge pakker, (2) yoy for et par kjente yrker mot egen omregning,
(3) at `occupations.json`-byggingen håndterer tom `exposure_quintile`
(3 yrker) og norske navn med æ/ø/å, (4) at nedlastingsmanifestet
plukker opp de to nye kortene.

## Det vi allerede er enige om (fra tråden)

1. Ny seksjon rett etter siste yrkescase (figur 8).
2. Alle aldre samlet, ikke aldersgrupper. Alder × yrke gir for mye støy.
3. Bare yrker med mer enn 30 lønnstakere.
4. Brukeren kan velge flere yrker samtidig og sammenligne dem.
5. Bare privat sektor. Begge sektorer blir forvirrende når alt over er
   privat.
6. Nedlastingsseksjonen må ikke bli hundrevis av kort.

## Anbefalt løsning i én setning

Én lang datapakke med alle yrker, én JSON-fil på nettsiden, og en
seksjon med søkefelt, valgte yrker som «chips» og ett linjediagram som
følger velgerne øverst (utfall, justering, glatting, referanse).

## Tall som styrer designet

Fra panelet `09_occ_agedecade_sektor_kpos_2021m01_2026m06_parsed.csv`,
privat sektor, 21–60 år, alle aldre samlet:

| Krav | Antall yrker |
|---|---|
| Alle yrker i panelet | 403 |
| Minst 30 lønnstakere hver måned 2021-01 til 2026-06 | 359 |
| Minst 100 hver måned | 329 |
| Minst 30 i hver av de fire aldersgruppene hver måned | 283 |

Anbefaling: terskelen er «minst 30 lønnstakere i alle måneder». Da får
ingen serie hull, og sesongjusteringen (logaritmer) er trygg. Det gir
359 yrker.

## Del A: data (Øystein, `dashboard/build_release.py`)

Ny pakketype, lang format med yrke som fasett. Ikke én mappe per yrke.

- `canaries_no_occupations`: kolonner `observation_date`, `adjustment`,
  `styrk08`, `occupation`, `Employment Index`, pluss to konstante
  kolonner per yrke: `n_base` (lønnstakere i november 2022) og
  `exposure_quintile`. `adjustment` bare `raw` og `sa`. Per innbygger
  er ikke meningsfullt for ett yrke, det skalerer alle serier likt.
- `canaries_no_wages_occupations`: samme oppsett, FTE-justert lønn,
  `raw` og `sa`. Lønn har ingen nullmåneder og tåler yoy/annualized.
- `canaries_no_hires_occupations`: valgfritt i v1. Små yrker har
  måneder med null nyansettelser, og basismåneden kan være nær null.
  Hvis den skal med: `derived=False` som for yrkescasene, og egen
  terskel (for eksempel minst 5 nyansettelser hver måned).
- Yrkesnavn på norsk fra `data/ai_exposure/styrk08_codes.csv`
  (nivå 4, kolonnen `name`, filen er latin-1). Engelske navn kan tas
  fra ILOs ISCO-08-struktur (STYRK-08 er ISCO-08 på firesifret nivå).
  Faller vi ikke på plass med engelsk, viser den engelske siden norsk
  navn og kode. Det er akseptabelt i v1.
- `write_package` kan brukes som den er med
  `facet_cols=["styrk08", "occupation"]`. `derive` håndterer fasetter.
- Data dictionary: én setning om terskelen, at yrkene er enkeltkoder
  (ikke grupper som i yrkescasene), og at små yrker er støyende.
- Releasene er uforanderlige, men build_release lar oss legge nye pakker
  til en eksisterende release. Pakken kan derfor legges i 2026-09 nå,
  uten å vente på oktoberdataene.

QA før overlevering: 359 yrker, 66 måneder hver, ingen NaN i `sa`,
lønnsserier uten åpenbare feil i juni (feriepenger), og at 2512, 4222,
7411 og 5322 stemmer med yrkescasene der koden er den samme.

## Del B: nettside (Andreas/Claude)

### `prepare_data.py`

- Ny funksjon `load_occupations(release)` som leser de lange pakkene og
  skriver `public/data/occupations.json`, ikke inn i `dashboard.json`.
  Grunn: 359 yrker × 66 måneder × 2 justeringer × 2 utfall er om lag
  95 000 tall, rundt 500 kB ukomprimert. `dashboard.json` er allerede
  664 kB, og hovedsiden skal ikke bli tregere.
- Struktur: `{release, dates, occupations: [{code, name_no, name_en,
  quintile, n_base, employment: {raw: [], sa: []}, wages: {raw: [],
  sa: []}}]}`. Avrundet til to desimaler som resten.
- `download_files`-manifestet plukker opp pakkene automatisk.

### `app.js`

- Egen `fetch("/data/occupations.json")` som starter etter at
  `dashboard.json` er lastet, slik at hovedfigurene ikke venter.
- Søkefelt med treff mens du skriver (kode + navn, norsk og engelsk),
  maks 12 treff i lista. Ingen nye biblioteker, samme som
  andreaskostol.no/ai gjør med et vanlig tekstfelt.
- Valgte yrker som chips med kryss for å fjerne. Maks 6 samtidig, det
  er grensen for lesbare endepunktsetiketter i Canaries-stilen.
- Hver chip viser `n_base` og kvintil i tittel-tekst. Yrker med under
  200 lønnstakere får en liten «lite yrke»-markering.
- Ett linjediagram gjennom `lineOption`/`renderLines`. Etikett er
  yrkesnavn kuttet til om lag 28 tegn, full tekst og kode i tooltip.
- Følger `state.outcome` (sysselsetting og lønn, nyansettelser hvis
  pakken finnes), `state.adjustment` (raw/sa, per innbygger faller ned
  til nærmeste som for lønn), `state.smoothing` og `state.epoch`.
  `seriesFor` leser i dag fra `DB.packages`. Den trenger en liten
  generalisering som tar en rå tallrekke og datoer direkte.
- Standardvalg ved lasting: 2512 Programvareutviklere, 4110
  Kontormedarbeidere, 5223 Butikkmedarbeidere, 7411 Elektrikere. Fire
  kjente yrker fra ulike kvintiler.
- Valget legges i URL-en (`?yrker=2512,4110`), slik at en lenke kan
  deles. Lite arbeid, stor nytte i LinkedIn-tråder.
- Knapp «Last ned valgte yrker (CSV)» som lager fila i nettleseren fra
  JSON-en. Da slipper vi kort per yrke i nedlastingsseksjonen.

### HTML (`index.html` og `en/index.html`, samme element-ID-er)

- Ny `<section id="yrker-velg">` med h2 «9 · Velg yrker selv», intro,
  søkefelt, chips, figur og fotnote. Fotnoten sier: privat sektor,
  alle aldre 21–60, bare yrker med minst 30 lønnstakere hver måned,
  små yrker er støyende, sammensetningen innenfor et yrke kan endre
  seg over tid.
- TOC-lenke og nav-lenke.
- Metode: kort `<details>` «Velg yrker selv (figur 9)».
- `om.html` og `en/about.html`: én setning i metodeavsnittet.

### Nummerering

Med den nye seksjonen som figur 9 må resten flyttes ett hakk:
KI-bruk 10–12, offentlig sektor 13–16. Alternativet er å la seksjonen
stå uten nummer. Anbefaling: renummerer, det er en times arbeid med
grep. Steder som må rettes, begge språk:

- TOC-lenkene («9 · Vekst etter KI-bruk», «10–11 · KI-bruk»,
  «12–15 · Offentlig sektor»).
- Overskriftene i seksjonene 9–15.
- `app.js`: `renderOutcomeTitles` skriver «12 · » og «14 · » for
  offentlig sektor.
- Tekstreferanser: «figur 9–11» i metode-details, «figur 10 under» i
  fotnoten til figur 9, «figur 15» i forbeholdsboksen, «figur 12–15» i
  quick-scope-linja, nav-en og metode-details for offentlig sektor.

### CSS

Søkefelt og treffliste (`.occ-search`, `.occ-hits`), chips
(`.occ-chip`), og en liten `.occ-small`-markering. Gjenbruk
`.btn-row`-stilen for knappene.

## Del C: nedlastingsseksjonen

- Yrkespakkene gir to eller tre kort, ikke 359.
- Seksjonen har allerede 40 kort. Forslag: grupper dem i
  `<details>`-blokker: Hovedkutt, Yrkescase, KI-bruk, Offentlig sektor,
  Alle yrker. Første gruppe åpen, resten lukket. Det er en liten
  endring i `renderDownloads` (én tittel-til-gruppe-tabell).

## Avgjørelser som gjenstår

| Spørsmål | Anbefaling |
|---|---|
| Terskel | Minst 30 lønnstakere hver måned (359 yrker) |
| Utfall i v1 | Sysselsetting og lønn. Nyansettelser i v2 med egen terskel |
| Maks antall yrker samtidig | 6 |
| Nummerering | Renummerer 9–16 |
| Standardvalg | 2512, 4110, 5223, 7411 |
| Engelske navn | ISCO-08 fra ILO hvis lett, ellers norsk navn + kode |
| Offentlig sektor | Ikke i v1. Kan senere legges som `sector`-fasett i pakken og en bryter inne i seksjonen |

## Rekkefølge og arbeidsdeling

1. Øystein: Del A i `build_release.py`, pakkene legges i
   `releases/2026-09/`. Anslag 2 timer med QA.
2. Andreas/Claude: `prepare_data.py` og `occupations.json`. Halv time.
3. Andreas/Claude: seksjon, app.js, CSS, renummerering, metodetekst,
   begge språk. 3–4 timer.
4. Nedlastingsgrupper. Halv time.
5. QA lokalt: `python3 -m http.server 8431` i `site/public/`, headless
   Chrome med `--screenshot` og `--dump-dom`, sjekk at alle canvas
   finnes og at konsollen er tom. Samme oppskrift som 2. september.
6. Bump cache-parameter, backup til `backups/`, `flyctl deploy`, commit.

Steg 2–6 kan gjøres samme dag som pakkene er klare.

## Ting å være obs på

- `seasonal_adjust` tar logaritmer. Terskelen på 30 sikrer at ingen
  måned er null.
- Yrkeskoder endres sjelden, men noen koder mangler Eloundou-skår
  (403 i panelet mot 397 i canaries-utvalget). Pakken bør ta med alle
  yrker over terskelen, ikke bare canaries-utvalget, og la
  `exposure_quintile` være tom der skår mangler.
- Personvern: microdata.no gjør sin egen avsløringskontroll ved
  eksport, og yrkescasene publiserer allerede serier per yrke.
  Terskelen på 30 gir ekstra margin.
- Cache: `occupations.json` må inn i `nginx.conf` som `no-cache` på
  samme måte som `dashboard.json`.
