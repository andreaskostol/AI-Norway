# AI-Norway

Replikasjon og utvidelse av Brynjolfsson et al. (2025) med norske registerdata fra microdata.no.
Bruker A-ordningen 2015–2025 for å dokumentere alderdifferensierte sysselsettings- og lønnsmønstre i yrker eksponert for AI.

**Arbeidstittel:** *AI Exposure and Age-Differentiated Employment: Evidence from Norwegian Register Data*

Det offentlige dashbordet finnes på **[kiindeksen.no](https://kiindeksen.no)** (norsk) og **[kiindeksen.no/en](https://kiindeksen.no/en/)** (English). Kildekoden ligger i `dashboard/site/`.

> **English:** Code, dashboard and paper sources for *The AI Labor Market Index* ([kiindeksen.no](https://kiindeksen.no/en/)), tracking AI exposure and age-differentiated employment in Norway. The register-derived data tables are **not** included in this public repository — see *Data* below.

## Mappestruktur

```
paper/              LaTeX-paper (main.tex er hoveddokument)
microdata-scripts/
  monthly/          Aktive microdata.no-scripts for månedlig datauttrekk
  monthly/archive/  Eldre/erstattede versjoner
  adhoc/            Hjelpescripts (pdf_to_markdown.py)
  adhoc/archive/    Engangs-/verifikasjonsscripts
  library/          Gjenbrukbare fragmenter (f.eks. AI-eksponering recode)
  docs/             microdata.no-syntaks og variabeloversikt
microdata-output/   Rå/parsede CSV-eksport fra microdata.no
                    (IKKE inkludert i public repo — se «Data» nedenfor)
data/
  ai_exposure/      AI-eksponeringsindekser (DAIOE, Eloundou, Felten, Handa),
                    STYRK-08 ↔ ISCO/SOC crosswalks, og docs/ med mapping-metode
  macro/            Makrokontekst (NAV, SSB, Norges Bank)
analysis/
  01_generate/      Generer microdata-scripts fra mal
  02_parse/         Parse rå microdata-output til long-format CSV
  03_mappings/      Bygg AI-eksponeringsmappinger (Eloundou, Felten, Handa)
  04_timeseries/    Bygg månedlige tidsserier
  05_tables/        Lag LaTeX-tabeller
  06_figures/       Lag figurer (én plot_*.py per tema)
  output/figures/   Genererte figurer (PDF)
  output/tables/    Genererte LaTeX-tabeller
  requirements.txt
dashboard/          Offentlig dashbord (kiindeksen.no)
  site/public/      Statisk nettsted (NO: index.html, EN: en/) + app.js
  build_release.py  Bygg månedlig datarelease for dashbordet
literature/         Referansepapere (ikke tracket i git pga. opphavsrett)
```

## Workflow for datauttrekk

microdata.no kjører ikke lokalt — scripts limes inn i nettleseren:

1. Rediger eller generer `.mdata`-script i `microdata-scripts/monthly/`
2. Kopier til utklippstavle: `cat script.mdata | clip`
3. Lim inn på https://microdata.no, kjør
4. "Eksporter skriptresultatene" → "Kopier til utklippstavlen" → lim inn i `microdata-output/<navn>_raw.csv`
5. Parse: `python analysis/02_parse/parse_microdata_output.py input_raw.csv output_parsed.csv`
6. Bygg tidsserier og figurer med scriptene i `analysis/04_timeseries/`, `analysis/05_tables/` og `analysis/06_figures/`

Se [microdata-scripts/docs/verifisert_syntaks.md](microdata-scripts/docs/verifisert_syntaks.md) for microdata.no-språkreferanse
og [microdata-scripts/docs/variable_dictionary.md](microdata-scripts/docs/variable_dictionary.md) for variabeldefinisjoner.
AI-eksponerings-mappingen er dokumentert i [data/ai_exposure/docs/](data/ai_exposure/docs/).

## Konvensjoner

- **Filnavn:** `{nr}_{innhold}_{periode}` — f.eks. `02_lonn_agemonth_2021_2025`
- **Aldersgrupper** defineres i microdata.no-scriptet (ikke lokalt) for å unngå tomme celler
- **AI-kvartiler** tildeles lokalt i Python, ikke i microdata.no
- **Rå CSV-er** i `microdata-output/*_raw.csv` skal aldri redigeres
- microdata.no bruker enkle anførselstegn for kategoriske verdier (`'fast'`, ikke `1`)
- Bruk alltid siste FDB-versjon: `require no.ssb.fdb:NN as db`

## Bygge paperet

```
cd paper
latexmk -pdf main.tex
```

Hovedfilen er [paper/main.tex](paper/main.tex). Seksjonsfilene (`section1_*.tex` til `section7_*.tex`) inkluderes derfra.

## Data

Eksterne referansedata ligger i repoet: AI-eksponering (Eloundou, Felten, Handa/DAIOE), STYRK-08 ↔ ISCO/SOC-crosswalks (`data/ai_exposure/`) og makrokontekst fra SSB/NAV/Norges Bank (`data/macro/`).

De **registeravledede** tabellene — månedlige uttrekk i `microdata-output/` og aggregerte tidsserier `data/NN_*.csv` — er **ikke inkludert** i dette offentlige repoet (størrelse og konfidensialitet). De aggregerte seriene som driver dashbordet kan lastes ned på [kiindeksen.no](https://kiindeksen.no/#data). Individdata fra sikker server publiseres ikke. Ta kontakt for replikasjonsdata.

## Forfattere

Øystein Hernæs (Frischsenteret) og Andreas R. Kostøl (Handelshøyskolen BI). Kontakt: andreas.r.kostol@bi.no

## Referanser

Hovedreferanse: Brynjolfsson, Chandar & Chen (2025), *Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of Artificial Intelligence*.
