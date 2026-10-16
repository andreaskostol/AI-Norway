# MCP-kobling til KI-indeksen

En MCP-server (Model Context Protocol) som gir avanserte brukere tilgang til
dataene bak kiindeksen.no, Yrker og Utdanning som verktøy, fra Claude, Codex, Kimi,
GLM, andre MCP-klienter eller et eget script. Alt er lesetilgang til de aggregerte tallene nettstedet
allerede publiserer. Ingen personopplysninger.

- Endepunkt: `https://kiindeksen-mcp.fly.dev/mcp` (Streamable HTTP, JSON-RPC 2.0)
- Andre transporter (2026-10-15): `GET /sse` + `POST /messages` (eldre HTTP+SSE),
  `python3 server.py --stdio` (stdio), REST `GET|POST /tools/<navn>` og
  `GET /openapi.json` for funksjonskall hos andre modelleverandører
- Brukerside: https://kiindeksen.no/mcp.html (under Labben), engelsk `en/mcp.html`;
  nettstedet serverer en kopi av `client_example.py` på `/mcp/client_example.py`
- Kilde: `dashboard/mcp/server.py`, bare Pythons standardbibliotek
- Data: hentes fra `https://kiindeksen.no/data/` ved oppstart og på nytt hver
  sjette time, så koblingen følger den månedlige releasen uten ny utrulling
- Drift: Fly.io-appen `kiindeksen-mcp` (region arn), `Dockerfile` og `fly.toml`
  i denne mappa. Utrulling: `cd dashboard/mcp && flyctl deploy`

## Koble til

Claude Code:

```bash
claude mcp add --transport http kiindeksen https://kiindeksen-mcp.fly.dev/mcp
```

claude.ai: Settings, Connectors, Add custom connector, lim inn adressen over.
Ingen innlogging; dataene er offentlige.

Andre klienter, samme adresse:

```bash
codex mcp add kiindeksen --url https://kiindeksen-mcp.fly.dev/mcp          # Codex CLI (OpenAI)
kimi mcp add --transport http kiindeksen https://kiindeksen-mcp.fly.dev/mcp # Kimi Code CLI
```

OpenCode: `"mcp": {"kiindeksen": {"type": "remote", "url": "https://kiindeksen-mcp.fly.dev/mcp", "enabled": true}}`
i `opencode.json`. Gemini CLI: `"mcpServers": {"kiindeksen": {"httpUrl": "https://kiindeksen-mcp.fly.dev/mcp"}}`
i `~/.gemini/settings.json`. GLM fra Z.ai brukes gjennom Claude Code, OpenCode, Cline
eller Kilo Code; legg koblingen til der. Klienter som bare kjenner den eldre
SSE-transporten, bruker `https://kiindeksen-mcp.fly.dev/sse`. Klienter som bare starter
lokale servere, registrerer kommandoen `python3 server.py --stdio`.

Fra kode uten MCP-klient: OpenAI Responses API tar verktøyet
`{"type": "mcp", "server_label": "kiindeksen", "server_url": "https://kiindeksen-mcp.fly.dev/mcp", "require_approval": "never"}`;
Anthropic Messages API (beta `mcp-client-2025-11-20`) tar
`{"type": "url", "url": "https://kiindeksen-mcp.fly.dev/mcp", "name": "kiindeksen"}` i
`mcp_servers` og `{"type": "mcp_toolset", "mcp_server_name": "kiindeksen"}` i `tools`.
Alle modeller med funksjonskall (Kimi, GLM, Gemini, Mistral ...) kan bruke REST-kallene
`GET /tools/<navn>?arg=verdi` (lister kommaseparert) eller `POST /tools/<navn>` med
JSON-kropp; `GET /openapi.json` beskriver dem. Eksempel:
`curl "https://kiindeksen-mcp.fly.dev/tools/compare_occupations?codes=4110,3312&index_base=2025-02"`.

Eget script: `client_example.py` viser hele samtalen med serveren uten andre
avhengigheter enn Python. Prøv:

```bash
python3 dashboard/mcp/client_example.py
```

## Verktøyene

| Verktøy | Hva det gir |
|---|---|
| `get_release` | Release, periode, normaliseringsmåned, antall yrker og utdanninger, hovedtallet med usikkerhet |
| `list_packages` | Alle tidsseriepakkene: sysselsetting, nyansettelser, lønn; privat og offentlig sektor; Eloundou- og Mouchel-kvintiler; yrkescase; bruksmønster |
| `get_series` | Tidsserier fra en pakke, med valg av spesifikasjon (raw, sa, percap, percap_sa), facet, serie, periode, basismåned og glatting |
| `get_growth` | Vekst fra en referansemåned til siste måned for alle serier i en pakke, pluss gapet kvintil 5 minus kvintil 1 |
| `get_headline` | Nettstedets hovedtall: KI-indeksen med bootstrap-standardfeil og 95 %-intervall, per mål, referanse og aldersgruppe |
| `get_composition` | Andel ansatte per aldersgruppe og kvintil |
| `search_occupations` | Søk i STYRK-08-yrker, norsk eller engelsk |
| `get_occupation` | Ett yrke: eksponering, kvintiler, Claude-bruk per utgave, nærmeste yrker, oppgavene med bruk og automatisering |
| `get_occupation_series` | Sysselsetting eller lønn for ett yrke, månedlig fra 2021 |
| `compare_occupations` | Flere yrker side om side med felles base |
| `list_education_levels`, `search_education`, `get_education_group` | Utdanning: faggrupper, oppgavene i jobbene, vanligste jobber |
| `list_downloads`, `get_data_dictionary` | CSV-ene for releasen og dokumentasjonen deres |
| `get_studio_papers` | Arbeidslista i Studio |
| `send_feedback` | Tilbakemelding til Andreas og Øystein (vis brukeren teksten først) |

