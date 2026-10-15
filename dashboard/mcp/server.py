#!/usr/bin/env python3
"""MCP-kobling til KI-indeksen: dataene bak kiindeksen.no, Yrker og Utdanning som verktøy.

Serveren snakker Model Context Protocol og bruker bare standardbiblioteket, så den kan kjøre
hvor som helst uten installasjon. Transporter (2026-10-15, for alle klienter og leverandører):
    POST /mcp                 Streamable HTTP, JSON-RPC 2.0 (Claude, Codex, Kimi, OpenCode, Gemini CLI ...)
    GET /mcp                  lyttestrøm (SSE) for klienter som åpner en; serveren sender ingenting selv
    GET /sse + POST /messages eldre HTTP+SSE-transport (protokoll 2024-11-05) for eldre klienter
    --stdio                   MCP over stdin/stdout for klienter som bare starter lokale servere
    GET /tools/<navn>         samme verktøy som vanlige HTTP-kall (REST), argumenter i spørrestrengen
    POST /tools/<navn>        samme med JSON-kropp
    GET /openapi.json         OpenAPI 3.1 for REST-kallene, til funksjonskall hos andre modeller og GPT-er

    python3 server.py                          # henter dataene fra https://kiindeksen.no/data/
    python3 server.py --data-dir ../site/public/data --port 8765   # lokale filer, til testing
    python3 server.py --stdio                  # stdio-transport, logg på stderr

Dataene leses inn ved oppstart og hentes på nytt hver KIINDEKSEN_REFRESH_HOURS time (standard 6),
så koblingen følger den månedlige releasen uten ny utrulling. Alt er lesetilgang; ingen
personopplysninger, bare de aggregerte tallene nettstedet allerede publiserer.

Koble til:
    Claude Code:   claude mcp add --transport http kiindeksen https://<vert>/mcp
    claude.ai:     Settings -> Connectors -> Add custom connector -> https://<vert>/mcp
    Codex CLI:     codex mcp add kiindeksen --url https://<vert>/mcp
    Kimi Code CLI: kimi mcp add --transport http kiindeksen https://<vert>/mcp
    Eget script:   se client_example.py (JSON-RPC over HTTP, ingen avhengigheter)
    Flere klienter og API-kall fra kode: https://kiindeksen.no/mcp.html

Verktøyene står i TOOLS nederst; README.md i samme mappe forklarer dataene og har et
gjennomgått eksempel på en analyse.
"""
import argparse, json, os, sys, threading, time, urllib.request
import queue, uuid
from urllib.parse import parse_qs

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "1.0.0"
SERVER_NAME = "kiindeksen"
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
BASE = os.environ.get("KIINDEKSEN_BASE", "https://kiindeksen.no").rstrip("/")
DATA_DIR = os.environ.get("KIINDEKSEN_DATA_DIR")
REFRESH_HOURS = float(os.environ.get("KIINDEKSEN_REFRESH_HOURS", "6"))
MAX_BODY = 1_000_000

FILES = {"dashboard": "dashboard.json", "occupations": "occupations.json", "yrker": "yrker.json",
         "utdanning": "utdanning.json", "studio": "studio_papers.json", "vacancies": "vacancies.json"}
OPTIONAL = {"studio", "vacancies"}

INSTRUCTIONS = (
    "KI-indeksen (kiindeksen.no) følger måned for måned hvordan kunstig intelligens påvirker det norske "
    "arbeidsmarkedet, bygget på registerdata for alle lønnstakere i privat sektor (A-ordningen via microdata.no). "
    "Yrker grupperes i fem like store grupper etter KI-eksponeringen til oppgavene deres (Eloundou mfl. 2024, "
    "alternativt Mouchel mfl. 2026), og etter hvordan Claude faktisk brukes på oppgavene (Anthropic Economic Index). "
    "Start med get_release og list_packages. Tidsserier er indekser med 100 i november 2022 (måneden ChatGPT kom); "
    "bruk index_base for å flytte basen, for eksempel til 2025-02 (Claude Code, agentisk KI). "
    "Yrker er STYRK-08-koder på fire siffer; søk med search_occupations. Utdanninger er NUS-faggrupper på tre siffer "
    "(nivå + fag); søk med search_education. Oppgi alltid release, spesifikasjon (raw/sa/percap) og basismåned når du "
    "rapporterer tall. Tallene er aggregater og kan ikke knyttes til personer."
)

# ---------------------------------------------------------------- data

STATE = {"data": None, "loaded": None, "dicts": {}}
LOCK = threading.Lock()


