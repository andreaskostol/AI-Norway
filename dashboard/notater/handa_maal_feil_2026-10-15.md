# Bruksmålet fra Anthropic på kiindeksen.no: feil som bør rettes

15. oktober 2026. Gjelder versjonen av nettstedet med Labben og Studio.

## Bakgrunn

Kiindeksen.no bruker Anthropic Economic Index på tre sider.

- Forsiden (Indeksen, `index.html`) grupperer yrker etter hvor stor andel
  av Claude-samtalene om yrkets oppgaver som er automatiserende eller
  augmenterende (figur 10 til 12).
- Yrkessiden (Yrker under Labben, `yrker.html`, engelsk
  `en/occupations.html`) viser andelene per yrke for flere utvalg.
- Utdanning under Labben (`utdanning.html`) viser automatiseringsandelen
  per oppgave og per utdanning. Den bruker bare siste utvalg fra Claude.ai
  (februar 2026) og Anthropics regel.

Labben-siden (`labben.html`) lenker til Yrker og Utdanning og nevner
Anthropic Economic Index som kilde. Studio (`studio.html`) lister
rapporter fra Anthropic. Siden bruker ikke dataene.

Anthropic klassifiserer samtalene i fem mønstre. Directive og feedback
loop regnes som automatisering. Task iteration, validation og learning
regnes som augmentering. Samtaler som ikke er klassifisert i de
publiserte dataene, står som «filtered».

Forsidens grupper kommer fra `data/ai_exposure/styrk08_handa_mapping.csv`.
Filen lages av `analysis/03_mappings/build_handa_mapping.py` fra to filer
i Anthropics utgivelse 27. mars 2025 (`release_2025_03_27`):

- `automation_vs_augmentation_by_task.csv`: andelen av hvert mønster per
  O*NET-oppgave.
- `task_pct_v2.csv`: oppgavens andel av alle samtaler.

Kjeden går fra O*NET-oppgave via SOC 2010 og ISCO-08 til STYRK-08. Den
gir 352 STYRK-koder. Forsiden deler dem i fem like store grupper med 71,
70, 70, 70 og 71 koder. De 45 yrkene i Eloundou-utvalget som mangler i
filen, vises som «Ingen bruk».

Yrkessiden lages av `analysis/03_mappings/build_aei_collaboration_mapping.py`
og `dashboard/site/prepare_panels.py`. Det første utvalget der bygger på
de samme to filene. De neste er Anthropics utgivelser for august 2025,
november 2025 og februar 2026, for Claude.ai og API-et.

## Oversikt

| Nr. | Problem | Hvor | Type |
|---|---|---|---|
| 1 | Feil dataperiode for det første utvalget | Yrkessiden, kode, dokumentasjon | Feil fakta |
| 2 | Yrker uten klassifisering får andel 0 og havner i Q1 | Forsiden, paperet | Endrer resultater |
| 3 | Delvis filtrerte yrker trekkes mot 0 | Forsiden, paperet | Endrer resultater |
| 4 | «Kvintil 1 (minst bruk)» er feil navn | Forsiden | Misvisende |
| 5 | Forsiden definerer automatisering annerledes enn Anthropic og BCC | Forsiden mot yrkessiden | Misvisende |
| 6 | Feil kilde for andelene | Forsiden, yrkessiden | Misvisende |
| 7 | «Publisert fire ganger» er utdatert | Yrkessiden | Utdatert |

Punkt 1 til 7 beskriver feilene slik nettstedet og paperet er i dag.
Anbefalingen under «Hvilken utgivelse bør vi bruke?» er å bytte bruksmål på
forsiden. Da løses punkt 2 til 5 på forsiden. Punkt 1, 6 og 7 må rettes
uansett. Punkt 2, 3 og 5 gjelder fortsatt for mars 2025-målet i paperet.

## 1. Feil dataperiode for det første utvalget

