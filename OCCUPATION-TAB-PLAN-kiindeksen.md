# Plan: kiindeksen.no — yrkesfane (augmentering/automatisering) + institusjonsutvidelse

Planleggingsdokument, 2026-09-06. **Ingenting bygges inn i kiindeksen.no ennå** — dette er
forslag til vurdering. Energi/compute (datasentre, kraftforbruk) er UTENFOR scope her og
planlegges separat for datarobot.no, se `ENERGY-COMPUTE-PLAN-datarobot.md` i samme mappe.

## Spor A — Utvid institusjonsanalysen fra 6 til alle relevante institusjoner

**Status i dag:** `Edutech/education-analysis/` (bygget 2026-09-02) kobler DBH-kandidattall →
utdanning.no-yrkesregister → dashbordets yrkeseksponering, aggregert til institusjonsnivå.
Kjører i dag på UiO, UiB, NTNU, UiS, NHH, BI. Output: `institutions_summary.csv` m.fl.,
presentasjonsside `tmt_utdanning_ki.html`.

**Forslag:**
1. Utvid `data/dbh/fetch_dbh.py` fra 6 til alle DBH-institusjoner med akkrediterte
   studieprogrammer (trolig 30-40, ekskluder rene fagskoler om ønskelig — Andreas avgjør
   avgrensningen).
2. Kjør pipeline 01→05 uendret (metodikk er allerede validert og dokumentert i
   `education-analysis/README.md`).
3. Beslutningspunkt: skal hele institusjonslisten inn i kiindeksen.no som egen figur/
   institusjonsvelger, eller holdes som eget presentasjonsverktøy slik `tmt_utdanning_ki.html`
   er i dag? Anbefaling: bygg først som utvidet standalone-analyse, vis Andreas resultatet,
   avgjør deretter om det er dashbord-verdig — unngår å bygge kiindeksen-UI for data som
   viser seg for tynt/usikkert ved små institusjoner (DBH skjermer små celler).
4. Avhengigheter: ingen nye datakilder, kun bredere spørring mot samme DBH-API.
5. Kjent begrensning som arves: profilene er nasjonale per NUS-utdanningskode, ikke per
   institusjon (se `education-analysis/README.md`, «Forbehold» pkt. 1) — utvidelsen endrer
   ikke denne begrensningen, bare hvor mange institusjoner som får en rad.

## Spor B (nytt, ikke tidligere navngitt) — Yrkesfane: augmentering vs. automatisering, "hvilke andre jobber kan gjøres"

Andreas' ønske: gjøre mer per yrke på selve augmentering/automatisering-aksen, og en egen
fane som viser hvilke ANDRE yrker et gitt yrkes oppgaver ligner på / kan gjøres av samme
person, gitt hvordan KI endrer oppgavesammensetningen.

**Data som allerede finnes lokalt og kan brukes uten nytt uttrekk:**
- `AI-Norway/data/ai_exposure/styrk08_all_exposure_measures.csv` — har allerede
  `handa_automation`, `handa_augmentation` PER STYRK-08-yrke (352/407 yrker dekket), pluss
  seks andre eksponeringsmål samme sted. Dette er nøyaktig augmentering/automatisering-
  aksen kiindeksen.no allerede diskuterer i metodeteksten, men foreløpig ikke viser yrke for
  yrke i selve dashbordet.
- `AI-Norway/data/ai_exposure/handa/automation_vs_augmentation_by_task.csv` — enda mer
  granulært: PER O*NET-OPPGAVE (3 364 oppgaver), med alle fem interaksjonstyper (feedback_loop,
  directive, task_iteration, validation, learning) hver for seg, ikke bare de to bøttene.
  Dette er det direkte lokale grunnlaget for å bygge en "hvilke oppgaver i yrket mitt er mest
  automatiserbare"-visning uten å vente på at Anthropic publiserer occupation-level data med
  den nye femdelte klassifiseringen (jf. overvåkingsjobben `anthropic-economic-index-watch`).
- `education-analysis/tools/occupation_table.py` og `occupation_figure.py` (Edutech-mappa)
  har allerede kode som slår opp disse kolonnene per yrke og lager tabell/figur i husstil —
  gjenbrukbart som utgangspunkt for en kiindeksen-fane, ikke bare til foredragsdekket.

