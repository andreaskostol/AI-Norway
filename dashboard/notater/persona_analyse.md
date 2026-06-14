# Persona-analyse av kiindeksen.no

Juni 2026. Grunnlag: lest `index.html`, `om.html`, `app.js`, `style.css` (faktisk
kildekode) og `presse_qa.md`. Formål: konstruere lesertyper, vurdere hvor godt
siden svarer dem, foreslå justeringer, og veie avveiningene.

Siden er bevisst en *edruelig monitor*: ledevisualet er den samlede KI-indeksen
(svakt positiv), metodevalgene er synlige, språket er hedget. Det er en styrke for
troverdighet og en kostnad for lesere som vil ha et raskt, personlig svar.

Et premiss styrer hele anbefalingen: for en troverdighetsdrevet monitor er
**edruelighet og lesbarhet selve rekkeviddestrategien**, ikke en kostnad ved den.
I norsk forskningsformidling skapes rekkevidde av forfatternes pitch, metodepapiret
og SSB-/registerdata-opphavet — ikke av at et delekort går viralt. Den dominerende
halerisikoen er det motsatte av lav rekkevidde: ett dekontekstualisert feilsitat
som blir prosjektets varige omdømme. Derav rekkefølgen under.

---

## Del 1 — Personas og treffsikkerhet

Delt i tre: leserne (de som lander på siden), de institusjonelle portvaktene og
forsterkerne (som avgjør om noe får rekkevidde og troverdighet), og fagpublikum.
Skillet er ikke kosmetisk: i Norge går rekkevidde gjennom portvaktene, ikke gjennom
viralitet.

### Leserne

**P1 · Maria, nyhetsjournalist (35), desk med deadline.**
Kommer for: én setning, ett tall, en figur å skjermdumpe. Lurer på: «Hva er
nyheten? Er det lov å si at KI tar jobbene fra unge?»
Treffer i dag: ✓ «For den utålmodige leseren» + headline-kort gir raskt
hovedbildet; ✓ sitering og kildehenvisning er forbilledlig. ✓ Det finnes en
statisk ungdomsfigur — «Unge (21–30 år)»-raden i oppsummeringsinfografikken
([app.js:391]) — men den ligger nederst, etter figur 1–11, og ledevisualet er den
beroligende samlede indeksen. ✗ Ingen presseside/kontakt, ingen uavhengighets-/
finansieringslinje hun trenger for å publisere. Hennes faktiske troverdighetsport
er ikke et delekort, men «er dette fagfellevurdert / hva sier SSB?».
Justering: løft den eksisterende ungdomsraden høyt opp *på siden*, paret med
forbeholdet; gjør et metodenotat og en uavhengighetslinje synlig. Hun finner ikke
siden ved å google den — den lander fordi forfatterne pitcher den.

**P2 · Per, allment nysgjerrig (52), leste en KI-sak i VG.**
Kommer for: «Bør jeg være bekymret?» på to minutter, uten sjargong.
Treffer i dag: ✓ den øverste skjermen (ingress + «utålmodige leseren» +
headline-kort) er sjargongfri; «beta»/«X-11» ligger i kollapsede `<details>`.
Første sjargong («kvintil», «STYRK-08») kommer i seksjon 1, med info-knapp, og det
er sju plain-Norwegian `?`-forklaringer. ✗ Ingen «hva betyr dette for meg / mitt
yrke»-inngang.
Justering: behold den sjargongfrie toppen; lenk til en kort FAQ.

**P3 · Sofie, ung jobbsøker (24), fersk regnskaps-/IT-utdanning.**
Kommer for: «Er yrket mitt utsatt? Kastet jeg bort utdanningen?» — kommer urolig.
Treffer i dag: ✗ Dårligst betjent, og samtidig den siden handler om. Bare fire
yrkescase er hardkodet; finner hun ikke sitt, får hun kvintil-aggregater. ✗ Tonen
er nøytral-analytisk; de beroligende, konkrete svarene fra `presse_qa` (Q13 «bør
unge droppe IT? Nei…», Q20 «til en 23-åring…») finnes ikke. ✗ Ingen yrkesoppslag.
Justering: frosset «største yrker per gruppe»-tabell *med arkitektoniske sperrer
mot individuell feillesing* (Del 3); en kort «for deg som er ung»-tekst fra
Q13/Q14/Q20.

