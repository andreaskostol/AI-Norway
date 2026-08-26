# Google AI & Economy ATLAS v1.0 (July 2026)

Kilde: "Google's AI & Economy ATLAS v1.0: Mapping Gemini Usage in the Economy",
Google AI & Economy Research Program, 23. juli 2026.
- Rapport-PDF: https://ai.google/static/documents/GoogleATLASv1.pdf (arXiv:2608.00038)
- Blogg: https://blog.google/innovation-and-ai/technology/research/understanding-the-ai-economy/
- Lokal kopi: literature/llm-selskapsrapporter/Google ATLAS 2026-07 Mapping Gemini Usage in the Economy.pdf

Per 2026-08-25 finnes INGEN offentlig maskinlesbar datafil på yrkesnivå
(sjekket ai.google/economy, blog.google, arXiv (inkl. kildepakke), HuggingFace,
Kaggle, GitHub). Rapporten oppgir at tilgang til det endelige datasettet er
"tightly restricted to a small team of researchers". Filene her er derfor
hentet ut fra selve rapporten.

## atlas_v1_soc_major_gemini_shares_digitized_2026-07.csv
Digitalisert fra rapportens Figur 1 (PNG i arXiv-kildepakken, Figures/Figure_2.1.png),
programmatisk via fargedeteksjon av punktsentre + kalibrering mot aksegridlinjer
(171 px per 5 pp). 22 SOC 2018 Major Groups (militære yrker utelatt).
- gemini_us_interaction_share_pct: andel av USA-arbeidsrelaterte Gemini-interaksjoner
  (App + AI Mode + API, 6.-19. april 2026) klassifisert til yrkesgruppen
- oews_us_employment_share_pct: andel av USA-sysselsetting (OEWS mai 2024)
- representation_ratio: gemini_share / employment_share
- *_dot_quality: "full" = hele punktet synlig; "partial(edge-recovered)" =
  punkt delvis skjult av overlappende punkt, sentrum estimert fra synlig kant + radius
  (gjelder OEWS for 21-0000, 23-0000, 45-0000)
Presisjon: begge kolonner summerer til ~100.2; OEWS-verdiene treffer publiserte
OEWS-andeler innenfor ~0.1 pp. Regn med +/-0.1 pp digitaliseringsfeil.

## atlas_v1_report_occupation_lists_2026-07.csv
Yrkesnavn (O*NET-SOC-titler, ingen tallverdier i rapporten) fra Tabell 1
(mest over-/underrepresentert og størst uobservert, detaljert nivå) og Tabell 2
(mest/minst task saturation). Kun kvalitativ bruk.

Lisens/vilkår: ingen egen datalisens publisert; figurinnhold fra offentlig
rapport, standard sitering av rapporten gjelder.
