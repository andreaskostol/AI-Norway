# AI-eksponering per utdanning: Kostøls tilnærming

*Arbeidsdokument, april 2026*

## Oversikt

Andreas Kostøl (BI) publiserer AI-eksponeringsscorer per utdanningsprogram på [andreaskostol.no/ai](https://andreaskostol.no/ai/). Vi har skrapet dette datasettet (7 246 NUS-utdanningskoder) for å forstå tilnærmingen og vurdere om vi kan gjøre noe tilsvarende.

**Ingen publisert metodikkbeskrivelse finnes.** Dokumentasjonen nedenfor er basert på analyse av dataene og rimelige antakelser. Vi kan ikke verifisere alle detaljer uten Kostøls kode.

---

## 1. Datastruktur

Hver av de 7 246 postene inneholder:

| Felt | Beskrivelse | Eksempel |
|------|-------------|---------|
| `nus_code` | 6-sifret NUS-utdanningskode | 654134 |
| `name` | Utdanningsnavn | Bachelor, spillteknologi og simulering, treårig |
| `level` | Hierarkisk nivå i NUS-standarden (1–5) | 5 |
| `education_level` | Tekstlig utdanningsnivå | Universitets-/høgskoleutdanning, lavere nivå |
| `field` | Fagfelt | Naturvitenskapelige fag, håndverksfag og tekniske fag |
| `n_styrk_linked` | Antall STYRK-yrker koblet til utdanningen | 4 |
| `n_styrk_with_exposure` | Antall av disse med AI-eksponeringsdata | 4 |
| `mean_exposure` | Gjennomsnittlig `exposure_index` over koblede yrker | 0.872 |

## 2. Sannsynlig konstruksjon

Basert på datastrukturen ser tilnærmingen ut til å være:

```
For hver NUS-utdanningskode:
  1. Finn alle STYRK-yrker som personer med denne utdanningen faktisk jobber i
     (fra SSB registerdata, A-ordningen × NUDB)
  2. Hent Kostøls AI-eksponeringsindeks for hvert av disse yrkene
  3. Beregn gjennomsnittet = mean_exposure
```

Koblingen NUS→STYRK er sannsynligvis hentet fra SSBs individbaserte registerdata, der hver sysselsatt person har både en NUS-utdanningskode (fra [NUDB](https://microdata.no/discovery/variable/no.ssb.fdb/17/NUDB_BU)) og en STYRK-yrkeskode (fra A-ordningen).

Vi vet ikke:
- Om gjennomsnittet er uvektet eller sysselsettingsvektet
- Om koblingen bruker alle sysselsatte eller bare heltidsansatte
- Hvilken tidsperiode koblingen er basert på
- Om det er en minimumsterskel for antall ansatte per NUS→STYRK-kombinasjon

SSB-rapporten [«Utdanning og yrke» (Graber, Kirkebøen & Vigtel, 2023)](https://www.ssb.no/arbeid-og-lonn/sysselsetting/artikler/utdanning-og-yrke) dokumenterer nøyaktig denne typen kobling mellom NUS og STYRK via registerdata.

## 3. NUS-hierarkiet

`level`-feltet angir hierarkisk nivå i [NUS2000-standarden](https://www.ssb.no/klass/klassifikasjoner/6):

| Level | NUS-sifre | Klassifiseringsnivå | Antall i data |
|-------|-----------|---------------------|---------------|
| 1 | 1 siffer | Utdanningsnivå (grunnskole, videregående, etc.) | 6 |
| 2 | 2 sifre | Nivå + fagfelt | 59 |
| 3 | 3 sifre | Faggruppe | 330 |
| 4 | 4 sifre | Utdanningsgruppe | 1 003 |
| 5 | 6 sifre | Enkeltutdanning | 5 848 |

81 % av postene er på nivå 5 (enkeltutdanninger, 6-sifret NUS-kode). Nivå 1–4 er aggregeringer.

Første siffer i NUS-koden angir utdanningsnivå:
- 3–4: Videregående
- 5: Påbygging / fagskole
- 6: Universitet/høgskole, lavere nivå (bachelor)
- 7: Universitet/høgskole, høyere nivå (master)
- 8: Forskerutdanning (ph.d.)

## 4. Gjennomsnittlig eksponering per utdanningsnivå

| Utdanningsnivå | Antall | Gj.snitt eksponering | Median |
|----------------|--------|---------------------|--------|
| Forskerutdanning | 710 | 0,548 | 0,546 |
| Universitet/høgskole, høyere nivå | 1 699 | 0,529 | 0,526 |
| Universitet/høgskole, lavere nivå | 1 693 | 0,479 | 0,477 |
| Påbygging til videregående | 1 406 | 0,373 | 0,380 |
| Videregående grunnutdanning | 834 | 0,383 | 0,324 |
| Videregående avsluttende | 904 | 0,277 | 0,223 |

Høyere utdanning = høyere AI-eksponering. Forskerutdanning har høyest gjennomsnitt (0,548), videregående avsluttende lavest (0,277).

## 5. Gjennomsnittlig eksponering per fagfelt

| Fagfelt | Antall | Gj.snitt | Median |
|---------|--------|----------|--------|
| Samfunnsfag og juridiske fag | 694 | 0,578 | 0,588 |
| Økonomiske og administrative fag | 640 | 0,543 | 0,570 |
| Lærerutdanninger og pedagogikk | 633 | 0,459 | 0,498 |
| Humanistiske og estetiske fag | 1 405 | 0,435 | 0,513 |
| Helse-, sosial- og idrettsfag | 1 063 | 0,428 | 0,399 |
| Naturvitenskapelige fag, håndverksfag og tekniske fag | 1 931 | 0,413 | 0,422 |
| Samferdsels- og sikkerhetsfag | 389 | 0,329 | 0,275 |
| Primærnæringsfag | 367 | 0,282 | 0,204 |

Samfunnsfag/jus og økonomi/admin har høyest eksponering. Primærnæringsfag lavest.

Merk: Naturvitenskapelige/tekniske fag har moderate gjennomsnitt (0,413) til tross for at enkelt-IT-utdanninger scorer svært høyt (>0,9). Dette skyldes at kategorien også inkluderer håndverksfag og andre tekniske fag med lav eksponering.

## 6. Datakvalitet

**Gap mellom koblede og dekkede yrker:** 439 av 7 246 utdanninger (6,1 %) har `n_styrk_with_exposure < n_styrk_linked`, dvs. noen koblede yrker mangler AI-eksponeringsdata. Mediangapet er 1 yrke. De største gapene (opptil 6 yrker) finnes i brede/generelle utdanningskategorier som kobler til mange yrker.

**Bredt koblede utdanninger:** Generelle utdanninger som «Allmenne fag» kobler til opptil 66 STYRK-yrker — eksponeringsscoren for disse er et bredt gjennomsnitt som ikke er spesielt informativt.

**Manglende vekting:** Vi vet ikke om `mean_exposure` er vektet etter antall ansatte i hvert yrke eller uvektet. Uvektet gjennomsnitt betyr at et nisjyrke med 50 ansatte teller like mye som et med 50 000.

## 7. Relevans for vår analyse

Kostøls utdanningsdimensjon er konstruert indirekte: utdanning → yrke → AI-eksponering. Den er avledet av yrkeseksponeringsmålet, ikke et uavhengig mål.

For vår analyse med microdata.no kan vi potensielt:
1. **Hente utdanningsdata** via NUDB_BU (høyeste fullførte utdanning, 6-sifret NUS)
2. **Koble direkte** til AI-eksponering via STYRK-kode i de samme arbeidsforholdsdataene
3. Dermed gjøre analyse på individuelt nivå i stedet for via aggregerte crosswalker

Fordelen med individuell kobling er at vi kan se heterogenitet *innenfor* utdanningsgrupper — f.eks. sykepleiere som jobber i IT vs. sykepleiere som jobber klinisk.

## 8. Tilsvarende tilnærminger internasjonalt

- **Federal Reserve (FEDS Notes, feb 2025):** Bruker National Survey of College Graduates for å koble utdanningsfelt til AI-eksponering via yrker i USA. Samme konseptuelle tilnærming som Kostøl.
- **US Treasury:** Mapper AI-eksponering via O\*NET → yrkeskoder → utdanningskoder (CIP-SOC crosswalk).
- **CIP-SOC crosswalk** (US Department of Education): Formell mapping fra utdanningsprogramkoder til SOC-yrkeskoder, analogt til SSBs NUS-STYRK registerkobling.

## 9. Datakilder

| Ressurs | Lenke |
|---------|-------|
| Kostøls AI-side | [andreaskostol.no/ai](https://andreaskostol.no/ai/) |
| SSB NUS-klassifisering | [ssb.no/klass/klassifikasjoner/6](https://www.ssb.no/klass/klassifikasjoner/6) |
| SSB rapport «Utdanning og yrke» | [Graber, Kirkebøen & Vigtel (2023)](https://www.ssb.no/arbeid-og-lonn/sysselsetting/artikler/utdanning-og-yrke) |
| NUS2000-standarden | [SSB Notater 2016/30](https://www.ssb.no/utdanning/norsk-standard-for-utdanningsgruppering) |
| NUDB_BU i microdata.no | [microdata.no/discovery](https://microdata.no/discovery/variable/no.ssb.fdb/17/NUDB_BU) |
| Lokalt skrapet data | [kostol_education_exposure.csv](../data/ai_exposure/kostol_education_exposure.csv) |
