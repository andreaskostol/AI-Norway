# data-pipeline

Quarto-presentasjon (reveal.js) med én sammenhengende animasjon fra rådata til figuren «Sysselsetting etter KI-eksponering». Hvert trykk er ett steg, og linjene beholder identiteten hele veien. Tallene er de faktiske seriene.

## To varianter

Presentasjonen har to animasjonsslides med samme steg og samme kode:

| Slide | Aldersgrupper | Deles på | Sesongfaktorer | KI-indeksen på siste steg |
|---|---|---|---|---|
| 2 | Bare 21–30 år | folketallet 21–30 | egne, én per kvintil og kalendermåned for de unge | −1,0 (unge-raden på kiindeksen.no) |
| 3 | Alle, 21–60 år samlet | folketallet 21–60 | én per kvintil og kalendermåned, 60 i alt | +1,6 (hovedtallet på kiindeksen.no) |

Rekkefølgen er valgt slik at presentasjonen ender på hovedtallet for alle aldre. Slide 2 passer eksempelet fra første trykk (programvareutviklere 21–30). Faktorene er forskjellige. For Q5 er juni −4,1 prosent for de unge og −5,2 for alle samlet. Juli er +1,6 for de unge og −1,3 for alle. Begge variantene er kontrollert mot dashboardets utgave 2026-09, og avviket er 0,0 indekspoeng. Tallene på siste steg er kontrollert mot kiindeksen.no (lokal kopi, utgave 2026-09): «Alle aldersgrupper» viser +1,6 med standardfeil 2,56 prosentpoeng, og «Unge (21–30 år)» viser −1,0 med standardfeil 3,80.

Vil du bytte rekkefølgen tilbake, flytter du de to slide-blokkene i `data-pipeline.qmd`.

## Åpne og redigere

1. Åpne mappen `slides/data-pipeline` i VS Code.
2. Åpne `data-pipeline.qmd`.
3. Trykk **Preview**-knappen øverst til høyre i editoren, eller Ctrl+Shift+K. Forhåndsvisningen oppdateres når du lagrer.

Den ferdige filen `data-pipeline.html` ligger i samme mappe. Den er selvstendig og trenger bare Chrome, Edge eller Firefox. Den trenger ikke internett.

Under visning går pil høyre, mellomrom eller en presentasjonsklikker ett steg frem, og pil venstre ett steg tilbake. Tasten S åpner presentatørvisning med notater.

## Oppdatere data

Dobbeltklikk `oppdater-data.bat`. Skriptet leser nyeste `09_occ_agedecade_sektor_kpos_*_parsed.csv` i `microdata-output` og skriver `data/pipeline-data.js` (alle aldre) og `data/pipeline-data-young.js` (21–30 år). Det stopper som standard ved siste måned i nyeste dashboard-utgave, så figuren er lik kiindeksen.no. Skriptet sammenligner indeksserien med utgaven og skriver `max_abs_diff`. Bygg deretter HTML-filen på nytt med Preview-knappen.

Andre valg i terminal: `python build_data.py --through latest` bruker alle måneder i filen. `--through 2026-04` stopper ved en bestemt måned.

## Stegene

| Trykk | Hva skjer |
|---|---|
| 0 | Tabellen med rådata: yrke, aldersgruppe, måned, antall |
| 1 | Tallene flyr til punkter og blir en linje (programvareutviklere, 21–30 år, 2021) |
| 2 | Zoom ut i tid til hele perioden |
| 3 | Tre serier til, logaritmisk akse |
| 4 | Alle seriene, tegnet fra venstre mot høyre |
| 5 | Fargelegging etter eksponeringskvintil |
| 6 | Summer i hver kvintil: de tynne linjene trekkes sammen til fem |
| 7 | Del på befolkningen 21–60 år |
| 8 | Sesongjustering 1: zoom inn på kvintil 5 og vis trenden (13 måneders glidende snitt, regnet på 2021–2024) |
| 9 | Sesongjustering 2: avvik fra trenden i prosent, én prikk per måned, alle juni-månedene merket |
| 10 | Sesongjustering 3: prikkene samles per kalendermåned, snittet er faktoren, tallene står øverst |
| 11 | Sesongjustering 4: verdien deles på 1 pluss faktoren, linjene jevnes ut |
| 12 | Indekser: nov. 2022 = 100, linjene trekkes sammen i ett punkt |
| 13 | Ferdig figur med direkte linjemerking |
| 14 | KI-indeksen: Q5 og Q1 fremhevet, bånd for «før» (de tre månedene til og med oktober 2022) og «nå» (de tre siste månedene), veksten og nivået som andel av før ved hver linje, og delingen Q5 / Q1 med tallene under hverandre |

Fra trinn 6 er linjene merket direkte ved enden, og forklaringen er tatt bort. Forklaringen kommer tilbake i trinn 10, der de små fargede prikkene trenger den. Aksene i trinn 6, 7, 8, 11, 12, 13 og 14 starter ikke på null. Y-aksen har et brudd nær bunnen, uten tekst. Avviksaksen i trinn 9 og 10 er symmetrisk rundt null.