**P12 · Skeptiker/faktasjekker.**
Kommer for: å etterprøve og finne svakhetene.
Treffer i dag: ✓ godt betjent på metode, vintage, frosne sesongfaktorer,
korrelasjon 1,000-kontroll, bruksbasert robusthet. ✗ uavhengighet/finansiering
(presse_qa Q24) mangler på siden; konfunder-forbeholdet er spredt; headline-kortet
sier «et tidlig varsel om at KI kan fortrenge jobber» ([index.html:120]), som
tilskriver KI en retning identifikasjonen ikke bærer.
Justering: omformuler den ene setningen (Del 3, punkt 2); samle forbeholdene.

**P13 · Delt-lenke-/søk-leseren.** Tapper en lenke i feed eller et søketreff.
Reell, men *nedstrøms*: i norsk kontekst skaper pressedekningen delingen, ikke
omvendt. Behovet (et delekort som tåler å bli skjermdumpet uten siden rundt) er
ekte — men det løses ved at delekortet er *nøytralt*, ikke ved at det bærer et
ungdomstall (Del 3, punkt 6).

**P14 · Tilbakevendende månedsleser.** Kom forrige release, vil se endring — det
*eneste* en månedlig monitor unikt tilbyr.
Treffer i dag: ✗ ingen «hva er nytt denne måneden», ingen datostatus øverst.
Justering: datert statuslinje + en kort «endringer denne releasen».

### Institusjonelle portvakter og forsterkere

**SSB.** Den mest påfallende utelatelsen. Siden bygger på A-ordningen via
microdata.no — SSBs egen infrastruktur. SSB er både mulig validator og mulig
offentlig kritiker, og en journalists *første* verifiseringsoppringning. «Vi ser
aldri enkeltpersoner; SSBs egne sperrer mot små celler» (presse_qa Q23) bør stå
*på siden*: i norsk registerdatakontekst foregriper det personvernspørsmålet og
gjør SSB-avhengigheten til et troverdighetsanker.

**Faktisk.no.** «KI tar jobbene fra unge» er akkurat det Faktisk.no sjekker hvis en
politiker gjentar tallet. De går rett på metodepapiret og konfunder-forbeholdet —
som hever innsatsen på riktig headline-ordlyd (punkt 2).

**Partene som forsterkere (Tekna, Akademikerne, LO, NHO, Abelia).** Tekna og
Akademikerne har medlemmer midt i de eksponerte STYRK-kodene (utviklere,
ingeniører, økonomer) og er den mest sannsynlige delingskanalen — en realistisk
erstatning for «organisk viralitet».

**Forvaltning (NAV / departement / HK-dir) — tre ulike aktorer.** En
NAV-analytiker (Kunnskapsavdelingen) kryssjekker mot egne ledighetstall; en
departementsrådgiver (AID/KD) vil ha et siterbart tall til en melding; HK-dir
eier kompetansepolitikk-vinkelen (lærling/praksis, Q27). Policy-pekepinner bør
holdes *etatsnøytrale* — «NAV bør …» nær figurene ser ut som at forfatterne gjør
NAVs jobb.

### Fag og internasjonalt

**P10 · Arbeidsmarkedsforsker.** ✓ blant best betjente (metode, crosswalks, X-11,
DEL-sammenligning, CSV + data dictionary). ✗ ingen kode/replikasjonspakke ennå.

**P11 · Internasjonal (OECD/EC-benchmarking, Stanford DEL/ADP).** Når siden via
*papiret*, ikke dashbordet. Begrunner én engelsk statisk metode-/funn-side, ikke
et tospråklig dashbord.

### Kuttet

**Bank/finans-analytiker.** Bruker SSB/Macrobond, ikke en enkelt-indikator.
Neglisjerbar trafikk; driver ingen designvalg de andre ikke driver.

---

## Del 2 — Kritisk gjennomgang

1. **`presse_qa` er et internt forberedelsesdokument, ikke publiseringsklart.**
   Finansieringssvaret er en `[FYLL INN]`-placeholder (Q24), regnskaps-omkodingen
   er en «ikke til sitat»-note (presse_qa:69–73), flere formuleringer er spissere
   enn en nettside bør være. En offentlig FAQ må *kurateres og gates*, ikke kopieres.

2. **Yrkesoppslag kan undergrave et kjernebudskap.** En etikett er ikke en
   arkitektonisk sperre. Et oppslag som sier «ditt yrke: Q5, −6 %» inviterer den
   individuelle lesingen siden advarer mot — og siden sier i dag ikke engang
   eksplisitt «celler, ikke personer».