**Hva som står.** Yrkessiden sier at det første utvalget er samtaler i
Claude.ai fra desember 2024 til januar 2025, fra Handa m.fl. (2025). Det
samme står i figurteksten, i koden og i dokumentasjonen. Utvalget er
merket med datoen 2024-12-01 i datafilene.

**Hva som er riktig.** Filene hører til mars-rapporten «Anthropic Economic
Index: Insights from Claude 3.7 Sonnet». Ifølge Anthropic bygger den på
samtaler fra de 11 dagene etter lanseringen av Claude 3.7 Sonnet. Modellen
ble lansert 24. februar 2025. Desember 2024 til januar 2025 er perioden
for den første rapporten, Handa m.fl. (2025). Den utgivelsen
(`release_2025_02_10`) har ingen fil med mønster per oppgave, bare en
samlet fordeling.

**Kontroll.**

- Våre to filer er byte-identiske med filene i `release_2025_03_27` på
  Hugging Face. Det er sjekket med md5-sum.
- Mars-utgivelsen har to samlede fordelinger. v1 er den første rapporten
  og v2 er Claude 3.7 Sonnet-rapporten. Tabellen sammenligner dem med vår
  fil, vektet med `task_pct_v2`. «Filtered» og «none» er holdt utenfor
  nevneren. Tallene er prosent.

| Mønster | Vår fil | v2 | v1 |
|---|---|---|---|
| Directive | 30,5 | 30,4 | 27,8 |
| Feedback loop | 12,8 | 12,7 | 14,8 |
| Task iteration | 25,0 | 24,8 | 31,3 |
| Validation | 3,7 | 4,1 | 2,8 |
| Learning | 28,0 | 28,0 | 23,3 |

- Vektet med `task_pct_v1` gir vår fil 30,4 % directive og 27,4 % learning.
  Klassifiseringen per oppgave er altså v2 uansett vekt.

**Steder som må rettes.**

- `dashboard/site/public/yrker.html:274-276`: sier at forsidens tall kommer
  fra «det første utvalget til Handa m.fl. (2025)».
- `dashboard/site/public/yrker.html:282-284`: perioden.
- `dashboard/site/public/en/occupations.html:278-280` og `:286-288`: det
  samme på engelsk.
- `dashboard/site/public/panels.js:973-974`: figurteksten.
- `dashboard/site/prepare_panels.py:40-41`: etikett og kilde. Skriptet
  lager `dashboard/site/public/data/yrker.json` på nytt.
- `analysis/03_mappings/build_aei_collaboration_mapping.py:5-7`, `:26-27`
  og `:60` (`HANDA_DATE = '2024-12-01'`).
- `analysis/03_mappings/build_automation_groups.py:20` og `:74`
  (`HANDA_DATE`).
- `data/ai_exposure/docs/styrk08_automation_groups_README.md:30`.
- `dashboard/PLAN_arbeidsmarkedet_2026-09.md:233` og `:451`. Dette er en
  plan og kan rettes sist.

**Retting.** Kort etikett: «feb.–mars 2025». Lang etikett: «11 dager etter
lanseringen av Claude 3.7 Sonnet 24. februar 2025». Kilde: Anthropic
Economic Index, mars 2025 (Claude 3.7 Sonnet). Sett `HANDA_DATE` til
lanseringsdatoen 2025-02-24 i begge skriptene. Anthropic oppgir ikke
nøyaktig startdato. Datoen identifiserer utvalget i
`data/ai_exposure/styrk08_aei_collaboration.csv` og i `yrker.json`.
Skriptene og `prepare_panels.py:219` må derfor kjøres eller rettes
samtidig.

## 2. Yrker uten klassifisering får andel 0 og havner i laveste kvintil

