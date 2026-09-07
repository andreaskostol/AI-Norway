#!/usr/bin/env python3
"""
Graduates, PhDs and registered students per study programme from DBH
(HK-dir), for every Norwegian institution with at least MIN_GRADS graduates
in the latest year.

Repo version of Edutech/education-analysis/data/dbh/fetch_dbh.py (which
covered six institutions). Same endpoint, same tables, same query rules:

  POST https://dbh.hkdir.no/api/Tabeller/hentJSONTabellData
  104  Ferdige kandidater (aggregert)   graduates = qualifications awarded, excl. PhD
  101  Avlagte doktorgrader (aggregert) PhD degrees
  123  Registrerte studenter            registered students, autumn semester
  211  Institusjon                      institution list (names, short names)
  436  Undernivaa                       level codes

  * Aggregated tables: send "groupBy", no "variabler"; counts come back.
  * List tables: send "variabler": ["*"], no "groupBy".
  * "kodetekst": "J" adds the name column of every coded variable.
  * Small cells are suppressed and shown as 0; the coarsest grouping loses
    least, so programme rows are pulled without avdeling.

Outputs, under data/education_analysis/dbh/:
  institutions.csv            code, name, short name, type, latest-year graduates
  nivaakoder.csv              level codes
  graduates_by_program.csv    table 104, institution x year x programme, YEARS
  graduates_phd_by_program.csv table 101
  students_by_program.csv     table 123, autumn semesters
  raw/*.json                  every API reply, incl. 104_kandidater_totaler.json
                              (all institutions) and 123_registrerte_totaler.json

Run:  python3 analysis/07_education/fetch_dbh.py
"""

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://dbh.hkdir.no"
API = BASE + "/api/Tabeller/hentJSONTabellData"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT_DIR = os.path.join(REPO, "data", "education_analysis", "dbh")
RAW_DIR = os.path.join(OUT_DIR, "raw")

YEARS = [str(y) for y in range(2019, 2026)]
LATEST = YEARS[-1]
AUTUMN = "3"
MIN_GRADS = 50        # institutions with fewer graduates in LATEST are skipped
T_GRADUATES, T_PHD, T_STUDENTS, T_INSTITUTIONS, T_LEVELS = 104, 101, 123, 211, 436


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def post(body, raw_name, retries=3):
    path = os.path.join(RAW_DIR, raw_name)
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API, data=data, headers={
                "Content-Type": "application/json; charset=UTF-8"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                raw = resp.read()
            with open(path, "wb") as f:
                f.write(raw)
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict):
                raise RuntimeError(parsed.get("message", str(parsed)[:300]))
            has_status = parsed and "status" in parsed[0]
            status = parsed[0]["status"] if has_status else {}
            rows = parsed[1:] if has_status else parsed
            log(f"  {raw_name}: {len(rows)} rows  ({status.get('melding', '')})")
            return rows
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError,
                json.JSONDecodeError, TimeoutError) as e:
            last_err = e
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"FAILED {raw_name}: {last_err}")


def item(var, values):
    return {"variabel": var, "selection": {"filter": "item", "values": list(values)}}


def agg_query(table, group_by, filters, sort_by=None):
    return {"tabell_id": table, "api_versjon": 1, "statuslinje": "J", "kodetekst": "J",
            "desimal_separator": ".", "groupBy": group_by,
            "sortBy": sort_by or group_by[:2], "filter": filters}


def list_query(table, filters, sort_by):
    return {"tabell_id": table, "api_versjon": 1, "statuslinje": "J", "kodetekst": "J",
            "desimal_separator": ".", "variabler": ["*"], "sortBy": sort_by, "filter": filters}


def to_int(v):
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return None


