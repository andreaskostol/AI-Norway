/* Arbeidsmarkedet — panelene ved siden av KI-indeksen: Yrker, Utdanning og
   KI-bruk per land. Ett script for alle tre; <body data-panel="..."> sier
   hvilket panel som skal tegnes, og <html lang> styrer språket slik at samme
   fil betjener / og /en/. Data: public/data/yrker.json, utdanning.json og
   bruk.json, bygget av prepare_panels.py. Figurstilen følger app.js
   (Canaries-palett, kildelinje nederst til venstre). */

(function () {
  "use strict";

  var EN = (document.documentElement.lang || "nb")
             .toLowerCase().indexOf("en") === 0;
  var PANEL = document.body.getAttribute("data-panel");
  var V = "20260907a";

  // ---------- Farger og etiketter ----------

  // Kvintilpaletten fra app.js: kaldt (minst eksponert) til varmt.
  var QUINT_COLORS = ["#577590", "#E6A817", "#E54A2B", "#8C1515", "#401415"];
  var GREY = "#b8b4ab";
  // Anthropics fem interaksjonstyper. De to automatiserende er varme, de
  // tre augmenterende er kalde, så en stolpe leses fra venstre: rødt er
  // automatisering, blått/gult er augmentering.
  var TYPES = ["d", "fb", "ti", "va", "le"];
  var TYPE_COLORS = { d: "#401415", fb: "#E54A2B", ti: "#E6A817",
                      va: "#577590", le: "#2b3e50" };
  var TYPE_LABELS = EN
    ? { d: "Directive", fb: "Feedback loop", ti: "Task iteration",
        va: "Validation", le: "Learning" }
    : { d: "Direkte delegering", fb: "Tilbakemeldingssløyfe",
        ti: "Oppgaveiterasjon", va: "Validering", le: "Læring" };
  var PLATFORM_LABELS = EN
    ? { claude_ai: "Claude.ai (chat)", api: "API (developers, agents)" }
    : { claude_ai: "Claude.ai (chat)", api: "API (utviklere, agenter)" };

  var BRAND = "kiindeksen.no  ·  Hernæs & Kostøl";
  function brandGraphic(src) {
    return [{
      type: "text", left: 10, bottom: 2, silent: true,
      style: { text: BRAND + "  ·  " + src, fontSize: 10, fill: "#a39f95" }
    }];
  }
  var SRC_AEI = EN
    ? "Source: Anthropic Economic Index, mapped to STYRK-08 via O*NET/SOC/ISCO"
    : "Kilde: Anthropic Economic Index, koblet til STYRK-08 via O*NET/SOC/ISCO";
  var SRC_EDU = EN
    ? "Source: DBH (HK-dir), utdanning.no register link, Eloundou et al. (2024), Mouchel et al. (2026)"
    : "Kilde: DBH (HK-dir), utdanning.no-registerkobling, Eloundou m.fl. (2024), Mouchel m.fl. (2026)";
  var SRC_USE = EN
    ? "Source: Anthropic Economic Index, country files"
    : "Kilde: Anthropic Economic Index, landfiler";

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
  function trunc(s, n) {
    s = s || "";
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  }
  function el(id) { return document.getElementById(id); }
  function setText(id, s) { var e = el(id); if (e) e.textContent = s; }
  function occName(o) { return EN && o.name_en ? o.name_en : o.name; }

  // Knapperad som i app.js: en aktiv knapp, resten passive.
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
          c.className = c.getAttribute("data-value") === String(get())
            ? "active" : "";
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
  window.addEventListener("resize", function () {
    Object.keys(CHARTS).forEach(function (k) { CHARTS[k].resize(); });
  });

  // Enkel scrollspy for innholdsfortegnelsen til venstre.
  function initToc() {
    var links = Array.prototype.slice.call(
      document.querySelectorAll("#toc-nav a[href^='#']"));
    if (!links.length) return;
    var targets = links.map(function (a) {
      return el(a.getAttribute("href").slice(1));
    });
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
    if (e) e.textContent = (EN ? "Could not load the data (" : "Kunne ikke laste dataene (")
      + err.message + ").";
  }

  // Stablet 100 %-stolpe med de fem typene, én rad per element.
  function stackedTypeOption(rows, src, opts) {
    opts = opts || {};
    var series = TYPES.map(function (t) {
      return {
        name: TYPE_LABELS[t], type: "bar", stack: "s",
        itemStyle: { color: TYPE_COLORS[t] },
        emphasis: { focus: "series" },
        barMaxWidth: 22,
        data: rows.map(function (r) { return r.v[t] === null ? 0 : r.v[t] * 100; })
      };
    });
    return {
      animationDuration: 300,
      grid: { left: opts.left || 250, right: 30, top: 44, bottom: 40 },
      graphic: brandGraphic(src),
      legend: { top: 4, left: opts.left || 250, itemWidth: 12, itemHeight: 10,
                textStyle: { fontSize: 11 } },
      tooltip: {
        trigger: "axis", axisPointer: { type: "shadow" },
        formatter: function (ps) {
          var r = rows[ps[0].dataIndex];
          var s = "<b>" + r.label + "</b>";
          if (r.sub) s += "<br><span style='color:#777'>" + r.sub + "</span>";
          ps.forEach(function (p) {
            s += "<br>" + p.marker + p.seriesName + ": " + pct(p.value, 1);
          });
          if (r.v.n) s += "<br><span style='color:#777'>" +
            (EN ? "Classified conversations: " : "Klassifiserte samtaler: ") +
            thousands(r.v.n) + "</span>";
          return s;
        }
      },
      xAxis: { type: "value", max: 100, axisLabel: { formatter: function (v) { return v + " %"; } },
               splitLine: { lineStyle: { color: "#eee" } } },
      yAxis: { type: "category", inverse: true,
               data: rows.map(function (r) { return r.axis; }),
               axisLabel: { fontSize: 11, width: (opts.left || 250) - 16,
                            overflow: "truncate" },
               axisTick: { show: false } },
      series: series
    };
  }

  // ==================================================================
  // YRKER
  // ==================================================================

  function initYrker(Y) {
    var byCode = {};
    Y.occupations.forEach(function (o) { byCode[o.code] = o; });
    var vint = Y.vintages;
    function vintagesFor(p) {
      return vint.filter(function (v) { return v.platform === p; });
    }
    var latestKey = { claude_ai: vintagesFor("claude_ai").slice(-1)[0].key,
                      api: vintagesFor("api").slice(-1)[0].key };
    var state = {
      platform: "claude_ai",
      vintage: latestKey.claude_ai,
      occs: ["2512", "4110", "2411", "3322", "5223", "2211"].filter(function (c) {
        return byCode[c];
      }),
      taskOcc: null,
      taskPlatform: "claude_ai"
    };
    state.taskOcc = state.occs[0];
    var OCC_MAX = 6;
    var vintByKey = {};
    vint.forEach(function (v) { vintByKey[v.key] = v; });
    function vlabel(v) { return EN ? v.label_en : v.label; }

    // ---- Nøkkeltall: sysselsettingsvektet automatiseringsandel ----
    function renderKpi() {
      var wsum = 0, asum = 0, k = 0;
      Y.occupations.forEach(function (o) {
        var v = o.v[state.vintage];
        if (!v || v.auto === null || !o.n) return;
        wsum += o.n; asum += o.n * v.auto; k++;
      });
      var v = vintByKey[state.vintage];
      setText("y-kpi", EN
        ? "Employment-weighted automation share, " + PLATFORM_LABELS[state.platform] +
          ", " + vlabel(v) + ": " + pct(asum / wsum * 100, 1) + " across " + k +
          " occupations with employment data."
        : "Sysselsettingsvektet automatiseringsandel, " + PLATFORM_LABELS[state.platform] +
          ", " + vlabel(v) + ": " + pct(asum / wsum * 100, 1) + " over " + k +
          " yrker med sysselsettingstall.");
    }

    // ---- Figur 1: de 30 største yrkene, stablet etter type ----
    function renderY1() {
      var rows = Y.occupations.filter(function (o) {
        return o.n && o.v[state.vintage] && o.v[state.vintage].auto !== null;
      }).sort(function (a, b) { return b.n - a.n; }).slice(0, 30);
      rows.sort(function (a, b) {
        return b.v[state.vintage].auto - a.v[state.vintage].auto;
      });
      var data = rows.map(function (o) {
        return { label: occName(o) + " (" + o.code + ")",
                 sub: (EN ? "Employees Nov 2022: " : "Lønnstakere nov. 2022: ") + thousands(o.n) +
                      (o.q ? (EN ? " · exposure quintile " : " · eksponeringskvintil ") + o.q : ""),
                 axis: trunc(occName(o), 34) + " (" + o.code + ")",
                 v: o.v[state.vintage] };
      });
      chart("chart-y1").setOption(stackedTypeOption(data, SRC_AEI), true);
      var v = vintByKey[state.vintage];
      setText("y1-note", EN
        ? "The 30 largest occupations with data, sorted by automation share (directive + feedback loop). " +
          PLATFORM_LABELS[state.platform] + ", " + vlabel(v) + " (" + (v.source_en || v.source) + ")."
        : "De 30 største yrkene med data, sortert etter automatiseringsandel (direkte delegering + tilbakemeldingssløyfe). " +
          PLATFORM_LABELS[state.platform] + ", " + vlabel(v) + " (" + v.source + ").");
    }

    // ---- Figur 2: alle yrker, Claude.ai mot API ----
    function renderY2() {
      var pts = [];
      Y.occupations.forEach(function (o) {
        var a = o.v[latestKey.claude_ai], b = o.v[latestKey.api];
        if (!a || !b || a.auto === null || b.auto === null) return;
        pts.push({ value: [a.auto * 100, b.auto * 100], o: o,
                   symbolSize: o.n ? Math.max(6, Math.sqrt(o.n) / 5) : 6,
                   itemStyle: { color: o.q ? QUINT_COLORS[o.q - 1] : GREY,
                                opacity: 0.8, borderColor: "#fff", borderWidth: 0.6 } });
      });
      var c = chart("chart-y2");
      c.setOption({
        animationDuration: 300,
        grid: { left: 60, right: 30, top: 30, bottom: 60 },
        graphic: brandGraphic(SRC_AEI),
        tooltip: {
          formatter: function (p) {
            var o = p.data.o;
            return "<b>" + occName(o) + " (" + o.code + ")</b><br>" +
              "Claude.ai: " + pct(p.value[0], 1) + "<br>API: " + pct(p.value[1], 1) +
              (o.n ? "<br>" + (EN ? "Employees: " : "Lønnstakere: ") + thousands(o.n) : "") +
              (o.q ? "<br>" + (EN ? "Exposure quintile " : "Eksponeringskvintil ") + o.q : "");
          }
        },
        xAxis: { name: EN ? "Automation share, Claude.ai (%)" : "Automatiseringsandel, Claude.ai (%)",
                 nameLocation: "middle", nameGap: 28, min: 0, max: 100,
                 splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { name: EN ? "Automation share, API (%)" : "Automatiseringsandel, API (%)",
                 nameLocation: "middle", nameGap: 42, min: 0, max: 100,
                 splitLine: { lineStyle: { color: "#eee" } } },
        series: [{
          type: "scatter", data: pts,
          markLine: { silent: true, symbol: "none",
                      lineStyle: { type: "dashed", color: "#999" },
                      data: [[{ coord: [0, 0] }, { coord: [100, 100] }]] }
        }]
      }, true);
      setText("y2-note", EN
        ? "Each circle is one occupation, " + vlabel(vintByKey[latestKey.claude_ai]) +
          ". Circle size is private-sector employment (Nov 2022), colour is the Eloundou exposure quintile (grey: no score). Points above the dashed line are more automated in the API than in chat."
        : "Hver sirkel er ett yrke, " + vlabel(vintByKey[latestKey.claude_ai]) +
          ". Størrelsen er sysselsetting i privat sektor (nov. 2022), fargen er eksponeringskvintilen etter Eloundou (grå: mangler skår). Punkter over den stiplede linjen er mer automatiserte i API-et enn i chat.");
    }

    // ---- Figur 3: valgte yrker over tid ----
    function renderY3() {
      var vs = vintagesFor(state.platform);
      var series = state.occs.map(function (code, i) {
        var o = byCode[code];
        return {
          name: occName(o) + " (" + code + ")", type: "line",
          symbol: "circle", symbolSize: 7, lineStyle: { width: 2.4 },
          itemStyle: { color: QUINT_COLORS[i % 5] },
          color: QUINT_COLORS[i % 5],
          endLabel: { show: true, formatter: trunc(occName(o), 26), fontSize: 11,
                      color: QUINT_COLORS[i % 5], fontWeight: 600, distance: 6 },
          labelLayout: { moveOverlap: "shiftY" },
          connectNulls: false,
          data: vs.map(function (v) {
            var x = o.v[v.key];
            return x && x.auto !== null ? +(x.auto * 100).toFixed(1) : null;
          })
        };
      });
      chart("chart-y3").setOption({
        animationDuration: 300,
        grid: { left: 50, right: 200, top: 24, bottom: 44 },
        graphic: brandGraphic(SRC_AEI),
        tooltip: { trigger: "axis",
                   valueFormatter: function (v) { return v === null ? "–" : pct(v, 1); } },
        xAxis: { type: "category", data: vs.map(vlabel), boundaryGap: false },
        yAxis: { type: "value", min: 0, max: 100,
                 axisLabel: { formatter: function (v) { return v + " %"; } },
                 splitLine: { lineStyle: { color: "#eee" } } },
        series: series
      }, true);
      setText("y3-note", EN
        ? "Automation share per vintage, " + PLATFORM_LABELS[state.platform] +
          ". The first Claude.ai point is the original Handa et al. (2025) sample; the API series starts in August 2025."
        : "Automatiseringsandel per årgang, " + PLATFORM_LABELS[state.platform] +
          ". Det første Claude.ai-punktet er det opprinnelige utvalget fra Handa m.fl. (2025); API-serien starter i august 2025.");
    }

    // ---- Figur 4: oppgavene i ett valgt yrke ----
    function renderY4() {
      var o = byCode[state.taskOcc];
      var tasks = o ? (o.tasks[state.taskPlatform] || []) : [];
      var data = tasks.map(function (t) {
        return { label: t.t, sub: "SOC " + t.soc + " · " +
                   (EN ? "share of all conversations " : "andel av alle samtaler ") + num(t.pct, 3) + " %",
                 axis: trunc(t.t, 70), v: t };
      });
      var c = chart("chart-y4");
      if (!data.length) {
        c.clear();
        setText("y4-note", EN
          ? "No task-level data for this occupation on this platform."
          : "Ingen oppgavedata for dette yrket på denne plattformen.");
        return;
      }
      c.setOption(stackedTypeOption(data, SRC_AEI, { left: 430 }), true);
      c.resize({ height: Math.max(300, 60 + data.length * 30) });
      var v = vintByKey[latestKey[state.taskPlatform]];
      setText("y4-note", EN
        ? occName(o) + " (" + o.code + "): the " + data.length +
          " O*NET tasks with most Claude use among the SOC occupations this code maps to, " +
          PLATFORM_LABELS[state.taskPlatform] + ", " + vlabel(v) +
          ". Task texts are O*NET's English statements. Only tasks with at least 10 classified conversations are listed."
        : occName(o) + " (" + o.code + "): de " + data.length +
          " O*NET-oppgavene med mest Claude-bruk blant SOC-yrkene koden er koblet til, " +
          PLATFORM_LABELS[state.taskPlatform] + ", " + vlabel(v) +
          ". Oppgavetekstene er O*NETs engelske formuleringer. Bare oppgaver med minst 10 klassifiserte samtaler er med.");
    }

    // ---- Yrkesvelger: søk, treff, chips ----
    function search(q) {
      q = (q || "").trim().toLowerCase();
      if (!q) return [];
      return Y.occupations.filter(function (o) {
        return o.code.indexOf(q) === 0 ||
          (o.name || "").toLowerCase().indexOf(q) >= 0 ||
          (o.name_en || "").toLowerCase().indexOf(q) >= 0;
      }).slice(0, 12);
    }
    function renderHits(hits) {
      var ul = el("occ-hits");
      ul.innerHTML = "";
      hits.forEach(function (o) {
        var li = document.createElement("li");
        var b = document.createElement("button");
        b.type = "button";
        b.innerHTML = "<code>" + o.code + "</code> " + occName(o) +
          (o.n ? " <span class='occ-small'>(" + thousands(o.n) + ")</span>" : "");
        b.addEventListener("click", function () {
          if (state.occs.indexOf(o.code) < 0) {
            state.occs.push(o.code);
            if (state.occs.length > OCC_MAX) state.occs.shift();
          }
          state.taskOcc = o.code;
          el("occ-search").value = "";
          ul.hidden = true;
          occChanged();
        });
        li.appendChild(b);
        ul.appendChild(li);
      });
      ul.hidden = !hits.length;
    }
    function renderChips() {
      var box = el("occ-chips");
      box.innerHTML = "";
      state.occs.forEach(function (code, i) {
        var o = byCode[code];
        var chip = document.createElement("span");
        chip.className = "occ-chip";
        chip.innerHTML = "<i style='background:" + QUINT_COLORS[i % 5] + "'></i>" +
          "<code>" + code + "</code> " + occName(o);
        var x = document.createElement("button");
        x.type = "button"; x.textContent = "×";
        x.setAttribute("aria-label", EN ? "Remove" : "Fjern");
        x.addEventListener("click", function () {
          state.occs = state.occs.filter(function (c) { return c !== code; });
          if (state.taskOcc === code) state.taskOcc = state.occs[0] || null;
          occChanged();
        });
        chip.appendChild(x);
        box.appendChild(chip);
      });
    }
    function occChanged() {
      renderChips();
      renderY3();
      makeButtons("task-occ-buttons", state.occs.map(function (c) {
        return { value: c, label: trunc(occName(byCode[c]), 24) + " (" + c + ")" };
      }), function () { return state.taskOcc; },
      function (v) { state.taskOcc = v; renderY4(); });
      renderY4();
    }

    // ---- Oppsett ----
    makeButtons("y-platform-buttons",
      ["claude_ai", "api"].map(function (p) { return { value: p, label: PLATFORM_LABELS[p] }; }),
      function () { return state.platform; },
      function (p) {
        state.platform = p; state.vintage = latestKey[p];
        makeVintageButtons(); renderKpi(); renderY1(); renderY3();
      });
    function makeVintageButtons() {
      makeButtons("y-vintage-buttons", vintagesFor(state.platform).map(function (v) {
        return { value: v.key, label: vlabel(v) };
      }), function () { return state.vintage; },
      function (k) { state.vintage = k; renderKpi(); renderY1(); });
    }
    makeVintageButtons();
    makeButtons("task-platform-buttons",
      ["claude_ai", "api"].map(function (p) { return { value: p, label: PLATFORM_LABELS[p] }; }),
      function () { return state.taskPlatform; },
      function (p) { state.taskPlatform = p; renderY4(); });

    var input = el("occ-search"), ul = el("occ-hits");
    input.addEventListener("input", function () { renderHits(search(input.value)); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { var f = ul.querySelector("button"); if (f) { e.preventDefault(); f.click(); } }
      else if (e.key === "Escape") ul.hidden = true;
    });
    document.addEventListener("click", function (e) {
      if (!e.target.closest || !e.target.closest(".occ-picker")) ul.hidden = true;
    });
    var dl = el("occ-download");
    if (dl) dl.addEventListener("click", function () {
      var lines = ["styrk08;name;platform;vintage;usage_pct;automation_share;augmentation_share;directive;feedback_loop;task_iteration;validation;learning;n_classified"];
      state.occs.forEach(function (code) {
        var o = byCode[code];
        vint.forEach(function (v) {
          var x = o.v[v.key];
          if (!x) return;
          lines.push([code, o.name, v.platform, v.date, x.u, x.auto, x.aug, x.d, x.fb, x.ti, x.va, x.le, x.n === null ? "" : x.n].join(";"));
        });
      });
      var blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "yrker_automatisering.csv";
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
    });

    setText("y-n-occ", String(Y.n_occupations));
    renderKpi(); renderY1(); renderY2(); occChanged();
  }

  // ==================================================================
  // UTDANNING
  // ==================================================================

  function initUtdanning(U) {
    var inst = U.institutions;
    var state = { version: "v1", inst: inst[0].code, cohort: "all" };
    var VLAB = EN
      ? { v1: "Eloundou et al. (2024)", v2: "Mouchel et al. (2026)" }
      : { v1: "Eloundou m.fl. (2024)", v2: "Mouchel m.fl. (2026)" };
    var QLAB = function (i) {
      return EN ? ["Q1 (least exposed)", "Q2", "Q3", "Q4", "Q5 (most exposed)"][i]
                : ["K1 (minst eksponert)", "K2", "K3", "K4", "K5 (mest eksponert)"][i];
    };

    // ---- Figur 1: eksponering per institusjon, begge mål ----
    function renderU1() {
      var sorted = inst.slice().sort(function (a, b) { return a.exposure_v1 - b.exposure_v1; });
      chart("chart-u1").setOption({
        animationDuration: 300,
        grid: { left: 80, right: 40, top: 40, bottom: 64 },
        graphic: brandGraphic(SRC_EDU),
        legend: { top: 4, left: 80, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11 } },
        tooltip: { trigger: "axis", valueFormatter: function (v) { return num(v, 3); } },
        xAxis: { type: "value", min: 0.3, max: 0.7, name: EN ? "Mean exposure (0–1)" : "Snitt-eksponering (0–1)",
                 nameLocation: "middle", nameGap: 34,
                 splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { type: "category", data: sorted.map(function (i) { return i.short; }),
                 axisTick: { show: false } },
        series: [
          { name: VLAB.v1, type: "scatter", symbolSize: 14,
            itemStyle: { color: QUINT_COLORS[3] },
            label: { show: true, position: "right", fontSize: 11,
                     formatter: function (p) { return num(p.value, 2); } },
            data: sorted.map(function (i) { return i.exposure_v1; }) },
          { name: VLAB.v2, type: "scatter", symbolSize: 14,
            itemStyle: { color: QUINT_COLORS[0] },
            label: { show: true, position: "left", fontSize: 11,
                     formatter: function (p) { return num(p.value, 2); } },
            data: sorted.map(function (i) { return i.exposure_v2; }) }
        ]
      }, true);
    }

    // ---- Figur 2: kvintilfordeling per institusjon ----
    function renderU2() {
      var key = "q_" + state.version;
      var sorted = inst.slice().sort(function (a, b) { return b[key][4] - a[key][4]; });
      chart("chart-u2").setOption({
        animationDuration: 300,
        grid: { left: 80, right: 30, top: 44, bottom: 40 },
        graphic: brandGraphic(SRC_EDU),
        legend: { top: 4, left: 80, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11 } },
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" },
                   valueFormatter: function (v) { return pct(v, 1); } },
        xAxis: { type: "value", max: 100, axisLabel: { formatter: function (v) { return v + " %"; } },
                 splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { type: "category", inverse: true, axisTick: { show: false },
                 data: sorted.map(function (i) { return i.short; }) },
        series: [0, 1, 2, 3, 4].map(function (q) {
          return { name: QLAB(q), type: "bar", stack: "q", barMaxWidth: 26,
                   itemStyle: { color: QUINT_COLORS[q] },
                   label: { show: q === 4, position: "insideRight", color: "#fff", fontSize: 11,
                            formatter: function (p) { return num(p.value, 0) + " %"; } },
                   data: sorted.map(function (i) { return i[key][q] * 100; }) };
        })
      }, true);
      setText("u2-note", EN
        ? "Share of the institution's graduates (weighted by programme) whose typical occupations fall in each exposure quintile, " + VLAB[state.version] + ". Quintiles cut the same way as on the KI-indeks page."
        : "Andel av institusjonens kandidater (vektet per program) som typisk går til yrker i hver eksponeringskvintil, " + VLAB[state.version] + ". Kvintilene er kuttet som på KI-indeks-siden.");
    }

    // ---- Figur 3: nasjonalt etter fagfelt ----
    function renderU3() {
      var k = "share_q5_" + state.version, e = "exposure_" + state.version;
      var rows = U.national.fields.filter(function (f) {
        return f.group.indexOf("Uoppgitt") < 0;
      }).sort(function (a, b) { return b[k] - a[k]; });
      chart("chart-u3").setOption({
        animationDuration: 300,
        grid: { left: 250, right: 40, top: 30, bottom: 64 },
        graphic: brandGraphic(SRC_EDU),
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" },
                   formatter: function (ps) {
                     var f = rows[ps[0].dataIndex];
                     return "<b>" + f.group + "</b><br>" +
                       (EN ? "Share in Q5: " : "Andel i K5: ") + pct(f[k] * 100, 1) + "<br>" +
                       (EN ? "Mean exposure: " : "Snitt-eksponering: ") + num(f[e], 3) + "<br>" +
                       (EN ? "Employed: " : "Sysselsatte: ") + thousands(f.n_employed);
                   } },
        xAxis: { type: "value", max: 100, axisLabel: { formatter: function (v) { return v + " %"; } },
                 name: EN ? "Share of employed in the most exposed quintile" : "Andel sysselsatte i mest eksponerte kvintil",
                 nameLocation: "middle", nameGap: 34,
                 splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { type: "category", inverse: true, axisTick: { show: false },
                 data: rows.map(function (f) { return f.group; }),
                 axisLabel: { fontSize: 11, width: 234, overflow: "truncate" } },
        series: [{ type: "bar", barMaxWidth: 22, itemStyle: { color: QUINT_COLORS[4] },
                   label: { show: true, position: "right", fontSize: 11,
                            formatter: function (p) { return num(p.value, 0) + " %"; } },
                   data: rows.map(function (f) { return f[k] * 100; }) }]
      }, true);
      setText("u3-note", EN
        ? "All employed residents 20–70 by field of their highest completed education (utdanning.no register link, Nov 2024), " + VLAB[state.version] + "."
        : "Alle sysselsatte bosatte 20–70 år etter fagfeltet til høyeste fullførte utdanning (utdanning.no-registerkobling, nov. 2024), " + VLAB[state.version] + ".");
    }

    // ---- Figur 4: fagfeltmiks per institusjon ----
    function renderU4() {
      var fields = [];
      inst.forEach(function (i) {
        i.fields.forEach(function (f) { if (fields.indexOf(f.field) < 0) fields.push(f.field); });
      });
      var palette = ["#577590", "#E6A817", "#E54A2B", "#8C1515", "#401415",
                     "#2b3e50", "#9D9C97", "#c9a227", "#7a9cc6", "#d98c7a"];
      chart("chart-u4").setOption({
        animationDuration: 300,
        grid: { left: 80, right: 30, top: 60, bottom: 40 },
        graphic: brandGraphic(SRC_EDU),
        legend: { top: 4, left: 80, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 10.5 } },
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" },
                   valueFormatter: function (v) { return pct(v, 1); } },
        xAxis: { type: "value", max: 100, axisLabel: { formatter: function (v) { return v + " %"; } },
                 splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { type: "category", inverse: true, axisTick: { show: false },
                 data: inst.map(function (i) { return i.short; }) },
        series: fields.map(function (fname, j) {
          return { name: fname, type: "bar", stack: "f", barMaxWidth: 26,
                   itemStyle: { color: palette[j % palette.length] },
                   data: inst.map(function (i) {
                     var f = i.fields.filter(function (x) { return x.field === fname; })[0];
                     return f ? f.share * 100 : 0;
                   }) };
        })
      }, true);
    }

    // ---- Tabell: toppyrker per institusjon ----
    function renderTable() {
      var i = inst.filter(function (x) { return x.code === state.inst; })[0];
      var rows = (i.top_occ[state.cohort] || []).slice(0, 10);
      var qk = "q_" + state.version;
      var h = "<table class='data-table'><thead><tr><th>#</th><th>" +
        (EN ? "Occupation (STYRK-08)" : "Yrke (STYRK-08)") + "</th><th class='num'>" +
        (EN ? "Share" : "Andel") + "</th><th>" + (EN ? "Quintile" : "Kvintil") + "</th></tr></thead><tbody>";
      rows.forEach(function (r) {
        var q = r[qk];
        h += "<tr><td>" + r.rank + "</td><td>" + r.name + " <code>" + r.code + "</code></td>" +
          "<td class='num'>" + pct(r.share * 100, 1) + "</td><td>" +
          (q ? "<span class='q-badge' style='background:" + QUINT_COLORS[q - 1] + "'>" +
               (EN ? "Q" : "K") + q + "</span>" : "–") + "</td></tr>";
      });
      h += "</tbody></table>";
      el("u-top-table").innerHTML = h;
      setText("u-table-note", EN
        ? i.name + ": the ten most common occupations among " +
          (state.cohort === "all" ? "everyone" : "recent graduates (1–3 years)") +
          " in Norway with the same educations, weighted by the institution's " +
          U.year + " graduates. Quintile: " + VLAB[state.version] + "."
        : i.name + ": de ti vanligste yrkene blant " +
          (state.cohort === "all" ? "alle" : "nyutdannede (1–3 år)") +
          " i Norge med de samme utdanningene, vektet med institusjonens kandidater " +
          U.year + ". Kvintil: " + VLAB[state.version] + ".");
    }

    function renderKpi() {
      var top = inst[0], low = inst[inst.length - 1];
      setText("u-kpi", EN
        ? "Graduates " + U.year + ": " + top.short + " has the highest mean exposure (" +
          num(top.exposure_v1, 2) + ", " + pct(top.q_v1[4] * 100, 0) + " in the top quintile), " +
          low.short + " the lowest (" + num(low.exposure_v1, 2) + ", " + pct(low.q_v1[4] * 100, 0) + ")."
        : "Kandidater " + U.year + ": " + top.short + " har høyest snitt-eksponering (" +
          num(top.exposure_v1, 2) + ", " + pct(top.q_v1[4] * 100, 0) + " i øverste kvintil), " +
          low.short + " lavest (" + num(low.exposure_v1, 2) + ", " + pct(low.q_v1[4] * 100, 0) + ").");
    }

    makeButtons("u-version-buttons", ["v1", "v2"].map(function (v) {
      return { value: v, label: VLAB[v] };
    }), function () { return state.version; },
    function (v) { state.version = v; renderU2(); renderU3(); renderTable(); });
    makeButtons("u-inst-buttons", inst.map(function (i) {
      return { value: i.code, label: i.short };
    }), function () { return state.inst; },
    function (v) { state.inst = v; renderTable(); });
    makeButtons("u-cohort-buttons", [
      { value: "all", label: EN ? "All" : "Alle" },
      { value: "recent", label: EN ? "Recent graduates" : "Nyutdannede" }
    ], function () { return state.cohort; },
    function (v) { state.cohort = v; renderTable(); });

    renderKpi(); renderU1(); renderU2(); renderU3(); renderU4(); renderTable();
  }

  // ==================================================================
  // KI-BRUK PER LAND
  // ==================================================================

  function initBruk(B) {
    var countries = B.countries;
    var byA3 = {};
    countries.forEach(function (c) { byA3[c.a3] = c; });
    var NAMES_EN = { NOR: "Norway", SWE: "Sweden", DNK: "Denmark", FIN: "Finland",
                     ISL: "Iceland", NLD: "Netherlands", DEU: "Germany",
                     GBR: "United Kingdom", CHE: "Switzerland", USA: "United States" };
    function cname(a3) { return EN ? (NAMES_EN[a3] || a3) : byA3[a3].name; }
    var MONTHS = EN
      ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
      : ["jan.", "feb.", "mars", "april", "mai", "juni", "juli", "aug.", "sep.", "okt.", "nov.", "des."];
    function dlabel(s) {
      var m = MONTHS[+s.date.slice(5, 7) - 1] + " " + s.date.slice(0, 4);
      return s.window === "uke" ? m + (EN ? " (week)" : " (uke)") : m;
    }
    var latest = B.series[B.series.length - 1];
    var monthly = B.series.filter(function (s) { return s.window !== "uke"; });

    // ---- Figur 1: Anthropics per capita-indeks, siste måned ----
    function renderB1() {
      var rows = countries.filter(function (c) { return latest.by_country[c.a3]; })
        .sort(function (a, b) { return latest.by_country[b.a3].aui - latest.by_country[a.a3].aui; });
      chart("chart-b1").setOption({
        animationDuration: 300,
        grid: { left: 110, right: 40, top: 20, bottom: 64 },
        graphic: brandGraphic(SRC_USE),
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" },
                   valueFormatter: function (v) { return num(v, 2); } },
        xAxis: { type: "value", name: EN ? "Anthropic Usage Index (1 = proportional to working-age population)"
                                          : "Anthropic Usage Index (1 = i takt med arbeidsfør befolkning)",
                 nameLocation: "middle", nameGap: 34, splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { type: "category", inverse: true, axisTick: { show: false },
                 data: rows.map(function (c) { return cname(c.a3); }) },
        series: [{ type: "bar", barMaxWidth: 22,
                   itemStyle: { color: function (p) { return rows[p.dataIndex].a3 === "NOR" ? QUINT_COLORS[3] : QUINT_COLORS[0]; } },
                   label: { show: true, position: "right", fontSize: 11,
                            formatter: function (p) { return num(p.value, 1); } },
                   data: rows.map(function (c) { return latest.by_country[c.a3].aui; }) }]
      }, true);
      setText("b1-note", EN
        ? "Claude.ai conversations per working-age adult relative to the world, " + dlabel(latest) + ". Anthropic's own index, from the June 2026 country file."
        : "Claude.ai-samtaler per arbeidsfør innbygger relativt til verden, " + dlabel(latest) + ". Anthropics egen indeks, fra landfilen i juni 2026.");
    }

    // ---- Figur 2: automatiseringsandel per land over tid ----
    function renderB2() {
      var show = ["NOR", "SWE", "DNK", "DEU", "GBR", "USA"];
      var cols = { NOR: QUINT_COLORS[3], SWE: QUINT_COLORS[0], DNK: QUINT_COLORS[1],
                   DEU: "#2b3e50", GBR: QUINT_COLORS[2], USA: QUINT_COLORS[4] };
      chart("chart-b2").setOption({
        animationDuration: 300,
        grid: { left: 50, right: 130, top: 24, bottom: 44 },
        graphic: brandGraphic(SRC_USE),
        tooltip: { trigger: "axis", valueFormatter: function (v) { return v === null ? "–" : pct(v, 1); } },
        xAxis: { type: "category", boundaryGap: false, data: B.series.map(dlabel) },
        yAxis: { type: "value", min: 30, max: 60,
                 axisLabel: { formatter: function (v) { return v + " %"; } },
                 splitLine: { lineStyle: { color: "#eee" } } },
        series: show.map(function (a3) {
          return { name: cname(a3), type: "line", symbol: "circle", symbolSize: 6,
                   lineStyle: { width: a3 === "NOR" ? 3.2 : 2 },
                   itemStyle: { color: cols[a3] }, color: cols[a3],
                   endLabel: { show: true, formatter: cname(a3), fontSize: 11,
                               color: cols[a3], fontWeight: 600, distance: 6 },
                   labelLayout: { moveOverlap: "shiftY" },
                   data: B.series.map(function (s) {
                     var c = s.by_country[a3];
                     return c && c.automation !== undefined ? c.automation : null;
                   }) };
        })
      }, true);
      setText("b2-note", EN
        ? "Share of classified Claude.ai conversations that are automation (directive + feedback loop). Three sample weeks from the raw releases, then two monthly country files."
        : "Andel av klassifiserte Claude.ai-samtaler som er automatisering (direkte delegering + tilbakemeldingssløyfe). Tre utvalgsuker fra rådataene, deretter to månedlige landfiler.");
    }

    // ---- Figur 3: arbeid, privat, skolearbeid ----
    function renderB3() {
      var rows = countries.filter(function (c) { return latest.by_country[c.a3] && latest.by_country[c.a3].work !== undefined; })
        .sort(function (a, b) { return latest.by_country[b.a3].work - latest.by_country[a.a3].work; });
      var keys = ["work", "personal", "coursework"];
      var lab = EN ? { work: "Work", personal: "Personal", coursework: "Coursework" }
                   : { work: "Arbeid", personal: "Privat", coursework: "Skolearbeid" };
      var col = { work: QUINT_COLORS[3], personal: QUINT_COLORS[0], coursework: QUINT_COLORS[1] };
      chart("chart-b3").setOption({
        animationDuration: 300,
        grid: { left: 110, right: 30, top: 40, bottom: 40 },
        graphic: brandGraphic(SRC_USE),
        legend: { top: 4, left: 110, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11 } },
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" },
                   valueFormatter: function (v) { return pct(v, 1); } },
        xAxis: { type: "value", max: 100, axisLabel: { formatter: function (v) { return v + " %"; } },
                 splitLine: { lineStyle: { color: "#eee" } } },
        yAxis: { type: "category", inverse: true, axisTick: { show: false },
                 data: rows.map(function (c) { return cname(c.a3); }) },
        series: keys.map(function (k) {
          return { name: lab[k], type: "bar", stack: "u", barMaxWidth: 22,
                   itemStyle: { color: col[k] },
                   data: rows.map(function (c) { return latest.by_country[c.a3][k]; }) };
        })
      }, true);
      setText("b3-note", EN
        ? "Use-case split of Claude.ai conversations, " + dlabel(latest) + ". The remainder is unclassified."
        : "Bruksformål i Claude.ai-samtalene, " + dlabel(latest) + ". Resten er uklassifisert.");
    }

    // ---- Tabell: Norge over tid ----
    function renderTable() {
      var h = "<table class='data-table'><thead><tr><th>" + (EN ? "Sample" : "Utvalg") +
        "</th><th class='num'>" + (EN ? "Share of global use" : "Andel av global bruk") +
        "</th><th class='num'>" + (EN ? "Per capita index" : "Per capita-indeks") +
        "</th><th class='num'>" + (EN ? "Automation" : "Automatisering") +
        "</th><th class='num'>" + (EN ? "Directive" : "Direkte deleg.") +
        "</th><th class='num'>" + (EN ? "Feedback loop" : "Tilbakemeld.") +
        "</th><th class='num'>" + (EN ? "Task iteration" : "Oppg.iterasjon") +
        "</th><th class='num'>" + (EN ? "Validation" : "Validering") +
        "</th><th class='num'>" + (EN ? "Learning" : "Læring") +
        "</th><th class='num'>" + (EN ? "Work use" : "Arbeid") + "</th></tr></thead><tbody>";
      B.series.forEach(function (s) {
        var c = s.by_country.NOR;
        if (!c) return;
        function cell(v) { return "<td class='num'>" + (v === undefined || v === null ? "–" : pct(v, 1)) + "</td>"; }
        h += "<tr><td>" + dlabel(s) + "</td><td class='num'>" + pct(c.usage_pct, 2) + "</td>" +
          "<td class='num'>" + (c.aui === undefined ? "–" : num(c.aui, 1)) + "</td>" +
          cell(c.automation) + cell(c.directive) + cell(c.feedback_loop) +
          cell(c.task_iteration) + cell(c.validation) + cell(c.learning) + cell(c.work) + "</tr>";
      });
      h += "</tbody></table>";
      el("b-table").innerHTML = h;
    }

    function renderKpi() {
      var n = latest.by_country.NOR;
      setText("b-kpi", EN
        ? "Norway, " + dlabel(latest) + ": " + pct(n.usage_pct, 2) + " of global Claude.ai use, per capita index " +
          num(n.aui, 1) + ", automation share " + pct(n.automation, 1) + "."
        : "Norge, " + dlabel(latest) + ": " + pct(n.usage_pct, 2) + " av global Claude.ai-bruk, per capita-indeks " +
          num(n.aui, 1) + ", automatiseringsandel " + pct(n.automation, 1) + ".");
    }

    renderKpi(); renderB1(); renderB2(); renderB3(); renderTable();
  }

  // ---------- Oppstart ----------

  initToc();
  var FILE = { yrker: "yrker", utdanning: "utdanning", bruk: "bruk" }[PANEL];
  var INIT = { yrker: initYrker, utdanning: initUtdanning, bruk: initBruk }[PANEL];
  if (!FILE) return;
  fetch("/data/" + FILE + ".json?v=" + V)
    .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(INIT)
    .catch(fail);
})();