KI-indeksen er ikke differansen mellom de to linjene i figuren. For hver av Q5 og Q1 regnes nivået nå som andel av nivået før, på tre måneders glidende snitt (siste måned mot oktober 2022). Så deles Q5-andelen på Q1-andelen, og 1 trekkes fra. Det måler hvor mye forholdet Q5 mot Q1 har endret seg. Alle aldre: 0,9827 / 0,9671 = 1,0161, altså +1,61 prosent. For 21–30 år: 0,9399 / 0,9490 = 0,9904, altså −0,96 prosent.

Differansen i vekst er en annen måte å regne på: 1,56 prosentpoeng for alle aldre og −0,91 for 21–30. Nettstedet bruker forholdet, men kaller tallet prosentpoeng. Strengt tatt er forholdstallet en relativ endring i prosent.

Beregningen er den samme som i `dashboard/build_release.py` (variant `percap_sa`). Indeksserien er identisk med dashboard-utgaven.

## Sesongfaktorene

- Det finnes én faktor per kvintil og kalendermåned: fem kvintiler ganger tolv måneder gir 60 faktorer. Det finnes ikke egne faktorer per aldersgruppe, fordi aldersgruppene er slått sammen før sesongjusteringen.
- Regnestykket per kvintil, på serien «ansatte delt på befolkningen»: (1) ta logaritmen, (2) trenden er et midtstilt glidende snitt over 13 måneder der de to ytterste teller halvt, (3) avviket er logaritmen minus trenden, (4) faktoren for en kalendermåned er snittet av avvikene for den måneden, trukket fra snittet over de tolv månedene slik at faktorene summerer til null, (5) faktorene fryses og brukes på alle måneder, også etter 2024.
- Estimeringsvinduet er januar 2021 til desember 2024. Trenden finnes bare for månedene med en full ramme på 13 måneder, så hver kalendermåned får tre avvik.
- En faktor på −5,2 prosent betyr at kalendermåneden vanligvis ligger 5,2 prosent under trenden. Verdien rettes ved å dele på 1 pluss faktoren, for eksempel 0,948. Tallene i animasjonen leses fra datafilene. Eksemplet gjelder alle aldre. Slide 3 har egne faktorer for 21–30 år.

## Filer

| Fil | Innhold |
|---|---|
| `data-pipeline.qmd` | Presentasjonen: tittelslide, animasjonsslide og talenotater |
| `pipeline.js` | Animasjonsmotoren (canvas, ingen biblioteker). Overskrifter og forklaringer står i listen `STEPS` |
| `pipeline.css` | Utseende |
| `build_data.py` | Bygger begge datafilene fra microdata-output |
| `data/pipeline-data.js` | Dataene til slide 2, alle aldre. Slide-blokken har `id="pl"` |
| `data/pipeline-data-young.js` | Dataene til slide 3, 21–30 år. Slide-blokken har `id="pl-young"` |
| `_pipeline-scripts.html` | Binder inn de to skriptene |
| `oppdater-data.bat` | Dobbeltklikk-knapp for `build_data.py` |

## Bruke animasjonen i en annen presentasjon

Kopier `pipeline.js`, `pipeline.css`, `_pipeline-scripts.html` og mappen `data`. Legg `css: pipeline.css` og `include-after-body: _pipeline-scripts.html` i YAML-hodet. Kopier slide-blokken fra `data-pipeline.qmd`, fra linjen `## {.pl-slide ...}` til og med talenotatene. Bruk `id="pl"` for alle aldre og `id="pl-young"` for 21–30. Motoren velger datafil etter id. Presentasjonen må bruke bredde 1280 og høyde 720.

## Ikke sjekket

- Filen er testet i nettleserpanelet i Claude, ikke på en annen maskin.
- KI-indeksen på siste steg er regnet med formelen i `dashboard/site/public/app.js`. Tallet er ikke sammenlignet med det som vises på kiindeksen.no.
- Det finnes ingen PDF-versjon. Animasjonen finnes bare i HTML.

## Inspirasjon

Lenkene er åpnet og lest av en agent i denne økten. Noen sider ga bare tomt skall til verktøyet og ble lest i nettleseren.

- The Pudding, Is the Love Song Dying: https://pudding.cool/2024/11/love-songs/ (samme objekter går mellom oppsett, ett steg per trykk)
- Kim, Correll og Heer (2019), animerte overganger for aggregering: https://idl.uw.edu/papers/animated-aggregate-operations
- Observable Plot, Index chart: https://observablehq.com/@observablehq/plot-index-chart (indeksering til valgt dato)
- quarto-animate-graph, D3 i reveal.js med fragmenter: https://github.com/ofkoru/quarto-animate-graph
- Gemini Editor, eksempler på overganger: https://idl.uw.edu/gemini-editor/
- The Pudding, The Naked Truth: https://pudding.cool/2021/03/foundation-names/ (enkeltmerker på canvas)
- Heer og Robertson (2007), Animated Transitions in Statistical Data Graphics: https://idl.uw.edu/papers/animated-transitions
- reveal.js, Auto-Animate: https://revealjs.com/auto-animate/
- tidyexplain: https://www.garrickadenbuie.com/project/tidyexplain/ (celler beholder identitet gjennom dataoperasjoner)
