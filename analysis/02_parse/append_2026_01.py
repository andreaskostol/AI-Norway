"""
Append January 2026 data from microdata-output/08_alle_2026_01.csv to all parsed
data files.

The raw file contains 15 tabulate blocks from a single combined microdata.no
script:

  Job-level (yrke4 x alder_gr):
    1. count           -> data/01_occ_agemonth_count_2021_2026.csv
    2. mean kontantlonn -> data/02_occ_agem_wage_2021_2026.csv (variable=kontantlonn)
    3. mean stillingspst -> data/02_occ_agem_wage_2021_2026.csv (variable=stillingspst)
    4. mean timelonn    -> data/02_occ_agem_wage_2021_2026.csv (variable=timelonn)
    5. count if sekt==1 -> data/04_occ_agem_sector_count_2021_2026.csv (sekt=1)
    6. count if sekt==2 -> data/04_occ_agem_sector_count_2021_2026.csv (sekt=2)
    7. count if sekt==3 -> data/04_occ_agem_sector_count_2021_2026.csv (sekt=3)
    8. mean overtid_timer -> data/06_occ_agem_overtid_nyjobb_2021_2026.csv
    9. mean ny_jobb       -> data/06_occ_agem_overtid_nyjobb_2021_2026.csv
   10. std kontantlonn    -> data/02_occ_agem_wagesd_2021_2026.csv

  Person-level:
   11. sysselsatt x alder -> microdata-output/03_syss_alder_2020_2026_parsed.csv
   12. alder_gr x utd_gr (pop)  -> microdata-output/04_utd_alder_2020_2026_parsed.csv
   13. alder_gr x nus3   (pop)  -> microdata-output/05_utd3_alder_combined_parsed.csv (new)
   14. alder_gr x utd_gr (syss) -> microdata-output/04_utd_alder_2020_2026_parsed.csv
   15. alder_gr x nus3   (syss) -> microdata-output/05_utd3_alder_combined_parsed.csv

Idempotent: existing 2026-01-16 rows are removed before appending.

Usage:
    python analysis/02_parse/append_2026_01.py
"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "microdata-output" / "08_alle_2026_01.csv"

DATE_JOB = "2026-01-16"
DATE_PERS = "2026-01-16"

TARGETS = {
    "count":      ROOT / "data" / "01_occ_agemonth_count_2021_2026.csv",
    "wage":       ROOT / "data" / "02_occ_agem_wage_2021_2026.csv",
    "wagesd":     ROOT / "data" / "02_occ_agem_wagesd_2021_2026.csv",
    "sector":     ROOT / "data" / "04_occ_agem_sector_count_2021_2026.csv",
    "overtid":    ROOT / "data" / "06_occ_agem_overtid_nyjobb_2021_2026.csv",
    "syss_alder": ROOT / "microdata-output" / "03_syss_alder_2020_2026_parsed.csv",
    "utd_alder":  ROOT / "microdata-output" / "04_utd_alder_2020_2026_parsed.csv",
    "utd3_alder": ROOT / "microdata-output" / "05_utd3_alder_combined_parsed.csv",
}


def split_blocks(text):
    """Split file into (tab_command, header_cells, data_rows) tuples.

    Returns list of dicts with keys: cmd (full tabulate line), header (list),
    rows (list of cell lists).
    """
    lines = text.split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("tabulate"):
            cmd = line
            # Skip blank lines until header
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines):
                break
            header = [c.strip() for c in lines[j].split(";")]
            # Read data rows until empty line or non-data line
            rows = []
            k = j + 1
            while k < len(lines):
                ln = lines[k].strip()
                if not ln:
                    k += 1
                    continue
                # Stop on next tabulate or any command word
                if ln.startswith(("tabulate", "delete", "create", "use", "import",
                                  "keep", "generate", "replace", "destring",
                                  "merge", "summarize", "require")):
                    break
                cells = [c.strip() for c in ln.split(";")]
                rows.append(cells)
                k += 1
            blocks.append({"cmd": cmd, "header": header, "rows": rows})
            i = k
        else:
            i += 1
    return blocks


def parse_value(s):
    s = s.replace(" ", "").replace("\xa0", "")
    if s == "-" or s == "":
        return None
    return s  # keep as string; downstream code casts as needed


def emit_yrke_alder_long(block, fixed_cols):
    """Emit rows from a yrke4 x alder_gr block.

    Header: yrke4; 0; 1; ...; 9; Total
    fixed_cols is a dict of extra columns to add to each row (e.g. variable name).
    Yields dicts with date, yrke4, alder_gr, [extras], plus 'value' or 'count'.
    """
    header = block["header"]
    age_cols = [(i, h) for i, h in enumerate(header)
                if i > 0 and h != "Total" and h.isdigit()]
    for r in block["rows"]:
        if not r or r[0].lower() == "total":
            continue
        yrke = r[0]
        for i, ag in age_cols:
            if i >= len(r):
                continue
            v = parse_value(r[i])
            if v is None:
                continue
            yield {"yrke4": yrke, "alder_gr": ag, **fixed_cols, "value": v}


def emit_aldergr_x_long(block, x_name):
    """Emit rows from alder_gr x [utd_gr|nus3] block.

    Header: alder_gr; <code1>; <code2>; ...; Total
    Yields: alder_gr, x_name, code, count
    """
    header = block["header"]
    code_cols = [(i, h) for i, h in enumerate(header) if i > 0 and h != "Total"]
    for r in block["rows"]:
        if not r or r[0].lower() == "total":
            continue
        ag = r[0]
        for i, code in code_cols:
            if i >= len(r):
                continue
            v = parse_value(r[i])
            if v is None:
                continue
            yield {"alder_gr": ag, x_name: code, "n": v}


def emit_sysselsatt_alder(block):
    """tabulate sysselsatt alder, flatten

    Header: sysselsatt; 1; 2; ...; Total
    """
    header = block["header"]
    age_cols = [(i, h) for i, h in enumerate(header) if i > 0 and h != "Total"]
    for r in block["rows"]:
        if not r or r[0].lower() == "total":
            continue
        syss = r[0]
        for i, age in age_cols:
            if i >= len(r):
                continue
            v = parse_value(r[i])
            if v is None:
                continue
            yield {"alder": age, "sysselsatt": syss, "n": v}


def remove_existing_date(path, date_value, date_col="date"):
    """Read CSV, drop rows with date_col == date_value, return rows + fieldnames."""
    if not path.exists():
        return [], None
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = [r for r in reader if r.get(date_col) != date_value]
    return rows, fieldnames


def append_to_csv(path, new_rows, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(new_rows)


def classify_block(cmd):
    """Map a tabulate command line to a (target, extras) tuple."""
    if "sysselsatt alder" in cmd:
        return ("syss_alder", None)
    if "alder_gr utd_gr" in cmd:
        return ("utd_alder", None)
    if "alder_gr nus3" in cmd:
        return ("utd3_alder", None)
    if "yrke4 alder_gr" not in cmd:
        return (None, None)
    if "summarize(kontantlonn) std" in cmd:
        return ("wagesd", {"variable": "kontantlonn_sd"})
    if "summarize(kontantlonn)" in cmd:
        return ("wage", {"variable": "kontantlonn"})
    if "summarize(stillingspst)" in cmd:
        return ("wage", {"variable": "stillingspst"})
    if "summarize(timelonn)" in cmd:
        return ("wage", {"variable": "timelonn"})
    if "summarize(overtid_timer)" in cmd:
        return ("overtid", {"variable": "overtid_timer"})
    if "summarize(ny_jobb)" in cmd:
        return ("overtid", {"variable": "ny_jobb"})
    m = re.search(r"if\s+sekt\s*==\s*(\d+)", cmd)
    if m:
        return ("sector", {"sekt": m.group(1), "variable": "count"})
    return ("count", None)


def main():
    text = SRC.read_text(encoding="utf-8")
    blocks = split_blocks(text)
    print(f"Found {len(blocks)} tabulate blocks")
    for b in blocks:
        cmd_short = b["cmd"][:80]
        print(f"  {len(b['rows']):>4} rows  |  {cmd_short}")

    # Aggregate new rows per target
    new_rows = {key: [] for key in TARGETS}
    # utd_alder is special: needs to merge pop + syss columns (two blocks)
    utd_pop, utd_syss = [], []
    utd3_pop, utd3_syss = [], []

    seen_utd_alder = 0
    seen_utd3 = 0

    for b in blocks:
        target, extras = classify_block(b["cmd"])
        if target is None:
            continue

        if target == "count":
            for row in emit_yrke_alder_long(b, {}):
                new_rows["count"].append({
                    "date": DATE_JOB,
                    "yrke4": row["yrke4"],
                    "alder_gr": row["alder_gr"],
                    "count": row["value"],
                })
        elif target == "wage":
            for row in emit_yrke_alder_long(b, extras):
                new_rows["wage"].append({
                    "date": DATE_JOB,
                    "yrke4": row["yrke4"],
                    "alder_gr": row["alder_gr"],
                    "variable": row["variable"],
                    "value": row["value"],
                })
        elif target == "wagesd":
            for row in emit_yrke_alder_long(b, extras):
                new_rows["wagesd"].append({
                    "date": DATE_JOB,
                    "yrke4": row["yrke4"],
                    "alder_gr": row["alder_gr"],
                    "variable": row["variable"],
                    "value": row["value"],
                })
        elif target == "sector":
            for row in emit_yrke_alder_long(b, extras):
                new_rows["sector"].append({
                    "date": DATE_JOB,
                    "yrke4": row["yrke4"],
                    "alder_gr": row["alder_gr"],
                    "sekt": row["sekt"],
                    "variable": row["variable"],
                    "value": row["value"],
                })
        elif target == "overtid":
            for row in emit_yrke_alder_long(b, extras):
                new_rows["overtid"].append({
                    "date": DATE_JOB,
                    "yrke4": row["yrke4"],
                    "alder_gr": row["alder_gr"],
                    "variable": row["variable"],
                    "value": row["value"],
                })
        elif target == "syss_alder":
            for row in emit_sysselsatt_alder(b):
                new_rows["syss_alder"].append({
                    "date": DATE_PERS,
                    "alder": row["alder"],
                    "sysselsatt": row["sysselsatt"],
                    "n": row["n"],
                })
        elif target == "utd_alder":
            seen_utd_alder += 1
            store = utd_pop if seen_utd_alder == 1 else utd_syss
            for row in emit_aldergr_x_long(b, "utd_gr"):
                store.append(row)
        elif target == "utd3_alder":
            seen_utd3 += 1
            store = utd3_pop if seen_utd3 == 1 else utd3_syss
            for row in emit_aldergr_x_long(b, "nus3"):
                store.append(row)

    # Merge utd_alder pop + syss into rows {date, alder_gr, utd_gr, pop, syss}
    pop_lookup = {(r["alder_gr"], r["utd_gr"]): r["n"] for r in utd_pop}
    syss_lookup = {(r["alder_gr"], r["utd_gr"]): r["n"] for r in utd_syss}
    keys = set(pop_lookup) | set(syss_lookup)
    for ag, ug in sorted(keys, key=lambda x: (int(x[0]), int(x[1]))):
        new_rows["utd_alder"].append({
            "date": DATE_PERS,
            "alder_gr": ag,
            "utd_gr": ug,
            "pop": pop_lookup.get((ag, ug), ""),
            "syss": syss_lookup.get((ag, ug), ""),
        })

    # Same for utd3_alder
    pop3 = {(r["alder_gr"], r["nus3"]): r["n"] for r in utd3_pop}
    syss3 = {(r["alder_gr"], r["nus3"]): r["n"] for r in utd3_syss}
    keys3 = set(pop3) | set(syss3)
    for ag, n3 in sorted(keys3, key=lambda x: (int(x[0]), int(x[1]))):
        new_rows["utd3_alder"].append({
            "date": DATE_PERS,
            "alder_gr": ag,
            "nus3": n3,
            "pop": pop3.get((ag, n3), ""),
            "syss": syss3.get((ag, n3), ""),
        })

    # Write each file: drop existing 2026-01-16 rows, append new ones
    for key, path in TARGETS.items():
        date_val = DATE_JOB if key not in ("syss_alder", "utd_alder", "utd3_alder") \
            else DATE_PERS
        existing, fieldnames = remove_existing_date(path, date_val)
        if fieldnames is None:
            # New file: derive fieldnames from new rows
            if not new_rows[key]:
                continue
            fieldnames = list(new_rows[key][0].keys())
        combined = existing + new_rows[key]
        append_to_csv(path, combined, fieldnames)
        added = len(new_rows[key])
        print(f"  {path.name}: +{added} rows for {date_val}")


if __name__ == "__main__":
    main()
