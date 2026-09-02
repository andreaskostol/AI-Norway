# Plan: målvelger på kiindeksen.no (Eloundou / Mouchel)

Fra Øystein (med Claude), 2. september 2026. Oppfølging av
kommentar-svar-posten: Mouchel et al. (2026) legges til som valgbart
eksponeringsmål i en nedtrekksmeny. 2016-placebo og fjernarbeid er
bevisst utsatt.

## Status: datadelen er ferdig (Øystein)

Seks `mouchel_*`-pakker ligger i `releases/2026-09/` (commit
`0d67c49`): `mouchel_by_exposure`, `mouchel_age_by_exposure` og
hires-/wages-tvillingene. Struktur, kolonnenavn, justeringer og
radantall er identiske med Eloundou-motstykkene, så prepare_data og
app.js kan parameteriseres med pakkeprefiks («» eller «mouchel_»).

- Kvintiler fra `mouchel_grounded` i
  `data/ai_exposure/styrk08_mouchel_mapping.csv` (kolonnen
  `quintile`), equal-frequency over de samme 397 yrkene som Eloundou.
  Spearman mot Eloundou-beta 0,94; 66 prosent av yrkene i samme
  kvintil.
- `by_age`, composition-pakken, yrkescasene, usage- og
  offentlig sektor-pakkene bygges ikke per mål: by_age pooler alle
  yrkene og er målnøytral, resten holder vi på Eloundou i v1.
- QA: composition summerer til 100, basismåned nøyaktig 100, rå
  Q5-indeks reprodusert uavhengig fra panelet. Rå-vs-sa-gapet i juni
  (~7 pp) er likt Eloundou-pakken (juni er sesonglav mot
  november-basen).
- Hovedtall under Mouchel-kvintiler: K1 −1,5 %, K5 +0,8 %,
  KI-indeks +2,3 pp (Eloundou: +1,7 pp).

## Del B: nettside (Andreas/Claude)

- Nedtrekksmeny i kontrollinja (ved utfall/justering):
  «Eksponeringsmål: Eloundou et al. (2024) / Mouchel et al. (2026)».
  Valget bytter pakkeprefiks for figur 1 (hovedfiguren), 2
  (etter eksponering) og 3 (alder × eksponering), pluss
  hires-/wages-variantene via utfallsvelgeren.
- **Usikkerhetsbåndet gjelder bare Eloundou.** Bootstrappen
  (`recursive_kiindeks_headline.py`) er kjørt på Eloundou-kvintilene.
  Skjul båndet når Mouchel er valgt, eller si fra så kjører jeg
  bootstrappen for Mouchel også (samme script, bytt mapping).
- Composition-figuren (4) og «Siste 12 måneder» kan bli stående på
  Eloundou i v1; si i så fall i fotnoten at målvelgeren gjelder
  figur 1-3.
- Metodetekst (`om.html`/`en/about.html`): ett avsnitt om Mouchel-målet
  (evidensgrunnet, samme 397 yrker, qcut), med referanse. Ordforklaring
  ved nedtrekksmenyen: én setning om at målene rangerer yrker nesten
  likt (Spearman 0,94), men at nivåene ikke er identiske.
- `occupations.json`/yrkesvelgeren: uendret i v1 (chipsene viser
  Eloundou-kvintil). Kan senere få begge kvintilene fra crosswalken.
- Nedlastingsseksjonen: de seks nye kortene legges i en egen gruppe
  eller under hovedkuttene.

## Til kommentar-svar-posten

Målvelgeren svarer på spørsmålet om ulike eksponeringsmål. Belegg som
kan brukes: fire uavhengige kilder for faktisk bruk (Anthropic 2026,
Microsoft Copilot, Google ATLAS, Handa) rangerer yrker nesten likt som
Eloundou (rangkorrelasjon 0,77-0,79), og Mouchel-målet gir samme
kvalitative bilde med KI-indeks +2,3 mot +1,7. Offentlig sektor-modulen
(figur 13-16) svarer på etterspørselen etter egen offentlig-modul;
kostnad/saksbehandlingstid/frigjorte årsverk/kvalitet krever data som
ikke finnes i A-ordningen.