**Forslag til ny fane "Yrke for yrke":**
1. **Del 1 — augmentering/automatisering per yrke.** Scatter eller sortert stolpe: yrke ×
   (handa_augmentation, handa_automation), med restandelen (uklassifisert) synlig som i
   `plot_augmentation_vs_automation.py` (Edutech-figuren). Koble til sysselsettingstall
   (samme kilde som kiindeksen bruker for kvintiler i dag) for å vekte/filtrere på størrelse.
2. **Del 2 — "hvilke oppgaver kan gjøres" (ny, ikke bygget noe sted ennå).** Bruk
   `automation_vs_augmentation_by_task.csv` til å vise, for et valgt yrke, hvilke av dets
   O*NET-oppgaver har høyest automatiseringsandel (directive) vs. augmenteringsandel
   (feedback_loop + task_iteration + validation + learning). Krever en STYRK08→O*NET-
   oppgave-kobling — sjekk om `styrk08_relational_mapping.csv` eller ISCO-SOC-kryss-gangen
   som allerede brukes for eksponeringsmålene kan gjenbrukes til å hente riktig oppgavesett
   per yrke; hvis ikke, må en slik kobling bygges (sannsynligvis via samme SOC-vei som
   `mapping_methodology.md` beskriver for de andre målene).
3. **Del 3 — "hvilke andre yrker" (Andreas' idé, ny analyse).** Dette er IKKE bygget noe sted.
   To mulige metoder å utrede, ikke velge nå:
   - **Oppgaveoverlapp:** yrker som deler mange av de samme O*NET-oppgavene (kosinuslikhet
     på oppgavevektorer) er kandidater for "kan gjøres av samme person". Datagrunnlag finnes
     (O*NET oppgave×yrke-kobling brukes allerede i eksponeringsbyggingen).
   - **Eksponeringsprofil-likhet:** yrker med lignende automatiserings-/augmenterings-
     fingeravtrykk (samme mønster på tvers av de fem interaksjonstypene), uavhengig av om
     oppgavene faktisk overlapper. Enklere å bygge, men svakere begrunnelse for "kan gjøres".
   Anbefaling: skisser begge som notat til Andreas før noe kode skrives — dette er en ny
   forskningsmetodisk beslutning, ikke bare en visualisering av eksisterende tall.
4. Ingen av delene krever nye eksterne datakilder. Alt kan starte fra filer som allerede
   ligger i `AI-Norway/data/ai_exposure/`.

## Rekkefølge foreslått

1. Spor A (institusjonsutvidelse) — mekanisk, lav risiko, kan gjøres først og vises fram.
2. Spor B del 1 (augmentering/automatisering yrke for yrke) — data finnes, ren visning.
3. Spor B del 2 (oppgavenivå per yrke) — trenger en kobling å bygge, men velkjent metode.
4. Spor B del 3 ("hvilke andre yrker") — ny metode, bør avklares med Andreas før bygging.

## Ikke i denne planen

- Energi/compute-fanen (datasentre, kraftforbruk, bygget/godkjent/planlagt): flyttet til
  `ENERGY-COMPUTE-PLAN-datarobot.md`, target-nettsted datarobot.no, ikke kiindeksen.no.
- Den internasjonale token/bruker-databasen (Anthropic/OpenAI/OpenRouter, Spor C fra forrige
  økt): fortsatt på vent i `data/ai_usage_cross_platform/`, ingen endring i status.
- SSBs individ-/foretaksundersøkelse som sammenligningsserie (tidligere Spor B, nå omdøpt
  fordi bokstaven B er brukt til yrkesfanen over) — ikke tatt opp i denne runden, ikke glemt.

## Status 2026-09-07 (Claude, bakgrunnsjobb)

Bygget på branch `arbeidsmarkedet-panels`, ikke deployet. Nettstedet heter nå
Arbeidsmarkedet, KI-indeksen er forsiden. Tre nye sider: `yrker.html` (Spor B
del 1 og 2, med de tre nyere Anthropic-utgivelsene aug. 2025, nov. 2025 og
feb. 2026, chat og API), `utdanning.html` (Spor A, seks institusjoner, ikke
utvidet ennå) og `bruk.html` (token/bruker-notatene). Del 3 «hvilke andre
yrker» er ikke bygget. Detaljer og åpne beslutninger:
`dashboard/PLAN_arbeidsmarkedet_2026-09.md`.
