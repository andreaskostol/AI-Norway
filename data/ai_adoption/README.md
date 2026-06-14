# AI-adopsjon i norsk næringsliv

Aggregerte tabeller fra SSBs årlige undersøkelse **"Bruk av IKT i næringslivet"**
(RA-0419), hentet via PxWebAPI fra Statistikkbanken. Utvalgsundersøkelse blant
foretak med ≥10 ansatte; ikke tilgjengelig på microdata.no per april 2026.

Disse måler **faktisk adopsjon** på nærings-/størrelsesnivå og komplementerer
den yrkesbaserte, teoretiske eksponeringen i [`../ai_exposure/`](../ai_exposure/).

## Filer

| Fil | SSB-tabell | Periode | Innhold |
|---|---|---|---|
| `13271_ai_purpose_naering_2021_2025.csv` | [13271](https://www.ssb.no/statbank/table/13271) | 2021, 2023–2025 | Andel foretak som bruker AI-teknologi, etter formål |
| `10965_ikt_spesialister_naering_2014_2023.csv` | [10965](https://www.ssb.no/statbank/table/10965) | 2014–2023 | Andel foretak som sysselsetter IKT-spesialister |

2022 mangler i 13271 — undersøkelsen om AI-formål ble ikke kjørt det året.

## Dimensjoner

Begge filene er i long-format med kolonnene `<dim>_code`, `<dim>_label` og `value`.

- **SyssGrpIKT** — størrelsesgruppe: `00` alle, `02` 10–19, `03` 20–49, `04` 50–99, `05` 100+
- **NACE2007** — 13 næringsgrupper (inkl. `Total+K`/`Total-K` med/uten finans)
- **ContentsCode** — for 13271: 10 AI-formål (markedsføring, produksjon, admin, styring, logistikk, HR, FoU, IKT-sikkerhet, regnskap, annet). For 10965: kun `SysselsetSpes`.
- **Tid** — år
- **value** — prosent foretak

## Nedlasting

Dataene ble hentet via SSBs åpne PxWebAPI
(`https://data.ssb.no/api/v0/no/table/{id}`) ved POST med `query: filter=all`
og `response.format=json-stat2`, deretter flatet ut til long-format CSV.
Rå metadata ligger i `_meta_13271.json` og `_meta_10965.json`.

## Bruksforslag

- **Validering av eksponeringsindekser:** korreler Eloundou/DAIOE-eksponering
  aggregert til NACE-nivå mot faktisk AI-adopsjon i 13271.
- **Næringsnivå treatment intensity:** bruk AI-bruksandel per NACE som
  kontinuerlig "treatment" i difference-in-differences på sysselsetting.
- **Før/etter ChatGPT:** 2021 vs. 2023–2025 gir et grovt skille rundt
  generativ AI-bølgen (nov. 2022).

## Forbehold

- Utvalgsundersøkelse, ikke fullregister. Kun foretak ≥10 ansatte.
- Selvrapportert; definisjonen av "AI" har endret seg mellom år.
- Kun aggregerte tall — foretaksnivå-kobling krever egen SSB-søknad.
