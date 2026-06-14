# Variabeloversikt — arbeidsmarked (A-ordningen)

Databank: `no.ssb.fdb`
Kilde: A-ordningen (månedlige data fra jan 2015)
Enhet: Arbeidsforhold (jobb) eller person, avhengig av variabel
Koblingsvariabel mellom jobb og person: `ARBEIDSFORHOLD_PERSON`

## Personvariabler (ARBLONN_PERS_*)

| Variabel | Beskrivelse | Type |
|----------|-------------|------|
| ARBLONN_PERS_ALDER | Alder | Numerisk |
| ARBLONN_PERS_KJOENN | Kjønn | Kategorisk |
| ARBLONN_PERS_KOMMNR | Bostedskommune | Kategorisk |
| ARBLONN_PERS_KOMMNR_KILDE | Kilde for kommune | Kategorisk |
| ARBLONN_PERS_BOSETT_STATUS | Bosatt/pendler | Kategorisk |
| ARBLONN_PERS_STATSBORGERSKAP | Statsborgerskap | Kategorisk |
| ARBLONN_PERS_DNR | Permanent/midlertidig ID | Kategorisk |
| ARBLONN_PERS_SUM_STILLINGSPST | Sum stillingsprosent alle jobber | Numerisk |
| ARBLONN_PERS_SUM_ARBEIDSTID | Sum arbeidstid alle jobber | Numerisk |
| ARBLONN_PERS_BOTID_FORST | Botid siden første registrering | Numerisk |
| ARBLONN_PERS_BOTID_SISTE | Botid siden siste registrering | Numerisk |

## Arbeidsforholdvariabler (ARBLONN_ARB_*)

| Variabel | Beskrivelse | Type |
|----------|-------------|------|
| ARBLONN_ARB_ARBMARK_STATUS | Arbeidsmarkedsstatus | Kategorisk |
| ARBLONN_ARB_SYSS | Sysselsettingsstatus (kurert) | Kategorisk |
| ARBLONN_ARB_HOVEDARBEID | Hoved-/biarbeidsforhold | Kategorisk |
| ARBLONN_ARB_YRKE_STYRK08 | Yrkeskode (STYRK08) | Kategorisk |
| ARBLONN_ARB_TYPE | Type arbeidsforhold | Kategorisk |
| ARBLONN_ARB_ANSETTELSESFORM | Ansettelsesform | Kategorisk |
| ARBLONN_ARB_H3LDELTID | Heltid/deltid | Kategorisk |
| ARBLONN_ARB_TID_ORDNING | Arbeidstidsordning (skift etc.) | Kategorisk |
| ARBLONN_ARB_STILLINGSPST | Stillingsprosent (kurert) | Numerisk |
| ARBLONN_ARB_STILLINGSPST_INNRAPP | Stillingsprosent (innrapportert) | Numerisk |
| ARBLONN_ARB_STILLINGSPST_KILDE | Kilde for stillingsprosent | Kategorisk |
| ARBLONN_ARB_ARBEIDSTID | Ukentlig arbeidstid | Numerisk |
| ARBLONN_ARB_TIMEANT_FULLTID | Fulltidstimer (kurert) | Numerisk |
| ARBLONN_ARB_TIMEANT_FULLTID_INNRAPP | Fulltidstimer (innrapportert) | Numerisk |
| ARBLONN_ARB_START | Startdato | Dato |
| ARBLONN_ARB_SLUTT | Sluttdato | Dato |
| ARBLONN_ARB_SLUTTAARSAK | Sluttårsak | Kategorisk |
| ARBLONN_ARB_KILDE | Datakilde | Kategorisk |
| ARBLONN_ARB_ARBKOMM | Arbeidsstedskommune | Kategorisk |

## Lønnsvariabler (ARBLONN_LONN_*)