**Hva som skjer.** 1 066 av 3 364 oppgaver i filen har `filtered = 1`.
Ingen av samtalene deres er klassifisert. 40 av de 352 STYRK-kodene har
bare slike oppgaver. `build_handa_mapping.py:181-182` setter da både
automatiserings- og augmenteringsandelen til 0. Alle de 40 kodene har
bruksandel over 0. Andelen er altså ukjent, ikke 0.

**Konsekvens.** Alle de 40 kodene havner i Q1, både for automatisering
og for augmentering. Q1 har 71 koder. Dermed er 40 av 71 yrker i Q1 yrker
der andelen er ukjent. Totalt har 58 koder automatiseringsandel 0, og alle
ligger i Q1. I figur 10 til 12 på forsiden mangler derfor over halvparten
av den laveste gruppen mål.

**Motsetning på forsiden.** Forsiden sier at «Ingen bruk» er yrker under
spørringsterskelen. De 45 yrkene i «Ingen bruk» har alle SOC-koder i
kryssgangen. Ingen av oppgavene deres finnes i Anthropics fil. De 40
kodene over er i praksis i samme situasjon. Likevel vises de som Q1.

**Slik gjør BCC.** Brynjolfsson, Chandar og Chen (BCC) har et lignende
problem og håndterer det på to måter. Tallene under er fra versjonen fra august
2026.

- Yrker der ingen oppgave har nok samtaler til å komme med i bruksdataene,
  får en egen kategori. Det tilsvarer «Ingen bruk» hos oss.
- Over 20 % av yrkene over terskelen har automatiseringsandel 0. BCC slår
  derfor sammen første og andre automatiseringskvintil til ett nivå (figur
  3, panel B). BCC sier ikke om nullene skyldes filtrerte oppgaver.
- De to laveste augmenteringskvintilene har svært lite bruk (fotnote 20).
  Yrkene der har i snitt 0,01 og 0,09 % av Claude-samtalene. BCC viser at
  resultatene er like når yrker med lite bruk tas ut (nettappendiks, figur
  F.4 og F.5).

Vi har verken sammenslåingen eller kontrollen. Hos oss har 58 av 352 koder
(16,5 %) automatiseringsandel 0.

**Retting.**

- Skriv tom verdi (NaN), ikke 0, når en kode mangler klassifiserte
  samtaler.
- Legg de 40 kodene i en egen kategori. Alternativt kan de slås sammen med
  «Ingen bruk» under et nytt navn, for eksempel «Ingen klassifisert bruk».
- Lag kvintilene over de 312 kodene som har klassifiserte samtaler.
- Oppdater forsidens tekst om «Ingen bruk».
- Et enklere alternativ er å slå sammen Q1 og Q2 for automatisering, slik
  BCC gjør. Det skjuler likevel at andelen er ukjent for 40 koder.
- Legg til kontrollen fra BCC: vis resultatene uten yrker med lite bruk.

## 3. Delvis filtrerte yrker trekkes mot 0

**Hva som skjer.** En STYRK-kode får ofte andeler fra flere SOC-yrker.
`build_handa_mapping.py:224-226` tar et likevektet snitt over dem.
SOC-yrker uten klassifiserte samtaler går inn i snittet med andel 0. 63
koder har minst ett slikt SOC-yrke og minst ett med data. 15 av dem ligger
i Q1 for automatisering.

**Retting.** Hopp over SOC-yrker uten klassifiserte samtaler når snittet
lages. `build_aei_collaboration_mapping.py:184` gjør allerede dette
(`if cls <= 0: continue`). Med den regelen får det første utvalget på
yrkessiden 312 koder. Rettingen av punkt 2 og 3 gir dermed samme
aggregering på forsiden og yrkessiden.

## 4. «Kvintil 1 (minst bruk)» er feil navn

