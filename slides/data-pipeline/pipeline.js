/*
 * pipeline.js
 *
 * One continuous animation from raw cells to the indexed figure. Each click
 * (reveal.js fragment) tweens a set of parameters, and everything on screen is a
 * function of those parameters. Lines are never swapped, they are interpolated
 * between the pixel geometry of consecutive "views" (axis scales and data layers).
 *
 * Data: window.PIPELINE_DATA from data/pipeline-data.js (built by build_data.py).
 * Plain JavaScript and canvas. No libraries, no network.
 */
function createPipeline(D, root) {
  "use strict";

  var canvas = root.querySelector("canvas");
  var ctx = canvas.getContext("2d");
  var AGE = D.meta.ageLabel;                           // "21–60" or "21–30"
  var ALL_AGES = D.meta.nAges > 1;

  /* ------------------------------------------------------------------ */
  /* constants                                                           */
  /* ------------------------------------------------------------------ */
  var W = 1280, H = 720;                               // logical slide size
  var PLOT = { l: 150, r: 900, t: 284, b: 630 };       // plot rectangle
  var NM = D.months.length;                            // months
  var NC = D.cells.q.length;                           // cell series

  var INK = "#1d2733", MUTE = "#5d6772", GREY = "#8d97a1", GRID = "#e2dfd7";
  var PAPER = "#fbfaf7", BAND = "#f1efe9", NAVY = "#1F4E79", TEAL = "#0B7A75";
  var QC = ["#577590", "#E6A817", "#E54A2B", "#8C1515", "#401415"];   // as on kiindeksen.no
  var QL = ["Q1 minst eksponert", "Q2", "Q3", "Q4", "Q5 mest eksponert"];
  var SANS = "'Segoe UI', Calibri, Arial, sans-serif";
  var MONO = "Consolas, 'Courier New', monospace";
  var MON = ["jan", "feb", "mar", "apr", "mai", "jun", "jul", "aug", "sep", "okt", "nov", "des"];
  var MONFULL = ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august",
                 "september", "oktober", "november", "desember"];
  var FQ = 4;                                          // quintile used to explain the seasonal step (Q5)

  /* ------------------------------------------------------------------ */
  /* small helpers                                                       */
  /* ------------------------------------------------------------------ */
  function clamp(x, a, b) { return x < a ? a : (x > b ? b : x); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function easeIO(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function fmt(n, d) {
    d = d || 0;
    return n.toLocaleString("nb-NO", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function sgn(x, d) { return (x >= 0 ? "+" : "−") + fmt(Math.abs(x), d); }
  function monthName(ym) { return MONFULL[+ym.slice(5, 7) - 1] + " " + ym.slice(0, 4); }
  function hex(c) { return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]; }
  function mix(c1, c2, t) {
    var a = hex(c1), b = hex(c2);
    return "rgb(" + Math.round(lerp(a[0], b[0], t)) + "," + Math.round(lerp(a[1], b[1], t)) + "," +
      Math.round(lerp(a[2], b[2], t)) + ")";
  }
  function bracket(v, lo, hi) {                        // integer view below v, and the fraction
    v = clamp(v, lo, hi);
    var k = Math.min(Math.floor(v), hi - 1);
    return { k: k, f: v - k };
  }
  function haloText(str, x, y, color) {
    ctx.lineJoin = "round"; ctx.lineWidth = 5; ctx.strokeStyle = PAPER;
    ctx.strokeText(str, x, y);
    ctx.fillStyle = color; ctx.fillText(str, x, y);
  }
  function spread(items, gap, bottom) {                // push overlapping labels apart
    items.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < items.length; i++) {
      if (items[i].y - items[i - 1].y < gap) { items[i].y = items[i - 1].y + gap; }
    }
    var over = items.length ? items[items.length - 1].y - bottom : 0;
    if (over > 0) { items.forEach(function (it) { it.y -= over; }); }
  }
  function nan(arr) { return arr.map(function (x) { return x == null ? NaN : x; }); }

  /* ------------------------------------------------------------------ */
  /* data                                                                */
  /* ------------------------------------------------------------------ */
  var cellV = D.cells.v.map(function (row) {
    var a = new Float32Array(NM);
    for (var m = 0; m < NM; m++) { a[m] = row[m] == null ? NaN : row[m]; }
    return a;
  });
  var cellQ = D.cells.q.map(function (q) { return q - 1; });          // 0..4
  var named = D.named;                                                  // 4 named cells
  var isNamed = new Uint8Array(NC);
  named.forEach(function (n) { isNamed[n.cell] = 1; });
  var cloud = [[], [], [], [], []];                                     // unnamed cells per quintile
  for (var ci = 0; ci < NC; ci++) { if (!isNamed[ci]) { cloud[cellQ[ci]].push(ci); } }
  var A = named[0].cell;                                                // the table's cell
  var refIdx = D.months.indexOf(D.meta.ref);
  var gptX = D.months.indexOf(D.meta.chatgptMonth) + (30 - 16) / 30.4;  // 30 Nov, months start on the 16th
  var trend = D.trend.map(nan), dev = D.dev.map(nan);                   // seasonal: trend and deviation
  var winFrom = D.months.indexOf(D.meta.seasFrom), winTo = D.months.indexOf(D.meta.seasTo);

  function finiteRange(arr, from, to) {
    var lo = Infinity, hi = -Infinity;
    for (var m = from; m < to; m++) {
      var x = arr[m];
      if (x === x) { if (x < lo) { lo = x; } if (x > hi) { hi = x; } }
    }
    return [lo, hi];
  }

  /* ------------------------------------------------------------------ */
  /* views: axis scales (one per stage of the pipeline)                  */
  /* ------------------------------------------------------------------ */
  function niceStep(range, n) {
    var raw = range / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / mag;
    return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * mag;
  }
  function linTicks(lo, hi, n, dec) {
    var st = niceStep(hi - lo, n), out = [];
    for (var v = Math.ceil(lo / st - 1e-9) * st; v <= hi + 1e-9; v += st) {
      var r = +v.toFixed(8);
      out.push({ v: r, label: fmt(r, dec != null ? dec : (st < 1 ? 1 : 0)) });
    }
    return out;
  }
  function logTicks(lo, hi) {                          // lo, hi in log10
    var out = [];
    for (var k = Math.floor(lo); k <= Math.ceil(hi); k++) {
      [1, 3].forEach(function (mult) {
        var v = mult * Math.pow(10, k), L = Math.log10(v);
        if (L >= lo - 1e-9 && L <= hi + 1e-9) { out.push({ v: v, label: fmt(v) }); }
      });
    }
    return out;
  }
  function xMap(a, b) { return function (m) { return PLOT.l + (m - a) / (b - a) * (PLOT.r - PLOT.l); }; }
  function yLin(lo, hi) { return function (v) { return PLOT.b - (v - lo) / (hi - lo) * (PLOT.b - PLOT.t); }; }
  function yLog(lo, hi) { return function (v) { return PLOT.b - (Math.log10(v) - lo) / (hi - lo) * (PLOT.b - PLOT.t); }; }
  function monthTicks() {                              // the first twelve months, spelled out
    return D.months.slice(0, 12).map(function (ym, m) {
      return { m: m, label: MON[+ym.slice(5, 7) - 1], sub: m === 0 ? ym.slice(0, 4) : "" };
    });
  }
  function yearTicks() {
    var out = [];
    D.months.forEach(function (ym, m) { if (ym.slice(5, 7) === "01") { out.push({ m: m, label: ym.slice(0, 4), sub: "" }); } });
    return out;
  }

  var V = [], VZ, VD, VC;
  (function buildViews() {
    var r1 = finiteRange(cellV[A], 0, 12), p1 = (r1[1] - r1[0]) * 0.34;
    var lo1 = r1[0] - p1, hi1 = r1[1] + p1;
    V[1] = { X: xMap(-0.8, 11.8), Y: yLin(lo1, hi1), yTicks: linTicks(lo1, hi1, 5), xTicks: monthTicks(),
             title: "Antall ansatte" };

    var r2 = finiteRange(cellV[A], 0, NM), p2 = (r2[1] - r2[0]) * 0.2;
    var lo2 = r2[0] - p2, hi2 = r2[1] + p2;
    V[2] = { X: xMap(-1, NM), Y: yLin(lo2, hi2), yTicks: linTicks(lo2, hi2, 5), xTicks: yearTicks(),
             title: "Antall ansatte" };

    var nmin = Infinity, nmax = -Infinity;
    named.forEach(function (n) { var r = finiteRange(cellV[n.cell], 0, NM); nmin = Math.min(nmin, r[0]); nmax = Math.max(nmax, r[1]); });
    var lo3 = Math.log10(nmin * 0.6), hi3 = Math.log10(nmax * 1.8);
    V[3] = { X: xMap(-1, NM), Y: yLog(lo3, hi3), yTicks: logTicks(lo3, hi3), xTicks: yearTicks(),
             title: "Antall ansatte, logaritmisk skala" };

    var amin = Infinity, amax = -Infinity;
    for (var i = 0; i < NC; i++) { var r = finiteRange(cellV[i], 0, NM); amin = Math.min(amin, r[0]); amax = Math.max(amax, r[1]); }
    var lo4 = Math.log10(amin * 0.7), hi4 = Math.log10(amax * 1.5);
    V[4] = { X: xMap(-1, NM), Y: yLog(lo4, hi4), yTicks: logTicks(lo4, hi4), xTicks: yearTicks(),
             title: "Antall ansatte, logaritmisk skala" };
    V[5] = V[4];

    // The axes from here on do not start at zero, so the lines fill the plot. `broken` marks that.
    var smin = Infinity, smax = 0;
    D.sum.forEach(function (row) { row.forEach(function (x) { smin = Math.min(smin, x); smax = Math.max(smax, x); }); });
    var lo6 = Math.max(0, smin - (smax - smin) * 0.3), hi6 = smax + (smax - smin) * 0.12;
    V[6] = { X: xMap(-1, NM), Y: yLin(lo6, hi6), yTicks: linTicks(lo6, hi6, 4), xTicks: yearTicks(),
             title: "Antall ansatte", broken: lo6 > 0 };

    var pmin = Infinity, pmax = 0;                     // per capita and seasonally adjusted share one axis
    [D.pc, D.sa].forEach(function (L) {
      L.forEach(function (row) { row.forEach(function (x) { pmin = Math.min(pmin, x); pmax = Math.max(pmax, x); }); });
    });
    var lo7 = Math.max(0, pmin - (pmax - pmin) * 0.3), hi7 = pmax + (pmax - pmin) * 0.12;
    V[7] = { X: xMap(-1, NM), Y: yLin(lo7, hi7), yTicks: linTicks(lo7, hi7, 4, 0), xTicks: yearTicks(),
             title: "Prosent av befolkningen " + AGE + " år", broken: lo7 > 0 };
    V[8] = V[7];

    var imin = Infinity, imax = -Infinity;
    D.idx.forEach(function (row) { row.forEach(function (x) { imin = Math.min(imin, x); imax = Math.max(imax, x); }); });
    var lo9 = Math.floor(imin - 1), hi9 = Math.ceil(imax + 1);
    V[9] = { X: xMap(-1, NM), Y: yLin(lo9, hi9), yTicks: linTicks(lo9, hi9, 5, 0), xTicks: yearTicks(),
             title: "Indeks, " + monthName(D.meta.ref) + " = 100", broken: true };
    V[10] = V[9];
    V.forEach(function (vw, k) { if (vw) { vw.xKey = k === 1 ? "months" : "years"; } });   // same key = same x axis

    // seasonal explanation: a zoomed level axis, a deviation axis, and a calendar-month axis
    var pr = finiteRange(D.pc[FQ], 0, NM), pz = (pr[1] - pr[0]) * 0.45;
    var loZ = pr[0] - pz, hiZ = pr[1] + pz;
    VZ = { X: V[7].X, Y: yLin(loZ, hiZ), yTicks: linTicks(loZ, hiZ, 3, 0), xTicks: V[7].xTicks,
           title: V[7].title, xKey: "years", broken: true };
    var dmax = 0;
    dev.forEach(function (row) { row.forEach(function (x) { if (x === x) { dmax = Math.max(dmax, Math.abs(x)); } }); });
    D.fac.forEach(function (row) { row.forEach(function (x) { dmax = Math.max(dmax, Math.abs(x)); }); });
    var da = Math.ceil(dmax * 1.15);
    VD = { X: V[7].X, Y: yLin(-da, da), yTicks: linTicks(-da, da, 6, 0), xTicks: V[7].xTicks,
           title: "Avvik fra trenden, prosent", xKey: "years" };
    var colW = (PLOT.r - PLOT.l) / 12;
    VC = { X: function (c) { return PLOT.l + (c + 0.5) * colW; },
           xTicks: MON.map(function (name, c) { return { m: c, label: name, sub: "" }; }), xKey: "cal" };
  })();
  var colX = VC.X;

  /* ------------------------------------------------------------------ */
  /* geometry per view (pixels), so a click only interpolates            */
  /* ------------------------------------------------------------------ */
  var cellX = [], cellY = [], qX = [], qY = [], qYz = [];
  [1, 2, 3, 4].forEach(function (k) {
    var vw = V[k], xs = new Float32Array(NM), ys = new Float32Array(NC * NM);
    for (var m = 0; m < NM; m++) { xs[m] = vw.X(m); }
    for (var i = 0; i < NC; i++) {
      for (var m2 = 0; m2 < NM; m2++) {
        var c = cellV[i][m2];
        ys[i * NM + m2] = c === c ? vw.Y(c) : NaN;
      }
    }
    cellX[k] = xs; cellY[k] = ys;
  });
  cellX[5] = cellX[4]; cellY[5] = cellY[4];

  var layers = { 6: D.sum, 7: D.pc, 8: D.sa, 9: D.idx };
  [6, 7, 8, 9].forEach(function (k) {
    var vw = V[k], xs = new Float32Array(NM), rows = [];
    for (var m = 0; m < NM; m++) { xs[m] = vw.X(m); }
    for (var q = 0; q < 5; q++) {
      var ys = new Float32Array(NM);
      for (var m2 = 0; m2 < NM; m2++) { ys[m2] = vw.Y(layers[k][q][m2]); }
      rows.push(ys);
    }
    qX[k] = xs; qY[k] = rows;
  });
  qX[10] = qX[9]; qY[10] = qY[9];
  for (var zq = 0; zq < 5; zq++) {                     // per-capita lines on the zoomed axis
    var zr = new Float32Array(NM);
    for (var zm = 0; zm < NM; zm++) { zr[zm] = VZ.Y(D.pc[zq][zm]); }
    qYz.push(zr);
  }

  var collapsed = new Float32Array(NC * NM);           // each cell line folded onto its quintile's sum line
  for (var cj = 0; cj < NC; cj++) {
    for (var cm = 0; cm < NM; cm++) { collapsed[cj * NM + cm] = qY[6][cellQ[cj]][cm]; }
  }

  /* ------------------------------------------------------------------ */
  /* the raw-data table                                                  */
  /* ------------------------------------------------------------------ */
  var TB = { x0: 64, xCode: 250, xTitle: 322, xAge: 618, valRight: 900, head: 262, rule: 282, y0: 312, rowH: 30 };
  var rows = D.table.rows;
  var occTitle = named[0].name, ageLabel = named[0].age;
  var numBelow = rows.map(function (r, i) {            // dips get their label under the dot
    return i > 0 && i < rows.length - 1 && r[4] < rows[i - 1][4] && r[4] < rows[i + 1][4];
  });

  /* ------------------------------------------------------------------ */
  /* the seasonal explanation points (Q5): where each deviation sits     */
  /* ------------------------------------------------------------------ */
  var hmIdx = 0;                                       // calendar month with the largest factor
  D.fac[FQ].forEach(function (x, c) { if (Math.abs(x) > Math.abs(D.fac[FQ][hmIdx])) { hmIdx = c; } });
  var devPts = [], seen = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
  for (var dm = 0; dm < NM; dm++) {
    if (dev[FQ][dm] === dev[FQ][dm]) {
      var cmo = +D.months[dm].slice(5, 7) - 1;
      devPts.push({ m: dm, cm: cmo, rank: seen[cmo]++ });
    }
  }
  var fF = D.fac[FQ][hmIdx], hmName = MONFULL[hmIdx];

  /* ------------------------------------------------------------------ */
  /* state, steps and the tween engine                                   */
  /* ------------------------------------------------------------------ */
  var DEF = { v: 1, axes: 0, tbl: 0, fly: 0, lblA: 0, revA: 0, aA: 0, dotsA: 0, labA: 0,
              revN: 0, aN: 0, labN: 0, revC: 0, aC: 0, col: 0, leg: 0, agg: 0, qa: 0,
              pop: 0, ref: 0, gpt: 0, qlab: 0, kimode: 0, kib: 0, kia: 0, kig: 0,
              zy: 0, sdim: 0, band: 0, trendA: 0, trendDraw: 0, dv: 0, devAx: 0, cm: 0, fb: 0, fo: 0, hm: 0 };

  var nmRange = (function () {
    var lo = Infinity, hi = -Infinity;
    named.forEach(function (n) { var r = finiteRange(cellV[n.cell], 0, NM); lo = Math.min(lo, r[0]); hi = Math.max(hi, r[1]); });
    return [lo, hi];
  })();
  var lastI = NM - 1;
  var rel = D.headline.rel;

  var STEPS = [
    { head: ["Rådata", "Én rad per yrke, alder og måned",
             "Antall ansatte i privat sektor, " + AGE + " år. Registerdata fra A-ordningen via microdata.no."],
      form: "", facts: true,
      set: { v: 1, axes: 0, tbl: 1, fly: 0, lblA: 1, revA: 0, aA: 0, dotsA: 0 } },

    { head: ["Fra rader til en linje", "Hver rad blir ett punkt",
             occTitle + ", " + ageLabel + " år, i 2021."],
      form: "", dur: 3000,
      set: { tbl: 0, fly: 1, axes: 1, revA: 12, aA: 1, dotsA: 1 },
      win: { tbl: [0, 0.3], fly: [0.04, 0.96], axes: [0.35, 0.85], revA: [0.5, 1], aA: [0.45, 0.55], dotsA: [0.45, 0.5] },
      ease: { revA: "lin", fly: "lin" } },

    { head: ["Tidsserien", "Én serie over hele perioden",
             "Fra " + monthName(D.meta.first) + " til " + monthName(D.meta.last) + ". Vekst og sesongsvingninger ligger i samme serie."],
      form: "", dur: 2600,
      set: { v: 2, revA: NM, dotsA: 0, lblA: 0, labA: 1 },
      win: { lblA: [0, 0.25], v: [0.05, 0.65], revA: [0.3, 1], dotsA: [0.1, 0.8], labA: [0.75, 1] },
      ease: { revA: "lin" } },

    { head: ["Flere serier", "Serier på helt ulike nivåer",
             "Fire serier fra " + fmt(nmRange[0]) + " til " + fmt(nmRange[1]) + " ansatte. Aksen er logaritmisk for at alle skal få plass."],
      form: "", dur: 2800,
      set: { v: 3, revN: NM, aN: 1, dotsA: 0, labN: 1 },
      win: { v: [0, 0.55], dotsA: [0, 0.3], aN: [0.3, 0.4], revN: [0.35, 1], labN: [0.85, 1] },
      ease: { revN: "lin" } },

    { head: ["Alle seriene", fmt(NC) + " serier",
             fmt(D.meta.nOcc) + " yrker " + (ALL_AGES ? "i fire aldersgrupper" : "i aldersgruppen " + AGE) +
             ". Hver tynn linje er én serie."],
      form: "", dur: 3400,
      set: { v: 4, revC: NM, aC: 1 },
      win: { v: [0, 0.55], aC: [0.2, 0.3], revC: [0.25, 1] },
      ease: { revC: "lin" } },

    { head: ["Eksponering", "Farg etter KI-eksponering",
             "Yrkene rangeres etter Eloundou mfl. (2024) og deles i fem grupper med like mange yrker."],
      form: "", dur: 2000,
      set: { v: 5, col: 1, leg: 1, labN: 0, labA: 0 },
      win: { col: [0, 1], leg: [0.5, 1], labN: [0, 0.3], labA: [0, 0.3] } },

    { head: ["Regneoperasjon 1", "Summer seriene i hver gruppe",
             "Alle serier i samme kvintil legges sammen måned for måned. Fem linjer står igjen."],
      form: "<span class='op'>Σ</span> ansatte i alle serier i kvintil <i>q</i>", dur: 3600,
      set: { v: 6, agg: 1, qa: 1, aC: 0, aN: 0, aA: 0, leg: 0, qlab: 1 },
      win: { agg: [0.1, 0.85], v: [0.1, 0.85], qa: [0.25, 0.8], aC: [0.8, 1], aN: [0.8, 1], aA: [0.8, 1],
             leg: [0, 0.2], qlab: [0.85, 1] } },

    { head: ["Regneoperasjon 2", "Del på befolkningen",
             "Ansatte i kvintilen delt på folketallet " + AGE + " år. Da forsvinner effekten av at befolkningen vokser."],
      form: "ansatte <span class='op'>/</span> befolkning " + AGE + " år", dur: 2800,
      set: { v: 7, pop: 1 },
      win: { pop: [0, 0.35], v: [0.25, 1] } },

    { head: ["Regneoperasjon 3, trinn 1 av 4", "Sesongjustering: finn trenden",
             "Vi tar kvintil 5 først. Trenden er et glidende gjennomsnitt over 13 måneder, regnet på " +
             D.meta.seasFrom.slice(0, 4) + "–" + D.meta.seasTo.slice(0, 4) + "."],
      form: "trend <span class='op'>=</span> glidende snitt over 13 måneder", dur: 3200,
      set: { pop: 0, zy: 1, sdim: 1, band: 1, trendA: 1, trendDraw: NM },
      win: { pop: [0, 0.2], zy: [0, 0.35], sdim: [0, 0.3], band: [0.2, 0.5], trendA: [0.35, 0.4], trendDraw: [0.35, 1] },
      ease: { trendDraw: "lin" } },

    { head: ["Regneoperasjon 3, trinn 2 av 4", "Sesongjustering: avvik fra trenden",
             "Kvintil 5: hvor mange prosent over eller under trenden ligger hver måned? Alle " + hmName + "-månedene er merket."],
      form: "avvik <span class='op'>=</span> verdi <span class='op'>/</span> trend <span class='op'>−</span> 1",
      dur: 3200,
      set: { dv: 1, devAx: 1, hm: 1 },
      win: { devAx: [0, 0.8], dv: [0.15, 0.85], hm: [0.75, 1] } },

    { head: ["Regneoperasjon 3, trinn 3 av 4", "Sesongjustering: faktor per måned",
             "Avvikene samles per kalendermåned. Snittet er faktoren, justert til null over året. Fem kvintiler gir " +
             (D.fac.length * 12) + " faktorer."],
      form: "faktor <span class='op'>=</span> snitt av avvikene i måneden", dur: 3600,
      set: { cm: 1, fb: 1, fo: 1, band: 0, trendA: 0, leg: 1 },       // the legend explains the colours of the small dots
      win: { band: [0, 0.25], trendA: [0, 0.25], cm: [0.05, 0.6], fb: [0.6, 0.85], fo: [0.8, 1], leg: [0.6, 1] } },

    { head: ["Regneoperasjon 3, trinn 4 av 4", "Sesongjustering: trekk fra faktorene",
             QL[FQ].slice(0, 2) + ", " + hmName + ": faktor " + sgn(fF, 1) + " prosent, så verdien deles på " +
             fmt(1 + fF / 100, 3) + ". Det gjøres for alle måneder, også etter " + D.meta.seasTo.slice(0, 4) + "."],
      form: "verdi <span class='op'>/</span> (1 + faktor)", dur: 4000,
      set: { v: 8, sdim: 0, zy: 0, dv: 0, devAx: 0, cm: 0, fb: 0, fo: 0, hm: 0, leg: 0 },
      win: { fb: [0, 0.15], fo: [0, 0.15], hm: [0, 0.15], leg: [0, 0.15], cm: [0.1, 0.5], dv: [0.3, 0.75],
             devAx: [0.3, 0.75], zy: [0.45, 0.9], sdim: [0.5, 0.9], v: [0.45, 0.95] } },

    { head: ["Regneoperasjon 4", "Sett " + monthName(D.meta.ref) + " til 100",
             "Hver linje deles på sitt eget nivå i referansemåneden. Da viser linjene vekst siden da."],
      form: "<span class='op'>100 ×</span> verdi <span class='op'>/</span> verdi i " +
            MON[+D.meta.ref.slice(5, 7) - 1] + ". " + D.meta.ref.slice(0, 4),
      dur: 3200,
      set: { v: 9, ref: 1 },
      win: { ref: [0, 0.3], v: [0.3, 1] } },

    { head: ["Resultatet", "Sysselsetting etter KI-eksponering",
             (ALL_AGES ? "Per innbygger" : "Per innbygger i aldersgruppen " + AGE) + ", sesongjustert, " +
             monthName(D.meta.ref) + " = 100. Data til og med " + monthName(D.meta.last) + "."],
      form: "", dur: 1800,
      set: { v: 10, ref: 0, gpt: 1 },
      win: { ref: [0, 0.4], gpt: [0.3, 0.8] } },

    { head: ["Resultatet, del 2", "KI-indeksen: hva sammenlignes",
             "Siste tre måneder mot de tre månedene til og med " + monthName(D.headline.ref) +
             ", for Q5 og Q1. Så deler vi Q5 på Q1."],
      form: "", result: true, dur: 3600,
      set: { kimode: 1, kib: 1, kia: 1, kig: 1, gpt: 0 },
      win: { kimode: [0, 0.3], kib: [0.1, 0.4], gpt: [0, 0.3], kia: [0.4, 0.85], kig: [0.75, 1] } }
  ];
  var LAST = STEPS.length - 1;

  var T = [];                                          // cumulative targets per step
  STEPS.forEach(function (s, k) { T[k] = Object.assign({}, k ? T[k - 1] : DEF, s.set); });

  var P = Object.assign({}, T[0]);                     // current parameter values
  var cur = 0, anim = null, raf = 0, reduce = false;
  try { reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { reduce = false; }

  function goTo(k, instant) {
    k = clamp(k, 0, LAST);
    if (k === cur && !instant && !anim) { return; }
    var prev = cur;
    cur = k;
    updateDom(k, instant);
    if (instant || reduce) { Object.assign(P, T[k]); anim = null; draw(); return; }
    var fwd = k > prev, spec = fwd ? STEPS[k] : STEPS[prev], win = {};
    Object.keys(T[k]).forEach(function (n) {
      var w = (spec.win && spec.win[n]) || [0, 1];
      win[n] = fwd ? w : [1 - w[1], 1 - w[0]];
    });
    anim = { t0: performance.now(), dur: spec.dur || 1800, from: Object.assign({}, P), to: T[k],
             win: win, ease: spec.ease || {} };
    draw();
  }

  function applyAnim(a, u) {                           // set every parameter for progress u in [0, 1]
    Object.keys(a.to).forEach(function (n) {
      var w = a.win[n], s = clamp((u - w[0]) / ((w[1] - w[0]) || 1e-6), 0, 1);
      var e = a.ease[n] === "lin" ? s : easeIO(s);
      P[n] = a.from[n] + (a.to[n] - a.from[n]) * e;
    });
  }
  function frame(now) {
    raf = 0;
    if (anim) {
      var u = (now - anim.t0) / anim.dur;
      applyAnim(anim, u);
      if (u >= 1) { Object.assign(P, anim.to); anim = null; }
    }
    render();
    if (anim) { raf = requestAnimationFrame(frame); }
  }
  function draw() { if (!raf) { raf = requestAnimationFrame(frame); } }
  function scrub(k, u) {                               // freeze step k at progress u (for checking frames)
    anim = null;
    var spec = STEPS[k], win = {};
    Object.keys(T[k]).forEach(function (n) { win[n] = (spec.win && spec.win[n]) || [0, 1]; });
    applyAnim({ from: T[k - 1], to: T[k], win: win, ease: spec.ease || {} }, u);
    render();
  }

  /* ------------------------------------------------------------------ */
  /* drawing                                                             */
  /* ------------------------------------------------------------------ */
  var pr = 1;
  function fit() {
    var sc = (window.Reveal && Reveal.getScale) ? Reveal.getScale() : 1;
    pr = Math.min(2, Math.max(1, (window.devicePixelRatio || 1) * sc));   // capped so weak graphics hardware keeps up
    canvas.width = Math.round(W * pr);
    canvas.height = Math.round(H * pr);
  }

  function drawAxisY(vw, alpha) {                      // gridlines, value labels and the axis title
    if (alpha < 0.01) { return; }
    ctx.globalAlpha = alpha;
    ctx.font = "22px " + SANS;
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    vw.yTicks.forEach(function (t) {
      var y = vw.Y(t.v);
      if (y < PLOT.t - 3 || y > PLOT.b + 3) { return; }
      var zero = vw === VD && t.v === 0;
      ctx.strokeStyle = zero ? INK : GRID; ctx.lineWidth = zero ? 2 : 1;
      ctx.beginPath(); ctx.moveTo(PLOT.l, y); ctx.lineTo(PLOT.r + 8, y); ctx.stroke();
      ctx.fillStyle = MUTE; ctx.fillText(t.label, PLOT.l - 14, y);
    });
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    ctx.font = "600 22px " + SANS; ctx.fillStyle = INK;
    ctx.fillText(vw.title, PLOT.l, PLOT.t - 38);
    ctx.strokeStyle = "#c9c6bd"; ctx.lineWidth = 1.5;  // the y axis itself
    ctx.beginPath(); ctx.moveTo(PLOT.l, PLOT.t - 4); ctx.lineTo(PLOT.l, PLOT.b); ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function drawAxisBreak(vw, alpha) {                  // a break in the y axis: the axis does not start at zero
    if (!vw.broken || alpha < 0.01) { return; }
    var x = PLOT.l, y = PLOT.b - 38;
    ctx.globalAlpha = alpha;
    ctx.fillStyle = PAPER; ctx.fillRect(x - 3, y - 10, 6, 20);        // gap in the axis line
    ctx.strokeStyle = "#7d776c"; ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x - 10, y - 2); ctx.lineTo(x + 10, y - 8);
    ctx.moveTo(x - 10, y + 8); ctx.lineTo(x + 10, y + 2);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function drawAxisX(vw, alpha) {                      // time axis: baseline, ticks, labels
    if (alpha < 0.01) { return; }
    ctx.globalAlpha = alpha;
    ctx.font = "22px " + SANS;
    ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillStyle = MUTE;
    ctx.strokeStyle = "#c9c6bd"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(PLOT.l, PLOT.b); ctx.lineTo(PLOT.r + 8, PLOT.b); ctx.stroke();
    vw.xTicks.forEach(function (t) {
      var x = vw.X(t.m);
      ctx.beginPath(); ctx.moveTo(x, PLOT.b); ctx.lineTo(x, PLOT.b + 6); ctx.stroke();
      ctx.fillText(t.label, x, PLOT.b + 10);
      if (t.sub) { ctx.fillText(t.sub, x, PLOT.b + 38); }
    });
    ctx.globalAlpha = 1;
  }

  // Old labels fade out first and new ones fade in after, so two scales never overlap.
  function drawAxes() {
    if (P.axes < 0.01) { return; }
    var ab = bracket(P.v, 1, 10), a = V[ab.k], b = V[ab.k + 1], f = ab.f;
    var yMain = 1 - clamp(2 * P.zy, 0, 1);
    var yZoom = clamp(2 * P.zy - 1, 0, 1) * (1 - clamp(2 * P.devAx, 0, 1));
    var yDev = clamp(2 * P.devAx - 1, 0, 1);
    if (a === b) { drawAxisY(a, P.axes * yMain); }
    else {
      drawAxisY(a, P.axes * yMain * clamp(1 - 2 * f, 0, 1));
      drawAxisY(b, P.axes * yMain * clamp(2 * f - 1, 0, 1));
    }
    drawAxisY(VZ, P.axes * yZoom);
    drawAxisY(VD, P.axes * yDev);
    var xYear = 1 - clamp(2 * P.cm, 0, 1), xMon = clamp(2 * P.cm - 1, 0, 1);
    if (a === b || a.xKey === b.xKey) { drawAxisX(b, P.axes * xYear); }
    else {
      drawAxisX(a, P.axes * xYear * clamp(1 - 2 * f, 0, 1));
      drawAxisX(b, P.axes * xYear * clamp(2 * f - 1, 0, 1));
    }
    drawAxisX(VC, P.axes * xMon);
    if (a === b) { drawAxisBreak(a, P.axes * yMain); }
    else {
      drawAxisBreak(a, P.axes * yMain * clamp(1 - 2 * f, 0, 1));
      drawAxisBreak(b, P.axes * yMain * clamp(2 * f - 1, 0, 1));
    }
    drawAxisBreak(VZ, P.axes * yZoom);
  }

  function drawBand() {                                // the estimation window for the seasonal factors
    if (P.band < 0.01) { return; }
    var x0 = V[7].X(winFrom - 0.5), x1 = V[7].X(winTo + 0.5);
    ctx.globalAlpha = P.band;
    ctx.fillStyle = "rgba(31,78,121,0.07)";
    ctx.fillRect(x0, PLOT.t, x1 - x0, PLOT.b - PLOT.t);
    ctx.font = "600 20px " + SANS; ctx.fillStyle = NAVY; ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    ctx.fillText("Anslått på " + D.meta.seasFrom.slice(0, 4) + "–" + D.meta.seasTo.slice(0, 4), x0 + 12, PLOT.b - 14);
    ctx.globalAlpha = 1;
  }

  function drawMarkers() {
    var v9 = V[9];
    if (P.ref > 0.01) {                                // reference month and the level 100
      ctx.globalAlpha = P.ref;
      var x = v9.X(refIdx), y100 = v9.Y(100);
      ctx.strokeStyle = INK; ctx.lineWidth = 1.6; ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(PLOT.l, y100); ctx.lineTo(PLOT.r + 8, y100); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x, PLOT.t - 4); ctx.lineTo(x, PLOT.b); ctx.stroke();
      ctx.font = "600 20px " + SANS; ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
      haloText(monthName(D.meta.ref), x, PLOT.t - 10, INK);
      ctx.globalAlpha = 1;
    }
    if (P.gpt > 0.01) {                                // ChatGPT launch
      ctx.globalAlpha = P.gpt;
      var xg = v9.X(gptX);
      ctx.strokeStyle = MUTE; ctx.lineWidth = 1.6; ctx.setLineDash([6, 5]);
      ctx.beginPath(); ctx.moveTo(xg, PLOT.t - 4); ctx.lineTo(xg, PLOT.b); ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = "600 20px " + SANS; ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
      haloText("ChatGPT lanseres", xg + 9, PLOT.t + 4, MUTE);
      ctx.globalAlpha = 1;
    }
  }

  function drawTable() {
    var ta = P.tbl, len = rows.length;
    ctx.textBaseline = "middle";
    if (ta > 0.01) {
      ctx.globalAlpha = ta;
      for (var i = 0; i < len; i += 2) {
        ctx.fillStyle = BAND;
        ctx.fillRect(TB.x0 - 16, TB.y0 + i * TB.rowH - TB.rowH / 2, TB.valRight - TB.x0 + 32, TB.rowH);
      }
      ctx.font = "600 20px " + SANS; ctx.fillStyle = MUTE; ctx.textAlign = "left";
      ctx.fillText("måned", TB.x0, TB.head);
      ctx.fillText("yrke (STYRK-08)", TB.xCode, TB.head);
      ctx.fillText("aldersgruppe", TB.xAge, TB.head);
      ctx.textAlign = "right"; ctx.fillText("antall ansatte", TB.valRight, TB.head);
      ctx.strokeStyle = "#c9c6bd"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(TB.x0 - 16, TB.rule); ctx.lineTo(TB.valRight + 16, TB.rule); ctx.stroke();
      ctx.fillStyle = INK; ctx.textAlign = "left";
      rows.forEach(function (r, k) {
        var y = TB.y0 + k * TB.rowH;
        ctx.font = "24px " + MONO;
        ctx.fillText(r[0], TB.x0, y); ctx.fillText(r[1], TB.xCode, y);
        ctx.font = "24px " + SANS;
        ctx.fillText(occTitle, TB.xTitle, y); ctx.fillText(ageLabel, TB.xAge, y);
      });
      ctx.fillStyle = MUTE; ctx.font = "24px " + SANS; ctx.textAlign = "left";
      var yd = TB.y0 + len * TB.rowH - 4;
      [TB.x0, TB.xCode, TB.xAge].forEach(function (x) { ctx.fillText("⋮", x + 4, yd); });
      ctx.textAlign = "right"; ctx.fillText("⋮", TB.valRight - 28, yd);
      ctx.globalAlpha = 1;
    }
    if (P.lblA > 0.01) {                               // the numbers, flying to their points
      var cb = bracket(P.v, 1, 5);
      ctx.globalAlpha = P.lblA; ctx.fillStyle = INK; ctx.textAlign = "center";
      rows.forEach(function (r, k) {
        var s = fmt(r[4]);
        ctx.font = "24px " + MONO;
        var sx = TB.valRight - ctx.measureText(s).width / 2, sy = TB.y0 + k * TB.rowH;
        var lf = easeIO(clamp((P.fly - 0.045 * k) / 0.5, 0, 1));
        var ex = lerp(cellX[cb.k][k], cellX[cb.k + 1][k], cb.f);
        var ey = lerp(cellY[cb.k][A * NM + k], cellY[cb.k + 1][A * NM + k], cb.f) + (numBelow[k] ? 24 : -22);
        var x = lerp(sx, ex, lf), y = lerp(sy, ey, lf), size = lerp(24, 20, lf);
        ctx.font = (lf >= 0.5 ? "700 " + size + "px " + SANS : size + "px " + MONO);
        ctx.fillText(s, x, y);
      });
      ctx.globalAlpha = 1;
    }
  }

  function xAtCell(cb, mf) {                           // current x of a (fractional) month index
    var m0 = clamp(Math.floor(mf), 0, NM - 1), m1 = Math.min(m0 + 1, NM - 1), t = clamp(mf - m0, 0, 1);
    var a = lerp(cellX[cb.k][m0], cellX[cb.k + 1][m0], cb.f), b = lerp(cellX[cb.k][m1], cellX[cb.k + 1][m1], cb.f);
    return lerp(a, b, t);
  }

  function strokeCells(list, cb, aggq, color, width, alpha) {
    var Y0 = cellY[cb.k], Y1 = cellY[cb.k + 1], X0 = cellX[cb.k], X1 = cellX[cb.k + 1], f = cb.f;
    ctx.beginPath();
    for (var n = 0; n < list.length; n++) {
      var base = list[n] * NM, pen = false;
      for (var m = 0; m < NM; m++) {
        var y0 = Y0[base + m];
        if (y0 !== y0) { pen = false; continue; }
        var y = f ? y0 + (Y1[base + m] - y0) * f : y0;
        if (aggq) { y += (collapsed[base + m] - y) * aggq; }
        var x = f ? X0[m] + (X1[m] - X0[m]) * f : X0[m];
        if (pen) { ctx.lineTo(x, y); } else { ctx.moveTo(x, y); pen = true; }
      }
    }
    ctx.globalAlpha = alpha; ctx.strokeStyle = color; ctx.lineWidth = width;
    ctx.lineJoin = "round"; ctx.lineCap = "round";
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function revealed(rev, cb, fn) {                     // left-to-right wipe up to month rev
    if (rev >= NM - 0.01) { fn(); return; }
    if (rev <= 0.01) { return; }
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, xAtCell(cb, rev - 1) + 0.5, H); ctx.clip();
    fn();
    ctx.restore();
  }

  function aggFor(q) { return easeIO(clamp((P.agg - 0.1 * q) / 0.6, 0, 1)); }

  function drawLines() {
    var cb = bracket(P.v, 1, 5);
    ctx.save();
    var padT = P.zy > 0.01 ? 0 : 16;                   // zoomed axis: lines that leave the plot are cut at its edge
    ctx.beginPath(); ctx.rect(PLOT.l - 8, PLOT.t - padT, PLOT.r - PLOT.l + 26, PLOT.b - PLOT.t + padT + 14); ctx.clip();

    if (P.aC > 0.01) {                                 // the cloud of thin lines
      revealed(P.revC, cb, function () {
        for (var q = 0; q < 5; q++) {
          var cq = clamp((P.col - 0.1 * q) / 0.6, 0, 1);
          strokeCells(cloud[q], cb, P.agg > 0 ? aggFor(q) : 0, mix(GREY, QC[q], cq), 0.9, P.aC * 0.2);
        }
      });
    }
    if (P.aN > 0.01) {                                 // the other three named lines
      revealed(P.revN, cb, function () {
        for (var n = 1; n < named.length; n++) {
          var q = named[n].q - 1, cq = clamp((P.col - 0.1 * q) / 0.6, 0, 1);
          strokeCells([named[n].cell], cb, P.agg > 0 ? aggFor(q) : 0, mix(INK, QC[q], cq), 3, P.aN);
        }
      });
    }
    if (P.aA > 0.01) {                                 // the first named line, with its dots
      var qa = named[0].q - 1, ca = mix(INK, QC[qa], clamp((P.col - 0.1 * qa) / 0.6, 0, 1));
      revealed(P.revA, cb, function () { strokeCells([A], cb, P.agg > 0 ? aggFor(qa) : 0, ca, 3.4, P.aA); });
      if (P.dotsA > 0.01) {
        ctx.globalAlpha = P.aA; ctx.fillStyle = ca; ctx.strokeStyle = PAPER; ctx.lineWidth = 2;
        for (var m = 0; m < NM; m++) {
          var rr = 6 * P.dotsA * clamp(P.revA - m, 0, 1);
          if (rr < 0.2) { continue; }
          var x = lerp(cellX[cb.k][m], cellX[cb.k + 1][m], cb.f);
          var y = lerp(cellY[cb.k][A * NM + m], cellY[cb.k + 1][A * NM + m], cb.f);
          ctx.beginPath(); ctx.arc(x, y, rr, 0, 6.2832); ctx.fill(); ctx.stroke();
        }
        ctx.globalAlpha = 1;
      }
    }

    if (P.qa > 0.01) {                                 // the five quintile lines
      var qb = bracket(P.v, 6, 10), k0 = qb.k, f = qb.f;
      for (var q2 = 0; q2 < 5; q2++) {
        var ya = qY[k0][q2], yb = qY[k0 + 1][q2], xa = qX[k0], xb = qX[k0 + 1], yz = qYz[q2];
        ctx.beginPath();
        for (var m2 = 0; m2 < NM; m2++) {
          var xx = f ? xa[m2] + (xb[m2] - xa[m2]) * f : xa[m2];
          var yy = f ? ya[m2] + (yb[m2] - ya[m2]) * f : ya[m2];
          if (P.zy > 0) { yy += (yz[m2] - yy) * P.zy; }
          if (m2) { ctx.lineTo(xx, yy); } else { ctx.moveTo(xx, yy); }
        }
        var al = q2 === FQ ? 1 - P.dv : (1 - 0.88 * P.sdim) * (1 - clamp(2 * P.dv, 0, 1));
        if (q2 > 0 && q2 < 4) { al *= 1 - 0.85 * P.kimode; }     // the KI-index compares only Q1 and Q5
        ctx.globalAlpha = P.qa * al; ctx.strokeStyle = QC[q2]; ctx.lineWidth = 4;
        ctx.lineJoin = "round"; ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    ctx.restore();
  }

  function drawSeasonal() {                            // trend, deviations, factors (quintile FQ)
    var x7 = V[7].X;
    if (P.trendA > 0.01 && P.trendDraw > 0.01) {
      ctx.save();
      ctx.beginPath(); ctx.rect(0, 0, x7(P.trendDraw - 1) + 0.5, H); ctx.clip();
      ctx.globalAlpha = P.trendA; ctx.strokeStyle = NAVY; ctx.lineWidth = 5;
      ctx.lineJoin = "round"; ctx.beginPath();
      var pen = false;
      for (var m = 0; m < NM; m++) {
        var t = trend[FQ][m];
        if (t !== t) { continue; }
        var y = lerp(VZ.Y(t), VD.Y(0), P.dv);
        if (pen) { ctx.lineTo(x7(m), y); } else { ctx.moveTo(x7(m), y); pen = true; }
      }
      ctx.stroke(); ctx.restore(); ctx.globalAlpha = 1;
    }

    if (P.fo > 0.01) {                                 // the other four quintiles' factors
      ctx.globalAlpha = P.fo;
      for (var q = 0; q < 5; q++) {
        if (q === FQ) { continue; }
        ctx.fillStyle = QC[q]; ctx.strokeStyle = PAPER; ctx.lineWidth = 2;
        for (var c = 0; c < 12; c++) {
          ctx.beginPath(); ctx.arc(colX(c) + (q - 1.5) * 15, VD.Y(D.fac[q][c]), 6, 0, 6.2832); ctx.fill(); ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
    }

    var da = clamp(P.dv * 3, 0, 1) * (1 - 0.55 * P.fb);
    if (da > 0.01) {                                   // one dot per month
      ctx.globalAlpha = da; ctx.strokeStyle = PAPER; ctx.lineWidth = 1.5;
      devPts.forEach(function (p) {
        var xt = x7(p.m), xc = colX(p.cm) + (p.rank - 1) * 19;
        var x = lerp(xt, xc, P.cm);
        var y = lerp(VZ.Y(D.pc[FQ][p.m]), VD.Y(dev[FQ][p.m]), P.dv);
        var hl = p.cm === hmIdx ? P.hm : 0;
        ctx.fillStyle = mix(QC[FQ], TEAL, hl);
        ctx.beginPath(); ctx.arc(x, y, 6 + 3 * hl, 0, 6.2832); ctx.fill(); ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    if (P.fb > 0.01) {                                 // the factors: one bar and one number per calendar month
      ctx.globalAlpha = P.fb;
      ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
      for (var c2 = 0; c2 < 12; c2++) {
        var fv = D.fac[FQ][c2], xx = colX(c2), yy = VD.Y(fv), col = c2 === hmIdx ? TEAL : INK;
        ctx.strokeStyle = col; ctx.lineWidth = 7; ctx.lineCap = "butt";
        ctx.beginPath(); ctx.moveTo(xx - 27, yy); ctx.lineTo(xx + 27, yy); ctx.stroke();
        ctx.font = "700 22px " + SANS;
        ctx.fillStyle = col; ctx.fillText(sgn(fv, 1), xx, PLOT.t - 16);
      }
      ctx.font = "600 20px " + SANS; ctx.fillStyle = MUTE; ctx.textAlign = "right";
      ctx.fillText("faktor", PLOT.l - 14, PLOT.t - 16);
      ctx.globalAlpha = 1;
    }

    if (P.hm > 0.01) {                                 // key for the highlighted month
      ctx.globalAlpha = P.hm * (1 - P.fb);
      ctx.fillStyle = TEAL; ctx.beginPath(); ctx.arc(PLOT.l + 22, PLOT.t + 22, 9, 0, 6.2832); ctx.fill();
      ctx.font = "600 22px " + SANS; ctx.textAlign = "left"; ctx.textBaseline = "middle";
      ctx.fillText("Alle " + hmName + "-måneder", PLOT.l + 40, PLOT.t + 22);
      ctx.globalAlpha = 1;
    }
  }

  function drawNameLabels() {
    if (P.labA < 0.01 && P.labN < 0.01) { return; }
    var cb = bracket(P.v, 1, 5), items = [];
    named.forEach(function (n, k) {
      var a = k === 0 ? P.labA : P.labN;
      if (a < 0.01) { return; }
      var y = lerp(cellY[cb.k][n.cell * NM + lastI], cellY[cb.k + 1][n.cell * NM + lastI], cb.f);
      var x = lerp(cellX[cb.k][lastI], cellX[cb.k + 1][lastI], cb.f);
      items.push({ x: x + 14, y: y, a: a, name: n.name, age: n.age + " år", q: n.q - 1 });
    });
    spread(items, 56, PLOT.b);
    ctx.textAlign = "left"; ctx.textBaseline = "middle";
    items.forEach(function (it) {
      ctx.globalAlpha = it.a;
      var col = mix(INK, QC[it.q], clamp(P.col, 0, 1));
      ctx.font = "700 22px " + SANS; haloText(it.name, it.x, it.y - 12, col);
      ctx.font = "500 20px " + SANS; haloText(it.age, it.x, it.y + 13, MUTE);
    });
    ctx.globalAlpha = 1;
  }

  function drawLegend() {
    if (P.leg < 0.01) { return; }
    ctx.globalAlpha = P.leg; ctx.textAlign = "left"; ctx.textBaseline = "middle";
    ctx.font = "600 18px " + SANS; ctx.fillStyle = MUTE;
    ctx.fillText("KI-EKSPONERING", 948, PLOT.t + 2);
    ctx.font = "22px " + SANS;
    for (var q = 0; q < 5; q++) {
      var y = PLOT.t + 42 + (4 - q) * 36;
      ctx.strokeStyle = QC[q]; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.moveTo(948, y); ctx.lineTo(980, y); ctx.stroke();
      ctx.fillStyle = INK; ctx.fillText(QL[q], 994, y);
    }
    ctx.globalAlpha = 1;
  }

  function labelColor(q) { return QC[q] === "#E6A817" ? "#9a6f00" : QC[q]; }   // the yellow needs a darker text

  function drawEndLabels() {                           // direct labels at the right end of the five lines
    if (P.qlab < 0.01) { return; }
    var qb = bracket(P.v, 6, 10), items = [];
    for (var q = 0; q < 5; q++) {
      var y = lerp(qY[qb.k][q][lastI], qY[qb.k + 1][q][lastI], qb.f);
      if (P.zy > 0) { y = lerp(y, qYz[q][lastI], P.zy); }
      var x = lerp(qX[qb.k][lastI], qX[qb.k + 1][lastI], qb.f);
      var a = P.qlab * (q === FQ ? 1 : 1 - P.sdim) * (1 - clamp(2 * P.dv, 0, 1)) * (1 - P.kimode);
      items.push({ x: x + 14, y: y, q: q, a: a });
    }
    spread(items, 30, PLOT.b);
    ctx.textAlign = "left"; ctx.textBaseline = "middle";
    items.forEach(function (it) {
      if (it.a < 0.01) { return; }
      ctx.globalAlpha = it.a;
      var strong = it.q === 0 || it.q === 4;
      ctx.font = (strong ? "700 24px " : "600 22px ") + SANS;
      haloText(QL[it.q], it.x, it.y, labelColor(it.q));
    });
    ctx.globalAlpha = 1;
  }

  /* The elements behind the KI-index: for Q1 and Q5, the mean of the three months to and including
     the reference month against the mean of the last three months, and the growth between them. */
  function ma3(arr) {                                  // trailing three-month mean, rounded as on the site
    return arr.map(function (v, i) {
      var s = 0, n = 0;
      for (var j = i - 2; j <= i; j++) { if (j >= 0) { s += arr[j]; n++; } }
      return Math.round(100 * s / n) / 100;
    });
  }
  var hlI = D.months.indexOf(D.headline.ref);
  var kiQ = [0, 4].map(function (q) {
    var sm = ma3(D.idx[q]), r = sm[lastI] / sm[hlI];  // r = level now as a share of the level before
    return { q: q, before: sm[hlI], after: sm[lastI], r: r, g: 100 * (r - 1) };
  });
  var kiRatio = kiQ[1].r / kiQ[0].r;                   // Q5 now/before divided by Q1 now/before
  var kiRel = 100 * (kiRatio - 1);
  if (Math.abs(kiRel - D.headline.rel) > 0.011) { console.warn("KI-indeksen i animasjonen avviker fra datafilen", kiRel, D.headline.rel); }
  function span(m0, m1) { return MON[+D.months[m0].slice(5, 7) - 1] + "–" + MON[+D.months[m1].slice(5, 7) - 1] + " " + D.months[m1].slice(0, 4); }

  function drawKI() {
    if (P.kib < 0.01 && P.kig < 0.01) { return; }
    var v9 = V[9];
    var bx0 = v9.X(hlI - 2.5), bx1 = v9.X(hlI + 0.5), ax0 = v9.X(lastI - 2.5), ax1 = v9.X(lastI + 0.5);
    ctx.globalAlpha = P.kib; ctx.fillStyle = "rgba(31,78,121,0.09)";
    ctx.fillRect(bx0, PLOT.t, bx1 - bx0, PLOT.b - PLOT.t);
    ctx.fillRect(ax0, PLOT.t, ax1 - ax0, PLOT.b - PLOT.t);
    ctx.font = "600 20px " + SANS; ctx.fillStyle = NAVY; ctx.textBaseline = "alphabetic";
    ctx.textAlign = "center"; ctx.fillText("Snitt " + span(hlI - 2, hlI), (bx0 + bx1) / 2, PLOT.b - 16);
    ctx.textAlign = "right"; ctx.fillText("Snitt " + span(lastI - 2, lastI), ax1 + 6, PLOT.b - 16);
    var items = [];
    kiQ.forEach(function (k, n) {
      var col = QC[k.q], yb = v9.Y(k.before), ya = v9.Y(k.after);
      ctx.globalAlpha = P.kib; ctx.strokeStyle = col; ctx.lineWidth = 7; ctx.lineCap = "butt";
      ctx.beginPath(); ctx.moveTo(bx0, yb); ctx.lineTo(bx1, yb); ctx.moveTo(ax0, ya); ctx.lineTo(ax1, ya); ctx.stroke();
      var xa = ax1 + 12 + n * 18;                      // dashed carry-over of the "before" level, then an arrow to the "after" level
      ctx.globalAlpha = P.kib * 0.85; ctx.lineWidth = 2; ctx.setLineDash([8, 6]);
      ctx.beginPath(); ctx.moveTo(bx1, yb); ctx.lineTo(xa, yb); ctx.stroke(); ctx.setLineDash([]);
      if (P.kia > 0.01) {
        var yt = lerp(yb, ya, P.kia), dir = ya > yb ? 1 : -1;
        ctx.globalAlpha = 1; ctx.lineWidth = 4;
        ctx.beginPath(); ctx.moveTo(xa, yb); ctx.lineTo(xa, yt); ctx.stroke();
        if (Math.abs(yt - yb) > 12) {
          ctx.fillStyle = col; ctx.beginPath();
          ctx.moveTo(xa, yt + dir * 3); ctx.lineTo(xa - 8, yt - dir * 11); ctx.lineTo(xa + 8, yt - dir * 11); ctx.closePath(); ctx.fill();
        }
      }
      items.push({ x: ax1 + 12 + 2 * 18 + 8, y: ya, q: k.q, g: k.g, r: k.r });
    });
    if (P.kig > 0.01) {                                // the growth of each, and what it leaves as a share of the level before
      spread(items, 66, PLOT.b - 20);
      ctx.textAlign = "left"; ctx.textBaseline = "middle"; ctx.globalAlpha = P.kig;
      items.forEach(function (it) {
        ctx.font = "700 24px " + SANS;
        haloText("Q" + (it.q + 1) + " " + sgn(it.g, 2) + " %", it.x, it.y - 14, labelColor(it.q));
        ctx.font = "20px " + SANS;
        haloText(fmt(it.r, 4) + " av nivået før", it.x, it.y + 14, MUTE);
      });
    }
    ctx.globalAlpha = 1;
  }

  var INS = { x: 948, y: 178, w: 292, h: 62 };
  function drawInsets() {
    if (P.pop > 0.01) {                                // the denominator
      ctx.globalAlpha = P.pop;
      var lo = Infinity, hi = -Infinity;
      D.pop.forEach(function (p) { lo = Math.min(lo, p); hi = Math.max(hi, p); });
      lo *= 0.985; hi *= 1.005;
      ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
      ctx.font = "600 18px " + SANS; ctx.fillStyle = MUTE;
      ctx.fillText("BEFOLKNING " + AGE + " ÅR", INS.x, INS.y - 18);
      ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.beginPath();
      D.pop.forEach(function (p, m) {
        var x = INS.x + m / (NM - 1) * INS.w, y = INS.y + INS.h - (p - lo) / (hi - lo) * INS.h;
        if (m) { ctx.lineTo(x, y); } else { ctx.moveTo(x, y); }
      });
      ctx.stroke();
      ctx.font = "600 22px " + SANS; ctx.fillStyle = INK;
      ctx.textAlign = "left"; ctx.fillText(fmt(D.pop[0] / 1e6, 2) + " mill.", INS.x, INS.y + INS.h + 32);
      ctx.textAlign = "right"; ctx.fillText(fmt(D.pop[NM - 1] / 1e6, 2) + " mill.", INS.x + INS.w, INS.y + INS.h + 32);
      ctx.globalAlpha = 1;
    }
  }

  function render() {
    ctx.setTransform(pr, 0, 0, pr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    drawBand();
    drawAxes();
    drawMarkers();
    drawTable();
    drawLines();
    drawSeasonal();
    drawKI();
    drawNameLabels();
    drawLegend();
    drawEndLabels();
    drawInsets();
  }

  /* ------------------------------------------------------------------ */
  /* captions, formulas and the step dots (plain DOM, crisp text)        */
  /* ------------------------------------------------------------------ */
  var elKick = root.querySelector(".pl-kicker"), elTitle = root.querySelector(".pl-title"),
      elSub = root.querySelector(".pl-sub"), elHead = root.querySelector(".pl-head"),
      elForm = root.querySelector(".pl-formula"), elFacts = root.querySelector(".pl-facts"),
      elRes = root.querySelector(".pl-result"), elDots = root.querySelector(".pl-dots");

  elFacts.innerHTML =
    "<div class='big'>" + fmt(D.meta.nRows) + "</div>" +
    "<div>rader. Hver rad er antall ansatte i ett yrke og én aldersgruppe i én måned.</div>" +
    "<div class='kv'><b>" + fmt(NC) + "</b> serier<br><b>" + fmt(D.meta.nOcc) + "</b> yrker<br><b>" +
    fmt(NM) + "</b> måneder</div>";
  function calcRow(op, num, text, color, cls) {
    return "<tr" + (cls ? " class='" + cls + "'" : "") + "><td class='op'>" + op + "</td><td class='n'>" + num +
           "</td><td class='t'" + (color ? " style='color:" + color + "'" : "") + ">" + text + "</td></tr>";
  }
  elRes.innerHTML =
    "<div class='lab'>KI-indeksen" + (ALL_AGES ? "" : ", " + AGE + " år") + "</div>" +
    "<div class='big'>" + sgn(kiRel, 1) + "</div>" +
    "<div>prosent per " + monthName(D.headline.last) + "</div>" +
    "<table class='calc'>" +
      calcRow("", fmt(kiQ[1].r, 4), "Q5 nå / før", labelColor(4)) +
      calcRow("/", fmt(kiQ[0].r, 4), "Q1 nå / før", labelColor(0)) +
      calcRow("=", fmt(kiRatio, 4), "Q5 / Q1", "", "sum") +
    "</table>" +
    "<div class='small'>Q5 ligger " + fmt(Math.abs(kiRel), 2) + " prosent " + (kiRel >= 0 ? "høyere" : "lavere") +
    " i forhold til Q1 enn før. Standardfeil er ikke vist her.</div>";

  for (var di = 0; di <= LAST; di++) { var dot = document.createElement("span"); elDots.appendChild(dot); }
  var swapTimer = 0;
  function updateDom(k, instant) {
    var s = STEPS[k];
    function apply() {
      elKick.textContent = s.head[0]; elTitle.textContent = s.head[1]; elSub.textContent = s.head[2];
      if (s.form) { elForm.innerHTML = s.form; }
      elForm.classList.toggle("on", !!s.form);
      elHead.classList.remove("out");
    }
    clearTimeout(swapTimer);
    if (instant || reduce) { apply(); } else { elHead.classList.add("out"); swapTimer = setTimeout(apply, 170); }
    elFacts.classList.toggle("on", !!s.facts);
    elRes.classList.toggle("on", !!s.result);
    var ds = elDots.children;
    for (var i = 0; i < ds.length; i++) { ds[i].classList.toggle("on", i === k); ds[i].classList.toggle("past", i < k); }
  }

  /* ------------------------------------------------------------------ */
  /* reveal.js: each fragment on the slide is one click                  */
  /* ------------------------------------------------------------------ */
  function onOurSlide() {
    var s = window.Reveal && Reveal.getCurrentSlide && Reveal.getCurrentSlide();
    return s && s.contains(root) ? s : null;
  }
  function stepFromFragments() {
    var s = onOurSlide();
    return s ? s.querySelectorAll(".fragment.visible").length : null;
  }
  function wire() {
    fit();
    Reveal.on("fragmentshown", function () { var k = stepFromFragments(); if (k != null) { goTo(k); } });
    Reveal.on("fragmenthidden", function () { var k = stepFromFragments(); if (k != null) { goTo(k); } });
    Reveal.on("slidechanged", function () { var k = stepFromFragments(); if (k != null) { fit(); goTo(k, true); } });
    Reveal.on("resize", function () { fit(); render(); });
    var k0 = stepFromFragments();
    goTo(k0 == null ? 0 : k0, true);
    cur = k0 == null ? 0 : k0;
  }
  function boot() {
    if (window.Reveal && Reveal.isReady && Reveal.isReady()) { wire(); }
    else if (window.Reveal) { Reveal.on("ready", wire); }
    else { setTimeout(boot, 60); }
  }
  boot();

  return { goTo: goTo, P: P, STEPS: STEPS, T: T, render: render, scrub: scrub };   // for testing from the console
}

(function () {                                         // one animation per data file that is present
  var made = {};
  [["all", "pl", window.PIPELINE_DATA], ["young", "pl-young", window.PIPELINE_DATA_YOUNG]].forEach(function (a) {
    var root = document.getElementById(a[1]);
    if (a[2] && root) { made[a[0]] = createPipeline(a[2], root); }
  });
  window.__pls = made;
  window.__pl = made.all;
})();