def _read(name):
    if DATA_DIR:
        p = os.path.join(DATA_DIR, name)
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    req = urllib.request.Request(f"{BASE}/data/{name}", headers={"User-Agent": f"kiindeksen-mcp/{VERSION}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def load_data():
    d = {}
    for key, name in FILES.items():
        try:
            d[key] = _read(name)
        except Exception as e:                      # valgfrie filer kan mangle
            if key in OPTIONAL:
                d[key] = None
            else:
                raise RuntimeError(f"kunne ikke lese {name}: {e}")
    # oppslag
    d["occ_by_code"] = {o["code"]: o for o in d["occupations"]["occupations"]}
    d["yrk_by_code"] = {o["code"]: o for o in d["yrker"]["occupations"]}
    d["edu_by_code"] = {g["code"]: g for g in d["utdanning"]["groups"]}
    with LOCK:
        STATE["data"] = d
        STATE["loaded"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        STATE["dicts"] = {}
    return d


def data():
    with LOCK:
        d = STATE["data"]
    if d is None:
        d = load_data()
    return d


def refresher():
    while True:
        time.sleep(REFRESH_HOURS * 3600)
        try:
            load_data()
            print("data oppdatert", STATE["loaded"], flush=True)
        except Exception as e:
            print("oppdatering feilet:", e, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- helpers

class ToolError(Exception):
    pass


def ym(s):
    """'2025-02' eller '2025-02-01' -> '2025-02-01'."""
    if not s:
        return None
    s = str(s)
    if len(s) == 7:
        s += "-01"
    if len(s) != 10:
        raise ToolError(f"ugyldig måned: {s!r} (bruk YYYY-MM)")
    return s


def window(dates, start, end):
    i0 = 0 if not start else next((i for i, d in enumerate(dates) if d >= start), len(dates))
    i1 = len(dates) if not end else next((i for i, d in enumerate(dates) if d > end), len(dates))
    return i0, i1


def rebase(vals, dates, base):
    if not base:
        return vals
    if base not in dates:
        raise ToolError(f"basismåned {base[:7]} finnes ikke i serien ({dates[0][:7]} til {dates[-1][:7]})")
    b = vals[dates.index(base)]
    if b in (None, 0):
        raise ToolError(f"ingen verdi i basismåneden {base[:7]}")
    return [None if v is None else round(100 * v / b, 2) for v in vals]


def ma(vals, k):
    if not k or k <= 1:
        return vals
    out = []
    for i in range(len(vals)):
        w = [v for v in vals[max(0, i - k + 1): i + 1] if v is not None]
        out.append(round(sum(w) / len(w), 3) if len(w) == min(k, i + 1) else None)
    return out


def describe_package(name):
    sector = "offentlig sektor" if name.startswith("public_") else "privat sektor"
    core = name.replace("public_", "").replace("mouchel_", "")
    measure = "Mouchel mfl. (2026)" if name.startswith("mouchel_") else "Eloundou mfl. (2024)"
    if core.startswith("hires_"):
        outcome, core = "nyansettelser", core[6:]
    elif core.startswith("wages_"):
        outcome, core = "lønn (FTE-justert)", core[6:]
    else:
        outcome = "sysselsetting"
    grouping = {
        "by_exposure": "etter KI-eksponeringskvintil, alle aldre",
        "age_by_exposure": "etter eksponeringskvintil (facet) og aldersgruppe (serie)",
        "by_age": "etter aldersgruppe, alle yrker",
        "usage_patterns_by_age": "etter observert Claude-bruk (facet: Augmentation|Automation × aldersgruppe; serie: brukskvintil)",
        "software_developers": "yrkescase programvareutviklere (STYRK 2512-2514, 2519), etter aldersgruppe",
        "customer_service": "yrkescase kundesentermedarbeidere (STYRK 4222), etter aldersgruppe",
        "electricians": "yrkescase elektrikere (STYRK 7411), etter aldersgruppe",
        "home_health_aides": "yrkescase hjemmehjelpere (STYRK 5322), etter aldersgruppe",
    }.get(core, core)
    exposure_note = f", kvintiler etter {measure}" if "exposure" in core else ""
    return f"{outcome.capitalize()}, {sector}, {grouping}{exposure_note}."


def package(name):
    P = data()["dashboard"]["packages"]
    if name not in P:
        raise ToolError(f"ukjent pakke {name!r}; se list_packages")
    return P[name]


def occ_card(code):
    d = data()
    y = d["yrk_by_code"].get(code)
    x = d["yrker"]["extra"].get(code)
    o = d["occ_by_code"].get(code)
    if not (y or x or o):
        raise ToolError(f"ukjent STYRK-08-kode {code!r}; søk med search_occupations")
    src = y or x
    card = {"code": code, "name": (src or o)["name"], "name_en": (src or o).get("name_en"),
            "n_employees": (src or {}).get("n", o["n_base"] if o else None),
            "exposure_eloundou": (src or {}).get("beta"), "quintile_eloundou": (src or {}).get("q", o["quintile"] if o else None),
            "exposure_mouchel": (src or {}).get("mouchel"), "quintile_mouchel": (src or {}).get("q_mouchel"),
            "has_usage_data": bool(y), "has_series": bool(o)}
    if y:
        latest = {}
        for key, v in y["v"].items():
            plat, date = key.split("|")
            if plat not in latest or date > latest[plat][0]:
                latest[plat] = (date, v)
        card["automation_share_latest"] = {p: {"vintage": dv[0], "automation": dv[1]["auto"], "augmentation": dv[1]["aug"],
                                               "usage_share_pct": dv[1]["u"], "n_tasks_matched": dv[1]["nt"]}
                                           for p, dv in latest.items()}
    return card


# ---------------------------------------------------------------- tools

def t_get_release(a):
    d = data(); dash = d["dashboard"]
    dates = dash["packages"]["by_exposure"]["dates"]
    return {"release": dash["release"], "normalisation_month": dash["base_month"],
            "first_month": dates[0], "last_month": dates[-1], "n_packages": len(dash["packages"]),
            "n_occupations_with_series": len(d["occupations"]["occupations"]),
            "n_occupations_with_usage": d["yrker"]["n_occupations"],
            "n_education_groups": len(d["utdanning"]["groups"]),
            "education_register_vintage": d["utdanning"]["register_vintage"], "onet_version": d["utdanning"]["onet_version"],
            "aei_latest": d["utdanning"]["aei_latest"],
            "headline_eloundou_chatgpt": dash["headline_uncertainty"],
            "data_loaded_at": STATE["loaded"], "source": BASE or DATA_DIR,
            "note": "Serier er indekser med 100 i normalisation_month. KI-indeksen = vekst i kvintil 5 minus kvintil 1."}


def t_list_packages(a):
    P = data()["dashboard"]["packages"]
    out = []
    for name, p in P.items():
        specs = list(p["series"].keys()); facets = list(p["series"][specs[0]].keys())
        out.append({"package": name, "description": describe_package(name), "specs": specs,
                    "facets": facets, "series": list(p["series"][specs[0]][facets[0]].keys()),
                    "first_month": p["dates"][0], "last_month": p["dates"][-1]})
    return {"packages": out, "spec_meaning": {"raw": "antall lønnstakere, indeks", "sa": "sesongjustert", "percap": "per innbygger i aldersgruppen", "percap_sa": "per innbygger og sesongjustert"}}


def t_get_series(a):
    p = package(a["package"]); spec = a.get("spec", "sa")
    if spec not in p["series"]:
        raise ToolError(f"pakken har ikke spesifikasjonen {spec!r}; har {list(p['series'])}")
    facets = p["series"][spec]
    want_f = a.get("facet")
    if want_f is None:
        want_f = ["_"] if "_" in facets else list(facets)
    elif isinstance(want_f, str):
        want_f = [want_f]
    series_sel = a.get("series")
    if isinstance(series_sel, str):
        series_sel = [series_sel]
    start, end, base = ym(a.get("start")), ym(a.get("end")), ym(a.get("index_base"))
    k = int(a.get("moving_average") or 1)
    dates = p["dates"]; i0, i1 = window(dates, start, end)
    out = {}
    for f in want_f:
        if f not in facets:
            raise ToolError(f"ukjent facet {f!r}; har {list(facets)}")
        out[f] = {}
        for s, vals in facets[f].items():
            if series_sel and s not in series_sel:
                continue
            v = ma(vals, k)
            v = rebase(v, dates, base)
            out[f][s] = v[i0:i1]
    return {"package": a["package"], "spec": spec, "dates": dates[i0:i1], "facets": out,
            "index_base": base or data()["dashboard"]["base_month"], "moving_average": k,
            "description": describe_package(a["package"])}


def t_get_growth(a):
    p = package(a["package"]); spec = a.get("spec", "sa")
    if spec not in p["series"]:
        raise ToolError(f"pakken har ikke spesifikasjonen {spec!r}")
    ref = ym(a.get("reference") or "2022-10"); k = int(a.get("moving_average") or 3)
    dates = p["dates"]
    if ref not in dates:
        raise ToolError(f"referansemåneden {ref[:7]} finnes ikke")
    ir = dates.index(ref)
    out = {}
    for f, series in p["series"][spec].items():
        out[f] = {}
        for s, vals in series.items():
            v = ma(vals, k)
            if v[ir] is None or v[-1] is None or v[ir] == 0:
                out[f][s] = None
            else:
                out[f][s] = round(100 * (v[-1] / v[ir] - 1), 2)
        keys = list(out[f].keys())
        if len(keys) >= 2 and out[f][keys[0]] is not None and out[f][keys[-1]] is not None:
            out[f]["gap_last_minus_first_pp"] = round(out[f][keys[-1]] - out[f][keys[0]], 2)
    return {"package": a["package"], "spec": spec, "reference_month": ref, "last_month": dates[-1],
            "moving_average": k, "growth_pct": out,
            "note": "Vekst i prosent fra referansemåneden til siste måned, begge glattet med etterslepende snitt over moving_average måneder. "
                    "gap_last_minus_first_pp er siste serie minus første (for eksponeringspakker: kvintil 5 minus kvintil 1, KI-indeksens form). "
                    "Nettstedets offisielle hovedtall med usikkerhet får du fra get_headline."}


def t_get_headline(a):
    dash = data()["dashboard"]
    measure = a.get("measure", "eloundou"); ref = a.get("reference", "chatgpt"); young = bool(a.get("young", False))
    key = "headline_uncertainty" + ("_young" if young else "") + ("_claudecode" if ref == "claudecode" else "") + "_by_measure"
    if key not in dash or measure not in dash[key]:
        raise ToolError(f"finner ikke {key}/{measure}")
    h = dict(dash[key][measure])
    h.update({"measure": measure, "reference": ref, "population": "21-30 år" if young else "21-60 år",
              "meaning": "ki = prosentpoeng forskjell i sysselsettingsvekst mellom mest og minst eksponerte femdel siden referansen; "
                         "se = bootstrap-standardfeil; ci = 95 %-intervall"})
    return h


def t_get_composition(a):
    snaps = data()["dashboard"]["snapshots"]
    name = a.get("snapshot", "composition")
    if name not in snaps:
        raise ToolError(f"ukjent snapshot; har {list(snaps)}")
    return {"snapshot": name, **snaps[name]}


def _occ_search_rows():
    d = data(); rows = []
    seen = set()
    for o in d["yrker"]["occupations"]:
        seen.add(o["code"]); rows.append((o["code"], o["name"], o.get("name_en") or ""))
    for c, o in d["yrker"]["extra"].items():
        if c not in seen:
            seen.add(c); rows.append((c, o["name"], o.get("name_en") or ""))
    for o in d["occupations"]["occupations"]:
        if o["code"] not in seen:
            seen.add(o["code"]); rows.append((o["code"], o["name"], o.get("name_en") or ""))
    return rows


def t_search_occupations(a):
    q = str(a.get("query", "")).strip().lower(); limit = int(a.get("limit") or 20)
    if not q:
        raise ToolError("query mangler")
    hits = [c for c, n, e in _occ_search_rows() if q in c or q in n.lower() or q in e.lower()]
    hits.sort(key=lambda c: (not c.startswith(q), c))
    return {"query": a["query"], "n_hits": len(hits), "occupations": [occ_card(c) for c in hits[:limit]]}


def t_get_occupation(a):
    code = str(a.get("code", "")).zfill(4); d = data()
    card = occ_card(code); y = d["yrk_by_code"].get(code)
    if y:
        card["neighbours_by_onet_tasks"] = [{"code": n["code"], "name": d["yrk_by_code"].get(n["code"], d["yrker"]["extra"].get(n["code"], {})).get("name"),
                                            "similarity": n["sim"], "shared_elements": n["shared"]} for n in y["nb"]]
        card["usage_by_vintage"] = {k: v for k, v in y["v"].items()}
        card["vintages"] = [{"key": v["key"], "label": v["label"], "source": v["source"]} for v in d["yrker"]["vintages"]]
        if a.get("include_tasks", True):
            plat = a.get("platform", "claude_ai")
            rows = []
            for t in y["tasks"].get(plat, []):
                r = dict(t)
                r["auto"] = round((t.get("d") or 0) + (t.get("fb") or 0), 4)   # Anthropics regel: automatisering = direktiv + sløyfe
                rows.append(r)
            rows.sort(key=lambda r: -(r.get("pct") or 0))
            card["tasks"] = {"platform": plat, "rows": rows}
            card["task_fields"] = {"t": "O*NET-oppgave (engelsk)", "t_no": "norsk oversettelse", "soc": "SOC-koden oppgaven kommer fra",
                                   "pct": "prosent av all Claude-bruk som gjelder denne oppgaven, siste utgave", "n": "klassifiserte samtaler",
                                   "d/fb/ti/va/le": "andel direktiv, tilbakemeldingssløyfe, oppgaveiterasjon, validering, læring (Anthropics fem typer)",
                                   "auto": "automatisering = d + fb", "im": "O*NET importance (1-5)", "rt": "O*NET relevance (prosent av utøverne)",
                                   "rk": "rangering etter bruk", "nt": "antall oppgaver i yrket", "v": "per tidligere utgave: [d, fb, ti, va, le, n, pct]"}
        card["usage_fields"] = {"u": "yrkets andel av all Claude-bruk, prosent", "auto": "automatiseringsandel (direktiv + tilbakemeldingssløyfe)",
                                "aug": "augmenteringsandel", "d,fb,ti,va,le": "de fem samarbeidstypene", "n": "klassifiserte samtaler", "nt": "oppgaver med treff"}
    return card


def t_get_occupation_series(a):
    code = str(a.get("code", "")).zfill(4); d = data()
    o = d["occ_by_code"].get(code)
    if not o:
        raise ToolError(f"ingen tidsserie for {code} (bare yrker med minst 30 lønnstakere hver måned har serie)")
    outcome = a.get("outcome", "employment"); spec = a.get("spec", "sa")
    if outcome not in o or spec not in o[outcome]:
        raise ToolError(f"har ikke {outcome}/{spec}; har {[k for k in ('employment','wages') if k in o]} × {list(o['employment'])}")
    dates = d["occupations"]["dates"]
    start, end, base = ym(a.get("start")), ym(a.get("end")), ym(a.get("index_base"))
    k = int(a.get("moving_average") or 1)
    v = rebase(ma(o[outcome][spec], k), dates, base)
    i0, i1 = window(dates, start, end)
    return {"code": code, "name": o["name"], "outcome": outcome, "spec": spec, "quintile_eloundou": o["quintile"],
            "n_base": o["n_base"], "dates": dates[i0:i1], "values": v[i0:i1],
            "index_base": base or d["dashboard"]["base_month"], "moving_average": k,
            "note": "Privat sektor, 21-60 år, alle aldre samlet. Indeks 100 i index_base."}


def t_compare_occupations(a):
    codes = a.get("codes") or []
    if isinstance(codes, str):
        codes = [c.strip() for c in codes.split(",")]
    if not codes:
        raise ToolError("codes mangler")
    out = []
    for c in codes:
        card = occ_card(str(c).zfill(4))
        try:
            s = t_get_occupation_series({"code": c, "outcome": a.get("outcome", "employment"), "spec": a.get("spec", "sa"),
                                         "start": a.get("start"), "end": a.get("end"), "index_base": a.get("index_base"),
                                         "moving_average": a.get("moving_average")})
            card["series"] = {"dates": s["dates"], "values": s["values"], "index_base": s["index_base"]}
            card["last_value"] = s["values"][-1]
        except ToolError as e:
            card["series_error"] = str(e)
        out.append(card)
    return {"outcome": a.get("outcome", "employment"), "spec": a.get("spec", "sa"), "occupations": out}


def t_list_education_levels(a):
    u = data()["utdanning"]
    return {"levels": u["levels"], "exposure_versions": {"v1": "Eloundou mfl. (2024)", "v2": "Mouchel mfl. (2026)"},
            "quintile_cuts": u["quintile_cuts"], "top5_cut": u["top5_cut"], "register_vintage": u["register_vintage"]}


def edu_card(g):
    return {"code": g["code"], "level": g["level"], "field": g["field"], "name": g["name"], "field_name": g["field_name"],
            "n_total": g["n_total"], "n_employed": g["n_employed"], "share_employed": g["share_employed"],
            "exposure_v1": g["exposure_v1"], "exposure_v2": g["exposure_v2"], "share_in_top_quintile_v1": g["q5_v1"],
            "share_in_top_quintile_v2": g["q5_v2"], "automation": g["automation"], "n_occupations": g["n_occ"]}


def t_search_education(a):
    u = data()["utdanning"]; q = str(a.get("query", "")).strip().lower(); level = a.get("level"); limit = int(a.get("limit") or 20)
    groups = [g for g in u["groups"] if not level or g["level"] == str(level)]
    if q:
        hit_codes = {n["g"] for n in u["names"] if q in n["n"].lower() or q in (n.get("s") or "").lower() or q in (n.get("e") or "").lower() or q in n["c"]}
        groups = [g for g in groups if q in g["name"].lower() or q in g["field_name"].lower() or q in g["code"] or g["code"] in hit_codes]
    groups.sort(key=lambda g: -g["n_total"])
    return {"query": q, "level": level, "n_hits": len(groups), "groups": [edu_card(g) for g in groups[:limit]],
            "fields": {"exposure_v1": "gjennomsnittlig eksponering i jobbene (Eloundou)", "exposure_v2": "samme med Mouchel",
                       "share_in_top_quintile": "andel sysselsatte i mest eksponerte femdel", "automation": "automatiseringsandel i Claude-bruk, vektet"}}


def t_get_education_group(a):
    code = str(a.get("code", "")); g = data()["edu_by_code"].get(code)
    if not g:
        raise ToolError(f"ukjent faggruppe {code!r}; søk med search_education")
    out = edu_card(g)
    out.update({"q_v1": g["q_v1"], "q_v2": g["q_v2"], "task_exposure": g["task_exposure"], "task_automation": g["task_automation"],
                "tasks": g["tasks"], "occupations_all": g["occ_all"], "occupations_recent_graduates": g["occ_recent"], "n_recent": g["n_recent"],
                "fields": {"q_v1/q_v2": "andel sysselsatte i kvintil 1-5", "tasks": "de ti vanligste O*NET-oppgavene i jobbene, med eksponering (e) og automatisering (auto)",
                           "occupations_all": "vanligste yrker, andel av sysselsatte", "occupations_recent_graduates": "samme for dem som fullførte for 1-3 år siden"}})
    return out


def t_list_downloads(a):
    dash = data()["dashboard"]; rel = dash["release"]
    base = f"{BASE}/data/releases/{rel}"
    out = []
    for name, kinds in dash["download_files"].items():
        folder = f"canaries_no_{name}"
        files = {}
        for k in kinds:
            suffix = {"csv": ".csv", "yoy_change": "_yoy_change.csv", "annualized": "_annualized.csv", "data_dictionary": "_data_dictionary.md"}[k]
            files[k] = f"{base}/{folder}/{folder}{suffix}"
        out.append({"package": name, "files": files})
    return {"release": rel, "downloads": out, "note": "Lange CSV-er i Stanford Canaries-format, med kolonnen adjustment (raw/sa/percap/percap_sa). Se get_data_dictionary."}


def t_get_data_dictionary(a):
    name = a.get("package", "by_exposure"); dash = data()["dashboard"]
    if name not in dash["download_files"]:
        raise ToolError(f"ukjent pakke {name!r}; se list_downloads")
    with LOCK:
        cached = STATE["dicts"].get(name)
    if cached:
        return {"package": name, "text": cached}
    folder = f"canaries_no_{name}"; rel = dash["release"]
    if DATA_DIR:
        with open(os.path.join(DATA_DIR, "releases", rel, folder, f"{folder}_data_dictionary.md"), encoding="utf-8") as f:
            text = f.read()
    else:
        req = urllib.request.Request(f"{BASE}/data/releases/{rel}/{folder}/{folder}_data_dictionary.md", headers={"User-Agent": f"kiindeksen-mcp/{VERSION}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8")
    with LOCK:
        STATE["dicts"][name] = text
    return {"package": name, "text": text}


def t_get_studio_papers(a):
    s = data()["studio"]
    if not s:
        raise ToolError("studio_papers.json er ikke tilgjengelig")
    typ = a.get("type"); papers = [p for p in s["papers"] if not typ or p.get("type") == typ]
    return {"updated": s.get("updated"), "n": len(papers), "papers": papers}


TOOLS = [
    ("get_release", "Release, periode, normaliseringsmåned, antall yrker og utdanninger, og hovedtallet (KI-indeksen) med usikkerhet. Start her.",
     {"type": "object", "properties": {}}, t_get_release),
    ("list_packages", "Alle tidsseriepakkene bak kiindeksen.no (sysselsetting, nyansettelser, lønn; privat og offentlig sektor; Eloundou- og Mouchel-kvintiler; yrkescase; bruksmønster), med facets, serier og spesifikasjoner.",
     {"type": "object", "properties": {}}, t_list_packages),
    ("get_series", "Hent tidsserier fra en pakke. Indeks 100 i november 2022; flytt basen med index_base (YYYY-MM), for eksempel 2025-02 for Claude Code.",
     {"type": "object", "properties": {
         "package": {"type": "string", "description": "pakkenavn fra list_packages, f.eks. by_exposure, age_by_exposure, software_developers"},
         "spec": {"type": "string", "enum": ["raw", "sa", "percap", "percap_sa"], "default": "sa"},
         "facet": {"type": ["string", "array", "null"], "description": "facet, '_' for pakker uten facets; utelatt = alle"},
         "series": {"type": ["string", "array", "null"], "description": "serienavn, f.eks. 'Quintile 5 (most exposed)' eller '21-30'; utelatt = alle"},
         "start": {"type": "string", "description": "YYYY-MM"}, "end": {"type": "string", "description": "YYYY-MM"},
         "index_base": {"type": "string", "description": "YYYY-MM; serien skaleres til 100 i denne måneden"},
         "moving_average": {"type": "integer", "description": "etterslepende glatting i måneder, 1 = ingen", "default": 1}},
      "required": ["package"]}, t_get_series),
    ("get_growth", "Vekst i prosent fra en referansemåned til siste måned for alle serier i en pakke, glattet, pluss gapet siste minus første serie (KI-indeksens form: kvintil 5 minus kvintil 1).",
     {"type": "object", "properties": {"package": {"type": "string"}, "spec": {"type": "string", "default": "sa"},
                                       "reference": {"type": "string", "description": "YYYY-MM, standard 2022-10 (måneden før ChatGPT); 2025-01 gir Claude Code-referansen"},
                                       "moving_average": {"type": "integer", "default": 3}}, "required": ["package"]}, t_get_growth),
    ("get_headline", "Nettstedets offisielle hovedtall: KI-indeksen i prosentpoeng med bootstrap-standardfeil og 95 %-intervall, per eksponeringsmål, referanse og aldersgruppe.",
     {"type": "object", "properties": {"measure": {"type": "string", "enum": ["eloundou", "mouchel"], "default": "eloundou"},
                                       "reference": {"type": "string", "enum": ["chatgpt", "claudecode"], "default": "chatgpt"},
                                       "young": {"type": "boolean", "description": "true = 21-30 år", "default": False}}}, t_get_headline),
    ("get_composition", "Sammensetning: andel av de ansatte per aldersgruppe og eksponeringskvintil (eller brukskvintil), i siste måned.",
     {"type": "object", "properties": {"snapshot": {"type": "string", "enum": ["composition", "usage_augmentation_ratio_composition", "usage_automation_ratio_composition", "public_composition"], "default": "composition"}}}, t_get_composition),
    ("search_occupations", "Søk etter yrker (STYRK-08) på kode eller navn, norsk eller engelsk. Gir eksponering (Eloundou og Mouchel), kvintil, antall lønnstakere og siste automatiseringsandel.",
     {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 20}}, "required": ["query"]}, t_search_occupations),
    ("get_occupation", "Alt om ett yrke: eksponeringsskår, kvintiler, Claude-bruk per utgave (automatisering, augmentering, de fem samarbeidstypene), de tre nærmeste yrkene etter O*NET-oppgaver, og oppgavene med bruksandel og automatisering.",
     {"type": "object", "properties": {"code": {"type": "string", "description": "STYRK-08, fire siffer"}, "include_tasks": {"type": "boolean", "default": True},
                                       "platform": {"type": "string", "enum": ["claude_ai", "api"], "default": "claude_ai"}}, "required": ["code"]}, t_get_occupation),
    ("get_occupation_series", "Sysselsetting eller lønn for ett yrke, månedlig fra 2021, privat sektor, indeks. Krever at yrket har minst 30 lønnstakere hver måned.",
     {"type": "object", "properties": {"code": {"type": "string"}, "outcome": {"type": "string", "enum": ["employment", "wages"], "default": "employment"},
                                       "spec": {"type": "string", "enum": ["raw", "sa"], "default": "sa"}, "start": {"type": "string"}, "end": {"type": "string"},
                                       "index_base": {"type": "string"}, "moving_average": {"type": "integer", "default": 1}}, "required": ["code"]}, t_get_occupation_series),
    ("compare_occupations", "Flere yrker side om side: eksponering, automatisering og tidsserie for hvert, med felles base. Bruk den til par med lik eksponering og ulik automatisering.",
     {"type": "object", "properties": {"codes": {"type": ["array", "string"], "items": {"type": "string"}, "description": "liste med STYRK-08-koder"},
                                       "outcome": {"type": "string", "enum": ["employment", "wages"], "default": "employment"}, "spec": {"type": "string", "default": "sa"},
                                       "start": {"type": "string"}, "end": {"type": "string"}, "index_base": {"type": "string"}, "moving_average": {"type": "integer"}},
      "required": ["codes"]}, t_compare_occupations),
    ("list_education_levels", "Utdanningsnivåene (NUS), eksponeringsversjonene og kvintilgrensene som Utdanning-siden bruker.",
     {"type": "object", "properties": {}}, t_list_education_levels),
    ("search_education", "Søk etter faggrupper (NUS, tre siffer: nivå + fag) på navn, engelsk navn, NUS6-kode eller enkeltutdanning. Gir eksponering, andel i mest eksponerte femdel og automatisering i jobbene utdanningen fører til.",
     {"type": "object", "properties": {"query": {"type": "string"}, "level": {"type": "string", "description": "nivåkode 3-8, se list_education_levels"}, "limit": {"type": "integer", "default": 20}}}, t_search_education),
    ("get_education_group", "Alt om én faggruppe: de ti vanligste oppgavene i jobbene med eksponering og automatisering, kvintilfordeling, og de vanligste jobbene (alle og nyutdannede).",
     {"type": "object", "properties": {"code": {"type": "string", "description": "faggruppekode, f.eks. 641"}}, "required": ["code"]}, t_get_education_group),
    ("list_downloads", "Nedlastbare CSV-er for releasen (lange tabeller i Canaries-format) med adresser, per pakke.",
     {"type": "object", "properties": {}}, t_list_downloads),
    ("get_data_dictionary", "Dokumentasjonen (data dictionary) for en nedlastbar pakke: konvensjoner, kolonner, kilder.",
     {"type": "object", "properties": {"package": {"type": "string", "default": "by_exposure"}}}, t_get_data_dictionary),
    ("get_studio_papers", "Arbeidslista i Studio: nye artikler og rapporter om KI og arbeid, med status og plan.",
     {"type": "object", "properties": {"type": {"type": "string", "enum": ["forskning", "anthropic", "rapport"]}}}, t_get_studio_papers),
]
TOOL_MAP = {name: (desc, schema, fn) for name, desc, schema, fn in TOOLS}

RESOURCES = [
    {"uri": "kiindeksen://om", "name": "Om KI-indeksen og koblingen", "mimeType": "text/plain", "description": "Hva dataene er, hvordan de er bygget, og hvordan tallene bør rapporteres."},
    {"uri": "kiindeksen://konvensjoner", "name": "Konvensjoner i tidsseriene", "mimeType": "text/markdown", "description": "Data dictionary for by_exposure: normalisering, sesongjustering, per innbygger."},
]

PROMPTS = [
    {"name": "analyser_yrkespar", "description": "Sammenlign to yrker med lik eksponering og ulik automatisering: skår, bruk, oppgaver og sysselsetting siden Claude Code.",
     "arguments": [{"name": "code_a", "description": "STYRK-08-kode", "required": True}, {"name": "code_b", "description": "STYRK-08-kode", "required": True}]},
    {"name": "maanedsrapport", "description": "Kort månedsrapport fra siste release: hovedtall med usikkerhet, de unge, og ett yrkescase.", "arguments": []},
]


def prompt_text(name, args):
    if name == "analyser_yrkespar":
        a, b = args.get("code_a", ""), args.get("code_b", "")
        return (f"Bruk KI-indeksen-koblingen. 1) get_occupation for {a} og {b}: sammenlign eksponeringsskår (Eloundou og Mouchel), kvintil og automatiseringsandel i siste Claude.ai-utgave. "
                f"2) Finn de tre oppgavene med mest bruk i hvert yrke og oppgi automatiseringsandelen per oppgave. "
                f"3) compare_occupations med codes [{a}, {b}], outcome employment, spec sa, index_base 2025-02, og rapporter siste verdi for hvert. "
                f"4) Skriv tre korte avsnitt: lik eksponering, ulik bruk, ulik utvikling. Oppgi release og basismåned. Ingen tall du ikke har hentet.")
    if name == "maanedsrapport":
        return ("Bruk KI-indeksen-koblingen. 1) get_release og get_headline (eloundou, chatgpt), samt get_headline med young true og reference claudecode. "
                "2) get_growth for by_exposure og age_by_exposure med reference 2025-01. 3) get_series for software_developers, spec percap_sa, index_base 2022-10, siste verdi per aldersgruppe. "
                "4) Skriv en rapport på under 200 ord: hovedtallet med intervall, de unge, og yrkescaset. Oppgi release, spesifikasjon og base i hver setning med tall.")
    raise ToolError(f"ukjent prompt {name!r}")


def resource_text(uri):
    if uri == "kiindeksen://om":
        return INSTRUCTIONS + "\n\nVerktøy: " + ", ".join(n for n, *_ in TOOLS) + ".\nNettsted: https://kiindeksen.no. Metode og sitering: https://kiindeksen.no/#metode og /#sitering."
    if uri == "kiindeksen://konvensjoner":
        return t_get_data_dictionary({"package": "by_exposure"})["text"]
    raise ToolError(f"ukjent ressurs {uri!r}")


# ---------------------------------------------------------------- JSON-RPC

def rpc_error(id_, code, message):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def handle_message(msg, proto):
    """Én JSON-RPC-melding -> svar (dict) eller None for notifikasjoner."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
        return rpc_error(msg.get("id") if isinstance(msg, dict) else None, -32600, "ugyldig forespørsel")
    method, params, id_ = msg["method"], msg.get("params") or {}, msg.get("id")
    if id_ is None:
        return None                                      # notifikasjon (notifications/initialized m.m.)
    try:
        if method == "initialize":
            req = params.get("protocolVersion", PROTOCOLS[0])
            result = {"protocolVersion": req if req in PROTOCOLS else PROTOCOLS[0],
                      "capabilities": {"tools": {"listChanged": False}, "resources": {"subscribe": False, "listChanged": False}, "prompts": {"listChanged": False}},
                      "serverInfo": {"name": SERVER_NAME, "title": "KI-indeksen", "version": VERSION},
                      "instructions": INSTRUCTIONS}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [{"name": n, "description": d, "inputSchema": s} for n, d, s, _ in TOOLS]}
        elif method == "tools/call":
            name = params.get("name"); args = params.get("arguments") or {}
            if name not in TOOL_MAP:
                return rpc_error(id_, -32602, f"ukjent verktøy {name!r}")
            try:
                out = TOOL_MAP[name][2](args)
                result = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}], "isError": False}
                if proto >= "2025-06-18":
                    result["structuredContent"] = out
            except ToolError as e:
                result = {"content": [{"type": "text", "text": str(e)}], "isError": True}
        elif method == "resources/list":
            result = {"resources": RESOURCES}
        elif method == "resources/templates/list":
            result = {"resourceTemplates": []}
        elif method == "resources/read":
            uri = params.get("uri", "")
            mime = next((r["mimeType"] for r in RESOURCES if r["uri"] == uri), "text/plain")
            result = {"contents": [{"uri": uri, "mimeType": mime, "text": resource_text(uri)}]}
        elif method == "prompts/list":
            result = {"prompts": PROMPTS}
        elif method == "prompts/get":
            name = params.get("name"); args = params.get("arguments") or {}
            result = {"description": next((p["description"] for p in PROMPTS if p["name"] == name), ""),
                      "messages": [{"role": "user", "content": {"type": "text", "text": prompt_text(name, args)}}]}
        elif method in ("logging/setLevel", "completion/complete"):
            result = {}
        else:
            return rpc_error(id_, -32601, f"ukjent metode {method!r}")
    except ToolError as e:
        return rpc_error(id_, -32602, str(e))
    except Exception as e:                              # pragma: no cover
        return rpc_error(id_, -32603, f"intern feil: {e}")
    return {"jsonrpc": "2.0", "id": id_, "result": result}


# ---------------------------------------------------------------- andre transporter og REST
# Eldre HTTP+SSE-transport (protokoll 2024-11-05): sessionId -> kø med svar som skal ut på
# klientens strøm. Streamable HTTP over POST /mcp er fortsatt hovedveien.
SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
SSE_KEEPALIVE = 15          # sekunder mellom kommentarlinjer som holder strømmen åpen
SSE_MAX_SECONDS = 3600      # en strøm lukkes etter en time; klienten kobler til på nytt


def _types(prop):
    t = prop.get("type", "string")
    return t if isinstance(t, list) else [t]


def coerce_args(schema, raw):
    """Spørrestreng (alle verdier er tekst) -> argumenter etter verktøyets JSON-skjema.
    Lister gis kommaseparert (codes=4110,3312)."""
    props = schema.get("properties", {})
    out = {}
    for k, vals in raw.items():
        v = vals[-1] if isinstance(vals, list) else vals
        if k not in props:
            out[k] = v
            continue
        types = _types(props[k])
        if "array" in types and ("," in v or "string" not in types):
            out[k] = [x.strip() for x in v.split(",") if x.strip()]
        elif "integer" in types:
            out[k] = int(v)
        elif "number" in types:
            out[k] = float(v)
        elif "boolean" in types:
            out[k] = v.lower() in ("1", "true", "ja", "yes")
        else:
            out[k] = v
    return out


def rest_call(name, args):
    """Kall et verktøy utenom MCP. Returnerer (HTTP-status, JSON-objekt)."""
    if name not in TOOL_MAP:
        return 404, {"error": f"ukjent verktøy {name!r}", "tools": [n for n, *_ in TOOLS]}
    try:
        return 200, TOOL_MAP[name][2](args)
    except ToolError as e:
        return 400, {"error": str(e)}
    except (ValueError, TypeError, KeyError) as e:
        return 400, {"error": f"ugyldig argument: {e}"}


def _query_param(name, prop, required):
    types = [t for t in _types(prop) if t != "null"]
    desc = prop.get("description", "")
    if "array" in types:
        sch = {"type": "string"}
        desc = (desc + " (kommaseparert liste)").strip()
    else:
        sch = {"type": types[0] if types else "string"}
        for key in ("enum", "default"):
            if key in prop:
                sch[key] = prop[key]
    p = {"name": name, "in": "query", "required": required, "schema": sch}
    if desc:
        p["description"] = desc
    return p


def openapi_spec(public_url):
    """OpenAPI 3.1 for REST-endepunktene, generert fra verktøyskjemaene, så GPT-er,
    agentplattformer og funksjonskall hos andre modelleverandører kan bruke dataene."""
    ok = {"description": "Resultat som JSON", "content": {"application/json": {"schema": {"type": "object"}}}}
    err = {"description": "Feil i argumentene", "content": {"application/json": {
        "schema": {"type": "object", "properties": {"error": {"type": "string"}}}}}}
    paths = {}
    for name, desc, schema, _ in TOOLS:
        req = set(schema.get("required", []))
        params = [_query_param(k, p, k in req) for k, p in schema.get("properties", {}).items()]
        paths[f"/tools/{name}"] = {
            "get": {"operationId": name, "summary": desc, "parameters": params,
                    "responses": {"200": ok, "400": err}},
            "post": {"operationId": name + "_post", "summary": desc,
                     "requestBody": {"required": bool(req), "content": {"application/json": {"schema": schema}}},
                     "responses": {"200": ok, "400": err}}}
    return {"openapi": "3.1.0",
            "info": {"title": "KI-indeksen", "version": VERSION,
                     "description": "Dataene bak kiindeksen.no som enkle HTTP-kall, samme verktøy som MCP-serveren. " + INSTRUCTIONS},
            "servers": [{"url": public_url}],
            "paths": paths}


def serve_stdio():
    """MCP stdio-transport: én JSON-RPC-melding per linje inn på stdin, svar ut på stdout.
    For klienter som bare starter lokale servere. Alt annet (logg) går til stderr."""
    out = sys.stdout
    sys.stdout = sys.stderr
    load_data()
    print(f"lastet release {STATE['data']['dashboard']['release']} fra {DATA_DIR or BASE}", flush=True)
    if not DATA_DIR:
        threading.Thread(target=refresher, daemon=True).start()
    proto = PROTOCOLS[0]
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            reply = rpc_error(None, -32700, "ugyldig JSON")
        else:
            if isinstance(msg, dict) and msg.get("method") == "initialize":
                req = (msg.get("params") or {}).get("protocolVersion", proto)
                proto = req if req in PROTOCOLS else PROTOCOLS[0]
            reply = handle_message(msg, proto)
        if reply is not None:
            out.write(json.dumps(reply, ensure_ascii=False) + "\n")
            out.flush()


class Handler(BaseHTTPRequestHandler):
    server_version = f"kiindeksen-mcp/{VERSION}"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept, Authorization, Mcp-Session-Id, MCP-Protocol-Version")
        self.send_header("Access-Control-Expose-Headers", "Mcp-Session-Id, MCP-Protocol-Version")

    def _send(self, status, body=b"", ctype="application/json; charset=utf-8", extra=None):
        self.send_response(status)
        self._cors()
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        if body:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            d = STATE["data"]
            rel = d["dashboard"]["release"] if d else "ikke lastet"
            text = (f"KI-indeksen MCP-kobling {VERSION}. Release {rel}.\n"
                    "MCP: POST /mcp (Streamable HTTP, JSON-RPC 2.0). Eldre HTTP+SSE: GET /sse, POST /messages. "
                    "Stdio: python3 server.py --stdio.\n"
                    "REST: GET /tools, GET eller POST /tools/<navn>, GET /openapi.json.\n"
                    f"Verktøy: {', '.join(n for n, *_ in TOOLS)}.\n"
                    "Dokumentasjon: https://kiindeksen.no/mcp.html. Kode: https://github.com/andreaskostol/AI-Norway (dashboard/mcp).\n")
            self._send(200, text.encode("utf-8"), "text/plain; charset=utf-8")
        elif path == "/health":
            ok = STATE["data"] is not None
            self._send(200 if ok else 503, (b"ok\n" if ok else b"loading\n"), "text/plain")
        elif path == "/mcp":
            # Streamable HTTP: klienter kan åpne en lyttestrøm med GET. Serveren sender
            # ingen egne meldinger, men holder strømmen åpen så klienten ikke feiler.
            if "text/event-stream" in (self.headers.get("Accept") or ""):
                self._sse_headers()
                self._sse_loop(queue.Queue())
            else:
                self._send(405, b"", extra={"Allow": "POST, OPTIONS"})
        elif path == "/sse":
            # Eldre HTTP+SSE-transport: klienten åpner GET /sse, får en endpoint-hendelse
            # med adressen den skal POSTe til, og mottar alle svar på denne strømmen.
            sid = uuid.uuid4().hex
            q = queue.Queue()
            with SESSIONS_LOCK:
                SESSIONS[sid] = q
            try:
                self._sse_headers()
                self.wfile.write(f"event: endpoint\ndata: /messages?sessionId={sid}\n\n".encode("utf-8"))
                self.wfile.flush()
                self._sse_loop(q)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with SESSIONS_LOCK:
                    SESSIONS.pop(sid, None)
        elif path == "/openapi.json":
            self._send(200, json.dumps(openapi_spec(self._public_url()), ensure_ascii=False).encode("utf-8"))
        elif path == "/tools":
            body = {"tools": [{"name": n, "description": d, "inputSchema": sch} for n, d, sch, _ in TOOLS]}
            self._send(200, json.dumps(body, ensure_ascii=False).encode("utf-8"))
        elif path.startswith("/tools/"):
            name = path[len("/tools/"):]
            qs = parse_qs(self.path.partition("?")[2], keep_blank_values=False)
            schema = TOOL_MAP[name][1] if name in TOOL_MAP else {}
            try:
                status, out = rest_call(name, coerce_args(schema, qs))
            except ValueError as e:
                status, out = 400, {"error": f"ugyldig argument: {e}"}
            self._send(status, json.dumps(out, ensure_ascii=False).encode("utf-8"))
        else:
            self._send(404, b"not found\n", "text/plain")

    def _public_url(self):
        proto = self.headers.get("X-Forwarded-Proto") or "http"
        return f"{proto}://{self.headers.get('Host', 'localhost')}"

    def _sse_headers(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

    def _sse_loop(self, q):
        """Skriv svar fra køen til strømmen, med kommentarlinjer som holder den åpen,
        til klienten kobler fra eller tiden er ute."""
        t0 = time.time()
        while time.time() - t0 < SSE_MAX_SECONDS:
            try:
                item = q.get(timeout=SSE_KEEPALIVE)
            except queue.Empty:
                item = None
            try:
                if item is None:
                    self.wfile.write(b": keep-alive\n\n")
                else:
                    self.wfile.write(f"event: message\ndata: {json.dumps(item, ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                break

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            self._send(413, b"for stor\n", "text/plain")
            return None
        return self.rfile.read(n) if n else b""

    def do_DELETE(self):
        self._send(200 if self.path.split("?")[0] == "/mcp" else 404)

    def do_POST(self):
        path, _, query = self.path.partition("?")
        if path.startswith("/tools/"):                   # REST med JSON-kropp
            raw = self._body()
            if raw is None:
                return
            try:
                args = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                return self._send(400, b'{"error": "ugyldig JSON"}')
            status, out = rest_call(path[len("/tools/"):], args if isinstance(args, dict) else {})
            return self._send(status, json.dumps(out, ensure_ascii=False).encode("utf-8"))
        if path == "/messages":                          # eldre HTTP+SSE: svaret går på strømmen
            sid = (parse_qs(query).get("sessionId") or parse_qs(query).get("session_id") or [""])[0]
            with SESSIONS_LOCK:
                q = SESSIONS.get(sid)
            if q is None:
                return self._send(404, b"ukjent eller utloept sesjon; aapne GET /sse paa nytt\n", "text/plain")
            raw = self._body()
            if raw is None:
                return
            try:
                msg = json.loads(raw.decode("utf-8") or "null")
            except Exception:
                return self._send(400, json.dumps(rpc_error(None, -32700, "ugyldig JSON")).encode("utf-8"))
            for m in (msg if isinstance(msg, list) else [msg]):
                r = handle_message(m, "2024-11-05")
                if r is not None:
                    q.put(r)
            return self._send(202)
        if path not in ("/mcp", "/"):
            return self._send(404, b"not found\n", "text/plain")
        raw = self._body()
        if raw is None:
            return
        try:
            msg = json.loads(raw.decode("utf-8") or "null")
        except Exception:
            body = json.dumps(rpc_error(None, -32700, "ugyldig JSON")).encode("utf-8")
            return self._send(400, body)
        proto = self.headers.get("MCP-Protocol-Version") or "2025-03-26"
        msgs = msg if isinstance(msg, list) else [msg]
        replies = [r for r in (handle_message(m, proto) for m in msgs) if r is not None]
        if not replies:
            return self._send(202)
        out = replies if isinstance(msg, list) else replies[0]
        self._send(200, json.dumps(out, ensure_ascii=False).encode("utf-8"), extra={"MCP-Protocol-Version": proto})

    def log_message(self, fmt, *args):             # kort logg: metode, sti, status
        print(f"{self.address_string()} {fmt % args}", flush=True)


def main():
    global BASE, DATA_DIR
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--base", help="nettsted dataene hentes fra (standard https://kiindeksen.no)")
    ap.add_argument("--data-dir", help="les JSON-filene lokalt i stedet (dashboard/site/public/data)")
    ap.add_argument("--stdio", action="store_true",
                    help="MCP over stdin/stdout for klienter som bare starter lokale servere; dataene hentes fortsatt fra nettstedet")
    a = ap.parse_args()
    if a.base:
        BASE = a.base.rstrip("/")
    if a.data_dir:
        DATA_DIR = a.data_dir
    if a.stdio:
        return serve_stdio()
    load_data()
    print(f"lastet release {STATE['data']['dashboard']['release']} fra {DATA_DIR or BASE}", flush=True)
    if not DATA_DIR:
        threading.Thread(target=refresher, daemon=True).start()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"KI-indeksen MCP på http://{a.host}:{a.port}/mcp", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
