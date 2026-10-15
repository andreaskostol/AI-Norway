/* KI Studio: artikkelsporingen (Studio). Leser data/studio_papers.json og fyller
   tabellen paa studio.html / en/studio.html. Spraak fra <html lang>.
   Ingen avhengigheter. Lista vedlikeholdes for haand i JSON-fila. */
(function () {
  "use strict";
  var V = "20261014a";                       // samme noekkel som ?v= i HTML
  var LANG = document.documentElement.lang === "en" ? "en" : "nb";
  var T = {
    nb: {
      all: "Alle", forskning: "Forskningsartikler", anthropic: "Anthropic", rapport: "Andre rapporter",
      status: { ny: "Ny", notat: "Notat under arbeid", video: "Video under arbeid", podkast: "Podkast under arbeid", publisert: "Publisert" },
      plan: { notat: "Notat", "notat+video": "Notat og kort video", podkast: "Podkast", ingen: "Ikke bestemt" },
      count: function (n, tot) { return n === tot ? n + " artikler" : n + " av " + tot + " artikler"; },
      nodate: "dato ikke sjekket", empty: "Ingen artikler i dette utvalget ennå.",
      failed: "Fikk ikke lastet lista. Prøv å laste siden på nytt."
    },
    en: {
      all: "All", forskning: "Research papers", anthropic: "Anthropic", rapport: "Other reports",
      status: { ny: "New", notat: "Note in progress", video: "Video in progress", podkast: "Podcast in progress", publisert: "Published" },
      plan: { notat: "Note", "notat+video": "Note and short video", podkast: "Podcast", ingen: "Not decided" },
      count: function (n, tot) { return n === tot ? n + " papers" : n + " of " + tot + " papers"; },
      nodate: "date not checked", empty: "No papers in this selection yet.",
      failed: "Could not load the list. Try reloading the page."
    }
  }[LANG];
  var TYPES = ["all", "forskning", "anthropic", "rapport"];
  var papers = [], current = "all";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // "2026-08" sorteres foran "2026"; begge foran 2025. Manglende dato sist.
  function sortKey(p) { return (p.date || "0000") + (p.date && p.date.length === 4 ? "-00" : ""); }

  function render() {
    var tbody = document.querySelector("#studio-table tbody");
    var rows = papers.filter(function (p) { return current === "all" || p.type === current; });
    rows.sort(function (a, b) { return sortKey(b).localeCompare(sortKey(a)); });
    tbody.innerHTML = rows.map(function (p) {
      var title = p.url
        ? '<a href="' + esc(p.url) + '" target="_blank" rel="noopener">' + esc(p.title) + "</a>"
        : esc(p.title);
      var who = p.authors ? '<span class="paper-authors">' + esc(p.authors) + "</span>" : "";
      var note = (LANG === "en" ? p.note_en : p.note) || "";
      note = note ? '<span class="paper-note">' + esc(note) + "</span>" : "";
      var status = T.status[p.status] || esc(p.status || "");
      var plan = T.plan[p.plan] || T.plan.ingen;
      return "<tr>" +
        '<td class="paper-date">' + (p.date ? esc(p.date) : '<span class="paper-nodate">' + T.nodate + "</span>") + "</td>" +
        '<td class="paper-title">' + title + who + note + "</td>" +
        "<td>" + esc(p.source || "") + "</td>" +
        '<td><span class="status-pill status-' + esc(p.status || "ny") + '">' + status + "</span></td>" +
        "<td>" + plan + "</td></tr>";
    }).join("");
    if (!rows.length) tbody.innerHTML = '<tr><td colspan="5" class="paper-empty">' + T.empty + "</td></tr>";
    document.getElementById("studio-count").textContent = T.count(rows.length, papers.length);
    document.querySelectorAll("#studio-filters button").forEach(function (b) {
      b.classList.toggle("active", b.dataset.type === current);
      b.setAttribute("aria-selected", b.dataset.type === current ? "true" : "false");
    });
  }

  function initFilters() {
    var row = document.getElementById("studio-filters");
    row.innerHTML = TYPES.map(function (t) {
      return '<button type="button" role="tab" data-type="' + t + '">' + T[t] + "</button>";
    }).join("");
    row.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      current = b.dataset.type;
      render();
    });
  }

  fetch("/data/studio_papers.json?v=" + V)
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      papers = d.papers || [];
      initFilters();
      render();
    })
    .catch(function () {
      document.getElementById("studio-count").textContent = T.failed;
    });
})();