3. **Edrueligheten *er* produktet.** Ethvert grep som gjør ungdomshistorien
   «spissere» trekker mot årsaksoverdrivelse. Forbeholdet kan ikke flyttes med på
   en flate som reiser uten siden rundt seg (et delekort) — derfor må delekortet
   være nøytralt, og forbeholdet stå *på selve siden*.

4. **Tallene er ikke verifisert for delingsbruk.** Headline-skalaren er
   likevektet per yrke og kan svinge på sammensetning; «6 %»-tallet ligger i Q5
   21–30, nettopp cellen som er forurenset av regnskapsomkodingen (presse_qa:69–73);
   «doblet fra 2 til 4 %» er en endring av en endring, dobbelt volatil og kanskje
   båret av små delceller. Ingen av disse er klarert som *hero-tall* ennå.

5. **Vedlikehold for to personer er den knappe ressursen.** Hardkodet prosa (FAQ,
   råd, policy, yrkestabell) kan drive ut av takt med de auto-genererte tallene.
   Alt slikt må være frosset/datostemplet by design.

---

## Del 3 — Avveininger og samlet anbefaling

### Kjernespenninger
- **A. Spisshet vs. troverdighet.** Løses ved at forbeholdet står på siden, at den
  ene kausale setningen rettes, og at delekortet ikke bærer noe tall.
- **B. Personlig nytte vs. «celler, ikke personer».** Løses arkitektonisk (punkt 7),
  ikke med en etikett.
- **C. Norsk identitet vs. internasjonal rekkevidde.** Løses med én engelsk statisk
  side — og en *bevisst* beslutning om Bokmål/Nynorsk (punkt 8).
- **D. Rikere tjeneste vs. vedlikehold for to.** Alt nytt innhold frosset/datostemplet.

### Anbefaling

1. **Metodenotat som lanseringsport.** I norsk akademisk pressekultur er det
   citerbare metodepapiret det bærende troverdighetsinstrumentet; det er svaret
   `presse_qa` gir hver skeptiker (Q21, Q25). Å lansere den pressedrevne monitoren
   uten *minst* et offentlig, citerbart metodenotat (eller `om.html` hevet til
   citerbar status med permanent arkiv/DOI) er den største troverdighetsrisikoen —
   større enn noe delekort. Bør foreligge ved lansering.

2. **Årsaksdisiplin på selve siden** (den mest skjermdumpbare flaten må *allerede*
   være den hedgede):
   - Omformuler [index.html:120] «et tidlig varsel om at KI kan fortrenge jobber»
     → f.eks. «et tidlig varsel om endrede ansettelsesmønstre i de mest
     KI-eksponerte yrkene».
   - Legg én konfunder-setning i *samme* kort (rente/konjunktur/normalisering).
   - Legg «celler, ikke personer» og SSB-personvernlinjen (presse_qa Q23) synlig på
     siden.
   - Vurder en åpen note i `om.html` om regnskapsomkodingen (mai 2025).

3. **Tilgjengelighet som rettslig krav, ikke høflighet.** En publikumsrettet side
   fra Frischsenteret/BI er en «IKT-løsning rettet mot allmennheten» under
   likestillings- og diskrimineringsloven §18 og uu-forskriften, håndhevet av
   Uutilsynet/Digdir; ingen forskningsunntak. *Presiser standarden:* privat sektor
   er bundet av **WCAG 2.0 AA** (35 av 61 kriterier); 2.1 AA er beste praksis å sikte
   mot (og gjeldende krav hvis offentlig tilknytning trekker siden inn under
   webdirektivet). Konkret her, i prioritert rekkefølge:
   - **echarts-figurene er den reelle eksponeringen** (canvas er ugjennomsiktig for
     skjermlesere). `aria`/`decal` alene gir ikke konformitet; den robuste veien er
     *tekst-/dataalternativ* per figur (SC 1.1.1) — siden er nær der allerede via
     CSV-nedlasting + prosa-introer. Knytt dem sammen.
   - **Farge som eneste bærer av informasjon** (SC 1.4.1): `#8C1515` er kvintil 1 i
     linjediagrammet ([app.js:26]) men kvintil 5 i headline-stolpene ([app.js:683])
     og dessuten «21–30» i AGE_COLORS — samme rød, tre grupper. Gjør konsistent og
     fargeblind-trygt; legg på `decal`-mønstre.
   - **Død fargeklasse:** [app.js:677] setter alltid `"headline-yoy"`, så grønn/rød i
     CSS aldri trer i kraft.
   - **Tastatur-/skjermlesertilgang** til info-popover (SC 2.1.1, 4.1.2); `aria-live`
     på dynamiske felter (god praksis, ikke strengt 2.0-krav).
   - **Mobilnav kollapser ikke** (14-punkts TOC forsvinner < 979 px; header-nav uten
     hamburger blir en høy ombrukket liste).
   Stående krav uten lanseringsfrist, men «skal-ikke-publiseres-uten».

