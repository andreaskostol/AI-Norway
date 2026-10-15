# Kiindeksen.no: feil og misvisende tekst

15. oktober 2026. Gjelder arbeidskopien av nettstedet med Labben og Studio.

## Omfang

Gjennomgangen dekker alle tolv sider på norsk og engelsk: forsiden
(Indeksen), Labben, Yrker, Utdanning, Studio og Om. Tekst og tall er
sjekket mot dataene i `dashboard/site/public/data/` og mot koden som lager
dem. Sidene er også åpnet i en nettleser. Der var det ingen konsollfeil og
ingen døde interne lenker eller ankre.

Bruksmålet fra Anthropic er ikke behandlet her. Det gjelder figur 10 til 12
på forsiden og bruksdelen av Yrker.

Funnene er delt i tre typer. «Feil» gir feil tall eller feil fakta.
«Misvisende» gir leseren et feil inntrykk. «Kosmetisk» er resten.

Linjenumrene gjelder arbeidskopien 15. oktober 2026. Stier uten mappe
ligger i `dashboard/site/public/`. Den engelske siden har som regel samme
feil som den norske.

## Oversikt

| ID | Side | Problem | Type |
|---|---|---|---|
| F1 | Forsiden | Oppsummeringen kaller lønn og nyansettelser «sysselsetting» | Feil |
| F2 | Forsiden | Radene under hovedtallet bytter utfall med feil etikett | Feil |
| F3 | Forsiden | Befolkningstallene er beskrevet feil | Feil |
| F4 | Forsiden | Sysselsetting teller arbeidsforhold, ikke lønnstakere | Feil |
| F5 | Utdanning | Annen eksponeringsskår enn resten av nettstedet | Feil |
| F6 | Yrker | Samme oppgave står to ganger i oppgavefiguren | Feil |
| F7 | Studio | Feil forfatternavn | Feil |
| M1 | Forsiden | Mouchel beskrives som bygget på KI-bruk | Misvisende |
| M2 | Forsiden | Ordvalget tar ikke hensyn til usikkerheten | Misvisende |
| M3 | Forsiden | Eldre releaser kan ikke lastes ned | Misvisende |
| M4 | Forsiden | Referansemåneden beskrives med Claude Code som standard | Misvisende |
| M5 | Forsiden | «Eksakt» samme metode som DEL | Misvisende |
| M6 | Forsiden | Teksten uten JavaScript stemmer ikke med dataene | Misvisende |
| M7 | Forsiden | Yrkesvelgeren følger ikke valgt eksponeringsmål | Misvisende |
| M8 | Yrker | Oppgavetekstene og antall oppgaver beskrives feil | Misvisende |
| M9 | Yrker | API-påstanden er for sterk | Misvisende |
| M10 | Yrker | O*NET-ferdighetene er ikke vurdert av ansatte | Misvisende |
| M11 | Yrker | Antall lønnstakere er fra november 2022 | Misvisende |
| M12 | Yrker | API vises flere steder enn teksten sier | Misvisende |
| M13 | Yrker | 18 yrker vises uten eksponering | Misvisende |
| M14 | Labben | Mouchel er ikke alternativ per oppgave | Misvisende |
| M15 | Utdanning | Metodeteksten mangler to forbehold | Misvisende |
| M16 | Studio | Datoer med bare årstall sorteres feil | Misvisende |
| M17 | Studio | Lista er ufullstendig | Misvisende |
| M18 | Alle | Bunnteksten følger ikke den nye menyen | Misvisende |
| K1 | Forsiden | Velgeren «Referanse» går utenfor skjermen på mobil | Kosmetisk |
| K2 | Forsiden | Hovedtallet kalles en differanse | Kosmetisk |
| K3 | Forsiden | Ikke alle datapakker har alle filtyper | Kosmetisk |
| K4 | Forsiden | Menylenken og metabeskrivelsen er utdatert | Kosmetisk |
| K5 | Yrker | Spennet i antall yrker er for smalt | Kosmetisk |
| K6 | Yrker | Gruppeseksjonen ligger feil og mangler i innholdslista | Kosmetisk |
| K7 | Yrker | Figurtekster sier «kvintil» | Kosmetisk |
| K8 | Studio | Titler og navn er hentet fra filnavn | Kosmetisk |
| K9 | Alle | Metadata er utdatert eller mangler | Kosmetisk |
| K10 | Kode | Dokumentasjonen peker på gamle navn | Kosmetisk |

