# Ledige stillinger fra NAV, per STYRK-08

Datakontrakt for «sammenlign arbeidsmarkedet» på kiindeksen.no/yrker.html.
Mappa ligger i Dropbox-repoet, så den agenten som samler inn (Mac Mini) og
den som bygger nettsiden ser de samme filene. Alt her er åpne data fra
arbeidsplassen.nav.no.

## Hvem gjør hva

- **Innsamling** (Mac Mini-agenten, eller hvem som helst med mappa):
  `python dashboard/collect_nav_vacancies.py` én gang i uka, gjerne mandag.
  Skriptet henter alle åpne annonser fylke for fylke fra
  `https://arbeidsplassen.nav.no/stillinger/api/search`, dedupliserer på uuid,
  kobler STYRK-08-navnene i `categoryList` til firesifret kode via
  `data/ai_exposure/styrk08_codes.csv`, og skriver ett øyeblikksbilde. Deretter
  bygger det serien på nytt fra alle øyeblikksbildene på disk.
- **Nettsiden** (`dashboard/site/prepare_panels.py`, `build_vacancies()`): leser
  `nav_vacancies_by_styrk.csv` og skriver `public/data/vacancies.json`. Panelet
  viser stillingsfiguren bare når filen finnes.

Agenten trenger ikke bruke skriptet. Det holder å levere filer i formatet
under, i denne mappa.

## Filer

`snapshots/nav_ads_YYYY-MM-DD.csv`, én rad per annonse:

| kolonne | innhold |
|---|---|
| uuid | annonse-id fra NAV |
| published, expires | dato (YYYY-MM-DD) |
| county | fylke (første i `locationList`) |
| sector | Privat / Offentlig / Ikke oppgitt |
| positioncount | antall stillinger i annonsen (tom = 1) |
| styrk08 | firesifrede koder, `;`-skilt (en annonse kan ha flere) |
| styrk_names | NAVs STYRK-08-navn, `;`-skilt |
| title | annonsetittel |

`nav_vacancies_by_styrk.csv`, én rad per øyeblikksbilde × yrke (det nettsiden
leser):

| kolonne | innhold |
|---|---|
| snapshot_date | YYYY-MM-DD |
| styrk08 | firesifret kode |
| n_ads | åpne annonser som lister yrket |
| n_positions | sum av positioncount |
| n_ads_new7d | annonser publisert de siste 7 dagene før øyeblikksbildet |

`nav_vacancies_totals.csv`: `snapshot_date, n_ads_unique, n_ads_mapped,
n_styrk_codes`. `unmapped_names.csv`: STYRK-navn koblingen ikke fant, med
antall annonser, for manuell oppfølging.

## Takt mot NAV

NAV svarer 429 (Too Many Requests) og blokkerer adressen i over ti minutter
etter om lag 120 forespørsler på få minutter, uansett user agent. Skriptet
venter 3 sekunder mellom forespørsler som standard (`--sleep`), og en full
kjøring tar da rundt sju minutter. Ikke kjør det oftere enn ukentlig, og ikke
parallelt med andre spørringer mot samme API fra samme maskin.

## Forbehold

- Beholdning av åpne annonser, ikke tilgang. `n_ads_new7d` er nærmeste
  strømmål.
- En annonse teller i hvert yrke den lister. Summen over yrker overstiger
  antall annonser.
- Kun arbeidsplassen.nav.no. Annonser som bare ligger hos Finn eller hos
  arbeidsgiver er ikke med.
- Serien starter 2026-09-07. Et eldre uttrekk (15. juni 2026, i
  `AI-research/analysis/nav/`) er avkortet til 10 000 annonser og er derfor
  ikke tatt inn.
