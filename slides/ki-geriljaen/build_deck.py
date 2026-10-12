"""
build_deck.py

Setter sammen dekket til én selvstendig HTML-fil:
  deck.html  (kilden, med plassholdere)  ->  dist/ki-geriljaen_2026-10-06.html

Plassholdere i deck.html:
  {{svg:navn}}   limer inn figures/navn.svg (uten XML-hode)
  {{img:fil}}    limer inn img/fil som data-URI
  {{n:nøkkel}}   tall fra figures/numbers.json, norsk format
                 nøkkel = gruppe.felt, f.eks. eloundou_chatgpt.ki
                 suffiks |pp gir fortegn, |abs gir absoluttverdi, |0 gir null desimaler

Kjøring:  python3 build_deck.py
"""

import base64
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
NUM = json.load(open(os.path.join(HERE, "figures", "numbers.json"), encoding="utf-8"))
OUT_DIR = os.path.join(HERE, "dist")
os.makedirs(OUT_DIR, exist_ok=True)


def svg(name):
    s = open(os.path.join(HERE, "figures", name + ".svg"), encoding="utf-8").read()
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = re.sub(r"<!DOCTYPE[^>]*>", "", s)
    # Unike id-er per figur, så clipPath-ene ikke kolliderer når flere SVG-er står i samme dokument.
    s = s.replace('id="', f'id="{name}-').replace('url(#', f'url(#{name}-').replace('xlink:href="#', f'xlink:href="#{name}-')
    return s.strip()


def img(fname):
    ext = fname.rsplit(".", 1)[1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}[ext]
    data = base64.b64encode(open(os.path.join(HERE, "img", fname), "rb").read()).decode("ascii")
    return f"data:{mime};base64,{data}"


def fmt(key):
    key, _, flag = key.partition("|")
    grp, _, fld = key.partition(".")
    v = NUM[grp][fld] if fld else NUM[grp]
    if isinstance(v, str):
        return v
    d = 0 if flag == "0" or float(v).is_integer() and abs(v) >= 50 else 1
    if flag == "abs":
        v = abs(v)
    s = f"{v:.{d}f}".replace(".", ",").replace("-", "−")
    if flag == "pp" and v > 0:
        s = "+" + s
    return s


src = open(os.path.join(HERE, "deck.html"), encoding="utf-8").read()
src = re.sub(r"\{\{svg:([\w-]+)\}\}", lambda m: svg(m.group(1)), src)
src = re.sub(r"\{\{img:([\w.-]+)\}\}", lambda m: img(m.group(1)), src)
src = re.sub(r"\{\{n:([\w.|-]+)\}\}", lambda m: fmt(m.group(1)), src)
out = os.path.join(OUT_DIR, "ki-geriljaen_2026-10-06.html")
open(out, "w", encoding="utf-8").write(src)
print(out, round(os.path.getsize(out) / 1e6, 2), "MB")