Forsiden kaller gruppene «Kvintil 1 (minst bruk)» og «Kvintil 5 (mest
bruk)». Navnene står i `dashboard/build_release.py:67-69` og er oversatt i
`dashboard/site/public/app.js:26-27`. Gruppene er laget etter hvor stor
andel av samtalene som er automatiserende eller augmenterende. De sier
ikke hvor mye yrket bruker Claude. Et yrke med mye bruk og lav
automatiseringsandel ligger i Q1. Stanford-dashboardet bruker de samme
navnene i sine datafiler («Quintile 1 (least usage)»). Der er de like
misvisende.

**Retting.** Bruk navn som «Kvintil 1 (lavest andel)» og «Kvintil 5
(høyest andel)». Endringen må gjøres i `build_release.py` og i
oversettelsen og gruppelisten i `app.js` (linje 26-27 og 587-588).

## 5. Forsiden definerer automatisering annerledes enn Anthropic og BCC

Forsiden regner bare directive som automatisering. Feedback loop regnes
som augmentering. Yrkessiden bruker Anthropics regel, der automatisering
er directive pluss feedback loop. Yrkessiden sier fra om avviket. Forsiden
sier ikke at den avviker fra Anthropic.

Forsiden skriver at gruppene er laget «som i» BCC
(`dashboard/site/public/index.html:514-516`, `en/index.html:523-525`).
BCC bruker Anthropics regel. Det står i fotnote 14 i versjonen fra
november 2025 og i fotnote 40 i versjonen fra august 2026. Forsiden følger
altså verken Anthropic eller BCC på dette punktet.

Forskjellen påvirker grupperingen. Rangkorrelasjonen mellom de to
definisjonene er 0,80 til 0,90 i de fire Claude.ai-utvalgene. Av 291 yrker
med gruppe i `data/ai_exposure/styrk08_automation_groups.csv` havner
75,6 % i samme tertil med begge definisjonene.

**Retting.** Bruk Anthropics regel på forsiden også. Da stemmer forsiden
med Anthropic, BCC og yrkessiden. Alternativt kan forsiden si at feedback
loop regnes som augmentering, i motsetning til hos Anthropic og BCC. Da må
«som i» BCC tas ut.

## 6. Feil kilde for andelene

Forsiden lenker til Handa m.fl. (2025), arXiv:2503.04761, som kilde for
andelene. Lenkene står i `dashboard/site/public/index.html:369`, `:381` og
`:513`, og i `en/index.html:375`, `:388` og `:522`. Yrkessiden kaller det
første utvalget «Handa m.fl. (2025)». Handa m.fl. bruker data fra desember
2024 til januar 2025 og publiserte ikke andeler per oppgave. Andelene vi
bruker, kommer fra mars-rapporten 2025.

**Retting.** Oppgi mars-rapporten som datakilde. Handa m.fl. (2025) kan
stå som kilde for inndelingen i fem mønstre.

## 7. «Publisert fire ganger» er utdatert

Yrkessiden sier at tabellen oppgave × type er publisert fire ganger.
Utgivelsen 26. juni 2026 («Cadences») har også directive og de andre
mønstrene per O*NET-oppgave. Tallene er globale for Claude.ai og gitt per
måned. Filen `release_2026_06_26/data/aei_claude_ai_2026-06-26.csv` har
for eksempel `collaboration_directive_pct` på oppgavenivå for april 2026.
`analysis/03_mappings/extract_aei_release_slices.py` henter bare `pct` fra
denne utgivelsen, så mønstrene er ikke med.

**Retting.** Skriv hvilke utgivelser siden bygger på, og hvorfor juni 2026
ikke er med. Grunnene står under «Hvilken utgivelse bør vi bruke?».

## Hvilken utgivelse bør vi bruke?

Anthropic har publisert seks utgivelser av Economic Index på Hugging Face.
Ingen er kommet etter juni 2026.

