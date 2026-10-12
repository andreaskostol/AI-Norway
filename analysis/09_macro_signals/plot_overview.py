"""
Oversiktsfigurer for KI-signaler i norske serier. Leser analysis/output/macro_signals/series/*.csv og
summary.csv (fra run_all.py) og skriver overview_*.png og .pdf til analysis/output/macro_signals/.

Hvert panel viser faktisk utvikling og trenden fra foer februar 2025 med 95 % baand, samme modell som
trend_break.py. Figurene er laget for aa skaleres til ca. 16 cm bredde: 10 tommer bredt, minste tekst
14 punkt. Linjer er merket direkte, uten forklaringsboks.

Kjor: cd analysis/09_macro_signals && python plot_overview.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

import trend_break as tb

OUT = Path(__file__).resolve().parents[2] / "analysis" / "output" / "macro_signals"
SUM = pd.read_csv(OUT / "summary.csv")
BRK = tb.BREAKS["2025m02"]

# Okabe-Ito
BLUE, ORANGE, GREEN, PURPLE, RED, GRAY, INK, MUTED = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00",
                                                      "#6E6E6E", "#1A1A1A", "#555555")
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman"], "mathtext.fontset": "stix",
    "font.size": 15, "axes.titlesize": 16, "axes.titleweight": "bold", "axes.labelsize": 15,
    "xtick.labelsize": 14, "ytick.labelsize": 14, "axes.edgecolor": "#888888", "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": "white", "axes.facecolor": "white",
    "lines.linewidth": 2.2,
})


def num(v, _=None):
    if abs(v) >= 1e6:
        return f"{v / 1e6:.1f}".replace(".", ",") + " mill."
    return f"{v:,.0f}".replace(",", " ")


def pct(v):
    return f"{v:+.1f}".replace(".", ",").replace("-", "−")


def series(name):
    d = pd.read_csv(OUT / "series" / f"{name}.csv", dtype={"period": str})
    y = pd.Series(d["value"].astype(float).values, index=tb.to_period(d["period"])).sort_index()
    start = SUM[(SUM.series == name) & (SUM["break"] == "2025m02")].pre_start.iloc[0]
    return y[y.index >= pd.Period(start, y.index.freqstr)]


def style(ax, title):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(True, axis="y", color="#E3E3E3", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", pad=8)
    ax.yaxis.set_major_formatter(FuncFormatter(num))
    ax.yaxis.set_major_locator(MaxNLocator(5))


def end_labels(ax, items):
    """items: liste av (x, y, tekst, farge). Skyver etikettene fra hverandre i y-retning."""
    lo, hi = ax.get_ylim()
    gap = 0.075 * (hi - lo)
    items = sorted(items, key=lambda t: t[1])
    ys = [it[1] for it in items]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + gap)
    for (x, _, text, color), yy in zip(items, ys):
        ax.annotate(text, xy=(x, yy), xytext=(8, 0), textcoords="offset points", va="center", ha="left",
                    color=color, fontsize=14, fontweight="bold", annotation_clip=False)


def year_axis(ax, x0, x1):
    span = x1 - x0
    step = 1 if span <= 5 else 2
    ax.set_xticks(range(int(np.ceil(x0)), int(x1) + 1, step))
    ax.set_xlim(x0, x1 + 0.12 * span)  # plass til etiketter til hoyre


def trend_panel(ax, name, title):
    y = series(name)
    row, fitted, proj = tb.fit_break(y, BRK)
    x, xp = tb.xnum(y.index), tb.xnum(proj.index)
    annual = y.index.freqstr[0] in "YA"
    ax.fill_between(xp, proj.lo, proj.hi, color="#C8C8C8", alpha=0.5, linewidth=0)
    ax.plot(xp, proj.proj, color=GRAY, linestyle="--", linewidth=2)
    ax.plot(x, y.values, color=BLUE, marker="o" if annual else None, markersize=6)
    if annual:
        err = np.vstack([(proj.proj - proj.lo).values, (proj.hi - proj.proj).values])
        ax.errorbar(xp, proj.proj.values, yerr=err, fmt="o", color=GRAY, markersize=6, capsize=4, linewidth=1.5)
    ax.axvline(tb.xnum(pd.PeriodIndex([BRK]))[0] - 1 / 24, color="#999999", linestyle=":", linewidth=1.3)
    style(ax, title)
    ax.set_ylim(0, max(y.max(), proj.hi.max()) * 1.12)
    year_axis(ax, x[0], xp[-1])
    end_labels(ax, [(x[-1], y.values[-1], "Faktisk", BLUE), (xp[-1], proj.proj.values[-1], "Trend", GRAY)])
    txt = f"Siste år {pct(row['gap_last12_pct'])} % mot trend, {row['class']}, bånd ±{row['band_halfwidth_pct']:.0f} %"
    ax.set_title(title, loc="left", pad=30)
    ax.text(0, 1.03, txt, transform=ax.transAxes, va="bottom", ha="left", fontsize=14, color=INK)


def index_panel(ax, names, title, base="2024Q4"):
    items = []
    for name, label, color in names:
        y = series(name)
        y = 100 * y / y[pd.Period(base, "Q")]
        x = tb.xnum(y.index)
        ax.plot(x, y.values, color=color, linewidth=3 if label == "Norge" else 2)
        items.append((x[-1], y.values[-1], label, color))
    ax.axhline(100, color="#BBBBBB", linewidth=1)
    ax.axvline(tb.xnum(pd.PeriodIndex([BRK]))[0] - 1 / 24, color="#999999", linestyle=":", linewidth=1.3)
    style(ax, title)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
    year_axis(ax, x[0], x[-1])
    end_labels(ax, items)


def note(fig, text, y=0.0):
    fig.text(0.01, y, text, ha="left", va="top", fontsize=13, color=MUTED, wrap=True)


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("lagret", name)


TREND_NOTE = ("Blå: faktisk. Grå stiplet: log-lineær trend med sesongdummyer estimert før februar 2025 "
              "(prikket linje), med 95 % bånd. «Siste år» er faktisk mot trend de siste tolv månedene.")
NORDIC = [("NO", "Norge", BLUE), ("SE", "Sverige", ORANGE), ("DK", "Danmark", GREEN), ("FI", "Finland", PURPLE),
          ("US", "USA", RED)]


def fig_software():
    fig, axs = plt.subplots(2, 2, figsize=(10, 8.6))
    trend_panel(axs[0, 0], "ig_no_git_pushes", "a) Git pushes fra Norge")
    trend_panel(axs[0, 1], "ig_no_new_developers", "b) Nye utviklerkontoer i Norge")
    index_panel(axs[1, 0], [(f"ig_{c.lower()}_git_pushes", lab, col) for c, lab, col in NORDIC],
                "c) Git pushes, 2024K4 = 100")
    index_panel(axs[1, 1], [(f"ig_{c.lower()}_new_developers", lab, col) for c, lab, col in NORDIC],
                "d) Nye utviklerkontoer, 2024K4 = 100")
    for ax in axs.flat:
        ax.set_ylabel("")
    fig.tight_layout(h_pad=2.2, w_pad=2.5)
    note(fig, "Per kvartal, 2020K1–2026K1. Kilde: GitHub Innovation Graph. Nye utviklerkontoer er endring i "
              "bestand. " + TREND_NOTE, y=0.0)
    save(fig, "overview_1_programvare")


def fig_github():
    fig, axs = plt.subplots(4, 2, figsize=(10, 15.5))
    for j, (grp, who) in enumerate([("nav", "NAV"), ("pub", "Andre offentlige")]):
        trend_panel(axs[0, j], f"gh_{grp}_commits_kv", f"{'ab'[j]}) {who}: commits")
        trend_panel(axs[1, j], f"gh_{grp}_prs_nodep_kv", f"{'cd'[j]}) {who}: pull requests")
        trend_panel(axs[2, j], f"gh_{grp}_prs_merged_nodep_kv", f"{'ef'[j]}) {who}: flettede PR-er")
        trend_panel(axs[3, j], f"gh_{grp}_new_repos_kv", f"{'gh'[j]}) {who}: nye repoer")
    fig.tight_layout(h_pad=2.2, w_pad=2.5)
    note(fig, "Per kvartal. NAV fra 2020, andre fra 2017. Andre offentlige er Skatteetaten, Digdir, Entur, Oslo "
              "kommune, Statens vegvesen, NRK, Kartverket og Politiet. Pull requests er uten avhengighetsboter "
              "(Dependabot, Renovate, GitHub Actions). Bare offentlige repoer. " + TREND_NOTE, y=0.0)
    save(fig, "overview_2_github")


def fig_copilot():
    d = pd.read_csv(Path(__file__).resolve().parents[2] / "data" / "macro_signals" / "github_orgs.csv")
    d = d[(d.metric == "prs_copilot_agent") & (d.period >= "2025-01")]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    items = []
    for grp, label, color in [("navikt", "NAV", BLUE), ("offentlig", "Andre offentlige", ORANGE)]:
        s = d[d.group == grp].groupby("period").value.sum()
        x = tb.xnum(pd.PeriodIndex(s.index, freq="M"))
        ax.plot(x, s.values, color=color, linewidth=2.6)
        items.append((x[-1], s.values[-1], label, color))
    style(ax, "Pull requests laget av Copilot-agenten per måned")
    ax.set_xlim(x[0], x[-1] + 0.35)
    ax.set_xticks([2025, 2025.5, 2026, 2026.5])
    ax.set_xticklabels(["jan. 2025", "jul. 2025", "jan. 2026", "jul. 2026"])
    end_labels(ax, items)
    fig.tight_layout()
    note(fig, "Forfatter app/copilot-swe-agent, offentlige repoer. Kilde: GitHub API.", y=0.0)
    save(fig, "overview_3_copilot")


def fig_firms():
    fig, axs = plt.subplots(2, 2, figsize=(10, 8.6))
    trend_panel(axs[0, 0], "ssb_new_firms", "a) Nye foretak, alle næringer")
    trend_panel(axs[0, 1], "ssb_new_firms_62", "b) Nye foretak, IT-tjenester (62)")
    trend_panel(axs[1, 0], "brreg_nace62_kv", "c) Enhetsregisteret, næring 62")
    trend_panel(axs[1, 1], "norid_new_domains_kv", "d) Nye .no-domener")
    fig.tight_layout(h_pad=2.2, w_pad=2.5)
    note(fig, "Per kvartal. Kilder: SSB tabell 08076 (a, b), Enhetsregisteret (c, bare enheter som finnes i dag, "
              "så eldre kvartaler er undertalt), Norid (d). " + TREND_NOTE, y=0.0)
    save(fig, "overview_4_foretak")


def fig_research():
    fig, axs = plt.subplots(3, 2, figsize=(10, 12.6))
    trend_panel(axs[0, 0], "oa_works", "a) Publikasjoner uten datasett")
    trend_panel(axs[0, 1], "oa_articles", "b) Tidsskriftartikler")
    trend_panel(axs[1, 0], "ssb_patent", "c) Patentsøknader per år")
    trend_panel(axs[1, 1], "ssb_trademark", "d) Varemerkesøknader per år")
    trend_panel(axs[2, 0], "fr_applications", "e) Søknader til Forskningsrådet")
    trend_panel(axs[2, 1], "fr_forskerprosjekt", "f) Forskerprosjekt, søknader")
    fig.tight_layout(h_pad=2.2, w_pad=2.5)
    note(fig, "a og b per måned, verk med minst én norsk institusjon, uten verk datert 1. januar (OpenAlex). c–f per "
              "år: SSB 10990 og 10992 (Patentstyret), Forskningsrådets åpne data etter søknadsdato, til og med 2025. "
              "For årsseriene er trenden uten sesong. " + TREND_NOTE, y=0.0)
    save(fig, "overview_5_forskning")


def fig_other():
    fig, axs = plt.subplots(3, 2, figsize=(10, 12.6))
    trend_panel(axs[0, 0], "wiki_no_editors", "a) Aktive redaktører, Wikipedia")
    trend_panel(axs[0, 1], "wiki_no_new_pages_kv", "b) Nye sider, Wikipedia")
    trend_panel(axs[1, 0], "ct_first_submitted_kv", "c) Kliniske studier, registrert")
    trend_panel(axs[1, 1], "einnsyn_innsynskrav_kv", "d) Innsynskrav via eInnsyn")
    trend_panel(axs[2, 0], "hor_svar_total", "e) Høringssvar, regjeringen.no")
    trend_panel(axs[2, 1], "hor_svar_median", "f) Høringssvar per høring, median")
    fig.tight_layout(h_pad=2.2, w_pad=2.5)
    note(fig, "a per måned, b–f per kvartal. Wikipedia på bokmål, uten boter. Kliniske studier med studiested "
              "i Norge etter første innsending (ClinicalTrials.gov). Høringssvar etter kvartalet for høringsfristen, "
              "høringer publisert fra 2016. " + TREND_NOTE, y=0.0)
    save(fig, "overview_6_tekst_helse_forvaltning")


GROUPS = [
    ("Programvare", [("ig_no_git_pushes", "Git pushes, Norge"), ("ig_no_new_developers", "Nye utviklerkontoer"),
                     ("ig_no_new_repos", "Nye repoer"), ("gh_nav_commits_kv", "NAV: commits"),
                     ("gh_nav_prs_nodep_kv", "NAV: pull requests"), ("gh_nav_prs_merged_nodep_kv", "NAV: flettede PR-er"),
                     ("gh_nav_new_repos_kv", "NAV: nye repoer"), ("gh_pub_commits_kv", "Andre off.: commits"),
                     ("gh_pub_prs_nodep_kv", "Andre off.: pull requests"),
                     ("gh_pub_prs_merged_nodep_kv", "Andre off.: flettede PR-er"),
                     ("gh_pub_new_repos_kv", "Andre off.: nye repoer")]),
    ("Foretak og domener", [("ssb_new_firms", "Nye foretak, alle"), ("ssb_new_firms_62", "Nye foretak, næring 62"),
                            ("ssb_new_firms_63", "Nye foretak, næring 63"),
                            ("brreg_nace62_kv", "Enhetsregisteret, næring 62"),
                            ("norid_new_domains_kv", "Nye .no-domener")]),
    ("Forskning og tekst", [("oa_works", "Publikasjoner"), ("oa_articles", "Tidsskriftartikler"),
                            ("oa_preprints_kv", "Preprints"), ("oa_math_kv", "Matematikk"),
                            ("oa_cs_kv", "Informatikk"), ("ssb_patent", "Patentsøknader"),
                            ("ssb_design", "Designsøknader"), ("ssb_trademark", "Varemerkesøknader"),
                            ("wiki_no_edits_kv", "Wikipedia: redigeringer"),
                            ("wiki_no_new_pages_kv", "Wikipedia: nye sider"),
                            ("wiki_no_editors", "Wikipedia: aktive redaktører"),
                            ("nb_books_nob", "Bøker på bokmål"),
                            ("fr_applications", "Søknader til Forskningsrådet"),
                            ("fr_forskerprosjekt", "Forskningsrådet: forskerprosjekt")]),
    ("Helse og forvaltning", [("ct_first_submitted_kv", "Kliniske studier, registrert"),
                              ("ct_start_kv", "Kliniske studier, startet"),
                              ("einnsyn_innsynskrav_kv", "Innsynskrav"),
                              ("hor_svar_total", "Høringssvar"),
                              ("hor_svar_median", "Høringssvar per høring")]),
]
XMIN, XMAX = -60, 100


def fig_summary():
    rows, labels, heads = [], [], []
    for head, items in GROUPS:
        heads.append(len(labels))
        labels.append(head)
        rows.append(None)
        for name, lab in items:
            if (SUM.series == name).any():
                labels.append(lab)
                rows.append(name)
    n = len(labels)
    fig, axs = plt.subplots(1, 2, figsize=(10, 0.36 * n + 1.6), sharey=True)
    for ax, (b, title) in zip(axs, [("2022m11", "Brudd nov. 2022"), ("2025m02", "Brudd feb. 2025")]):
        for i, name in enumerate(rows):
            if name is None:
                continue
            r = SUM[(SUM.series == name) & (SUM["break"] == b)].iloc[0]
            if r["class"] == "for kort":
                ax.text(0, i, "for kort", ha="center", va="center", fontsize=13, color=MUTED, style="italic",
                        bbox=dict(facecolor="white", edgecolor="none", pad=1), zorder=5)
                continue
            w = min(r.band_halfwidth_pct, XMAX)
            ax.barh(i, 2 * w, left=-w, height=0.62, color="#DADADA", linewidth=0)
            g = float(np.clip(r.gap_last12_pct, XMIN + 2, XMAX - 2))
            outside = r["class"] in ("brudd opp", "brudd ned")
            ax.plot(g, i, "o", markersize=9, color=BLUE if outside else "white",
                    markeredgecolor=BLUE, markeredgewidth=2)
            if r.gap_last12_pct > XMAX or r.gap_last12_pct < XMIN:
                left = r.gap_last12_pct < XMIN
                ax.text(g + (5 if left else -5), i, pct(r.gap_last12_pct), ha="left" if left else "right",
                        va="center", fontsize=13, color=INK)
        ax.axvline(0, color="#888888", linewidth=1)
        ax.set_xlim(XMIN, XMAX)
        ax.set_title(title, loc="left", pad=8)
        ax.set_xlabel("Siste år mot trend, %")
        ax.grid(True, axis="x", color="#E3E3E3", linewidth=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axs[0].set_yticks(range(n))
    axs[0].set_yticklabels(labels)
    for i in heads:
        axs[0].get_yticklabels()[i].set_fontweight("bold")
        axs[0].get_yticklabels()[i].set_color(INK)
    axs[0].set_ylim(n - 0.5, -0.7)
    fig.tight_layout(w_pad=1.5)
    note(fig, "Punkt: faktisk mot trend siste år. Grå stolpe: 95 % bånd rundt trenden. Fylt punkt: brudd (minst "
              "halvparten av periodene siste år utenfor båndet og bånd under ±25 %). Åpent punkt: ingen brudd "
              "eller for støyete. Verdier utenfor aksen står som tall.", y=0.0)
    save(fig, "overview_0_sammendrag")


if __name__ == "__main__":
    fig_summary()
    fig_software()
    if (OUT / "series" / "gh_nav_commits.csv").exists():
        fig_github()
        fig_copilot()
    fig_firms()
    fig_research()
    fig_other()
