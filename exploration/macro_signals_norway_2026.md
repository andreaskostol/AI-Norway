# KI-signaler i norske løpende serier, oktober 2026

Notat etter `MACRO-AI-SIGNALS-PLAN.md`, Del B. Data hentet 2026-10-08. Hver serie er testet for
brudd i trend i november 2022 (ChatGPT) og februar 2025 (agentisk koding, etter Demirer, Musolff og
Yang 2026). Internasjonale kilder står i `literature/summaries/macro_ai_signals_international.md`.
Datakilder og status for alle kandidatserier står i `data/macro_signals/README.md`.

## Hva er hentet

Tolv kilder er hentet. Antall serier og kvartalssummer står i `summary.csv`.

- Programvare: GitHub Innovation Graph for Norge, Norden og USA (kvartal fra 2020). Commits, pull
  requests og nye repoer i NAVs GitHub-organisasjon (navikt) og i tolv andre offentlige
  organisasjoner (måned fra 2016, testet som kvartalssum).
- Foretak og domener: nye .no-domener (Norid), nye foretak (SSB 08076, kvartal) og registrerte
  enheter i Enhetsregisteret (måned).
- Forskning og tekst: publikasjoner med norsk institusjon (OpenAlex), norsk Wikipedia, bøker i
  Nasjonalbibliotekets katalog, patent-, design- og varemerkesøknader (SSB, år) og søknader til
  Forskningsrådet (år).
- Helse og forvaltning: kliniske studier med studiested i Norge (ClinicalTrials.gov), innsynskrav
  via eInnsyn og høringssvar på regjeringen.no.

NAV-annonsene er ikke hentet. Mappa `data/nav_vacancies/snapshots/` finnes ikke ennå.

## Metode

Testen ligger i `analysis/09_macro_signals/trend_break.py`. Log av serien regresseres på lineær
trend og måneds- eller kvartalsdummyer i førperioden. Førperioden slutter perioden før den som
inneholder bruddmåneden. Projeksjonen får et 95 % prediksjonsbånd fra HAC-kovariansen
(Newey-West, lag lik antall perioder per år) pluss residualvariansen.

Klassifiseringen bruker siste tolv måneder (fire kvartaler, ett år):

- for kort: under fire år i førperioden
- for støyete: snittet av båndets halvbredde er over 25 %
- brudd opp eller ned: minst halvparten av periodene ligger over eller under båndet
- ingen brudd: ellers

Standard start er januar 2016. Innovation Graph starter i 2020, så alle Innovation Graph-serier er
for korte for bruddet i 2022. Månedsserier som er for støyete, testes også som kvartalssummer. Det
gjelder også alle GitHub-seriene.

Testen er kontrollert på to måter. I en simulering med kjent svar (200 trekninger, AR(1)-feil, se
`test_trend_break.py`) gir den falsk brudd i 1,0 til 3,5 % av trekningene uten hopp. Et hopp på
pluss eller minus 20 % i februar 2025 fanges i 98,5 til 99 % av trekningene for bruddet i 2025 og i
93 % for bruddet i 2022. Git pushes fra USA i Innovation Graph gir brudd opp etter februar 2025, 46,5 % over trend siste år.
Det stemmer med Cunninghams tracker, som har 319,8 mill. globale pushes i 2026K1 mot 212,2 mill. i
snitt for 2025.

## Begreper i GitHub-seriene

- **Repo** (repository, kodelager): all koden og hele endringshistorikken for ett prosjekt, for
  eksempel én app eller tjeneste. «Nye repoer» er antall nye prosjekter som opprettes.
- **Commit**: én lagret endring i koden, med tidspunkt, forfatter og en kort beskrivelse. Vi teller
  commits på hovedgrenen, altså endringer som er tatt inn i den gjeldende versjonen.
- **Pull request (PR)**: en forespørsel om å ta en samling endringer inn i hovedgrenen. Endringene
  lages på en egen gren. Andre utviklere ser gjennom, kommenterer og godkjenner, og automatiske tester
  kjøres. En PR kan inneholde én eller mange commits.
- **Flettet PR** (merged): en PR som er godkjent og tatt inn i hovedgrenen. Den ligger nærmere en levert
  endring enn en åpnet PR, fordi noen PR-er blir avvist eller lagt bort.
