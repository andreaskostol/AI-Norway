# FD-Trygd forløpsfiler — bruksanvisning og fallgruver

Denne noten beskriver hvordan FD-Trygd forløpsfiler (`f_aap`, `f_rehab`,
`f_attf`, `f_tu`, `f_fufor`, `f_ufp`, `f_shj`, `f_kvalif`, m.fl.) bør
brukes, og dokumenterer dekningsmangler vi har oppdaget.

## Strukturen i FD-Trygd spell-filer

Hver hendelse i et forløp registreres som en **separat linje** i filen.
Typisk vil ett forløp generere minst to linjer:

1. **Oppstartslinje**: `tilgdato` er satt, `avgdato` er missing.
   Registreres når personen først tilstår ytelsen.
2. **Avslutningslinje** (eller endringslinje): både `tilgdato` og
   `avgdato` er satt. Registreres når forløpet avsluttes eller
   gradering/type endres.

Dette betyr at **man ikke bare kan bruke `avgdato` direkte per rad** —
oppstartslinjen har per definisjon manglende avgdato.

### Riktig håndtering ved bestandstelling ("er personen aktiv i måned M?")

For hvert forløp må man bestemme en gyldig `(start, stopp)`-intervall:

**A. Eksplisitt avsluttede forløp:** Hvis personen har minst én linje
med satt `avgdato`, er avslutningen eksplisitt registrert. Slett alle
linjer med manglende `avgdato` for denne personen (de er
oppstartslinjer som er duplisert av avslutningslinjen).

**B. Høyresensurerte forløp:** Hvis personen kun har linjer med
manglende `avgdato`, er forløpet sensurert (registreringen avsluttes
før vi observerte slutten). Da settes `avgdato` til siste observerte
`avgdato` i hele filen — som er beste estimat for når registeret
slutter.

### Feil man bør unngå

- **Sette `avgdato = 99999` (eller stor verdi) for alle missing:**
  Gjør at oppstartslinjer og sensurerte forløp blir behandlet som
  "evige", og bestanden akkumuleres urealistisk over tid.
- **Beholde alle linjer som separate spells:** En person med to
  registreringslinjer (oppstart + slutt) for samme forløp blir talt to
  ganger.
- **Bruke `tilgdato` på avslutningslinjen som forløpsstart:** Den
  refererer til det samme forløpet — men dersom gradering endres
  underveis, kan tilgdato være forskjellig fra oppstartslinjen. For
  sikkerhet: ta `min(tilgdato)` per person per forløp.

### Stata-implementasjon

```stata
* Bygg (start, stopp) per person fra råforløp-fil
use lopenr_person tilgdato avgdato using "$raw\trygd\f_XXX.dta", clear

gen int start_mnd = floor(tilgdato/100)*12 + mod(tilgdato, 100) ///
    if tilgdato != . & tilgdato > 100
gen int stopp_mnd = floor(avgdato/100)*12 + mod(avgdato, 100) ///
    if avgdato != . & avgdato > 100
drop if start_mnd == .

* (A) Har personen minst én linje med avgdato? Slett oppstartslinjer
bysort lopenr_person: egen byte har_avg = max(stopp_mnd != .)
drop if har_avg == 1 & stopp_mnd == .
drop har_avg

* (B) Resten (kun oppstartslinjer) → sett stopp til siste observerte
qui sum stopp_mnd
replace stopp_mnd = `r(max)' if stopp_mnd == .
```

## Tidsdekning per register (fra SSB variabelliste)

**Kritisk for riktig analyse av AAP-reformen 1. mars 2010:**

| Register | Dekning | Kommentar |
|---|---|---|
| `f_aap` | 2010–2024 | Innført ved reformen |
| `f_rehab` | 2002–2010 | Medisinsk rehabilitering. Slutter ved reform |
| `f_attf` | **1992–2001** | **OBS! Dekker ikke 2002–2010!** |
| `f_tu` | 2004–2010 | Tidsbegrenset uførestønad. Slutter ved reform |
| `f_fufor` | 1992–2010 | Foreløpig uførestønad. Slutter ved reform |
| `f_ufp` | 1992–2010 | Uførepensjon (før 2015-reformen) |
| `f_pensj_ufp` | 2011–2024 | Uførepensjon/uføretrygd (fra FD-Trygd-omorganisering) |
| `f_shj` | 1992–2024 | Sosialhjelp |
| `f_kvalif` | 2008–2024 | Kvalifiseringsstønad (KVP) |

## KRITISK: Attføring 2002–2010 må hentes fra `sofastat`

`f_attf` dekker bare 1992–2001. Fra 2002 ble medisinsk rehabilitering
skilt ut til `f_rehab`, men det finnes **ingen separat
attføringspenger-forløpsfil** for 2002–2010. Attføringspenger i denne
perioden finnes kun i arbeidssøkerregisteret:

### Hvor ligger attføring 2002–2010?

- **`sofastat1989_2012.dta`** (wide format): Månedlige statuskoder
  `stat1`..`stat288` (stat145 = jan 2001, stat288 = des 2012). Bruk
  `strpos(stat{N}, "AT") > 0` for å finne attføring-måneder.
- **`sofa{YYYY}.dta`** (long format, 2001–2012): Bruk
  `as_ytelse == "AP"` for attføringspenger (ikke `as_hoved`, og ikke
  "AT" som man kanskje skulle tro — koden er "AP").

### Konsekvens ved å ignorere dette

Hvis man bygger en union over "helserelaterte ytelser" kun fra
`f_aap`, `f_rehab`, `f_attf`, `f_tu` og `f_fufor`, vil man få:

- Nesten ingen attføring-mottakere pre-reform 2002–2010 (kun restene
  fra f_attf 2001-kohorten).
- Alle attføring-mottakere post-reform (fordi de ble overført til
  `f_aap`).

Dette ser ut som et massivt reform-hopp, men er i realiteten bare en
registreringsartefakt. I robek_aap-prosjektet så vi opprinnelig en
"reformeffekt" på AAP-hazarden på +0.028 per måned. Etter å ha lagt
til sofastat AT og sofa `as_ytelse=="AP"` i unionen falt tallet
dramatisk.

### Riktig oppskrift

```stata
* Bygg attføring-union fra sofastat (2001-2012) + f_attf (1992-2001)
* Se robek_aap/code/00b_forbered_attf.do for full implementasjon
```

## Generell lærdom

1. **Gjør rå opptelling av bestandstall per register per måned
   FØR du bygger analyseutvalg.** Enhver kunstig diskontinuitet
   (hopp, knekk, sesong som forsvinner) er et varseltegn.
2. **Les SSB variabelliste først.** Dekningsintervallene
   (`fra_aar`/`til_aar`) avslører om et register dekker perioden du
   tror det gjør.
3. **Kryss-valider mellom registre.** f_attf og sofa-AT skal fange opp
   samme populasjon i overlappende perioder — sammenlign dem.
4. **Test spell-håndteringen.** Hvis bestanden vokser monotont innen
   ett år uten å falle, har du sannsynligvis ikke håndtert sensurerte
   spells riktig.
