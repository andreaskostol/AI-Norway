# mapping-pipeline

Quarto-presentasjon (reveal.js) som viser hvordan en eksponeringsskår går fra O*NET-oppgaver til norske STYRK-08-yrker. Det er to animasjoner med samme stil som `data-pipeline`: én for Eloundou mfl. (2024) og én for Mouchel mfl. (2026). Hvert trykk er ett steg, og tabeller, koder og prikker går over i hverandre.

## Åpne og redigere

1. Åpne mappen `slides/mapping-pipeline` i VS Code.
2. Åpne `mapping-pipeline.qmd`.
3. Trykk **Preview**-knappen øverst til høyre, eller Ctrl+Shift+K.

Den ferdige filen `mapping-pipeline.html` ligger i samme mappe. Den er selvstendig og trenger bare Chrome, Edge eller Firefox. Pil høyre, mellomrom eller en presentasjonsklikker går ett steg frem. Tasten S åpner presentatørvisning med notater.

## Tekstene

Overskrift og ingress for hvert steg står i listen `STEPS` i `mapping.js`. Et linjeskift i ingressen skrives som `
` og blir et linjeskift på sliden. Eksempelkortet øverst til høyre styres av `tag` i hvert steg. Informasjonsrådgivere står på kortet i stegene som følger eksempelet fra oppgaver til kode (Eloundou trykk 1 til 5, Mouchel trykk 2 og 3). Kortet viser STYRK-koden først når kjeden er forklart. Kortet bytter til elektrikere og ledere i Eloundou trykk 6 og til de fire unntakene i trykk 7. Etter det er eksempelet markert med ring og navn på prikken, og med farget rad i tabellen.

Forkortelsene forklares første gang de brukes. O*NET står i ingressen i Eloundou trykk 0 og i boksen i Mouchel trykk 0. SOC, ISCO-08, STYRK-08 og BLS står i en liste under kodekjeden (`ACR` i `mapping.js`) i Eloundou trykk 5 og Mouchel trykk 3. Pilene i kjeden sier hva hver kobling gjør. β forklares i Eloundou trykk 3.

Radene i resultattabellene er sortert med høyeste skår først. Sorteringen gjøres i `build_data.py`.

## Oppdatere data

Dobbeltklikk `oppdater-data.bat`. Skriptet `build_data.py` leser prosjektfilene og skriver `data/mapping-eloundou.js` og `data/mapping-mouchel.js`. Deretter bygger du HTML-filen på nytt med Preview-knappen. Skriptet sjekker at oppgavene for eksempelyrket gir det publiserte skåren, og at gjennomsnittet i delingseksempelet stemmer med mappingfilen.

## Stegene

| Slide | Trykk | Hva skjer |
|---|---|---|
| Eloundou | 0 | O*NET: datasett fra US Department of Labor med 923 yrker og 19 265 oppgaver |
| | 1 | O*NET-oppgavene for informasjonsrådgivere, med type kjerne eller tillegg |
| | 2 | GPT-4s vurdering E0, E1 eller E2 for hver oppgave. Menneskelige vurderere nevnes |
| | 3 | Hver vurdering får et poeng β: 0, 1 eller 0,5 |
| | 4 | Vektene 2 og 1, og det veide snittet 19,5 / 33 = 0,591 |
| | 5 | Tallet flyr inn i kodekjeden O*NET, SOC 2018, SOC 2010, ISCO-08 og STYRK-08 |
| | 6 | Flere blir én (elektrikere, snitt) og én blir flere (ledere, kopi til sju koder med kort tittel) |
| | 7 | Fire norske unntak: to kopier og to direkte fra SOC |
| | 8 | 397 prikker i kodens rekkefølge |
| | 9 | Prikkene rangeres og deles i fem like store grupper |
| | 10 | Resultattabell for seks yrker |
| Mouchel | 0 | Oppgaver, grunnlag, sju modeller og utfallet E0 til E3 |
| | 1 | Rubrikken med poeng. E3 gjelder bilde og video |
| | 2 | Skår for informasjonsrådgivere: Eloundou, A1 og S0 |
| | 3 | Samme kodekjede som for Eloundou, med forklaring av SOC 2010 og reglene under |
| | 4 | 397 prikker i kodens rekkefølge, på A1 |
| | 5 | Rangert og delt i fem grupper |
| | 6 | Spredningsdiagram mot Eloundou, med korrelasjoner og de fire største flytterne |
| | 7 | Resultattabell med Eloundou, A1 og S0 |

## Hva tallene bygger på

- Tallene 923 yrker og 19 265 oppgaver er regnet ut av `build_data.py` fra `data/ai_exposure/eloundou/full_labelset.tsv`. Eloundou mfl. skriver at O*NET 27.2 har 1 016 yrker og at 923 har oppgaveinformasjon (artikkelen og tillegget i `literature/`). Der står også at forfatterne og innleide vurderere merket oppgavene for hånd, i tillegg til GPT-4.
- Oppgavene og vurderingene for eksempelet: samme fil. De 18 oppgavene gir 19,5 / 33 = 0,590909, som er skåren i den publiserte yrkesfilen. Uvektet snitt er 0,583.
- SOC 2010 trengs fordi O*NET-filen bruker SOC 2018, mens BLS-tabellen mot ISCO-08 (`isco_soc_crosswalk.xls`, august 2012, oppdatert juni 2015) er laget for SOC 2010. Overgangen fra 2018 til 2010 bruker BLS-tabellen fra november 2017.
- Kjeden og reglene: de samme som i `analysis/03_mappings/build_eloundou_mapping.py` og `build_mouchel_mapping.py`. Antall koder i hver ledd (923, 798, 778, 430 og 397) er regnet ut av `build_data.py`.
- Gruppene: like mange yrker i hver gruppe (80, 79, 79, 79 og 80), med lik skår rangert etter kode. Filene `styrk08_eloundou_beta_mapping.csv` og `styrk08_mouchel_mapping.csv` er kilden for skår og grupper.
- Mouchel: tallene om sju modeller, ca. 30 000 nyhetsartikler og ca. 24 000 sammendrag står i `replication/mouchel_exposure/README.md` og i GitHub-utgaven (29 857 artikler og 23 669 sammendrag, juli 2026). Artikkelversjonen i `literature/` oppgir over 34 000 artikler, 19 000 sammendrag og tre modeller, og nevner ikke A1 og S0. Sliden viser ikke antall oppgave-yrke-par (18 796 i O*NET 30.2), fordi Eloundou bruker O*NET 27.2 med 19 265 oppgaver og tallene ville forvirret. Filen i repoet har bare yrkesskår, så animasjonen viser ikke Mouchels vurdering av enkeltoppgaver.
- Korrelasjonene mellom Mouchel A1 og Eloundou er regnet av `build_data.py`: 0,921 (Pearson), 0,943 (Spearman), 66,0 prosent i samme gruppe og 98,7 prosent innen én gruppe.

## Ikke sjekket

- Animasjonene er testet i nettleserpanelet i Claude, ikke på en annen maskin.
- Mellomrammene i overgangene er sett som stillbilder.
- De norske kortnavnene på de 18 oppgavene er skrevet for hånd, med utgangspunkt i SAM-presentasjonen. De er ikke en offisiell oversettelse.
- De korte titlene på de sju kodene i delingseksempelet (`SHORT_FAN` i `build_data.py`) er også skrevet for hånd. De er forkortinger av de offisielle STYRK-navnene.