- **Avhengighetsboter** (Dependabot, Renovate): programmer som lager PR-er for å oppdatere eksterne
  biblioteker. De står for rundt 60 % av NAVs PR-er og er holdt utenfor.
- **Copilot-agenten**: GitHubs KI-agent. Den får en oppgave, skriver koden selv og åpner en PR.
- **Git push** (Innovation Graph): én opplasting av commits fra en utvikler til GitHub.

I rammen til Demirer, Musolff og Yang er commits og PR-er innsats, flettede PR-er er nærmere levert
arbeid, og nye repoer er nye prosjekter. Når en PR flettes som én samlet endring, blir den også én
commit på hovedgrenen. Commits og flettede PR-er overlapper derfor.

## Figurer

Oversiktsfigurene ligger i `analysis/output/macro_signals/` som PNG og PDF:

- `overview_0_sammendrag`: avvik fra trend siste år for alle serier, begge brudd
- `overview_1_programvare`: git pushes og nye utviklerkontoer, Norge mot Norden og USA
- `overview_2_github`: NAV og andre offentlige organisasjoner på GitHub
- `overview_3_copilot`: pull requests laget av Copilot-agenten
- `overview_4_foretak`: nye foretak og .no-domener
- `overview_5_forskning`: publikasjoner, patenter, varemerker og søknader til Forskningsrådet
- `overview_6_tekst_helse_forvaltning`: Wikipedia, kliniske studier, innsynskrav og høringssvar

Én figur per serie med begge brudd ligger i `fig_<serie>.png`. Alle tall står i `summary.csv`.

## Resultater

Tabellen viser klassifisering, avvik fra trend siste år og båndets halvbredde for hvert brudd.
Avviket er faktisk mot trend siste år. Tallet etter ± er båndets halvbredde i prosent.

