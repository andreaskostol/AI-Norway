# Eloundou GPT-4 beta: vekting, kildeproveniens og krav til dokumentasjon

**Revisjonsdato:** 9. august 2026  
**Formål:** Fastslå hvilken oppgavevekting som ligger i `dv_rating_beta`, forklare
forskjellen mellom artikkel, supplement, notebook og publisert CSV, og angi hva
som må dokumenteres i AI-Norway-paperet.

## Konklusjon

`dv_rating_beta` i den publiserte `occ_level.csv` er **core-vektet**, ikke
likt vektet. Dette kan fastslås numerisk for alle 923 O*NET-yrkene i filen:

- core-vektet rekonstruksjon matcher 923 av 923 yrkesskårer;
- største absolutte avvik er `1.11e-16`, det vil si flyttallsavrunding;
- likt vektet rekonstruksjon matcher bare 233 av 923;
- gjennomsnittlig absolutt avvik ved lik vekting er `0.010785`;
- største avvik ved lik vekting er `0.107143`.

Den tilsynelatende inkonsistensen gjelder derfor ikke hovedmetoden i den
publiserte artikkelen. Artikkelen og supplementet angir core-vekting tydelig,
og den publiserte yrkesfilen følger denne metoden eksakt. Problemet er at den
synlige standardinnstillingen i kode-notebooken er `equal_weight`, mens
yrkesfilen ble lagt til senere og er core-vektet. Det er et hull i
reproduserbarhetsproveniensen i repositoriet, ikke en tvetydighet i den
publiserte metodebeskrivelsen.

## Hvem står bak artikkelen og repositoriet?

Uttrykket «OpenAI-repositoriet» er teknisk forståelig fordi repositoriet ligger
under GitHub-organisasjonen `openai`:
<https://github.com/openai/GPTs-are-GPTs>.

Uttrykket kan likevel gi et misvisende inntrykk av forfatterskapet. En mer
presis formulering er:

> forfatternes offentlige kode- og datarepository under OpenAIs
> GitHub-organisasjon

Ifølge den publiserte supplementfilen var forfattertilknytningene:

- Tyna Eloundou — OpenAI;
- Sam Manning — Centre for the Governance of AI;
- Pamela Mishkin — OpenAI;
- Daniel Rock — University of Pennsylvania, Wharton School.

Forfattergruppen var altså ikke uavhengig av OpenAI, men heller ikke en ren
OpenAI-gruppe. To av fire forfattere var oppført med OpenAI-tilknytning.

Lokal kilde:
[`Eloundou Manning Mishkin Rock 2024 GPTs are GPTs-supplementary.md`](../../../literature/Eloundou%20Manning%20Mishkin%20Rock%202024%20GPTs%20are%20GPTs-supplementary.md).

## Hva den publiserte metoden sier

Hovedartikkelen sier at O*NETs «Supplemental»-oppgaver får halvparten så stor
vekt som «Core»-oppgaver, med mindre annet er oppgitt. Supplementets avsnitt
9.3 presiserer standardmetoden:

- Core-oppgave: vekt 2;
- Supplemental eller uklassifisert oppgave: vekt 1;
- vektene normaliseres innen hvert detaljert O*NET-yrke;
- lik vekting brukes i enkelte alternative analyser og skal da angis.

For GPT-4-betaen som AI-Norway bruker, er oppgaveskåren

\[
s_t = 1\{E1_t\} + 0.5\,1\{E2_t\},
\]

og yrkesskåren er

\[
\beta_o =
\frac{\sum_{t\in o} w_t s_t}{\sum_{t\in o}w_t},
\qquad
w_t =
\begin{cases}
2 & \text{Core},\\
1 & \text{Supplemental eller uklassifisert}.
\end{cases}
\]

Det er derfor mest presist å si at `E1` og `E2` i yrkesformelen er
**core-vektede andeler av oppgavene**, ikke uvektede oppgaveandeler.

Lokale kilder:

- [`Eloundou Manning Mishkin Rock 2024 GPTs are GPTs.md`](../../../literature/Eloundou%20Manning%20Mishkin%20Rock%202024%20GPTs%20are%20GPTs.md), metodeavsnittet om O*NET-oppgaver;
- [`Eloundou Manning Mishkin Rock 2024 GPTs are GPTs-supplementary.md`](../../../literature/Eloundou%20Manning%20Mishkin%20Rock%202024%20GPTs%20are%20GPTs-supplementary.md), avsnitt 9.3.

## Numerisk kontroll av den publiserte CSV-filen

Kontrollen kombinerte følgende filer fra det offentlige repositoriet:

