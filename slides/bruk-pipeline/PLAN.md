# Plan: presentasjon om bruksdataene fra Anthropic

15. oktober 2026

## Mål

Presentasjonen skal vise hvordan bruksmålene fra Anthropic Economic Index
går fra Claude-samtaler til norske STYRK-08-yrker. Bruksmålene er
bruksandel, automatiseringsandel og augmenteringsandel. Formen er den samme
som i `slides/mapping-pipeline`:

- Quarto og reveal.js, med en animasjon på canvas.
- Ett trykk per steg. Tabeller, koder og prikker går over i hverandre.
- Ett eksempelyrke følges gjennom hele kjeden.
- Dataene bygges av `build_data.py`. Skriptet kontrollerer tallene mot de
  ferdige filene i `data/ai_exposure/`.
- Presentatørnotater for hvert steg.
- En README med stegtabell, «Hva tallene bygger på» og «Ikke sjekket».

Presentasjonen får to animasjoner, som Eloundou og Mouchel i
`mapping-pipeline`. Den første viser hva Anthropic gjør. Den andre viser
hva vi gjør.

## Eksempelyrket

Eksempelet er informasjonsrådgivere (STYRK 2432, O*NET 27-3031.00). Det er
samme yrke som i Eloundou-animasjonen, med de samme 18 O*NET-oppgavene. Da
kan publikum kjenne igjen oppgavelista og sammenligne eksponering og bruk
direkte.

Tall for eksempelet, lest fra `data/ai_exposure/` 15. oktober:

| Utvalg | Klassifiserte samtaler | Automatiseringsandel | Bare directive |
|---|---|---|---|
| Mars 2025 | Ikke oppgitt | 0,377 | 0,365 |
| August 2025 | 2 961 | 0,447 | 0,440 |
| November 2025 | 3 431 | 0,310 | 0,310 |
| Februar 2026 | 4 010 | 0,305 | 0,305 |
| Aug. 2025 til feb. 2026 slått sammen | 10 402 | 0,347 | |

- 11 av de 18 oppgavene har samtaler i februar 2026.
- Yrket har én SOC-kode og én ISCO-kode, så kodekjeden er enkel.
- I det sammenslåtte målet havner yrket i den laveste av tre grupper.

Fire andre yrker brukes der eksempelet ikke viser poenget. Tre av dem er
også eksempler i `mapping-pipeline`.

| Yrke | Hva det viser | Tall |
|---|---|---|
| Programvareutviklere (2512) | Definisjonen betyr mye | Feb. 2026: bare directive 0,255, Anthropics regel 0,655 |
| Elektrikere (7411) | To SOC-koder blir én | Feb. 2026: 0,472 og 0,667 gir snittet 0,569. Sammenslått: 0,506 med 1 083 samtaler |
| Butikkmedarbeidere (5223) | Ett ukesutvalg er ustabilt | 0,788 i aug. 2025, 0,413 i nov. 2025 og 0,450 i feb. 2026 |
| Hotellsjefer (1411) | Ukjent andel i mars 2025 | Mars 2025: alle oppgavene filtrert, andelen satt til 0 og yrket i Q1 på forsiden. Sammenslått: 0,430 med 581 samtaler |

Rettet 15. oktober: en tidligere versjon brukte elektrikere som eksempel på
ukjent andel. Elektrikere hadde klassifiserte samtaler i mars 2025, men
alle lignet augmentering. Andelen 0 var derfor reell.

## Animasjon 1: fra samtale til oppgave og mønster

Denne delen beskriver Anthropics arbeid. Ingenting her er vårt.