| Utgivelse | Samtaler fra | Brukt hos oss |
|---|---|---|
| Februar 2025 (Handa m.fl.) | Desember 2024 til januar 2025 | Nei. Har ingen andeler per oppgave. |
| Mars 2025 (Claude 3.7 Sonnet) | 11 dager etter 24. februar 2025 | Forsiden, paperet, første utvalg på yrkessiden |
| September 2025 | 4. til 11. august 2025 | Yrkessiden, Claude.ai og API |
| Januar 2026 | 13. til 20. november 2025 | Yrkessiden, Claude.ai og API |
| Mars 2026 | 5. til 12. februar 2026 | Yrkessiden, Claude.ai og API. Utdanning, Claude.ai. |
| Juni 2026 («Cadences») | April og mai 2026, per måned | Bare bruksandeler, for Norge og globalt |

Perioden for september 2025 til mars 2026 står i navnene på rådatafilene.

**Slik gjør BCC.** Versjonen fra august 2026 bruker mars 2025 i
hovedresultatene. Nettappendiks F.2 slår sammen utgivelsene fra september
2025, januar 2026 og april 2026 (fotnote 12). Der regnes Claude.ai og API
sammen. Hugging Face har ingen utgivelse fra april 2026, bare fra 24. mars
2026. Om BCC mener den samme, er ikke sjekket.

**Slik gjør Stanford-dashboardet.** Dashboardet viderefører BCC, men
oppgir ikke hvilken utgivelse det bruker. Det står verken på siden eller i
beskrivelsene av datafilene. Feltet `vintage` i datafilene er 2026-09-17,
og det samsvarer ikke med noen utgivelse fra Anthropic. Dashboardet viser
fem automatiseringskvintiler pluss «No usage». BCC slår som nevnt sammen
de to laveste i artikkelen.

**Juni 2026-utgivelsen.**

- Dokumentasjonen sier at utgivelsen dekker april og mai 2026. Den omfatter
  Claude chat og Cowork.
- Den har mønstre for 2 403 oppgaver i april og 2 709 i mai. Antall
  samtaler er ikke oppgitt. Alle verdier er avrundet til to desimaler.
- Oppgavens andel av bruken er 0,00 for 1 304 av 2 410 oppgaver i april og
  1 566 av 2 713 i mai. Vektene som kjeden vår bruker, mangler dermed for
  over halvparten av oppgavene.
- Gjennom kjeden vår gir april 256 STYRK-koder og mai 263 med bruksvekter.
  Med lik vekt per oppgave blir det 325 og 334. Februar 2026 gir 319.
- Rangeringen av yrker avviker sterkt fra de tidligere utvalgene.
  Rangkorrelasjonen med februar 2026 er 0,08 til 0,18, avhengig av måned og
  vekt. Mot august og november 2025 er den 0,20 til 0,35. Mellom april og
  mai er den 0,89 til 0,94.
- På oppgavenivå er rangkorrelasjonen med februar 2026 0,45 til 0,46. Da
  er bare oppgaver med minst 30 klassifiserte samtaler i februar tatt med.

**Hvorfor juni 2026 avviker.** Anthropic endret metoden i denne
utgivelsen. Endringene står i kapittel 1 i appendikset til rapporten
«Cadences».

- Utvalget er et fast antall samtaler hver time gjennom måneden. Tidligere
  dekket hvert utvalg én uke.
- Samtalene kobles til oppgaver på en ny måte. Klassifisereren velger
  først en detaljert arbeidsaktivitet (DWA) og så en oppgave innenfor den.
  Har flere oppgaver like høy sikkerhet, trekkes én tilfeldig. Anthropic
  skriver at dette skal spre samtalene på flere oppgaver.
- Oppgavelisten er O*NET versjon 30.2 fra februar 2026.
- Klassifisereren ser en mye større del av hver samtale.
- Dataene omfatter Claude chat og Cowork.
- Appendikset sier ikke om klassifiseringen av de fem mønstrene er
  endret.

Tallene våre viser at endringen slår ut på to måter.

