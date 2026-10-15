# Plan: presentasjon om de nye målene fra Anthropic

15. oktober 2026

## Mål

En egen presentasjon i `slides/bruk-pipeline` om to nyere mål fra
Anthropic. Den skal vise hvordan de skiller seg fra det sammenslåtte
bruksmålet i hovedpresentasjonen.

- **Juni 2026 («Cadences»):** samme type tall som før, men laget med en ny
  metode.
- **Observed exposure (mars 2026):** et eksponeringsmål per yrke som
  kombinerer Eloundou og bruksdata.

Formen er den samme som i hovedpresentasjonen: Quarto og reveal.js,
animasjon på canvas, ett trykk per steg, presentatørnotater, data fra et
byggeskript med kontroller, og en README. Motoren og stilen deles med
hovedpresentasjonen. Filen kan hete `nye-maal.qmd`.

Eksempelet er informasjonsrådgivere (STYRK 2432) også her, slik at
publikum kan sammenligne med hovedpresentasjonen.

## Animasjon 1: juni 2026

Hovedpoenget er at juni 2026 er et brudd i serien, ikke en ny måling av
det samme.

| Trykk | Overskrift | Innhold |
|---|---|---|
| 0 | Hva er nytt | Tidslinjen fra hovedpresentasjonen, med juni 2026 uthevet. Månedlige tall for april og mai 2026. Claude chat og Cowork sammen. Ingen antall samtaler. Alle verdier avrundet til to desimaler. |
| 1 | Ny kobling til oppgaver | To diagrammer ved siden av hverandre. Før: et tre med kategorier laget for hånd. Nå: først en detaljert arbeidsaktivitet (DWA), så en oppgave innenfor den. Har flere oppgaver like høy sikkerhet, trekkes én tilfeldig. |
| 2 | Ny oppgaveliste | O*NET 30.2 fra februar 2026. 415 av 2 400 oppgavetekster i april finnes ikke i O*NET-listen vår. De faller ut av kjeden. |
| 3 | Eksempelet | Informasjonsrådgivere: 11 av 18 oppgaver har samtaler i februar 2026, mot 7 av 18 i april og i mai 2026. Andelen går fra 0,305 til 0,395 og 0,413. |
| 4 | Samme oppgave, ny andel | Rangkorrelasjon for samme oppgave: 0,83 mellom november 2025 og februar 2026. 0,45 til 0,46 mellom februar og april eller mai 2026. 0,91 mellom april og mai 2026. |
| 5 | Yrkene stokkes om | Rangkorrelasjon per yrke: 0,62 med gammel metode, 0,09 til 0,11 mellom gammel og ny, 0,89 innen ny. Elektrikere går fra 0,569 i februar til 0,867 i april og 0,884 i mai. |
| 6 | Vektene mangler | Oppgavens andel av all bruk er 0,00 for 1 304 av 2 410 oppgaver i april. Med bruksvekter gir kjeden 256 yrker i april. Med lik vekt per oppgave gir den 325. Februar 2026 ga 319. |
| 7 | Hva vi gjør | Juni 2026 slås ikke sammen med de tidligere utgivelsene. Skal den brukes, blir den en ny serie med egen kobling fra O*NET 30.2 til STYRK-08. |

Notatene til trykk 4 og 5 forklarer tabellen under. Den skiller mellom to
grunner til avviket.

| Sammenligning | Samme oppgave | Yrker, alle oppgaver | Yrker, felles oppgaver |
|---|---|---|---|
| Nov. 2025 mot feb. 2026 (gammel metode) | 0,83 | 0,62 | 0,74 |
| Feb. 2026 mot april og mai 2026 | 0,45 til 0,46 | 0,09 til 0,11 | 0,36 til 0,39 |
| April mot mai 2026 (ny metode) | 0,91 | 0,89 | 0,95 |

Én grunn er at samme oppgave får en annen andel. Den andre er at andre
oppgaver får samtalene. Regnes yrkene bare på felles oppgaver, stiger
korrelasjonen fra rundt 0,1 til rundt 0,37. Yrkestallene i tabellen er
regnet med lik vekt per oppgave og per SOC-yrke.

Notatene må også si to ting. Appendikset til «Cadences» sier ikke om
klassifiseringen av de fem mønstrene er endret. De publiserte dataene
skiller ikke chat fra Cowork. Vi kan derfor ikke si hvor mye av bruddet
som kommer av hver endring.

## Animasjon 2: observed exposure

Hovedpoenget er at observed exposure spør om noe annet enn
automatiseringsandelen. Observed exposure måler hvor stor del av jobben
som ser bruk som ligner automatisering. Automatiseringsandelen måler hvordan
Claude brukes på det som brukes.