- `data/full_labelset.tsv`: E0/E1/E2-klassifisering på oppgavenivå;
- `data/full_onet_data.tsv`: Core/Supplemental-status;
- `data/occ_level.csv`: publisert `dv_rating_beta` på yrkesnivå.

For hvert av 923 detaljerte O*NET-yrker ble beta beregnet både med lik
oppgavevekt og med 2:1 core-vekting. Resultatet var:

| Kontroll | Likt vektet | Core-vektet |
|---|---:|---:|
| Eksakte treff av 923 | 233 | 923 |
| Gjennomsnittlig absolutt avvik | 0.010785 | `1.16e-17` |
| Største absolutte avvik | 0.107143 | `1.11e-16` |

At 233 yrker også matcher under lik vekting, skyldes blant annet yrker der
fordelingen av etiketter ikke påvirkes av forskjellen mellom Core og
Supplemental. Disse treffene er derfor ikke evidens for at CSV-filen er likt
vektet.

Som konkret eksempel har O*NET 27-3031.00, *Public Relations Specialists*:

- likt vektet beta: `0.583333`;
- core-vektet beta: `0.590909`;
- publisert `dv_rating_beta`: `0.590909`.

### Kontrollerte versjoner

- `occ_level.csv`, Git-commit `9ed4148` (filen lagt til som yrkesskårer i
  `2c98447` og deretter omdøpt): SHA-256
  `5A7184B0B7C6B36109276DC4B29349A2FA71C6E38B5180C984ACEBE772A26FFC`;
- `full_labelset.tsv`, Git-commit `36af7ac`: SHA-256
  `4358FFBD5C52912FE589C6F7C38EB03FAB4B3A1115840D3530021618AFA137BD`;
- lokal `data/ai_exposure/eloundou_occ_level.csv` har samme tabellinnhold som
  den offentlige filen; den rå SHA-256-en avviker på grunn av linjesluttformat;
- lokal ferdig STYRK-mapping
  `styrk08_eloundou_beta_mapping.csv`: SHA-256
  `F5C9491965AD5E4218E7EE58B3561720EA2F03545F96778B03E73E0DA48AC1DF`.

## Hvor notebooken skaper forvirring

Den innsjekkede notebooken `code/gpts_are_gpts_script1.ipynb` har den synlige
innstillingen:

```python
weight_field = "equal_weight"
```

Notebooken inneholder samtidig kode for både `equal_weight`, `core_weight`,
relevansvekt og viktighetsvekt, og senere celler beregner blant annet
`core_weighted_avg_gpt4_rating`.

Git-historikken er viktig:

- notebooken og oppgavefilene ble lagt inn 20. juni 2024;
- yrkesskårene ble først lagt inn 3. oktober 2025;
- den senere `occ_level.csv` kan reproduseres eksakt med core-vekting, men ikke
  med notebookens synlige `equal_weight`-valg.

Den sikreste tolkningen er at CSV-filen er produsert med core-grenen eller en
ekvivalent beregning, men at repositoriet ikke bevarer den eksakte notebook-
tilstanden som genererte filen. Vi bør derfor ikke bruke notebookens synlige
standard som dokumentasjon av `dv_rating_beta`. Metodebeskrivelsen,
supplementet og numerisk rekonstruksjon er samstemte og sterkere evidens.

## Hva AI-Norway gjør etter at yrkesskåren er lest inn

Core-vektingen skjer hos Eloundou et al. **innen det detaljerte O*NET-yrket**.
AI-Norways mappingkode leser den ferdige, allerede core-vektede
`dv_rating_beta`. Deretter brukes enkle gjennomsnitt på andre
aggregeringsnivåer:

1. O*NETs detaljsuffiks `.XX` fjernes for å få sekssifret SOC 2018. Hvis flere
   detaljyrker har samme SOC-kode, tas et uvektet gjennomsnitt av deres allerede
   core-vektede yrkesskårer.
2. SOC 2018 kobles til SOC 2010 og videre til ISCO-08/STYRK-08. Når flere
   kildeyrker bidrar til samme målyrke, tas et uvektet gjennomsnitt av de
   allerede oppgavevektede yrkesskårene.
3. STYRK-08-yrkene deles i kvintiler med lik vekt per yrkeskode, ikke etter
   sysselsettingsandel.

«Uvektet» i AI-Norways mappingkode viser altså til aggregering **mellom
yrkesskårer**. Det opphever ikke core-vektingen **mellom oppgaver innen yrke**.

Lokal kode:
[`build_eloundou_mapping.py`](../../../analysis/03_mappings/build_eloundou_mapping.py).

