/* KI-indeksen — sidene ved siden av forsiden: Yrker og Utdanning.
   Ett script for begge; <body data-panel="..."> sier hvilken side som skal
   tegnes, og <html lang> styrer språket slik at samme fil betjener / og /en/.
   Data: public/data/yrker.json, utdanning.json, occupations.json (yrkes-
   velgeren på forsiden) og vacancies.json når den finnes, alle bygget av
   prepare_panels.py / prepare_data.py. Figurstilen følger app.js.
   Sammendragene skrives som løpende tekst fra dataene, som på forsiden. */

(function () {
  "use strict";

  var EN = (document.documentElement.lang || "nb")
             .toLowerCase().indexOf("en") === 0;
  var PANEL = document.body.getAttribute("data-panel");
  var V = "20260925a";

  // ---------- Farger og etiketter ----------

  var QUINT_COLORS = ["#577590", "#E6A817", "#E54A2B", "#8C1515", "#401415"];
  var GREY = "#b8b4ab";
  // Fargen til plass 1-6 i yrkeslista. Plass 1 er hovedyrket (roedt).
  var SLOT_COLORS = ["#8C1515", "#577590", "#E6A817", "#2b3e50", "#E54A2B", "#9D9C97"];
  var TYPES = ["d", "fb", "ti", "va", "le"];
  // To farger overalt (Andreas, runde 13): automatisering (direkte delegering +
  // tilbakemeldingssloeyfe) moerk, augmentering (de tre andre) lys. Samme som i
  // «Slik brukes Claude paa oppgavene».
  var AUTO_COLOR = "#401415", AUG_COLOR = "#d3cec2";
  var TYPE_COLORS = { d: AUTO_COLOR, fb: AUTO_COLOR, ti: AUG_COLOR, va: AUG_COLOR, le: AUG_COLOR };
  var TYPE_LABELS = EN
    ? { d: "Directive", fb: "Feedback loop", ti: "Task iteration", va: "Validation", le: "Learning" }
    : { d: "Direkte delegering", fb: "Tilbakemeldingssløyfe", ti: "Oppgaveiterasjon",
        va: "Validering", le: "Læring" };
  var PLATFORM_LABELS = EN
    ? { claude_ai: "Claude.ai (chat)", api: "API (developers, agents)" }
    : { claude_ai: "Claude.ai (chat)", api: "API (utviklere, agenter)" };
  var PLATFORM_SHORT = { claude_ai: EN ? "Chat" : "Chat", api: "API" };

  // O*NETs 41 arbeidsaktiviteter og 35 ferdigheter, norske navn. Brukes i
  // «Yrker som ligner»; engelsk beholdes paa /en/.
  var ONET_NO = {
    "Active Learning": "aktiv læring",
    "Active Listening": "aktiv lytting",
    "Analyzing Data or Information": "analyse av data og informasjon",
    "Assisting and Caring for Others": "hjelp og omsorg for andre",
    "Coaching and Developing Others": "veiledning og utvikling av andre",
    "Communicating with People Outside the Organization": "kommunikasjon med folk utenfor virksomheten",
    "Communicating with Supervisors, Peers, or Subordinates": "kommunikasjon med ledere, kolleger og underordnede",
    "Complex Problem Solving": "kompleks problemløsning",
    "Controlling Machines and Processes": "styring av maskiner og prosesser",
    "Coordinating the Work and Activities of Others": "koordinering av andres arbeid",
    "Coordination": "koordinering",
    "Critical Thinking": "kritisk tenkning",
    "Developing Objectives and Strategies": "utvikling av mål og strategier",
    "Developing and Building Teams": "bygging av team",
    "Documenting/Recording Information": "dokumentasjon og registrering av informasjon",
    "Drafting, Laying Out, and Specifying Technical Devices, Parts, and Equipment": "tegning og spesifikasjon av teknisk utstyr",
    "Equipment Maintenance": "vedlikehold av utstyr",
    "Equipment Selection": "valg av utstyr",
    "Establishing and Maintaining Interpersonal Relationships": "bygging og vedlikehold av relasjoner",
    "Estimating the Quantifiable Characteristics of Products, Events, or Information": "anslag av mengder, størrelser og kostnader",
    "Evaluating Information to Determine Compliance with Standards": "vurdering av samsvar med regler og standarder",
    "Getting Information": "innhenting av informasjon",
    "Guiding, Directing, and Motivating Subordinates": "ledelse og motivering av underordnede",
    "Handling and Moving Objects": "håndtering og flytting av gjenstander",
    "Identifying Objects, Actions, and Events": "identifisering av objekter, handlinger og hendelser",
    "Inspecting Equipment, Structures, or Materials": "inspeksjon av utstyr, konstruksjoner og materialer",
    "Installation": "installasjon",
    "Instructing": "undervisning",
    "Interpreting the Meaning of Information for Others": "tolkning av informasjon for andre",
    "Judging the Qualities of Objects, Services, or People": "vurdering av kvaliteten på ting, tjenester og folk",
    "Judgment and Decision Making": "skjønn og beslutninger",
    "Learning Strategies": "læringsstrategier",
    "Making Decisions and Solving Problems": "beslutninger og problemløsning",
    "Management of Financial Resources": "økonomistyring",
    "Management of Material Resources": "styring av materielle ressurser",
    "Management of Personnel Resources": "personalledelse",
    "Mathematics": "matematikk",
    "Monitoring": "oppfølging av egen og andres innsats",
    "Monitoring Processes, Materials, or Surroundings": "overvåking av prosesser, materialer og omgivelser",
    "Monitoring and Controlling Resources": "overvåking og styring av ressurser",
    "Negotiation": "forhandling",
    "Operating Vehicles, Mechanized Devices, or Equipment": "kjøring og betjening av kjøretøy og maskiner",
    "Operation and Control": "betjening og styring av utstyr",
    "Operations Analysis": "kravanalyse",
    "Operations Monitoring": "overvåking av utstyr i drift",
    "Organizing, Planning, and Prioritizing Work": "organisering, planlegging og prioritering av arbeid",
    "Performing Administrative Activities": "administrative oppgaver",
    "Performing General Physical Activities": "fysisk arbeid",
    "Performing for or Working Directly with the Public": "direkte arbeid med publikum",
    "Persuasion": "overtalelse",
    "Processing Information": "bearbeiding av informasjon",
    "Programming": "programmering",
    "Providing Consultation and Advice to Others": "rådgivning",
    "Quality Control Analysis": "kvalitetskontroll",
    "Reading Comprehension": "leseforståelse",
    "Repairing": "reparasjon",
    "Repairing and Maintaining Electronic Equipment": "reparasjon og vedlikehold av elektronisk utstyr",
    "Repairing and Maintaining Mechanical Equipment": "reparasjon og vedlikehold av mekanisk utstyr",
    "Resolving Conflicts and Negotiating with Others": "konfliktløsning og forhandling",
    "Scheduling Work and Activities": "planlegging av arbeid og aktiviteter",
    "Science": "naturvitenskapelige metoder",
    "Selling or Influencing Others": "salg og påvirkning",
    "Service Orientation": "serviceinnstilling",
    "Social Perceptiveness": "sosial oppmerksomhet",
    "Speaking": "muntlig fremstilling",
    "Staffing Organizational Units": "rekruttering og bemanning",
    "Systems Analysis": "systemanalyse",
    "Systems Evaluation": "systemevaluering",
    "Technology Design": "teknologidesign",
    "Thinking Creatively": "kreativ tenkning",
    "Time Management": "tidsstyring",
    "Training and Teaching Others": "opplæring av andre",
    "Troubleshooting": "feilsøking",
    "Updating and Using Relevant Knowledge": "oppdatering og bruk av fagkunnskap",
    "Working with Computers": "arbeid med datamaskiner",
    "Writing": "skriving"
  };
  function onetName(s) {
    if (EN) return s.charAt(0).toLowerCase() + s.slice(1);
    return ONET_NO[s] || s;
  }
  var MONTHS = EN
    ? ["January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]
    : ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august",
       "september", "oktober", "november", "desember"];
  function monthLabel(d) { return MONTHS[+d.slice(5, 7) - 1] + " " + d.slice(0, 4); }

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
  function cap(s) { s = s || ""; return s.charAt(0).toUpperCase() + s.slice(1); }
  // Bredde per kategorietikett i femtype-figurene, saa de ikke overlapper paa smale skjermer.
  function typeLabelWidth(id) {
    var w = el(id) ? el(id).clientWidth : 600;
    return Math.max(52, Math.min(120, Math.floor((w - 90) / 5) - 8));
  }
  function el(id) { return document.getElementById(id); }
  function setText(id, s) { var e = el(id); if (e) e.textContent = s; }
  function occName(o) { return EN && o.name_en ? o.name_en : o.name; }
  // De fem eksponeringsgruppene (femdeling av yrkene) med navn i stedet for
  // «kvintil»: gruppe 1 er minst utsatt, gruppe 5 mest.
  var GROUP_NAMES = EN ? ["Least exposed", "Low", "Medium", "High", "Most exposed"]
                       : ["Minst utsatt", "Lite utsatt", "Middels", "Mye utsatt", "Mest utsatt"];
  function qBadge(q) {
    return q ? "<span class='q-badge' style='background:" + QUINT_COLORS[q - 1] + "'>" + GROUP_NAMES[q - 1] + "</span>" : "–";
  }

  // Nedtrekksmeny med samme kontrakt som makeButtons. Brukes der det er
  // mer enn tre valg, saa siden ikke fylles av knapperader.
  function makeSelect(id, options, get, set) {
    var sel = el(id);
    if (!sel) return;
    sel.innerHTML = "";
    options.forEach(function (opt) {
      var o = document.createElement("option");
      o.value = opt.value;
      o.textContent = opt.label;
      sel.appendChild(o);
    });
    sel.value = get();
    sel.addEventListener("change", function () { set(sel.value); });
  }
  // Fyll en nedtrekksmeny paa nytt uten aa legge til flere lyttere.
  function fillSelect(id, options, value) {
    var sel = el(id);
    if (!sel) return;
    sel.innerHTML = "";
    options.forEach(function (opt) {
      var o = document.createElement("option");
      o.value = opt.value;
      o.textContent = opt.label;
      sel.appendChild(o);
    });
    sel.value = value;
  }
  function setAll(selector, text) {
    Array.prototype.forEach.call(document.querySelectorAll(selector), function (e) { e.textContent = text; });
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

  // Stablet 100 %-stolpe med automatisering og augmentering, én rad per element;
  // de fem typene ligger i tooltipen.
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
          s += "<br><span style='color:#777'>" + TYPES.map(function (t) { return TYPE_LABELS[t] + " " + pct((r.v[t] || 0) * 100, 0); }).join(" · ") + "</span>";
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
      series: [
        { name: EN ? "Automation" : "Automatisering", type: "bar", stack: "s", itemStyle: { color: AUTO_COLOR },
          emphasis: { focus: "series" }, barMaxWidth: 22,
          data: rows.map(function (r) { return r.v.d === null ? 0 : (r.v.d + r.v.fb) * 100; }) },
        { name: EN ? "Augmentation" : "Augmentering", type: "bar", stack: "s", itemStyle: { color: AUG_COLOR },
          emphasis: { focus: "series" }, barMaxWidth: 22,
          data: rows.map(function (r) { return r.v.d === null ? 0 : (r.v.ti + r.v.va + r.v.le) * 100; }) }
      ]
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
    var state = { occs: [], outcome: "employment", smooth: 6, platform: "claude_ai",
                  vintage: latestKey.claude_ai, tidPlatform: "claude_ai", taskPlatform: "claude_ai",
                  typesPlatform: "claude_ai", typesCompare: "", task: 0, taskCompare: "", taskCount: 5, tasksCompare: "",
                  tidMeasure: "u", random: false };
    // Naboyrker uten Claude-data ligger i Y.extra (navn, stoerrelse, kvintil).
    var extra = Y.extra || {};
    function anyOcc(code) { return byCode[code] || extra[code] || null; }
    function focus() { return state.occs[0] ? byCode[state.occs[0]] : null; }
    function latestChat(o) { return o.v[latestKey.claude_ai]; }
    function latestApi(o) { return o.v[latestKey.api]; }
    // Samme glatting som forsiden (app.js movingAverage/indexSeries):
    // etterslepende glidende snitt over k maaneder, deretter skalert saa
    // referansemaaneden (feb. 2025, Claude Code) er noeyaktig 100.
    function movingAverage(values, k) {
      if (k <= 1) return values;
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
    function indexSeries(raw) {
      var sm = movingAverage(raw, state.smooth);
      var baseIdx = OCC.dates.indexOf(REF_MONTH);
      if (baseIdx < 0 || !sm[baseIdx]) return null;
      var base = sm[baseIdx];
      return sm.map(function (v) { return v == null ? null : Math.round(10000 * v / base) / 100; });
    }
    // Endring siden Claude Code (feb. 2025) i den glattede, sesongjusterte
    // serien, siste maaned med tall. Samme tall som figuren viser.
    function changeSince(code, outcome) {
      var s = OCC.byCode[code];
      if (!s || !s[outcome]) return null;
      var idx = indexSeries(s[outcome].sa);
      if (!idx) return null;
      var refIdx = OCC.dates.indexOf(REF_MONTH), last = idx.length - 1;
      while (last >= 0 && idx[last] === null) last--;
      if (last <= refIdx) return null;
      return { pct: idx[last] - 100, date: OCC.dates[last] };
    }

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
        pick.innerHTML = "<i style='background:" + SLOT_COLORS[i] + "'></i>" + occName(o) +
          "<span class='occ-code'>" + code + "</span>";
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
        var idx = indexSeries(s[state.outcome].sa);
        if (!idx) { missing.push(occName(byCode[code])); return; }
        series.push({
          name: occName(byCode[code]) + " (" + code + ")", type: "line", showSymbol: false,
          lineStyle: { width: i === 0 ? 3.4 : 2.2 }, itemStyle: { color: SLOT_COLORS[i] }, color: SLOT_COLORS[i],
          endLabel: { show: true, formatter: trunc(occName(byCode[code]), 24), fontSize: 11,
                      color: SLOT_COLORS[i], fontWeight: 600, distance: 6 },
          labelLayout: { moveOverlap: "shiftY" },
          data: idx.slice(start)
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
      var smoothTxt = state.smooth > 1
        ? (EN ? ", " + state.smooth + "-month trailing average" : ", " + state.smooth + " mnd glidende snitt")
        : (EN ? ", unsmoothed" : ", uglattet");
      setText("lm-note", (state.outcome === "employment"
        ? (EN ? "Employment" : "Sysselsetting") : (EN ? "Pay per full-time equivalent" : "Lønn per fulltidsekvivalent")) +
        (EN ? ", seasonally adjusted" : ", sesongjustert") + smoothTxt +
        (EN ? ", private sector, ages 21–60. Index 100 in February 2025."
            : ", privat sektor, 21–60 år. Indeks 100 i februar 2025.") +
        (missing.length ? (EN ? " No series (fewer than 30 employees): " : " Ingen serie (under 30 lønnstakere): ") +
          missing.join(", ") + "." : ""));
    }

    // ---- Sammendrag for hovedyrket, skrevet som tekst fra dataene ----
    // Tre avsnitt: hvor stort yrket er og hvor eksponert det er; hvordan
    // Claude brukes paa oppgavene; hvordan sysselsetting og loenn har gaatt
    // siden Claude Code. Samme tall som figurene under, saa teksten og
    // figurene kan sjekkes mot hverandre.
    function qWord(q) {
      if (!q) return "";
      if (EN) return [", among the least exposed occupations", ", below the middle", ", in the middle",
                      ", above the middle", ", among the most exposed occupations"][q - 1];
      return [", blant de minst eksponerte yrkene", ", under midten", ", midt på treet",
              ", over midten", ", blant de mest eksponerte yrkene"][q - 1];
    }
    // Yrkesnavn midt i en overskrift: liten forbokstav, unntatt forkortelser
    // som «IKT-...» der andre bokstav ogsaa er stor.
    function lcFirst(s) {
      return s.length > 1 && s.charAt(1) === s.charAt(1).toLowerCase() ? s.charAt(0).toLowerCase() + s.slice(1) : s;
    }
    function renderSummary() {
      var box = el("pick-summary"), o = focus();
      setAll(".occ-focus-name", o ? lcFirst(occName(o)) : (EN ? "the chosen occupation" : "valgt yrke"));
      setText("pick-hint", o && state.random
        ? (EN ? "The example was drawn at random. Search for your own occupation above."
              : "Eksempelet er trukket tilfeldig. Søk opp ditt eget yrke over.")
        : "");
      if (!o) { box.innerHTML = ""; return; }
      var c = latestChat(o), a = latestApi(o);
      var chatV = vlabel(vintByKey[latestKey.claude_ai]);
      var p1, p2, p3 = "";
      if (EN) {
        p1 = "<strong>" + occName(o) + "</strong> (STYRK-08 " + o.code + ")" +
          (o.n ? " has " + thousands(o.n) + " private-sector employees."
               : " has fewer than 30 private-sector employees, so there is no monthly series for employment and pay.");
        if (o.beta !== null) {
          p1 += " Its AI exposure is " + num(o.beta, 2) + " on a scale from 0 to 1 (Eloundou et al. 2024). That puts it in the group " +
            qBadge(o.q) + " (" + o.q + " of 5).";
          if (o.mouchel !== null) p1 += " The Mouchel et al. (2026) measure, built on documented AI use, gives " +
            num(o.mouchel, 2) + ", group " + qBadge(o.q_mouchel) + ".";
        }
        if (c && c.auto !== null) {
          p2 = "The occupation's tasks account for " + num(c.u, 2) + " % of all Claude.ai use. When Claude is used on them, " +
            pct(c.auto * 100, 0) + " of conversations are automation, where the model does the work, and " +
            pct(c.aug * 100, 0) + " are augmentation, where the person and the model work together.";
          if (a && a.auto !== null) p2 += " In the API, where developers and agents call the model, " + pct(a.auto * 100, 0) + " is automation.";
          p2 += " The figures are for " + chatV + (c.n ? ", " + thousands(c.n) + " classified conversations." : ".");
        } else {
          p2 = "Anthropic has no usage data for this occupation in the latest sample.";
        }
        var e = changeSince(o.code, "employment"), w = changeSince(o.code, "wages");
        if (e) {
          p3 = "Employment in the occupation was " + num(Math.abs(e.pct), 1) + " % " + (e.pct >= 0 ? "higher" : "lower") +
            " in " + monthLabel(e.date) + " than in February 2025, when Claude Code launched" +
            (w ? ", and pay per full-time equivalent was " + num(Math.abs(w.pct), 1) + " % " + (w.pct >= 0 ? "higher" : "lower") : "") +
            ". The figure below shows the path from two years earlier.";
        }
      } else {
        p1 = "<strong>" + occName(o) + "</strong> (STYRK-08 " + o.code + ")" +
          (o.n ? " har " + thousands(o.n) + " lønnstakere i privat sektor."
               : " har under 30 lønnstakere i privat sektor, så det finnes ingen månedsserie for sysselsetting og lønn.");
        if (o.beta !== null) {
          p1 += " KI-eksponeringen er " + num(o.beta, 2) + " på skalaen fra 0 til 1 (Eloundou m.fl. 2024). Det plasserer yrket i gruppen " +
            qBadge(o.q) + " (" + o.q + " av 5).";
          if (o.mouchel !== null) p1 += " Målet fra Mouchel m.fl. (2026), som bygger på dokumentert KI-bruk, gir " +
            num(o.mouchel, 2) + ", gruppe " + qBadge(o.q_mouchel) + ".";
        }
        if (c && c.auto !== null) {
          p2 = "Oppgavene i yrket står for " + num(c.u, 2) + " % av all bruk av Claude.ai. Når Claude brukes på dem, er " +
            pct(c.auto * 100, 0) + " av samtalene automatisering, der modellen gjør jobben, og " +
            pct(c.aug * 100, 0) + " augmentering, der personen og modellen jobber sammen.";
          if (a && a.auto !== null) p2 += " I API-et, der utviklere og agenter kaller modellen, er " + pct(a.auto * 100, 0) + " automatisering.";
          p2 += " Tallene gjelder " + chatV + (c.n ? ", " + thousands(c.n) + " klassifiserte samtaler." : ".");
        } else {
          p2 = "Anthropic har ingen bruksdata for dette yrket i det siste utvalget.";
        }
        var e2 = changeSince(o.code, "employment"), w2 = changeSince(o.code, "wages");
        if (e2) {
          p3 = "Sysselsettingen i yrket var " + num(Math.abs(e2.pct), 1) + " % " + (e2.pct >= 0 ? "høyere" : "lavere") +
            " i " + monthLabel(e2.date) + " enn i februar 2025, da Claude Code kom" +
            (w2 ? ", og lønna per fulltidsekvivalent var " + num(Math.abs(w2.pct), 1) + " % " + (w2.pct >= 0 ? "høyere" : "lavere") : "") +
            ". Figuren under viser utviklingen fra to år før.";
        }
      }
      // Tre korte setninger synlig; tallene bak «Tallene bak».
      var ch = changeSince(o.code, "employment"), lead = [];
      var name = occName(o);
      if (EN) {
        lead.push(o.q
          ? name + [" is among the least AI-exposed occupations.", " sits below the middle in AI exposure.",
                    " sits in the middle in AI exposure.", " sits above the middle in AI exposure.",
                    " is among the most AI-exposed occupations."][o.q - 1]
          : name + " has no exposure score.");
        lead.push(c && c.auto !== null
          ? (c.auto > 0.5 ? "When Claude is used on its tasks, it usually does the job itself."
                          : "When Claude is used on its tasks, it usually helps rather than replaces.")
          : "Anthropic has no usage data for it.");
        lead.push(ch ? "Employment is " + num(Math.abs(ch.pct), 1) + " % " + (ch.pct >= 0 ? "higher" : "lower") + " than when Claude Code launched."
                     : (o.n ? "" : "The occupation is too small for a monthly series."));
      } else {
        lead.push(o.q
          ? name + [" er blant de minst KI-eksponerte yrkene.", " ligger under midten i KI-eksponering.",
                    " ligger midt på treet i KI-eksponering.", " ligger over midten i KI-eksponering.",
                    " er blant de mest KI-eksponerte yrkene."][o.q - 1]
          : name + " har ingen eksponeringsskår.");
        lead.push(c && c.auto !== null
          ? (c.auto > 0.5 ? "Når Claude brukes på oppgavene, gjør den oftest jobben selv."
                          : "Når Claude brukes på oppgavene, er den oftest en hjelp, ikke en erstatning.")
          : "Anthropic har ingen bruksdata for yrket.");
        lead.push(ch ? "Sysselsettingen er " + num(Math.abs(ch.pct), 1) + " % " + (ch.pct >= 0 ? "høyere" : "lavere") + " enn da Claude Code kom."
                     : (o.n ? "" : "Yrket er for lite til å ha en månedsserie."));
      }
      box.innerHTML = "<p class='pick-lead'>" + lead.filter(Boolean).join(" ") + "</p>" +
        "<details class='more'><summary>" + (EN ? "The numbers behind this" : "Tallene bak") + "</summary>" +
        "<p>" + p1 + "</p><p>" + p2 + "</p>" + (p3 ? "<p>" + p3 + "</p>" : "") + "</details>";
    }

    // ---- De fem typene for hovedyrket: soeyler for siste utvalg, eller
    // endringen i prosentpoeng siden et tidligere utvalg brukeren velger ----
    function fillCompareSelect() {
      var sel = el("types-compare");
      if (!sel) return;
      var p = state.typesPlatform, vs = vintagesFor(p), latest = vs[vs.length - 1];
      sel.innerHTML = "";
      var o0 = document.createElement("option");
      o0.value = ""; o0.textContent = EN ? "Latest sample only (" + vlabel(latest) + ")" : "Bare siste utvalg (" + vlabel(latest) + ")";
      sel.appendChild(o0);
      vs.slice(0, -1).forEach(function (v) {
        var op = document.createElement("option");
        op.value = v.key; op.textContent = (EN ? "Change since " : "Endring siden ") + vlabel(v);
        sel.appendChild(op);
      });
      if (!vintByKey[state.typesCompare] || vintByKey[state.typesCompare].platform !== p) state.typesCompare = "";
      sel.value = state.typesCompare;
    }
    function renderTypes() {
      var o = focus(), c = chart("chart-types");
      if (!o) { c.clear(); return; }
      var p = state.typesPlatform, latestV = vintByKey[latestKey[p]];
      var now = o.v[latestKey[p]];
      var cmpV = state.typesCompare ? vintByKey[state.typesCompare] : null;
      var then = cmpV ? o.v[cmpV.key] : null;
      if (!now || now.auto === null) {
        c.clear();
        setText("types-note", EN ? "No usage data for this occupation." : "Ingen bruksdata for dette yrket.");
        return;
      }
      if (cmpV && (!then || then.auto === null)) {
        c.clear();
        setText("types-note", EN ? "No data for " + vlabel(cmpV) + " for this occupation." : "Ingen data for " + vlabel(cmpV) + " for dette yrket.");
        return;
      }
      var data = TYPES.map(function (t) {
        var v = then ? (now[t] - then[t]) * 100 : now[t] * 100;
        return { value: +v.toFixed(1), itemStyle: { color: TYPE_COLORS[t] },
                 label: { position: v >= 0 ? "top" : "bottom" } };
      });
      c.setOption({
        animationDuration: 300,
        grid: { left: 56, right: 20, top: 36, bottom: 64 },
        graphic: brandGraphic(SRC_AEI),
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: function (ps) {
          var t = TYPES[ps[0].dataIndex];
          var s = "<b>" + TYPE_LABELS[t] + "</b><br>" + vlabel(latestV) + ": " + pct(now[t] * 100, 1);
          if (then) s += "<br>" + vlabel(cmpV) + ": " + pct(then[t] * 100, 1) +
            "<br>" + (EN ? "Change: " : "Endring: ") + (ps[0].value > 0 ? "+" : "") + num(ps[0].value, 1) + " pp";
          return s;
        } },
        xAxis: { type: "category", data: TYPES.map(function (t) { return TYPE_LABELS[t]; }),
                 axisTick: { show: false }, axisLabel: { interval: 0, fontSize: 11, width: typeLabelWidth("chart-types"), overflow: "break", lineHeight: 13 } },
        yAxis: { type: "value", min: then ? null : 0,
                 name: then ? (EN ? "Change, percentage points" : "Endring, prosentpoeng") : (EN ? "Share of conversations" : "Andel av samtalene"),
                 nameTextStyle: { align: "left" },
                 axisLabel: { formatter: function (v) { return then ? (v > 0 ? "+" : "") + v : v + " %"; } },
                 splitLine: { lineStyle: { color: "#eee" } } },
        series: [{ type: "bar", barMaxWidth: 70, data: data,
                   label: { show: true, fontSize: 12, fontWeight: 600,
                            formatter: function (q) { return then ? (q.value > 0 ? "+" : "") + num(q.value, 1) : num(q.value, 0) + " %"; } },
                   markLine: then ? { silent: true, symbol: "none", lineStyle: { color: "#666" }, label: { show: false }, data: [{ yAxis: 0 }] } : undefined }]
      }, true);
      var autoTxt = EN ? "Automation (the two first types) " : "Automatisering (de to første typene) ";
      setText("types-note", then
        ? (EN ? "Change in percentage points from " + vlabel(cmpV) + " to " + vlabel(latestV) + ", " + PLATFORM_LABELS[p] + ". " +
                autoTxt + pct(then.auto * 100, 0) + " → " + pct(now.auto * 100, 0) + "."
              : "Endring i prosentpoeng fra " + vlabel(cmpV) + " til " + vlabel(latestV) + ", " + PLATFORM_LABELS[p] + ". " +
                autoTxt + pct(then.auto * 100, 0) + " → " + pct(now.auto * 100, 0) + ".")
        : (EN ? "Share of classified Claude conversations about the occupation's tasks, " + PLATFORM_LABELS[p] + ", " + vlabel(latestV) +
                (now.n ? ", " + thousands(now.n) + " conversations" : "") + ". " + autoTxt + pct(now.auto * 100, 0) + ", augmentation " + pct(now.aug * 100, 0) + "."
              : "Andel av klassifiserte Claude-samtaler om yrkets oppgaver, " + PLATFORM_LABELS[p] + ", " + vlabel(latestV) +
                (now.n ? ", " + thousands(now.n) + " samtaler" : "") + ". " + autoTxt + pct(now.auto * 100, 0) + ", augmentering " + pct(now.aug * 100, 0) + "."));
    }

    // ---- Yrker som ligner: en liste, ett yrke per rad ----
    function renderNeighbours() {
      var box = el("pick-neighbours"), o = focus();
      box.innerHTML = "";
      if (!o) return;
      if (!o.nb.length) {
        box.innerHTML = "<li>" + (EN ? "No O*NET profile for this occupation." : "Ingen O*NET-profil for dette yrket.") + "</li>";
        setText("nb-note", "");
        return;
      }
      o.nb.forEach(function (nb) {
        var n = anyOcc(nb.code);
        if (!n) return;
        var hasData = !!byCode[nb.code];
        var c = hasData ? latestChat(n) : null;
        var li = document.createElement("li");
        var facts = [(EN ? "Similarity " : "Likhet ") + num(nb.sim, 2)];
        if (n.n) facts.push(thousands(n.n) + (EN ? " employees" : " lønnstakere"));
        if (n.q) facts.push((EN ? "exposure " : "eksponering ") + (n.beta !== null && n.beta !== undefined ? num(n.beta, 2) + " " : "") + qBadge(n.q));
        if (c && c.auto !== null) facts.push((EN ? "automation in chat " : "automatisering i chat ") + pct(c.auto * 100, 0));
        else if (!hasData) facts.push(EN ? "no Claude usage data" : "ingen bruksdata fra Claude");
        var inList = state.occs.indexOf(nb.code) >= 0;
        li.innerHTML = "<span class='nb-name'>" + occName(n) + "</span> <span class='occ-code'>" + nb.code + "</span>" +
          "<span class='nb-facts'>" + facts.join(" · ") + "</span>" +
          (nb.shared && nb.shared.length
            ? "<span class='nb-shared'>" + (EN ? "In common: " : "Felles arbeidsinnhold: ") +
              nb.shared.map(onetName).join(", ") + "</span>" : "");
        if (hasData) {
          var act = document.createElement("span");
          act.className = "nb-actions";
          var b1 = document.createElement("button");
          b1.type = "button"; b1.className = "link-btn";
          b1.textContent = inList ? (EN ? "In the list" : "Er i lista") : (EN ? "Add to the list" : "Legg til i lista");
          b1.disabled = inList;
          b1.addEventListener("click", function () { addOcc(nb.code); });
          var b2 = document.createElement("button");
          b2.type = "button"; b2.className = "link-btn";
          b2.textContent = EN ? "Make this the main occupation" : "Gjør til hovedyrke";
          b2.addEventListener("click", function () { state.random = false; setFocus(nb.code); });
          act.appendChild(b1); act.appendChild(document.createTextNode(" · ")); act.appendChild(b2);
          li.appendChild(act);
        }
        box.appendChild(li);
      });
      setText("nb-note", EN
        ? "Closest to " + occName(o) + " by O*NET work activities and skills."
        : "Nærmest " + occName(o) + " etter O*NETs arbeidsaktiviteter og ferdigheter.");
    }

    // ---- Oppgavene i hovedyrket: histogram over de fem stoerste, klikk gir
    // soeylediagram over de fem typene med endring siden valgt utvalg ----
    function taskRec(arr) {
      return arr ? { d: arr[0], fb: arr[1], ti: arr[2], va: arr[3], le: arr[4], n: arr[5], u: arr[6], auto: arr[0] + arr[1] } : null;
    }
    function barTypes(id, now, then, nowLab, thenLab, src) {
      var data = TYPES.map(function (t) {
        var v = then ? (now[t] - then[t]) * 100 : now[t] * 100;
        return { value: +v.toFixed(1), itemStyle: { color: TYPE_COLORS[t] }, label: { position: v >= 0 ? "top" : "bottom" } };
      });
      chart(id).setOption({
        animationDuration: 300,
        grid: { left: 56, right: 20, top: 36, bottom: 64 },
        graphic: brandGraphic(src),
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: function (ps) {
          var t = TYPES[ps[0].dataIndex], s = "<b>" + TYPE_LABELS[t] + "</b><br>" + nowLab + ": " + pct(now[t] * 100, 1);
          if (then) s += "<br>" + thenLab + ": " + pct(then[t] * 100, 1) + "<br>" + (EN ? "Change: " : "Endring: ") + (ps[0].value > 0 ? "+" : "") + num(ps[0].value, 1) + " pp";
          return s;
        } },
        xAxis: { type: "category", data: TYPES.map(function (t) { return TYPE_LABELS[t]; }), axisTick: { show: false },
                 axisLabel: { interval: 0, fontSize: 11, width: typeLabelWidth(id), overflow: "break", lineHeight: 13 } },
        yAxis: { type: "value", min: then ? null : 0,
                 name: then ? (EN ? "Change, percentage points" : "Endring, prosentpoeng") : (EN ? "Share of conversations" : "Andel av samtalene"),
                 nameTextStyle: { align: "left" }, axisLabel: { formatter: function (v) { return then ? (v > 0 ? "+" : "") + v : v + " %"; } },
                 splitLine: { lineStyle: { color: "#eee" } } },
        series: [{ type: "bar", barMaxWidth: 70, data: data,
                   label: { show: true, fontSize: 12, fontWeight: 600, formatter: function (q) { return then ? (q.value > 0 ? "+" : "") + num(q.value, 1) : num(q.value, 0) + " %"; } },
                   markLine: then ? { silent: true, symbol: "none", lineStyle: { color: "#666" }, label: { show: false }, data: [{ yAxis: 0 }] } : undefined }]
      }, true);
    }
    function curTask() {
      var o = focus(), tasks = o ? (o.tasks[state.taskPlatform] || []) : [];
      return tasks[state.task] || null;
    }
    function fillTaskCompare() {
      var sel = el("task-compare"), t = curTask();
      if (!sel) return;
      sel.innerHTML = "";
      var p = state.taskPlatform, vs = vintagesFor(p), latest = vs[vs.length - 1];
      var o0 = document.createElement("option");
      o0.value = ""; o0.textContent = EN ? "Latest sample only (" + vlabel(latest) + ")" : "Bare siste utvalg (" + vlabel(latest) + ")";
      sel.appendChild(o0);
      vs.slice(0, -1).forEach(function (v) {
        if (!t || !t.v || !t.v[v.key]) return;
        var op = document.createElement("option");
        op.value = v.key; op.textContent = (EN ? "Change since " : "Endring siden ") + vlabel(v);
        sel.appendChild(op);
      });
      if (!t || !t.v || !t.v[state.taskCompare]) state.taskCompare = "";
      sel.value = state.taskCompare;
    }
    function renderTaskChart() {
      var t = curTask(), c = chart("chart-task"), p = state.taskPlatform;
      if (!t) { c.clear(); setText("task-title", ""); setText("task-note", ""); return; }
      setText("task-title", (EN ? "How Claude is used on: " : "Slik brukes Claude på: ") + (EN ? cap(t.t) : (t.t_no || t.t)));
      var latestV = vintByKey[latestKey[p]], now = taskRec(t.v && t.v[latestKey[p]]) || { d: t.d, fb: t.fb, ti: t.ti, va: t.va, le: t.le, n: t.n, u: t.pct, auto: t.d + t.fb };
      var cmpV = state.taskCompare ? vintByKey[state.taskCompare] : null, then = cmpV ? taskRec(t.v[cmpV.key]) : null;
      barTypes("chart-task", now, then, vlabel(latestV), cmpV ? vlabel(cmpV) : "", SRC_AEI);
      setText("task-note", then
        ? (EN ? "Change in percentage points from " + vlabel(cmpV) + " to " + vlabel(latestV) + ", " + PLATFORM_LABELS[p] + ". Automation " + pct(then.auto * 100, 0) + " → " + pct(now.auto * 100, 0) + "."
              : "Endring i prosentpoeng fra " + vlabel(cmpV) + " til " + vlabel(latestV) + ", " + PLATFORM_LABELS[p] + ". Automatisering " + pct(then.auto * 100, 0) + " → " + pct(now.auto * 100, 0) + ".")
        : (EN ? PLATFORM_LABELS[p] + ", " + vlabel(latestV) + (now.n ? ", " + thousands(now.n) + " classified conversations" : "") + ". Automation (directive + feedback loop) " + pct(now.auto * 100, 0) + "."
              : PLATFORM_LABELS[p] + ", " + vlabel(latestV) + (now.n ? ", " + thousands(now.n) + " klassifiserte samtaler" : "") + ". Automatisering (direkte delegering + tilbakemeldingssløyfe) " + pct(now.auto * 100, 0) + "."));
    }
    function fillTasksCompare(tasks) {
      // «Vis»: nivaa i siste utvalg, eller endring i bruksandel siden et tidligere utvalg der noen av oppgavene har data.
      var sel = el("tasks-compare");
      if (!sel) return;
      var p = state.taskPlatform, vs = vintagesFor(p), latest = vs[vs.length - 1];
      sel.innerHTML = "";
      var o0 = document.createElement("option");
      o0.value = ""; o0.textContent = EN ? "Level, latest sample (" + vlabel(latest) + ")" : "Nivå, siste utvalg (" + vlabel(latest) + ")";
      sel.appendChild(o0);
      var ok = { "": true };
      vs.slice(0, -1).forEach(function (v) {
        if (!tasks.some(function (t) { return t.v && t.v[v.key] && t.v[v.key][6]; })) return;
        var op = document.createElement("option");
        op.value = v.key; op.textContent = (EN ? "Change since " : "Endring siden ") + vlabel(v);
        sel.appendChild(op); ok[v.key] = true;
      });
      if (!ok[state.tasksCompare]) state.tasksCompare = "";
      sel.value = state.tasksCompare;
    }
    function renderTasks() {
      // Histogram over de fem eller ti oppgavene med mest bruk. Nivaa: stolpe = andel av
      // all Claude-bruk paa plattformen, delt i automatisering og augmentering. Endring:
      // prosent endring i oppgavens bruksandel siden valgt utvalg, nullinje i midten.
      var o = focus(), box = el("chart-tasks"), c = chart("chart-tasks"), p = state.taskPlatform;
      var tasks = o ? (o.tasks[p] || []).slice(0, state.taskCount) : [];
      if (!tasks.length) {
        c.clear();
        setText("y4-note", EN ? "No task-level data for this occupation." : "Ingen oppgavedata for dette yrket.");
        state.task = 0; fillTasksCompare([]); fillTaskCompare(); renderTaskChart();
        return;
      }
      if (state.task >= tasks.length) state.task = 0;
      fillTasksCompare(tasks);
      var latestV = vintByKey[latestKey[p]], cmpV = state.tasksCompare ? vintByKey[state.tasksCompare] : null, isChg = !!cmpV;
      var AUTO = EN ? "Automation" : "Automatisering", AUG = EN ? "Augmentation" : "Augmentering";
      var labW = Math.max(120, Math.min(320, Math.round(box.clientWidth * 0.42)));
      var wide = box.clientWidth >= 700;
      var names = tasks.map(function (t, i) { return (i + 1) + ". " + (EN ? cap(t.t) : (t.t_no || t.t)); });
      // O*NET: hvor viktig oppgaven er for yrket (IM 1-5) og rangen blant yrkets oppgaver (IM x RT).
      function impLine(t) {
        if (t.im === null || t.im === undefined) return "";
        return EN ? "Importance to the occupation " + num(t.im, 1) + " of 5" + (t.rk ? " · no. " + t.rk + " of " + t.nt + " tasks" : "")
                  : "Betydning for yrket " + num(t.im, 1) + " av 5" + (t.rk ? " · nr. " + t.rk + " av " + t.nt + " oppgaver" : "");
      }
      function uAt(t, key) { var x = t.v && t.v[key]; return x && x[6] ? x[6] : null; }
      var uNow = tasks.map(function (t) { return uAt(t, latestV.key) || t.pct; });
      var chg = isChg ? tasks.map(function (t, i) { var u0 = uAt(t, cmpV.key); return u0 ? +((uNow[i] / u0 - 1) * 100).toFixed(1) : null; }) : null;
      var auto = tasks.map(function (t) { return +(t.pct * (t.d + t.fb)).toFixed(4); });
      var aug = tasks.map(function (t) { return +(t.pct * Math.max(0, 1 - t.d - t.fb)).toFixed(4); });
      // Radhoeyde etter den lengste etiketten (ca. 6,2 px per tegn ved 11 px), saa radene ikke overlapper.
      var lines = Math.max.apply(null, names.map(function (nm) { return Math.ceil(nm.length * 6.2 / labW); }));
      var rowH = Math.max(52, lines * 14 + 16), chartH = 96 + tasks.length * rowH;
      sizeChart("chart-tasks", chartH);
      // Betydningslinjen som liten graa tekst rett under hver stolpe: rad i har
      // sentrum i gridTop + band * (i + 0.5); stolpen er hoeyst 26 px hoey.
      var gridTop = 34, gridBottom = 70, band = (chartH - gridTop - gridBottom) / tasks.length;
      var impGraphics = tasks.map(function (t, i) {
        var l = impLine(t);
        if (!l) return null;
        return { type: "text", silent: true, left: labW + 16, top: gridTop + band * (i + 0.5) + 13 + 3,
                 style: { text: l, fontSize: 10, fill: "#8a877f" } };
      }).filter(Boolean);
      var xAxis, series;
      if (isChg) {
        // Fast aksesteg ogsaa her; nullinja er alltid med, og litt luft til hoeyre for etikettene.
        var vals = chg.filter(function (v) { return v !== null; });
        var lo = Math.min(0, Math.min.apply(null, vals.concat([0]))), hi = Math.max(0, Math.max.apply(null, vals.concat([0]))), span = (hi - lo) || 10;
        var cs = [5, 10, 20, 25, 50, 100, 200, 500, 1000, 2000], nT = wide ? 6 : 3, cstep = cs[cs.length - 1];
        for (var j = 0; j < cs.length; j++) { if (span / cs[j] <= nT) { cstep = cs[j]; break; } }
        var xMin = lo < 0 ? Math.floor(lo / cstep) * cstep : 0, xMax = Math.ceil((hi + span * (wide ? 0.06 : 0.25)) / cstep) * cstep;
        xAxis = { type: "value", min: xMin, max: xMax, interval: cstep,
                  name: EN ? "Change in share of all Claude use since " + vlabel(cmpV) + ", per cent" : "Endring i andel av all Claude-bruk siden " + vlabel(cmpV) + ", prosent",
                  nameLocation: "middle", nameGap: 30, nameTextStyle: { fontSize: 11 },
                  axisLabel: { formatter: function (v) { return (v > 0 ? "+" : "") + num(v, 0) + " %"; } },
                  splitLine: { lineStyle: { color: "#eee" } } };
        series = [{ name: EN ? "Change" : "Endring", type: "bar", barMaxWidth: 26, itemStyle: { color: "#577590" },
                    data: chg,
                    label: { show: true, position: "right", fontSize: 11, fontWeight: 600, color: "#2b3e50",
                             formatter: function (q) { return (q.value > 0 ? "+" : "") + num(q.value, 0) + " %"; } },
                    markLine: { silent: true, symbol: "none", lineStyle: { color: "#666" }, label: { show: false }, data: [{ xAxis: 0 }] } }];
      } else {
        // Fast aksesteg: faa merker paa smale skjermer, saa de ikke overlapper.
        var maxU = Math.max.apply(null, tasks.map(function (t) { return t.pct || 0; })) || 0.01;
        var steps = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10], nTicks = wide ? 5 : 2, step = steps[steps.length - 1];
        for (var k = 0; k < steps.length; k++) { if (maxU / steps[k] <= nTicks) { step = steps[k]; break; } }
        var axMax = Math.ceil(maxU / step - 1e-9) * step, dec = step < 0.01 ? 3 : (step < 0.1 ? 2 : 1);
        xAxis = { type: "value", min: 0, max: axMax, interval: step,
                  name: EN ? "Share of all Claude.ai conversations, all occupations" : "Andel av alle Claude.ai-samtaler, alle yrker",
                  nameLocation: "middle", nameGap: 30, nameTextStyle: { fontSize: 11 },
                  axisLabel: { formatter: function (v) { return num(v, dec) + " %"; } },
                  splitLine: { lineStyle: { color: "#eee" } } };
        series = [
          { name: AUTO, type: "bar", stack: "s", barMaxWidth: 26, data: auto, itemStyle: { color: AUTO_COLOR } },
          { name: AUG, type: "bar", stack: "s", barMaxWidth: 26, data: aug, itemStyle: { color: AUG_COLOR },
            label: { show: true, position: "right", fontSize: 11, fontWeight: 600, color: AUTO_COLOR,
                     formatter: function (q) { var t = tasks[q.dataIndex]; return pct((t.d + t.fb) * 100, 0) + (wide ? " " + AUTO.toLowerCase() : ""); } } }
        ];
      }
      c.setOption({
        animationDuration: 300,
        grid: { left: labW + 14, right: wide ? 130 : 48, top: gridTop, bottom: gridBottom },
        graphic: [].concat(brandGraphic(SRC_AEI), impGraphics),
        legend: { show: !isChg, top: 0, right: 8, itemWidth: 12, itemHeight: 12, itemGap: 10, data: [AUTO, AUG] },
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: function (ps) {
          var i = ps[0].dataIndex, t = tasks[i], h = "<b>" + (EN ? cap(t.t) : (t.t_no || t.t)) + "</b><br>";
          var ol = impLine(t);
          if (ol) h += "<span style='color:#8a877f'>" + ol + (t.rt !== null && t.rt !== undefined ? (EN ? " · relevant for " : " · gjelder ") + pct(t.rt, 0) + (EN ? " of incumbents" : " av utøverne") : "") + "</span><br>";
          if (isChg) {
            var u0 = uAt(t, cmpV.key), k = uNow[i] ? t.pct / uNow[i] : 1;
            h += (EN ? "Share of all Claude use, all occupations: " : "Andel av all Claude-bruk, alle yrker: ") + (u0 ? pct(u0 * k, 2) : "–") + " (" + vlabel(cmpV) + ") → " + pct(t.pct, 2) + " (" + vlabel(latestV) + ")";
            h += "<br>" + (EN ? "Change: " : "Endring: ") + (chg[i] === null ? (EN ? "no data in " : "ingen data i ") + vlabel(cmpV) : (chg[i] > 0 ? "+" : "") + num(chg[i], 0) + " %");
            h += "<br>" + AUTO + " " + pct((t.d + t.fb) * 100, 0) + " (" + vlabel(latestV) + ")";
          } else {
            h += (EN ? "Share of all Claude use, all occupations: " : "Andel av all Claude-bruk, alle yrker: ") + pct(t.pct, 2) + " · " + thousands(t.n) + (EN ? " conversations" : " samtaler") +
              "<br>" + AUTO + " " + pct((t.d + t.fb) * 100, 0) + " · " + AUG + " " + pct((1 - t.d - t.fb) * 100, 0);
          }
          return h;
        } },
        xAxis: xAxis,
        yAxis: { type: "category", inverse: true, data: names, triggerEvent: true,
                 axisTick: { show: false }, axisLine: { show: false },
                 axisLabel: { interval: 0, fontSize: 11, lineHeight: 14, width: labW, overflow: "break",
                              color: function (v, i) { return i === state.task ? "#0f4c81" : "#4a5868"; } } },
        series: series
      }, true);
      c.off("click");
      c.on("click", function (e) {
        var i = e.componentType === "yAxis" ? names.indexOf(e.value) : e.dataIndex;
        if (i === undefined || i < 0) return;
        state.task = i; state.taskCompare = ""; renderTasks();
      });
      var n = tasks.length, nLab = EN ? (n === 5 ? "five" : n === 10 ? "ten" : String(n)) : (n === 5 ? "fem" : n === 10 ? "ti" : String(n));
      if (isChg) {
        var miss = chg.filter(function (v) { return v === null; }).length;
        setText("y4-note", EN
          ? occName(o) + ": the " + nLab + " tasks with most Claude use in " + vlabel(latestV) + ", and the change in each task's share of all Claude use since " + vlabel(cmpV) + ", " + PLATFORM_LABELS[p] + "." +
            (miss ? " " + miss + " task" + (miss > 1 ? "s" : "") + " without data in " + vlabel(cmpV) + " " + (miss > 1 ? "have" : "has") + " no bar." : "") + " Click a task."
          : occName(o) + ": de " + nLab + " oppgavene med mest Claude-bruk i " + vlabel(latestV) + ", og endringen i hver oppgaves andel av all Claude-bruk siden " + vlabel(cmpV) + ", " + PLATFORM_LABELS[p] + "." +
            (miss ? " " + miss + " oppgave" + (miss > 1 ? "r" : "") + " uten data i " + vlabel(cmpV) + " har ingen stolpe." : "") + " Klikk på en oppgave.");
      } else {
        setText("y4-note", EN
          ? occName(o) + ": the " + nLab + " tasks with most Claude use, " + PLATFORM_LABELS[p] + ", " + vlabel(latestV) + ". The share is of all conversations in Anthropic's sample, not of this occupation's; a task several occupations share is split evenly between them. Importance from O*NET 30.1. Click a task."
          : occName(o) + ": de " + nLab + " oppgavene med mest Claude-bruk, " + PLATFORM_LABELS[p] + ", " + vlabel(latestV) + ". Andelen er av alle samtaler i Anthropics utvalg, ikke av yrkets; en oppgave flere yrker deler, er delt likt mellom dem. Betydning fra O*NET 30.1. Klikk på en oppgave.");
      }
      fillTaskCompare(); renderTaskChart();
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
                 data: vs.map(function (v) {
                   var x = o.v[v.key];
                   if (!x) return null;
                   return state.tidMeasure === "u" ? (x.u === null ? null : +x.u.toFixed(3)) : (x.auto === null ? null : +(x.auto * 100).toFixed(1));
                 }) };
      });
      var isU = state.tidMeasure === "u";
      // Referanse: alle yrker med sysselsettingstall, vektet med sysselsetting.
      var ref = vs.map(function (v) {
        var w = 0, s = 0;
        Y.occupations.forEach(function (o) {
          var x = o.v[v.key];
          if (x && x.auto !== null && o.n) { w += o.n; s += o.n * x.auto; }
        });
        return w ? +(100 * s / w).toFixed(1) : null;
      });
      if (!isU) series.push({ name: EN ? "All occupations, employment-weighted" : "Alle yrker, sysselsettingsvektet", type: "line",
                    symbol: "circle", symbolSize: 5, lineStyle: { width: 1.6, type: "dashed", color: "#8a877f" },
                    itemStyle: { color: "#8a877f" }, color: "#8a877f",
                    endLabel: { show: true, formatter: EN ? "All occupations" : "Alle yrker", fontSize: 11, color: "#8a877f", distance: 6 },
                    labelLayout: { moveOverlap: "shiftY" }, data: ref });
      chart("chart-y3").setOption({
        animationDuration: 300,
        grid: { left: 50, right: 200, top: 40, bottom: 44, containLabel: true },
        graphic: brandGraphic(SRC_AEI),
        tooltip: { trigger: "axis", valueFormatter: function (v) { return v === null ? "–" : (isU ? num(v, 2) + " %" : pct(v, 1)); } },
        xAxis: { type: "category", data: vs.map(vlabel), boundaryGap: false },
        yAxis: { type: "value", min: 0, max: isU ? null : 100, axisLabel: { formatter: function (v) { return v + " %"; } },
                 name: isU ? (EN ? "Share of all Claude use (%)" : "Andel av all Claude-bruk (%)") : "", nameGap: 16, nameTextStyle: { align: "left" },
                 splitLine: { lineStyle: { color: "#eee" } } },
        series: series
      }, true);
      setText("y3-note", isU
        ? (EN ? "The occupation's tasks as a share of all Claude.ai use, per sample. A falling share alongside a falling automation share means the automated tasks are leaving the channel, not that automation stopped. The first chat point is Handa et al. (2025), Dec 2024 to Jan 2025; later points are one week each."
              : "Yrkets oppgaver som andel av all Claude.ai-bruk, per utvalg. Faller bruksandelen samtidig med automatiseringsandelen, er det de automatiserte oppgavene som forlater kanalen, ikke automatiseringen som stopper. Det første chat-punktet er Handa m.fl. (2025), des. 2024 til jan. 2025; de neste er én uke hver.")
        : (EN ? "Automation share (directive + feedback loop) per sample, " + PLATFORM_LABELS[state.tidPlatform] + ". Grey dashed line: all occupations, weighted by employment. The share is conditional on the task still being used in the channel, so it understates automation where it succeeds. Occupations with few conversations swing a lot between samples."
              : "Automatiseringsandel (direkte delegering + tilbakemeldingssløyfe) per utvalg, " + PLATFORM_LABELS[state.tidPlatform] + ". Grå stiplet linje: alle yrker, vektet med sysselsetting. Andelen er betinget på at oppgaven fortsatt brukes i kanalen, så den undervurderer automatisering der den lykkes. Yrker med få samtaler svinger mye mellom utvalg."));
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
      renderChips(); renderSummary(); renderLM(); renderTypes(); renderNeighbours(); renderTasks(); renderTid();
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
        b.innerHTML = occName(o) + " <span class='occ-small'>" + o.code +
          (o.n ? " · " + thousands(o.n) + (EN ? " employees" : " lønnstakere") : "") + "</span>";
        b.addEventListener("click", function () {
          el("occ-search").value = ""; ul.hidden = true; state.random = false; setFocus(o.code);
        });
        li.appendChild(b); ul.appendChild(li);
      });
      ul.hidden = !hits.length;
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
    el("occ-random").addEventListener("click", function () { state.random = true; randomOcc(); });
    el("occ-add-nb").addEventListener("click", addNeighbours);
    makeButtons("lm-outcome-buttons", [
      { value: "employment", label: EN ? "Employment" : "Sysselsetting" },
      { value: "wages", label: EN ? "Pay (FTE)" : "Lønn (FTE)" }
    ], function () { return state.outcome; }, function (v) { state.outcome = v; renderLM(); });
    // Glatting: samme valg som paa forsiden. Sammendraget bruker samme serie.
    if (el("lm-smooth")) {
      el("lm-smooth").value = String(state.smooth);
      el("lm-smooth").addEventListener("change", function (e) {
        state.smooth = +e.target.value; renderLM(); renderSummary();
      });
    }
    makeButtons("types-platform-buttons", ["claude_ai", "api"].map(function (p) { return { value: p, label: PLATFORM_LABELS[p] }; }),
      function () { return state.typesPlatform; },
      function (p) { state.typesPlatform = p; fillCompareSelect(); renderTypes(); });
    fillCompareSelect();
    if (el("types-compare")) el("types-compare").addEventListener("change", function (e) {
      state.typesCompare = e.target.value; renderTypes();
    });
    makeButtons("task-platform-buttons", ["claude_ai", "api"].map(function (p) { return { value: p, label: PLATFORM_LABELS[p] }; }),
      function () { return state.taskPlatform; }, function (p) { state.taskPlatform = p; state.task = 0; state.taskCompare = ""; renderTasks(); });
    makeButtons("tid-platform-buttons", ["claude_ai", "api"].map(function (p) { return { value: p, label: PLATFORM_LABELS[p] }; }),
      function () { return state.tidPlatform; }, function (p) { state.tidPlatform = p; renderTid(); });
    // Dyplenker for oppgavefiguren: ?oppgaver=10 og ?endring=<utvalg>, f.eks. endring=claude_ai|2025-08-04.
    var qTasks = (location.search.match(/[?&]oppgaver=(\d+)/) || [])[1];
    if (qTasks === "10") state.taskCount = 10;
    var qChg = (location.search.match(/[?&]endring=([^&]+)/) || [])[1];
    if (qChg) state.tasksCompare = decodeURIComponent(qChg);
    makeButtons("tasks-count-buttons", [
      { value: 5, label: EN ? "Top 5" : "Topp 5" },
      { value: 10, label: EN ? "Top 10" : "Topp 10" }
    ], function () { return state.taskCount; }, function (v) { state.taskCount = v; renderTasks(); });
    if (el("tasks-compare")) el("tasks-compare").addEventListener("change", function (e) { state.tasksCompare = e.target.value; renderTasks(); });
    makeButtons("tid-measure-buttons", [
      { value: "u", label: EN ? "Share of all Claude use" : "Andel av all Claude-bruk" },
      { value: "auto", label: EN ? "Automation share" : "Automatiseringsandel" }
    ], function () { return state.tidMeasure; }, function (v) { state.tidMeasure = v; renderTid(); });
    if (el("task-compare")) el("task-compare").addEventListener("change", function (e) { state.taskCompare = e.target.value; renderTaskChart(); });
    makeButtons("y-platform-buttons", ["claude_ai", "api"].map(function (p) { return { value: p, label: PLATFORM_LABELS[p] }; }),
      function () { return state.platform; },
      function (p) { state.platform = p; state.vintage = latestKey[p]; makeVintageButtons(); renderKpi(); renderY1(); });
    function makeVintageButtons() {
      makeButtons("y-vintage-buttons", vintagesFor(state.platform).map(function (v) { return { value: v.key, label: vlabel(v) }; }),
        function () { return state.vintage; }, function (k) { state.vintage = k; renderKpi(); renderY1(); });
    }
    makeVintageButtons();
    renderKpi(); renderY1(); renderY2();

    // Hele lista for én eksponeringsgruppe, nederst paa siden (2026-09-25).
    // Universet er alle yrker siden kjenner: Y.occupations, Y.extra og
    // occupations.json fra forsiden. Kvintilen er den samme i alle tre.
    var allOcc = {};
    OCC.occupations.forEach(function (o) {
      if (o.quintile) allOcc[o.code] = { code: o.code, name: o.name, name_en: o.name_en, n: o.n_base, q: o.quintile, beta: null };
    });
    Object.keys(extra).forEach(function (c) {
      var o = extra[c];
      var prev = allOcc[c];
      if (o.q) allOcc[c] = { code: c, name: o.name, name_en: o.name_en, n: o.n || (prev ? prev.n : null), q: o.q, beta: o.beta };
    });
    Y.occupations.forEach(function (o) {
      var prev = allOcc[o.code];
      if (o.q) allOcc[o.code] = { code: o.code, name: o.name, name_en: o.name_en,
                                  n: o.n || (prev ? prev.n : null), q: o.q, beta: o.beta };
    });
    state.group = 5;
    function renderGroup() {
      var box = el("grp-table");
      if (!box) return;
      var rows = Object.keys(allOcc).map(function (c) { return allOcc[c]; })
        .filter(function (o) { return o.q === state.group; })
        .sort(function (a, b) {
          var ba = a.beta === null || a.beta === undefined ? -1 : a.beta;
          var bb = b.beta === null || b.beta === undefined ? -1 : b.beta;
          return bb - ba || occName(a).localeCompare(occName(b), EN ? "en" : "nb");
        });
      var tot = rows.reduce(function (s, o) { return s + (o.n || 0); }, 0);
      setText("grp-summary", EN
        ? GROUP_NAMES[state.group - 1] + ": " + rows.length + " occupations with " + thousands(tot) + " private-sector employees in November 2022."
        : GROUP_NAMES[state.group - 1] + ": " + rows.length + " yrker med " + thousands(tot) + " lønnstakere i privat sektor i november 2022.");
      var h = "<table class='data-table'><thead><tr><th>#</th><th>" + (EN ? "Occupation (STYRK-08)" : "Yrke (STYRK-08)") +
        "</th><th class='num'>" + (EN ? "Employees Nov 2022" : "Lønnstakere nov. 2022") +
        "</th><th class='num'>" + (EN ? "AI exposure (0–1)" : "KI-eksponering (0–1)") + "</th></tr></thead><tbody>";
      rows.forEach(function (o, i) {
        var link = byCode[o.code]
          ? "<a href='#velg' class='grp-pick' data-code='" + o.code + "'>" + occName(o) + "</a>"
          : occName(o);
        h += "<tr><td>" + (i + 1) + "</td><td>" + link + " <span class='occ-code'>" + o.code + "</span></td><td class='num'>" +
          (o.n ? thousands(o.n) : "–") + "</td><td class='num'>" +
          (o.beta === null || o.beta === undefined ? "–" : num(o.beta, 2)) + "</td></tr>";
      });
      h += "</tbody></table>";
      box.innerHTML = h;
      Array.prototype.forEach.call(box.querySelectorAll("a.grp-pick"), function (a) {
        a.addEventListener("click", function (e) {
          e.preventDefault();
          state.random = false;
          setFocus(a.getAttribute("data-code"));
          var top = el("velg");
          if (top) top.scrollIntoView({ behavior: "smooth" });
        });
      });
      setText("grp-note", EN
        ? "Occupations without a link have no Claude data and cannot be selected above. A dash under employees means the data have no private-sector count for the occupation. A dash under exposure means the page has no score for it. Sources: Eloundou et al. (2024), A-ordningen via microdata.no."
        : "Yrker uten lenke har ikke Claude-data og kan ikke velges øverst. Strek under lønnstakere betyr at dataene ikke har tall for privat sektor i yrket. Strek under eksponering betyr at siden ikke har skår for yrket. Kilder: Eloundou m.fl. (2024), A-ordningen via microdata.no.");
    }
    makeButtons("grp-buttons", [1, 2, 3, 4, 5].map(function (q) { return { value: q, label: GROUP_NAMES[q - 1] }; }),
      function () { return state.group; }, function (q) { state.group = q; renderGroup(); });
    renderGroup();

    var fromUrl = (location.search.match(/[?&]yrke=(\d{4})/) || [])[1];
    if (fromUrl && byCode[fromUrl]) { state.random = false; startFrom(fromUrl); }
    else { state.random = true; randomOcc(); }
  }

  // ==================================================================
  // UTDANNING
  // ==================================================================

  function initUtdanning(U) {
    // Studievalget: nivaa (bachelor som standard) og faggruppe (NUS2000,
    // tresifret). For valget: en kort setning med tallene bak, de ti
    // vanligste oppgavene i jobbene utdanningen foerer til (klikk paa en
    // oppgave for Claude-bruken), og de vanligste jobbene.
    var groups = U.groups, levels = U.levels;
    var byCode = {};
    groups.forEach(function (g) { byCode[g.code] = g; });
    var VLAB = EN ? { v1: "Eloundou et al. (2024)", v2: "Mouchel et al. (2026)" }
                  : { v1: "Eloundou m.fl. (2024)", v2: "Mouchel m.fl. (2026)" };
    var LABEL_WORD = EN ? { E1: "High", E2: "Partial", E0: "None" } : { E1: "Stor", E2: "Delvis", E0: "Ingen" };
    var LABEL_COLOR = { E1: QUINT_COLORS[4], E2: QUINT_COLORS[2], E0: QUINT_COLORS[0] };
    var state = { level: "6", group: null, task: 0, cohort: "all" };
    // «Sterkt», «middels», «lite»: tredeler av faggruppene etter oppgaveskaar.
    var exVals = groups.map(function (g) { return g.task_exposure; })
      .filter(function (v) { return v !== null; }).sort(function (a, b) { return a - b; });
    var T1 = exVals[Math.floor(exVals.length / 3)], T2 = exVals[Math.floor(2 * exVals.length / 3)];
    function exWordFor(ex) {
      if (ex === null) return "";
      if (EN) return ex >= T2 ? "highly" : ex >= T1 ? "moderately" : "little";
      return ex >= T2 ? "sterkt" : ex >= T1 ? "middels" : "lite";
    }

    function levelName(l) {
      var x = levels.filter(function (v) { return v.code === l; })[0];
      return x ? (EN ? x.name_en : x.name) : l;
    }
    function levelLow(l) { var s = levelName(l); return s.charAt(0).toLowerCase() + s.slice(1); }
    function groupsFor(l) { return groups.filter(function (g) { return g.level === l; }); }
    function defaultGroup(l) {
      var gs = groupsFor(l);
      var pref = gs.filter(function (g) { return g.code.slice(1) === "41"; })[0];
      return (pref || gs[0]).code;
    }
    function cur() { return byCode[state.group]; }
    function occNameOf(o) { return EN && o.name_en ? o.name_en : o.name; }
    // ---- Fagvelger: nedtrekksliste som ogsaa tar soekeord ----
    // Treffer faggruppene og navnene paa enkeltutdanningene i registeret
    // (U.names), saa «siviløkonom» eller «master i rettsvitenskap» finner
    // riktig gruppe og nivaa.
    var STOP = EN ? { "in": 1, "of": 1, "and": 1, "the": 1, "a": 1, "an": 1, "with": 1, "degree": 1, "studies": 1 }
                  : { "i": 1, "og": 1, "med": 1, "for": 1, "av": 1, "en": 1, "et": 1, "på": 1, "innen": 1,
                      "fagbrev": 1, "grad": 1, "utdanning": 1, "studium": 1, "studier": 1 };
    var SYN = EN
      ? { lawyer: "law", nurse: "nursing", nurses: "nursing", teacher: "teacher", economist: "economics",
          doctor: "medicine", physician: "medicine", psychologist: "psychology", pharmacist: "pharmacy",
          physiotherapist: "physiotherapy", it: "informatics", computer: "computer", accountant: "accounting",
          auditor: "auditing", engineer: "engineer" }
      : { jurist: "rettsvitenskap", advokat: "rettsvitenskap", jus: "rettsvitenskap", lege: "medisin",
          sykepleier: "sykepleie", lærer: "lærer", økonom: "økonomi", tannlege: "odontologi",
          psykolog: "psykologi", sosionom: "sosialt arbeid", farmasøyt: "farmasi", fysioterapeut: "fysioterapi",
          ergoterapeut: "ergoterapi", vernepleier: "vernepleie", revisor: "revisjon", regnskapsfører: "regnskap",
          it: "informa", ingeniør: "ingeniør", barnehagelærer: "barnehagelærer", siviløkonom: "siviløkonom" };
    function norm(s) { return (s || "").toLowerCase().replace(/[^a-z0-9æøåäöü ]+/g, " ").replace(/\s+/g, " ").trim(); }
    function tokens(q) {
      return norm(q).split(" ").filter(function (t) { return t.length > 1 && !STOP[t]; })
        .map(function (t) { return SYN[t] || t; });
    }
    var INDEX = groups.map(function (g) {
      return { t: "g", code: g.code, hay: norm(g.name + " " + levelName(g.level) + " " + g.field_name), p: g.n_total };
    }).concat((U.names || []).map(function (n) {
      var g = byCode[n.g];
      return { t: "e", code: n.g, name: EN && n.e ? n.e : n.n, sub: n.s, p: n.p,
               hay: norm(n.n + " " + n.s + " " + n.e + " " + (g ? g.name + " " + levelName(g.level) : "")) };
    }));
    function search(q) {
      var ts = tokens(q);
      if (!ts.length) return { groups: [], edu: [] };
      var hits = INDEX.filter(function (e) { return ts.every(function (t) { return e.hay.indexOf(t) >= 0; }); });
      var gs = hits.filter(function (e) { return e.t === "g"; }).sort(function (a, b) { return b.p - a.p; }).slice(0, 5);
      var es = hits.filter(function (e) { return e.t === "e"; }).sort(function (a, b) { return b.p - a.p; }).slice(0, 10);
      return { groups: gs, edu: es };
    }
    function hitButton(label, sub, code) {
      var li = document.createElement("li"), b = document.createElement("button");
      b.type = "button";
      b.innerHTML = label + (sub ? "<span class='hit-sub'>" + sub + "</span>" : "");
      b.addEventListener("click", function () { setGroup(code); });
      li.appendChild(b);
      return li;
    }
    function head(text) { var li = document.createElement("li"); li.className = "hit-head"; li.textContent = text; return li; }
    function renderHits(q) {
      var ul = el("u-hits");
      ul.innerHTML = "";
      if (!tokens(q).length) {
        ul.appendChild(head((EN ? "Fields, " : "Faggrupper, ") + levelLow(state.level)));
        groupsFor(state.level).forEach(function (g) {
          ul.appendChild(hitButton(g.name + " <span class='occ-small'>" + thousands(g.n_total) + "</span>", "", g.code));
        });
      } else {
        var r = search(q);
        if (r.groups.length) {
          ul.appendChild(head(EN ? "Fields" : "Faggrupper"));
          r.groups.forEach(function (e) {
            var g = byCode[e.code];
            ul.appendChild(hitButton(g.name + " <span class='occ-small'>" + levelLow(g.level) + " · " + thousands(g.n_total) + "</span>", "", g.code));
          });
        }
        if (r.edu.length) {
          ul.appendChild(head(EN ? "Degrees in the register" : "Utdanninger i registeret"));
          r.edu.forEach(function (e) {
            var g = byCode[e.code];
            ul.appendChild(hitButton(e.sub && e.sub !== e.name ? e.sub : e.name,
              (e.sub && e.sub !== e.name ? e.name + " · " : "") + g.name + ", " + levelLow(g.level) + " · " + thousands(e.p) +
              (EN ? " persons" : " personer"), e.code));
          });
        }
        if (!r.groups.length && !r.edu.length) ul.appendChild(head(EN ? "No match" : "Ingen treff"));
      }
      ul.hidden = false;
    }
    function showGroupInInput() {
      var g = cur();
      el("u-search").value = g ? g.name + " · " + levelLow(g.level) : "";
    }
    function setGroup(code) {
      if (!byCode[code]) return;
      state.group = code; state.level = code.charAt(0); state.task = 0;
      el("u-level").value = state.level;
      el("u-hits").hidden = true;
      showGroupInInput();
      renderAll();
    }

    // ---- Kort setning + tallene bak ----
    function renderLead() {
      var g = cur(), box = el("u-lead");
      var head = "<strong>" + g.name + ", " + levelLow(g.level) + "</strong>";
      var ex = g.task_exposure, au = g.task_automation;
      var exWord = exWordFor(ex);
      var terc = EN ? " \"Highly\", \"moderately\" and \"little\" split the groups into thirds by task score (cut-offs " + num(T1, 2) + " and " + num(T2, 2) + ")."
                    : " «Sterkt», «middels» og «lite» deler faggruppene i tre like store deler etter oppgaveskåren (grensene " + num(T1, 2) + " og " + num(T2, 2) + ").";
      var lead, full;
      if (EN) {
        lead = head + " is the highest education of " + thousands(g.n_total) + " people in Norway. " +
          pct(g.q5_v1 * 100, 0) + " of those in work are in the most AI-exposed fifth of occupations. " +
          (ex === null ? "" : "The tasks in their jobs are " + exWord + " exposed to language models (score " + num(ex, 2) + " of 1)") +
          (au === null ? (ex === null ? "" : ".") : (ex === null ? "Where Claude is used on their tasks, " : ", and where Claude is used on them, ") + pct(au * 100, 0) + " of the use is automation.");
        full = "<p>Register link, November 2024: " + thousands(g.n_total) + " residents aged 20 to 70 with the education as their highest completed, " +
          pct(g.share_employed * 100, 0) + " employed and " + pct(g.share_studying * 100, 0) + " in education. The employed work in " + g.n_occ + " occupations.</p>" +
          "<p>The occupations have a mean AI exposure of " + num(g.exposure_v1, 2) + " by " + VLAB.v1 + (g.exposure_v2 !== null ? " and " + num(g.exposure_v2, 2) + " by " + VLAB.v2 : "") +
          ". " + pct(g.q5_v1 * 100, 0) + (g.q5_v2 !== null ? " and " + pct(g.q5_v2 * 100, 0) : "") + " work in the most exposed fifth by the two measures.</p>" +
          "<p>The task score is the weighted mean of Eloundou et al.'s labels over every O*NET task in these occupations (a language model alone halves the time = 1, with extra software = 0.5, neither = 0), weighted by how important and common the task is and by how many hold the occupation. " +
          (g.task_coverage !== null ? pct(g.task_coverage * 100, 0) + " of the employed are in occupations with an O*NET task list." : "") + terc + " " +
          "The automation share is Anthropic's own bucketing (directive + feedback loop) over the same tasks, weighted by each task's share of all Claude.ai use, " + vlabelAei("claude_ai") + ". Weighted by occupation instead, automation is " + (g.automation === null ? "unknown" : pct(g.automation * 100, 0)) + ".</p>";
      } else {
        lead = head + " er høyeste utdanning for " + thousands(g.n_total) + " personer i Norge. " +
          pct(g.q5_v1 * 100, 0) + " av dem som jobber, er i den mest KI-utsatte femdelen av yrkene. " +
          (ex === null ? "" : "Oppgavene i jobbene deres er " + exWord + " eksponert for språkmodeller (skår " + num(ex, 2) + " av 1)") +
          (au === null ? (ex === null ? "" : ".") : (ex === null ? "Der Claude brukes på oppgavene, " : ", og der Claude brukes på dem, ") + "er " + pct(au * 100, 0) + " av bruken automatisering.");
        full = "<p>Registerkobling november 2024: " + thousands(g.n_total) + " bosatte 20–70 år med utdanningen som høyeste fullførte, " +
          pct(g.share_employed * 100, 0) + " sysselsatte og " + pct(g.share_studying * 100, 0) + " i utdanning. De sysselsatte jobber i " + g.n_occ + " yrker.</p>" +
          "<p>Yrkene har en snitt-eksponering for KI på " + num(g.exposure_v1, 2) + " etter " + VLAB.v1 + (g.exposure_v2 !== null ? " og " + num(g.exposure_v2, 2) + " etter " + VLAB.v2 : "") +
          ". " + pct(g.q5_v1 * 100, 0) + (g.q5_v2 !== null ? " og " + pct(g.q5_v2 * 100, 0) : "") + " jobber i den mest eksponerte femdelen etter de to målene.</p>" +
          "<p>Oppgaveskåren er det vektede snittet av Eloundou m.fl. sine etiketter over alle O*NET-oppgaver i disse yrkene (en språkmodell alene halverer tiden = 1, med tilleggsverktøy = 0,5, ingen av delene = 0), vektet med hvor viktig og vanlig oppgaven er og hvor mange som har yrket. " +
          (g.task_coverage !== null ? pct(g.task_coverage * 100, 0) + " av de sysselsatte er i yrker med O*NET-oppgaveliste." : "") + terc + " " +
          "Automatiseringsandelen er Anthropics egen inndeling (direkte delegering + tilbakemeldingssløyfe) over de samme oppgavene, vektet med hver oppgaves andel av all Claude.ai-bruk, " + vlabelAei("claude_ai") + ". Vektet etter yrke i stedet er automatiseringen " + (g.automation === null ? "ukjent" : pct(g.automation * 100, 0)) + ".</p>";
      }
      box.innerHTML = "<p class='pick-lead'>" + lead + "</p><details class='more'><summary>" +
        (EN ? "The numbers behind this" : "Tallene bak") + "</summary>" + full + "</details>";
      setAll(".u-group-name", g.name.charAt(0).toLowerCase() + g.name.slice(1) + ", " + levelLow(g.level));
    }
    function vlabelAei(p) {
      var d = U.aei_latest[p];
      return monthLabel(d);
    }

    // ---- De ti vanligste oppgavene ----
    // Oppgavens eksponering: skaar 0-1 (snitt av Eloundous tre vurderinger)
    // og gruppe i samme femdeling som yrkene.
    function labelBadge(t) {
      if (t.score === null || t.score === undefined) return "–";
      return num(t.score, 2) + " " + qBadge(t.q);
    }
    function renderTasks() {
      var g = cur(), box = el("u-task-table");
      if (!g.tasks.length) {
        box.innerHTML = "<p class='chart-footnote'>" + (EN ? "No O*NET task list for these occupations." : "Ingen O*NET-oppgaveliste for disse yrkene.") + "</p>";
        return;
      }
      // En oppgave hoerer ofte til flere av yrkene utdanningen foerer til: vis de
      // som bidrar mest til oppgavens vekt, hele lista med andeler ved hover.
      function occCell(t) {
        var os = t.occs && t.occs.length ? t.occs : [{ c: t.occ_code, n: t.occ_name, n_en: t.occ_name_en, s: 1 }];
        var nm = function (x) { return EN && x.n_en ? x.n_en : x.n; };
        var total = t.n_occ || os.length, shown = os.slice(0, 3), more = total - shown.length;
        var title = os.map(function (x) { return nm(x) + " (" + pct(x.s * 100, 0) + ")"; }).join(", ") +
          (total > os.length ? (EN ? " and " : " og ") + (total - os.length) + (EN ? " more" : " til") : "");
        return "<span title=\"" + title.replace(/"/g, "”") + "\">" + shown.map(nm).join(", ") +
          (more > 0 ? " <span class='occ-small'>+" + more + "</span>" : "") + "</span>";
      }
      var h = "<table class='data-table task-table'><thead><tr><th>#</th><th>" + (EN ? "Task" : "Oppgave") + "</th><th>" +
        (EN ? "Occupations" : "Yrker") + "</th><th>" + (EN ? "AI exposure" : "KI-eksponering") + "</th><th class='num'>" +
        (EN ? "Automation" : "Automatisering") + "</th></tr></thead><tbody>";
      g.tasks.forEach(function (t, i) {
        var c = t.chat;
        h += "<tr data-i='" + i + "'" + (i === state.task ? " class='is-active'" : "") + " tabindex='0'><td>" + (i + 1) + "</td><td>" + (EN ? t.text : (t.text_no || t.text)) +
          "</td><td class='top-occ'>" + occCell(t) + "</td><td>" + labelBadge(t) + "</td><td class='num'>" +
          (c ? "<span class='score-bar'><i style='width:" + Math.round(c.auto * 100) + "%'></i></span>" + pct(c.auto * 100, 0) : "<span class='occ-small'>" + (EN ? "no data" : "ingen data") + "</span>") +
          "</td></tr>";
      });
      h += "</tbody></table>";
      box.innerHTML = h;
      Array.prototype.forEach.call(box.querySelectorAll("tr[data-i]"), function (tr) {
        function pick() { state.task = +tr.getAttribute("data-i"); renderTasks(); renderTask(); }
        tr.addEventListener("click", pick);
        tr.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
      });
      setText("u-task-foot", EN
        ? "The ten tasks with the largest weight across the occupations the graduates work in: importance × share of incumbents who do the task (O*NET 30.1), weighted by how many hold each occupation. Occupations: those contributing most to the task's weight, with share and the full list on hover. Task texts are O*NET's English statements. Exposure: Eloundou et al. (2024) per task. Automation: share of Claude.ai conversations about the task that are automation, " + vlabelAei("claude_ai") + ". Click a task to see how Claude is used on it."
        : "De ti oppgavene med størst vekt på tvers av yrkene de sysselsatte har: viktighet × andel som gjør oppgaven (O*NET 30.1), vektet med hvor mange som har hvert yrke. Yrker: de som bidrar mest til oppgavens vekt, med andel og hele lista når du holder musen over. Oppgavetekstene er oversatt fra O*NET. Eksponering: Eloundou m.fl. (2024) per oppgave. Automatisering: andel av Claude.ai-samtalene om oppgaven som er automatisering, " + vlabelAei("claude_ai") + ". Klikk på en oppgave for å se hvordan Claude brukes på den.");
    }

    // ---- Claude-bruken paa den valgte oppgaven: bare Claude.ai (chat), de fem
    // typene i de to standardfargene (automatisering moerk, augmentering lys) ----
    function renderTask() {
      var g = cur(), t = g.tasks[state.task], c = chart("chart-u-task");
      if (!t) { c.clear(); setText("u-task-title", ""); setText("u-task-note", ""); return; }
      setText("u-task-title", (EN ? "How Claude is used on: " : "Slik brukes Claude på: ") + (EN ? t.text : (t.text_no || t.text)));
      var p = t.chat;
      if (!p) {
        c.clear();
        setText("u-task-note", EN ? "Anthropic has no Claude.ai usage data for this task in the latest sample." : "Anthropic har ingen bruksdata for denne oppgaven i det siste utvalget.");
        return;
      }
      c.setOption({
        animationDuration: 300,
        grid: { left: 56, right: 20, top: 40, bottom: 64 },
        graphic: brandGraphic(SRC_AEI),
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: function (v) { return pct(v, 1); } },
        xAxis: { type: "category", data: TYPES.map(function (k) { return TYPE_LABELS[k]; }), axisTick: { show: false },
                 axisLabel: { interval: 0, fontSize: 11, width: typeLabelWidth("chart-u-task"), overflow: "break", lineHeight: 13 } },
        yAxis: { type: "value", min: 0, max: 100, name: EN ? "Share of conversations" : "Andel av samtalene", nameTextStyle: { align: "left" },
                 axisLabel: { formatter: function (v) { return v + " %"; } }, splitLine: { lineStyle: { color: "#eee" } } },
        series: [{ name: EN ? "Share of conversations" : "Andel av samtalene", type: "bar", barMaxWidth: 70,
                   data: TYPES.map(function (k) { return { value: +(p[k] * 100).toFixed(1), itemStyle: { color: TYPE_COLORS[k] } }; }),
                   label: { show: true, position: "top", fontSize: 12, fontWeight: 600, formatter: function (q) { return num(q.value, 0) + " %"; } } }]
      }, true);
      setText("u-task-note", PLATFORM_LABELS.claude_ai + ", " + vlabelAei("claude_ai") + ": " + (EN ? "automation " : "automatisering ") + pct(p.auto * 100, 0) + ", " +
        thousands(p.n) + (EN ? " classified conversations, " : " klassifiserte samtaler, ") + num(p.u, 2) +
        (EN ? " % of all Claude.ai use. The two first types are automation, the three last augmentation." : " % av all Claude.ai-bruk. De to første typene er automatisering, de tre siste augmentering."));
    }

    // ---- De vanligste jobbene ----
    function renderOcc() {
      var g = cur(), rows = state.cohort === "recent" ? g.occ_recent : g.occ_all;
      var box = el("u-occ-table");
      if (!rows.length) {
        box.innerHTML = "<p class='chart-footnote'>" + (EN ? "Too few recent graduates in the register." : "For få nyutdannede i registeret.") + "</p>";
        return;
      }
      var h = "<table class='data-table'><thead><tr><th>#</th><th>" + (EN ? "Occupation (STYRK-08)" : "Yrke (STYRK-08)") + "</th><th class='num'>" +
        (EN ? "Share of employed" : "Andel av sysselsatte") + "</th><th>" + (EN ? "Exposure" : "Eksponering") + "</th><th class='num'>" + (EN ? "Automation" : "Automatisering") + "</th></tr></thead><tbody>";
      rows.forEach(function (o, i) {
        h += "<tr><td>" + (i + 1) + "</td><td>" + occNameOf(o) + " <span class='occ-code'>" + o.code + "</span></td><td class='num'>" + pct(o.share * 100, 1) +
          "</td><td>" + (o.e_v1 !== null && o.e_v1 !== undefined ? num(o.e_v1, 2) + " " : "") + qBadge(o.q_v1) + "</td><td class='num'>" + (o.auto === null || o.auto === undefined ? "–" : pct(o.auto * 100, 0)) + "</td></tr>";
      });
      h += "</tbody></table>";
      box.innerHTML = h;
      setText("u-occ-note", (state.cohort === "recent"
        ? (EN ? "Employed residents who completed the education one to three years ago (" + thousands(g.n_recent) + " persons). "
              : "Sysselsatte som fullførte utdanningen for ett til tre år siden (" + thousands(g.n_recent) + " personer). ")
        : (EN ? "All employed residents 20–70 with the education as their highest, " + thousands(g.n_employed) + " persons. "
              : "Alle sysselsatte bosatte 20–70 år med utdanningen som høyeste, " + thousands(g.n_employed) + " personer. ")) +
        (EN ? "Exposure: score 0–1 by " + VLAB.v1 + " and its group, five equal groups of occupations from least to most exposed. Automation: Claude.ai, " + vlabelAei("claude_ai") + "."
            : "Eksponering: skår 0–1 etter " + VLAB.v1 + " og gruppen skåren gir, fem like store grupper av yrkene fra minst til mest utsatt. Automatisering: Claude.ai, " + vlabelAei("claude_ai") + "."));
    }

    function renderAll() { renderLead(); renderTasks(); renderTask(); renderOcc(); }

    // ---- Oppsett ----
    var fromUrl = (location.search.match(/[?&]fag=(\d{3})/) || [])[1];
    if (fromUrl && byCode[fromUrl]) { state.level = fromUrl.charAt(0); state.group = fromUrl; }
    else state.group = defaultGroup(state.level);
    makeSelect("u-level", levels.map(function (l) { return { value: l.code, label: EN ? l.name_en : l.name }; }),
      function () { return state.level; },
      function (v) { state.level = v; state.group = defaultGroup(v); state.task = 0; showGroupInInput(); renderAll(); });
    var inp = el("u-search"), hits = el("u-hits");
    showGroupInInput();
    inp.addEventListener("focus", function () { inp.select(); renderHits(""); });
    inp.addEventListener("click", function () { if (hits.hidden) renderHits(inp.value === (cur() ? cur().name + " · " + levelLow(cur().level) : "") ? "" : inp.value); });
    inp.addEventListener("input", function () { renderHits(inp.value); });
    inp.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { var f = hits.querySelector("li:not(.hit-head) button"); if (f) { e.preventDefault(); f.click(); } }
      else if (e.key === "Escape") { hits.hidden = true; showGroupInInput(); }
    });
    document.addEventListener("click", function (e) {
      if (!e.target.closest || !e.target.closest(".control-search")) { hits.hidden = true; if (!inp.value.trim()) showGroupInInput(); }
    });
    makeButtons("u-cohort-buttons", [{ value: "all", label: EN ? "All" : "Alle" }, { value: "recent", label: EN ? "Recent graduates (1–3 years)" : "Nyutdannede (1–3 år)" }],
      function () { return state.cohort; }, function (v) { state.cohort = v; renderOcc(); });
    renderAll();
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