| Sammenligning | Samme oppgave | Yrker, alle oppgaver | Yrker, felles oppgaver |
|---|---|---|---|
| Nov. 2025 mot feb. 2026 (gammel metode) | 0,83 | 0,62 | 0,74 |
| Feb. 2026 mot april og mai 2026 | 0,45 til 0,46 | 0,09 til 0,11 | 0,36 til 0,39 |
| April mot mai 2026 (ny metode) | 0,91 | 0,89 | 0,95 |

Tallene er rangkorrelasjoner for automatiseringsandelen. Yrkestallene er
regnet med lik vekt per oppgave og per SOC-yrke. Én oppgave får altså en
annen andel med ny metode. Samtidig er det andre oppgaver som får
samtalene. Når yrkene bare regnes på felles oppgaver, stiger
korrelasjonen fra rundt 0,1 til rundt 0,37. På felles oppgaver steg snittet
for automatiseringsandelen fra 0,44 til 0,50.

I april finnes 415 av 2 400 ulike oppgavetekster ikke i O*NET-listen vår.
I mai gjelder det 453 av 2 706. Det stemmer med at Anthropic har byttet til ny
O*NET-versjon. Disse oppgavene faller ut av kjeden vår.

Avviket er derfor mest sannsynlig et brudd i serien. Det kommer samtidig
med en dokumentert metodeendring. Med gammel metode var korrelasjonen for
samme oppgave 0,83 over tre måneder. Over de to månedene fra februar til
april falt den til 0,45. Den høye korrelasjonen mellom april og mai viser
at den nye metoden gir stabile tall. Den viser ikke at metoden er bedre.

**Målet vi bruker, mot andre mål.** Målet i paperet og på forsiden bygger
på mars 2025 og regner bare directive som automatisering. Det har 352
koder. Tabellen sammenligner automatiseringsandelen med andre mål.

| Sammenlignet med | Rangkorrelasjon | Andel av vår Q5 som også er i Q5 |
|---|---|---|
| Mars 2025, samme definisjon, punkt 2 og 3 rettet | 0,88 | 0,76 |
| Mars 2025, Anthropics regel (yrkessiden) | 0,76 | 0,65 |
| August 2025, Claude.ai | 0,13 | 0,28 |
| November 2025, Claude.ai | 0,15 | 0,23 |
| Februar 2026, Claude.ai | 0,12 | 0,22 |
| Februar 2026, API | −0,21 | 0,16 |
| August 2025 til februar 2026 slått sammen, n ≥ 100 | 0,15 | 0,25 |
| April 2026 (ny metode) | −0,20 | 0,24 |
| Mai 2026 (ny metode) | −0,21 | 0,19 |

Q5-kolonnen viser hvor stor andel av yrkene i vår øverste kvintil som også
er i øverste kvintil i det andre målet. Den er regnet uten de 40 kodene der
andelen er ukjent. Uavhengige rangeringer ville gitt rundt 0,20. Uten de 40
kodene stiger korrelasjonen mot de senere Claude.ai-utvalgene til 0,15 til
0,23. April og mai 2026 er regnet med lik vekt per oppgave.

To forhold trekker korrelasjonen ned. Tabellen under sammenligner med
august 2025, november 2025 og februar 2026 i Claude.ai.

| Mars 2025-målet | Mot senere utvalg, bare directive | Mot senere utvalg, Anthropics regel |
|---|---|---|
| Som vi bruker det | 0,22 til 0,29 | 0,12 til 0,15 |
| Med punkt 2 og 3 rettet | 0,42 til 0,45 | 0,34 til 0,43 |

I første rad er mars 2025-målet det vi bruker, med bare directive. I andre
rad har mars 2025-målet samme definisjon som kolonnen.

- Konstruksjonen vår. Med bare directive gjør rettingene i punkt 2 og 3
  korrelasjonen mot de senere utvalgene 1,5 til 2 ganger så høy. Det
  rettede målet korrelerer likevel 0,88 med det vi bruker.
