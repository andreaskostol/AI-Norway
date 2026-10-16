#!/usr/bin/env python3
"""Vis tilbakemeldinger sendt til KI-indeksen: knappen «Tilbakemelding» paa nettstedet (feedback.js)
og MCP-verktoeyet send_feedback. Samme oppskrift som scripts/feedback.py paa andreaskostol.no.

    python3 dashboard/mcp/feedback.py          nye meldinger siden sist, og merk dem som lest
    python3 dashboard/mcp/feedback.py --all    alle meldinger
    python3 dashboard/mcp/feedback.py --peek   nye meldinger uten aa merke dem som lest

Meldingene ligger i /data/feedback/feedback.jsonl paa Fly-volumet til appen kiindeksen-mcp. Scriptet
leser fila over `fly ssh` (flyctl maa vaere logget inn som Andreas) og husker id-en til siste viste
melding i .git/feedback-seen-kiindeksen. Ingenting kopieres inn i repoet, som ligger paa GitHub.
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

APP = "kiindeksen-mcp"
STORE = "/data/feedback/feedback.jsonl"
REPO = Path(__file__).resolve().parent.parent.parent


def seen_file() -> Path:
    common = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--git-common-dir"],
                            capture_output=True, text=True, check=True).stdout.strip()
    return (REPO / common).resolve() / "feedback-seen-kiindeksen"


def fetch() -> list:
    # Maskinen stopper naar den er ledig. Et kall vekker den foer ssh kobler til.
    try:
        urllib.request.urlopen("https://kiindeksen-mcp.fly.dev/health", timeout=30).read()
    except Exception:
        pass
    r = None
    for attempt in range(3):
        r = subprocess.run(["fly", "ssh", "console", "-a", APP, "-C", f'sh -c "cat {STORE} 2>/dev/null || true"'],
                           capture_output=True, text=True)
        if r.returncode == 0:
            break
        time.sleep(3)
    if r is None or r.returncode != 0:
        sys.exit(f"fly ssh feilet: {(r.stderr if r else '').strip()}")
    out = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def main() -> None:
    show_all = "--all" in sys.argv
    peek = "--peek" in sys.argv
    msgs = fetch()
    sf = seen_file()
    last = sf.read_text().strip() if sf.exists() else ""
    if not show_all and last:
        ids = [m.get("id") for m in msgs]
        msgs = msgs[ids.index(last) + 1:] if last in ids else msgs
    if not msgs:
        print("Ingen nye meldinger.")
        return
    for m in msgs:
        print(f"--- {m.get('time', '?')}  [{m.get('source', '?')}]  {m.get('page', '')}  {m.get('contact', '')}".rstrip())
        print(m.get("message", ""))
        print()
    print(f"{len(msgs)} melding(er).")
    if not peek and msgs and msgs[-1].get("id"):
        sf.write_text(msgs[-1]["id"])


if __name__ == "__main__":
    main()