RENAME = {
    "Institusjonskode": "institusjonskode", "Institusjonsnavn": "institusjonsnavn",
    "Årstall": "aar", "Semester": "semester", "Semesternavn": "semesternavn",
    "Studentkategori": "studentkategori", "Studieprogramkode": "studieprogramkode",
    "Studieprogramnavn": "studieprogramnavn", "Studiumkode": "studiumkode",
    "Studnavn": "studiumnavn", "Nivåkode": "nivaakode", "Nivånavn": "nivaanavn",
    "NUS-kode": "nus_kode", "Studiepoeng": "studiepoeng",
}


def tidy(rows, prefix):
    out = []
    for r in rows:
        d = {RENAME.get(k, k): v for k, v in r.items()}
        tot = to_int(r.get("Antall totalt"))
        k, m = to_int(r.get("Antall kvinner")), to_int(r.get("Antall menn"))
        suppressed = 0
        if tot is not None and tot > 0 and (k or 0) + (m or 0) < tot:
            k, m, suppressed = "", "", 1
        d[f"{prefix}_totalt"] = tot if tot is not None else ""
        d[f"{prefix}_kvinner"] = k if k is not None else ""
        d[f"{prefix}_menn"] = m if m is not None else ""
        d["kjonn_skjermet"] = suppressed
        for c in ("Antall totalt", "Antall kvinner", "Antall menn"):
            d.pop(c, None)
        out.append(d)
    return out


def collapse_student_categories(rows):
    keyf = lambda r: (r["Institusjonskode"], r["Årstall"], r["Semester"], r["Studieprogramkode"],
                      r.get("Studiumkode", ""), r.get("Nivåkode", ""), r.get("NUS-kode", ""),
                      r.get("Studiepoeng", ""))
    groups = {}
    for r in rows:
        groups.setdefault(keyf(r), []).append(r)
    out = []
    for grp in groups.values():
        base = dict(grp[0])
        base["Antall totalt"] = sum(to_int(g["Antall totalt"]) or 0 for g in grp)
        base["Antall kvinner"] = sum(to_int(g["Antall kvinner"]) or 0 for g in grp)
        base["Antall menn"] = sum(to_int(g["Antall menn"]) or 0 for g in grp)
        base.pop("Studentkategori", None)
        base.pop("Studentkategorinavn", None)
        out.append(base)
    return out


def write_csv(path, rows, columns):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    log(f"wrote {os.path.basename(path)}: {len(rows)} rows")


