#!/usr/bin/env python3
"""Eksempel: analyser KI-indeksen-dataene gjennom MCP-koblingen, uten andre avhengigheter.

    python3 client_example.py                                  # mot https://kiindeksen-mcp.fly.dev/mcp
    python3 client_example.py --url http://localhost:8765/mcp  # mot en lokal server

Scriptet gjør det en analytiker (eller Claude) ville gjort med verktøyene:
  1. initialize + tools/list: hva finnes?
  2. hovedtallet med usikkerhet, alle og unge, begge referanser
  3. veksten per eksponeringskvintil siden Claude Code (januar 2025 som referanse)
  4. to yrker med samme eksponering og ulik automatisering: kontormedarbeidere (4110) og
     kundebehandlere lån og kreditt (3312), oppgave for oppgave og i sysselsettingen
  5. en utdanning: hva jobbene består av
Alle tall skrives ut slik de kommer fra serveren.
"""
import argparse, json, urllib.request

DEFAULT_URL = "https://kiindeksen-mcp.fly.dev/mcp"


class Client:
    def __init__(self, url):
        self.url, self.n = url, 0

    def rpc(self, method, params=None, notify=False):
        self.n += 1
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            msg["id"] = self.n
        req = urllib.request.Request(self.url, data=json.dumps(msg).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                                              "MCP-Protocol-Version": "2025-06-18"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8")
        if notify or not body:
            return None
        out = json.loads(body)
        if "error" in out:
            raise RuntimeError(f"{method}: {out['error']}")
        return out["result"]

    def call(self, tool, **args):
        res = self.rpc("tools/call", {"name": tool, "arguments": args})
        if res.get("isError"):
            raise RuntimeError(f"{tool}: {res['content'][0]['text']}")
        return res.get("structuredContent") or json.loads(res["content"][0]["text"])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--url", default=DEFAULT_URL); a = ap.parse_args()
    c = Client(a.url)

    init = c.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "client_example", "version": "1.0"}})
    c.rpc("notifications/initialized", notify=True)
    tools = c.rpc("tools/list")["tools"]
    print(f"Server: {init['serverInfo']['title']} {init['serverInfo']['version']}, protokoll {init['protocolVersion']}, {len(tools)} verktøy:")
    print("  " + ", ".join(t["name"] for t in tools))

    # 1. release og hovedtall
    rel = c.call("get_release")
    print(f"\nRelease {rel['release']}: {rel['first_month'][:7]} til {rel['last_month'][:7]}, base {rel['normalisation_month'][:7]}.")
    for young in (False, True):
        for ref in ("chatgpt", "claudecode"):
            h = c.call("get_headline", measure="eloundou", reference=ref, young=young)
            print(f"  KI-indeksen, {h['population']}, referanse {ref}: {h['ki']:+.1f} pp (se {h['se']:.1f}, intervall {h['ci_lo']:.1f} til {h['ci_hi']:.1f})")

    # 2. vekst per kvintil siden Claude Code
    g = c.call("get_growth", package="by_exposure", spec="sa", reference="2025-01", moving_average=3)
    print(f"\nVekst i sysselsetting {g['reference_month'][:7]} til {g['last_month'][:7]}, sa, 3 mnd snitt, privat sektor:")
    for k, v in g["growth_pct"]["_"].items():
        print(f"  {k:28s} {v:+.2f}")
    gy = c.call("get_growth", package="age_by_exposure", spec="sa", reference="2025-01", moving_average=3)["growth_pct"]
    print("  21-30 år: Q1 {:+.2f}, Q5 {:+.2f}".format(gy["Quintile 1 (least exposed)"]["21-30"], gy["Quintile 5 (most exposed)"]["21-30"]))

    # 3. to yrker, samme eksponering, ulik automatisering
    print("\nTo yrker med samme eksponering og ulik automatisering:")
    pair = c.call("compare_occupations", codes=["4110", "3312"], outcome="employment", spec="sa", index_base="2025-02")
    for o in pair["occupations"]:
        auto = o["automation_share_latest"]["claude_ai"]
        print(f"  {o['code']} {o['name']}: Eloundou {o['exposure_eloundou']:.2f} (Q{o['quintile_eloundou']}), Mouchel {o['exposure_mouchel']:.2f} (Q{o['quintile_mouchel']}), "
              f"automatisering {100*auto['automation']:.0f} % ({auto['vintage']}), sysselsetting {o['last_value']} i {o['series']['dates'][-1][:7]} (feb. 2025 = 100)")
    for code in ("4110", "3312"):
        occ = c.call("get_occupation", code=code, platform="claude_ai")
        rows = occ["tasks"]["rows"][:3]                    # serveren sorterer etter bruk
        print(f"  Mest brukte oppgaver, {occ['name']} (pct = prosent av all Claude-bruk):")
        for t in rows:
            print(f"    {(t.get('t_no') or t['t'])[:80]}: {t.get('pct') or 0:.2f} %, automatisering {100*(t.get('auto') or 0):.0f} %")

    # 4. en utdanning
    hits = c.call("search_education", query="økonomi", level="6", limit=3)["groups"]
    if hits:
        gr = c.call("get_education_group", code=hits[0]["code"])
        print(f"\nUtdanning {gr['code']} {gr['name']} ({gr['n_employed']} sysselsatte): eksponering {gr['exposure_v1']:.2f}, "
              f"{100*gr['share_in_top_quintile_v1']:.0f} % i mest eksponerte femdel, automatisering {100*gr['automation']:.0f} %")
        for t in gr["tasks"][:3]:
            print(f"    {t.get('text_no') or t['text'][:70]}")
        print("  Vanligste jobber: " + ", ".join(f"{o['name']} ({100*o['share']:.0f} %)" for o in gr["occupations_all"][:3]))


if __name__ == "__main__":
    main()
