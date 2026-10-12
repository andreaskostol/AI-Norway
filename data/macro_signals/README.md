# Norske løpende serier for KI-signaler

Datagrunnlag for `MACRO-AI-SIGNALS-PLAN.md`, Del B. Seriene testes for trendbrudd i november 2022 og
februar 2025 med `analysis/09_macro_signals/run_all.py`. Figurer og samletabell ligger i
`analysis/output/macro_signals/`. Funnene står i `exploration/macro_signals_norway_2026.md`.

Alle filer er hentet 2026-10-08. Hver CSV har en `_meta_*.json` med kilde, URL, hentet dato og filter.
Råsvar ligger i `raw/<kilde>/`. Den fulle filen fra Enhetsregisteret er ikke lagret (ca. 150 MB).
Et slankt uttrekk ligger i `raw/brreg/` og er utenfor git.

## Filer

| Fil | Kilde | Frekvens og periode | Hentescript | Merknad |
|---|---|---|---|---|
| `github_innovation_graph.csv` | GitHub Innovation Graph, CC0 | Kvartal, 2020K1–2026K1 | `fetch_github_innovation_graph.py` | Norge, USA, Sverige, Danmark, Finland, EU. Git pushes er strøm. Repoer, utviklere og organisasjoner er bestander, så nye enheter regnes som endring i bestand |
| `github_orgs.csv` | GitHub REST og GraphQL API | Måned, 2016-01–2026-09 | `fetch_github_orgs.py` | Commits, PR-er (alle, uten avhengighetsboter, flettede, Copilot-agent) og nye repoer per org. Bare offentlige repoer. Commits for navikt er talt med commit-søk, for de andre org-ene med GraphQL-historikk per repo. For Skatteetaten ga de to metodene like tall hvert år 2016–2026 |
| `norid_new_domains.csv` | Norid, nøkkeltall | Måned, 2000-01–2026-09 | `fetch_norid.py` | Nyregistrerte domenenavn. Norid nevner regelendringer i 2001, 2004 og 2014 |
| `ssb_08076_nye_foretak.csv` | SSB tabell 08076 | Kvartal, 2008K1–2026K2 | `fetch_ssb.py` | Nye foretak, SN2007. Alle næringer og NACE 58, 62, 63, alle organisasjonsformer |
| `brreg_registrations.csv` | Enhetsregisteret, full nedlasting | Måned, 2008-01–2026-09 | `fetch_brreg.py` | Bare enheter som finnes i dag. Slettede enheter mangler, så eldre kohorter er undertalt |
| `openalex_norway.csv` | OpenAlex | Måned, 2015-01–2026-09 | `fetch_openalex.py` | Verk med minst én norsk institusjon, etter type og fagfelt. Verk datert 1. januar er talt for seg |
| `clinicaltrials_norway.csv` | ClinicalTrials.gov API v2 | Måned, 2014-01–2026-09 | `fetch_clinicaltrials.py` | Studier med studiested i Norge, etter startdato og etter første innsending |
| `ssb_10990_patentsoknader.csv`, `ssb_10991_designsoknader.csv`, `ssb_10992_varemerkesoknader.csv` | SSB tabell 10990–10992 (Patentstyret) | År, 2002–2025 | `fetch_ssb.py` | Søknader til Patentstyret. Søknader direkte til EPO er ikke med |
| `wikimedia_norway.csv` | Wikimedia Analytics REST API | Måned, 2010-01–2026-09 | `fetch_wikimedia.py` | Bokmål og nynorsk. Redigeringer, nye sider og aktive redaktører, uten boter, bare innholdssider |
| `einnsyn_statistics.csv` | eInnsyn, `api.einnsyn.no/statistics` | Måned, 2016-01–2026-09 | `fetch_einnsyn.py` | Innsynskrav fra 2018-02. Opprettede dokumenter har et nivåskift i september 2024, årsak ikke sjekket |
| `forskningsradet_soknader.csv` | Forskningsrådet, åpne data «Søknader - versjon 2» (GitHub, oppdatert 2026-08-27) | År, 2004–2026 | `fetch_forskningsradet.py` | Alle søknader, avslag og bevilgninger, etter søknadsdato, søknadstype og sektor. Trukne, lukkede og avviste søknader er ikke med. Søknader i det nye saksbehandlingssystemet Tibi er ikke med, så 2026 er ufullstendig og utelatt i testen |
| `horinger.csv` | regjeringen.no, høringer | Én rad per høring publisert fra 2016 | `fetch_horinger.py` | Dato, departement, høringsfrist, status og antall høringssvar (treff i svarvisningen `?showSvar=true`). Testen bruker kvartalet for høringsfristen |
| `nb_books.csv` | Nasjonalbiblioteket, katalog-API | År, 2010–2025 | `fetch_nb_books.py` | Bøker etter utgivelsesår, alle og på bokmål eller nynorsk. Siste år er ufullstendige |

## Status for alle kandidatserier i planen

«Hentet» betyr at serien er lastet ned og testet. «Ikke sjekket» betyr at kilden ikke er åpnet i denne runden.

### Programvare og digitale produkter