## Feil

**F1. Oppsummeringen kaller lønn og nyansettelser «sysselsetting».**
`index.html:132-133` sier at punktene følger valget av utfall. Bare punkt 3
gjør det (`app.js:1035`). Teksten i punkt 3 sier likevel alltid
«sysselsettingen» (`app.js:1052-1053`). Med Lønn valgt står det at
sysselsettingen blant de yngste har vokst med 20,6 %. Tallet er lønnsvekst.
Punkt 1, 2 og 4 viser alltid sysselsetting.
Retting: lås punkt 3 til sysselsetting, og ta «utfall» ut av setningen.

**F2. Radene under hovedtallet bytter utfall med feil etikett.**
Radene for alle aldre og for unge følger valgt utfall (`app.js:641`). De
står likevel med etiketten «KI-indeksen» (`app.js:815`) og med
standardfeilen fra sysselsetting (`app.js:818`). Med Nyansettelser står
−22,9 rett under hovedtallet +1,5, og begge har standardfeil 2,69.
Overskriften på figur 11 er fast «Sysselsetting etter KI-bruk»
(`index.html:375`). Figuren følger likevel utfallet (`app.js:484`).
Retting: lås radene til sysselsetting. La overskriften på figur 11 følge
utfallet.

**F3. Befolkningstallene er beskrevet feil.**
`index.html:598-600` sier «kvartalstall interpolert til måned». SSB-tabell
07459 har årstall per 1. januar. `data/macro/build_population_quarterly.py`
interpolerer dem til midten av hvert kvartal. Hver måned får så tallet for
sitt kvartal.
Retting: «Årstall per 1. januar (SSB 07459), interpolert til midten av
hvert kvartal og brukt for alle måneder i kvartalet.»

**F4. Sysselsetting teller arbeidsforhold, ikke lønnstakere.**
`index.html:543` sier «Sysselsetting er antall lønnstakere i gruppen». Se
også `index.html:468-469`. Uttrekket bygger på et datasett per
arbeidsforhold og fjerner forhold uten positiv kontantlønn
(`microdata-scripts/monthly/09_kpos_decade_2026m07.mdata`). Samme side sier
litt lenger ned at indeksen måler «jobber per person».
Retting: «Sysselsetting er antall arbeidsforhold med utbetalt kontantlønn i
måneden.»

**F5. Utdanning bruker en annen eksponeringsskår enn resten av nettstedet.**
`analysis/07_education/build_majors.py:117-120` leser
`inputs/styrk08_exposure_v2.csv` og lager egne grupper. Yrker og forsiden
bruker `eloundou_beta` og `eloundou_q` fra
`data/ai_exposure/styrk08_all_exposure_measures.csv`. Av 224 yrker som
finnes på begge sider, havner 22 i en annen gruppe på Utdanning.
Elektrikere (7411) er i gruppe 2 på Utdanning og gruppe 1 ellers.
Hjemmehjelpere (5322) har skår 0,079 og gruppe 1 på Utdanning, men 0,219
og gruppe 2 på Yrker. Teksten sier at gruppen er «den samme femdelingen
som yrkene» (`utdanning.html:120-121`). Labben sier at verktøyene bruker
«samme kryssgang som KI-indeksen» (`labben.html:74`).
Retting: la `build_majors.py` bruke skårene og gruppene fra
`styrk08_all_exposure_measures.csv`.

**F6. Samme oppgave står to ganger i oppgavefiguren på Yrker.**
Ni yrker har samme oppgavetekst to ganger i lista for Claude.ai. Blant
dem er 2310 Universitetslektorer, 2341 Grunnskolelærere, 2352
Spesiallærere og 2512 Programvareutviklere. Når to SOC-koder har samme
oppgave, slår `analysis/03_mappings/build_aei_collaboration_mapping.py`
dem ikke sammen før de største velges.
Retting: slå sammen like oppgaver og summer bruksandelen før topplista
lages.