| Variabel | Beskrivelse | Type |
|----------|-------------|------|
| ARBLONN_LONN_FAST | Fast månedslønn (kurert) | Numerisk |
| ARBLONN_LONN_FAST_INNRAPP | Fast månedslønn (innrapportert) | Numerisk |
| ARBLONN_LONN_FAST_TILLEGG | Faste tillegg | Numerisk |
| ARBLONN_LONN_OVERTID | Overtidsgodtgjørelse | Numerisk |
| ARBLONN_LONN_OVERTID_TIMER | Overtidstimer | Numerisk |
| ARBLONN_LONN_BONUS | Bonus | Numerisk |
| ARBLONN_LONN_FERIE | Feriepenger | Numerisk |
| ARBLONN_LONN_GODTGJORELSE | Godtgjørelse | Numerisk |
| ARBLONN_LONN_TIME | Timelønn | Numerisk |
| ARBLONN_LONN_TIME_ANTALL | Antall timer | Numerisk |
| ARBLONN_LONN_KONTANT_IMP | Kontantytelser (imputert) | Numerisk |
| ARBLONN_LONN_KONTANT_INNRAPP | Kontantytelser (innrapportert) | Numerisk |
| ARBLONN_LONN_NATURAL | Naturalytelser | Numerisk |
| ARBLONN_LONN_SLUTTVEDERLAG | Sluttvederlag | Numerisk |
| ARBLONN_LONN_UREGTIL_ARBEIDET | Uregelmessige tillegg (arbeidet) | Numerisk |
| ARBLONN_LONN_UREGTIL_UARBEIDET | Uregelmessige tillegg (ikke arbeidet) | Numerisk |
| ARBLONN_LONN_ANNEN_BET | Annen betaling | Numerisk |
| ARBLONN_LONN_IMP_STATUS | Imputeringsstatus | Kategorisk |

### Ekvivalentlønnsvariabler (ARBLONN_LONN_EKV_*)

| Variabel | Beskrivelse | Type |
|----------|-------------|------|
| ARBLONN_LONN_EKV_FMLONN | Ekvivalent fullmånedslønn | Numerisk |
| ARBLONN_LONN_EKV_IALT | Ekvivalent totallønn | Numerisk |
| ARBLONN_LONN_EKV_BONUS | Ekvivalent bonus | Numerisk |
| ARBLONN_LONN_EKV_UREGTIL | Ekvivalent uregelmessige tillegg | Numerisk |
| ARBLONN_LONN_EKV_VEKT | Ekvivalentvekt | Numerisk |

## Foretaks-/virksomhetsvariabler

| Variabel | Beskrivelse | Type |
|----------|-------------|------|
| ARBLONN_FRTK_SEKTOR_2014 | Sektor (2014-klassifisering) | Kategorisk |

## Registerbasert sysselsetting (REGSYS_*) — årlige data

| Variabel | Beskrivelse |
|----------|-------------|
| REGSYS_ARB_ARBMARK_STATUS | Arbeidsmarkedsstatus |
| REGSYS_ARB_ARBKOMM | Arbeidsstedskommune |
| REGSYS_ARB_YRKE_STYRK08 | Yrkeskode |
| REGSYS_ARB_ARBEIDSTID | Arbeidstid |
| REGSYS_VIRK_NACE1_SN07 | Næring (NACE SN2007) |
| REGSYS_NARING_SN2007 | Næring (SN2007) |
| REGSYS_SEKTOR_2014 | Sektor |
| REGSYS_YRKSTAT | Yrkesaktivstatus |

## Viktige tilleggsvariabler fra andre registre

| Variabel | Beskrivelse |
|----------|-------------|
| BEFOLKNING_KJOENN | Kjønn (befolkningsregisteret) |
| BEFOLKNING_FOEDSELS_AAR_MND | Fødselsår og -måned (YYYYMM-format, bruk `int(var/100)` for år) |
| BEFOLKNING_KOMMNR_BOSTED | Bostedskommune |
| BEFOLKNING_STATUSKODE | Bosattstatus |
| NUDB_BU | Høyeste fullførte utdanning |
| NUDB_FAGFELT | Utdanningsfelt |

## Merknader

- A-ordningen inkluderer personer som ikke er i andre registre (f.eks. utenlandske pendlere). Vær forsiktig med kobling til BEFOLKNING-variabler — bruk `outer_join` ved behov.
- Variablene finnes i kurerte og innrapporterte versjoner. Kurerte (`_INNRAPP` mangler) er renset av SSB og anbefales som standard.
- Dato for import: bruk den 15. i måneden (f.eks. `2025-01-15`).
