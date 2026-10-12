"""
Teller aktivitet per maaned i offentlige norske GitHub-organisasjoner: commits, pull requests
(alle, uten avhengighetsboter, flettede, og laget av Copilot-agenten) og nye repoer. NAV (navikt)
er egen serie, de andre summeres til gruppen "offentlig". Org-nivaa beholdes i output.

Kilde: GitHub API med token fra `gh auth token`.
- commits for navikt: REST search/commits, org:X committer-date:<maaned>. Standardgren, ikke forks.
- commits for de andre org-ene: GraphQL history(since, until) paa standardgrenen, ett kall per repo
  (ikke forks). Commit-soket ble for tregt paa grunn av GitHubs sekundaere grenser. Der commit-soket
  ble fullfort (Skatteetaten, digdir, felleslosninger), ligger det som commits_search til kontroll.
- PR-er: GraphQL search(type: ISSUE) med 25 sok per kall.
- nye repoer: REST orgs/X/repos, created_at, ikke forks.
Bare offentlige repoer er synlige. Slettede eller private repoer er ikke med.
Hvert sok logges i data/macro_signals/raw/github_orgs/*.jsonl. Sok som er gjort hoppes over,
saa skriptet kan avbrytes og startes igjen.

Kjor: python analysis/09_macro_signals/fetch_github_orgs.py
"""
import calendar
import json
import subprocess
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
RAW = OUT / "raw" / "github_orgs"
RAW.mkdir(parents=True, exist_ok=True)

# org -> (gruppe, etat)
ORGS = {
    "navikt": ("navikt", "NAV"),
    "Skatteetaten": ("offentlig", "Skatteetaten"),
    "digdir": ("offentlig", "Digdir"),
    "felleslosninger": ("offentlig", "Digdir"),
    "entur": ("offentlig", "Entur"),
    "oslokommune": ("offentlig", "Oslo kommune"),
    "vegvesen": ("offentlig", "Statens vegvesen"),
    "nvdb-vegdata": ("offentlig", "Statens vegvesen"),
    "NPRA": ("offentlig", "Statens vegvesen"),
    "svvsaga": ("offentlig", "Statens vegvesen"),
    "nrkno": ("offentlig", "NRK"),
    "kartverket": ("offentlig", "Kartverket"),
    "politiet": ("offentlig", "Politiet"),
}
START = (2016, 1)
END = (2026, 9)  # siste hele maaned
DEPBOTS = " -author:app/dependabot -author:app/renovate -author:app/github-actions -author:app/dependabot-preview"
PR_METRICS = {  # metrikk -> sokestreng, {w} er maanedsvinduet
    "prs": "is:pr created:{w}",
    "prs_nodep": "is:pr created:{w}" + DEPBOTS,
    "prs_merged": "is:pr merged:{w}",
    "prs_merged_nodep": "is:pr merged:{w}" + DEPBOTS,
    "prs_copilot_agent": "is:pr created:{w} author:app/copilot-swe-agent",
}
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
S = requests.Session()
S.headers.update({"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"})


def load(name):
    f = RAW / name
    return {json.loads(l)["q"]: json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()} if f.exists() else {}


def log(name, rec):
    with (RAW / name).open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


REST, GQL = load("search_log.jsonl"), load("graphql_log.jsonl")
NOW = lambda: datetime.now(timezone.utc).isoformat()


def request(method, url, **kw):
    while True:
        r = S.request(method, url, timeout=90, **kw)
        if r.status_code in (403, 429) or r.status_code >= 500:
            wait = int(r.headers.get("Retry-After", 0)) or max(
                int(r.headers.get("X-RateLimit-Reset", time.time())) - int(time.time()), 0) + 5
            wait = min(max(wait, 30), 600)
            print(f"  {r.status_code}, venter {wait}s", flush=True)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r


def commit_search(q):
    if q in REST and not REST[q]["incomplete"]:
        return REST[q]
    best = None
    for _ in range(3):  # incomplete_results skyldes tidsavbrudd hos GitHub, proev igjen
        time.sleep(2.3)
        js = request("GET", "https://api.github.com/search/commits", params={"q": q, "per_page": 1}).json()
        rec = {"endpoint": "commits", "q": q, "total_count": js["total_count"],
               "incomplete": js["incomplete_results"], "fetched": NOW()}
        if best is None or rec["total_count"] > best["total_count"] or not rec["incomplete"]:
            best = rec
        if not rec["incomplete"]:
            break
    log("search_log.jsonl", best)
    REST[q] = best
    return best


def commits(org, y, m):
    last = calendar.monthrange(y, m)[1]
    rec = commit_search(f"org:{org} committer-date:{y}-{m:02d}-01..{y}-{m:02d}-{last:02d}")
    if not rec["incomplete"]:
        return rec["total_count"], False
    parts = [(1, 7), (8, 14), (15, 21), (22, last)]  # del maaneden hvis soket ikke ble komplett
    recs = [commit_search(f"org:{org} committer-date:{y}-{m:02d}-{a:02d}..{y}-{m:02d}-{b:02d}") for a, b in parts]
    return sum(r["total_count"] for r in recs), any(r["incomplete"] for r in recs)


