# SSBmikrodata — AI og arbeidsmarked i Norge

Norsk replikasjon av Brynjolfsson et al. (2025), Humlum & Vestergaard (2026) og Lodefalk et al. (2026).
Bruker microdata.no for månedlige arbeidsmarkedsdata fra A-ordningen (2015–2025).

## microdata.no scriptspråk
- Eget Stata-lignende språk — IKKE Stata, IKKE Python
- Scripts kan IKKE kjøres lokalt — limes inn i nettleseren på microdata.no
- Ingen `//` kommentarer — gir feil
- Versjonsnummer obligatorisk: `require no.ssb.fdb:52 as db` — bruk alltid **siste versjon** for å få med nyeste data. Sjekk på https://microdata.no/discovery/dataStore/no.ssb.fdb
- ARBLONN statusdato: den **16. i måneden**
- Kategoriske verdier: enkle anførselstegn (`'fast'`, ikke `1`)
- Se `microdata-scripts/docs/verifisert_syntaks.md` for komplett referanse

## Mappestruktur
```
microdata-scripts/
  monthly/            Aktive .mdata-scripts for datauttrekk (01_count, 02_wage)
  adhoc/              pdf_to_markdown.py + adhoc/archive/ med engangsscripts
  library/            Gjenbrukbare fragmenter (AI-recode etc.)
microdata-output/
  *_raw.csv           Rå eksport fra microdata.no (copy-paste)
  *_parsed.csv        Parsert til long-format CSV
data/
  ai_exposure/        DAIOE-indeks, Eloundou, STYRK-08 crosswalks
  macro/              Bl.a. ssb_population_by_age_quarterly.csv (nevner for sysselsettingsrater per 1-årig alder)
analysis/
  01_generate/        Generer microdata-scripts
  02_parse/           Parse rå microdata-output
  03_mappings/        Bygg AI-eksponeringsmappinger
  04_timeseries/      Bygg månedlige tidsserier
  05_tables/          Lag LaTeX-tabeller
  06_figures/         Lag figurer (plot_*.py)
  output/             Genererte figurer og tabeller
literature/
  *.pdf               Referansepapere
  summaries/          Oppsummeringer og sammenligning
```

## Konvensjoner
- Filnavn output: `{nr}_{innhold}_{periode}.csv` — f.eks. `01_occ_age_count_2016_2020.csv`
- Scripts: `{nr}_{innhold}_{periode}.mdata` — f.eks. `01_yrke4_aldersgruppe_2016_2020.mdata`
- AI-kvartiler tildeles lokalt i Python, ikke i microdata.no
- Aldersgrupper defineres **i microdata.no-scriptet** (ikke lokalt) for å unngå for mange tomme celler ved eksport
- Aldersgrupper: 0=missing, 1=≤21, 2=22-25, 3=26-30, 4=31-34, 5=35-40, 6=41-49, 7=50-59, 8=60-69, 9=70+

## Workflow
1. Generer/oppdater .mdata-script → `cat script.mdata | clip`
2. Lim inn i microdata.no, kjør
3. "Eksporter skriptresultatene" → "Kopier til utklippstavlen" → lim inn i fil
4. Lagre rå output i `microdata-output/`
5. Parse med `python analysis/02_parse/parse_microdata_output.py input.csv output_parsed.csv`
6. Analyser lokalt

## Git og commits
- Repoet er på privat GitHub. Hovedbranch: `main`. Commit ofte med beskrivende meldinger.
- **Små endringer (få linjer, opplagte rettelser):** commit automatisk uten å spørre, med en kort, presis melding.
- **Store endringer (>~30 linjer i én fil, sletting av innhold, omskriving av seksjon):** vis diff og be om OK før commit.
- Aldri `git push --force`, `git reset --hard`, `git rebase`, `git commit --amend` uten eksplisitt instruks.
- Ved merge conflict: løs den selv hvis den er triviell, ellers vis konflikten og spør.
- Rå CSV-er i `microdata-output/*_raw.csv` er read-only og må ikke endres.

## Pakkeinstallasjoner og nedlasting av kjørbar kode
Claude kjører i bypass-modus, så disse reglene er bindende for å unngå supply chain-angrep.

**`pip install` (og tilsvarende for npm, uv, cargo, yarn):**
- Installer uten å spørre *kun* hvis pakken er åpenbart veletablert
  (pandas, numpy, matplotlib, scipy, openpyxl, requests, beautifulsoup4, lxml,
  pyyaml, jinja2, click, tqdm, pytest og tilsvarende kjerneøkosystem-pakker)
- For alle andre pakker: stopp og spør først. Oppgi pakkenavn, hvorfor denne
  pakken velges, og nevn alternativer hvis relevant.
- Verifiser kanonisk stavemåte før install. I tvil → spør, ikke gjett.
- En pakke du skal oppgradere er ikke "kjent trygg" bare fordi navnet er det —
  nyeste versjon kan være kompromittert. Spør før `--upgrade` på kritiske pakker.

**Alltid spør først, uansett kontekst:**
- `curl ... | sh`, `wget ... | bash` og alle varianter av pipe-til-shell
- `git clone` av ukjente repo *etterfulgt av kjøring* av noe fra klonen
  (klonen i seg selv er trygg; kjøring fra den er ikke)
- `python setup.py install` eller `pip install .` fra et klonet repo
- Installasjon av binærfiler fra tilfeldige URL-er

**Ren datanedlasting er greit** (`curl`, `wget`, `WebFetch`, `WebSearch` osv.)
så lenge filen bare leses/parses, ikke kjøres.

## Ikke track i git
- `literature/**/*.pdf` og `literature/**/*.md` — opphavsrett / parsed innhold
- LaTeX-byggartefakter (`*.aux`, `*.log` osv.)
- Python `__pycache__/`, `.venv/`