| Serie | Frekvens | Fra | Nov. 2022 | Feb. 2025 |
|---|---|---|---|---|
| **Programvare** | | | | |
| Git pushes, Norge | kvartal | 2020Q1 | for kort | brudd opp (+17,5 %, ±9) |
| Nye utviklerkontoer | kvartal | 2020Q2 | for kort | brudd opp (+84,6 %, ±19) |
| Nye repoer | kvartal | 2020Q2 | for kort | for støyete (+18,8 %, ±31) |
| NAV: commits | kvartal | 2020Q1 | for kort | ingen brudd (+8,4 %, ±15) |
| NAV: pull requests | kvartal | 2020Q1 | for kort | for støyete (+31,4 %, ±27) |
| NAV: flettede PR-er | kvartal | 2020Q1 | for kort | brudd opp (+27,4 %, ±20) |
| NAV: nye repoer | kvartal | 2020Q1 | for kort | for støyete (+15,5 %, ±46) |
| Andre off.: commits | kvartal | 2017Q1 | for støyete (+2,8 %, ±80) | for støyete (+15,6 %, ±49) |
| Andre off.: pull requests | kvartal | 2017Q1 | for støyete (−12,6 %, ±145) | for støyete (−0,1 %, ±77) |
| Andre off.: flettede PR-er | kvartal | 2017Q1 | for støyete (−31,2 %, ±119) | for støyete (−14,3 %, ±68) |
| Andre off.: nye repoer | kvartal | 2017Q1 | for støyete (−10,2 %, ±83) | for støyete (+7,5 %, ±73) |
| **Foretak og domener** | | | | |
| Nye foretak, alle | kvartal | 2016Q1 | brudd ned (−19,2 %, ±16) | ingen brudd (−4,5 %, ±23) |
| Nye foretak, næring 62 | kvartal | 2016Q1 | for støyete (+70,7 %, ±36) | for støyete (+49,0 %, ±28) |
| Nye foretak, næring 63 | kvartal | 2016Q1 | for støyete (+91,8 %, ±68) | for støyete (+37,3 %, ±61) |
| Enhetsregisteret, næring 62 | kvartal | 2016Q1 | for støyete (+38,6 %, ±37) | brudd opp (+50,3 %, ±25) |
| Nye .no-domener | kvartal | 2016Q1 | for støyete (+34,4 %, ±26) | brudd opp (+21,4 %, ±25) |
| **Forskning og tekst** | | | | |
| Publikasjoner | måned | 2016-01 | ingen brudd (−13,6 %, ±19) | ingen brudd (−2,1 %, ±20) |
| Tidsskriftartikler | måned | 2016-01 | brudd ned (−17,5 %, ±18) | ingen brudd (−4,9 %, ±18) |
| Preprints | kvartal | 2016Q1 | for støyete (−74,5 %, ±114) | for støyete (−50,7 %, ±104) |
| Matematikk | kvartal | 2016Q1 | for støyete (+2,2 %, ±37) | for støyete (+19,1 %, ±31) |
| Informatikk | kvartal | 2016Q1 | for støyete (−14,9 %, ±28) | for støyete (+9,0 %, ±39) |
| Patentsøknader | år | 2016 | for støyete (+60,7 %, ±32) | brudd opp (+43,5 %, ±17) |
| Designsøknader | år | 2016 | ingen brudd (+5,5 %, ±11) | ingen brudd (+6,0 %, ±10) |
| Varemerkesøknader | år | 2016 | brudd ned (−18,6 %, ±12) | ingen brudd (−4,0 %, ±20) |
| Wikipedia: redigeringer | kvartal | 2016Q1 | for støyete (−27,5 %, ±45) | for støyete (−21,4 %, ±32) |
| Wikipedia: nye sider | kvartal | 2016Q1 | for støyete (+17,6 %, ±103) | for støyete (+72,3 %, ±88) |
| Wikipedia: aktive redaktører | måned | 2016-01 | brudd ned (−17,7 %, ±10) | brudd ned (−13,0 %, ±10) |
| Bøker på bokmål | år | 2016 | brudd ned (−11,1 %, ±8) | brudd ned (−8,9 %, ±8) |
| Søknader til Forskningsrådet | år | 2016 | brudd ned (−11,8 %, ±9) | for støyete (+34,5 %, ±37) |
| Forskningsrådet: forskerprosjekt | år | 2016 | for støyete (−42,9 %, ±27) | for støyete (+18,3 %, ±90) |
| **Helse og forvaltning** | | | | |
| Kliniske studier, registrert | kvartal | 2016Q1 | for støyete (−47,0 %, ±60) | for støyete (−36,7 %, ±51) |
| Kliniske studier, startet | kvartal | 2016Q1 | for støyete (−41,4 %, ±44) | for støyete (−31,8 %, ±38) |
| Innsynskrav | kvartal | 2018Q2 | ingen brudd (−0,7 %, ±19) | for støyete (+6,2 %, ±35) |
| Høringssvar | kvartal | 2016Q3 | for støyete (−48,2 %, ±338) | for støyete (+21,9 %, ±269) |
| Høringssvar per høring | kvartal | 2016Q3 | for støyete (+22,7 %, ±40) | for støyete (+6,9 %, ±35) |

### Programvare: Innovation Graph

Git pushes fra Norge ligger 17,5 % over trenden fra før februar 2025 siste år, med bånd på ±9 %.
Tre av fire kvartaler ligger over båndet. Nivået steg fra 885 664 i 2024K4 til 1 450 334 i 2026K1.
Sverige (+21,8 %), Danmark (+11,2 %) og Finland (+20,2 %) har også brudd opp. USA ligger 46,5 % over.

Nye utviklerkontoer i Norge ligger 84,6 % over trend, med bånd på ±19 %. Tallet per kvartal steg
fra 14 094 i 2024K4 til 36 978 i 2026K1. Sverige og Danmark har også brudd opp. Finland og USA er
for støyete. Innovation Graph utelater boter og kontoer med høyere aktivitet enn et menneske kan ha, og
plasserer aktivitet etter IP-adresse. Nye repoer og nye organisasjoner er for støyete.

Alle Innovation Graph-serier er for korte for bruddet i november 2022.

### Programvare: offentlige GitHub-organisasjoner

GitHub-seriene er testet som kvartalssummer. NAV starter i 2020, fordi aktiviteten i navikt bygges
opp fra nesten null i 2016. Alle NAV-seriene er derfor for korte for bruddet i 2022.

