# Inkonsekvenser i W:\1191 — filnavn, nøkler og typer

**Kilde:** `datadoc/metadata_scan1191.csv` (skann av leveransen, 10.6.2026).
**Formål:** Samle alle kjente inkonsekvenser i filnavn, prefikser, nøkkelvariabler
og datatyper, slik at Stata-kode kan skrives defensivt og feil fanges før
serverkjøring. Oppdater dokumentet når nye leveranser endrer strukturen.

Kjør alltid `_dryrun_validate.py` (prosjektspesifikk variant) mot
`metadata_scan1191.csv` før kjøring på sikker sone.

---

## 1. Personnøkkelen: `lopenr_person` vs `w19_0345_lopenr_person`

Leveransen bruker **to navn på samme nøkkel**, uten system på tvers av registre:

- **448 aktive filer** bruker `w19_0345_lopenr_person`: hele `trygd/` (nav, sofa,
  syk_teller/nevner, f_*-forløpsfilene), `demo/`-kjernefilene (faste_oppl,
  ektef_sambo, regstat, familienr_sivilstand, slekt), `innt/formuesvariabler.dta`,
  `innt/innt.dta`, skattefilene 2023–2024, `utd/f_utd_*`, `kurs/`, og
  `bedr/bof_roller_*`.
- **~600 aktive filer** bruker `lopenr_person`: hele `atid/ameld_statdata_*`,
  `innt/inntekt_nodub*`, `demo/hush_fam_*` (t.o.m. 2023), m.fl.

Tilsvarende w19-varianter finnes for foretak/virksomhet: `w19_0345_lopenr_frtk`,
`_orgnr`, `_orgnrbed`, `_virk`. **Merk:** `lopenr_hush` og `lopenr_familie` har
*ikke* fått w19-prefiks noe sted.

### Nøkkelen skifter navn MIDT I en filfamilie

| Familie | `lopenr_person` | `w19_0345_lopenr_person` |
|---|---|---|
| `hush_fam_YYYY` | 2005–2023 | **2024–2025** |
| `ameld_utvalgte_YYYY_mM` | 2021m1–2025m8 | **2025m9, 2026m1** |
| `sivilstand_*` | 1975_2023, 2019_2022 | **1975_2025** |

Kode som looper over årganger i disse familiene krasjer når den treffer
overgangsåret. Bruk alltid det defensive mønsteret:

```stata
capture use w19_0345_lopenr_person <vars> using "<fil>", clear
if _rc == 0  rename w19_0345_lopenr_person lopenr_person
else use lopenr_person <vars> using "<fil>", clear
```

---

## 2. Filnavnkonvensjoner — fire ulike daterings-systemer

### Måned
| Mønster | Eksempel | Felle |
|---|---|---|
| `_YYYY_mM` (underscore, ikke nullpaddet) | `ameld_statdata_2023_m2.dta` | sorterer ikke kronologisk (m10 < m2) |
| `_YYYYmMM` (nullpaddet, ingen underscore) | `sofa_2018m01.dta` | — |
| `_nodubYYMM` (tosifret år!) | `sofa_nodub1801.dta` | år 18 ≠ 2018 uten kontekst |
| `_YYYYM` (ikke nullpaddet, ingen skilletegn) | `bof_roller_20231.dta` | **tvetydig**: `20231` = 2023m1, men `202310` = 2023m10; regex på `\d+` kan ikke skille år+måned uten lengdesjekk |

### Kvartal
- `nav_YYYYkQ` (`nav_2007k1.dta`) — uten prefiks på året
- `syk_teller_gYYYYkQ` / `syk_nevner_gYYYYkQ` (`syk_teller_g2000k2.dta`) — med `g`-prefiks

### Årstall: med/uten underscore — begge varianter aktive samtidig
- `aksjonaerer2004.dta` **og** `aksjonaerer_2004.dta` finnes begge i `bedr/`
  (14 + 19 filer) — to parallelle serier med nesten likt navn