**F7. Feil forfatternavn i Studio.**
Navnene ser ut til å komme fra filnavn i `literature/`.

- `data/studio_papers.json:188`: «Kauhanen og Petri». Forfatterne er Antti
  Kauhanen og Petri Rouvinen (ETLA Working Papers 135, januar 2026).
- `data/studio_papers.json:212`: «Iscenko, Curto og Millet». Forfatterne
  er Zanna Iscenko og Fabien Curto Millet (januar 2026).
- `data/studio_papers.json:272`: Demirer, Horton, Immorlica og Lucier. Peyman
  Shahidi mangler.

Retting: bruk navnene fra artiklene.

## Misvisende

**M1. Mouchel beskrives som bygget på KI-bruk.**
`index.html:529` sier at målet «bygger på dokumentert KI-bruk». Det samme
står i `app.js:1913-1914` og `1964-1965`. Ifølge
`data/ai_exposure/docs/styrk08_all_exposure_measures_README.md` er målet
språkmodellers vurdering av hver oppgave, støttet av nyheter og forskning.
Det er aldri kalibrert mot bruksdata.
Retting: «bygger på språkmodellers vurdering av hver oppgave, støttet av
nyheter og forskning».

**M2. Ordvalget tar ikke hensyn til usikkerheten.**
Oppsummeringen kaller indeksen «positiv» når den er minst 1
(`app.js:1015-1019`). Med standardvalgene står det «KI-indeksen er positiv
(+1,5)». Samme side oppgir intervallet −3,8 til +6,8 og «ikke statistisk
forskjellig fra null». Punkt 3 bruker «viktige forskjeller» ut fra
fortegnet alene (`app.js:1039-1044`).
Retting: skriv «om lag null» når intervallet dekker null. Krev et
minstegap før «viktige».

**M3. Eldre releaser kan ikke lastes ned.**
`index.html:646` sier at alle tidligere releaser kan lastes ned. Lenkene
lages bare for gjeldende release (`app.js:1612-1615`). Under
`data/releases/` ligger 2026-06, 2026-07, 2026-09 og 2026-10. 2026-08
finnes bare i `dashboard/releases/`.
Retting: lenk til eldre releaser, eller fjern løftet.

**M4. Referansemåneden beskrives med Claude Code som standard.**
`index.html:553-554` sier «februar 2025, eller november 2022 når ChatGPT er
valgt». Standard er ChatGPT.
Retting: «november 2022 som standard, februar 2025 når Claude Code er
valgt».

**M5. «Eksakt» samme metode som DEL.**
`index.html:635-636` sier at de rå seriene «reproduserer deres metode
eksakt». Linjene rett før beskriver forskjeller: DEL bruker et balansert
firmapanel og finere aldersgrupper.
Retting: «de rå seriene følger DELs indeksering og kvintilkonstruksjon».

**M6. Teksten uten JavaScript stemmer ikke med dataene.**
`index.html:136-139` sier at andelen sysselsatte er om lag stabil og at
KI-indeksen er om lag null. Teksten vises før dataene er lastet, og når
JavaScript ikke kjører. Med dagens data er indeksen +1,5.
Retting: bytt teksten ut med en nøytral plassholder.

**M7. Yrkesvelgeren følger ikke valgt eksponeringsmål.**
`index.html:661-662` sier at yrkene har «samme eksponeringskvintil som i
figur 1». Med Mouchel valgt bruker figur 1 Mouchel-kvintiler, mens
yrkesvelgeren viser Eloundou-kvintilen. Nedlastingsdelen kaller målet
«Mouchel et al. (2026)» på norsk (`app.js:1585`).
Retting: «Yrkene har Eloundou-kvintilen». Bruk «m.fl.» på norsk.

**M8. Oppgavetekstene og antall oppgaver beskrives feil på Yrker.**
`yrker.html:304` sier at oppgavetekstene er O*NETs engelske formuleringer.
`yrker.html:171` sier at de er oversatt til norsk, og de vises på norsk.
`utdanning.html:212` har samme feil. `yrker.html:302` sier at figuren viser
15 oppgaver. Den viser 5 eller 10.
Retting: «oversatt fra O*NETs engelske formuleringer» og «de fem eller ti
oppgavene med mest bruk».