| Trykk | Overskrift | Innhold |
|---|---|---|
| 0 | Kilden | Et utvalg Claude-samtaler fra Claude.ai. Fra utgivelsen i september 2025 også fra API-et. Ingen mennesker leser samtalene. Claude klassifiserer dem i et system for personvern (Clio), og bare samlede tall publiseres. |
| 1 | Hvilken oppgave? | Claude kobler samtalene til O*NET-oppgaver. Fram til mars 2026 skjer det gjennom et tre med kategorier Anthropic har laget for hånd. |
| 2 | Hvordan jobber personen med Claude? | Claude velger ett av fem mønstre, eller «none». Tabell med Anthropics definisjoner og deres egne eksempler. |
| 3 | To grupper | Directive og feedback loop er automatisering. Task iteration, validation og learning er augmentering. «None» og ikke klassifisert teller ikke med. |
| 4 | Hva som publiseres | En tabell med oppgave × mønster, og oppgavens andel av all bruk. Tre rader fra eksempelyrket vises. Celler under terskelen på 15 samtaler og 5 kontoer publiseres ikke. |
| 5 | Utgivelsene | Tidslinje fra februar 2025 til juni 2026: utvalgsperiode, plattform, og om tabellen har antall eller bare andeler. Bruddet i juni 2026 markeres. |

Trykk 5 markerer bruddet i juni 2026 og sier at det har en egen
presentasjon (se `PLAN_nye_maal.md`). Rangkorrelasjonen mellom februar og
mai 2026 for samme oppgave er 0,46, mot 0,83 mellom november 2025 og
februar 2026.

## Animasjon 2: fra oppgave til norsk yrke

| Trykk | Overskrift | Innhold |
|---|---|---|
| 0 | Et yrke er en liste med oppgaver | De 18 oppgavene til informasjonsrådgivere, som i Eloundou-animasjonen. De 7 uten samtaler i februar 2026 blir grå. |
| 1 | Bruk per oppgave | Lengden på hver stolpe er antall klassifiserte samtaler. Fargene viser de fem mønstrene. |
| 2 | Bruksandel | Yrkets oppgaver som andel av all Claude-bruk. Forklarer at tallet er globalt, ikke norsk. |
| 3 | Fra oppgaver til yrke | Samtalene summeres over oppgavene. Automatiseringsandelen er automatiserende samtaler delt på klassifiserte samtaler. En oppgave som hører til flere SOC-yrker, deles likt på dem. |
| 4 | Definisjonen betyr noe | Programvareutviklere: bare directive gir 0,255, og Anthropics regel gir 0,655. Feedback loop er mesteparten av forskjellen. |
| 5 | Tre utvalg | Tre søyler for informasjonsrådgivere: august 2025, november 2025 og februar 2026. Høyden er andelen og bredden er antall samtaler. Butikkmedarbeidere vises ved siden av: 0,788, 0,413 og 0,450. Ett utvalg alene holder ikke. |
| 6 | Slik slås de sammen | Utregningen vises linje for linje, som kortet «Skår for yrket» i Eloundou-animasjonen. Se under tabellen. |
| 7 | Fra SOC til STYRK | Samme kodekjede som for Eloundou, men uten SOC 2018. Anthropics oppgaveliste bruker koder fra SOC 2010. SOC 2010 går til ISCO-08 og ISCO-08 til STYRK-08. |
| 8 | Når kodene ikke passer | Flere koder blir én: snitt. Elektrikere har to SOC-koder, med 0,472 og 0,667 i feb. 2026. Én kode blir flere: kopi. SOC 11-1021 går til sju koder, men bare to av dem får nøyaktig 0,431. De fem andre får også bidrag fra andre SOC-koder. De fire norske unntakene som i Eloundou-animasjonen. |
| 9 | For lite bruk | Yrker med under 100 klassifiserte samtaler i de tre utvalgene til sammen får gruppen «too_few». 106 av 397 yrker havner der: 61 uten noen data og 45 under terskelen. 85 av de 106 ligger i de to laveste Eloundou-kvintilene. |
| 10 | Alle yrker | 291 prikker i kodens rekkefølge. Høyden er automatiseringsandelen. |
| 11 | Tre grupper | Rangert og delt i tre like store grupper, 97 i hver. Notatene forklarer hvorfor ikke fem: rangkorrelasjonen mellom ukesutvalgene er bare 0,61 til 0,75. |
| 12 | Mot Eloundou | Spredningsdiagram: eksponering mot automatiseringsandel. Rangkorrelasjonen over de 291 yrkene er 0,001. De to målene henger ikke sammen. |
| 13 | Resultatet | Tabell for de fire eksempelyrkene og to til: andel, antall samtaler, gruppe og andel i mars 2025. |