- Bruken eller målingen har endret seg. Selv rettet ligger mars 2025 på
  0,34 til 0,45 mot de senere utvalgene. Mellom de senere utvalgene er
  korrelasjonen 0,61 til 0,75.

For augmentering korrelerer målet vi bruker 0,62 med mars 2025 slik
yrkessiden regner det. Mot februar 2026 er korrelasjonen 0,24.

**For nyere data.**

- Andelene har endret seg. Snittet for automatiseringsandelen i Claude.ai
  er 0,36 i mars 2025 og 0,45 til 0,52 i de tre senere utvalgene.
- Rangeringen har endret seg. Med Anthropics regel og punkt 2 og 3 rettet
  er rangkorrelasjonen mellom mars 2025 og februar 2026 0,34. Valget av
  utgivelse avgjør altså hvilke yrker som havner øverst og nederst.
- De nyere utgivelsene har antall samtaler. Da kan tynne celler skilles ut.
  Mars 2025 har ingen antall.

**For mars 2025.**

- Den gjør oss sammenlignbare med hovedresultatene til BCC.
- Hvert av de nyere utvalgene dekker én uke. Rangkorrelasjonen mellom dem i
  Claude.ai er 0,61 til 0,75. Ett enkelt utvalg er derfor for ustabilt, og
  de må slås sammen.

**Anbefaling.** Kiindeksen.no bør ha ett bruksmål. I dag bruker forsiden
mars 2025, Yrker alle utvalg og Utdanning februar 2026. Forsiden, Yrker og
Utdanning bør bygge på det samme målet.

1. Bruk det sammenslåtte målet fra august 2025, november 2025 og februar
   2026 i Claude.ai. Det ligger i
   `data/ai_exposure/styrk08_automation_groups.csv` og følger Anthropics
   regel. Grunnene er disse:
   - Målet beskriver bruken i 2025 og 2026. Mars 2025-målet vårt har
     rangkorrelasjon 0,12 til 0,15 med disse utvalgene.
   - Utgivelsene har antall samtaler. Yrker med færre enn 100 klassifiserte
     samtaler får en egen gruppe, «too_few». Da forsvinner problemene i
     punkt 2 og 3.
   - Målet bruker samme definisjon som Anthropic, BCC og yrkessiden. Da
     forsvinner punkt 5.
   - Forsiden, Yrker og Utdanning gir samme bilde av hvert yrke.
2. Forsiden må forklare fire følger av byttet.
   - Det blir tre like store grupper pluss «too_few», ikke fem kvintiler.
     I filen er det 97 yrker i hver gruppe og 106 i «too_few». Tre grupper
     er valgt fordi rangeringen bare er delvis stabil mellom utvalgene
     (0,61 til 0,75).
   - «Too_few» består mest av lite eksponerte yrker. 85 av de 106 ligger i
     de to laveste Eloundou-kvintilene.
   - Forsiden kan ikke lenger sammenlignes direkte med hovedresultatene til
     BCC, som bruker mars 2025. BCC bruker det sammenslåtte målet i
     appendiks F.2.
   - BCC regner Claude.ai og API sammen. Vi bruker bare Claude.ai, fordi
     automatiseringsandelen i API-et nesten ikke skiller yrker. I februar
     2026 ligger den midterste halvparten av yrkene mellom 0,84 og 1,00.

   Gruppenavnene bør si at det gjelder andel, for eksempel «lav
   automatiseringsandel» (punkt 4). Byttet flytter mange yrker. Av de 71
   yrkene i dagens Q5 havner 27 i den høyeste gruppen, 22 i midten, 16 i
   den laveste og 6 i «too_few». Av de 71 yrkene i dagens Q1 havner 41 i
   «too_few».
3. Yrkessiden kan fortsatt vise andelen per utvalg for hvert yrke.
   Dataperioden og kilden for mars 2025 må rettes uansett (punkt 1 og 6).
   Utdanning bør regne andelen per utdanning fra det sammenslåtte målet,
   ikke bare fra februar 2026.