Flettede pull requests i NAV, uten avhengighetsboter, ligger 27,4 % over trend siste år, med bånd på
±20 %. Det er brudd opp. Antallet steg fra 10 306 i 2024K4 til 17 583 i 2026K3. Alle pull requests
uten boter ligger 31,4 % over trend, men båndet er ±27 %, så serien er for støyete. Commits viser
ingen brudd (+8,4 %). Avhengighetsboter står for 62 % av NAVs pull requests i 2024 og 61 % i 2026.

Copilot-agenten laget 151 pull requests i NAV i 2025 og 1 090 fra januar til september 2026. Toppen
var 204 i mars 2026. I de andre offentlige organisasjonene laget den 91 i alt.

Seriene for de andre offentlige organisasjonene er for støyete for begge brudd, med bånd fra ±49 til
±145 %. Gruppen endrer sammensetning når organisasjoner kommer til eller legger ut flere repoer.
Commits ligger 15,6 % over trend, og pull requests ligger på trend. Commits for NAV er talt med
GitHubs commit-søk og for de andre med historikken per repo. For Skatteetaten, Digdir og
felleslosninger ga de to metodene like tall.

### Foretak og domener

Nye foretak i alt (SSB 08076) viser brudd ned mot trenden fra før november 2022, 19,2 % under siste
år. Førperioden ender med en topp i 2021, med 20 553 nye foretak i 2021K1. Fallet i 2023 og 2024
kom samtidig med renteoppgangen. Det er ikke testet. Mot trenden fra før februar 2025 er det ingen
brudd (−4,5 %).

Nye foretak i NACE 62 (IT-tjenester) ligger 49,0 % over trend siste år for bruddet i 2025. Båndet er
±28 %, så serien er klassifisert som for støyete. Tre av fire kvartaler ligger over båndet. Antallet
var 1 011 i 2026K1 og 1 162 i 2026K2, mot 540 til 793 per kvartal fra 2024K4 til 2025K4. SSBs
SN2025-tabell 14721 gir 1 015 og 1 162 for de samme kvartalene. I Enhetsregisteret er økningen størst
i 62.100 (programmering). Der steg registreringene fra 118–183 per måned i første halvår 2025 til
276–413 per måned i 2026. Økningen startet høsten 2025 og kom gradvis, ikke som ett hopp ved
overgangen til SN2025.

Enhetsregisteret egner seg ikke til trendtesten. Filen har bare enheter som finnes i dag. For NACE 62
var forholdet mellom antall levende enheter i Enhetsregisteret og nye foretak hos SSB 0,41 for 2016
og 1,00 for 2022. Trenden i Enhetsregisteret blir dermed kunstig bratt (14–15 % per år mot under
1 % hos SSB). Kvartalssummen for NACE 62 gir likevel brudd opp, 50,3 % over trend.

Nye .no-domener er for støyete per måned. Som kvartalssum ligger de 21,4 % over trenden fra før
februar 2025, med bånd på ±24,8 %. Det gir brudd opp, rett under støygrensen. Kvartalene i 2026 lå
mellom 37 498 og 40 528, mot 29 819 til 33 770 i 2025K2 til 2025K4. Serien hadde topper av samme
størrelse i 2023 (38 161 i 2023K1 og 40 300 i 2023K3). Årsaken er ikke sjekket.

### Forskning og tekst

Publikasjoner med norsk institusjon i OpenAlex, uten datasett, viser ingen brudd. Tidsskriftartikler viser brudd ned
mot trenden fra før november 2022 (−17,5 %). Veksten flatet ut før ChatGPT: 25 336 artikler i 2021,
24 372 i 2022 og 25 400 i 2025. Mot trenden fra før februar 2025 er det ingen brudd. Preprints,
matematikk og informatikk er for støyete. Preprints vokste 42 % per år i førperioden, trolig fordi
OpenAlex har fått inn flere arkiver. Det er ikke sjekket.