| Trykk | Overskrift | Innhold |
|---|---|---|
| 0 | Spørsmålet | Massenkoff og McCrory (2026), publisert 5. mars 2026. Av oppgavene en språkmodell kan gjøre raskere, hvilke ser faktisk automatisert bruk i arbeid? |
| 1 | Tre kilder | O*NET-oppgavene, Eloundou-vurderingen per oppgave og bruksdata fra utgivelsene for august og november 2025. |
| 2 | Når er en oppgave dekket? | Eloundou må si at oppgaven kan gjøres minst dobbelt så raskt (β = 0,5 eller 1). Oppgaven må også ha nok arbeidsrelatert bruk. |
| 3 | Hvordan bruken teller | Automatisert bruk teller fullt. Bruk som ligner augmentering, teller halvt. Bruk gjennom API-et trekker opp. |
| 4 | Fra oppgave til yrke | Snitt over oppgavene, vektet med hvor stor del av arbeidstiden hver oppgave tar. Informasjonsrådgivere får 0,453. 16 av de 18 oppgavene finnes i Anthropics oppgavefil, og 7 av dem har dekning over 0. |
| 5 | Fra SOC til STYRK | Anthropic oppgir målet per yrke på SOC 2018. Kjeden er SOC 2018, SOC 2010, ISCO-08 og STYRK-08, som for Eloundou. 388 STYRK-koder får verdi. |
| 6 | Mange nuller | 129 av 388 STYRK-koder har verdi 0. Alle 78 i laveste kvintil og 51 av 77 i nest laveste har 0. Kvintilgrensen mellom dem avgjøres da av kodenummeret. |
| 7 | Mot de andre målene | Rangkorrelasjon over 331 yrker: 0,75 mot Eloundou, 0,69 mot bruksandelen og 0,03 mot den sammenslåtte automatiseringsandelen. |
| 8 | Eksempler | Tabellen under. |
| 9 | To ulike spørsmål | Observed exposure ligger nær Eloundou og bruksandelen. Automatiseringsandelen henger nesten ikke sammen med noen av dem. |

Tabell til trykk 8:

| Yrke | Observed exposure | Kvintil | Eloundou | Automatiseringsandel, sammenslått | Gruppe |
|---|---|---|---|---|---|
| Informasjonsrådgivere (2432) | 0,453 | 5 | 0,591 | 0,347 | lav |
| Programvareutviklere (2512) | 0,404 | 5 | 0,873 | 0,665 | høy |
| Kundesentermedarbeidere (4222) | 0,567 | 5 | 0,551 | 0,534 | høy |
| Elektrikere (7411) | 0 | 1 | 0,128 | 0,506 | middels |
| Butikkmedarbeidere (5223) | 0,161 | 4 | 0,342 | 0,516 | høy |
| Farmasøyter (2262) | 0,090 | 4 | 0,429 | 0,223 | lav |

Elektrikere er det tydeligste eksempelet. De har 1 083 klassifiserte
samtaler i de tre utvalgene, og over halvparten ligner automatisering. Likevel
er observed exposure 0. Hvorfor er ikke sjekket. Det kan skyldes
Eloundou-vurderingen eller kravet om arbeidsrelatert bruk.

Paperet (v9) bruker kvintilene til observed exposure som et av
kontrollmålene. Trykk 6 viser at laveste kvintil der bare består av yrker
med 0.

## Data: `build_data_nye.py`

Skriptet skriver `data/nye-maal.js`.

Juni 2026:

- Filen fra Anthropic er 219 MB. Før presentasjonen bygges, bør
  `analysis/03_mappings/extract_aei_release_slices.py` utvides til å lagre
  mønstrene per oppgave, globalt for Claude.ai, i
  `data/ai_exposure/handa/aei_releases/`. Da leser byggeskriptet en liten
  fil lokalt.
- O*NET-listen og kodekjeden hentes fra
  `analysis/03_mappings/build_aei_collaboration_mapping.py`, som i
  hovedpresentasjonen.

Observed exposure:

- `data/ai_exposure/handa/job_exposure.csv` (756 SOC-yrker) og
  `task_penetration.csv` (17 998 oppgaver). Begge er identiske med
  `labor_market_impacts/` i Anthropics datasett på Hugging Face. Det er
  sjekket med md5-sum for `job_exposure.csv`.
- `data/ai_exposure/styrk08_job_exposure_mapping.csv`, laget av
  `analysis/03_mappings/build_job_exposure_mapping.py`.

Kontroller:

- Rangkorrelasjonene i trykk 4, 5 og 7 regnes på nytt og skal stemme med
  tallene over.
- 0,453 for informasjonsrådgivere er lik verdien for SOC 27-3031 i
  `job_exposure.csv`.
- Antall nuller og kvintilstørrelser stemmer med mappingfilen.

## Kilder for tekstene

- Appendikset til «Cadences», kapittel 1: endringene i juni 2026.
- Dokumentasjonen til juni-utgivelsen på Hugging Face: april og mai 2026,
  avrunding og hvilke tall som finnes.
- Massenkoff og McCrory (2026), «Labor market impacts of AI: A new measure
  and early evidence»:
  `literature/llm-selskapsrapporter/Anthropic 2026-03 Labor market impacts of AI-new measure and early evidence.pdf`.

## Ikke sjekket

- Hva «nok arbeidsrelatert bruk» betyr i tall. Det står i appendikset til
  Massenkoff og McCrory, som ikke ligger i repoet.
- Hvor mye API-bruk teller i observed exposure.
- Om 0,453 kan regnes ut fra oppgavene. Tidsandelene per oppgave er ikke
  funnet i repoet.
- Hvorfor elektrikere får observed exposure 0.
- Hvor mye av bruddet i juni 2026 som kommer av ny kobling til oppgaver,
  og hvor mye som kommer av Cowork.
