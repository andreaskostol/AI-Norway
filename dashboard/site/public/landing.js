/* Landingssiden (okt. 2026): to animerte figurer med de mest og de minst
   KI-eksponerte yrkene, for alle aldre (21-60) og for de yngste (21-30), med
   hendelsene ChatGPT (nov. 2022) og agentisk KI (Claude Code, feb. 2025)
   tegnet inn, og KI-indeksen regnet som paa indekssiden (app.js):
   tre maaneders etterslepende snitt, vekst fra referansemaaneden (okt. 2022
   / jan. 2025) til siste maaned, relativ vekst Q5 mot Q1. Tallene i rutene
   over figurene er nettstedets egne (headline_uncertainty_* i dashboard.json),
   med bootstrap-standardfeil. Tospraaklig via <html lang>. */

(function () {
  "use strict";

  var EN = (document.documentElement.lang || "nb").toLowerCase().indexOf("en") === 0;
  var Q1 = "Quintile 1 (least exposed)", Q5 = "Quintile 5 (most exposed)";
  var COL_Q1 = "#577590", COL_Q5 = "#401415";           // samme palett som app.js
  var HEADLINE_MA = 3;
  var MONTHS = EN
    ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    : ["jan.", "feb.", "mars", "april", "mai", "juni", "juli", "aug.", "sep.", "okt.", "nov.", "des."];

  // De to hendelsene. ref = referansemaaneden indeksen maales fra (maaneden
  // foer lanseringen, som paa indekssiden), date = maaneden som markeres.
  var EVENTS = [
    { key: "chatgpt", date: "2022-11-01", ref: "2022-10-01",
      label: "ChatGPT", when: EN ? "Nov 2022" : "nov. 2022",
      unc: ["headline_uncertainty_by_measure", "headline_uncertainty_young_by_measure"] },
    { key: "claudecode", date: "2025-02-01", ref: "2025-01-01",
      label: EN ? "Agentic AI" : "Agentisk KI", when: EN ? "Feb 2025" : "feb. 2025",
      unc: ["headline_uncertainty_claudecode_by_measure", "headline_uncertainty_young_claudecode_by_measure"] }
  ];

  function fmtMonth(iso) { return MONTHS[+iso.slice(5, 7) - 1] + " " + iso.slice(0, 4); }
  function fmtNum(v, d) {
    var s = (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(d == null ? 1 : d);
    return EN ? s : s.replace(".", ",");
  }
  function fmtLevel(v) { var s = v.toFixed(1); return EN ? s : s.replace(".", ","); }

  // Samme glatting og vekstmaal som app.js, saa tallene stemmer med indekssiden.
  function movingAverage(values, k) {
    var out = [], i, j, s, n;
    for (i = 0; i < values.length; i++) {
      if (values[i] == null) { out.push(null); continue; }
      s = 0; n = 0;
      for (j = i - k + 1; j <= i; j++) {
        if (j >= 0 && values[j] != null) { s += values[j]; n += 1; }
      }
      out.push(n ? Math.round(100 * s / n) / 100 : null);
    }
    return out;
  }
  function epochGrowth(values, dates, refMonth) {
    var i = dates.indexOf(refMonth);
    if (i < 0) return null;
    var sm = movingAverage(values, HEADLINE_MA);
    var before = sm[i], after = sm[sm.length - 1];
    if (!before || after == null) return null;
    return 100 * (after / before - 1);
  }
  function kiIndex(q1, q5, dates, refMonth) {
    var g1 = epochGrowth(q1, dates, refMonth), g5 = epochGrowth(q5, dates, refMonth);
    if (g1 == null || g5 == null) return null;
    return 100 * ((1 + g5 / 100) / (1 + g1 / 100) - 1);
  }

  // ---------- Data ----------
  var DB, dates, panels;
  function loadPanels() {
    var be = DB.packages.by_exposure, ae = DB.packages.age_by_exposure;
    dates = be.dates;
    var sa = be.series.sa._, ysa = ae.series.sa;
    return [
      { id: "chart-all", young: false, q1: sa[Q1], q5: sa[Q5] },
      { id: "chart-young", young: true, q1: ysa[Q1]["21-30"], q5: ysa[Q5]["21-30"] }
    ];
  }

  // Nettstedets hovedtall med usikkerhet; faller tilbake til egen utregning.
  function headline(panel, ev) {
    var key = ev.unc[panel.young ? 1 : 0];
    var u = (DB[key] || {}).eloundou;
    var computed = kiIndex(panel.q1, panel.q5, dates, ev.ref);
    if (u && u.spec === "sa" && typeof u.ki === "number") {
      return { ki: u.ki, se: u.se, lo: u.ci_lo, hi: u.ci_hi, computed: computed };
    }
    return { ki: computed, se: null, lo: null, hi: null, computed: computed };
  }

  // ---------- Rutene over figurene ----------
  function renderTiles() {
    var holder = document.getElementById("stat-grid");
    if (!holder) return;
    var html = "";
    EVENTS.forEach(function (ev) {
      panels.forEach(function (p) {
        var h = headline(p, ev);
        if (h.ki == null) return;
        var cls = Math.abs(h.ki) < 0.05 ? "" : (h.ki > 0 ? " pos" : " neg");
        var who = p.young ? (EN ? "Ages 21–30" : "Unge, 21–30 år")
                          : (EN ? "Ages 21–60" : "Alle, 21–60 år");
        html += '<div class="stat-tile">' +
          '<div class="stat-label">' + (EN ? "Since " : "Siden ") + ev.label + " (" + ev.when + ")</div>" +
          '<div class="stat-who">' + who + "</div>" +
          '<div class="stat-value' + cls + '">' + fmtNum(h.ki) + "</div>" +
          '<div class="stat-unit">' + (EN ? "percentage points" : "prosentpoeng") +
          (h.se != null ? (EN ? ", standard error " : ", standardfeil ") + fmtLevel(h.se) : "") + "</div>" +
          "</div>";
      });
    });
    holder.innerHTML = html;
  }

  // ---------- Figurene ----------
  var charts = {}, timer = null;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function yRange() {
    var lo = Infinity, hi = -Infinity;
    panels.forEach(function (p) {
      p.q1.concat(p.q5).forEach(function (v) { if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } });
    });
    return [Math.floor(lo - 1.5), Math.ceil(hi + 2.5)];
  }

  function eventLines(k) {
    // De stiplede strekene for hendelsene animasjonen har naadd. Tekstene
    // settes som grafikk i piksler (placeLabels), saa de staar vannrett.
    var data = [];
    EVENTS.forEach(function (ev) {
      var i = dates.indexOf(ev.date);
      if (i < 0 || i >= k) return;
      data.push({ xAxis: ev.date, lineStyle: { color: "#3a3a3a", type: "dashed", width: 1.4 }, label: { show: false } });
    });
    data.push({ yAxis: 100, lineStyle: { color: "#cfcdc6", type: "dotted", width: 1 }, label: { show: false } });
    return data;
  }

  // Hendelsestekster og dato som vannrett grafikk. Samme id-er hver gang, saa
  // setOption i flettemodus bytter dem ut i stedet for aa stable dem.
  function placeLabels(chart, panel, k, finished) {
    var els = [{ id: "date", type: "text", left: 48, top: 8, style: {
      text: fmtMonth(dates[Math.max(0, Math.min(k, dates.length) - 1)]),
      fill: "#4a5868", fontSize: 12, fontWeight: 600 } }];
    EVENTS.forEach(function (ev) {
      var i = dates.indexOf(ev.date);
      var reached = i >= 0 && i < k;
      var x = reached ? chart.convertToPixel({ xAxisIndex: 0 }, ev.date) : 0;
      var line2 = ev.when;
      if (finished) {
        var h = headline(panel, ev);
        if (h.ki != null) line2 = (EN ? "Index " : "KI-indeksen ") + fmtNum(h.ki);
      }
      els.push({ id: "ev-" + ev.key, type: "text", invisible: !reached, left: x + 6, top: 26,
                 style: { text: ev.label + "\n" + line2, fill: "#3a3a3a", fontSize: 12,
                          fontWeight: 600, lineHeight: 15 } });
    });
    chart.setOption({ graphic: els });
  }

  function option(panel, k, finished) {
    var range = yRange();
    // Sluttetikettene dyttes fra hverandre naar linjene ender naer hverandre.
    var l1 = panel.q1[k - 1], l5 = panel.q5[k - 1], dy1 = 0, dy5 = 0;
    if (l1 != null && l5 != null && Math.abs(l1 - l5) < 2.2) {
      dy1 = l1 >= l5 ? -9 : 9; dy5 = -dy1;
    }
    function series(name, vals, color, dy) {
      return {
        name: name, type: "line", data: vals.slice(0, k), showSymbol: false,
        lineStyle: { width: 2.6, color: color }, itemStyle: { color: color },
        emphasis: { disabled: true }, animation: false, z: 3,
        endLabel: { show: true, formatter: function (p) {
          return name + (p.value != null ? " " + fmtLevel(p.value) : "");
        }, color: color, fontSize: 11.5, fontWeight: 700, offset: [6, dy] }
      };
    }
    return {
      animation: false,
      grid: { left: 44, right: 118, top: 60, bottom: 32 },
      tooltip: { trigger: "axis", valueFormatter: function (v) { return v == null ? "–" : fmtLevel(v); },
                 axisPointer: { label: { formatter: function (p) { return fmtMonth(p.value); } } } },
      xAxis: { type: "category", data: dates, boundaryGap: false,
               axisLabel: { interval: 0, formatter: function (v) { return v.slice(5, 7) === "01" ? v.slice(0, 4) : ""; } },
               axisTick: { show: false }, axisLine: { lineStyle: { color: "#bdb9b0" } } },
      yAxis: { type: "value", min: range[0], max: range[1], splitLine: { lineStyle: { color: "#eee" } },
               axisLabel: { formatter: function (v) { return v; } } },
      series: [
        Object.assign(series(EN ? "Least exposed" : "Minst eksponert", panel.q1, COL_Q1, dy1),
                      { markLine: { symbol: "none", silent: true, animation: false, data: eventLines(k) } }),
        series(EN ? "Most exposed" : "Mest eksponert", panel.q5, COL_Q5, dy5)
      ]
    };
  }

  function draw(k, finished) {
    panels.forEach(function (p) {
      charts[p.id].setOption(option(p, k, finished), { notMerge: true, lazyUpdate: false });
      placeLabels(charts[p.id], p, k, finished);
    });
  }

  // Tidsstyrt animasjon: hver maaned har en varighet (lengre rundt
  // hendelsene), og bildet velges etter medgaatt tid. Da blir den ferdig
  // paa samme tid selv om nettleseren struper tidtakere, og foerste bilde
  // tegnes med en gang.
  function schedule() {
    var cum = [0], t = 0;
    for (var m = 1; m <= dates.length; m++) {
      var near = EVENTS.some(function (ev) { var i = dates.indexOf(ev.date); return i >= 0 && Math.abs(m - i) <= 2; });
      t += near ? 140 : 55;
      cum.push(t);
    }
    return cum;
  }
  function play() {
    timer = null;
    var n = dates.length;
    if (reduce) { draw(n, true); return; }
    var cum = schedule(), t0 = null, last = 0, run = {};
    timer = run;
    var frame = function (now) {
      if (timer !== run) return;                         // ny avspilling startet
      if (t0 === null) t0 = now;
      var el = now - t0, k = 2;
      while (k < n && cum[k] <= el) k += 1;
      if (k !== last) { draw(Math.min(k, n), false); last = k; }
      if (k < n) {
        // setTimeout, ikke requestAnimationFrame: tegner ogsaa i en fane som
        // ikke er synlig, og tidsstyringen gjoer at struping ikke forsinker slutten.
        setTimeout(function () { frame(performance.now()); }, 30);
      } else {
        draw(n, true);
        timer = null;
      }
    };
    frame(performance.now());
  }

  function init() {
    panels = loadPanels();
    panels.forEach(function (p) {
      var el = document.getElementById(p.id);
      if (el) charts[p.id] = echarts.init(el, null, { renderer: "canvas" });
    });
    renderTiles();
    var note = document.getElementById("landing-release");
    if (note) {
      note.textContent = (EN ? "Release " : "Release ") + DB.release +
        (EN ? ", data through " : ", data til og med ") + fmtMonth(dates[dates.length - 1]) + ".";
    }
    var btn = document.getElementById("replay");
    if (btn) btn.addEventListener("click", play);
    window.addEventListener("resize", function () {
      Object.keys(charts).forEach(function (id) { charts[id].resize(); });
      if (!timer) draw(dates.length, true);           // tekstene maa plasseres paa nytt
    });
    play();
  }

  // ---------- Filmene ----------
  // Lest fra data/videos.json. Bare status "publisert" vises; uten engelsk fil
  // vises den norske med en merknad. Ingen publiserte filmer: hele blokken skjult.
  function esc(t) {
    return String(t == null ? "" : t).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function renderVideos(man) {
    var sec = document.getElementById("landing-videos"), grid = document.getElementById("video-grid");
    if (!sec || !grid || !man || !man.videos) return;
    var lang = EN ? "en" : "no", html = "";
    man.videos.slice().sort(function (a, b) { return (a.order || 0) - (b.order || 0); }).forEach(function (v) {
      if (v.status !== "publisert") return;
      var t = v[lang] || {}, fb = v.no || {};
      var src = t.src || fb.src, poster = t.poster || fb.poster, note = t.src ? "" : (t.fallback_note || "");
      if (!src) return;
      html += '<div class="video-card"><h3>' + esc(t.title || fb.title) + "</h3>" +
        '<video controls preload="metadata" playsinline' + (poster ? ' poster="' + esc(poster) + '"' : "") + ">" +
        '<source src="' + esc(src) + '" type="video/mp4">' +
        (EN ? "Your browser cannot play this video." : "Nettleseren din kan ikke spille av videoen.") + "</video>" +
        "<p>" + esc(t.text || fb.text) + (note ? " " + esc(note) : "") + "</p></div>";
    });
    grid.innerHTML = html;
    sec.hidden = !html;
  }

  fetch("/data/videos.json", { cache: "no-cache" })
    .then(function (r) { return r.json(); })
    .then(renderVideos)
    .catch(function () { /* ingen filmer: blokken forblir skjult */ });

  fetch("/data/dashboard.json", { cache: "no-cache" })
    .then(function (r) { return r.json(); })
    .then(function (d) { DB = d; init(); })
    .catch(function (e) {
      var el = document.getElementById("stat-grid");
      if (el) el.textContent = EN ? "The data could not be loaded." : "Dataene kunne ikke lastes.";
      if (window.console) console.error(e);
    });
})();