- Samme for `aksjeselskap_YYYY` / `aksjeselskaperYYYY` / `aksjeselskaper_YYYY`
- `sivilstand1992_2019.dta` vs `sivilstand_1975_2023.dta` (med/uten underscore)
- Årsranger skrives både `kort_g2004g2015` (g-prefiks) og `kort_2019` (uten)

### Dedup-suffikset: `nodub` vs `nodup`, og plasseringen varierer
- Aktiv konvensjon: `nodub` limt til årstallet — `inntekt_nodub2017.dta`,
  `hush_fam_nodub2017.dta`, `sofa_nodub1801.dta`
- Gammel (i `hush_fam_bak/`): `nodup` etter årstallet — `hush_fam_2017_nodup.dta`
- Altså både **stavemåten** (nodub/nodup) og **posisjonen** (før/etter år) skiftet

### Avkuttede/feilskrevne navn
- `bedr/aksjeselskaper_fore_202.dta` — årstallet er kuttet (202?); 421 821 rader

---

## 3. Backup-mapper: tre navnekonvensjoner, og skjulte navnekollisjoner

Backup-/versjonsmapper heter `old`, `Old` **og** `*_bak`, avhengig av register:

| Mappe | Innhold |
|---|---|
| `atid/old` | ameld_statdata 2023 m2–m12 (gamle versjoner, **samme filnavn som aktive**) |
| `demo/Old` (stor O) | ektef_sambo, faste_oppl, regstat, familienr_sivilstand |
| `demo/hush_fam_bak` | hush_fam_YYYY_nodup (gammel navnekonvensjon) |
| `innt/old` | formuesvariabler, innt (gamle versjoner, samme navn) |
| `innt/innt_bak` | inntekt1993–2022 (gamle årsfiler med **gamle variabelnavn**) |
| `innt/formue_bak` | formue1994–2015 |
| `trygd/old` | 105 filer (f_*, syk_teller_*) — samme navn som aktive |
| `trygd/sofa_bak` | sofa1801–sofa2212 (uten nodub-suffiks) |
| `utd/old` | f_utd_demografi, f_utd_person — samme navn som aktive |

**Fellen:** mange filnavn finnes både aktivt og i backup (`faste_oppl.dta`,
`formuesvariabler.dta`, `f_utd_demografi.dta`, alle syk_teller …). Et søk på
filnavn alene (f.eks. i metadata) treffer begge — koden må alltid verifisere at
stien er den kanoniske (`innt/`, ikke `innt/innt_bak/`). `check_path()` i
`_dryrun_validate.py` gjør akkurat dette.

Kjente flyttinger i juni 2026-leveransen:

- `inntekt{år}.dta` → `innt/innt_bak/`; kanonisk er `inntekt_nodub{år}.dta`
- `hush_fam_{år}_nodup.dta` → `demo/hush_fam_bak/`; kanonisk er `hush_fam_nodub{år}.dta`

---

## 4. Samme filnavn, ULIKT innhold, i to aktive mapper

Dette er de farligste tilfellene — ingen feilmelding, bare feil data:

| Fil | Variant 1 | Variant 2 |
|---|---|---|
| `arv_gaver.dta` | `bedr/`: 132 113 rader | `innt/`: 220 587 rader |
| `tidspunktbestemte_var.dta` | `demo/`: 10,46 mill. rader, 90 var | `grkrets/`: 9,93 mill. rader, 84 var |

Referer alltid til disse med full mappe-sti, og dokumenter i koden hvilken
variant som er ment.

`contents.dta` ligger i fire mapper (atid, bedr, demo, innt) — det er
metadata-/oversiktsfiler, ulike per mappe; ufarlig, men gir støy i filsøk.

---

## 5. Variabelnavn-drift på tvers av årganger

### Gamle årsfiler (innt_bak) vs nodub-seriene
De gamle `inntekt{år}.dta` i `innt_bak/` bruker gamle navn; de aktive
`inntekt_nodub{år}.dta` er **standardisert til nye navn i alle årganger**
(1993–2022) — en av få ting som er konsistent:

