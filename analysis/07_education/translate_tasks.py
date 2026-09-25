#!/usr/bin/env python3
"""
Translate the O*NET task statements used on kiindeksen.no to Norwegian.

Reads every task text used on the Yrker page (data/ai_exposure/styrk08_aei_tasks.csv)
and the Utdanning page (data/education_analysis/majors.json), keeps the rows that
already exist in data/ai_exposure/onet_task_translations_no.csv, and translates the
rest with the Claude API in batches. Needs ANTHROPIC_API_KEY in the environment.
Uses only `requests`; no SDK. Re-run prepare_panels.py / build_majors.py afterwards.

    ANTHROPIC_API_KEY=... python analysis/07_education/translate_tasks.py [--dry-run]

Cost guide: about 2 300 statements, 33 000 words; a few hundred thousand tokens.
"""
import csv
import json
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "data", "ai_exposure", "onet_task_translations_no.csv")
MODEL = os.environ.get("TRANSLATE_MODEL", "claude-sonnet-5")
BATCH = 40
SYSTEM = ("Du oversetter arbeidsoppgaver fra O*NET (amerikanske yrkesbeskrivelser) til norsk bokmål. "
          "Oversett hver setning presist og kort, i samme form (infinitiv-liste uten subjekt), "
          "med norske fagtermer der de finnes. Behold amerikanske egennavn. Svar med JSON: "
          "en liste av objekter {\"i\": nummer, \"no\": oversettelse}, ingenting annet.")


def norm(s):
    return " ".join((s or "").lower().split())


def load_needed():
    texts = {}
    p = os.path.join(REPO, "data", "ai_exposure", "styrk08_aei_tasks.csv")
    for r in csv.DictReader(open(p, encoding="utf-8")):
        texts.setdefault(norm(r["task_name"]), r["task_name"].strip())
    p = os.path.join(REPO, "data", "education_analysis", "majors.json")
    if os.path.exists(p):
        for g in json.load(open(p, encoding="utf-8"))["groups"]:
            for t in g["tasks"]:
                texts.setdefault(norm(t["text"]), t["text"].strip())
    return texts


def load_done():
    if not os.path.exists(OUT):
        return {}
    return {norm(r["task"]): r for r in csv.DictReader(open(OUT, encoding="utf-8")) if r.get("task_no")}


def save(rows):
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["task", "task_no", "source"])
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])


def translate(batch, key):
    prompt = "\n".join("%d\t%s" % (i, t) for i, t in batch)
    r = requests.post("https://api.anthropic.com/v1/messages",
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                      json={"model": MODEL, "max_tokens": 8000, "system": SYSTEM,
                            "messages": [{"role": "user", "content": prompt}]}, timeout=180)
    r.raise_for_status()
    text = r.json()["content"][0]["text"].strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[1]
    return {int(o["i"]): o["no"].strip() for o in json.loads(text)}


def main():
    dry = "--dry-run" in sys.argv
    needed, done = load_needed(), load_done()
    todo = [(k, t) for k, t in needed.items() if k not in done]
    print(f"{len(needed)} task texts in use, {len(done)} translated, {len(todo)} to do")
    if dry or not todo:
        return
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("Set ANTHROPIC_API_KEY")
    for start in range(0, len(todo), BATCH):
        chunk = todo[start:start + BATCH]
        batch = [(i + 1, t) for i, (_, t) in enumerate(chunk)]
        for attempt in range(3):
            try:
                got = translate(batch, key)
                break
            except Exception as e:  # noqa: BLE001
                print("retry", attempt + 1, e)
                time.sleep(5 * (attempt + 1))
        else:
            raise SystemExit("gave up")
        for i, (k, t) in enumerate(chunk):
            if got.get(i + 1):
                done[k] = {"task": t, "task_no": got[i + 1], "source": MODEL}
        save(done)
        print(f"  {min(start + BATCH, len(todo))}/{len(todo)}")


if __name__ == "__main__":
    main()