4. Paperet kan bruke samme mål som kiindeksen. Mars 2025 kan da stå som
   kontroll for sammenlignbarhet med BCC, rettet etter punkt 2, 3 og 5.
5. Ikke bruk juni 2026-utgivelsen. Metoden er ny, og tallene kan ikke
   sammenlignes med de tidligere. Den mangler også antall samtaler, så
   tynne celler kan ikke skilles ut. Verken BCC eller vi bruker den i dag.

## Paperet (v8 og v9)

Begge versjonene bruker `styrk08_handa_mapping.csv`. Filen ble sist endret
20. juni 2026, og v8 er datert juli 2026.

Begge versjonene har delen «Automation versus Augmentation»
(`sec:results:auto_aug`). Fire elementer deler yrkene i kvintiler etter
automatiserings- og augmenteringsandel. Alle leser kvintilkolonnene i
`styrk08_handa_mapping.csv`.

| Element | Innhold | Lages av |
|---|---|---|
| Hovedtekst, `fig:handa_auto_sa` og `fig:handa_aug_sa` | Sysselsetting per kvintil og tiårig aldersgruppe, sesongjustert | `analysis/06_figures/plot_handa_decade.py` |
| Appendiks, `fig:age_by_quintile_handa_auto` og `fig:age_by_quintile_handa_aug` | De samme figurene uten sesongjustering (figur 5b og 5c) | `analysis/06_figures/plot_handa_decade.py` |
| Appendiks, `tab:did_cell_handa` | DiD på cellenivå per kvintil. Q1 er referansegruppen. | `analysis/06_figures/microdata_did_cell_handa.R` |
| Appendiks, `fig:bcc_handa` | Bruk, automatisering og augmentering, 22 til 25 år, i BCC-stil | `analysis-indiv/scripts/A1_bcc_descriptive_agg.R` |

Hovedteksten konkluderer at et eventuelt gap åpner seg der bruken ligner
automatisering, ikke augmentering. Konklusjonen hviler på dette målet.

- Punkt 2 og 3 gjelder alle fire elementene. I DiD-tabellen er Q1
  referansegruppen, og 40 av de 71 yrkene der har ukjent andel.
- Begge versjonene sier at 352 STYRK-koder er kartlagt (86,5 % dekning).
  De sier ikke at andelen er ukjent for 40 av dem.
- Punkt 5 gjelder. Teksten kaller automatisering «directive task
  delegation». Den sier ikke at feedback loop regnes som augmentering.
- Punkt 6 gjelder. Begge versjonene siterer bare Handa m.fl. (2025).
- Punkt 1 gjelder ikke. Paperet oppgir ikke dataperioden.
- Målet har rangkorrelasjon 0,12 til 0,15 med de senere Claude.ai-utvalgene
  (se «Hvilken utgivelse bør vi bruke?»).
- De sammenslåtte gruppene er allerede koblet inn i individdataanalysen
  (`analysis-indiv/scripts/1c_automation_groups.R`). De er ikke brukt i v9.

## Åpne spørsmål

- Hvor mye resultatene på forsiden endres med det sammenslåtte målet, og
  hvor mye paperets resultater endres når punkt 2 og 3 rettes. Ingen av
  delene er sjekket.
- Om nullene hos BCC skyldes filtrerte oppgaver. BCC sier det ikke.
- Hvor godt målet til BCC fra mars 2025 stemmer med nyere data. Dette er
  ikke sjekket.
- Hvilken utgivelse Stanford-dashboardet bruker. Den er ikke oppgitt.
- Hvor mye av bruddet i juni 2026 som skyldes ny kobling til oppgaver,
  og hvor mye som skyldes Cowork eller andre endringer. De publiserte
  dataene skiller ikke chat fra Cowork.
