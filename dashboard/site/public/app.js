/* KI-indeksen / The AI Labor Market Index — dashboard-logikk. Leser
   data/dashboard.json (generert av prepare_data.py fra siste datarelease) og
   tegner alle figurene i samme stil som Stanford/ADP Canaries Dashboard
   (Flourish-aktige linjediagram med direkte endepunktsetiketter og
   ChatGPT-markering).

   Tospråklig: samme script betjener den norske forsiden (/) og den engelske
   (/en/). Språket bestemmes av <html lang>; all brukervendt tekst rutes
   gjennom EN-grenene under, og dataene (dashboard.json) er språknøytrale. */

(function () {
  "use strict";

  // ---------- Språk ----------
  var EN = (document.documentElement.lang || "nb")
             .toLowerCase().indexOf("en") === 0;

  // ---------- Etiketter og farger ----------

  var NO_LABELS = {
    "Quintile 1 (least exposed)": "Kvintil 1 (minst eksponert)",
    "Quintile 2": "Kvintil 2",
    "Quintile 3": "Kvintil 3",
    "Quintile 4": "Kvintil 4",
    "Quintile 5 (most exposed)": "Kvintil 5 (mest eksponert)",
    "Quintile 1 (least usage)": "Kvintil 1 (minst bruk)",
    "Quintile 5 (most usage)": "Kvintil 5 (mest bruk)",
    "No usage": "Ingen bruk",
    "All ages": "All ages"
  };
  // De engelske kolonnenavnene fra dataene brukes som de er på EN-siden;
  // på NO-siden oversettes de via tabellen over.
  function lab(s) { return EN ? s : (NO_LABELS[s] || s); }

  // Stanford-dashboardets palett i kvintilrekkefoelge
  // (jf. canaries_dashboard_oversikt.md).
  var QUINT_COLORS = ["#8C1515", "#577590", "#E54A2B", "#E6A817", "#401415"];
  var AGE_COLORS = { "21-30": "#8C1515", "31-40": "#E6A817",
                     "41-50": "#577590", "51-60": "#401415" };
  var USE_COLORS = ["#9D9C97", "#8C1515", "#577590", "#E54A2B",
                    "#E6A817", "#401415"];

  var MONTHS = EN
    ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    : ["jan.", "feb.", "mars", "april", "mai", "juni",
       "juli", "aug.", "sep.", "okt.", "nov.", "des."];
  function fmtMonth(iso) {
    return MONTHS[+iso.slice(5, 7) - 1] + " " + iso.slice(0, 4);
  }
  // Aldersgruppe-etikett: "21-30 år" på norsk, bare "21-30" på engelsk.
  function ageLab(c) { return EN ? c : c + " år"; }

  // ---------- Tallformatering ----------

  // Norsk bruker komma som desimalskille og mellomrom foran %.
  function fmtNum(v) {
    var s = (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(1);
    return EN ? s : s.replace(".", ",");
  }
  function unit() { return EN ? "%" : " %"; }
  function fmtPct(v) { return fmtNum(v) + unit(); }
  function magPct(v) {                       // usignert, allerede i prosent
    var s = Math.abs(v).toFixed(1);
    return EN ? s + "%" : s.replace(".", ",") + " %";
  }
  function pctMag(v) { return magPct(100 * v); }   // for forholdstall (ratio)
  function signedPct(v) { return fmtPct(100 * v); }

  // ---------- Tilstand ----------

  var DB = null;
  // Figurene viser raa serier (som DEL); sesong- og befolknings-
  // justerte varianter finnes kun i de nedlastbare filene.
  var state = { outcome: "employment", adjustment: "sa",
                smoothing: 6, epoch: "chatgpt", ageFacet: "21-30",
                usagePattern: "Automation", usageAge: "All ages" };

  // Referansepunkter: indeksene normaliseres til 100 i basismaaneden,
  // den vertikale markeringen flyttes, og foer-perioden i
  // vekstfigurene byttes.
  var EPOCHS = {
    chatgpt: {
      base: "2022-11-01",
      baseLabel: EN ? "Nov 2022" : "nov. 2022",
      mark: "2022-11-30",
      markLabel: EN ? "ChatGPT launch" : "ChatGPT-lansering",
      preFrom: "2022-10-01", preTo: "2022-10-01",
      preText: EN
        ? "the level in October 2022 (the month before ChatGPT)"
        : "nivået i oktober 2022 (måneden før ChatGPT)",
      note: EN
        ? "Index = 100 in November 2022 (launch of ChatGPT)"
        : "Indeks = 100 i november 2022 (lansering av ChatGPT)"
    },
    claudecode: {
      base: "2025-02-01",
      baseLabel: EN ? "Feb 2025" : "feb. 2025",
      mark: "2025-02-24",
      markLabel: EN ? "Claude Code launch" : "Claude Code-lansering",
      preFrom: "2024-02-01", preTo: "2025-01-01",
      preText: EN
        ? "the average of the twelve months before Claude Code " +
          "(February 2024–January 2025)"
        : "gjennomsnittet av de siste tolv månedene før " +
          "Claude Code (februar 2024–januar 2025)",
      note: EN
        ? "Index = 100 in February 2025 (launch of Claude Code, agentic AI)"
        : "Indeks = 100 i februar 2025 (lansering av Claude Code, " +
          "agentisk KI)"
    }
  };
  function epoch() { return EPOCHS[state.epoch]; }
  var charts = {};

  var OCCUPATIONS = ["software_developers", "customer_service",
                     "electricians", "home_health_aides"];

  // Utfall for hovedfigurene 1-3: pakkeprefiks og figurtitler.
  // Loenn publiseres bare raw/sa (per innbygger er meningsloest for
  // loenn); adjFor faller tilbake naar varianten mangler i pakken.
  var OUTCOMES = {
    employment: { prefix: "", word: EN ? "Employment" : "Sysselsetting" },
    hires: { prefix: "hires_", word: EN ? "New hires" : "Nyansettelser" },
    wages: { prefix: "wages_",
             word: EN ? "Pay (FTE-adjusted)" : "Lønn (FTE-justert)" }
  };
  function corePkg(base) { return OUTCOMES[state.outcome].prefix + base; }

  // ---------- Hjelpere ----------

  function movingAverage(values, k) {
    if (k <= 1) return values;
    var half = Math.floor(k / 2), out = [], i, j, s, n;
    for (i = 0; i < values.length; i++) {
      if (values[i] == null) { out.push(null); continue; }
      s = 0; n = 0;
      for (j = i - half; j <= i + half; j++) {
        if (j >= 0 && j < values.length && values[j] != null) {
          s += values[j]; n += 1;
        }
      }
      out.push(n ? Math.round(100 * s / n) / 100 : null);
    }
    return out;
  }

  // Justeringsvariant for pakken: oensket variant hvis den finnes,
  // ellers naermeste (loennspakkene mangler percap-variantene).
  function adjFor(pkg) {
    var s = DB.packages[pkg].series;
    if (s[state.adjustment]) return state.adjustment;
    return state.adjustment === "percap_sa" ? "sa" : "raw";
  }

  function seriesFor(pkg, facetKey, col) {
    var raw = DB.packages[pkg].series[adjFor(pkg)][facetKey][col];
    // Renormaliser til 100 i den valgte referansemaaneden.
    var baseIdx = DB.packages[pkg].dates.indexOf(epoch().base);
    if (baseIdx >= 0 && raw[baseIdx]) {
      var base = raw[baseIdx];
      raw = raw.map(function (v) {
        return v == null ? null : Math.round(10000 * v / base) / 100;
      });
    }
    return movingAverage(raw, state.smoothing);
  }

  function getChart(id) {
    if (!charts[id]) {
      charts[id] = echarts.init(document.getElementById(id), null,
                                { renderer: "canvas" });
    }
    return charts[id];
  }

  // Kildelinje nederst i hver figur, slik at kiindeksen.no og kildene
  // foelger med naar noen tar skjermbilde av en enkeltfigur.
  var BRAND = "kiindeksen.no · Hernæs & Kostøl";
  var SRC_MAIN = EN
    ? "Source: A-ordningen via microdata.no · Eloundou et al. (2024)"
    : "Kilde: A-ordningen via microdata.no · Eloundou m.fl. (2024)";
  var SRC_USAGE = EN
    ? "Source: A-ordningen via microdata.no · Anthropic Economic Index"
    : "Kilde: A-ordningen via microdata.no · Anthropic Economic Index";
  function brandGraphic(src) {
    return [{
      type: "text", left: 10, bottom: 2, silent: true,
      style: { text: BRAND + "  ·  " + (src || SRC_MAIN),
               fontSize: 10, fill: "#a39f95" }
    }];
  }

  // Linjediagram i Canaries-stil: tykke linjer, ingen legend, direkte
  // navnsetting ved endepunktene, vertikal "ChatGPT-lansering"-markering,
  // kun horisontale stoettelinjer.
  function lineOption(dates, seriesDefs, src, opts) {
    var series = seriesDefs.map(function (d) {
      return {
        name: d.name,
        type: "line",
        showSymbol: false,
        connectNulls: false,
        emphasis: { focus: "series", lineStyle: { width: 4 } },
        lineStyle: { width: 2.8 },
        itemStyle: { color: d.color },
        color: d.color,
        endLabel: {
          show: true, formatter: d.name, fontSize: 11.5,
          color: d.color, fontWeight: 600, distance: 8
        },
        labelLayout: { moveOverlap: "shiftY" },
        data: dates.map(function (t, i) { return [t, d.values[i]]; })
      };
    });
    return {
      animationDuration: 350,
      grid: { left: 44, right: 185, top: 34, bottom: 54 },
      graphic: brandGraphic(src),
      tooltip: {
        trigger: "axis",
        order: "valueDesc",
        valueFormatter: function (v) {
          return v == null ? "–" : (+v).toFixed(1);
        },
        axisPointer: { type: "line" }
      },
      legend: { show: false },
      xAxis: {
        type: "time",
        axisLabel: { formatter: "{yyyy}", hideOverlap: true,
                     color: "#5a5a5a" },
        axisLine: { lineStyle: { color: "#cfcdc6" } },
        axisTick: { show: false },
        splitLine: { show: false }
      },
      yAxis: {
        type: "value",
        scale: true,
        name: (EN ? "Index (" : "Indeks (") + epoch().baseLabel + " = 100)",
        nameTextStyle: { color: "#5a5a5a", align: "left" },
        nameGap: 16,
        axisLabel: { color: "#5a5a5a" },
        splitLine: { lineStyle: { color: "#e9e7e0" } }
      },
      series: series.concat([marks(opts)])
    };
  }

  // "_marks"-serien: ChatGPT-markeringen, 100-linjen og (for figur 1)
  // et svakt felt over gjeninnhentingen etter pandemien 2021-2022.
  function marks(opts) {
    var m = {
      name: "_marks", type: "line", data: [], silent: true,
      markLine: {
        symbol: "none",
        animation: false,
        data: [
          { xAxis: epoch().mark,
            lineStyle: { color: "#3a3a3a", type: "dashed", width: 1.3 },
            label: { formatter: epoch().markLabel,
                     position: "end", distance: 7,
                     color: "#3a3a3a", fontSize: 11.5, fontWeight: 600 } },
          { yAxis: 100,
            lineStyle: { color: "#cfcdc6", type: "dotted", width: 1 },
            label: { show: false } }
        ]
      }
    };
    if (opts && opts.band) {
      m.markArea = {
        silent: true,
        itemStyle: { color: "rgba(64,20,21,0.05)" },
        label: {
          show: true, position: "insideTop", distance: 6,
          color: "#9c958c", fontSize: 10, fontWeight: 600,
          lineHeight: 13,
          formatter: EN ? "Post-pandemic\nrecovery"
                        : "Gjeninnhenting\netter pandemien"
        },
        data: [[{ xAxis: "2021-01-01" }, { xAxis: "2022-11-01" }]]
      };
    }
    return m;
  }

  function renderLines(id, pkg, defs, src, opts) {
    var dates = DB.packages[pkg].dates;
    getChart(id).setOption(lineOption(dates, defs, src, opts),
                           { notMerge: true });
  }

  // ---------- Figurer 1-3 og 5-9 ----------

  function renderByExposure() {
    var pkg = corePkg("by_exposure");
    var cols = DB.packages[pkg].value_cols;
    renderLines("chart-by-exposure", pkg, cols.map(function (c, i) {
      return { name: lab(c), color: QUINT_COLORS[i],
               values: seriesFor(pkg, "_", c) };
    }), SRC_MAIN, { band: true });
  }

  function renderByAge() {
    var pkg = corePkg("by_age");
    var cols = DB.packages[pkg].value_cols;
    renderLines("chart-by-age", pkg, cols.map(function (c) {
      return { name: ageLab(c), color: AGE_COLORS[c],
               values: seriesFor(pkg, "_", c) };
    }));
  }

  function renderAgeByExposure() {
    var pkg = corePkg("age_by_exposure");
    var quintiles = Object.keys(DB.packages[pkg].series[adjFor(pkg)]);
    quintiles.sort();
    renderLines("chart-age-by-exposure", pkg,
      quintiles.map(function (q, i) {
        return { name: lab(q), color: QUINT_COLORS[i],
                 values: seriesFor(pkg, q, state.ageFacet) };
      }));
  }

  function renderOutcomeTitles() {
    var word = OUTCOMES[state.outcome].word;
    document.getElementById("title-exposure").textContent =
      "1 · " + word + (EN ? " by AI exposure" : " etter KI-eksponering");
    document.getElementById("title-age").textContent =
      "3 · " + word + (EN ? " by age" : " etter alder");
  }

  function renderOccupations() {
    OCCUPATIONS.forEach(function (occ) {
      var pkg = corePkg(occ);
      var cols = DB.packages[pkg].value_cols;
      renderLines("chart-occ-" + occ, pkg, cols.map(function (c) {
        return { name: ageLab(c), color: AGE_COLORS[c],
                 values: seriesFor(pkg, "_", c) };
      }));
    });
  }

  function renderUsage() {
    var pn = corePkg("usage_patterns_by_age");
    var pkg = DB.packages[pn];
    var key = state.usagePattern + "|" + state.usageAge;
    renderLines("chart-usage", pn,
      pkg.value_cols.map(function (c, i) {
        return { name: lab(c), color: USE_COLORS[i],
                 values: seriesFor(pn, key, c) };
      }), SRC_USAGE);
    renderUsageComposition();
  }

  // ---------- Figur 4 og 10-11: sammensetning ----------

  function stackedShareOption(rows, groups, colors, src) {
    var ages = [];
    rows.forEach(function (r) {
      if (ages.indexOf(r.age) < 0) ages.push(r.age);
    });
    ages.sort();
    var series = groups.map(function (g, i) {
      return {
        name: lab(g), type: "bar", stack: "total",
        itemStyle: { color: colors[i] },
        barWidth: "55%",
        data: ages.map(function (a) {
          var row = rows.filter(function (r) {
            return r.age === a && r.group === g;
          })[0];
          return row ? row.share : 0;
        })
      };
    });
    return {
      grid: { left: 70, right: 24, top: 34, bottom: 50 },
      graphic: brandGraphic(src),
      tooltip: {
        trigger: "axis", axisPointer: { type: "shadow" },
        valueFormatter: function (v) {
          return (+v).toFixed(1) + (EN ? "%" : " %");
        }
      },
      legend: { top: 0, textStyle: { fontSize: 11 } },
      xAxis: { type: "value",
               axisLabel: { formatter: EN ? "{value}%" : "{value} %",
                            color: "#5a5a5a" },
               splitLine: { lineStyle: { color: "#e9e7e0" } } },
      yAxis: { type: "category", axisLabel: { color: "#5a5a5a" },
               data: ages.map(function (a) { return ageLab(a); }) },
      series: series
    };
  }

  function renderComposition() {
    var snap = DB.snapshots.composition;
    var groups = ["Quintile 1 (least exposed)", "Quintile 2", "Quintile 3",
                  "Quintile 4", "Quintile 5 (most exposed)"];
    getChart("chart-composition").setOption(
      stackedShareOption(snap.rows, groups, QUINT_COLORS, SRC_MAIN),
      { notMerge: true });
  }

  function renderUsageComposition() {
    var name = "usage_" + state.usagePattern.toLowerCase()
               + "_ratio_composition";
    var snap = DB.snapshots[name];
    var groups = ["No usage", "Quintile 1 (least usage)", "Quintile 2",
                  "Quintile 3", "Quintile 4", "Quintile 5 (most usage)"];
    getChart("chart-usage-composition").setOption(
      stackedShareOption(snap.rows, groups, USE_COLORS, SRC_USAGE),
      { notMerge: true });
  }

  // ---------- Oppsummeringen: punktdiagram à la Stanford-infografikken
  // (tre rader paa felles prosentakse, dotter per gruppe, tekst ved
  // siden av hver rad). ----------

  var OUTCOME_NOUN = EN
    ? { employment: "employment", hires: "new hires", wages: "pay" }
    : { employment: "sysselsettingen", hires: "nyansettelsene",
        wages: "lønnen" };
  // Verbsamsvar (kun engelsk): "new hires have", "employment has".
  var OUTCOME_AUX = { employment: "has", hires: "have", wages: "has" };

  var LEAST_EXP = EN ? "Least exposed" : "Minst eksponert";
  var MOST_EXP = EN ? "Most exposed" : "Mest eksponert";
  var LEAST_USE = EN ? "Least usage" : "Minst bruk";
  var MOST_USE = EN ? "Most usage" : "Mest bruk";

  function yoyOf(pkg, fk, col) {
    var y = DB.packages[pkg].yoy_latest;
    if (!y) return null;
    var s = y.series[adjFor(pkg)];
    return s && s[fk] ? s[fk][col] : null;
  }

  // Verbfraser for forholdstall (ratio): norsk "falt/økt 1,2 %",
  // engelsk "fallen/risen 1.2%".
  function verbNo(v) { return (v < 0 ? "falt " : "økt ") + pctMag(v); }
  function fellRose(v) { return (v < 0 ? "fallen " : "risen ") + pctMag(v); }

  function summaryRowsData() {
    var be = corePkg("by_exposure"), ae = corePkg("age_by_exposure");
    if (!DB.packages[be].yoy_latest) return null;
    var qcols = DB.packages[be].value_cols;
    var noun = OUTCOME_NOUN[state.outcome];
    var aux = OUTCOME_AUX[state.outcome];

    function quintPoints(getVal) {
      return qcols.map(function (c, i) {
        return { name: lab(c), inside: String(i + 1),
                 above: i === 0 ? LEAST_EXP
                        : (i === qcols.length - 1 ? MOST_EXP : null),
                 color: QUINT_COLORS[i], value: getVal(c) };
      });
    }

    var r1 = quintPoints(function (c) { return yoyOf(be, "_", c); });
    var r2 = quintPoints(function (c) { return yoyOf(ae, c, "21-30"); });

    function v(points, i) { return points[i] ? points[i].value : null; }

    var rows;
    if (EN) {
      rows = [
        { label: "All age groups,<br>by exposure", points: r1,
          text: "Across all ages, " + noun +
            " in the most AI-exposed occupations " + aux + " " +
            fellRose(v(r1, 4)) + " over the past twelve months, versus " +
            signedPct(v(r1, 0)) + " in the least exposed." },
        { label: "Young (21–30),<br>by exposure", points: r2,
          text: "Among the youngest (21–30), " + noun +
            " in the most exposed occupations " + aux + " " +
            fellRose(v(r2, 4)) + ", while the least exposed " + aux + " " +
            fellRose(v(r2, 0)) + "." }
      ];
    } else {
      rows = [
        { label: "Alle aldersgrupper,<br>etter eksponering", points: r1,
          text: "Blant arbeidstakere i alle aldre har " + noun +
            " i de mest KI-eksponerte yrkene " + verbNo(v(r1, 4)) +
            " siste tolv måneder, mot " + signedPct(v(r1, 0)) +
            " i de minst eksponerte." },
        { label: "Unge (21–30 år),<br>etter eksponering", points: r2,
          text: "Blant de yngste (21–30 år) har " + noun +
            " i de mest eksponerte yrkene " + verbNo(v(r2, 4)) +
            ", mens de minst eksponerte har " + verbNo(v(r2, 0)) + "." }
      ];
    }
    return { date: DB.packages[be].yoy_latest.date, rows: rows };
  }

  function infoRowOption(points, xmin, xmax, isLast, src) {
    var pts = points.filter(function (p) { return p.value != null; });
    var vals = pts.map(function (p) { return 100 * p.value; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    return {
      animationDuration: 250,
      grid: { left: 10, right: 10, top: 44,
              bottom: isLast ? 44 : 6 },
      graphic: isLast ? brandGraphic(src) : [],
      tooltip: {
        trigger: "item",
        formatter: function (p) {
          return p.data.fullName + ": " + fmtPct(p.value[0]);
        }
      },
      xAxis: {
        type: "value", min: xmin, max: xmax,
        axisLabel: {
          show: isLast, color: "#5a5a5a",
          formatter: function (v) {
            return (v > 0 ? "+" : "") +
              (EN ? String(v) : String(v).replace(".", ",")) + unit();
          }
        },
        axisLine: { show: isLast, lineStyle: { color: "#cfcdc6" } },
        axisTick: { show: isLast },
        splitLine: { show: false }
      },
      yAxis: { type: "value", min: -1, max: 1, show: false },
      series: [
        { // spennet mellom gruppene
          type: "line", silent: true, z: 1,
          showSymbol: false,
          lineStyle: { color: "#d8d4ca", width: 2 },
          data: [[lo, 0], [hi, 0]],
          markLine: {
            symbol: "none", silent: true,
            data: [{ xAxis: 0,
                     lineStyle: { color: "#b9b6ad", type: "dotted",
                                  width: 1.2 },
                     label: { show: false } }]
          }
        },
        { // selve punktene
          type: "scatter", z: 3, symbolSize: 17,
          data: pts.map(function (p) {
            return {
              value: [100 * p.value, 0],
              fullName: p.name,
              itemStyle: { color: p.color },
              label: { show: p.inside !== "", position: "inside",
                       formatter: p.inside, color: "#fff",
                       fontWeight: 700, fontSize: 10 }
            };
          })
        },
        { // roterte navn over punktene
          type: "scatter", z: 2, symbolSize: 0, silent: true,
          data: pts.filter(function (p) { return p.above; })
            .map(function (p) {
              return {
                value: [100 * p.value, 0],
                fullName: p.name,
                label: { show: true, position: "top", distance: 11,
                         rotate: 36, align: "left",
                         verticalAlign: "middle",
                         formatter: p.above, fontSize: 10,
                         fontWeight: 600, color: p.color }
              };
            })
        }
      ]
    };
  }

  function renderSummary() {
    var S = summaryRowsData();
    var holder = document.getElementById("summary-infographic");
    if (!S) { holder.innerHTML = ""; return; }

    document.getElementById("summary-subtitle").textContent = EN
      ? "Change over the past twelve months by group (" +
        OUTCOME_NOUN[state.outcome] + "), as of " + fmtMonth(S.date) + "."
      : "Endring siste tolv måneder per gruppe (" +
        OUTCOME_NOUN[state.outcome] + "), per " + fmtMonth(S.date) + ".";

    if (!holder.children.length) {
      S.rows.forEach(function (row, i) {
        var div = document.createElement("div");
        div.className = "info-row";
        div.innerHTML =
          '<div class="info-label">' + row.label + "</div>" +
          '<div class="info-chart" id="info-chart-' + i + '"></div>' +
          '<p class="info-text" id="info-text-' + i + '"></p>';
        holder.appendChild(div);
      });
    }

    var all = [0];
    S.rows.forEach(function (row) {
      row.points.forEach(function (p) {
        if (p.value != null) all.push(100 * p.value);
      });
    });
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var pad = Math.max(0.4, (hi - lo) * 0.22);
    var xmin = Math.floor((lo - pad) * 2) / 2;
    var xmax = Math.ceil((hi + pad) * 2) / 2;

    S.rows.forEach(function (row, i) {
      getChart("info-chart-" + i).setOption(
        infoRowOption(row.points, xmin, xmax, i === S.rows.length - 1,
                      SRC_MAIN),
        { notMerge: true });
      document.getElementById("info-text-" + i).textContent = row.text;
    });
  }

  // Vekstfiguren foer figur 9: sysselsettingsvekst per bruksgruppe,
  // automatisering oeverst og augmentering nederst. Etter = snittet av
  // de tre siste maanedene; foer = referanseperioden for valgt epoke
  // (foer ChatGPT, eller siste aar foer Claude Code). Alltid
  // sysselsetting, alle aldre, raa indeks.
  function usageGrowth(values, dates) {
    var ep = epoch();
    var i0 = dates.indexOf(ep.preFrom), i1 = dates.indexOf(ep.preTo);
    if (i0 < 0 || i1 < 0) return null;
    var s = 0, n = 0, i;
    for (i = i0; i <= i1; i++) {
      if (values[i] != null) { s += values[i]; n += 1; }
    }
    var m = values.length;
    var after = (values[m - 3] + values[m - 2] + values[m - 1]) / 3;
    return n ? after / (s / n) - 1 : null;
  }

  function renderUsageInfographic() {
    var pkg = DB.packages.usage_patterns_by_age;
    var holder = document.getElementById("usage-infographic");
    var cols = pkg.value_cols;
    var dates = pkg.dates;

    // "Ingen bruk"-gruppen holdes utenfor figuren (foerste kolonne).
    function points(pattern) {
      return cols.slice(1).map(function (c, i) {
        return {
          name: lab(c),
          inside: String(i + 1),
          above: i === 0 ? LEAST_USE
                 : (i === cols.length - 2 ? MOST_USE : null),
          color: USE_COLORS[i + 1],
          value: usageGrowth(
            pkg.series[adjFor("usage_patterns_by_age")][
              pattern + "|All ages"][c], dates)
        };
      });
    }
    // ordNo/ordEn: "automatiserende"/"automating" osv.
    function rowText(points, ordNo, ordEn) {
      var q5 = points[points.length - 1].value, q1 = points[0].value;
      if (q5 == null || q1 == null) return "";
      if (EN) {
        return "Where Claude usage is most " + ordEn +
          ", employment has " + fellRose(q5) + ", versus " + signedPct(q1) +
          " where it is least " + ordEn + ".";
      }
      return "Der Claude-bruken er mest " + ordNo +
        " har sysselsettingen " + verbNo(q5) + ", mot " + signedPct(q1) +
        " der den er minst " + ordNo + ".";
    }
    var rA = points("Automation"), rB = points("Augmentation");
    var rows = [
      { label: EN ? "Automation,<br>by usage group"
                  : "Automatisering,<br>etter bruksgruppe",
        points: rA, text: rowText(rA, "automatiserende", "automating") },
      { label: EN ? "Augmentation,<br>by usage group"
                  : "Augmentering,<br>etter bruksgruppe",
        points: rB, text: rowText(rB, "augmenterende", "augmenting") }
    ];

    var m1 = fmtMonth(dates[dates.length - 3]);
    var m2 = fmtMonth(dates[dates.length - 1]);
    document.getElementById("usage-summary-subtitle").textContent = EN
      ? "Employment growth by usage group, all ages: the average of the " +
        "last three months (" + m1 + "–" + m2 + ") versus " +
        epoch().preText + "."
      : "Vekst i sysselsettingen per bruksgruppe, alle aldre: snittet av " +
        "de tre siste månedene (" + m1 + "–" + m2 + ") mot " +
        epoch().preText + ".";

    if (!holder.children.length) {
      rows.forEach(function (row, i) {
        var div = document.createElement("div");
        div.className = "info-row";
        div.innerHTML =
          '<div class="info-label">' + row.label + "</div>" +
          '<div class="info-chart" id="usage-info-chart-' + i + '"></div>' +
          '<p class="info-text" id="usage-info-text-' + i + '"></p>';
        holder.appendChild(div);
      });
    }

    var all = [0];
    rows.forEach(function (row) {
      row.points.forEach(function (p) {
        if (p.value != null) all.push(100 * p.value);
      });
    });
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var pad = Math.max(0.4, (hi - lo) * 0.22);
    var xmin = Math.floor((lo - pad) * 2) / 2;
    var xmax = Math.ceil((hi + pad) * 2) / 2;

    rows.forEach(function (row, i) {
      getChart("usage-info-chart-" + i).setOption(
        infoRowOption(row.points, xmin, xmax, i === rows.length - 1,
                      SRC_USAGE),
        { notMerge: true });
      document.getElementById("usage-info-text-" + i).textContent =
        row.text;
    });
  }

  // "For den utaalmodige leseren": setningene fylles med ferske tall
  // fra dataene (alltid sysselsetting, raa serier).
  function growthVerb(p) {                  // p allerede i prosent
    if (EN) return (p < 0 ? "fallen by " : "grown by ") + magPct(p);
    return (p < 0 ? "falt med " : "vokst med ") + magPct(p);
  }

  function renderQuickSummary() {
    var g = headlineGrowth();
    var el = document.getElementById("qs-2");
    if (!el) return;
    if (EN) {
      var gradEn = Math.abs(g.rel) < 1 ? "slightly " : "";
      el.innerHTML =
        "<strong>The AI Labor Market Index is " + gradEn +
        (g.rel >= 0 ? "positive" : "negative") + " (" +
        fmtNum(g.rel) + "):</strong> since October 2022 (the month before " +
        "ChatGPT), total private-sector employment in the most AI-exposed " +
        "occupations has " + growthVerb(g.g5) + ", versus " +
        fmtPct(g.g1) + " in the least-exposed occupations.";
    } else {
      var grad = Math.abs(g.rel) < 1 ? "svakt " : "";
      el.innerHTML =
        "<strong>KI-indeksen er " + grad +
        (g.rel >= 0 ? "positiv" : "negativ") + " (" +
        fmtNum(g.rel) + "):</strong> siden oktober 2022 " +
        "(måneden før ChatGPT) har samlet sysselsetting i privat sektor i " +
        "de mest KI-eksponerte yrkene " + growthVerb(g.g5) + ", mot " +
        fmtPct(g.g1) + " i de minst eksponerte yrkene.";
    }
  }

  // ---------- Hovedindeksen: sysselsettingsvektet snitt ----------

  var ADJ_LABELS = EN
    ? { raw: "Raw", sa: "Seasonally adjusted", percap: "Per capita",
        percap_sa: "Per capita, seasonally adjusted" }
    : { raw: "Rå", sa: "Sesongjustert", percap: "Per innbygger",
        percap_sa: "Per innbygger, sesongjustert" };

  // Hovedfiguren: sysselsettingsvekst etter vs. foer ChatGPT for minst
  // og mest eksponerte yrker. Foer = nivaaet i oktober 2022 (maaneden
  // rett foer ChatGPT), valgt for aa unngaa den differensielle gjen-
  // innhentingen etter pandemien i 2021-2022; etter = snitt av de tre
  // siste maanedene. Indeksen over soylene = relativ vekst (differansen).
  var Q5L = "Quintile 5 (most exposed)";
  var Q1L = "Quintile 1 (least exposed)";

  // Hovedindeksen foelger justeringsvalget; etter = snittet av de
  // tre siste maanedene.
  function headlineGrowth() {
    var be = DB.packages.by_exposure;
    var ser = be.series[adjFor("by_exposure")]._;
    var iPre0 = be.dates.indexOf("2022-10-01");
    var iPre1 = iPre0;
    var n = be.dates.length;
    function growth(col) {
      var v = ser[col], s = 0, i;
      for (i = iPre0; i <= iPre1; i++) s += v[i];
      var before = s / (iPre1 - iPre0 + 1);
      var after = (v[n - 3] + v[n - 2] + v[n - 1]) / 3;
      return 100 * (after / before - 1);
    }
    var g1 = growth(Q1L), g5 = growth(Q5L);
    return { g1: g1, g5: g5,
             rel: 100 * ((1 + g5 / 100) / (1 + g1 / 100) - 1),
             lastDate: be.dates[n - 1] };
  }

  function renderHeadline() {
    var g = headlineGrowth();
    document.getElementById("headline-value").textContent = fmtNum(g.rel);
    document.getElementById("headline-date").textContent = EN
      ? "percentage points, as of " + fmtMonth(g.lastDate) + " (" +
        ADJ_LABELS[adjFor("by_exposure")].toLowerCase() + ")"
      : "prosentpoeng, per " + fmtMonth(g.lastDate) + " (" +
        ADJ_LABELS[adjFor("by_exposure")].toLowerCase() + ")";
    var yoyEl = document.getElementById("headline-yoy");
    yoyEl.textContent = EN
      ? "Most exposed: " + fmtPct(g.g5) +
        " · Least exposed: " + fmtPct(g.g1)
      : "Mest eksponerte: " + fmtPct(g.g5) +
        " · Minst eksponerte: " + fmtPct(g.g1);
    yoyEl.className = "headline-yoy";

    // Usikkerhetsbaand: okkupasjons-klynge-bootstrap av KI-indeksen.
    // Standardfeilen gjelder bare den sesongjusterte hovedindeksen
    // (spec 'sa'), saa vi viser intervallet kun naar det valgte
    // justeringsnivaaet er det bootstrappen ble regnet paa; ellers
    // skjuler vi baandet framfor aa vise et intervall som ikke passer.
    var ciEl = document.getElementById("headline-ci");
    if (ciEl) {
      var u = DB.headline_uncertainty;
      if (u && adjFor("by_exposure") === u.spec) {
        ciEl.textContent = EN
          ? "95% bootstrap interval: " + fmtNum(u.ci_lo) + " to " +
            fmtNum(u.ci_hi) + " pp — not statistically distinguishable " +
            "from zero."
          : "95 % bootstrap-intervall: " + fmtNum(u.ci_lo) + " til " +
            fmtNum(u.ci_hi) + " pp — ikke statistisk forskjellig fra null.";
        ciEl.title = (EN ? "Occupation-cluster bootstrap standard error: "
                         : "Okkupasjons-klynge-bootstrap, standardfeil: ") +
          fmtNum(u.se) + " pp";
        ciEl.hidden = false;
      } else {
        ciEl.textContent = "";
        ciEl.hidden = true;
      }
    }

    var bars = EN ? [
      { name: "Least-exposed occupations\n(quintile 1)", value: g.g1,
        color: "#577590" },
      { name: "Most-exposed occupations\n(quintile 5)", value: g.g5,
        color: "#8C1515" }
    ] : [
      { name: "Minst eksponerte yrker\n(kvintil 1)", value: g.g1,
        color: "#577590" },
      { name: "Mest eksponerte yrker\n(kvintil 5)", value: g.g5,
        color: "#8C1515" }
    ];
    getChart("chart-headline").setOption({
      title: {
        text: (EN ? "AI Labor Market Index (relative growth): "
                  : "KI-indeksen (relativ vekst): ") + fmtPct(g.rel),
        left: "center", top: 4,
        textStyle: { fontSize: 14, fontWeight: 700, color: "#1d2733" }
      },
      grid: { left: 52, right: 30, top: 74, bottom: 62 },
      graphic: brandGraphic(SRC_MAIN),
      tooltip: {
        trigger: "axis", axisPointer: { type: "shadow" },
        valueFormatter: function (v) { return fmtPct(+v); }
      },
      xAxis: {
        type: "category",
        data: bars.map(function (b) { return b.name; }),
        axisLabel: { interval: 0, fontSize: 11.5, lineHeight: 15,
                     color: "#2a2a2a" },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: "#cfcdc6" } }
      },
      yAxis: {
        type: "value",
        name: EN ? "Growth after vs. before ChatGPT, %"
                 : "Vekst etter vs. før ChatGPT, %",
        nameTextStyle: { color: "#5a5a5a", align: "left" },
        nameGap: 18,
        axisLabel: { color: "#5a5a5a",
                     formatter: function (v) {
                       return v + (EN ? "%" : " %"); } },
        splitLine: { lineStyle: { color: "#e9e7e0" } }
      },
      series: [{
        type: "bar", barWidth: "44%",
        data: bars.map(function (b) {
          return {
            value: Math.round(b.value * 10) / 10,
            name: b.name,
            itemStyle: { color: b.color },
            label: {
              show: true,
              position: b.value >= 0 ? "top" : "bottom",
              fontWeight: 700, fontSize: 13, color: "#2a2a2a",
              formatter: function (p) { return fmtPct(p.value); }
            }
          };
        })
      }]
    }, { notMerge: true });

    document.getElementById("kpi-note").textContent = EN
      ? "Each bar shows how much employment in the group has grown since " +
        "October 2022 (the month just before ChatGPT), measured as the " +
        "average of the last three months. October 2022 is used as the " +
        "reference to avoid the differential post-pandemic recovery in " +
        "2021–2022. The AI Labor Market Index is the difference between " +
        "the bars. Explore the breakdown by quintile, age and occupation " +
        "in the figures below."
      : "Hver søyle viser hvor mye sysselsettingen i gruppen har vokst " +
        "siden oktober 2022 (måneden rett før ChatGPT), målt som snittet " +
        "av de tre siste månedene. Oktober 2022 brukes som referanse for " +
        "å unngå den ulike gjeninnhentingen etter pandemien i 2021–2022. " +
        "KI-indeksen er forskjellen mellom søylene. Utforsk fordelingen " +
        "på kvintiler, alder og yrker i figurene under.";
  }

  // ---------- Nedlastinger ----------

  var PKG_TITLES = EN ? {
    by_exposure: "By AI exposure",
    age_by_exposure: "Age × exposure",
    by_age: "By age group",
    composition: "Composition (snapshot)",
    software_developers: "Case: software developers",
    customer_service: "Case: customer service reps",
    electricians: "Case: electricians",
    home_health_aides: "Case: home health aides",
    stock_clerks: "Case: stock clerks",
    usage_patterns_by_age: "AI usage × age",
    usage_augmentation_ratio_composition: "Composition, augmentation",
    usage_automation_ratio_composition: "Composition, automation",
    hires_by_exposure: "New hires by AI exposure",
    hires_age_by_exposure: "New hires, age × exposure",
    hires_by_age: "New hires by age group",
    hires_software_developers: "New hires, case: software developers",
    hires_customer_service: "New hires, case: customer service reps",
    hires_electricians: "New hires, case: electricians",
    hires_home_health_aides: "New hires, case: home health aides",
    hires_stock_clerks: "New hires, case: stock clerks",
    hires_usage_patterns_by_age: "New hires, AI usage × age",
    wages_by_exposure: "Pay (FTE) by AI exposure",
    wages_age_by_exposure: "Pay (FTE), age × exposure",
    wages_by_age: "Pay (FTE) by age group",
    wages_software_developers: "Pay (FTE), case: software developers",
    wages_customer_service: "Pay (FTE), case: customer service reps",
    wages_electricians: "Pay (FTE), case: electricians",
    wages_home_health_aides: "Pay (FTE), case: home health aides",
    wages_stock_clerks: "Pay (FTE), case: stock clerks",
    wages_usage_patterns_by_age: "Pay (FTE), AI usage × age"
  } : {
    by_exposure: "Etter KI-eksponering",
    age_by_exposure: "Alder × eksponering",
    by_age: "Etter aldersgruppe",
    composition: "Sammensetning (snapshot)",
    software_developers: "Case: programvareutviklere",
    customer_service: "Case: kundebehandlere",
    electricians: "Case: elektrikere",
    home_health_aides: "Case: hjemmehjelpere",
    stock_clerks: "Case: lagermedarbeidere",
    usage_patterns_by_age: "KI-bruk × alder",
    usage_augmentation_ratio_composition: "Sammensetning, augmentering",
    usage_automation_ratio_composition: "Sammensetning, automatisering",
    hires_by_exposure: "Nyansettelser etter KI-eksponering",
    hires_age_by_exposure: "Nyansettelser, alder × eksponering",
    hires_by_age: "Nyansettelser etter aldersgruppe",
    hires_software_developers: "Nyansettelser, case: programvareutviklere",
    hires_customer_service: "Nyansettelser, case: kundebehandlere",
    hires_electricians: "Nyansettelser, case: elektrikere",
    hires_home_health_aides: "Nyansettelser, case: hjemmehjelpere",
    hires_stock_clerks: "Nyansettelser, case: lagermedarbeidere",
    hires_usage_patterns_by_age: "Nyansettelser, KI-bruk × alder",
    wages_by_exposure: "Lønn (FTE) etter KI-eksponering",
    wages_age_by_exposure: "Lønn (FTE), alder × eksponering",
    wages_by_age: "Lønn (FTE) etter aldersgruppe",
    wages_software_developers: "Lønn (FTE), case: programvareutviklere",
    wages_customer_service: "Lønn (FTE), case: kundebehandlere",
    wages_electricians: "Lønn (FTE), case: elektrikere",
    wages_home_health_aides: "Lønn (FTE), case: hjemmehjelpere",
    wages_stock_clerks: "Lønn (FTE), case: lagermedarbeidere",
    wages_usage_patterns_by_age: "Lønn (FTE), KI-bruk × alder"
  };

  var DL = EN
    ? { yoy: "12-month change", ann: "Annualized", doc: "Documentation" }
    : { yoy: "12 mnd endring", ann: "Annualisert", doc: "Dokumentasjon" };

  function renderDownloads() {
    var holder = document.getElementById("download-list");
    var rel = DB.release;
    var avail = DB.download_files || {};
    document.getElementById("release-label").textContent = rel;
    Object.keys(PKG_TITLES).forEach(function (name) {
      var kinds = avail[name];
      // Bare pakker som faktisk finnes i denne releasen, og bare de
      // filtypene som er generert (unngaar doede lenker).
      if (!kinds || kinds.indexOf("csv") < 0) return;
      var pkg = "canaries_no_" + name;
      var base = "/data/releases/" + rel + "/" + pkg + "/" + pkg;
      var card = document.createElement("div");
      card.className = "download-card";
      var links = '<a href="' + base + '.csv" download>CSV</a>';
      if (kinds.indexOf("yoy_change") >= 0) {
        links += '<a href="' + base +
                 '_yoy_change.csv" download>' + DL.yoy + '</a>';
      }
      if (kinds.indexOf("annualized") >= 0) {
        links += '<a href="' + base +
                 '_annualized.csv" download>' + DL.ann + '</a>';
      }
      if (kinds.indexOf("data_dictionary") >= 0) {
        links += '<a href="' + base +
                 '_data_dictionary.md" download>' + DL.doc + '</a>';
      }
      card.innerHTML = "<strong>" + PKG_TITLES[name] + "</strong>" + links;
      holder.appendChild(card);
    });
  }

  // ---------- Kontroller ----------

  function makeButtons(holderId, items, getActive, onPick) {
    var holder = document.getElementById(holderId);
    holder.innerHTML = "";
    items.forEach(function (it) {
      var b = document.createElement("button");
      b.textContent = it.label;
      b.setAttribute("role", "tab");
      if (it.value === getActive()) b.className = "active";
      b.addEventListener("click", function () {
        onPick(it.value);
        Array.prototype.forEach.call(holder.children, function (c) {
          c.className = c === b ? "active" : "";
        });
      });
      holder.appendChild(b);
    });
  }

  function renderAll() {
    renderOutcomeTitles();
    renderHeadline();
    renderQuickSummary();
    renderByExposure();
    renderAgeByExposure();
    renderByAge();
    renderComposition();
    renderOccupations();
    renderUsage();
    renderSummary();
    renderUsageInfographic();
  }

  function init(db) {
    DB = db;

    makeButtons("age-facet-buttons",
      DB.packages.age_by_exposure.value_cols.map(function (a) {
        return { value: a, label: ageLab(a) };
      }),
      function () { return state.ageFacet; },
      function (v) { state.ageFacet = v; renderAgeByExposure(); });

    var ageSel = document.getElementById("sel-usage-age");
    ["All ages", "21-30", "31-40", "41-50", "51-60"].forEach(function (a) {
      var o = document.createElement("option");
      o.value = a;
      o.textContent = a === "All ages"
        ? (EN ? "All ages" : "Alle aldre") : ageLab(a);
      ageSel.appendChild(o);
    });

    document.getElementById("sel-outcome")
      .addEventListener("change", function (e) {
        state.outcome = e.target.value;
        // Loenn finnes ikke per innbygger: deaktiver percap-valgene og
        // fall ned til naermeste variant.
        var adjSel = document.getElementById("sel-adjustment");
        var isWages = state.outcome === "wages";
        Array.prototype.forEach.call(adjSel.options, function (o) {
          if (o.value.indexOf("percap") === 0) o.disabled = isWages;
        });
        if (isWages && state.adjustment.indexOf("percap") === 0) {
          state.adjustment =
            state.adjustment === "percap_sa" ? "sa" : "raw";
          adjSel.value = state.adjustment;
        }
        renderAll();
      });
    document.getElementById("sel-smoothing")
      .addEventListener("change", function (e) {
        state.smoothing = +e.target.value; renderAll();
      });
    document.getElementById("sel-adjustment")
      .addEventListener("change", function (e) {
        state.adjustment = e.target.value; renderAll();
      });
    document.getElementById("sel-epoch")
      .addEventListener("change", function (e) {
        state.epoch = e.target.value;
        document.getElementById("idx-note").textContent = epoch().note;
        renderAll();
      });
    document.getElementById("sel-usage-pattern")
      .addEventListener("change", function (e) {
        state.usagePattern = e.target.value; renderUsage();
      });
    ageSel.addEventListener("change", function (e) {
      state.usageAge = e.target.value; renderUsage();
    });

    window.addEventListener("resize", function () {
      Object.keys(charts).forEach(function (k) { charts[k].resize(); });
    });

    // Innholdsfortegnelsen til venstre: marker aktiv seksjon ved
    // skrolling.
    var tocLinks = Array.prototype.slice.call(
      document.querySelectorAll("#toc-nav a"));
    if (tocLinks.length && "IntersectionObserver" in window) {
      var spy = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          tocLinks.forEach(function (a) {
            a.className = a.getAttribute("href") === "#" + en.target.id
              ? "active" : "";
          });
        });
      }, { rootMargin: "-12% 0px -78% 0px" });
      tocLinks.forEach(function (a) {
        var sec = document.querySelector(a.getAttribute("href"));
        if (sec) spy.observe(sec);
      });
    }

    renderDownloads();
    renderAll();
  }

  // ---------- Ordforklaringer (?-knappene) ----------

  var GLOSSARY = EN ? {
    utfall: "“Employment” is the number of wage earners in the group. " +
      "“New hires” is the number of new jobs that started during the " +
      "month. “Pay (FTE-adjusted)” is average monthly pay converted to " +
      "full-time: FTE stands for full-time equivalent, so a part-time " +
      "job counts as its share of a full-time position. This keeps " +
      "changes in pay separate from changes in how much people work. " +
      "Pay figures are nominal (not inflation-adjusted).",
    justering: "“Seasonally adjusted” removes fixed seasonal patterns – " +
      "such as the January dip and summer temps – so the underlying " +
      "trend is clearer. “Per capita” divides by the population in the " +
      "same age group, so growth does not simply reflect a larger " +
      "population.",
    glatting: "A moving average smooths out random month-to-month " +
      "fluctuations by showing the average of the surrounding months. " +
      "This makes trends easier to see.",
    referanse: "The point in time the series are measured from. ChatGPT " +
      "(November 2022) marks the breakthrough of large language models; " +
      "Claude Code (February 2025) the breakthrough of “agentic” AI that " +
      "carries out longer tasks on its own.",
    kvintil: "Occupations are sorted by AI exposure and split into five " +
      "equal-sized groups (“quintiles”). Quintile 1 is the fifth of " +
      "occupations with the lowest exposure, quintile 5 the fifth with " +
      "the highest.",
    eksponering: "AI exposure measures the share of an occupation’s " +
      "tasks that large language models (such as ChatGPT) can perform " +
      "substantially faster, as estimated by Eloundou et al. (2024). " +
      "High exposure means AI can be used for much of the job – not " +
      "necessarily that the job disappears.",
    indeks: "Every series is set to 100 in the reference month " +
      "(November 2022, when ChatGPT launched). 105 means 5% more than " +
      "then, 95 means 5% fewer. This lets large and small groups be " +
      "compared directly."
  } : {
    utfall: "«Sysselsetting» er antall lønnstakere i gruppen. " +
      "«Nyansettelser» er antall nye jobber som startet i måneden. " +
      "«Lønn (FTE-justert)» er gjennomsnittlig månedslønn omregnet til " +
      "full stilling: FTE står for fulltidsekvivalent, så en deltids- " +
      "jobb teller som sin andel av et årsverk. Slik blandes ikke " +
      "lønnsendringer med endringer i hvor mye folk jobber. " +
      "Lønnstallene er nominelle (ikke prisjustert).",
    justering: "«Sesongjustert» fjerner faste sesongmønstre – som " +
      "januardippen og sommervikarene – slik at den underliggende " +
      "utviklingen synes bedre. «Per innbygger» deler på befolkningen " +
      "i samme aldersgruppe, slik at veksten ikke bare skyldes at det " +
      "er blitt flere folk.",
    glatting: "Glidende snitt jevner ut tilfeldige svingninger fra " +
      "måned til måned ved å vise gjennomsnittet av månedene rundt. " +
      "Det gjør trendene lettere å se.",
    referanse: "Tidspunktet seriene regnes fra. ChatGPT (november " +
      "2022) markerer gjennombruddet for språkmodeller; Claude Code " +
      "(februar 2025) gjennombruddet for «agentisk» KI som utfører " +
      "lengre oppgaver på egen hånd.",
    kvintil: "Yrkene er sortert etter KI-eksponering og delt i fem " +
      "like store grupper («kvintiler»). Kvintil 1 er femtedelen av " +
      "yrkene med lavest eksponering, kvintil 5 femtedelen med " +
      "høyest.",
    eksponering: "KI-eksponering måler hvor stor andel av oppgavene i " +
      "et yrke som store språkmodeller (som ChatGPT) kan utføre " +
      "vesentlig raskere, anslått av Eloundou m.fl. (2024). Høy " +
      "eksponering betyr at KI kan brukes til mye av jobben – ikke " +
      "nødvendigvis at jobben forsvinner.",
    indeks: "Alle serier settes til 100 i referansemåneden (november " +
      "2022, da ChatGPT ble lansert). 105 betyr 5 % flere enn da, 95 " +
      "betyr 5 % færre. Slik kan store og små grupper sammenlignes " +
      "direkte."
  };

  document.addEventListener("click", function (e) {
    var btn = e.target.closest ? e.target.closest(".info-btn") : null;
    var pop = document.getElementById("term-pop");
    if (!btn) {
      if (pop) pop.style.display = "none";
      return;
    }
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "term-pop";
      document.body.appendChild(pop);
    }
    if (pop.style.display === "block" && pop._for === btn) {
      pop.style.display = "none";
      return;
    }
    pop.textContent = GLOSSARY[btn.getAttribute("data-term")] || "";
    pop._for = btn;
    pop.style.display = "block";
    var r = btn.getBoundingClientRect();
    pop.style.left =
      Math.max(8, Math.min(r.left, window.innerWidth - 310)) + "px";
    pop.style.top = (r.bottom + window.scrollY + 8) + "px";
  });
  document.addEventListener("keydown", function (e) {
    var pop = document.getElementById("term-pop");
    if (e.key === "Escape" && pop) pop.style.display = "none";
  });

  // ---------- Sitering: dagens dato og kopier-knapper ----------

  (function () {
    var MONTHS_FULL = EN
      ? ["January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"]
      : ["januar", "februar", "mars", "april", "mai", "juni", "juli",
         "august", "september", "oktober", "november", "desember"];
    var d = new Date();
    var dato = EN
      ? MONTHS_FULL[d.getMonth()] + " " + d.getDate() + ", " +
        d.getFullYear()
      : d.getDate() + ". " + MONTHS_FULL[d.getMonth()] + " " +
        d.getFullYear();
    Array.prototype.forEach.call(
      document.querySelectorAll(".cite-date"), function (el) {
        el.textContent = dato;
      });
    var bib = document.getElementById("cite-dash-bib");
    if (bib) bib.textContent = bib.textContent.replace("{{DATO}}", dato);

    Array.prototype.forEach.call(
      document.querySelectorAll(".copy-btn"), function (btn) {
        btn.addEventListener("click", function () {
          var el = document.getElementById(
            btn.getAttribute("data-copy"));
          if (!el || !navigator.clipboard) return;
          navigator.clipboard.writeText(el.innerText).then(function () {
            var orig = btn.textContent;
            btn.textContent = EN ? "Copied!" : "Kopiert!";
            btn.className = "copy-btn copied";
            setTimeout(function () {
              btn.textContent = orig;
              btn.className = "copy-btn";
            }, 1600);
          });
        });
      });
  })();

  // Versjonsparameteren omgaar gamle hurtigbufrede kopier; holdes i
  // takt med ?v= paa app.js i index.html. Absolutt sti slik at samme
  // script virker baade fra / og /en/.
  fetch("/data/dashboard.json?v=20260718a")
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(init)
    .catch(function (err) {
      document.getElementById("kpi-note").textContent = EN
        ? "Could not load the data (" + err.message + "). Please reload " +
          "the page."
        : "Kunne ikke laste dataene (" + err.message + "). Prøv å laste " +
          "siden på nytt.";
    });
})();
