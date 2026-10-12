# KI-geriljaen 6. oktober 2026

HTML-deck til websamlingen i KI-geriljaen (Teams, 14:00–15:00). Tittel:
«KI forandrer stigen: hva skjer med inngangen til arbeidslivet?». Data til og
med juli 2026 fra release 2026-10, den samme som ligger på kiindeksen.no.

## Filen som skal brukes

`dist/ki-geriljaen_2026-10-06.html`. Selvstendig, trenger bare en nettleser.
Åpne i Chrome, trykk F for fullskjerm.

Taster: pil høyre eller mellomrom går ett trykk fram (fragmenter og
animasjoner først, så neste lysbilde). Pil venstre går tilbake. N åpner
talenotatene. Home og End hopper til start og slutt. `#s12.4` i adressen
åpner lysbilde 12 på trykk 4.

## Oppbygging

| Del | Lysbilder | Innhold |
|---|---|---|
| Åpning | 1–4 | Tittel, presseveggen, spørsmålet fra Arendalsgata, tre svar |
| Rammeverk | 5–8 | Fire animasjoner: oppgavebunten, brukerkostnad og terskel, tre krefter, stigen |
| Måling | 9–15 | Eloundou steg for steg, informasjonsrådgivere som regneeksempel, tre yrker med Anthropic-bruk, Claude Code, Mouchel, hantelfiguren |
| Data | 16–22 | Fire steg, alle aldre, etter alder, unge, utviklere, fire yrkescase, alle spesifikasjoner |
| Avslutning | 23–27 | Andre land, ser og ser ikke, politikk og råd, kiindeksen.no |

Sporet følger Øystein Hernæs' deck fra Arendalsgata 13. august 2026
(`slides/arendalsgata/`), med rammeverket fra `AI-research/comparative
advantage/conceptual-framework.tex` lagt inn foran, og to referansepunkter på
datasidene: ChatGPT (oktober 2022 = 100) og agentisk KI (januar 2025 = 100).
Datasidene 16, 17, 19 og 20 bytter referanse på ett trykk.

## Bygge på nytt

```
python3 build_figures.py   # SVG-figurer og figures/numbers.json fra dashboard.json
python3 build_deck.py      # deck.html + figurer + bilder -> dist/
```

Alle tall på lysbildene kommer fra `figures/numbers.json` gjennom
plassholdere `{{n:...}}` i `deck.html`. Hovedtallet regnes som på
kiindeksen.no: etterslepende tremåneders snitt, referansemåned mot siste
måned, relativ vekst Q5 mot Q1. Standardfeilene leses fra
`analysis/output/coefficients/coef_recursive_kiindeks_headline*.csv`.

Tall som ikke kommer fra numbers.json, og hvor de er lest:

- Eloundou-metoden (923 yrker, 19 265 oppgaver, 397 av 407 koder, grupper på
  80/79/79/79/80, 99,8 prosent dekning): `slides/aid-presentasjon/_variables.yml`.
- Informasjonsrådgivere (18 oppgaver, 19,5 av 33, 0,591, uvektet 0,583):
  samme fil og `slides/arendalsgata/03_maling.tex`.
- Mouchel (18 796 par, sju modeller, 30 000 artikler, 24 000 sammendrag,
  r 0,92, ρ 0,94, 66 og 99 prosent, 0,705 og 0,742): `_variables.yml` og
  `modules/data/mapping-mouchel.js`. Temperatur 20 og 1,6 prosent og 72
  prosent: artikkelens sammendrag og innledning (arXiv 2605.15474).
- Lindenlaub mfl. R²: `_variables.yml` (lorv).
- Anthropic-bruk per oppgave: `data/ai_exposure/styrk08_aei_tasks.csv`,
  1P API, 2026-02-05. Utviklere 15,9 prosent samlet, 8,7 på én oppgave,
  kundesenter 0,7, elektrikere 0,1.
- Andre land: `slides/aid-presentasjon/litteratur_tall.yml`, kontrollert av
  Hernæs 3. oktober 2026.
- METR (dobling hver fjerde måned siden 2023): `_variables.yml` (metr).

## Bilder

`img/presse_*.jpg` er kopiert fra AID-dekket. `img/kiindeksen_2026-10-05.png`
er et skjermbilde av forsiden tatt 5. oktober 2026 etter at release 2026-10
gikk live. `figures/occ_exposure_no.svg` er konvertert fra edutech-dekkets
`figure_occ_exposure_no.pdf` med pdftocairo.
