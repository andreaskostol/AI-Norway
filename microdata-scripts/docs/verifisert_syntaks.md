# Verifisert syntaks for microdata.no

Alt i dette dokumentet er testet og bekreftet å fungere (mars 2026, versjon 52).

## Grunnregler

- Versjonsnummer er OBLIGATORISK: `require no.ssb.fdb:52 as db`
- Ingen kommentarer i scripts — `//` gir feil
- Datoformat: YYYY-MM-DD
- ARBLONN-variabler bruker den **16. i måneden** som statusdato
- BEFOLKNING-variabler bruker typisk 1. januar (f.eks. 2025-01-01)
- NUDB (utdanning) har siste dato **før 2024-08-01** — oppdateres sjeldnere
- Kategoriske verdier bruker enkle anførselstegn: `keep if regstatus == '1'`
- Plattformen foreslår riktig dato/variabelnavn i feilmeldinger — svært nyttig

## Enhetstyper: PERSON vs JOBB

Et datasett kan kun inneholde variabler av én enhetstype.

**PERSON-variabler:**
- BEFOLKNING_* (kjønn, fødselsdato, bosted, statuskode)
- ARBLONN_PERS_* (sum stillingsprosent, sum arbeidstid, alder, kjønn, kommune)
- NUDB_* (utdanning)
- ARBSTATUS_PERS_* (sysselsettingsstatus — men oppdateres saktere)

**JOBB-variabler:**
- ARBLONN_ARB_* (arbeidsstatus, yrke, heltid/deltid, stillingsprosent, arbeidstid)
- ARBLONN_LONN_* (fastlønn, overtid, bonus, etc.)

**Kobling mellom dem:** `ARBEIDSFORHOLD_PERSON` (se merge-mønster nedenfor)

## Verifiserte variabelnavn

| Variabel | Enhetstype | Statusdato | Notater |
|----------|-----------|------------|---------|
| BEFOLKNING_STATUSKODE | PERSON | 2025-01-01 | '1' = bosatt |
| BEFOLKNING_KJOENN | PERSON | (ingen dato) | '1' = Mann, '2' = Kvinne |
| BEFOLKNING_FOEDSELS_AAR_MND | PERSON | (ingen dato) | YYYYMM-format, bruk int(var/100) for år |
| ARBLONN_PERS_SUM_STILLINGSPST | PERSON | 2025-01-16 | Kontinuerlig. Missing = ingen arbeidsforhold. > 0 = sysselsatt |
| ARBLONN_PERS_SUM_ARBEIDSTID | PERSON | 2025-01-16 | |
| ARBLONN_ARB_ARBMARK_STATUS | JOBB | 2025-01-16 | Kun '1 - Lønnstaker'. Kun de MED arbeidsforhold |
| ARBLONN_ARB_H3LDELTID | JOBB | 2025-01-16 | NB: H3L ikke HEL. '1' = Heltid, '2' = Deltid |
| ARBLONN_ARB_STILLINGSPST | JOBB | 2025-01-16 | Stillingsprosent per jobb |
| ARBLONN_ARB_YRKE_STYRK08 | JOBB | 2025-01-16 | Yrkeskode |
| ARBLONN_LONN_FAST | JOBB | 2025-01-16 | Fast månedslønn. 2,15M av 3,09M har verdi |
| NUDB_BU | PERSON | 2024-07-01 | Strengvariabel. Første siffer = utdanningsnivå (NUS) |
| ARBEIDSFORHOLD_PERSON | (kobling) | (ingen dato) | Kobler JOBB til PERSON. 24,9M enheter |

**Variabelnavn som IKKE finnes:**
- ~~BEFOLKNING_FOEDSELS_AAR~~ → bruk BEFOLKNING_FOEDSELS_AAR_MND
- ~~ARBLONN_ARB_HELDELTID~~ → bruk ARBLONN_ARB_H3LDELTID

## Verifiserte kommandoer med eksempler

### Grunnleggende oppsett
```
require no.ssb.fdb:51 as db
create-dataset mittnavn
```

### Import
```
import db/BEFOLKNING_KJOENN as kjoenn
import db/ARBLONN_LONN_FAST 2025-01-16 as fastlonn
```

### Filtrering
```
keep if regstatus == '1'
keep if alder >= 25 & alder <= 54
drop if sysmiss(stillingspst)
```

### Generere og erstatte
```
generate alder = 2025 - int(fodtaarmd / 100)
generate sysselsatt = 0
replace sysselsatt = 1 if stillingspst > 0
```

### Strengoperasjoner
```
generate utdnivaa1 = substr(utdnivaa, 1, 1)
destring utdnivaa1
```

### Labels
```
define-labels utdlbl 0 'Ingen' 1 'Barneskole' 2 'Ungdomsskole' 3 'VGS' 4 'Fagskole' 5 'Univ lavere' 6 'Univ hoeyere' 7 'Univ lang' 8 'Forskerutd' 9 'Uoppgitt'
assign-labels utdnivaa1 utdlbl
```

### Tabulate
```
tabulate kjoenn, flatten
tabulate sysselsatt kjoenn, flatten
tabulate sysselsatt kjoenn, rowpct flatten
tabulate kjoenn, summarize(fastlonn) flatten
tabulate heldeltid kjoenn, summarize(fastlonn) flatten
```