**M9. API-påstanden er for sterk.**
`yrker.html:363-364` sier at nesten alle yrker ligger over 80 prosent
direkte delegering i API-et. Det gjelder 242 av 319 yrker i februar 2026
og 254 av 304 i august 2025.
Retting: «om lag tre av fire».

**M10. O*NET-ferdighetene er ikke vurdert av ansatte.**
`yrker.html:310-313` sier at O*NET har spurt ansatte, og at det samme er
gjort for 35 ferdigheter. Alle vurderingene av ferdigheter i
`data/ai_exposure/onet_relational/Skills.txt` er gjort av O*NETs
analytikere.
Retting: «Ferdighetene er vurdert av O*NETs analytikere.»

**M11. Antall lønnstakere er fra november 2022.**
Sammendraget på Yrker skriver at yrket «har» et antall lønnstakere
(`panels.js:538`). Tallet er fra november 2022. Yrker uten månedsserie får
teksten «har under 30 lønnstakere» (`panels.js:539`). Kravet for serie er
minst 30 i hver måned fra januar 2021. Mangler serien, betyr det ikke at
yrket har under 30 i dag.
Retting: «hadde N lønnstakere i privat sektor i november 2022», og «har
ikke minst 30 lønnstakere i hver måned siden 2021».

**M12. API vises flere steder enn teksten sier.**
`yrker.html:170-171` sier at API-et bare vises i figuren «Chat mot API».
Sammendraget viser også API-ets automatiseringsandel (`panels.js:550`).
Retting: «API-et vises i figuren «Chat mot API» og i sammendraget».

**M13. 18 yrker vises uten eksponering.**
Gruppetabellen på Yrker viser strek for eksponering hos 18 yrker som har
skår. Det skjer fordi yrker som bare finnes i `data/occupations.json`, får
`beta: null` (`panels.js:1133`).
Retting: legg skåren for alle yrker med kvintil inn i `data/yrker.json`.

**M14. Mouchel er ikke alternativ per oppgave.**
`labben.html:74-75` sier at eksponeringen per oppgave er Eloundou, med
Mouchel som alternativ. Mouchel vises bare per yrke.
Retting: «Eksponeringen per oppgave er Eloundou m.fl. (2024). Per yrke
vises også Mouchel m.fl. (2026).»

**M15. Metodeteksten på Utdanning mangler to forbehold.**

- Siden viser høyst tre oppgaver fra samme yrke
  (`analysis/07_education/build_majors.py:79`). Alle 215 faggrupper når
  denne grensen. Teksten sier bare at de ti med størst vekt vises
  (`utdanning.html:117`).
- Skåren i tabellen er snittet av tre vurderinger. Utdanningens samlede
  skår bygger bare på GPT-4-vurderingen. 973 av 2 150 tabellrader har en
  skår som avviker fra GPT-4-vurderingen.

Retting: «De ti med størst vekt vises, høyst tre fra samme yrke.» Bruk
samme skår begge steder, eller si at de er ulike.

**M16. Datoer med bare årstall sorteres feil i Studio.**
19 av 34 oppføringer i `data/studio_papers.json` har bare årstall.
`studio.js:36` sorterer «2026» som «2026-00». De havner derfor under
mars 2026, også de nyeste.
Retting: før inn måned fra artiklene.

**M17. Studio-lista er ufullstendig.**

- Nyere artikler i `literature/` mangler. Blant dem er Imas og Schaal
  (2026), Kim og Koning, «AI-native firms» (2026), og Microsofts «Global AI
  Diffusion» for andre kvartal 2026. Lista har bare første kvartal.
- 17 av 34 oppføringer har tom kilde, og 33 av 34 har tom lenke.
- «AI Economic Indicators: June 2026 Update» har datoen 2026-08. Siden
  sier at datoen er publiseringsmåneden.