Patentsøknader til Patentstyret ligger 43,5 % over trend i 2025, med bånd på ±17 %. Det er ett år
etter bruddet. Søknadene steg fra 1 305 i 2024 til 1 729 i 2025. Nasjonale søknader fra innenlandske
søkere steg fra 740 til 1 125. SSB skriver 29. juni 2026 at private personer sendte dobbelt så mange
patentsøknader i 2025. Patentstyret tror årsaken er at flere privatsøkere og små bedrifter bruker KI
til å skrive søknadene. Ingen annen norsk kilde her knytter selv en endring til KI. Designsøknader viser ingen brudd. Varemerkesøknader viser brudd ned mot trenden fra
før 2022 og ingen brudd mot trenden fra før 2025.

Søknader til Forskningsrådet, talt etter søknadsdato, falt fra 5 435 i 2021 til 3 299 i 2023 og steg
til 4 723 i 2025. Mot trenden fra før november 2022 er det brudd ned (−11,8 %). Mot trenden fra før
februar 2025 ligger 2025 34,5 % over, men båndet er ±37 %, så serien er for støyete. Søknader om
forskerprosjekt falt fra 2 116 i 2022 til 1 135 i 2023 og steg til 1 402 i 2025. Antallet styres av
utlysningene, og årsaken til fallet i 2023 er ikke sjekket. Datasettet mangler søknader i det nye
saksbehandlingssystemet Tibi, så 2026 er utelatt. Andelen søknader som fikk bevilgning, lå mellom
30 og 40 % hvert år fra 2016 til 2025.

Aktive redaktører på norsk Wikipedia (bokmål) viser brudd ned for begge brudd: 17,7 % og 13,0 %
under trend. Snittet per måned falt fra 1 303 i 2016 til 1 109 i 2022, 914 i 2025 og 822 hittil i
2026. Redigeringer og nye sider er for støyete. Nye sider hadde en topp i 2025K4 og 2026K1
(9 792 og 14 718). Om toppen skyldes maskinskrevne artikler, er ikke sjekket.

Bøker i Nasjonalbibliotekets katalog viser brudd ned. De siste årene er ufullstendige fordi
katalogiseringen tar tid, så resultatet kan ikke tolkes.

### Helse og forvaltning

Kliniske studier med studiested i Norge er for støyete, med 7 til 22 studier per måned i 2026. Begge
mål ligger under trend: 220 studier ble sendt inn i 2025, mot 257 til 328 per år i 2016 til 2024.

Innsynskrav via eInnsyn viser ingen brudd for 2022 og er for støyete for 2025, 6,2 % over trend.
Kvartalene i 2026 lå mellom 158 815 og 170 487.

Høringssvar på regjeringen.no er hentet for 3 104 høringer publisert fra 2016, og 2 914 av dem har
antall svar. Testen bruker kvartalet for høringsfristen, fra 2016K3. Totalen er for støyete, med bånd
på ±269 %, fordi noen få høringer får svært mange svar. De største er koronasertifikat (22 106 svar,
frist mars 2022), forbud mot varsling av trafikkontroller (19 749, mars 2025) og ny smittevernlov
(10 564, april 2026). Medianen per høring lå mellom 23 og 27 hvert år fra 2016 til 2026. Mot trenden
fra før februar 2025 er den 6,9 % over, men for støyete. Tellingen tar med svar uten merknader og
noen dokumenter fra departementet.

## For kort eller for støyete

Alle Innovation Graph-serier er for korte for bruddet i 2022, fordi dataene starter i 2020. NAV-seriene
er også for korte for 2022, fordi de starter i 2020.

For støyete for begge brudd, også som kvartalssum: nye foretak i NACE 63, preprints, matematikk og
informatikk i OpenAlex, kliniske studier, redigeringer og nye sider på Wikipedia og nynorsk
Wikipedia, søknader om forskerprosjekt og høringssvar. Det samme gjelder alle serier for de andre
offentlige GitHub-organisasjonene.

Småtall gir brede bånd. Matematikk i OpenAlex og kliniske studier har noen titall til noen hundre per
måned. Seriene med topper, som nye sider på Wikipedia og nye .no-domener, får brede bånd selv med
mange observasjoner.

## Forbehold

- Testen sammenligner med en trend. Den kan ikke skille KI fra andre ting som skjedde samtidig. Nye
  foretak og tidsskriftartikler viser brudd ned for 2022, men nedgangen startet før ChatGPT eller
  falt sammen med renteoppgangen.
