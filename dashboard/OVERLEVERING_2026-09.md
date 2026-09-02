# Overlevering: publisering av 2026-09-releasen på kiindeksen.no

Til Andreas, fra Øystein (med Claude), 1. september 2026.

Datagrunnlaget er ferdig og committet (`f16f980`). Dette notatet beskriver
hva som gjenstår før releasen kan deployes, pluss noen andre mangler ved
nettsiden vi har notert underveis.

## Status 2026-09-02: publisert

Releasen ble deployet 2. september 2026 (Fly-image
`deployment-01M1GYXN68Z6ARTQHDG67E5BN9`; forrige live-versjon var
`deployment-01KXT7N26ANNAZYGD0ND59ATP9`). Alle seks punktene under
«Gjenstår før deploy» er gjort: de 10 `public_`-pakkene er inne i
`prepare_data.py`, offentlig sektor har egen seksjon (figur 12–15) med
forbehold på norsk og engelsk, bootstrap-båndet er rekjørt for vintage
2026-06 (KI +1,73, se 2,54, intervall −3,2 til +6,7), Hovedfunn/Key
findings er oppdatert, cache-parameteren er `v=20260902a`, og backup
ligger i `backups/kiindeksen_site_2026-09-02_pre-2026-09-release.tar.gz`.
Nedlastingsseksjonen viste allerede stock_clerks- og
usage-ratio-composition-pakkene (den bygges fra `PKG_TITLES`, ikke fra
figurlisten), så det punktet krevde ingen endring. Working paperet er
fortsatt ikke lenket.

## Status: hva som er gjort

- `releases/2026-09/` er bygget: alle 40 pakker (30 private + de 10 nye
  offentlig sektor-pakkene fra 2026-08), med data **2021-01 til 2026-06**
  (microdata.no versjon 56, uttrekk august 2026).
- QA: alle 100 CSV-er er rad-identiske med 2026-08 til og med 2026-04
  (sesongfaktorene er frosset 2021-2024, så historikken flytter seg ikke).
  Ingen null-måneder i noen offentlig ansettelsesfasett (minimum
  150/måned), så hires beholder yoy/annualized. Juni-lønnshoppet
  (63 000 mot 52 600 i mai) er det vanlige feriepengemønsteret.
- 2026-08-releasen ble aldri deployet; 2026-09 erstatter den som
  publiseringskandidat. Mappen ligger igjen i git som verifisert mellomsteg.

**Viktig innholdsendring:** KI-indeksen går fra **+0,5 til +1,7
prosentpoeng** (sa, siste tre måneder = april-juni 2026). Endringen drives
av at de *minst* eksponerte yrkene (K1) har falt siste halvår (til 99,0),
mens K5 har flatet ut rundt 99,9. Verd å ha klart for seg i omtalen:
hovedtallet stiger fordi kontrollgruppen faller, ikke fordi de mest
eksponerte faller mer.

## Gjenstår før deploy

1. **`site/prepare_data.py`**: de 10 `public_`-pakkene må inn i
   `TS_PACKAGES`/`SNAP_PACKAGES` (scriptet plukker nyeste release
   automatisk, så selve release-valget ordner seg selv). Husk caveaten fra
   data dictionaries: nivåsammenligning på tvers av sektorer er
   misvisende (kvintilsammensetningen er svært ulik; offentlig K5
   domineres av yrke 2422).
2. **`app.js` + HTML**: ny seksjon/velger for offentlig sektor, i takt på
   norsk (`index.html`) og engelsk (`en/index.html`), jf. README-regelen om
   felles element-ID-er.
3. **Bootstrap-usikkerhetsbåndet må rekjøres.** `dashboard.json` sitt
   `headline_uncertainty` er fra vintage 2026-04 (ki 0,52, se 2,44,
   CI [-4,3, +5,3]) og hører ikke til +1,7. Kjør
   `analysis/06_figures/recursive_kiindeks_headline.py` med `LAST_CUT`
   bumpet fra `"2026-04"` til `"2026-06"` (linje ~52); `prepare_data.py`
   leser siste rad i `coef_recursive_kiindeks_headline.csv` automatisk.
4. **Hardkodede tall og datoer i teksten** (oppdateres ikke av scriptene):
   - `om.html` «Hovedfunn»: «KI-indeksen er svakt positiv (+0,5)» (linje
     ~53) og fotnoten «Per april 2026 (release juli 2026)» (linje ~48).
   - `en/about.html` «Key findings»: «(+0.5)» (linje ~54) og «As of April
     2026 (July 2026 release)» (linje ~47).
   - Sjekk om de øvrige hovedfunn-kulepunktene fortsatt stemmer med
     juni-tallene (særlig omtalen av unge i mest eksponerte yrker).
5. **Cache-parameter**: bump `?v=20260718b` i alle fire HTML-filer når
   `app.js`/`style.css` endres.
6. **Deploy**: ta backup av `site/` til `backups/` først (jf. mønsteret
   fra juli), så `cd dashboard/site && flyctl deploy`.

## Andre mangler ved nettsiden (uavhengig av releasen)

- **Working paperet er ikke lenket.** Siteringsseksjonen (`#sitering`) og
  `#paper-ref` sier bare «Under arbeid (working paper)» uten lenke, selv om
  tittelen er oppdatert («Does AI Widen Employment Gaps? ...»). Legg inn
  lenke til PDF/SSRN/nettside når paperet legges ut — både i den norske og
  engelske siteringsblokken og i BibTeX-en (`url`-felt).
- **Fem pakker i releasene vises ikke på siden og kan heller ikke lastes
  ned derfra**: `stock_clerks` (+ hires/wages-variantene) og de to
  usage-ratio-composition-pakkene. Nedlastingsseksjonen bygges fra samme
  liste som figurene, så de faller utenfor. Vurder om lagermedarbeidere
  skal inn som sjette yrkescase, eller om nedlastingslisten bør utvides
  uavhengig av figurene.
- **Publiseringen svarer på LinkedIn-tilbakemeldingen fra juni** (Erik
  Slinning etterlyste offentlig sektor-modul; du svarte «neste runde»).
  Kan være verdt å nevne i lanseringsposten. Kommentarene ligger i
  `dashboard/2026-06 linkedin comments.txt`.

## Referanser

- Byggekjeden: `microdata-scripts/monthly/09_kpos_decade_2026m05_m06.mdata`
  → `analysis/02_parse/append_09_2026m05_m06.py` →
  `dashboard/build_release.py 2026-09`.
- Redigerings- og deploy-guide: `dashboard/README.md`.
- Teknisk dokumentasjon for siten: `dashboard/site/README.md`.