- «Labor Market Consequences of Generative AI» mangler undertittelen
  «Early Evidence from Norway» (Facius og Iacono, CESifo Working Paper
  12752, juni 2026).

Retting: legg inn de nye artiklene, fyll inn kilde og lenke, og bruk
titler og datoer fra artiklene.

**M18. Bunnteksten følger ikke den nye menyen.**
Menyen er Indeksen, Labben (Yrker, Utdanning), Studio og Om.

- Forsiden har Yrker og Utdanning ved siden av Labben (`index.html:839-841`).
- Studio har ikke Yrker og Utdanning (`studio.html:93-95`).
- Om har ingen lenke til Indeksen (`om.html:155-158`).

Retting: bruk bunnteksten fra `labben.html` på alle sider.

## Kosmetisk

**K1. Velgeren «Referanse» går utenfor skjermen på mobil.**
På 375 piksler bredde stikker `#sel-epoch` 26 piksler utenfor. Siden kan da
rulles sidelengs. Teksten i valget for Claude Code er for lang.
Retting: gi `.control select` en største bredde på 100 %.

**K2. Hovedtallet kalles en differanse.**
`index.html:107-108` beskriver hovedtallet som veksten i de mest utsatte
minus veksten i de minst utsatte. Koden regner forholdet
100·((1+g5)/(1+g1)−1) (`app.js:1133`). Med dagens tall gir begge +1,5.
Retting: «relativ vekst i de mest eksponerte mot de minst eksponerte».

**K3. Ikke alle datapakker har alle filtyper.**
`index.html:746-748` sier at hver pakke har tidsserie, tolvmånedersendring,
annualisert vekst og data dictionary. Noen pakker mangler noen av disse.
Retting: «De fleste pakkene inneholder også …».

**K4. Menylenken og metabeskrivelsen er utdatert.**
Menylenken «KI-bruk» peker til figur 11 (`index.html:29`) og hopper over
figur 10. Metabeskrivelsen i `index.html:7` nevner egne sider for yrker
og utdanning, ikke Labben.
Retting: pek lenken til `#bruk-vekst`, og nevn Labben.

**K5. Spennet i antall yrker er for smalt.**
`yrker.html:300-301` sier 300 til 320 yrker per utvalg. Tallet er 306 til
319 i Claude.ai og 304 til 323 i API-et.
Retting: «300 til 325 yrker per utvalg».

**K6. Gruppeseksjonen på Yrker ligger etter Metode.**
Seksjonen starter på `yrker.html:372`, etter Metode på linje 238. Den
mangler i innholdslista. Den heter `gruppe` på norsk og `group` på
engelsk.
Retting: flytt den foran Metode, legg den inn i innholdslista og bruk samme
id på begge språk.

**K7. Figurtekster på Yrker sier «kvintil».**
`panels.js:999`, `1026` og `1038` sier «eksponeringskvintil». Resten av
siden bruker gruppenavn som «Mest utsatt».
Retting: bruk gruppenavnet.

**K8. Titler og navn i Studio er hentet fra filnavn.**
Eksempler: «The broken ladder: AI and remote work» heter «The Broken
Ladder: AI, Remote Work, and Early-Career Hiring». «Lothman» skal være
Löthman. «Teeselink» skal være Klein Teeselink.
Retting: bruk titler og navn fra artiklene.

**K9. Metadata er utdatert eller mangler.**

- `sitemap.xml` har `lastmod` 2026-09-02 for forsiden og Om.
- Ingen sider har Open Graph-tagger.
- Taglinjen er «Monthly indicators of» på `en/index.html`, `en/lab.html`
  og `en/studio.html`. De andre engelske sidene har «on».

Retting: oppdater `lastmod`, legg inn `og:url`, `og:title` og
`og:description`, og bruk samme tagline overalt.

**K10. Dokumentasjonen peker på gamle navn.**

- `data/studio_papers.json:2` nevner `ki-studio.html` og
  `en/ai-studio.html`. Filene heter `studio.html` og `en/studio.html`.
- `dashboard/site/README.md:90` sier `v=20260907d`. Sidene bruker
  `20261014a`.

Retting: oppdater de to stedene.