Sammenslåingen i trykk 6 skjer i to trinn, slik
`analysis/03_mappings/build_automation_groups.py` gjør det:

1. Andelen regnes for hvert yrke og hvert utvalg for seg, gjennom hele
   kjeden i trykk 3, 7 og 8.
2. De tre andelene veies sammen med antall klassifiserte samtaler som vekt.

For informasjonsrådgivere blir det
(0,447 × 2 961 + 0,310 × 3 431 + 0,305 × 4 010) / 10 402 = 0,347.
Det er det samme som alle automatiserende samtaler delt på alle
klassifiserte samtaler i de tre ukene. Terskelen i trykk 9 gjelder
summen, 10 402. Februar 2026 får mest vekt fordi det utvalget har flest
samtaler. Mars 2025 er ikke med, fordi den utgivelsen ikke har antall.
Juni 2026 er ikke med, fordi metoden er ny.

Trykk 2 og 3 dekker bruk. Augmentering er resten av de klassifiserte
samtalene, og vises som egen farge i trykk 1 og som egen kolonne i trykk
13. Vil vi ha egne grupper for augmentering, må de bygges, for
`styrk08_automation_groups.csv` har bare automatisering.

## Målet animasjonen ender i

Avgjort 15. oktober: animasjonen ender i det sammenslåtte målet fra august
2025 til februar 2026 (`styrk08_automation_groups.csv`). Forsiden på
kiindeksen.no bruker fortsatt mars 2025. Teksten på sliden må ikke si at
forsiden bruker dette målet før byttet er gjort.

Juni 2026 og Anthropics «observed exposure» får en egen presentasjon i
samme mappe. Planen for den står i `PLAN_nye_maal.md`.

## Data: `build_data.py`

Skriptet leser filene i prosjektet og skriver `data/bruk-anthropic.js`
(`window.BRUK_ANTHROPIC`).

Inndata:

- `data/ai_exposure/handa/aei_releases/onet_task_collaboration_claude_ai_{dato}.csv`
  og `onet_task_claude_ai_{dato}.csv` for august 2025, november 2025 og
  februar 2026
- `data/ai_exposure/handa/onet_task_statements.csv` (oppgavene og
  O*NET-SOC-kodene)
- `data/ai_exposure/handa/automation_vs_augmentation_by_task.csv` og
  `task_pct_v2.csv` for mars 2025
- `data/ai_exposure/isco_soc_crosswalk.xls` og `styrk08_codes.csv`
- `data/ai_exposure/styrk08_aei_collaboration.csv`,
  `styrk08_automation_groups.csv` og `styrk08_eloundou_beta_mapping.csv`
  som fasit
- de norske kortnavnene på de 18 oppgavene, hentet fra `TASK_NO` i
  `slides/mapping-pipeline/build_data.py`

Kontroller (assert), som i `mapping-pipeline`:

- Summen av samtalene over oppgavene til 27-3031 i februar 2026 er lik
  `n_classified` for 2432 i `styrk08_aei_collaboration.csv` (4 010).
- Automatiseringsandelen regnet fra oppgavene er lik verdien i filen.
- Det sammenslåtte snittet, vektet med antall samtaler, er lik
  `styrk08_automation_groups.csv` (0,3469 og 10 402).
- Samme utregning gir verdien i `styrk08_automation_groups.csv` for alle
  yrker, ikke bare eksempelet.
- Oppgavene i eksempelet er de samme 18 som i Eloundou-animasjonen. 17 har
  samme ID. Den 18. (20556) er en eldre formulering av 23951 i O*NET 27.2,
  fordi oppgavelista bak Anthropics tabeller er eldre.