- Bruddet i november 2022 har en lang etterperiode. Usikkerheten i trenden vokser med avstanden, og en
  liten feil i trendvekst gir store avvik etter fire år.
- Årsseriene har bare ett år etter bruddet i 2025. Patentsøknadene er ett datapunkt.
- Enhetsregisteret har bare levende enheter. Nasjonalbibliotekets katalog er ufullstendig for de
  siste årene. OpenAlex indekserer med forsinkelse.
- GitHub-tallene dekker bare offentlige repoer. En organisasjon som gjør repoer private, ser ut som
  fall i aktivitet. Innovation Graph plasserer aktivitet etter IP-adresse.
- Standard start i 2016 er et valg. Tadepalli bruker 2019–2024 for Steam. En senere start gir en
  annen trend og kan endre klassifiseringen. Det er ikke testet her.

## Åpne spørsmål

- Hvor mye av økningen i git pushes og nye utviklerkontoer i Norge er nye personer, og hvor mye er
  mer aktivitet per person? Innovation Graph gir antall kontoer, ikke antall aktive utviklere i alt.
- Er økningen i nye IT-foretak (NACE 62) enkeltpersonforetak eller aksjeselskaper, og hvem står bak?
  Startet de som frilansere fordi de mistet jobben, eller fordi KI gjør det billigere å starte?
- Skyldes toppen i .no-domener i 2026 kampanjer hos forhandlere, prisendringer eller nye nettsteder?
- Hvorfor faller kliniske studier med norsk studiested, mens nye registreringer globalt øker?
  Overgangen til EUs CTIS-system kan forklare noe. Det er ikke sjekket.
- Hvorfor øker flettede pull requests i NAV mer enn commits? Det kan være flere og mindre pull
  requests, eller mer kode per pull request. Antall endrede linjer er ikke hentet.

## Kandidater for mer dybde

- **Patentsøknader fra privatpersoner.** Dobbelt så mange i 2025, og Patentstyret peker selv på KI.
  Neste steg er søknader etter søkertype og måned fra Patentstyret, og samme tall for Sverige og
  Danmark. Patentstyret sier at foreløpige tall viser samme utvikling i nabolandene.
- **Nye foretak i NACE 62.** 49 % over trend hos SSB, men for støyete etter regelen. Brudd opp i
  Enhetsregisteret, størst i programmering (62.100).
  Neste steg er å koble nye foretak til eierens alder, utdanning og tidligere yrke, for å se om dette
  er utviklere som går ut av lønnet arbeid. Om det kan gjøres i microdata.no eller på sikker server
  (`analysis-indiv/`), er ikke sjekket.
- **Nye utviklerkontoer og git pushes.** Git pushes har brudd opp i alle de nordiske landene. Nye
  utviklerkontoer har brudd opp i Norge, Sverige og Danmark. Innovation Graph har også språk og
  emner per land og kvartal. De kan vise om de nye kontoene skriver kode eller lager enkle nettsider.
- **NAV på GitHub.** Flettede pull requests har brudd opp, og Copilot-agenten laget 1 090 pull
  requests fra januar til september 2026. Neste steg er tall per repo, KI-medforfattere i
  commit-meldinger og leveranser (releases eller deploy-kjøringer).
- **Aktive redaktører på Wikipedia.** Fallet ble brattere etter 2022. Wikimedia har tall per
  redaktørgruppe og aktivitetsnivå, og tallene kan sammenlignes med svensk og dansk Wikipedia.
- **Innsynskrav.** Ingen brudd i totalen. Krav til enkelte etater kan likevel ha økt. Om eInnsyn gir
  tall per mottaker, er ikke sjekket.
- **Høringssvar.** Svarvisningen har et filter etter type høringsinstans. Om det skiller ut
  privatpersoner, er ikke sjekket. Andelen svar fra privatpersoner og hvor like svarene er, kan vise
  om KI gjør det billigere å sende kampanjesvar.
- **Kliniske studier.** En annen metode trengs: sammenlign Norge med Sverige og Danmark i samme kilde,
  og legg til EU CTIS.