4. **Det mest siterte tallet — gjør det robust og selvforklarende før noe deles.**
   - For *hero*-tallet er egen-cellevekst (12-måneders endring i sysselsetting i
     cellen Q5 × 21–30, sesongjustert, som andel av cellens egen basemåned)
     renere og mindre manipulerbart enn per innbygger: per innbygger blander en smal
     teller med en bred nevner (studenter, innvandring, økende studietilbøyelighet),
     og kvartals-til-måned-interpolasjonen lager kunstig glatt nevner nettopp ved
     vendepunkter (H2 2025). `presse_qa` Q2 oppgir at «6 %» allerede er justert for
     *sesong og befolkningsutvikling* — så hold per innbygger som det *oppgitte
     forholdstallet* for konsistens med pressen, men vis egen-cellevekst ved siden
     av som robusthetssjekk, og **selvmerk** alltid justering + referanseperiode +
     glatting i selve objektet.
   - **Robusthetsporter før et tall blir hero:** (i) beregn «6 %» med og uten
     regnskapskodene 3313/4311 og vis at forskjellen er under en forhåndsdefinert
     terskel; (ii) en oppgitt minste cellestørrelse; (iii) tegn-robusthet for
     headline-skalaren under sysselsettingsvektet (ikke bare likevektet)
     kvintilkonstruksjon.

5. **Løft den eksisterende ungdomsraden** ([app.js:391]) høyt opp *på siden*, paret
   med forbeholdet fra punkt 2. Billigere enn å bygge en ny hero — men den blir
   *ikke* et frittstående delekort-tall (punkt 6).

6. **Delekort/OG-metadata — nøytralt, uten tall.** En lenke uten OG-tagger ser
   uferdig ut, så de bør finnes. Men `og:image` reiser strippet for siden:
   gjør den til det *nøytrale* objektet (prosjektnavn, «månedlig monitor for KI og
   arbeidsmarkedet», den samlede indeksen, institusjonene). Aldri ungdomstallet
   (~6 % / ~5 000) på en flate som reiser uten forbeholdet — det er nettopp
   «KI tar jobbene fra unge»-overskriften `presse_qa` er bygget for å hindre.

7. **Frosset «største yrker per eksponeringsgruppe»-tabell** (finnes i
   presse_qa-vedlegget), datostemplet, med arkitektoniske sperrer: vis kontrafaktisk
   kontekst (f.eks. at Q5 i 31–40 vokser), ikke navngitte enkeltyrker med fall som
   «din prognose». Betjener P3/P6/P7+P8 — det største innholds-gapet.

8. **Engelsk statisk metode-/funn-side** for det papir-nådde internasjonale
   publikummet — *og* en bevisst beslutning om Nynorsk. Mållova binder neppe en
   privat aktør direkte, men en nasjonal «indeks» kun på Bokmål er en kjent
   svakhet, og å sende en engelsk side mens Nynorsk ignoreres har dårlig optikk.
   Avgjør bevisst, ikke ved unnlatelse.

9. **Datert statuslinje** + «endringer denne releasen» (P14). **Kuratert FAQ —
   gated** på utfylt finansieringslinje + fjernet intern note. **Utsett:** fullt
   interaktivt yrkessøk, tospråklig dashbord, persona-router, kode-/replikasjonspakke
   (knytt til papiret), API.

**Gjør ikke:** ikke lag et tallbærende ungdoms-delekort; ikke gjør headline til en
kausal påstand; ikke publiser FAQ med placeholder eller intern note; ikke stamp et
hero-tall som «kanonisk» før robusthetsportene er passert; behold den nøkterne
tonen.

### Hvis bare én ting
Få det citerbare metodenotatet på plass og sett forbeholdet på den mest
skjermdumpbare flaten (rett headline-setningen, legg konfunder + «celler, ikke
personer» på siden). For en troverdighetsmonitor er det å være vanskelig å
feilsitere selve rekkeviddemotoren — og det eneste grepet som ikke bevæpner
overskriften prosjektet finnes for å avvæpne.
