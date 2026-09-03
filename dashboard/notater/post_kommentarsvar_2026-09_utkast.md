# Utkast: LinkedIn-post som svarer på kommentarene i ett (september 2026)

Publiseres etter at målvelgeren (Mouchel) er live (den gikk live
2026-09-03). Tone: takknemlig, presis, ingen overdrivelser. Hovedtallet
omtales med forbehold.

Redigert av Andreas 2026-09-03: ny åpningssetning, offentlig
sektor-tallet presisert (1,1 millioner er alle aldre og alle yrker;
figurene dekker 943 000 i alderen 21–60), Mouchel-tallet lagt inn,
lenker fylt ut. Tallet 0,77–0,79 (rangkorrelasjon mot bruksdata fra
Anthropic, Microsoft og Google) er ikke verifisert av Andreas; Øystein
bekrefter kilden før publisering.

Kildesjekk 2026-09-03 (Øystein med Claude): tallene fantes bare som
konsoll-utskrift i de tre scatter-scriptene, aldri lagret. De ligger nå
i `analysis/output/coefficients/coef_exposure_vs_usage_correlations.csv`
(commit `1d9b967`). Reproduserte verdier: Anthropic 2026 0,78 (n=388
yrker), Microsoft 0,77 (n=393 yrker), Google ATLAS 0,79 — men over 22
SOC-hovedgrupper, ikke yrker, og digitalisert fra en figur i Googles
rapport. Handa overall, som også er brukstall, ligger på 0,64.
Avsnittet er derfor omskrevet: Anthropic og Microsoft oppgis med egne
tall på yrkesnivå, ATLAS nevnes som grovere, og «0,77-0,79» som ett
intervall for tre kilder er tatt ut.

---

Juni-tallene er ute på kiindeksen.no. Kommentarfeltet fra forrige
runde har blitt til en ny og (foreløpig) uvanlig fagfellevurdering, og
her er svarene, i form av ting dere kan klikke på.

Dere ba om en egen modul for offentlig sektor. Den er live: fire nye
figurer med sysselsetting, nyansettelser og lønn for offentlig sektor,
943 000 ansatte mellom 21 og 60 år, med de samme kuttene som privat
sektor. https://kiindeksen.no/#offentlig

Dere spurte om resultatene tåler andre mål for KI-eksponering. Nå kan
dere sjekke selv: en ny velger lar dere bytte mellom Eloundou-målet vi
har brukt hele tiden og det evidensbaserte målet fra Mouchel et al.
(2026). De to rangerer yrker nesten likt (rangkorrelasjon 0,94), og
KI-indeksen er +2,3 med Mouchel-målet mot +1,7 med Eloundou.
Konklusjonen flytter seg ikke med målet. Vi har også sammenliknet
eksponeringsmålet med data om faktisk KI-bruk: Anthropics og
Microsofts brukstall rangerer yrker omtrent som Eloundou
(rangkorrelasjon 0,78 og 0,77 på tvers av nesten 400 yrker). Googles
ATLAS peker samme vei, men er publisert bare for 22 yrkesgrupper, så
den sammenlikningen er grovere. https://kiindeksen.no/?maal=mouchel

Dere sa at figurene var vanskelige å kjenne seg igjen i. Nå kan dere
velge deres eget yrke: søk blant 358 yrker, sammenlign opptil seks om
gangen, og del lenken. https://kiindeksen.no/#yrker-velg

Hva viser tallene? KI-indeksen er +1,7 prosentpoeng: sysselsettingen i
de mest KI-eksponerte yrkene har vokst 0,5 prosent siden oktober 2022,
mens de minst eksponerte har falt 1,2 prosent. Endringen siden sist
skyldes altså de minst eksponerte yrkene, ikke et fall blant de mest
eksponerte, og forskjellen er fortsatt ikke statistisk utskillbar fra
null. Norge ser fortsatt ikke ut som USA.

Det vi ikke har fulgt opp ennå: mål på oppnådde effekter i offentlig
sektor, som kostnad, saksbehandlingstid og frigjorte årsverk. Det
krever data som ikke finnes i A-ordningen i dag, og som Riksrevisjonen
og DFØ har etterlyst. Fjernarbeid og placebo-perioder står på lista.

Forskningsartikkelen bak dashbordet er nå ute som RFBerlin Discussion
Paper 179/26:
https://www.rfberlin.com/wp-content/uploads/2026/07/26179.pdf

Fortsett å utfordre oss. Det er slik indeksen blir bedre.

Øystein Hernæs og Andreas R. Kostøl

---

Kommentar-til-svar-kartet (til vår egen sjekk før publisering):

| Kommentar | Svar i posten |
|---|---|
| Slinning: offentlig modul, faktisk bruk, effekter | Modul live; bruksdata validert; effekter = ærlig ikke-ennå |
| «Ulike mål for KI-eksponering?» | Målvelger med Mouchel + kryssvalidering |
| Samme kommentar: fjernarbeid, 2016 | «Står på lista» (bevisst utsatt) |
| Brekne Johnsen: «skjønte ingenting av figurene» | Yrkesvelgeren, uten å nevne ham |
| Godager: ledighet blant ph.d.-er | Dekkes ikke i posten; svart i tråden tidligere |