| Serie | Status | Prioritet |
|---|---|---|
| Git pushes, repoer, utviklere og organisasjoner for Norge (Innovation Graph) | Hentet | 1 |
| Commits, PR-er og nye repoer i navikt | Hentet. Releases er ikke hentet, fordi det krever ett kall per repo (3 171 offentlige repoer) | 1 |
| Samme for andre offentlige org-er som én gruppe | Hentet for Skatteetaten, digdir, felleslosninger (Digdir), entur, oslokommune, vegvesen, nvdb-vegdata, NPRA og svvsaga (Statens vegvesen), nrkno, kartverket og politiet. Org-nivå er beholdt | 1 |
| Nye .no-domener per måned | Hentet fra JSON-kilden bak grafen på Norids nøkkeltallside | 1 |
| Nyregistrerte foretak, alle næringer og NACE 62 og 63 | Hentet fra Enhetsregisteret (månedlig, bare levende enheter) og fra SSB 08076 (kvartal, alle nye foretak). SSB 14721 (SN2025) dekker bare 2026K1–K2 og er kontrollert mot 08076, men ikke lagret | 1 |
| Stillingsannonser for utviklere og KI-andel | Ikke hentet. `data/nav_vacancies/snapshots/` finnes ikke. README-en beskriver innsamlingen. Ingen øyeblikksbilder er lagret | 2 |
| Norske apper i App Store og Google Play | Ikke sjekket. Ingen kjent åpen kilde med utviklerland | 3, trolig forkast |
| Norske spill på Steam og itch.io | Ikke sjekket | 3 |

### Forskning, patenter og tekstproduksjon

| Serie | Status | Prioritet |
|---|---|---|
| Publikasjoner og preprints med norsk institusjon, med matematikk og informatikk | Hentet fra OpenAlex. Uten API-nøkkel gir OpenAlex 1 000 kreditter per dag | 1 |
| Søknader til Forskningsrådet | Hentet fra Forskningsrådets åpne data på GitHub (lenket fra data.norge.no). 2026 mangler søknader i det nye systemet Tibi | 2 |
| Patent-, varemerke- og designsøknader | Hentet som årstall fra SSB. Månedstall fra Patentstyret er ikke funnet. Adressen patentstyret.no/om-patentstyret/statistikk ga 404 | 2 |
| Høringssvar per høring | Hentet for høringer publisert fra 2016. Listen gir 20 høringer per side, og svarvisningen for hver høring gir antall treff. robots.txt sperrer filterparametrene i listen, men ikke `page` og `showSvar` | 2 |
| Journalposter per måned per virksomhet | Delvis. Statistikkendepunktet gir opprettede dokumenter og innsynskrav per måned for hele eInnsyn, ikke per virksomhet og ikke etter journaldato | 2 |
| Nye bøker og ISBN | Hentet som årstall fra Nasjonalbibliotekets katalog. Bokbasen er ikke sjekket | 2 |
| Redigeringer og nye artikler på norsk Wikipedia | Hentet | 2 |
| Artikler i norske medier | Utgår. Ingen tilgang til Retriever/Atekst | Utgår |
| Vitenskapelig publisering per institusjon (Cristin/NVI) | Ikke sjekket | 3 |

### Sikkerhet, helse og juss

| Serie | Status | Prioritet |
|---|---|---|
| Hendelser håndtert av NSM/NorCERT | Ikke sjekket | 3 |
| CVE-er med norsk leverandør eller rapportør | Ikke sjekket | 3 |
| Kliniske studier med norsk studiested | Hentet fra ClinicalTrials.gov. Studier som bare er registrert i EU CTIS, mangler | 2 |
| Søknader om kliniske studier (CTIS, DMP, REK) | Ikke sjekket | 3 |
| Domstolene, Finansklagenemnda, Forbrukertilsynet, Sivilombudet, NAV-klager | Ikke hentet, etter planen | 3 |

## Finnes allerede i repoet

- KI-indeksen og yrkesseriene fra A-ordningen: `analysis/` og kiindeksen.no.
- NAV ledige stillinger per STYRK: `data/nav_vacancies/` (bare README per 2026-10-08).
- NAV arbeidssøkere etter utdanning: `data/nav_arbeidssokere/`.
- SSB KI-bruk i foretak og husholdninger: `data/ai_adoption/` og `data/ai_boom_norway/`.
- Anthropic Economic Index for Norge: `data/ai_usage_cross_platform/`.
- Investeringer, bygg og KI-bruk: `analysis/08_ai_boom/`.
- Datasenterstrøm: planlagt i `ENERGY-COMPUTE-PLAN-datarobot.md`.

## Reproduksjon

```
python analysis/09_macro_signals/fetch_github_innovation_graph.py
python analysis/09_macro_signals/fetch_github_orgs.py
python analysis/09_macro_signals/fetch_norid.py
python analysis/09_macro_signals/fetch_ssb.py
python analysis/09_macro_signals/fetch_brreg.py
python analysis/09_macro_signals/fetch_openalex.py
python analysis/09_macro_signals/fetch_clinicaltrials.py
python analysis/09_macro_signals/fetch_wikimedia.py
python analysis/09_macro_signals/fetch_einnsyn.py
python analysis/09_macro_signals/fetch_nb_books.py
python analysis/09_macro_signals/fetch_forskningsradet.py
python analysis/09_macro_signals/fetch_horinger.py
cd analysis/09_macro_signals && python run_all.py && python plot_overview.py && python summary_table.py
```

`test_trend_break.py` kjører simuleringstesten av trendbruddstesten.

`fetch_github_orgs.py` bruker token fra `gh auth token` og tar et par timer på grunn av GitHubs
søkegrenser. Skriptet hopper over søk som allerede ligger i `raw/github_orgs/`.
