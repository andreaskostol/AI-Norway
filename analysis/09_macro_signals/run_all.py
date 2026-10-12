"""
Bygger alle serier fra data/macro_signals/ og kjorer trend_break.test paa hver.
Skriver figurer og analysis/output/macro_signals/summary.csv (en rad per serie og brudd)
og series/<navn>.csv med kolonnene period og value.

Standard start er 2016 (forste maaned eller kvartal). NAV-seriene starter 2020-01. Commits i navikt
steg fra 7 834 i 2016 til 111 159 i 2019, og PR-er var null i 2016. Den tidlige veksten ser ut som
oppbygging av organisasjonen paa GitHub, ikke som en trend. De andre offentlige org-ene starter 2017-01,
fordi PR-er var null i de forste maanedene av 2016 og entur og oslokommune kom til i 2016. Innsynskrav starter 2018-02.
Serier med manglende datafil hoppes over med en melding.

Kjor: python analysis/09_macro_signals/run_all.py
"""
from pathlib import Path

import pandas as pd

import trend_break as tb

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "macro_signals"
OUT = ROOT / "analysis" / "output" / "macro_signals"
(OUT / "series").mkdir(parents=True, exist_ok=True)
SRC = {"ig": "GitHub Innovation Graph (CC0)", "gh": "GitHub API, offentlige repoer", "norid": "Norid",
       "ssb": "SSB tabell 08076", "ssb_ip": "SSB tabell 10990-10992 (Patentstyret)", "brreg": "Brønnøysundregistrene, Enhetsregisteret",
       "oa": "OpenAlex", "ct": "ClinicalTrials.gov", "wiki": "Wikimedia REST API",
       "einnsyn": "eInnsyn (api.einnsyn.no/statistics)",
       "nb": "Nasjonalbiblioteket, katalog-API", "fr": "Forskningsrådet, åpne data (søknader)",
       "hor": "regjeringen.no, høringer"}


def ig(metric, iso="NO", diff=False):
    d = pd.read_csv(DATA / "github_innovation_graph.csv")
    s = d[(d.metric == metric) & (d.iso2_code == iso)].set_index("period")["value"].sort_index()
    return (s.diff().dropna() if diff else s).rename("value").reset_index()


def gh(metric, group):
    d = pd.read_csv(DATA / "github_orgs.csv")
    return d[(d.metric == metric) & (d.group == group)].groupby("period", as_index=False)["value"].sum()


def simple(file, **flt):
    d = pd.read_csv(DATA / file)
    for k, v in flt.items():
        d = d[d[k] == v]
    return d[["period", "value"]]


def openalex(metric, group):
    """Verk per maaned uten verk datert 1. januar, som ofte bare har aarstall."""
    d = pd.read_csv(DATA / "openalex_norway.csv")
    s = d[(d.metric == metric) & (d.group == group)].set_index("period")["value"]
    j = d[(d.metric == metric + "_jan1") & (d.group == group)]
    s = s.sub(j.set_index("period")["value"], fill_value=0)
    return s.rename("value").reset_index()


def openalex_nodata():
    """Alle verk minus datasett. Datasett kommer i store puljer (2 801 i september 2026)."""
    w, d = openalex("works", "all").set_index("period")["value"], openalex("works_type", "dataset").set_index("period")["value"]
    return w.sub(d, fill_value=0).rename("value").reset_index()


def fr(group, dim="all"):
    """Søknader per år. 2026 er utelatt, fordi søknader i det nye systemet Tibi ikke er med."""
    d = pd.read_csv(DATA / "forskningsradet_soknader.csv", dtype={"period": str})
    d = d[(d.metric == "applications") & (d.dim == dim) & (d.group == group) & (d.period < "2026")]
    return d[["period", "value"]]


def hor(stat):
    """Høringer med frist som er passert, gruppert på kvartalet for høringsfristen."""
    d = pd.read_csv(DATA / "horinger.csv", parse_dates=["date", "deadline"]).dropna(subset=["deadline", "n_svar"])
    d = d[d.deadline < pd.Timestamp.today().to_period("Q").start_time]  # bare hele kvartaler
    d["period"] = d.deadline.dt.to_period("Q").astype(str)
    return d.groupby("period")["n_svar"].agg(stat).rename("value").reset_index()


