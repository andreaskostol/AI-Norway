# Sesongjustering av sysselsettingsseriene

Notat om metoden bak sesongjusteringen i indeksfigurene
(`analysis/06_figures/plot_canaries_style_index.py`) og forholdet til
sesongkontrollen i regresjonene. Alle tall i logpoeng (lp) der ikke annet
er sagt. Diagnostikken er kjørt på per capita-seriene per kvintil x
aldersgruppe, privat sektor, juni 2026.

## Metode

Justeringen følger kjernen i X-11, per serie, i logger:

1. Trend: sentrert 2x12 glidende snitt (13 måneder, halv vekt på
   ytterpunktene, slik at hver kalendermåned inngår med lik vekt).
2. Sesongfaktorer: gjennomsnittlig log-avvik fra trenden per
   kalendermåned i estimeringsvinduet 2021m01-2024m12, normalisert til
   snitt null.
3. Faktorene trekkes fra hele serien, også observasjoner etter
   estimeringsvinduet, og holdes faste når nye måneder kommer til.

Faste faktorer er et bevisst valg: løpende re-estimering (som i
X-13-praksis) reviderer historien hver måned, og den sekvensielle
inferensen i overvåkingen forutsetter at fortiden ligger fast. Prisen er
at endringer i sesongmønsteret ikke fanges; avvik fra det faste mønsteret
blir stående i den justerte serien og kan være signal.

## Hvorfor ikke regresjonsbasert detrending

En naturlig enklere variant er OLS av log-serien på lineær trend pluss
månedsdummyer. Den er skjev når trenden er ikke-lineær: med balansert
kalender kanselleres feil som er konstante innen år, men innen-års-
gradienten i restleddet lekker inn i faktorene. COVID-gjeninnhentingen i
2021 stiger 8-13 lp gjennom året, og en firedel av den rampen leses som
sesong. Målt mot MA-faktorene: median 0,35 lp, maks 1,33 lp (serien
21-30 Q2, som har brattest gjeninnhenting). Kubisk trend hjelper ikke
(maks 1,97 lp; polynomendene vrir seg inn i faktorene).

Årsspesifikke trender er ikke et alternativ: innen ett kalenderår er
trend og kalendermåned samme variabel, så med frie årsvise helninger er
sesong og trend ikke separat identifisert. Identifikasjon krever at
trenden bindes glatt over årsgrensene, som det glidende snittet gjør.

## Estimeringsvindu

Vinduet 2021m01-2024m12 gir avvik for juli 2021-juni 2024 (MA-trenden
mister 6 måneder i hver ende), tre observasjoner per kalendermåned.

To følsomhetssjekker:

- Stanford-vinduet 2021m05-2024m04 (rullerende 5 år, 3 sykluser) gir
  15-20 prosent høyere residualruhet i de justerte seriene. Det beholder
  gjenåpningsmånedene mai-desember 2021 og kaster de rene månedene
  mai-desember 2024. Visningsvindu og estimeringsvindu bør derfor velges
  uavhengig av hverandre.
- Årgangs-asymmetri fra kanteffekten: januar-juni-faktorene bygger på
  2022-2024, juli-desember-faktorene på 2021-2023, altså med
  gjenåpningshalvåret 2021 som en tredjedel av grunnlaget. Droppes
  2021-avvikene helt, endres faktorene med median 0,10 lp, maks 1,12 lp,
  konsentrert i oktober-november (snitt 0,24-0,27 lp). Uten betydning
  for noen av mønstrene i figurene.

## Forholdet til regresjonene

Event-studiene og trendbruddmodellen kontrollerer for differensiell
sesong på yrkesnivå (kvintil x kalendermåned), enten som offset estimert
i et eget førstesteg (preseas) eller simultant der trenden er
parametrisk. Måneds-faste effekter absorberer der all felles
ikke-linearitet, så bare differensiell krumning kan lekke inn i
sesongleddene; simultan og to-stegs estimering ga identiske helninger,
og faktorvinduet (2021-2024 mot kun pre-ChatGPT) flytter ikke
resultatene. Den aggregerte justeringen i dette notatet brukes bare i
indeksfigurene.

## Kjente begrensninger

- Fast mønster: bevegelig sesong og kalendereffekter (påskens plassering
  mot referanseuken med den 16.) fanges ikke. For antall sysselsatte er
  dette trolig lite; for timer og lønn ville det veid tyngre.
- 2021 inngår i faktorgrunnlaget. Følsomheten er kvantifisert over og
  liten, men ikke null.
- X-13ARIMA-SEATS er ikke kjørt. En engangs benchmark mot X-13 vil vise
  om bevegelig sesong er kvantitativt viktig; X-13 egner seg uansett
  ikke som produksjonsmetode her på grunn av revisjonene.