To ressurser (`kiindeksen://om`, `kiindeksen://konvensjoner`) og to prompter
(`analyser_yrkespar`, `maanedsrapport`) følger med.

## Konvensjoner

- Tidsseriene er indekser med 100 i november 2022, måneden ChatGPT kom. Bruk
  `index_base` for å flytte basen, for eksempel `2025-02` for Claude Code.
- `sa` er sesongjustert, `percap` er per innbygger i aldersgruppen.
- KI-indeksen er veksten i den mest eksponerte femdelen minus veksten i den
  minst eksponerte, i prosentpoeng. `get_headline` gir nettstedets tall med
  usikkerhet; `get_growth` lar deg regne på egne referanser og glattinger.
- Yrker er STYRK-08 på fire siffer. Bare yrker med minst 30 lønnstakere hver
  måned har tidsserie. Automatisering er Anthropics regel: direktiv pluss
  tilbakemeldingssløyfe.
- Utdanninger er NUS-faggrupper på tre siffer, nivå pluss fag.
- Oppgi release, spesifikasjon og basismåned når du rapporterer tall.

## Eksempel: samme eksponering, ulik automatisering

Spørsmålet: to yrker har nesten samme KI-eksponering. Brukes KI likt i dem,
og går det likt med sysselsettingen? Dette er det `client_example.py` gjør,
og det er det Claude gjør hvis du ber om prompten `analyser_yrkespar` med
kodene 4110 og 3312.

1. `get_release` og `get_headline`. Release 2026-10 dekker januar 2021 til juli
   2026. KI-indeksen for 21–60 år med ChatGPT som referanse er +1,5
   prosentpoeng, standardfeil 2,7. For 21–30 år siden Claude Code er den −2,9,
   standardfeil 2,0.

2. `get_growth` på `by_exposure` med referanse 2025-01 og tre måneders
   glatting. Fra januar 2025 til juli 2026, sesongjustert: minst eksponerte
   femdel −0,3 prosent, mest eksponerte −0,3 prosent. Gapet er −0,1
   prosentpoeng. Samme kall på `age_by_exposure` for 21–30 år: −1,8 i minst
   eksponerte, −4,6 i mest eksponerte.

3. `compare_occupations` med kodene 4110 og 3312, sysselsetting, sesongjustert,
   basismåned 2025-02:

   | Yrke | Eloundou | Mouchel | Automatisering (feb. 2026) | Sysselsetting juli 2026 |
   |---|---|---|---|---|
   | 4110 Kontormedarbeidere | 0,59 (Q5) | 0,59 (Q5) | 67 % | 95,7 |
   | 3312 Kundebehandlere lån og kreditt | 0,61 (Q5) | 0,62 (Q5) | 30 % | 96,5 |

4. `get_occupation` for hvert yrke, plattform `claude_ai`, gir oppgavene.
   Kontormedarbeidere: feilsøking av kontorutstyr (1,26 prosent av all
   Claude-bruk, automatisering 60 prosent), skjemaer og reiseregninger (66
   prosent) og kontormaskiner (51 prosent). Kundebehandlere: anbefale
   økonomisk strategi (24 prosent), forklare kredittvurdering og regelverk (22
   prosent) og forklare lånetyper (27 prosent).

5. Tolkningen skriver du selv: samme eksponeringsskår, men i det ene yrket
   bestilles arbeidet ferdig, i det andre drøftes det. Det er det
   eksponeringsmålet ikke ser og bruksdataene viser.

Samme øvelse for en utdanning: `search_education` med «økonomi» på
bachelornivå gir faggruppe 641 Økonomisk-administrative fag, 101 315
sysselsatte, eksponering 0,55, halvparten i den mest eksponerte femdelen,
automatisering 43 prosent. `get_education_group` gir de ti vanligste
oppgavene i jobbene og de vanligste jobbene, regnskapsførere øverst.

Alle tall over er lest fra serveren 2026-10-15 med release 2026-10. Nye
releaser gir nye tall; kjør scriptet på nytt.

## Tilbakemeldinger

Knappen «Tilbakemelding» på `mcp.html` (`public/feedback.js`) og verktøyet
`send_feedback` skriver til `/data/feedback/feedback.jsonl` på Fly-volumet
`feedback_data` (se `[mounts]` i `fly.toml`). Lagret: tid, kilde, side, melding og
valgfri kontakt. Ikke lagret: IP-adresse. Ratebegrensning: 20 per klient og time, 500
per dag, med en saltet hash av adressen som slettes etter en time. Les meldingene:

```bash
python3 dashboard/mcp/feedback.py          # nye siden sist
python3 dashboard/mcp/feedback.py --all
```

`GET /feedback` svarer `{"writable": true, "durable": true}` når volumet er på plass.

## Lokal kjøring og testing

```bash
cd dashboard/mcp
python3 server.py --data-dir ../site/public/data --port 8765
python3 client_example.py --url http://localhost:8765/mcp
```

Uten `--data-dir` henter serveren fra nettstedet. `GET /health` svarer `ok`
når dataene er lastet, `GET /` gir en kort beskrivelse.