def ssb_ip(file):
    d = pd.read_csv(DATA / f"ssb_{file}.csv")
    return d[d.ContentsCode_code == d.ContentsCode_code.iloc[0]][["period", "value"]].astype({"period": str})


def ssb(nace):
    d = pd.read_csv(DATA / "ssb_08076_nye_foretak.csv", dtype={"NACE2007_code": str, "OrgFormer_code": str})
    return d[(d.NACE2007_code == nace) & (d.OrgFormer_code == "99")][["period", "value"]]


# (navn, tittel, kilde, enhet, funksjon, start)
SERIES = [
    ("ig_us_git_pushes", "USA: git pushes per kvartal (testserie)", "ig", "per kvartal", lambda: ig("git_pushes", "US"), None),
    ("ig_no_git_pushes", "Norge: git pushes per kvartal", "ig", "per kvartal", lambda: ig("git_pushes"), None),
    ("ig_no_new_repos", "Norge: nye repoer per kvartal (endring i bestand)", "ig", "per kvartal", lambda: ig("repositories", diff=True), None),
    ("ig_no_new_developers", "Norge: nye utviklerkontoer per kvartal (endring i bestand)", "ig", "per kvartal", lambda: ig("developers", diff=True), None),
    ("ig_no_new_orgs", "Norge: nye organisasjoner per kvartal (endring i bestand)", "ig", "per kvartal", lambda: ig("organizations", diff=True), None),
    ("ig_se_git_pushes", "Sverige: git pushes per kvartal", "ig", "per kvartal", lambda: ig("git_pushes", "SE"), None),
    ("ig_dk_git_pushes", "Danmark: git pushes per kvartal", "ig", "per kvartal", lambda: ig("git_pushes", "DK"), None),
    ("ig_fi_git_pushes", "Finland: git pushes per kvartal", "ig", "per kvartal", lambda: ig("git_pushes", "FI"), None),
    ("ig_us_new_developers", "USA: nye utviklerkontoer per kvartal (endring i bestand)", "ig", "per kvartal", lambda: ig("developers", "US", diff=True), None),
    ("ig_se_new_developers", "Sverige: nye utviklerkontoer per kvartal (endring i bestand)", "ig", "per kvartal", lambda: ig("developers", "SE", diff=True), None),
    ("ig_dk_new_developers", "Danmark: nye utviklerkontoer per kvartal (endring i bestand)", "ig", "per kvartal", lambda: ig("developers", "DK", diff=True), None),
    ("ig_fi_new_developers", "Finland: nye utviklerkontoer per kvartal (endring i bestand)", "ig", "per kvartal", lambda: ig("developers", "FI", diff=True), None),
    ("gh_nav_commits", "NAV (navikt): commits per måned", "gh", "per måned", lambda: gh("commits", "navikt"), "2020-01"),
    ("gh_nav_prs", "NAV (navikt): pull requests per måned, alle", "gh", "per måned", lambda: gh("prs", "navikt"), "2020-01"),
    ("gh_nav_prs_nodep", "NAV (navikt): pull requests uten avhengighetsboter", "gh", "per måned", lambda: gh("prs_nodep", "navikt"), "2020-01"),
    ("gh_nav_prs_merged_nodep", "NAV (navikt): flettede pull requests uten avhengighetsboter", "gh", "per måned", lambda: gh("prs_merged_nodep", "navikt"), "2020-01"),
    ("gh_nav_new_repos", "NAV (navikt): nye offentlige repoer per måned", "gh", "per måned", lambda: gh("new_repos", "navikt"), "2020-01"),
    ("gh_pub_commits", "Andre offentlige org-er: commits per måned", "gh", "per måned", lambda: gh("commits", "offentlig"), "2017-01"),
    ("gh_pub_prs", "Andre offentlige org-er: pull requests per måned, alle", "gh", "per måned", lambda: gh("prs", "offentlig"), "2017-01"),
    ("gh_pub_prs_nodep", "Andre offentlige org-er: pull requests uten avhengighetsboter", "gh", "per måned", lambda: gh("prs_nodep", "offentlig"), "2017-01"),
    ("gh_pub_prs_merged_nodep", "Andre offentlige org-er: flettede pull requests uten avhengighetsboter", "gh", "per måned", lambda: gh("prs_merged_nodep", "offentlig"), "2017-01"),
    ("gh_pub_new_repos", "Andre offentlige org-er: nye offentlige repoer per måned", "gh", "per måned", lambda: gh("new_repos", "offentlig"), "2017-01"),
    ("norid_new_domains", "Nye .no-domener per måned", "norid", "per måned", lambda: simple("norid_new_domains.csv"), None),
    ("ssb_new_firms", "Nye foretak per kvartal, alle næringer", "ssb", "per kvartal", lambda: ssb("01-99"), None),
    ("ssb_new_firms_62", "Nye foretak per kvartal, NACE 62 (IT-tjenester)", "ssb", "per kvartal", lambda: ssb("62"), None),
    ("ssb_new_firms_63", "Nye foretak per kvartal, NACE 63 (informasjonstjenester)", "ssb", "per kvartal", lambda: ssb("63"), None),
    ("brreg_all", "Enhetsregisteret: registrerte enheter per måned, i live i dag", "brreg", "per måned", lambda: simple("brreg_registrations.csv", metric="all"), None),
    ("brreg_as", "Enhetsregisteret: nye AS per måned, i live i dag", "brreg", "per måned", lambda: simple("brreg_registrations.csv", metric="AS"), None),
    ("brreg_nace62", "Enhetsregisteret: nye enheter i NACE 62 per måned, i live i dag", "brreg", "per måned", lambda: simple("brreg_registrations.csv", metric="nace62"), None),
    ("oa_works", "Publikasjoner med norsk institusjon per måned, uten datasett", "oa", "per måned", lambda: openalex_nodata(), None),
    ("oa_articles", "Tidsskriftartikler med norsk institusjon per måned", "oa", "per måned", lambda: openalex("works_type", "article"), None),
    ("oa_preprints", "Preprints med norsk institusjon per måned", "oa", "per måned", lambda: openalex("works_type", "preprint"), None),
    ("oa_math", "Publikasjoner i matematikk med norsk institusjon", "oa", "per måned", lambda: openalex("works_field", "Mathematics"), None),
    ("oa_cs", "Publikasjoner i informatikk med norsk institusjon", "oa", "per måned", lambda: openalex("works_field", "Computer Science"), None),
    # Prioritet 2
    ("ct_start", "Kliniske studier med studiested i Norge, etter startmåned", "ct", "per måned", lambda: simple("clinicaltrials_norway.csv", metric="start"), None),
    ("ct_first_submitted", "Kliniske studier med studiested i Norge, etter registreringsmåned", "ct", "per måned", lambda: simple("clinicaltrials_norway.csv", metric="first_submitted"), None),
    ("ssb_patent", "Patentsøknader per år", "ssb_ip", "per år", lambda: ssb_ip("10990_patentsoknader"), None),
    ("ssb_design", "Designsøknader per år", "ssb_ip", "per år", lambda: ssb_ip("10991_designsoknader"), None),
    ("ssb_trademark", "Varemerkesøknader per år", "ssb_ip", "per år", lambda: ssb_ip("10992_varemerkesoknader"), None),
    ("wiki_no_edits", "Norsk Wikipedia (bokmål): redigeringer av innholdssider, uten boter", "wiki", "per måned", lambda: simple("wikimedia_norway.csv", project="no.wikipedia.org", metric="edits"), None),
    ("wiki_no_new_pages", "Norsk Wikipedia (bokmål): nye innholdssider, uten boter", "wiki", "per måned", lambda: simple("wikimedia_norway.csv", project="no.wikipedia.org", metric="new_pages"), None),
    ("wiki_no_editors", "Norsk Wikipedia (bokmål): aktive redaktører", "wiki", "per måned", lambda: simple("wikimedia_norway.csv", project="no.wikipedia.org", metric="active_editors"), None),
    ("wiki_nn_edits", "Nynorsk Wikipedia: redigeringer av innholdssider, uten boter", "wiki", "per måned", lambda: simple("wikimedia_norway.csv", project="nn.wikipedia.org", metric="edits"), None),
    ("nb_books_nob", "Bøker på bokmål i Nasjonalbibliotekets katalog, etter utgivelsesår", "nb", "per år", lambda: simple("nb_books.csv", group="nob").astype({"period": str}), None),
    ("nb_books_nno", "Bøker på nynorsk i Nasjonalbibliotekets katalog, etter utgivelsesår", "nb", "per år", lambda: simple("nb_books.csv", group="nno").astype({"period": str}), None),
    ("fr_applications", "Søknader til Forskningsrådet per år", "fr", "per år", lambda: fr("all"), None),
    ("fr_forskerprosjekt", "Søknader til Forskningsrådet, forskerprosjekt", "fr", "per år", lambda: fr("Forskerprosjekt", "soknadstype"), None),
    ("fr_innovasjonsprosjekt", "Søknader til Forskningsrådet, innovasjonsprosjekt", "fr", "per år", lambda: fr("Innovasjonsprosjekt", "soknadstype"), None),
    ("fr_naeringsliv", "Søknader til Forskningsrådet fra næringslivet", "fr", "per år", lambda: fr("Næringsliv", "sektor"), None),
    ("hor_svar_total", "Høringssvar på regjeringen.no per kvartal, etter høringsfrist", "hor", "per kvartal", lambda: hor("sum"), "2016Q3"),
    ("hor_svar_median", "Median antall høringssvar per høring, etter høringsfrist", "hor", "per kvartal", lambda: hor("median"), "2016Q3"),
    ("hor_antall", "Høringer på regjeringen.no med frist i kvartalet", "hor", "per kvartal", lambda: hor("size"), "2016Q3"),
    ("einnsyn_innsynskrav", "Innsynskrav sendt via eInnsyn", "einnsyn", "per måned", lambda: simple("einnsyn_statistics.csv", metric="innsynskrav"), "2018-02"),
]