## Endringer som trengs for korrekt paper-dokumentasjon

- [ ] **Metodeavsnittet i `paper_dashboard_v8.tex`:** Skriv eksplisitt at
  `dv_rating_beta` er et core-vektet oppgavegjennomsnitt med vekt 2 for Core og
  1 for Supplemental/uklassifisert. Presiser at `E1` og `E2` er de tilsvarende
  vektede oppgaveandelene.
- [ ] **Skill mellom tre vektingsnivåer:** Dokumenter separat (a) upstream
  core-vekting av oppgaver, (b) lokal uvektet aggregering av allerede vektede
  O*NET/SOC-yrkesskårer og (c) equal-occupation-kvintiler. Unngå ordet
  «unweighted» uten å angi nivået.
- [ ] **Tabell 1:** Utvid definisjonen av Eloundou-beta i
  `analysis/output/tables/table1_measures.tex` med «Core tasks weight 2;
  Supplemental/unclassified tasks weight 1». Tabellen er håndholdt ifølge
  `paper/to_RA/README.md`.
- [ ] **Mappingdokumentasjonen:** Oppdater
  `data/ai_exposure/docs/mapping_methodology.md` og
  `styrk08_all_exposure_measures_README.md`, som nå definerer beta som
  `E1 + 0.5 E2` uten å oppgi upstream oppgavevekting.
- [ ] **Kodedokumentasjonen:** Utvid docstringen i
  `analysis/03_mappings/build_eloundou_mapping.py` og kommentaren ved
  `dv_rating_beta` med at kolonnen er core-vektet i kildefilen. Forklar at
  gjennomsnittet etter fjerning av `.XX` er et separat, lokalt og uvektet
  gjennomsnitt av ferdige yrkesskårer.
- [ ] **Kildeversjon:** Fest `occ_level.csv` til commit eller SHA-256 i
  reproduksjonspakken. En flytende `main`-URL er ikke nok til å sikre samme
  input ved senere replikasjon.
- [ ] **Automatisert kontroll:** Legg inn en liten audit-test som rekonstruerer
  beta fra `full_labelset.tsv` og `full_onet_data.tsv` og krever samsvar med
  `occ_level.csv` for alle 923 yrker. Testen bør også vise at equal-weight ikke
  er brukt.
- [ ] **Reproduserbarhetsmerknad:** Nevn kort at den innsjekkede notebookens
  synlige `weight_field` ikke dokumenterer den senere CSV-filens run-state.
  Dette hører hjemme i README/metodedokumentasjon, ikke nødvendigvis i
  hovedteksten.
- [ ] **RA-pakken:** Når tekst og kode er oppdatert, bygg `paper/to_RA` på nytt
  slik at mappingkode, Tabell 1, README, manifest og checksums er konsistente
  med paperet.
- [ ] **Sitering:** Siter både hovedartikkelen og Supplementary Materials
  section 9.3 for vektingen. Repositoriet skal brukes som datakilde og
  versjonsreferanse, ikke som eneste metodereferanse.

## Forslag til formulering i paperet

> We use the released GPT-4 occupation-level beta score
> (`dv_rating_beta`). Within each detailed O*NET occupation, the score is the
> weighted mean of task labels, assigning 1 to E1, 0.5 to E2, and 0 to E0;
> Core tasks receive weight 2 and Supplemental or unclassified tasks weight
> 1. When multiple detailed O*NET occupations collapse to the same six-digit
> SOC code, and when multiple source SOC codes map to the same STYRK-08 code,
> we take the unweighted mean of these already task-weighted occupation
> scores. We then form equal-occupation quintiles over the resulting STYRK-08
> scores.

## Kilder og revisjonsspor

- Eloundou, Manning, Mishkin og Rock (2024), *Science*, DOI
  <https://doi.org/10.1126/science.adj0998>.
- Offentlig kode og data:
  <https://github.com/openai/GPTs-are-GPTs>.
- Publisert yrkesfil ved kontrollert commit:
  <https://github.com/openai/GPTs-are-GPTs/blob/9ed4148/data/occ_level.csv>.
- Notebook ved første innsjekking:
  <https://github.com/openai/GPTs-are-GPTs/blob/1ec076d/code/gpts_are_gpts_script1.ipynb>.
- AI-Norway-kildefil:
  [`eloundou_occ_level.csv`](../eloundou_occ_level.csv).
- AI-Norway-mapping:
  [`styrk08_eloundou_beta_mapping.csv`](../styrk08_eloundou_beta_mapping.csv).