def history_counts(org, repo_rows, wins):
    """Commits per maaned paa standardgrenen i hvert repo (ikke forks), via GraphQL history. Bufres per repo."""
    f = RAW / f"history_{org}.jsonl"
    cache = {json.loads(l)["repo"]: json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()} if f.exists() else {}
    for r in repo_rows:
        if r["fork"] or r["full_name"] in cache:
            continue
        owner, name = r["full_name"].split("/")
        fields = " ".join(f'm{y}_{m:02d}: history(since: "{w[:10]}T00:00:00Z", until: "{w[12:]}T23:59:59Z") {{ totalCount }}'
                          for (y, m), w in wins.items())
        q = f'query {{ repository(owner: "{owner}", name: "{name}") {{ defaultBranchRef {{ target {{ ... on Commit {{ {fields} }} }} }} }} }}'
        time.sleep(0.5)
        js = request("POST", "https://api.github.com/graphql", json={"query": q}).json()
        ref = ((js.get("data") or {}).get("repository") or {}).get("defaultBranchRef") or {}
        rec = {"repo": r["full_name"], "fetched": NOW(),
               "counts": {f"{k[1:5]}-{k[6:8]}": v["totalCount"] for k, v in (ref.get("target") or {}).items()}}
        log(f"history_{org}.jsonl", rec)
        cache[r["full_name"]] = rec
    out = {}
    for rec in cache.values():
        for per, n in rec["counts"].items():
            out[per] = out.get(per, 0) + n
    return out


def graphql_counts(queries):
    todo = [q for q in queries if q not in GQL]
    for i in range(0, len(todo), 25):
        chunk = todo[i:i + 25]
        body = " ".join(f'a{j}: search(query: {json.dumps(q)}, type: ISSUE, first: 0) {{ issueCount }}'
                        for j, q in enumerate(chunk))
        time.sleep(2)
        js = request("POST", "https://api.github.com/graphql", json={"query": "query { " + body + " }"}).json()
        for j, q in enumerate(chunk):
            rec = {"q": q, "issueCount": js["data"][f"a{j}"]["issueCount"], "fetched": NOW()}
            log("graphql_log.jsonl", rec)
            GQL[q] = rec
    return {q: GQL[q]["issueCount"] for q in queries}


def repos(org):
    rows, page = [], 1
    while True:
        js = request("GET", f"https://api.github.com/orgs/{org}/repos",
                     params={"per_page": 100, "page": page, "type": "public"}).json()
        rows += [{k: r[k] for k in ("full_name", "created_at", "pushed_at", "fork", "archived", "language")} for r in js]
        if len(js) < 100:
            return rows
        page += 1


def months(first):
    y, m = first
    while (y, m) <= END:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


rows = []
for org, (group, etat) in ORGS.items():
    created = datetime.fromisoformat(request("GET", f"https://api.github.com/orgs/{org}").json()["created_at"][:10])
    first = max(START, (created.year, created.month))
    repo_rows = repos(org)
    (RAW / f"repos_{org}.json").write_text(json.dumps(repo_rows, indent=1), encoding="utf-8")
    new = pd.Series([r["created_at"][:7] for r in repo_rows if not r["fork"]], dtype=str).value_counts()
    wins = {(y, m): f"{y}-{m:02d}-01..{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}" for y, m in months(first)}
    prq = {(ym, k): f"org:{org} " + v.format(w=w) for ym, w in wins.items() for k, v in PR_METRICS.items()}
    pr = graphql_counts(list(prq.values()))
    print(org, "fra", first, f"{len(repo_rows)} repoer, PR-er hentet", flush=True)
    hist = history_counts(org, repo_rows, wins) if group != "navikt" else None
    for (y, m) in wins:
        period = f"{y}-{m:02d}"
        if hist is None:
            n_c, inc = commits(org, y, m)
            vals = [("commits", n_c)]
        else:
            n_c, inc = hist.get(period, 0), False
            q = f"org:{org} committer-date:{wins[(y, m)]}"
            vals = [("commits", n_c)] + ([("commits_search", REST[q]["total_count"])] if q in REST else [])
        vals += [("new_repos", int(new.get(period, 0)))] + [(k, pr[prq[((y, m), k)]]) for k in PR_METRICS]
        rows += [{"org": org, "group": group, "agency": etat, "metric": k, "period": period, "value": v,
                  "incomplete": inc and k == "commits"} for k, v in vals]
    print(f"  ferdig {org}", flush=True)

df = pd.DataFrame(rows)
df.to_csv(OUT / "github_orgs.csv", index=False)
meta = {"source": "GitHub REST og GraphQL API", "url": "https://api.github.com", "fetched": date.today().isoformat(),
        "orgs": {o: {"group": g, "agency": e} for o, (g, e) in ORGS.items()},
        "filter": {"commits": "navikt: REST search/commits org:X committer-date:<maaned>. Andre: GraphQL history paa standardgrenen per repo, summert. Ikke forks",
                   "commits_search": "REST search/commits der soket ble fullfort, til kontroll",
                   **{k: "GraphQL search org:X " + v.replace("{w}", "<maaned>") for k, v in PR_METRICS.items()},
                   "new_repos": "REST orgs/X/repos type=public, created_at, ikke forks"},
        "note": "Bare offentlige repoer. Repoer som er slettet eller gjort private er ikke med. "
                "incomplete=True betyr at GitHub-soket ikke ble komplett, verdien er da en nedre grense."}
(OUT / "_meta_github_orgs.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print("skrev", OUT / "github_orgs.csv", len(df))