rows = []
for name, title, src, unit, load, start in SERIES:
    try:
        df = load()
    except FileNotFoundError as e:
        print("hopper over", name, "mangler", Path(e.filename).name)
        continue
    df = df.sort_values("period")
    df.to_csv(OUT / "series" / f"{name}.csv", index=False)
    first = start or ("2016Q1" if "Q" in str(df.period.iloc[0]) else "2016-01" if "-" in str(df.period.iloc[0]) else "2016")
    r = tb.test(df, name, title, SRC[src], unit, start=first)
    rows += [{**x, "source": SRC[src]} for x in r]
    print(f"{name:28s}", " | ".join(f"{x['break']}: {x['class']} ({x['gap_last12_pct']:+.1f} %)" for x in r))
    if r[0]["freq"] == "M" and (any(x["class"] == "for støyete" for x in r) or name.startswith("gh_")):  # kvartalssum
        q = df.assign(q=pd.PeriodIndex(df.period, freq="M").asfreq("Q").astype(str)).groupby("q")["value"].agg(["sum", "size"])
        q = q[q["size"] == 3]["sum"].rename("value").rename_axis("period").reset_index()
        q.to_csv(OUT / "series" / f"{name}_kv.csv", index=False)
        r = tb.test(q, name + "_kv", title.replace(" per måned", "") + " (kvartalssum)", SRC[src], "per kvartal", start=str((pd.Period(first, "M") + 2).asfreq("Q")))
        rows += [{**x, "source": SRC[src]} for x in r]
        print(f"{name + '_kv':28s}", " | ".join(f"{x['break']}: {x['class']} ({x['gap_last12_pct']:+.1f} %)" for x in r))

pd.DataFrame(rows).to_csv(OUT / "summary.csv", index=False)
print("skrev", OUT / "summary.csv", len(rows), "rader")