def main():
    os.makedirs(RAW_DIR, exist_ok=True)

    log("== Graduate totals, all institutions (table 104)")
    tot = post(agg_query(T_GRADUATES, ["Institusjonskode", "Årstall"], [item("Årstall", YEARS)],
                         ["Institusjonskode", "Årstall"]), "104_kandidater_totaler.json")
    latest_tot = {r["Institusjonskode"]: to_int(r["Antall totalt"]) or 0
                  for r in tot if r["Årstall"] == LATEST}
    codes = sorted(c for c, n in latest_tot.items() if n >= MIN_GRADS)
    log(f"  {len(latest_tot)} institutions with graduates in {LATEST}, "
        f"{len(codes)} with >= {MIN_GRADS}")

    log("== Institutions (table 211)")
    inst = post(list_query(T_INSTITUTIONS, [item("Institusjonskode", codes)], ["Institusjonskode"]),
                "211_institusjoner.json")
    inst_rows = [{"institusjonskode": r["Institusjonskode"], "institusjonsnavn": r["Institusjonsnavn"],
                  "kortnavn": r.get("Kortnavn", ""), "institusjonstypekode": r.get("Institusjonstypekode", ""),
                  "institusjonstype": r.get("Typenavn", ""),
                  "kandidater_siste_aar": latest_tot.get(r["Institusjonskode"], "")} for r in inst]
    inst_rows.sort(key=lambda r: -(r["kandidater_siste_aar"] or 0))
    write_csv(os.path.join(OUT_DIR, "institutions.csv"), inst_rows, list(inst_rows[0]))
    names = {r["institusjonskode"]: (r["kortnavn"] or r["institusjonskode"]) for r in inst_rows}

    log("== Level codes (table 436)")
    lv = post(list_query(T_LEVELS, [{"variabel": "Nivåkode", "selection": {"filter": "all", "values": ["*"]}}],
                         ["Orden"]), "436_nivaakoder.json")
    write_csv(os.path.join(OUT_DIR, "nivaakoder.csv"),
              [{"nivaakode": r["Nivåkode"], "nivaanavn": r["Nivånavn"], "hovednivaakode": r["Hovednivåkode"],
                "beskrivelse": r["Beskrivelse"], "orden": r["Orden"]} for r in lv],
              ["nivaakode", "nivaanavn", "hovednivaakode", "beskrivelse", "orden"])

    log("== Graduates per programme (table 104)")
    gb = ["Institusjonskode", "Årstall", "Studieprogramkode", "Studiumkode", "Nivåkode", "NUS-kode", "Studiepoeng"]
    grad = []
    for code in codes:
        grad += post(agg_query(T_GRADUATES, gb, [item("Institusjonskode", [code]), item("Årstall", YEARS)],
                               ["Institusjonskode", "Årstall", "Studieprogramkode"]),
                     f"104_kandidater_{code}.json")
        time.sleep(0.5)
    grad = tidy(grad, "kandidater")
    cols = ["institusjonskode", "institusjonsnavn", "aar", "studieprogramkode", "studieprogramnavn",
            "studiumkode", "studiumnavn", "nivaakode", "nivaanavn", "nus_kode", "studiepoeng",
            "kandidater_totalt", "kandidater_kvinner", "kandidater_menn", "kjonn_skjermet"]
    write_csv(os.path.join(OUT_DIR, "graduates_by_program.csv"), grad, cols)

    log("== PhD (table 101)")
    phd = post(agg_query(T_PHD, ["Institusjonskode", "Årstall", "Studieprogramkode"],
                         [item("Institusjonskode", codes), item("Årstall", YEARS)],
                         ["Institusjonskode", "Årstall", "Studieprogramkode"]), "101_doktorgrader.json")
    phd = tidy(phd, "kandidater")
    for r in phd:
        r.setdefault("nivaakode", "FU")
        r.setdefault("nivaanavn", "Forskerutdanning")
    write_csv(os.path.join(OUT_DIR, "graduates_phd_by_program.csv"), phd,
              ["institusjonskode", "institusjonsnavn", "aar", "studieprogramkode", "studieprogramnavn",
               "nivaakode", "nivaanavn", "kandidater_totalt", "kandidater_kvinner", "kandidater_menn",
               "kjonn_skjermet"])

    log("== Registered students, autumn (table 123)")
    gb_st = ["Institusjonskode", "Årstall", "Semester", "Studentkategori", "Studieprogramkode",
             "Studiumkode", "Nivåkode", "NUS-kode", "Studiepoeng"]
    stud_raw = []
    for code in codes:
        stud_raw += post(agg_query(T_STUDENTS, gb_st,
                                   [item("Institusjonskode", [code]), item("Årstall", YEARS), item("Semester", [AUTUMN])],
                                   ["Institusjonskode", "Årstall", "Studieprogramkode"]),
                         f"123_registrerte_{code}.json")
        time.sleep(0.5)
    stud = tidy(collapse_student_categories(stud_raw), "studenter")
    write_csv(os.path.join(OUT_DIR, "students_by_program.csv"), stud,
              ["institusjonskode", "institusjonsnavn", "aar", "semester", "studieprogramkode",
               "studieprogramnavn", "studiumkode", "studiumnavn", "nivaakode", "nivaanavn", "nus_kode",
               "studiepoeng", "studenter_totalt", "studenter_kvinner", "studenter_menn", "kjonn_skjermet"])
    post(agg_query(T_STUDENTS, ["Institusjonskode", "Årstall"],
                   [item("Institusjonskode", codes), item("Årstall", YEARS), item("Semester", [AUTUMN])]),
         "123_registrerte_totaler.json")

    print(f"{len(codes)} institutions: " + ", ".join(names[c] for c in codes))


if __name__ == "__main__":
    main()