- Gruppestørrelsene er 97, 97, 97 og 106.
- Antall koder i hvert ledd i kjeden regnes ut og skrives til konsollen.
- Hele kjeden bygges på nytt fra rådataene for alle fire utvalg i Claude.ai.
  Andel, directive-andel, bruksandel, antall samtaler og antall SOC-koder
  skal være lik `styrk08_aei_collaboration.csv` for alle yrker.
- Sammenslåingen, terskelen og tertilene gir samme verdier og grupper som
  `styrk08_automation_groups.csv` for alle 397 yrker.

Status 15. oktober: `build_data.py` er skrevet, og alle kontrollene går
gjennom.

## Teknisk oppsett

Lag mappen `slides/bruk-pipeline` med samme filer som `mapping-pipeline`:
`.qmd`, `.css`, `.js`, `_scripts.html`, `build_data.py`,
`oppdater-data.bat` og `README.md`.

Kopier motoren fra `mapping.js` til `bruk.js`, i stedet for å utvide den.
Stegene i animasjon 1 og trykk 1 til 5 i animasjon 2 er nye typer grafikk:
mønsterstolper, tidslinje og vektede søyler. En egen fil holder den ferdige
`mapping-pipeline` uendret. Kodekjeden, prikkene, gruppene og
resultattabellen kan kopieres nesten rett over.

Test i nettleserpanelet, også på mobil, før README skrives ferdig.

## Kilder for tekstene

- Handa m.fl. (2025): Clio, oppgavetreet og de fem mønstrene med
  eksempler. `literature/llm-selskapsrapporter/Anthropic Handa et al
  2025-02 ... AEI paper.pdf`.
- Mars-rapporten 2025: 11 dager etter lanseringen av Claude 3.7 Sonnet 24.
  februar 2025. `... Insights from Claude 3.7 Sonnet (web).md`.
- Rapporten fra september 2025: API-et og tabeller med antall.
- Rapporten «Cadences» med appendiks (juni 2026): metodebruddet.
- `data/ai_exposure/docs/styrk08_automation_groups_README.md`: terskel,
  sammenslåing, tertiler og «too_few».
- Dokumentasjonen til hver utgivelse på Hugging Face.

## Feil som ikke må gjentas

De eldre Beamer-lysbildene i `slides/mapping/handa.tex` og `anthropic.tex`
skal ikke brukes som kilde. `handa.tex` regner feedback loop som
augmentering og sier at indeksen kom i april 2025. Videre gjelder:

- Mars 2025-utvalget er fra de 11 dagene etter 24. februar 2025, ikke fra
  desember 2024 til januar 2025.
- «Filtered» betyr at klassifiseringen ikke er publisert. Det betyr ikke
  andel 0.
- Bruksandelen gjelder all Claude-bruk i verden, ikke norske arbeidstakere.
- Andelene gjelder bruk i chat. Automatisering som flytter til API-et eller
  Claude Code, synes ikke.
- Juni 2026 bruker en ny metode og skal ikke stå på samme skala som de
  tidligere utgivelsene.

## Rekkefølge

1. Skriv `build_data.py` med kontrollene.
2. Skriv overskrifter, ingresser og notater for alle steg.
3. Lag `bruk.js` ved å kopiere og tilpasse motoren.
4. Test i nettleserpanelet.
5. Skriv README med stegtabell, kilder og «Ikke sjekket».
6. Lag presentasjonen om de nye målene etter `PLAN_nye_maal.md`. Den
   bruker samme motor og stil.

## Ikke sjekket

- Antall samtaler i hver utgivelse. Oversikten i
  `literature/llm-selskapsrapporter/00-OVERSIKT.md` sier 4 millioner for
  Handa m.fl. og 1 million for februar 2026. Anthropics side om
  mars-rapporten sier om lag 1 million. Tallene må sjekkes mot rapportene.
- Om Anthropic kobler en samtale til én eller flere oppgaver i utgivelsene
  før juni 2026.
- Korrelasjonen mellom Eloundou og det sammenslåtte målet.
- Hvilke sitater av Anthropics eksempelsamtaler som kan brukes på sliden.