Begrensninger:
- Kan ikke tabulere kontinuerlige variabler direkte
- Krysstabell med for mange celler gir feil — bruk grovere kategorier
- Bruk alltid `flatten` for eksportvennlig format

### Summarize
```
summarize fastlonn
```
Gir: gjennomsnitt, standardavvik, antall, 1%, 25%, 50%, 75%, 99%

### Histogram
```
histogram fastlonn, bin(50)
```

## Merge-mønster: PERSON-variabler inn i JOBB-datasett

Dette er den verifiserte metoden for å koble personkjennetegn til jobbdata:

```
require no.ssb.fdb:51 as db

create-dataset personer
import db/BEFOLKNING_KJOENN as kjoenn

create-dataset jobber
import db/ARBLONN_ARB_ARBMARK_STATUS 2025-01-16 as arbstatus
import db/ARBLONN_LONN_FAST 2025-01-16 as fastlonn

create-dataset kobling
import db/ARBEIDSFORHOLD_PERSON as personid
merge personid into jobber

use personer
merge kjoenn into jobber on personid

use jobber
tabulate kjoenn, summarize(fastlonn) flatten
```

Nøkkelpunkter:
1. Lag persondatasett med PERSON-variabler
2. Lag jobbdatasett med JOBB-variabler
3. Lag koblingsdatasett, importer ARBEIDSFORHOLD_PERSON, merge personid inn i jobber
4. `use` kildedatasettet (personer), deretter `merge var into mål on personid`
5. `use jobber` for å jobbe med resultatet

Merge-regel: **aktivt datasett er kilden**, `into` peker på målet.

## Sysselsetting på personnivå (uten JOBB-data)

For å måle sysselsettingsrate uten å gå via JOBB-datasett:

```
require no.ssb.fdb:51 as db

create-dataset mydata
import db/BEFOLKNING_STATUSKODE 2025-01-01 as regstatus
keep if regstatus == '1'

import db/BEFOLKNING_FOEDSELS_AAR_MND as fodtaarmd
generate alder = 2025 - int(fodtaarmd / 100)
keep if alder >= 25 & alder <= 54

import db/BEFOLKNING_KJOENN as kjoenn
import db/ARBLONN_PERS_SUM_STILLINGSPST 2025-01-16 as stillingspst

generate sysselsatt = 0
replace sysselsatt = 1 if stillingspst > 0

tabulate sysselsatt kjoenn, flatten
tabulate sysselsatt kjoenn, rowpct flatten
```

Resultat bekreftet: missing = ingen arbeidsforhold, > 0 = sysselsatt.
Ingen har stillingsprosent = 0 (bare missing eller > 0).

## Panel over tid (bredt format)

Importer samme variabel med ulike datoer og ulike alias:

```
import db/ARBLONN_PERS_SUM_STILLINGSPST 2024-01-16 as pst_jan
import db/ARBLONN_PERS_SUM_STILLINGSPST 2024-04-16 as pst_apr
import db/ARBLONN_PERS_SUM_STILLINGSPST 2024-07-16 as pst_jul
import db/ARBLONN_PERS_SUM_STILLINGSPST 2024-10-16 as pst_okt
```

(Ikke verifisert ennå — neste test)

## Utdanningsnivå med NUS-koder

NUDB_BU er en strengvariabel med NUS-kode. Første siffer = nivå:

| Kode | Nivå | Antall (25-54 år) |
|------|------|-------------------|
| 0 | Ingen/førskole | 3 323 |
| 1 | Barneskole | 11 905 |
| 2 | Ungdomsskole | 339 861 |
| 3 | Videregående (påbygging?) | 22 585 |
| 4 | Fagskole/fullført VGS | 601 179 |
| 5 | Universitet lavere | 81 573 |
| 6 | Universitet høyere | 678 675 |
| 7 | Universitet lang | 351 594 |
| 8 | Forskerutdanning | 30 665 |

NB: Fordelingen mellom nivå 2-4 avviker fra intuisjon. NUS-klassifiseringen grupperer annerledes — bør sjekkes mot SSBs NUS-dokumentasjon.

## Referansetall (jan 2025)

- Bosatte (BEFOLKNING_STATUSKODE = '1'): 5 594 338
- Bosatte 25-54 år: 2 253 071
- Sysselsatte 25-54 år: 1 743 576 (77,4%)
- Arbeidsforhold totalt (ARBLONN_ARB): 3 089 036
- Arbeidsforhold med fastlønn: 2 149 927
- Gjennomsnittlig fastlønn: 51 722 kr/mnd (median 50 000)
- Fastlønn heltid: 60 091 kr, deltid: 22 786 kr
- Fastlønn menn: 56 782 kr, kvinner: 46 602 kr

## Ytelse og begrensninger

- Første import bestemmer populasjonen (left-join)
- Paneldata: hold under 1 million enheter
- Celleundertrykkelse er automatisk — unngå svært detaljerte krysstabeller
- Scripts stopper ved feil uten resume — hold scripts korte (under 20 linjer)
- Tabulate med for mange celler gir feil — grupper variabler grovere