| Gammelt (innt_bak) | Nytt (inntekt_nodub) |
|---|---|
| `wies` | `ies` |
| `arbled` | `arbledtrygd` |
| `wskfrovf` | `wskfrie_overf` |
| `bankinnsk`, `gjeld` | finnes kun i nodub2016/2017 (gamle navn beholdt der!) |

### Variabler som dukker opp/forsvinner i inntekt_nodub-serien
- `aap`, `uforetrygd`: finnes **kun fra 2016** (ordningen/rapporteringen ny)
- Balansevariabler (`bankinnsk`, `gjeld`, `prim_mark`, `sek_mark`): finnes kun i
  nodub**2016 og 2017**; fra 2018 ligger balansen i `formuesvariabler.dta`
  (med *nye* navn: `bankinnskudd`, `sum_gjeld`, `studiegjeld`, `usikret_gjeld`).
  En tidsserie over 2017/2018-grensen må altså bytte både fil og variabelnavn.
- `formuesvariabler.dta` dekker 2010–2024 (per juni 2026; tidligere 2018–2022 —
  dekningen har endret seg mellom leveranser, sjekk `aargang` først).

---

## 6. Datatype-inkonsekvenser (samme variabelnavn, ulik type)

88 variabelnavn har mer enn én type på tvers av aktive filer. De viktigste:

| Variabel | Typer | Kommentar |
|---|---|---|
| `kjoenn` | str1 (sofa_nodub m.fl.) / **str2** (faste_oppl, dnr_stat) | har også vært numerisk i egne avledede filer — bruk `capture confirm string variable` |
| `kommnr` | str4 / str6 | str6-variantene (eldre atmlto) har trolig grunnkrets el. annet vedheng |
| `aar` | double / str2 / str4 / str8 | str2 = tosifret år i sofa_nodub! |
| `aargang` | str4 overalt (innt) | konsistent — men string, så `aargang == "2021"`, ikke `== 2021` |
| `alder` | double / str4 / str6 | |
| `fnr_dat`, `bnrdato`, `statdat` | double / str8 / str10 / str12 | datoformat varierer mellom registre |
| `sektor`, `reg_type`, `samm_kod` | double / str | |

**Regel:** test alltid type før sammenligning eller `real()`-konvertering når en
variabel hentes fra mer enn én fil/årgang.

---

## 7. Andre strukturelle observasjoner

- `sofa_YYYYmM` (6 var) og `sofa_nodubYYMM` (8 var) er **parallelle serier over
  samme måneder** med litt ulikt radantall (f.eks. 2018m01: 478 212 vs 478 251).
  nodub-serien har flere variabler; avklar hvilken som er kanonisk før bruk.
- `faste_oppl.dta` finnes i varianter med `forstdato` vs `forst_aar_mnd`
  (innvandringsdato skiftet navn mellom versjoner) og kan ha duplikate personer
  → dedup på `doeds_aar_mnd` før 1:1-merge.
- Dedupliserte (`nodub`) og rå versjoner eksisterer side om side i samme mappe
  (`hush_fam_2017.dta` og `hush_fam_nodub2017.dta`) — bruk nodub, men vit at
  også nodub-filer kan ha duplikate personer (gjelder hush_fam_nodub2017).

---

## 8. Kjøreregler (oppsummert)

1. **Defensiv nøkkel-lesing** (capture/rename-mønsteret i §1) for alle filer i
   `demo/`, `innt/`, `trygd/`, `utd/`, `kurs/` — og fra 2024-årgangen også `hush_fam`.
2. **Full sti, aldri bare filnavn** — sjekk at filen ligger kanonisk og ikke i
   `old/`, `Old/` eller `*_bak/`, og vær eksplisitt for `arv_gaver` og
   `tidspunktbestemte_var` som har ulikt innhold per mappe.
3. **Typetest før sammenligning** for `kjoenn`, `kommnr`, `aar`, datovariabler.
4. **`aargang` er alltid str4** — sammenlign mot streng.
5. **Dedup etter innlasting** av faste_oppl, ektef_sambo, hush_fam_nodub*.
6. **Dry-run mot metadata_scan1191.csv** før hver serverkjøring; legg til en
   sjekk per ny fil-/variabelreferanse i koden.
