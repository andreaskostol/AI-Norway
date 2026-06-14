"""
Build three macro CSV files:
1. norges_bank_policy_rate.csv - from Norges Bank policy rate changes
2. ssb_aku_unemployment.csv - from SSB table 13760 API (json-stat2)
3. ssb_registered_unemployment.csv - from NAV seasonally adjusted CSV

Run: python build_macro_csvs.py
"""

import csv
import json
import os
from datetime import datetime, date
from pathlib import Path

OUTDIR = Path(__file__).parent


# ── 1. Norges Bank policy rate ──────────────────────────────────────
# Data from: https://www.norges-bank.no/en/topics/Monetary-policy/Policy-rate/
# These are the decision dates and the new rate level.
# We convert to monthly by taking the rate in effect at end of month.

rate_changes = [
    # (date_str, rate)
    ("2020-05-07", 0.00),
    ("2021-01-21", 0.00),
    ("2021-03-18", 0.00),
    ("2021-05-06", 0.00),
    ("2021-06-17", 0.00),
    ("2021-08-19", 0.00),
    ("2021-09-23", 0.25),
    ("2021-11-04", 0.25),
    ("2021-12-16", 0.50),
    ("2022-01-20", 0.50),
    ("2022-03-24", 0.75),
    ("2022-05-05", 0.75),
    ("2022-06-23", 1.25),
    ("2022-08-18", 1.75),
    ("2022-09-22", 2.25),
    ("2022-11-03", 2.50),
    ("2022-12-15", 2.75),
    ("2023-01-19", 2.75),
    ("2023-03-23", 3.00),
    ("2023-05-04", 3.25),
    ("2023-06-22", 3.75),
    ("2023-08-17", 4.00),
    ("2023-09-21", 4.25),
    ("2023-11-02", 4.25),
    ("2023-12-14", 4.50),
    ("2024-01-25", 4.50),
    ("2024-03-21", 4.50),
    ("2024-05-03", 4.50),
    ("2024-06-20", 4.50),
    ("2024-08-15", 4.50),
    ("2024-09-19", 4.50),
    ("2024-11-07", 4.50),
    ("2024-12-19", 4.50),
    ("2025-01-23", 4.50),
    ("2025-03-27", 4.50),
    ("2025-05-08", 4.50),
    ("2025-06-19", 4.25),
    ("2025-08-14", 4.25),
    ("2025-09-18", 4.00),
    ("2025-11-06", 4.00),
    ("2025-12-18", 4.00),
]

# Parse changes into (date, rate) sorted
changes = sorted([(datetime.strptime(d, "%Y-%m-%d").date(), r) for d, r in rate_changes])

# For each month end from 2021-01 to 2025-12, find the rate in effect
policy_rows = []
for year in range(2021, 2026):
    for month in range(1, 13):
        # End of month date
        if month == 12:
            eom = date(year, 12, 31)
        else:
            eom = date(year, month + 1, 1)
            from datetime import timedelta
            eom = eom - timedelta(days=1)

        # Find rate in effect at end of month
        current_rate = None
        for change_date, rate in changes:
            if change_date <= eom:
                current_rate = rate
            else:
                break

        policy_rows.append((f"{year}-{month:02d}", current_rate))

outfile = OUTDIR / "norges_bank_policy_rate.csv"
with open(outfile, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in policy_rows:
        w.writerow([d, v])
print(f"Wrote {len(policy_rows)} rows to {outfile.name}")


# ── 2. SSB AKU unemployment (table 13760) ──────────────────────────
# Data fetched from SSB API: json-stat2 format
# Seasonally adjusted, both genders, 15-74 years
# Unemployment rate as % of labour force

aku_time_labels = [
    "2021M01","2021M02","2021M03","2021M04","2021M05","2021M06",
    "2021M07","2021M08","2021M09","2021M10","2021M11","2021M12",
    "2022M01","2022M02","2022M03","2022M04","2022M05","2022M06",
    "2022M07","2022M08","2022M09","2022M10","2022M11","2022M12",
    "2023M01","2023M02","2023M03","2023M04","2023M05","2023M06",
    "2023M07","2023M08","2023M09","2023M10","2023M11","2023M12",
    "2024M01","2024M02","2024M03","2024M04","2024M05","2024M06",
    "2024M07","2024M08","2024M09","2024M10","2024M11","2024M12",
    "2025M01","2025M02","2025M03","2025M04","2025M05","2025M06",
    "2025M07","2025M08","2025M09","2025M10","2025M11","2025M12",
]

aku_values = [
    5.1,5.4,4.3,5.1,5.5,4.5,5.0,4.0,3.7,3.6,4.0,3.3,
    3.2,3.5,3.0,2.6,3.8,3.1,2.9,3.4,3.4,3.1,3.3,3.5,
    3.6,3.9,3.6,3.4,3.1,3.4,3.7,3.6,3.5,3.7,3.9,3.7,
    4.5,3.6,3.9,4.3,4.0,4.0,3.9,4.0,4.0,4.1,3.8,4.3,
    3.8,4.1,4.5,4.4,4.6,5.4,4.4,4.9,4.7,4.4,4.6,4.3,
]

outfile = OUTDIR / "ssb_aku_unemployment.csv"
with open(outfile, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for t, v in zip(aku_time_labels, aku_values):
        # Convert 2021M01 -> 2021-01
        d = t.replace("M", "-")
        w.writerow([d, v])
print(f"Wrote {len(aku_values)} rows to {outfile.name}")


# ── 3. Registered unemployment (NAV seasonally adjusted) ───────────
# Source: NAV "Sesongjusterte tall landet" CSV
# Column: Helt_ledige_sesjust (seasonally adjusted fully unemployed count)
# We extract 2021-01 through 2025-12

nav_csv = OUTDIR / "nav_sesongjusterte_landet.csv"
reg_rows = []

with open(nav_csv, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f, delimiter=";")
    for row in reader:
        ym = row["Aar_maaned"]  # e.g. "202101"
        year = int(ym[:4])
        month = int(ym[4:6])
        if 2021 <= year <= 2025:
            val = row["Helt_ledige_sesjust"].strip()
            if val:
                reg_rows.append((f"{year}-{month:02d}", int(val)))

outfile = OUTDIR / "ssb_registered_unemployment.csv"
with open(outfile, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in reg_rows:
        w.writerow([d, v])
print(f"Wrote {len(reg_rows)} rows to {outfile.name}")

print("\nDone. All three macro CSVs created.")
