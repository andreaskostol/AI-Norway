/*
 * mapping.js
 *
 * Two animations in one engine: how an exposure score travels from O*NET tasks to Norwegian STYRK-08
 * occupations, for Eloundou et al. (2024) and for Mouchel et al. (2026).
 *
 * Same principle as data-pipeline: every click (reveal.js fragment) tweens a set of parameters and the
 * canvas redraws from them, so tables, codes and dots move into each other instead of being swapped.
 * Text cards, tables and boxes are plain HTML on top of the canvas, so they stay sharp.
 *
 * Data: window.MAP_ELOUNDOU and window.MAP_MOUCHEL from data/*.js (built by build_data.py).
 * Plain JavaScript and canvas. No libraries, no network.
 */
function createMapping(D, root, kind) {
  "use strict";

  var E = kind === "e";                                // Eloundou (true) or Mouchel (false)
  var canvas = root.querySelector("canvas");
  var ctx = canvas.getContext("2d");

  /* ------------------------------------------------------------------ */
  /* constants and helpers                                               */
  /* ------------------------------------------------------------------ */
  var W = 1280, H = 720;
  var PLOT = { l: 150, r: 900, t: 284, b: 630 };
  var INK = "#1d2733", MUTE = "#5d6772", GREY = "#8d97a1", GRID = "#e2dfd7", PAPER = "#fbfaf7";
  var BAND = "#f1efe9", NAVY = "#1F4E79", TEAL = "#0B7A75";
  var QC = ["#577590", "#E6A817", "#E54A2B", "#8C1515", "#401415"];
  var ECOL = { E0: ["#e6e3dc", "#5d6772"], E1: ["#8C1515", "#ffffff"], E2: ["#E6A817", "#1d2733"] };
  var SANS = "'Segoe UI', Calibri, Arial, sans-serif";

  function clamp(x, a, b) { return x < a ? a : (x > b ? b : x); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function easeIO(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function fmt(n, d) {
    d = d || 0;
    return n.toLocaleString("nb-NO", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function hex(c) { return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]; }
  function mix(c1, c2, t) {
    var a = hex(c1), b = hex(c2);
    return "rgb(" + Math.round(lerp(a[0], b[0], t)) + "," + Math.round(lerp(a[1], b[1], t)) + "," +
      Math.round(lerp(a[2], b[2], t)) + ")";
  }
  function labelColor(q) { return QC[q] === "#E6A817" ? "#9a6f00" : QC[q]; }
  function haloText(str, x, y, color) {
    ctx.lineJoin = "round"; ctx.lineWidth = 5; ctx.strokeStyle = PAPER;
    ctx.strokeText(str, x, y);
    ctx.fillStyle = color; ctx.fillText(str, x, y);
  }
  function rrect(x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  function card(x, y, w, h) {                          // white card with a soft shadow
    ctx.save();
    ctx.shadowColor = "rgba(29,39,51,0.16)"; ctx.shadowBlur = 16; ctx.shadowOffsetY = 4;
    ctx.fillStyle = "#ffffff"; rrect(x, y, w, h, 12); ctx.fill();
    ctx.restore();
  }
  var wrapCache = {};
  var SHY = "­";                                   // soft hyphen: a word may be broken here if it does not fit
  function soft(s) { return s.replace("Informasjonsrådgivere", "Informasjons" + SHY + "rådgivere"); }
  function wrap(str, maxW, font) {                     // up to two lines
    var k = str + "|" + maxW + "|" + font;
    if (wrapCache[k]) { return wrapCache[k]; }
    ctx.font = font;
    var words = str.split(" "), lines = [""], i;
    for (i = 0; i < words.length; i++) {
      var w = words[i], plain = w.replace(/­/g, ""), cur = lines[lines.length - 1];
      if (cur && ctx.measureText(cur + " " + plain).width <= maxW) { lines[lines.length - 1] = cur + " " + plain; continue; }
      if (cur) { lines.push(""); }
      if (ctx.measureText(plain).width <= maxW || w.indexOf(SHY) < 0) { lines[lines.length - 1] = plain; }
      else { var p = w.split(SHY); lines[lines.length - 1] = p[0] + "-"; lines.push(p.slice(1).join("")); }
    }
    wrapCache[k] = lines.slice(0, 2);
    return wrapCache[k];
  }

  /* ------------------------------------------------------------------ */
  /* data                                                                */
  /* ------------------------------------------------------------------ */
  var N = D.dots.length;
  var key = E ? "eloundou_beta" : "a", rkey = E ? "r_eloundou_beta" : "ra";
  var yMax = E ? 1.25 : 1.15;                          // headroom above the highest dot, for the group labels
  var yTickMax = 1;
  var DX0 = new Float32Array(N), DX1 = new Float32Array(N), DX2 = new Float32Array(N), DY = new Float32Array(N),
      DQ = new Uint8Array(N), idxOf = {};
  D.dots.forEach(function (d, i) {
    DX0[i] = PLOT.l + (i + 0.5) / N * (PLOT.r - PLOT.l);
    DX1[i] = PLOT.l + (d[rkey] - 0.5) / N * (PLOT.r - PLOT.l);
    DX2[i] = E ? DX1[i] : PLOT.l + d.e * (PLOT.r - PLOT.l);
    DY[i] = PLOT.b - d[key] / yMax * (PLOT.b - PLOT.t);
    DQ[i] = d.q - 1;
    idxOf[d.c] = i;
  });
  var QCOUNT = D.meta.q;                               // 80, 79, 79, 79, 80
  var exampleCodes = ["2432", "2512", "7411", "5223"];
  var moverCodes = E ? [] : D.movers.up.concat(D.movers.down);

  /* ------------------------------------------------------------------ */
  /* html layers: right-hand card, wide area, note row                   */
  /* ------------------------------------------------------------------ */
  function rise(i) { return "rise' style='animation-delay:" + (i * 0.12).toFixed(2) + "s"; }
  function legend(withBeta) {
    var rows = [["e0", "E0", "Ingen eksponering", "0"], ["e1", "E1", "Språkmodellen alene halverer tiden", "1"],
                ["e2", "E2", "Modell og tilleggsprogramvare halverer tiden", "0,5"]];
    return "<div class='lab'>GPT-4s vurdering</div>" + rows.map(function (r, i) {
      return "<div class='leg-row " + rise(i) + "'><div><span class='chip " + r[0] + "'>" + r[1] + "</span>" +
             (withBeta ? "<span class='val'>β = " + r[3] + "</span>" : "") + "</div><div class='tx'>" + r[2] + "</div></div>";
    }).join("");
  }
  function calcCard() {
    var o = D.occ;
    return "<div class='lab'>Skår for yrket</div><table class='calc'>" +
      "<tr class='" + rise(0) + "'><td class='op'></td><td class='n'>" + fmt(o.num, 1) + "</td><td class='t'>Σ vekt × β</td></tr>" +
      "<tr class='" + rise(1) + "'><td class='op'>/</td><td class='n'>" + fmt(o.den, 0) + "</td><td class='t'>Σ vekt</td></tr>" +
      "<tr class='sum " + rise(2) + "'><td class='op'>=</td><td class='n'>" + fmt(o.beta, 3) + "</td><td class='t'>β for yrket</td></tr></table>";
  }
  function qchip(q) { return "<span class='chip q" + q + "'>Q" + q + "</span>"; }
  function resultE() {
    var rows = D.ex.map(function (r, i) {
      return "<tr class='" + (r.c === "2432" ? "hl " : "") + rise(i) + "'><td class='code'>" + r.c + "</td><td>" + r.n + "</td><td class='num'>" + fmt(r.b, 3) +
             "</td><td class='num'>" + r.r + " av " + N + "</td><td>" + qchip(r.q) + "</td></tr>";
    }).join("");
    return "<table class='res' style='width:860px'><tr><th>STYRK-08</th><th>Yrke</th><th class='num'>Skår</th><th class='num'>Plass</th><th>Gruppe</th></tr>" + rows + "</table>";
  }
  function resultM() {
    var rows = D.ex.map(function (r, i) {
      return "<tr class='" + (r.c === "2432" ? "hl " : "") + rise(i) + "'><td class='code'>" + r.c + "</td><td>" + r.n + "</td><td class='num'>" + fmt(r.e, 3) +
             "</td><td>" + qchip(r.qe) + "</td><td class='num'>" + fmt(r.a, 3) + "</td><td>" + qchip(r.q) +
             "</td><td class='num'>" + fmt(r.s, 3) + "</td></tr>";
    }).join("");
    return "<table class='res'><tr><th>STYRK-08</th><th>Yrke</th><th class='num'>Eloundou</th><th>Gruppe</th>" +
           "<th class='num'>Mouchel A1</th><th>Gruppe</th><th class='num'>Mouchel S0</th></tr>" + rows + "</table>";
  }
  function introE() {                                   // O*NET in three numbers, before the example
    var m = D.meta, arrow = function (i) { return "<div class='arrow " + rise(i) + "'>→</div>"; };
    return "<div class='flow'>" +
      "<div class='box short " + rise(0) + "'><div class='k'>Yrker i O*NET 27.2</div><div class='n'>" + fmt(m.nOnet) + "</div><div class='t'>med oppgavebeskrivelser</div></div>" +
      arrow(2) +
      "<div class='box short " + rise(3) + "'><div class='k'>Til sammen</div><div class='n'>" + fmt(m.nTasks) + "</div><div class='t'>konkrete oppgaver</div></div>" +
      arrow(5) +
      "<div class='box short " + rise(6) + "'><div class='k'>Eksempel</div><div class='n'>" + D.tasks.length + "</div><div class='t'>oppgaver for informasjons&shy;rådgivere</div></div></div>";
  }
  function processM() {
    var m = D.meta, dr = "";
    for (var i = 0; i < m.nModels; i++) { dr += "<i></i>"; }
    return "<div class='flow'>" +
      "<div class='box " + rise(0) + "'><div class='k'>O*NET</div><div class='n'>Alle</div><div class='t'>oppgaver for alle yrker i datasettet fra US Department of Labor</div></div>" +
      "<div class='arrow " + rise(2) + "'>→</div>" +
      "<div class='box " + rise(3) + "'><div class='k'>Grunnlag</div><div class='n' style='font-size:38px'>ca. " + fmt(m.nNews) + "</div><div class='t'>nyhetsartikler</div>" +
      "<div class='n' style='font-size:38px;margin-top:14px'>ca. " + fmt(m.nAbstracts) + "</div><div class='t'>forskningssammendrag</div></div>" +
      "<div class='arrow " + rise(5) + "'>→</div>" +
      "<div class='box " + rise(6) + "'><div class='k'>Vurdering</div><div class='n'>" + m.nModels + "</div><div class='t'>åpne språkmodeller</div><div class='dotrow'>" + dr + "</div></div>" +
      "<div class='arrow " + rise(8) + "'>→</div>" +
      "<div class='box " + rise(9) + "'><div class='k'>Per oppgave</div><div class='chips'><span class='chip e0'>E0</span><span class='chip e1'>E1</span>" +
      "<span class='chip e2'>E2</span><span class='chip e3'>E3</span></div><div class='t' style='margin-top:18px'>Ett utfall på grunnlag av kildene</div></div></div>";
  }
  function rubricM() {
    var cols = [["e0", "E0", "Ingen eksponering", "0"],
                ["e1", "E1", "En agent med vanlige nettleser- og arbeidsverktøy halverer tiden", "1"],
                ["e2", "E2", "Trenger tilleggsprogramvare eller integrasjoner i virksomheten", "0,5"],
                ["e3", "E3", "Halverer tiden først når modellen kan tolke bilder og video", "0,5"]];
    return "<div class='rub'>" + cols.map(function (c, i) {
      return "<div class='col " + rise(i) + "'><span class='chip " + c[0] + "'>" + c[1] + "</span><div class='d'>" + c[2] +
             "</div><div class='b'>Poeng</div><div class='bv'>" + c[3] + "</div></div>";
    }).join("") + "</div>";
  }
  function barsM() {
    var o = D.occ;
    var rows = [["Eloundou", "GPT-4, Eloundou mfl. (2024)", o.e, GREY], ["Mouchel A1", "Snittet av de sju modellene, ikke kalibrert", o.a, NAVY],
                ["Mouchel S0", "Kalibrert mot faktisk Claude-bruk", o.s, TEAL]];
    return "<div class='lab' style='margin-top:6px'>Informasjonsrådgivere, O*NET " + o.onet + "</div><div class='bars'>" + rows.map(function (r, i) {
      return "<div class='bar " + rise(i) + "'><div class='nm'>" + r[0] + "<span>" + r[1] + "</span></div><div class='tr'><div class='fl' style='width:" +
             (r[2] * 100).toFixed(1) + "%;background:" + r[3] + ";animation-delay:" + (0.25 + i * 0.2).toFixed(2) + "s'></div><div class='v'>" + fmt(r[2], 3) + "</div></div></div>";
    }).join("") + "</div>";
  }
  function corrCard() {
    var c = D.corr, big = "font-size:46px";
    return "<div class='lab'>Mouchel A1 mot Eloundou</div>" +
      "<div class='" + rise(0) + "'><div class='big' style='" + big + "'>" + fmt(c.pearson, 2) + "</div><div class='small'>korrelasjon. Spearman " + fmt(c.spearman, 2) + "</div></div>" +
      "<div class='" + rise(1) + "' style='margin-top:16px'><div class='big' style='" + big + "'>" + fmt(c.sameQ, 0) + " %</div><div class='small'>i samme gruppe</div></div>" +
      "<div class='" + rise(2) + "' style='margin-top:16px'><div class='big' style='" + big + "'>" + fmt(c.withinOne, 0) + " %</div><div class='small'>innen én gruppe</div></div>";
  }

  /* ------------------------------------------------------------------ */
  /* steps                                                               */
  /* ------------------------------------------------------------------ */
  var DEF = { tbl: 0, ch: 0, bt: 0, wt: 0, chA: 0, chn: 0, tka: 0, tf: 0, tp: 0, mfA: 0, mg: 0, fn: 0, exA: 0, ex: 0,
              ax: 0, dts: 0, dx: 0, dc: 0, bnd: 0, lab0: 0, lab: 0, lab2: 0 };
  var pctCoverage = fmt(100 * D.meta.nStyrk / D.meta.nStyrkAll, 1);
  var EX = D.chain[4];                                 // the running example: STYRK 2432 Informasjonsrådgivere
  function tag(k, n, c) { return "<div class='k'>" + k + "</div><div class='n'>" + n + "</div><div class='c'>" + c + "</div>"; }
  var EXAMPLE_ONET = tag("Eksempel", EX.n, "O*NET " + D.occ.onet);          // before STYRK has been explained
  var EXAMPLE = tag("Eksempel", EX.n, "STYRK " + EX.c + " · O*NET " + D.occ.onet);
  var ACR = [["SOC", "Standard Occupational Classification, USAs yrkeskoder"],
             ["ISCO-08", "International Standard Classification of Occupations, FNs yrkeskoder"],
             ["STYRK-08", "Standard for yrkesklassifisering, Norges versjon av ISCO-08"],
             ["BLS", "Bureau of Labor Statistics, USAs arbeidsstatistikk. Utgir koblingene mellom kodene"]];
  function acrNote() {                                 // the acronyms of the code chain, spelled out where the chain appears
    return "<div class='acr'>" + ACR.map(function (r, i) {
      return "<div class='" + rise(i) + "'><b>" + r[0] + "</b><span>" + r[1] + "</span></div>";
    }).join("") + "</div>";
  }

  var STEPS;
  if (E) {
    STEPS = [
      { head: ["O*NET", "Yrker beskrives som oppgaver",
               "O*NET er et datasett fra US Department of Labor.\nHvert yrke har en liste med konkrete oppgaver."],
        tab: introE(), set: {} },
      { head: ["Eksempel", "Et yrke er en liste med oppgaver",
               "Informasjonsrådgivere har " + D.tasks.length + " oppgaver i O*NET:\n" + D.occ.core + " kjerneoppgaver og " + D.occ.supp + " tilleggsoppgaver."],
        tag: EXAMPLE_ONET, tab: "", set: { tbl: 1 } },
      { head: ["Eloundou mfl.", "GPT-4 vurderer hver oppgave",
               "Kan en språkmodell halvere tiden på oppgaven?"],
        tag: EXAMPLE_ONET, card: legend(false), dur: 2600, set: { ch: 1 }, win: { ch: [0.1, 1] }, ease: { ch: "lin" } },
      { head: ["Poeng per oppgave", "Hver vurdering får et poeng", "Poenget kalles β. E1 gir 1, E2 gir 0,5 og E0 gir 0."],
        tag: EXAMPLE_ONET, card: legend(true), dur: 2400, set: { bt: 1 }, win: { bt: [0.1, 1] }, ease: { bt: "lin" } },
      { head: ["Skår for yrket", "Kjerneoppgaver teller dobbelt",
               "Kjerneoppgaver har vekt 2, tilleggsoppgaver vekt 1.\nDet veide snittet er skåren for yrket."],
        tag: EXAMPLE_ONET, card: calcCard(), dur: 2200, set: { wt: 1 }, win: { wt: [0, 0.5] } },
      { head: ["Fra O*NET til STYRK", "Skåren følger koden",
               "Fire koblinger tar O*NET-koden til en norsk yrkeskode.\nO*NET bruker SOC 2018, men ISCO-koblingen er laget for SOC 2010."],
        tag: EXAMPLE, card: "", note: acrNote(), dur: 4200, set: { tbl: 0, wt: 0, chA: 1, chn: 5, tka: 1, tf: 1, tp: 4 },
        win: { tbl: [0, 0.2], wt: [0, 0.2], chA: [0.05, 0.15], chn: [0.15, 0.6], tka: [0, 0.05], tf: [0.05, 0.4], tp: [0.55, 1] }, ease: { chn: "lin", tp: "lin" } },
      { head: ["Når kodene ikke passer", "Flere blir én, én blir flere",
               "Flere koder blir én: gjennomsnitt.\nÉn kode blir flere: samme skår kopieres."],
        tag: "<div class='k'>Eksempler</div><div class='n m'>Elektrikere</div><div class='n m'>Ledere i generell drift</div>",
        note: "", dur: 4200, set: { chA: 0, tka: 0, mfA: 1, mg: 1, fn: 1 },
        win: { chA: [0, 0.2], tka: [0, 0.2], mfA: [0.15, 0.3], mg: [0.25, 0.62], fn: [0.6, 1] }, ease: { mg: "lin", fn: "lin" } },
      { head: ["Norske unntak", "Fire koder får skår et annet sted",
               "To koder kopierer spesialsykepleiere.\nTo hentes fra SOC, fordi ISCO-koden betyr noe annet i Norge."],
        tag: tag("Norske koder", "Fire unntak", "2223, 2224, 2267 og 2269"),
        dur: 3200, set: { mfA: 0, exA: 1, ex: 1 }, win: { mfA: [0, 0.2], exA: [0.15, 0.3], ex: [0.2, 1] }, ease: { ex: "lin" } },
      { head: ["Alle yrker", D.meta.nStyrk + " norske yrker har skår",
               "Det er " + pctCoverage + " prosent av de " + D.meta.nStyrkAll + " yrkeskodene i STYRK-08."],
        tag: "", dur: 3000, set: { exA: 0, ax: 1, dts: 1, lab0: 1 },
        win: { exA: [0, 0.2], ax: [0.2, 0.5], dts: [0.25, 1], lab0: [0.85, 1] }, ease: { dts: "lin" } },
      { head: ["Gruppene", "Fem like store grupper",
               "Yrkene rangeres etter skår og deles i fem grupper\nmed like mange yrker. Q1 er minst og Q5 mest eksponert."],
        dur: 3800, set: { dx: 1, dc: 1, bnd: 1, lab: 1 }, win: { dx: [0, 0.55], dc: [0.5, 0.75], bnd: [0.65, 0.9], lab: [0.85, 1] } },
      { head: ["Resultatet", "Hvert yrke får skår og gruppe",
               "Filen styrk08_eloundou_beta_mapping.csv har " + D.meta.nStyrk + " rader."],
        tab: resultE(), dur: 1800, set: { ax: 0, dts: 0, bnd: 0, lab0: 0, lab: 0 },
        win: { ax: [0, 0.4], dts: [0, 0.4], bnd: [0, 0.4], lab0: [0, 0.4], lab: [0, 0.4] } }
    ];
  } else {
    STEPS = [
      { head: ["Mouchel mfl.", "Samme oppgaver, ny vurdering",
               "O*NET-oppgavene vurderes på nytt,\nmed grunnlag i nyheter og forskning."],
        tab: processM(), set: {} },
      { head: ["Rubrikken", "Klassene er oppdatert for 2026",
               "Eloundous klasser, tilpasset agentisk KI i 2026.\nE3 gjelder oppgaver der bilde eller video trengs."],
        tab: rubricM(), set: {} },
      { head: ["Fra oppgave til yrke", "To skår per yrke",
               "Oppgavene veies med O*NET-oppgavetid\ntil en skår per yrke, i to varianter."],
        tag: EXAMPLE_ONET, tab: barsM(), set: {} },
      { head: ["Fra O*NET til STYRK", "Samme kobling som for Eloundou",
               "Skåren følger koden gjennom de samme fire koblingene.\nO*NET bruker SOC 2018, men ISCO-koblingen er laget for SOC 2010.\nFlere blir én: snitt. Én blir flere: kopi."],
        tag: EXAMPLE, tab: "", note: acrNote(), dur: 4200, set: { chA: 1, chn: 5, tka: 1, tf: 1, tp: 4 },
        win: { chA: [0, 0.1], chn: [0.1, 0.55], tka: [0.5, 0.6], tp: [0.55, 1] }, ease: { chn: "lin", tp: "lin" } },
      { head: ["Alle yrker", D.meta.nStyrk + " norske yrker har skår",
               "Her varianten A1. Hver prikk er ett yrke."],
        note: "", dur: 3000, set: { chA: 0, tka: 0, ax: 1, dts: 1, lab0: 1 },
        win: { chA: [0, 0.2], tka: [0, 0.2], ax: [0.2, 0.5], dts: [0.25, 1], lab0: [0.85, 1] }, ease: { dts: "lin" } },
      { head: ["Gruppene", "Fem like store grupper",
               "Rangert på A1 og delt i fem like store grupper.\nQ1 er minst og Q5 mest eksponert."],
        dur: 3800, set: { dx: 1, dc: 1, bnd: 1, lab: 1 }, win: { dx: [0, 0.55], dc: [0.5, 0.75], bnd: [0.65, 0.9], lab: [0.85, 1] } },
      { head: ["Mot Eloundou", "Nesten samme rangering",
               "Hvert yrke: Eloundou-skåren mot Mouchel-skåren.\nFarge etter Mouchel-gruppe."],
        card: corrCard(), dur: 3600, set: { dx: 2, bnd: 0, lab: 0, lab2: 1 },
        win: { dx: [0.05, 0.7], bnd: [0, 0.3], lab: [0, 0.3], lab2: [0.75, 1] } },
      { head: ["Resultatet", "Hvert yrke får to skår og to grupper",
               "Filen styrk08_mouchel_mapping.csv har " + D.meta.nStyrk + " rader."],
        card: "", tab: resultM(), dur: 1800, set: { ax: 0, dts: 0, lab0: 0, lab2: 0 },
        win: { ax: [0, 0.4], dts: [0, 0.4], lab0: [0, 0.4], lab2: [0, 0.4] } }
    ];
  }
  var LAST = STEPS.length - 1;
  var T = [];
  STEPS.forEach(function (s, k) { T[k] = Object.assign({}, k ? T[k - 1] : DEF, s.set); });
  var P = Object.assign({}, T[0]);
  var cur = 0, anim = null, raf = 0, reduce = false;
  try { reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e1) { reduce = false; }

  /* ------------------------------------------------------------------ */
  /* the tween engine (same as data-pipeline)                            */
  /* ------------------------------------------------------------------ */
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
    anim = { t0: performance.now(), dur: spec.dur || 1800, from: Object.assign({}, P), to: T[k], win: win, ease: spec.ease || {} };
    draw();
  }
  function applyAnim(a, u) {
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
  function scrub(k, u) {
    anim = null;
    var spec = STEPS[k], win = {};
    Object.keys(T[k]).forEach(function (n) { win[n] = (spec.win && spec.win[n]) || [0, 1]; });
    applyAnim({ from: T[k - 1], to: T[k], win: win, ease: spec.ease || {} }, u);
    render();
  }
  var pr = 1;
  function fit() {
    var sc = (window.Reveal && Reveal.getScale) ? Reveal.getScale() : 1;
    pr = Math.min(2, Math.max(1, (window.devicePixelRatio || 1) * sc));
    canvas.width = Math.round(W * pr);
    canvas.height = Math.round(H * pr);
  }

  /* ------------------------------------------------------------------ */
  /* scene: the task table (Eloundou)                                    */
  /* ------------------------------------------------------------------ */
  var TB = { x0: 64, xType: 548, xChip: 672, xBeta: 812, xW: 896, head: 262, y0: 297, rowH: 22.5 };
  function drawTable() {
    if (!E || P.tbl < 0.01) { return; }
    var tasks = D.tasks;
    ctx.textBaseline = "middle";
    ctx.font = "600 18px " + SANS; ctx.fillStyle = MUTE;
    ctx.globalAlpha = P.tbl; ctx.textAlign = "left";
    ctx.fillText("OPPGAVE", TB.x0, TB.head); ctx.fillText("TYPE", TB.xType, TB.head);
    ctx.globalAlpha = P.tbl * clamp(P.ch * 3, 0, 1); ctx.fillText("GPT-4", TB.xChip, TB.head);
    ctx.textAlign = "right";
    ctx.globalAlpha = P.tbl * clamp(P.bt * 3, 0, 1); ctx.fillText("β", TB.xBeta, TB.head);
    ctx.globalAlpha = P.tbl * P.wt; ctx.fillText("VEKT", TB.xW, TB.head);
    tasks.forEach(function (t, i) {
      var y = TB.y0 + i * TB.rowH;
      ctx.globalAlpha = P.tbl;
      if (i % 2 === 0) { ctx.fillStyle = BAND; ctx.fillRect(TB.x0 - 12, y - TB.rowH / 2, TB.xW - TB.x0 + 36, TB.rowH); }
      ctx.font = "20px " + SANS; ctx.textAlign = "left";
      ctx.fillStyle = INK; ctx.fillText(t.no, TB.x0, y);
      ctx.fillStyle = mix(MUTE, INK, P.wt); ctx.fillText(t.type === "K" ? "Kjerne" : "Tillegg", TB.xType, y);
      var ca = clamp(P.ch * 1.8 - i * 0.045, 0, 1);
      if (ca > 0.01) {
        ctx.globalAlpha = P.tbl * ca;
        ctx.fillStyle = ECOL[t.e][0]; rrect(TB.xChip, y - 10, 52, 20, 5); ctx.fill();
        ctx.fillStyle = ECOL[t.e][1]; ctx.font = "700 17px " + SANS; ctx.textAlign = "center";
        ctx.fillText(t.e, TB.xChip + 26, y + 0.5);
      }
      var ba = clamp(P.bt * 1.8 - i * 0.045, 0, 1);
      if (ba > 0.01) {
        ctx.globalAlpha = P.tbl * ba; ctx.fillStyle = INK; ctx.font = "600 20px " + SANS; ctx.textAlign = "right";
        ctx.fillText(fmt(t.b, t.b === 0.5 ? 1 : 0), lerp(TB.xChip + 52, TB.xBeta, ba), y);
      }
      if (P.wt > 0.01) {
        ctx.globalAlpha = P.tbl * P.wt; ctx.fillStyle = INK; ctx.font = "600 20px " + SANS; ctx.textAlign = "right";
        ctx.fillText("× " + (t.type === "K" ? 2 : 1), TB.xW, y);
      }
    });
    ctx.globalAlpha = 1;
  }

  /* ------------------------------------------------------------------ */
  /* scene: the code chain and the token that carries the score          */
  /* ------------------------------------------------------------------ */
  var CH = { x0: 64, w: 186, gap: 54, y: 336, h: 168 };
  function bx(i) { return CH.x0 + i * (CH.w + CH.gap); }
  var TKY = CH.y - 70;
  var TK = { card: { x: 1030, y: 400 } };               // where the card's number sits; measured from the page
  var tokenText = E ? fmt(D.occ.beta, 3) : fmt(D.occ.a, 3);
  function drawChain() {
    if (P.chA < 0.01) { return; }
    var counts = [D.meta.nOnet, D.meta.nSoc18, D.meta.nSoc10, D.meta.nIsco, D.meta.nStyrk];
    var arrowLab = [["snitt", "per SOC-kode"], ["BLS-kobling", "2018 til 2010"], ["BLS-kobling", "SOC til ISCO"], ["samme kode", "i STYRK-08"]];
    ctx.textBaseline = "alphabetic";
    for (var i = 0; i < 5; i++) {
      var a = clamp(P.chn - i, 0, 1) * P.chA;
      if (a < 0.01) { continue; }
      var x = bx(i), y = CH.y + (1 - a) * 18, c = D.chain[i];
      ctx.globalAlpha = a; card(x, y, CH.w, CH.h);
      ctx.textAlign = "left"; ctx.fillStyle = MUTE; ctx.font = "600 18px " + SANS;
      ctx.fillText(c.k.toUpperCase(), x + 16, y + 30);
      ctx.fillStyle = INK; ctx.font = "600 28px " + SANS; ctx.fillText(c.c, x + 16, y + 68);
      ctx.fillStyle = "#3d4a59"; ctx.font = "20px " + SANS;
      wrap(soft(c.n), CH.w - 32, "20px " + SANS).forEach(function (ln, j) { ctx.fillText(ln, x + 16, y + 98 + j * 24); });
      ctx.fillStyle = MUTE; ctx.font = "18px " + SANS; ctx.fillText(fmt(counts[i]) + " koder", x + 16, y + CH.h - 14);
    }
    for (var j = 0; j < 4; j++) {
      var b = clamp(P.chn - j - 0.5, 0, 1) * P.chA;
      if (b < 0.01) { continue; }
      var x0 = bx(j) + CH.w + 6, x1 = lerp(x0, bx(j + 1) - 8, b), ay = CH.y + CH.h / 2;
      ctx.globalAlpha = b; ctx.strokeStyle = GREY; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(x0, ay); ctx.lineTo(x1, ay); ctx.stroke();
      if (b > 0.9) { ctx.fillStyle = GREY; ctx.beginPath(); ctx.moveTo(x1 + 4, ay); ctx.lineTo(x1 - 8, ay - 7); ctx.lineTo(x1 - 8, ay + 7); ctx.closePath(); ctx.fill(); }
      ctx.fillStyle = MUTE; ctx.font = "600 18px " + SANS; ctx.textAlign = "center";
      ctx.fillText(arrowLab[j][0], bx(j) + CH.w + CH.gap / 2, CH.y - 32);
      ctx.fillText(arrowLab[j][1], bx(j) + CH.w + CH.gap / 2, CH.y - 8);
    }
    ctx.globalAlpha = 1;
  }
  function drawToken() {
    if (P.tka < 0.01) { return; }
    var px = bx(0) + CH.w / 2 + (bx(1) - bx(0)) * P.tp;
    var x = lerp(TK.card.x, px, P.tf), y = lerp(TK.card.y, TKY, P.tf);
    ctx.globalAlpha = P.tka;
    ctx.save(); ctx.shadowColor = "rgba(29,39,51,0.25)"; ctx.shadowBlur = 10; ctx.shadowOffsetY = 3;
    ctx.fillStyle = NAVY; rrect(x - 52, y - 20, 104, 40, 20); ctx.fill(); ctx.restore();
    ctx.fillStyle = "#fff"; ctx.font = "700 24px " + SANS; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(tokenText, x, y + 1);
    ctx.globalAlpha = 1;
  }

  /* ------------------------------------------------------------------ */
  /* scene: several become one, one becomes several (Eloundou)           */
  /* ------------------------------------------------------------------ */
  function line(x0, y0, x1, y1, p) {                    // a curve drawn from its start to progress p
    if (p < 0.01) { return; }
    var steps = 28, mx = (x0 + x1) / 2;
    ctx.beginPath(); ctx.moveTo(x0, y0);
    for (var s = 1; s <= steps * p; s++) {
      var t = s / steps, u = 1 - t;
      ctx.lineTo(u * u * u * x0 + 3 * u * u * t * mx + 3 * u * t * t * mx + t * t * t * x1,
                 u * u * u * y0 + 3 * u * u * t * y0 + 3 * u * t * t * y1 + t * t * t * y1);
    }
    ctx.stroke();
  }
  function srcBox(x, y, w, h, code, name, val, a) {
    ctx.globalAlpha = a; card(x, y + (1 - a) * 12, w, h);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    ctx.fillStyle = INK; ctx.font = "600 24px " + SANS; ctx.fillText(code, x + 16, y + 28 + (1 - a) * 12);
    ctx.fillStyle = "#3d4a59"; ctx.font = "20px " + SANS; ctx.fillText(name, x + 16, y + 54 + (1 - a) * 12);
    ctx.textAlign = "right"; ctx.fillStyle = NAVY; ctx.font = "700 26px " + SANS;
    ctx.fillText(fmt(val, 3), x + w - 16, y + 28 + (1 - a) * 12);
  }
  function drawMergeFan() {
    if (!E || P.mfA < 0.01) { return; }
    var m = D.merge, f = D.fan, A = P.mfA;
    ctx.textBaseline = "alphabetic"; ctx.textAlign = "left";
    ctx.globalAlpha = A; ctx.font = "600 18px " + SANS; ctx.fillStyle = MUTE;
    ctx.fillText("FLERE BLIR ÉN", 64, 268); ctx.fillText("ÉN BLIR FLERE", 64, 462);
    // merge
    var g = P.mg, a1 = clamp(g * 3, 0, 1), a2 = clamp(g * 3 - 1, 0, 1), a3 = clamp(g * 3 - 2, 0, 1);
    var ys = [284, 356];
    m.soc10.forEach(function (s, i) { srcBox(64, ys[i], 380, 64, s.c, s.n, s.b, a1 * A); });
    ctx.strokeStyle = GREY; ctx.lineWidth = 3; ctx.globalAlpha = A;
    ys.forEach(function (y) { line(450, y + 32, 516, 348, a2); });
    if (a2 > 0.5) { ctx.fillStyle = MUTE; ctx.font = "600 18px " + SANS; ctx.textAlign = "center"; ctx.globalAlpha = A * clamp((a2 - 0.5) * 2, 0, 1); ctx.fillText("snitt", 486, 300); }
    if (a3 > 0.01) { srcBox(520, 308, 330, 80, m.styrk.c + " " + m.styrk.n, "snitt av de to", m.styrk.b, a3 * A); }
    // fan-out
    var q = P.fn, b1 = clamp(q * 3, 0, 1), b2 = clamp(q * 3 - 1, 0, 1), b3 = clamp(q * 3 - 2, 0, 1);
    srcBox(64, 480, 380, 70, f.src.c, f.src.n, f.src.b, b1 * A);
    var FY0 = 486, FDY = 28;                            // the seven Norwegian codes as rows: code, short title, score
    f.to.forEach(function (t, i) {
      var ry = FY0 + i * FDY;
      ctx.strokeStyle = GREY; ctx.lineWidth = 2.5; ctx.globalAlpha = A * b2; line(450, 515, 508, ry, b2);
      var a = clamp((b3 - i * 0.1) / 0.4, 0, 1) * A;
      if (a > 0.01) {
        var yy = ry + (1 - a) * 8;
        ctx.globalAlpha = a; ctx.textBaseline = "middle";
        if (i % 2 === 0) { ctx.fillStyle = BAND; ctx.fillRect(514, yy - FDY / 2, 480, FDY); }
        ctx.textAlign = "left"; ctx.fillStyle = INK; ctx.font = "600 22px " + SANS; ctx.fillText(t.c, 526, yy + 1);
        ctx.fillStyle = "#3d4a59"; ctx.font = "20px " + SANS; ctx.fillText(t.s || t.n, 612, yy + 1);
        ctx.textAlign = "right"; ctx.fillStyle = NAVY; ctx.font = "700 20px " + SANS; ctx.fillText(fmt(f.src.b, 3), 982, yy + 1);
      }
    });
    ctx.textBaseline = "alphabetic"; ctx.globalAlpha = 1;
  }

  /* ------------------------------------------------------------------ */
  /* scene: the four Norwegian exceptions (Eloundou)                     */
  /* ------------------------------------------------------------------ */
  function drawExceptions() {
    if (!E || P.exA < 0.01) { return; }
    ctx.textBaseline = "alphabetic"; ctx.textAlign = "left"; ctx.font = "600 18px " + SANS; ctx.fillStyle = MUTE;
    ctx.globalAlpha = P.exA; ctx.fillText("NORSK KODE", 64, 268); ctx.fillText("SKÅREN KOMMER FRA", 520, 268);
    ctx.textAlign = "right"; ctx.fillText("SKÅR", 1200, 268);
    D.exc.forEach(function (r, i) {
      var a = clamp((P.ex - i * 0.15) / 0.55, 0, 1) * P.exA;
      if (a < 0.01) { return; }
      var y = 290 + i * 92 + (1 - a) * 12;
      ctx.globalAlpha = a; card(64, y, 410, 72); card(520, y, 560, 72);
      ctx.textAlign = "left"; ctx.fillStyle = INK; ctx.font = "600 26px " + SANS; ctx.fillText(r.c, 80, y + 44);
      ctx.font = "24px " + SANS; ctx.fillText(r.n, 160, y + 44);
      ctx.fillStyle = "#3d4a59"; ctx.font = "22px " + SANS; ctx.fillText(r.how, 536, y + 44);
      ctx.strokeStyle = GREY; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(512, y + 36); ctx.lineTo(482, y + 36); ctx.stroke();
      ctx.fillStyle = GREY; ctx.beginPath(); ctx.moveTo(478, y + 36); ctx.lineTo(490, y + 29); ctx.lineTo(490, y + 43); ctx.closePath(); ctx.fill();
      ctx.textAlign = "right"; ctx.fillStyle = NAVY; ctx.font = "700 28px " + SANS; ctx.fillText(fmt(r.b, 3), 1200, y + 44);
    });
    ctx.globalAlpha = 1;
  }

  /* ------------------------------------------------------------------ */
  /* scene: the 397 occupations as dots, ranked, grouped, compared       */
  /* ------------------------------------------------------------------ */
  function layoutAlpha(k) { return clamp(1 - 2 * Math.abs(P.dx - k), 0, 1); }
  function drawDotAxes() {
    if (P.ax < 0.01) { return; }
    ctx.globalAlpha = P.ax; ctx.font = "22px " + SANS; ctx.textAlign = "right"; ctx.textBaseline = "middle";
    var step = 0.2, v;
    for (v = 0; v <= yTickMax + 1e-9; v += step) {
      var y = PLOT.b - v / yMax * (PLOT.b - PLOT.t);
      ctx.strokeStyle = GRID; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(PLOT.l, y); ctx.lineTo(PLOT.r + 8, y); ctx.stroke();
      ctx.fillStyle = MUTE; ctx.fillText(fmt(v, 1), PLOT.l - 14, y);
    }
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic"; ctx.font = "600 22px " + SANS; ctx.fillStyle = INK;
    ctx.fillText(E ? "Eloundou-skår (β)" : "Mouchel-skår (A1)", PLOT.l, PLOT.t - 38);
    ctx.strokeStyle = "#c9c6bd"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(PLOT.l, PLOT.t - 4); ctx.lineTo(PLOT.l, PLOT.b); ctx.lineTo(PLOT.r + 8, PLOT.b); ctx.stroke();
    var titles = ["STYRK-08 i kodens rekkefølge", "Yrker rangert etter skår, lavest til høyest", "Eloundou-skår (β)"];
    ctx.textAlign = "center"; ctx.font = "22px " + SANS; ctx.fillStyle = MUTE;
    titles.forEach(function (t, k) {
      var a = layoutAlpha(k) * P.ax;
      if (a < 0.01 || (E && k === 2)) { return; }
      ctx.globalAlpha = a; ctx.fillText(t, (PLOT.l + PLOT.r) / 2, PLOT.b + 54);
    });
    var ta = layoutAlpha(2) * P.ax;
    if (!E && ta > 0.01) {                              // numeric x ticks for the scatter
      ctx.globalAlpha = ta; ctx.textBaseline = "top";
      for (v = 0; v <= 1.0001; v += 0.2) {
        var x = PLOT.l + v * (PLOT.r - PLOT.l);
        ctx.strokeStyle = "#c9c6bd"; ctx.beginPath(); ctx.moveTo(x, PLOT.b); ctx.lineTo(x, PLOT.b + 6); ctx.stroke();
        ctx.fillText(fmt(v, 1), x, PLOT.b + 10);
      }
    }
    ctx.globalAlpha = 1;
  }
  function drawBands() {
    if (P.bnd < 0.01) { return; }
    var cum = 0;
    for (var q = 0; q < 5; q++) {
      var x0 = PLOT.l + cum / N * (PLOT.r - PLOT.l); cum += QCOUNT[q];
      var x1 = PLOT.l + cum / N * (PLOT.r - PLOT.l);
      ctx.globalAlpha = P.bnd * 0.1; ctx.fillStyle = QC[q]; ctx.fillRect(x0, PLOT.t, x1 - x0, PLOT.b - PLOT.t);
      ctx.globalAlpha = P.bnd; ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
      ctx.fillStyle = labelColor(q); ctx.font = "700 24px " + SANS; ctx.fillText("Q" + (q + 1), (x0 + x1) / 2, PLOT.t + 30);
      ctx.fillStyle = MUTE; ctx.font = "20px " + SANS; ctx.fillText(QCOUNT[q] + " yrker", (x0 + x1) / 2, PLOT.t + 56);
    }
    ctx.globalAlpha = 1;
  }
  function dotX(i) {
    var k = Math.min(Math.floor(clamp(P.dx, 0, 2)), 1), f = clamp(P.dx, 0, 2) - k;
    var a = k === 0 ? DX0[i] : DX1[i], b = k === 0 ? DX1[i] : DX2[i];
    return lerp(a, b, f);
  }
  function drawDots() {
    if (P.dts < 0.01) { return; }
    for (var i = 0; i < N; i++) {
      var a = clamp(P.dts * 1.6 - (i / N) * 0.6, 0, 1);
      if (a < 0.01) { continue; }
      ctx.globalAlpha = a * 0.8;
      ctx.fillStyle = mix(GREY, QC[DQ[i]], P.dc);
      ctx.beginPath(); ctx.arc(dotX(i), DY[i], 2.8 + 2 * a, 0, 6.2832); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
  var otherExamples = exampleCodes.filter(function (c) { return c !== EX.c; });
  function drawLabels() {                              // ring and name; names are pushed apart when they would overlap
    var groups = [[[EX.c], P.lab0], [otherExamples, P.lab], [moverCodes, P.lab2]], items = [];
    groups.forEach(function (g) {
      if (g[1] < 0.01) { return; }
      g[0].forEach(function (c) {
        var i = idxOf[c], d = D.dots[i];
        var upLeft = E ? d[rkey] > N * 0.6 : (D.movers.up.indexOf(c) >= 0 || d[rkey] > N * 0.6);
        items.push({ d: d, a: g[1], x: dotX(i), y: DY[i], up: upLeft, ly: upLeft ? DY[i] - 22 : DY[i] + 2 });
      });
    });
    if (!items.length) { return; }
    ctx.textBaseline = "middle";
    var gap = 28;
    items.filter(function (t) { return t.up; }).sort(function (a, b) { return b.ly - a.ly; })
      .forEach(function (t, k, arr) { if (k && arr[k - 1].ly - t.ly < gap) { t.ly = arr[k - 1].ly - gap; } });
    items.filter(function (t) { return !t.up; }).sort(function (a, b) { return a.ly - b.ly; })
      .forEach(function (t, k, arr) { if (k && t.ly - arr[k - 1].ly < gap) { t.ly = arr[k - 1].ly + gap; } });
    items.forEach(function (t) {
      ctx.globalAlpha = t.a;
      ctx.strokeStyle = INK; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.arc(t.x, t.y, 8, 0, 6.2832); ctx.stroke();
      ctx.font = "700 22px " + SANS;
      var toLeft = t.up && t.x - 14 - ctx.measureText(t.d.n).width > PLOT.l + 6;   // otherwise the name would run over the axis
      ctx.textAlign = toLeft ? "right" : "left";
      haloText(t.d.n, toLeft ? t.x - 14 : t.x + 16, t.ly, INK);
    });
    ctx.globalAlpha = 1;
  }

  function render() {
    ctx.setTransform(pr, 0, 0, pr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    drawTable();
    drawChain();
    drawToken();
    drawMergeFan();
    drawExceptions();
    drawBands();
    drawDotAxes();
    drawDots();
    drawLabels();
  }

  /* ------------------------------------------------------------------ */
  /* captions and html layers                                            */
  /* ------------------------------------------------------------------ */
  var sel = function (s) { return root.querySelector(s); };
  var elKick = sel(".pl-kicker"), elTitle = sel(".pl-title"), elSub = sel(".pl-sub"), elHead = sel(".pl-head"),
      elCard = sel(".pl-card"), elTab = sel(".pl-tab"), elNote = sel(".pl-note"), elTag = sel(".pl-tag"),
      elDots = sel(".pl-dots");
  for (var di = 0; di <= LAST; di++) { elDots.appendChild(document.createElement("span")); }
  var swapTimer = 0, layerTimers = [0, 0, 0, 0];
  function esc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function setLayer(el, html, idx, instant) {          // fade out, swap the html, fade in
    if (el.getAttribute("data-cur") === html) { return; }
    el.setAttribute("data-cur", html);
    clearTimeout(layerTimers[idx]);
    function put() { el.innerHTML = html; el.classList.toggle("on", !!html); if (el === elCard) { setTimeout(measureCard, 700); } }
    if (instant || reduce || !el.innerHTML) { put(); }
    else { el.classList.remove("on"); layerTimers[idx] = setTimeout(put, 260); }
  }
  function measureCard() {                              // where the card's result number sits, in slide coordinates
    var cell = elCard.querySelector("tr.sum td.n");
    if (!cell) { return; }
    var r = cell.getBoundingClientRect(), rr = root.getBoundingClientRect(), sc = rr.width / W || 1;
    TK.card.x = (r.left + r.width / 2 - rr.left) / sc - 6; TK.card.y = (r.top + r.height / 2 - rr.top) / sc;
  }
  function updateDom(k, instant) {
    var s = STEPS[k];
    function apply() {
      elKick.textContent = s.head[0]; elTitle.textContent = s.head[1];
      elSub.innerHTML = esc(s.head[2]).replace(/\n/g, "<br>");   // a line break in the text is a line break on the slide
      elHead.classList.remove("out");
    }
    clearTimeout(swapTimer);
    if (instant || reduce) { apply(); } else { elHead.classList.add("out"); swapTimer = setTimeout(apply, 170); }
    setLayer(elCard, s.card || "", 0, instant);
    setLayer(elTab, s.tab || "", 1, instant);
    setLayer(elNote, s.note || "", 2, instant);
    setLayer(elTag, s.tag || "", 3, instant);
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

  return { goTo: goTo, P: P, STEPS: STEPS, T: T, render: render, scrub: scrub };
}

(function () {                                          // one animation per data file that is present
  var made = {};
  [["eloundou", "map-eloundou", window.MAP_ELOUNDOU, "e"], ["mouchel", "map-mouchel", window.MAP_MOUCHEL, "m"]].forEach(function (a) {
    var root = document.getElementById(a[1]);
    if (a[2] && root) { made[a[0]] = createMapping(a[2], root, a[3]); }
  });
  window.__maps = made;
})();
