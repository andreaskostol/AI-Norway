/* Arbeidsmarkedet — panelene ved siden av KI-indeksen: Yrker og Utdanning.
   Ett script for begge; <body data-panel="..."> sier hvilket panel som skal
   tegnes, og <html lang> styrer språket slik at samme fil betjener / og /en/.
   Data: public/data/yrker.json, utdanning.json, occupations.json (yrkes-
   velgeren på forsiden) og vacancies.json når den finnes, alle bygget av
   prepare_panels.py / prepare_data.py. Figurstilen følger app.js. */

(function () {
  "use strict";

  var EN = (document.documentElement.lang || "nb")
             .toLowerCase().indexOf("en") === 0;
  var PANEL = document.body.getAttribute("data-panel");
  var V = "20260907c";

  // ---------- Farger og etiketter ----------

  var QUINT_COLORS = ["#577590", "#E6A817", "#E54A2B", "#8C1515", "#401415"];
  var GREY = "#b8b4ab";
  // Fargen til plass 1-6 i yrkeslista. Plass 1 er hovedyrket (roedt).
  var SLOT_COLORS = ["#8C1515", "#577590", "#E6A817", "#2b3e50", "#E54A2B", "#9D9C97"];
  var TYPES = ["d", "fb", "ti", "va", "le"];
  var TYPE_COLORS = { d: "#401415", fb: "#E54A2B", ti: "#E6A817", va: "#577590", le: "#2b3e50" };
  var TYPE_LABELS = EN
    ? { d: "Directive", fb: "Feedback loop", ti: "Task iteration", va: "Validation", le: "Learning" }
    : { d: "Direkte delegering", fb: "Tilbakemeldingssløyfe", ti: "Oppgaveiterasjon",
        va: "Validering", le: "Læring" };
  var PLATFORM_LABELS = EN
    ? { claude_ai: "Claude.ai (chat)", api: "API (developers, agents)" }
    : { claude_ai: "Claude.ai (chat)", api: "API (utviklere, agenter)" };
  var PLATFORM_SHORT = { claude_ai: EN ? "Chat" : "Chat", api: "API" };

  var BRAND = "kiindeksen.no  ·  Hernæs & Kostøl";
  function brandGraphic(src) {
    return [{ type: "text", left: 10, bottom: 2, silent: true,
              style: { text: BRAND + "  ·  " + src, fontSize: 10, fill: "#a39f95" } }];
  }
  var SRC_AEI = EN
    ? "Source: Anthropic Economic Index, mapped to STYRK-08 via O*NET/SOC/ISCO"
    : "Kilde: Anthropic Economic Index, koblet til STYRK-08 via O*NET/SOC/ISCO";
  var SRC_LM = EN ? "Source: A-ordningen via microdata.no" : "Kilde: A-ordningen via microdata.no";
  var SRC_EDU = EN
    ? "Source: DBH (HK-dir), utdanning.no register link, Eloundou et al. (2024), Mouchel et al. (2026)"
    : "Kilde: DBH (HK-dir), utdanning.no-registerkobling, Eloundou m.fl. (2024), Mouchel m.fl. (2026)";

  // ---------- Små hjelpere ----------

  function num(x, dec) {
    if (x === null || x === undefined || isNaN(x)) return "–";
    var s = Number(x).toFixed(dec === undefined ? 1 : dec);
    return EN ? s : s.replace(".", ",");
  }
  function pct(x, dec) { return num(x, dec) + " %"; }
  function thousands(n) {
    if (n === null || n === undefined) return "–";
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, EN ? "," : " ");
  }
  function trunc(s, n) { s = s || ""; return s.length > n ? s.slice(0, n - 1) + "…" : s; }
  function el(id) { return document.getElementById(id); }
  function setText(id, s) { var e = el(id); if (e) e.textContent = s; }
  function occName(o) { return EN && o.name_en ? o.name_en : o.name; }
  function qBadge(q) {
    return q ? "<span class='q-badge' style='background:" + QUINT_COLORS[q - 1] + "'>" +
      (EN ? "Q" : "K") + q + "</span>" : "–";
  }

  function makeButtons(id, options, get, set) {
    var box = el(id);
    if (!box) return;
    box.innerHTML = "";
    options.forEach(function (opt) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = opt.label;
      b.setAttribute("data-value", opt.value);
      b.className = get() === opt.value ? "active" : "";
      b.addEventListener("click", function () {
        set(opt.value);
        Array.prototype.forEach.call(box.children, function (c) {
          c.className = c.getAttribute("data-value") === String(get()) ? "active" : "";
        });
      });
      box.appendChild(b);
    });
  }

  var CHARTS = {};
  function chart(id) {
    var e = el(id);
    if (!e) return null;
    if (!CHARTS[id]) CHARTS[id] = echarts.init(e, null, { renderer: "canvas" });
    return CHARTS[id];
  }
  // Figurer med én rad per element: sett hoeyden paa beholderen foerst,
  // ellers tegner ECharts utenfor den og over neste seksjon.
  function sizeChart(id, height) {
    el(id).style.height = height + "px";
    chart(id).resize({ height: height });
  }
  window.addEventListener("resize", function () {
    Object.keys(CHARTS).forEach(function (k) { CHARTS[k].resize(); });
  });

  function initToc() {
    var links = Array.prototype.slice.call(document.querySelectorAll("#toc-nav a[href^='#']"));
    if (!links.length) return;
    var targets = links.map(function (a) { return el(a.getAttribute("href").slice(1)); });
    function update() {
      var y = window.scrollY + 120, active = 0;
      targets.forEach(function (t, i) { if (t && t.offsetTop <= y) active = i; });
      links.forEach(function (a, i) { a.className = i === active ? "active" : ""; });
    }
    window.addEventListener("scroll", update, { passive: true });
    update();
  }

  function fail(err) {
    var e = document.querySelector(".panel-status");
    if (e) e.textContent = (EN ? "Could not load the data (" : "Kunne ikke laste dataene (") +
      err.message + ").";
  }

  // Stablet 100 %-stolpe med de fem typene, én rad per element.
  function stackedTypeOption(rows, src, opts) {
    opts = opts || {};
    var left = opts.left || 250;
    return {
      animationDuration: 300,
      grid: { left: left, right: 30, top: 44, bottom: 40 },
      graphic: brandGraphic(src),
      legend: { top: 4, left: left, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11 } },
      tooltip: {
        trigger: "axis", axisPointer: { type: "shadow" },
        formatter: function (ps) {
          var r = rows[ps[0].dataIndex];
          var s = "<b>" + r.label + "</b>";
          if (r.sub) s += "<br><span style='color:#777'>" + r.sub + "</span>";
          ps.forEach(function (p) { s += "<br>" + p.marker + p.seriesName + ": " + pct(p.value, 1); });
          if (r.v.n) s += "<br><span style='color:#777'>" +
            (EN ? "Classified conversations: " : "Klassifiserte samtaler: ") + thousands(r.v.n) + "</span>";
          return s;
        }
      },
      xAxis: { type: "value", max: 100, axisLabel: { formatter: function (v) { return v + " %"; } },
               splitLine: { lineStyle: { color: "#eee" } } },
      yAxis: { type: "category", inverse: true, data: rows.map(function (r) { return r.axis; }),
               axisLabel: { fontSize: 11, width: left - 16, overflow: "truncate" },
               axisTick: { show: false } },
      series: TYPES.map(function (t) {
        return { name: TYPE_LABELS[t], type: "bar", stack: "s", itemStyle: { color: TYPE_COLORS[t] },
                 emphasis: { focus: "series" }, barMaxWidth: 22,
                 data: rows.map(function (r) { return r.v[t] === null ? 0 : r.v[t] * 100; }) };
      })
    };
  }

  // ==================================================================
  // YRKER
  // ==================================================================

  function initYrker(Y, OCC) {
    var byCode = {};
    Y.occupations.forEach(function (o) { byCode[o.code] = o; });
    OCC.byCode = {};
    OCC.occupations.forEach(function (o) { OCC.byCode[o.code] = o; });
    var vint = Y.vintages;
    function vintagesFor(p) { return vint.filter(function (v) { return v.platform === p; }); }
    var latestKey = { claude_ai: vintagesFor("claude_ai").slice(-1)[0].key,
                      api: vintagesFor("api").slice(-1)[0].key };
    var vintByKey = {};
    vint.forEach(function (v) { vintByKey[v.key] = v; });
    function vlabel(v) { return EN ? v.label_en : v.label; }
    var OCC_MAX = 6;
    var REF_MONTH = "2025-02-01";
    var WINDOW_START = "2023-02-01";   // to aar foer Claude Code
    var state = { occs: [], outcome: "employment", platform: "claude_ai",
                  vintage: latestKey.claude_ai, tidPlatform: "claude_ai", taskPlatform: "claude_ai" };
    function focus() { return state.occs[0] ? byCode[state.occs[0]] : null; }
    function latestChat(o) { return o.v[latestKey.claude_ai]; }
    function latestApi(o) { return o.v[latestKey.api]; }

    // ---- Lista: hovedyrket foerst ----
    function setFocus(code) {
      if (!byCode[code]) return;
      state.occs = [code].concat(state.occs.filter(function (c) { return c !== code; })).slice(0, OCC_MAX);
      renderAll();
    }
    function addOcc(code) {
      if (!byCode[code] || state.occs.indexOf(code) >= 0) return;
      state.occs.push(code);
      if (state.occs.length > OCC_MAX) state.occs.splice(1, 1);
      renderAll();
    }
    function removeOcc(code) {
      state.occs = state.occs.filter(function (c) { return c !== code; });
      renderAll();
    }
    function addNeighbours() {
      var f = focus();
      if (!f) return;
      f.nb.forEach(function (nb) {
        if (byCode[nb.code] && state.occs.indexOf(nb.code) < 0) {
          state.occs.push(nb.code);
          if (state.occs.length > OCC_MAX) state.occs.splice(1, 1);
        }
      });
      renderAll();
    }
    function startFrom(code) {
      var o = byCode[code];
      state.occs = [code].concat(o.nb.map(function (n) { return n.code; })
        .filter(function (c) { return byCode[c]; })).slice(0, OCC_MAX);
      renderAll();
    }
    function randomOcc() {
      var pool = Y.occupations.filter(function (o) { return o.n && o.n >= 2000 && o.nb.length; });
      startFrom(pool[Math.floor(Math.random() * pool.length)].code);
    }

    function renderChips() {
      var box = el("occ-chips");
      box.innerHTML = "";
      state.occs.forEach(function (code, i) {
        var o = byCode[code];
        var chip = document.createElement("span");
        chip.className = "occ-chip" + (i === 0 ? " occ-chip-focus" : "");
        chip.title = i === 0 ? (EN ? "Main occupation" : "Hovedyrke")
                             : (EN ? "Click to make this the main occupation" : "Klikk for å gjøre dette til hovedyrke");
        var pick = document.createElement("button");
        pick.type = "button";
        pick.className = "occ-chip-name";
        pick.innerHTML = "<i style='background:" + SLOT_COLORS[i] + "'></i><code>" + code + "</code> " + occName(o);
        pick.addEventListener("click", function () { if (i !== 0) setFocus(code); });
        chip.appendChild(pick);
        var x = document.createElement("button");
        x.type = "button"; x.textContent = "×";
        x.setAttribute("aria-label", EN ? "Remove" : "Fjern");
        x.addEventListener("click", function () { removeOcc(code); });
        chip.appendChild(x);
        box.appendChild(chip);
      });
    }

    // ---- Sysselsetting / loenn for lista, to aar foer Claude Code ----
    function renderLM() {
      var start = OCC.dates.indexOf(WINDOW_START);
      if (start < 0) start = 0;
      var dates = OCC.dates.slice(start);
      var refIdx = OCC.dates.indexOf(REF_MONTH);
      var series = [], missing = [];
      state.occs.forEach(function (code, i) {
        var s = OCC.byCode[code];
        if (!s || !s[state.outcome]) { missing.push(occName(byCode[code])); return; }
        var base = refIdx >= 0 ? s[state.outcome].sa[refIdx] : null;
        series.push({
          name: occName(byCode[code]) + " (" + code + ")", type: "line", showSymbol: false,
          lineStyle: { width: i === 0 ? 3.4 : 2.2 }, itemStyle: { color: SLOT_COLORS[i] }, color: SLOT_COLORS[i],
          endLabel: { show: true, formatter: trunc(occName(byCode[code]), 24), fontSize: 11,
                      color: SLOT_COLORS[i], fontWeight: 600, distance: 6 },
          labelLayout: { moveOverlap: "shiftY" },
          data: s[state.outcome].sa.slice(start).map(function (v) {
            return v === null || !base ? null : +(v / base * 100).toFixed(2);
          })
        });
      });
      var c = chart("chart-lm");
      if (!series.length) {
        c.clear();
        setText("lm-note", EN ? "No monthly series for these occupations (fewer than 30 employees)."
                             : "Ingen månedsserie for disse yrkene (under 30 lønnstakere).");
        return;
      }
      c.setOption({
        animationDuration: 300,
        grid: { left: 50, right: 190, top: 30, bottom: 44 },
        graphic: brandGraphic(SRC_LM),
        tooltip: { trigger: "axis", valueFormatter: function (v) { return v === null ? "–" : num(v, 1); } },
        xAxis: { type: "category", boundaryGap: false,
                 data: dates.map(function (d) { return d.slice(0, 7); }),
                 axisLabel: { interval: 0, formatter: function (v) { return v.slice(5) === "01" ? v.slice(0, 4) : ""; } } },
        yAxis: { type: "value", scale: true, splitLine: { lineStyle: { color: "#eee" } },
                 name: EN ? "Index (Feb 2025 = 100)" : "Indeks (feb. 2025 = 100)", nameTextStyle: { align: "left" } },
        series: series.concat([{ type: "line", data: [], markLine: {
          silent: true, symbol: "none", lineStyle: { type: "dashed", color: "#666" },
          label: { formatter: EN ? "Claude Code launch" : "Claude Code-lansering", fontSize: 10.5 },
          data: refIdx >= start ? [{ xAxis: refIdx - start }] : [] } }])
      }, true);
      setText("lm-note", (state.outcome === "employment"
        ? (EN ? "Employment" : "Sysselsetting") : (EN ? "Pay per full-time equivalent" : "Lønn per fulltidsekvivalent")) +
        (EN ? ", seasonally adjusted, private sector, ages 21–60. Index 100 in February 2025."
            : ", sesongjustert, privat sektor, 21–60 år. Indeks 100 i februar 2025.") +
        (missing.length ? (EN ? " No series (fewer than 30 employees): " : " Ingen serie (under 30 lønnstakere): ") +
          missing.join(", ") + "." : ""));
    }

    // ---- Skaarkort for hovedyrket ----
    function renderCard() {
      var box = el("pick-card"), o = focus();
      if (!o) { box.innerHTML = ""; return; }
      var c = latestChat(o), a = latestApi(o);
      function metric(label, value, extra) {
        return "<div class='pick-metric'><strong>" + value + "</strong>" + label + (extra ? " " + extra : "") + "</div>";
      }
      box.innerHTML =
        "<h3>" + occName(o) + " <code>" + o.code + "</code></h3>" +
        "<p class='pick-sub'>" + (o.n
          ? thousands(o.n) + (EN ? " private-sector employees (Nov 2022)" : " lønnstakere i privat sektor (nov. 2022)")
          : (EN ? "Fewer than 30 private-sector employees, no monthly series" : "Under 30 lønnstakere i privat sektor, ingen månedsserie")) +
        "</p><div class='pick-metrics'>" +
        metric(EN ? "AI exposure, Eloundou (0–1)" : "KI-eksponering, Eloundou (0–1)", o.beta === null ? "–" : num(o.beta, 2), qBadge(o.q)) +
        metric(EN ? "AI exposure, Mouchel (0–1)" : "KI-eksponering, Mouchel (0–1)", o.mouchel === null ? "–" : num(o.mouchel, 2), qBadge(o.q_mouchel)) +
        metric(EN ? "Share of all Claude.ai use" : "Andel av all Claude.ai-bruk", c ? num(c.u, 2) + " %" : "–") +
        metric(EN ? "Automation share, chat" : "Automatiseringsandel, chat", c && c.auto !== null ? pct(c.auto * 100, 0) : "–") +
        metric(EN ? "Augmentation share, chat" : "Augmenteringsandel, chat", c && c.aug !== null ? pct(c.aug * 100, 0) : "–") +
        metric(EN ? "Automation share, API" : "Automatiseringsandel, API", a && a.auto !== null ? pct(a.auto * 100, 0) : "–") +
        metric(EN ? "Classified conversations, chat" : "Klassifiserte samtaler, chat", c && c.n ? thousands(c.n) : "–") +
        "</div>";
    }

    // ---- De fem typene for hovedyrket, per utvalg ----
    function renderTypes() {
      var o = focus(), c = chart("chart-types");
      if (!o) { c.clear(); return; }
      var rows = [];
      vint.forEach(function (v) {
        var x = o.v[v.key];
        if (!x || x.auto === null) return;
        rows.push({ label: PLATFORM_LABELS[v.platform] + ", " + vlabel(v),
                    sub: EN ? v.source_en : v.source,
                    axis: PLATFORM_SHORT[v.platform] + " · " + vlabel(v), v: x });
      });
      if (!rows.length) {
        c.clear();
        setText("types-note", EN ? "No usage data for this occupation." : "Ingen bruksdata for dette yrket.");
        return;
      }
      c.setOption(stackedTypeOption(rows, SRC_AEI, { left: 190 }), true);
      setText("types-note", EN
        ? occName(o) + ": share of classified Claude conversations about the occupation's tasks, by interaction type. Red is automation, the rest augmentation."
        : occName(o) + ": andel av klassifiserte Claude-samtaler om yrkets oppgaver, etter interaksjonstype. Rødt er automatisering, resten augmentering.");
    }

    // ---- Naermeste yrker ----
    function renderNeighbours() {
      var box = el("pick-neighbours"), o = focus();
      box.innerHTML = "";
      if (!o) return;
      if (!o.nb.length) {
        box.innerHTML = "<p class='chart-footnote'>" + (EN ? "No O*NET profile for this occupation." : "Ingen O*NET-profil for dette yrket.") + "</p>";
        setText("nb-note", "");
        return;
      }
      o.nb.forEach(function (nb, i) {
        var n = byCode[nb.code];
        if (!n) return;
        var c = latestChat(n);
        var card = document.createElement("div");
        card.className = "pick-nb";
        card.style.borderTopColor = SLOT_COLORS[(i + 1) % SLOT_COLORS.length];
        card.innerHTML = "<h4>" + occName(n) + " <code>" + n.code + "</code></h4>" +
          "<p class='pick-sub'>" + (EN ? "Similarity " : "Likhet ") + num(nb.sim, 2) +
          (n.n ? " · " + thousands(n.n) + (EN ? " employees" : " lønnstakere") : "") + "</p>" +
          "<div>" + (EN ? "Exposure " : "Eksponering ") + qBadge(n.q) + " · " +
          (EN ? "automation, chat " : "automatisering, chat ") + (c && c.auto !== null ? pct(c.auto * 100, 0) : "–") + "</div>" +
          (nb.shared && nb.shared.length
            ? "<p class='pick-shared'>" + (EN ? "Shared: " : "Felles: ") + nb.shared.join(", ") + "</p>" : "");
        var b1 = document.createElement("button");
        b1.type = "button"; b1.textContent = EN ? "Add to the list" : "Legg til i lista";
        b1.addEventListener("click", function () { addOcc(n.code); });
        var b2 = document.createElement("button");
        b2.type = "button"; b2.textContent = EN ? "Make this the main one" : "Gjør til hovedyrke";
        b2.addEventListener("click", function () { setFocus(n.code); });
        card.appendChild(b1); card.appendChild(b2);
        box.appendChild(card);
      });
      setText("nb-note", EN
        ? "Closest to " + occName(o) + " by O*NET work activities and skills. \"Shared\" lists the activities both score high on that contribute most to the similarity (O*NET's names)."
        : "Nærmest " + occName(o) + " etter O*NETs arbeidsaktiviteter og ferdigheter. «Felles» er aktivitetene begge skårer høyt på og som bidrar mest til likheten (O*NETs navn).");
    }

    // ---- Oppgavene i hovedyrket ----
    function renderTasks() {
      var o = focus(), c = chart("chart-y4");
      var tasks = o ? (o.tasks[state.taskPlatform] || []) : [];
      var data = tasks.map(function (t) {
        return { label: t.t, sub: "SOC " + t.soc + " · " + (EN ? "share of all conversations " : "andel av alle samtaler ") + num(t.pct, 3) + " %",
                 axis: trunc(t.t, 70), v: t };
      });
      if (!data.length) {
        c.clear();
        setText("y4-note", EN ? "No task-level data for this occupation on this platform." : "Ingen oppgavedata for dette yrket på denne plattformen.");
        return;
      }
      sizeChart("chart-y4", Math.max(300, 60 + data.length * 30));
      c.setOption(stackedTypeOption(data, SRC_AEI, { left: 430 }), true);
      var v = vintByKey[latestKey[state.taskPlatform]];
      setText("y4-note", EN
        ? occName(o) + " (" + o.code + "): the " + data.length + " O*NET tasks with most Claude use among the SOC occupations this code maps to, " +
          PLATFORM_LABELS[state.taskPlatform] + ", " + vlabel(v) + ". Task texts are O*NET's English statements. Only tasks with at least 10 classified conversations."
        : occName(o) + " (" + o.code + "): de " + data.length + " O*NET-oppgavene med mest Claude-bruk blant SOC-yrkene koden er koblet til, " +
          PLATFORM_LABELS[state.taskPlatform] + ", " + vlabel(v) + ". Oppgavetekstene er O*NETs engelske formuleringer. Bare oppgaver med minst 10 klassifiserte samtaler.");
    }

    // ---- Automatisering over tid for lista ----
    function renderTid() {
      var vs = vintagesFor(state.tidPlatform);
      var series = state.occs.map(function (code, i) {
        var o = byCode[code];
        return { name: occName(o) + " (" + code + ")", type: "line", symbol: "circle", symbolSize: 7,
                 lineStyle: { width: i === 0 ? 3.2 : 2.2 }, itemStyle: { color: SLOT_COLORS[i] }, color: SLOT_COLORS[i],
                 endLabel: { show: true, formatter: trunc(occName(o), 26), fontSize: 11, color: SLOT_COLORS[i], fontWeight: 600, distance: 6 },
                 labelLayout: { moveOverlap: "shiftY" }, connectNulls: false,
                 data: vs.map(function (v) { var x = o.v[v.key]; return x && x.auto !== null ? +(x.auto * 100).toFixed(1) : null; }) };
      });
      chart("chart-y3").setOption({
        animationDuration: 300,
        grid: { left: 50, right: 200, top: 24, bottom: 44 },
        graphic: brandGraphic(SRC_AEI),
        tooltip: { trigger: "axis", valueFormatter: function (v) { return v === null ? "–" : pct(v, 1); } },
        xAxis: { type: "category", data: vs.map(vlabel), boundaryGap: false },
        yAxis: { type: "value", min: 0, max: 100, axisLabel: { formatter: function (v) { return v + " %"; } },
                 splitLine: { lineStyle: { color: "#eee" } } },
        series: series
      }, true);
      setText("y3-note", EN
        ? "Automation share (directive + feedback loop) per sample, " + PLATFORM_LABELS[state.tidPlatform] + ". The first chat point is the original Handa et al. (2025) sample; the API series starts in August 2025."
        : "Automatiseringsandel (direkte delegering + tilbakemeldingssløyfe) per utvalg, " + PLATFORM_LABELS[state.tidPlatform] + ". Det første chat-punktet er det opprinnelige utvalget fra Handa m.fl. (2025); API-serien starter i august 2025.");
    }

    // ---- De 30 stoerste ----
    function renderKpi() {
      var wsum = 0, asum = 0, k = 0;
      Y.occupations.forEach(function (o) {
        var v = o.v[state.vintage];
        if (!v || v.auto === null || !o.n) return;
        wsum += o.n; asum += o.n * v.auto; k++;
      });
      var v = vintByKey[state.vintage];
      setText("y-kpi", EN
        ? "Employment-weighted automation share, " + PLATFORM_LABELS[state.platform] + ", " + vlabel(v) + ": " + pct(asum / wsum * 100, 1) + " across " + k + " occupations with employment data."
        : "Sysselsettingsvektet automatiseringsandel, " + PLATFORM_LABELS[state.platform] + ", " + vlabel(v) + ": " + pct(asum / wsum * 100, 1) + " over " + k + " yrker med sysselsettingstall.");
    }
    function renderY1() {
      var rows = Y.occupations.filter(function (o) { return o.n && o.v[state.vintage] && o.v[state.vintage].auto !== null; })
        .sort(function (a, b) { return b.n - a.n; }).slice(0, 30);
      rows.sort(function (a, b) { return b.v[state.vintage].auto - a.v[state.vintage].auto; });
      var data = rows.map(function (o) {
        return { label: occName(o) + " (" + o.code + ")",
                 sub: (EN ? "Employees Nov 2022: " : "Lønnstakere nov. 2022: ") + thousands(o.n) +
                      (o.q ? (EN ? " · exposure quintile " : " · eksponeringskvintil ") + o.q : ""),
                 axis: trunc(occName(o), 34) + " (" + o.code + ")", v: o.v[state.vintage] };
      });
      chart("chart-y1").setOption(stackedTypeOption(data, SRC_AEI), true);
      var v = vintByKey[state.vintage];
      setText("y1-note", EN
        ? "The 30 largest occupations with data, sorted by automation share (directive + feedback loop). " + PLATFORM_LABELS[state.platform] + ", " + vlabel(v) + " (" + v.source_en + ")."
        : "De 30 største yrkene med data, sortert etter automatiseringsandel (direkte delegering + tilbakemeldingssløyfe). " + PLATFORM_LABELS[state.platform] + ", " + vlabel(v) + " (" + v.source + ").");
    }

    // ---- Chat mot API ----
    function renderY2() {
      var pts = [];
      Y.occupations.forEach(function (o) {
        var a = o.v[latestKey.claude_ai], b = o.v[latestKey.api];
        if (!a || !b || a.auto === null || b.auto === null) return;
        pts.push({ value: [a.auto * 100, b.auto * 100], o: o, symbolSize: o.n ? Math.max(6, Math.sqrt(o.n) / 5) : 6,
                   itemStyle: { color: o.q ? QUINT_COLORS[o.q - 1] : GREY, opacity: 0.8, borderColor: "#fff", borderWidth: 0.6 } });
      });
      chart("chart-y2").setOption({
        animationDuration: 300,
        grid: { left: 60, right: 30, top: 30, bottom: 60 },
        graphic: brandGraphic(SRC_AEI),
        tooltip: { formatter: function (p) {
          var o = p.data.o;
          return "<b>" + occName(o) + " (" + o.code + ")</b><br>Claude.ai: " + pct(p.value[0], 1) + "<br>API: " + pct(p.value[1], 1) +
            (o.n ? "<br>" + (EN ? "Employees: " : "Lønnstakere: ") + thousands(o.n) : "") +
            (o.q ? "<br>" + (EN ? "Exposure quintile " : "Eksponeringskvintil ") + o.q : "");
        } },
        xAxis: { name: EN ? "Automation share, Claude.ai (%)" : "Automatiseringsandel, Claude.ai (%)", nameLocation: "middle", nameGap: 28,
                 min: 0, max: 100, splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { name: EN ? "Automation share, API (%)" : "Automatiseringsandel, API (%)", nameLocation: "middle", nameGap: 42,
                 min: 0, max: 100, splitLine: { lineStyle: { color: "#eee" } } },
        series: [{ type: "scatter", data: pts,
                   markLine: { silent: true, symbol: "none", lineStyle: { type: "dashed", color: "#999" },
                               data: [[{ coord: [0, 0] }, { coord: [100, 100] }]] } }]
      }, true);
      setText("y2-note", EN
        ? "Each circle is one occupation, " + vlabel(vintByKey[latestKey.claude_ai]) + ". Circle size is private-sector employment (Nov 2022), colour is the Eloundou exposure quintile (grey: no score). Points above the dashed line are more automated in the API than in chat."
        : "Hver sirkel er ett yrke, " + vlabel(vintByKey[latestKey.claude_ai]) + ". Størrelsen er sysselsetting i privat sektor (nov. 2022), fargen er eksponeringskvintilen etter Eloundou (grå: mangler skår). Punkter over den stiplede linjen er mer automatiserte i API-et enn i chat.");
    }

    function renderAll() {
      renderChips(); renderLM(); renderCard(); renderTypes(); renderNeighbours(); renderTasks(); renderTid();
    }

    // ---- Soek ----
    function search(q) {
      q = (q || "").trim().toLowerCase();
      if (!q) return [];
      return Y.occupations.filter(function (o) {
        return o.code.indexOf(q) === 0 || (o.name || "").toLowerCase().indexOf(q) >= 0 ||
          (o.name_en || "").toLowerCase().indexOf(q) >= 0;
      }).slice(0, 12);
    }
    function renderHits(hits) {
      var ul = el("occ-hits");
      ul.innerHTML = "";
      hits.forEach(function (o) {
        var li = document.createElement("li"), b = document.createElement("button");
        b.type = "button";
        b.innerHTML = "<code>" + o.code + "</code> " + occName(o) + (o.n ? " <span class='occ-small'>(" + thousands(o.n) + ")</span>" : "");
        b.addEventListener("click", function () {
          el("occ-search").value = ""; ul.hidden = true; setFocus(o.code);
        });
        li.appendChild(b); ul.appendChild(li);
      });
      ul.hidden = !hits.length;
    }
    function download() {
      var start = Math.max(0, OCC.dates.indexOf(WINDOW_START));
      var refIdx = OCC.dates.indexOf(REF_MONTH);
      var lines = ["month;styrk08;name;employment_index;wages_index"];
      state.occs.forEach(function (code) {
        var s = OCC.byCode[code];
        if (!s) return;
        OCC.dates.slice(start).forEach(function (d, j) {
          var i = start + j;
          function idx(k) {
            var arr = s[k] && s[k].sa; if (!arr || !arr[refIdx]) return "";
            return arr[i] === null ? "" : (arr[i] / arr[refIdx] * 100).toFixed(2);
          }
          lines.push([d.slice(0, 7), code, byCode[code].name, idx("employment"), idx("wages")].join(";"));
        });
      });
      var blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "yrker_valgte.csv";
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
    }

    // ---- Oppsett ----
    var input = el("occ-search"), ul = el("occ-hits");
    input.addEventListener("input", function () { renderHits(search(input.value)); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { var f = ul.querySelector("button"); if (f) { e.preventDefault(); f.click(); } }
      else if (e.key === "Escape") ul.hidden = true;
    });
    document.addEventListener("click", function (e) {
      if (!e.target.closest || !e.target.closest(".occ-picker")) ul.hidden = true;
    });
    el("occ-random").addEventListener("click", randomOcc);
    el("occ-add-nb").addEventListener("click", addNeighbours);
    el("occ-download").addEventListener("click", download);
    makeButtons("lm-outcome-buttons", [
      { value: "employment", label: EN ? "Employment" : "Sysselsetting" },
      { value: "wages", label: EN ? "Pay (FTE)" : "Lønn (FTE)" }
    ], function () { return state.outcome; }, function (v) { state.outcome = v; renderLM(); });
    makeButtons("task-platform-buttons", ["claude_ai", "api"].map(function (p) { return { value: p, label: PLATFORM_LABELS[p] }; }),
      function () { return state.taskPlatform; }, function (p) { state.taskPlatform = p; renderTasks(); });
    makeButtons("tid-platform-buttons", ["claude_ai", "api"].map(function (p) { return { value: p, label: PLATFORM_LABELS[p] }; }),
      function () { return state.tidPlatform; }, function (p) { state.tidPlatform = p; renderTid(); });
    makeButtons("y-platform-buttons", ["claude_ai", "api"].map(function (p) { return { value: p, label: PLATFORM_LABELS[p] }; }),
      function () { return state.platform; },
      function (p) { state.platform = p; state.vintage = latestKey[p]; makeVintageButtons(); renderKpi(); renderY1(); });
    function makeVintageButtons() {
      makeButtons("y-vintage-buttons", vintagesFor(state.platform).map(function (v) { return { value: v.key, label: vlabel(v) }; }),
        function () { return state.vintage; }, function (k) { state.vintage = k; renderKpi(); renderY1(); });
    }
    makeVintageButtons();
    renderKpi(); renderY1(); renderY2();

    var fromUrl = (location.search.match(/[?&]yrke=(\d{4})/) || [])[1];
    if (fromUrl && byCode[fromUrl]) startFrom(fromUrl); else randomOcc();
  }

  // ==================================================================
  // UTDANNING
  // ==================================================================

  function initUtdanning(U) {
    var inst = U.institutions;
    var byCode = {};
    inst.forEach(function (i) { byCode[i.code] = i; });
    var VLAB = EN ? { v1: "Eloundou et al. (2024)", v2: "Mouchel et al. (2026)" }
                  : { v1: "Eloundou m.fl. (2024)", v2: "Mouchel m.fl. (2026)" };
    function QLAB(i) {
      return EN ? ["Q1 (least exposed)", "Q2", "Q3", "Q4", "Q5 (most exposed)"][i]
                : ["K1 (minst eksponert)", "K2", "K3", "K4", "K5 (mest eksponert)"][i];
    }
    var FIELDS = U.national.fields.map(function (f) { return f.group; })
      .filter(function (f) { return f.indexOf("Uoppgitt") < 0; });
    var LEVELS = ["Bachelor-nivå", "Master-nivå", "Ph.d.", "Påbygging/fagskole", "Videregående avsluttende"];
    var LEVEL_EN = { "Bachelor-nivå": "Bachelor level", "Master-nivå": "Master level", "Ph.d.": "PhD",
                     "Påbygging/fagskole": "Vocational college", "Videregående avsluttende": "Upper secondary" };
    function levelLab(l) { return EN ? (LEVEL_EN[l] || l) : l; }
    var state = { version: "v1", field: "Økonomiske og administrative fag", level: "Bachelor-nivå",
                  inst: inst[0].code, cohort: "all" };
    function ver(o, key) { return o[key + "_" + state.version]; }

    // ---- Fagfelt x nivaa, nasjonalt ----
    function natRow() {
      return U.national.field_level.filter(function (r) { return r.field === state.field && r.level === state.level; })[0];
    }
    function renderFieldLevel() {
      var r = natRow(), box = el("u-fl-card");
      var fl = [];
      inst.forEach(function (i) {
        i.field_level.forEach(function (x) {
          if (x.field === state.field && x.level === state.level && x.n > 0) fl.push({ inst: i, x: x });
        });
      });
      fl.sort(function (a, b) { return b.x.n - a.x.n; });
      var grads = fl.reduce(function (s, p) { return s + p.x.n; }, 0);
      if (!r) {
        box.innerHTML = "<p class='chart-footnote'>" + (EN ? "No register data for this combination." : "Ingen registerdata for denne kombinasjonen.") + "</p>";
        el("u-fl-table").innerHTML = "";
        chart("chart-u-fl-inst").clear();
        return;
      }
      function metric(label, value) { return "<div class='pick-metric'><strong>" + value + "</strong>" + label + "</div>"; }
      box.innerHTML = "<h3>" + state.field + " · " + levelLab(state.level) + "</h3>" +
        "<p class='pick-sub'>" + (EN ? "National register, residents 20–70 with this as highest completed education (Nov 2024): "
                                      : "Nasjonalt register, bosatte 20–70 år med dette som høyeste fullførte utdanning (nov. 2024): ") +
        thousands(r.n_total) + (EN ? " persons in " : " personer i ") + r.n_codes + (EN ? " education codes." : " utdanningskoder.") + "</p>" +
        "<div class='pick-metrics'>" +
        metric(EN ? "Employed" : "Sysselsatte", pct(r.share_employed * 100, 0)) +
        metric(EN ? "Mean exposure, " + VLAB[state.version] : "Snitt-eksponering, " + VLAB[state.version], num(ver(r, "exposure"), 2)) +
        metric(EN ? "Share in most exposed quintile" : "Andel i mest eksponerte kvintil", pct(ver(r, "q5") * 100, 0)) +
        metric(EN ? "Augmentation share of use (Handa)" : "Augmenteringsandel av bruken (Handa)", r.handa_aug === null ? "–" : pct(r.handa_aug * 100, 0)) +
        metric(EN ? "Institutions offering it" : "Institusjoner som tilbyr", String(fl.length)) +
        metric(EN ? "Graduates " + U.year : "Kandidater " + U.year, thousands(grads)) +
        "</div>";
      var top = r.top || [];
      var h = "<table class='data-table'><thead><tr><th>#</th><th>" + (EN ? "Occupation (STYRK-08)" : "Yrke (STYRK-08)") +
        "</th><th class='num'>" + (EN ? "Share of employed" : "Andel av sysselsatte") + "</th><th>" + (EN ? "Quintile" : "Kvintil") + "</th></tr></thead><tbody>";
      top.forEach(function (t) {
        var q = t["q_" + state.version];
        h += "<tr><td>" + t.rank + "</td><td>" + t.name + " <code>" + t.code + "</code></td><td class='num'>" + pct(t.share * 100, 1) + "</td><td>" + qBadge(q) + "</td></tr>";
      });
      h += "</tbody></table>";
      el("u-fl-table").innerHTML = h;

      var rows = fl.slice(0, 20);
      sizeChart("chart-u-fl-inst", Math.max(200, 80 + rows.length * 26));
      var c = chart("chart-u-fl-inst");
      c.setOption({
        animationDuration: 300,
        grid: { left: 90, right: 70, top: 10, bottom: 40 },
        graphic: brandGraphic(SRC_EDU),
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: function (ps) {
          var p = rows[ps[0].dataIndex];
          return "<b>" + p.inst.name + "</b><br>" + (EN ? "Graduates " : "Kandidater ") + U.year + ": " + thousands(p.x.n) +
            "<br>" + (EN ? "Programmes: " : "Programmer: ") + p.x.programmes +
            "<br>" + (EN ? "Mean exposure: " : "Snitt-eksponering: ") + num(ver(p.x, "exposure"), 2) +
            "<br>" + (EN ? "Share in Q5: " : "Andel i K5: ") + pct(ver(p.x, "q5") * 100, 0);
        } },
        xAxis: { type: "value", splitLine: { lineStyle: { color: "#eee" } }, name: EN ? "Graduates " + U.year : "Kandidater " + U.year,
                 nameLocation: "middle", nameGap: 26 },
        yAxis: { type: "category", inverse: true, axisTick: { show: false }, data: rows.map(function (p) { return p.inst.short; }) },
        series: [{ type: "bar", barMaxWidth: 18, itemStyle: { color: function (p) { return rows[p.dataIndex].inst.code === state.inst ? QUINT_COLORS[3] : QUINT_COLORS[0]; } },
                   label: { show: true, position: "right", fontSize: 11, formatter: function (p) { return thousands(p.value) + "  ·  " + num(ver(rows[p.dataIndex].x, "exposure"), 2); } },
                   data: rows.map(function (p) { return p.x.n; }) }]
      }, true);
      setText("u-fl-note", EN
        ? "Institutions by graduates in " + state.field + ", " + levelLab(state.level) + ", " + U.year + ". The number after the dot is the institution's mean exposure for these graduates (" + VLAB[state.version] + "). Red: the institution chosen below."
        : "Institusjoner etter kandidater i " + state.field + ", " + levelLab(state.level) + ", " + U.year + ". Tallet etter punktet er institusjonens snitt-eksponering for disse kandidatene (" + VLAB[state.version] + "). Rødt: institusjonen valgt under.");
    }

    // ---- Institusjon ----
    function renderInst() {
      var i = byCode[state.inst], box = el("u-inst-card");
      function metric(label, value, extra) { return "<div class='pick-metric'><strong>" + value + "</strong>" + label + (extra ? " " + extra : "") + "</div>"; }
      var first = i.trend[0], last = i.trend[i.trend.length - 1];
      box.innerHTML = "<h3>" + i.name + "</h3>" +
        "<p class='pick-sub'>" + i.type + " · " + (EN ? "graduates " : "kandidater ") + i.year + ": " + thousands(i.graduates) +
        (i.phd ? " (" + (EN ? "of which PhD " : "hvorav ph.d. ") + thousands(i.phd) + ")" : "") +
        " · " + (EN ? "registered students autumn " : "registrerte studenter høst ") + i.year + ": " + thousands(i.students) +
        " · " + i.programmes + (EN ? " programmes" : " programmer") + "</p>" +
        "<div class='pick-metrics'>" +
        metric(EN ? "Mean exposure, " + VLAB[state.version] : "Snitt-eksponering, " + VLAB[state.version], num(ver(i, "exposure"), 2)) +
        metric(EN ? "Share in most exposed quintile" : "Andel i mest eksponerte kvintil", pct(ver(i, "q")[4] * 100, 0)) +
        metric(EN ? "Bachelor / master / PhD" : "Bachelor / master / ph.d.", pct(i.share_bachelor * 100, 0) + " / " + pct(i.share_master * 100, 0) + " / " + pct(i.share_phd * 100, 0)) +
        metric(EN ? "Employed among graduates' educations" : "Sysselsatte blant kandidatenes utdanninger", pct(i.share_employed * 100, 0)) +
        metric(EN ? "Graduates " + first.year + " → " + last.year : "Kandidater " + first.year + " → " + last.year, thousands(first.graduates) + " → " + thousands(last.graduates)) +
        metric(EN ? "Programme rows with a profile" : "Programrader med profil", pct(i.coverage * 100, 0)) +
        "</div>" +
        "<p class='pick-sub'>" + (EN ? "Largest fields: " : "Største fagfelt: ") +
        i.fields.slice(0, 3).map(function (f) { return f.field + " (" + pct(f.share * 100, 0) + ")"; }).join(", ") + ".</p>";

      var rows = i.field_level.filter(function (x) { return x.n > 0; });
      var h = "<table class='data-table'><thead><tr><th>" + (EN ? "Field" : "Fagfelt") + "</th><th>" + (EN ? "Level" : "Nivå") +
        "</th><th class='num'>" + (EN ? "Graduates" : "Kandidater") + "</th><th class='num'>" + (EN ? "Exposure" : "Eksponering") +
        "</th><th class='num'>" + (EN ? "In Q5" : "I K5") + "</th><th>" + (EN ? "Typical occupations" : "Typiske yrker") + "</th></tr></thead><tbody>";
      rows.forEach(function (x) {
        h += "<tr><td>" + x.field + "</td><td>" + levelLab(x.level) + "</td><td class='num'>" + thousands(x.n) + "</td><td class='num'>" +
          num(ver(x, "exposure"), 2) + "</td><td class='num'>" + (ver(x, "q5") === null ? "–" : pct(ver(x, "q5") * 100, 0)) + "</td><td>" + x.top + "</td></tr>";
      });
      h += "</tbody></table>";
      el("u-inst-fl-table").innerHTML = h;
      renderTopTable();
    }
    function renderTopTable() {
      var i = byCode[state.inst];
      var rows = (i.top_occ[state.cohort] || []).slice(0, 10);
      var qk = "q_" + state.version;
      var h = "<table class='data-table'><thead><tr><th>#</th><th>" + (EN ? "Occupation (STYRK-08)" : "Yrke (STYRK-08)") +
        "</th><th class='num'>" + (EN ? "Share" : "Andel") + "</th><th>" + (EN ? "Quintile" : "Kvintil") + "</th></tr></thead><tbody>";
      rows.forEach(function (r) {
        h += "<tr><td>" + r.rank + "</td><td>" + r.name + " <code>" + r.code + "</code></td><td class='num'>" + pct(r.share * 100, 1) + "</td><td>" + qBadge(r[qk]) + "</td></tr>";
      });
      h += "</tbody></table>";
      el("u-top-table").innerHTML = h;
      setText("u-table-note", EN
        ? i.name + ": the ten most common occupations among " + (state.cohort === "all" ? "everyone" : "recent graduates (1–3 years)") +
          " in Norway with the same educations, weighted by the institution's " + U.year + " graduates. Quintile: " + VLAB[state.version] + "."
        : i.name + ": de ti vanligste yrkene blant " + (state.cohort === "all" ? "alle" : "nyutdannede (1–3 år)") +
          " i Norge med de samme utdanningene, vektet med institusjonens kandidater " + U.year + ". Kvintil: " + VLAB[state.version] + ".");
    }

    // ---- Oversikt: alle institusjoner ----
    function rowHeight(n) { return Math.max(300, 70 + n * 24); }
    function renderU1() {
      var sorted = inst.slice().sort(function (a, b) { return a.exposure_v1 - b.exposure_v1; });
      sizeChart("chart-u1", rowHeight(sorted.length));
      var c = chart("chart-u1");
      c.setOption({
        animationDuration: 300,
        grid: { left: 80, right: 40, top: 40, bottom: 64 },
        graphic: brandGraphic(SRC_EDU),
        legend: { top: 4, left: 80, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11 } },
        tooltip: { trigger: "axis", formatter: function (ps) {
          var i = sorted[ps[0].dataIndex];
          return "<b>" + i.name + "</b><br>" + VLAB.v1 + ": " + num(i.exposure_v1, 3) + "<br>" + VLAB.v2 + ": " + num(i.exposure_v2, 3) +
            "<br>" + (EN ? "Graduates: " : "Kandidater: ") + thousands(i.graduates);
        } },
        xAxis: { type: "value", min: 0.25, max: 0.7, name: EN ? "Mean exposure (0–1)" : "Snitt-eksponering (0–1)", nameLocation: "middle", nameGap: 34,
                 splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { type: "category", data: sorted.map(function (i) { return i.short; }), axisTick: { show: false }, axisLabel: { fontSize: 11 } },
        series: [
          { name: VLAB.v1, type: "scatter", symbolSize: 11, itemStyle: { color: QUINT_COLORS[3] }, data: sorted.map(function (i) { return i.exposure_v1; }) },
          { name: VLAB.v2, type: "scatter", symbolSize: 11, itemStyle: { color: QUINT_COLORS[0] }, data: sorted.map(function (i) { return i.exposure_v2; }) }
        ]
      }, true);
    }
    function renderU2() {
      var key = "q_" + state.version;
      var sorted = inst.slice().sort(function (a, b) { return b[key][4] - a[key][4]; });
      sizeChart("chart-u2", rowHeight(sorted.length));
      var c = chart("chart-u2");
      c.setOption({
        animationDuration: 300,
        grid: { left: 80, right: 30, top: 44, bottom: 40 },
        graphic: brandGraphic(SRC_EDU),
        legend: { top: 4, left: 80, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11 } },
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: function (v) { return pct(v, 1); } },
        xAxis: { type: "value", max: 100, axisLabel: { formatter: function (v) { return v + " %"; } }, splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { type: "category", inverse: true, axisTick: { show: false }, data: sorted.map(function (i) { return i.short; }), axisLabel: { fontSize: 11 } },
        series: [0, 1, 2, 3, 4].map(function (q) {
          return { name: QLAB(q), type: "bar", stack: "q", barMaxWidth: 18, itemStyle: { color: QUINT_COLORS[q] },
                   label: { show: q === 4, position: "insideRight", color: "#fff", fontSize: 10, formatter: function (p) { return num(p.value, 0) + " %"; } },
                   data: sorted.map(function (i) { return i[key][q] * 100; }) };
        })
      }, true);
      setText("u2-note", EN
        ? "Share of each institution's " + U.year + " graduates (weighted by programme) whose typical occupations fall in each exposure quintile, " + VLAB[state.version] + ". Sorted by the most exposed quintile."
        : "Andel av hver institusjons kandidater " + U.year + " (vektet per program) som typisk går til yrker i hver eksponeringskvintil, " + VLAB[state.version] + ". Sortert etter mest eksponerte kvintil.");
    }
    function renderU3() {
      var k = "q5_" + state.version, e = "exposure_" + state.version;
      var rows = U.national.fields.filter(function (f) { return f.group.indexOf("Uoppgitt") < 0; }).sort(function (a, b) { return b[k] - a[k]; });
      chart("chart-u3").setOption({
        animationDuration: 300,
        grid: { left: 250, right: 40, top: 30, bottom: 64 },
        graphic: brandGraphic(SRC_EDU),
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: function (ps) {
          var f = rows[ps[0].dataIndex];
          return "<b>" + f.group + "</b><br>" + (EN ? "Share in Q5: " : "Andel i K5: ") + pct(f[k] * 100, 1) + "<br>" +
            (EN ? "Mean exposure: " : "Snitt-eksponering: ") + num(f[e], 3) + "<br>" + (EN ? "Employed: " : "Sysselsatte: ") + thousands(f.n_employed);
        } },
        xAxis: { type: "value", max: 100, axisLabel: { formatter: function (v) { return v + " %"; } },
                 name: EN ? "Share of employed in the most exposed quintile" : "Andel sysselsatte i mest eksponerte kvintil", nameLocation: "middle", nameGap: 34,
                 splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { type: "category", inverse: true, axisTick: { show: false }, data: rows.map(function (f) { return f.group; }),
                 axisLabel: { fontSize: 11, width: 234, overflow: "truncate" } },
        series: [{ type: "bar", barMaxWidth: 22, itemStyle: { color: QUINT_COLORS[4] },
                   label: { show: true, position: "right", fontSize: 11, formatter: function (p) { return num(p.value, 0) + " %"; } },
                   data: rows.map(function (f) { return f[k] * 100; }) }]
      }, true);
      setText("u3-note", EN
        ? "All employed residents 20–70 by field of their highest completed education (utdanning.no register link, Nov 2024), " + VLAB[state.version] + "."
        : "Alle sysselsatte bosatte 20–70 år etter fagfeltet til høyeste fullførte utdanning (utdanning.no-registerkobling, nov. 2024), " + VLAB[state.version] + ".");
    }
    function renderKpi() {
      var top = inst.slice().sort(function (a, b) { return b.exposure_v1 - a.exposure_v1; });
      setText("u-kpi", EN
        ? U.n_institutions + " institutions with at least " + U.min_graduates + " graduates in " + U.year + ". Highest mean exposure: " + top[0].short + " (" + num(top[0].exposure_v1, 2) + "), lowest: " + top[top.length - 1].short + " (" + num(top[top.length - 1].exposure_v1, 2) + ")."
        : U.n_institutions + " institusjoner med minst " + U.min_graduates + " kandidater i " + U.year + ". Høyest snitt-eksponering: " + top[0].short + " (" + num(top[0].exposure_v1, 2) + "), lavest: " + top[top.length - 1].short + " (" + num(top[top.length - 1].exposure_v1, 2) + ").");
    }

    // ---- Oppsett ----
    makeButtons("u-field-buttons", FIELDS.map(function (f) { return { value: f, label: f }; }),
      function () { return state.field; }, function (v) { state.field = v; renderFieldLevel(); });
    makeButtons("u-level-buttons", LEVELS.map(function (l) { return { value: l, label: levelLab(l) }; }),
      function () { return state.level; }, function (v) { state.level = v; renderFieldLevel(); });
    var sel = el("u-inst-select");
    inst.forEach(function (i) {
      var o = document.createElement("option");
      o.value = i.code; o.textContent = i.name + " (" + thousands(i.graduates) + ")";
      sel.appendChild(o);
    });
    sel.value = state.inst;
    sel.addEventListener("change", function () { state.inst = sel.value; renderInst(); renderFieldLevel(); });
    makeButtons("u-cohort-buttons", [{ value: "all", label: EN ? "All" : "Alle" }, { value: "recent", label: EN ? "Recent graduates" : "Nyutdannede" }],
      function () { return state.cohort; }, function (v) { state.cohort = v; renderTopTable(); });
    makeButtons("u-version-buttons", ["v1", "v2"].map(function (v) { return { value: v, label: VLAB[v] }; }),
      function () { return state.version; }, function (v) { state.version = v; renderFieldLevel(); renderInst(); renderU2(); renderU3(); });

    var fromUrl = (location.search.match(/[?&]inst=(\d{4})/) || [])[1];
    if (fromUrl && byCode[fromUrl]) { state.inst = fromUrl; sel.value = fromUrl; }
    renderKpi(); renderFieldLevel(); renderInst(); renderU1(); renderU2(); renderU3();
  }

  // ---------- Oppstart ----------

  initToc();
  function getJSON(name) {
    return fetch("/data/" + name + ".json?v=" + V).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status + " (" + name + ")");
      return r.json();
    });
  }
  if (PANEL === "yrker") {
    Promise.all([getJSON("yrker"), getJSON("occupations")])
      .then(function (d) { initYrker(d[0], d[1]); }).catch(fail);
  } else if (PANEL === "utdanning") {
    getJSON("utdanning").then(initUtdanning).catch(fail);
  }
})();
