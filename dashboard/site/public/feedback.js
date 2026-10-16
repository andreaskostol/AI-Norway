/* Tilbakemeldingsknapp for kiindeksen.no, etter samme oppskrift som paa
   andreaskostol.no (site/www/feedback/feedback.js der). Legg til
   <script src="/feedback.js?v=..." defer></script> paa en side. Knappen nederst
   til hoeyre aapner en dialog; meldingen sendes som JSON {message, contact, page}
   til MCP-serveren (POST /feedback), som lagrer den paa et Fly-volum. Andreas
   leser dem med dashboard/mcp/feedback.py. IP-adresse og nettleser lagres ikke.
   Spraak foelger <html lang>. */
(function () {
  "use strict";
  var EN = (document.documentElement.lang || "nb").toLowerCase().indexOf("en") === 0;
  var URL = "https://kiindeksen-mcp.fly.dev/feedback";
  var T = EN ? {
    button: "Feedback", title: "Feedback",
    intro: "Errors, unclear explanations, ideas or things that worked well. Andreas Kostøl and Øystein Hernæs read everything. Your address and browser are not stored.",
    message: "Message", contact: "Email (optional, if you want an answer)", leave: "Leave empty",
    close: "Close", send: "Send", first: "Write a message first.", sending: "Sending ...",
    thanks: "Thank you.", fail: "Could not send. Please email andreas.r.kostol@bi.no."
  } : {
    button: "Tilbakemelding", title: "Tilbakemelding",
    intro: "Feil, uklare forklaringer, ideer eller noe som fungerte godt. Andreas Kostøl og Øystein Hernæs leser alt. Adressen og nettleseren din lagres ikke.",
    message: "Melding", contact: "E-post (valgfritt, hvis du vil ha svar)", leave: "La stå tom",
    close: "Lukk", send: "Send", first: "Skriv en melding først.", sending: "Sender ...",
    thanks: "Takk.", fail: "Kunne ikke sende. Send gjerne e-post til andreas.r.kostol@bi.no."
  };

  var css = "" +
    ".fb-button { position: fixed; right: 1.2rem; bottom: 1.2rem; z-index: 50; background: var(--accent, #0f4c81); color: #fff;" +
    " border: 0; border-radius: 999px; padding: 0.6rem 1.1rem; font: 600 0.9rem inherit; font-family: inherit; cursor: pointer;" +
    " box-shadow: 0 4px 16px rgba(0,0,0,0.15); }" +
    ".fb-button:hover { background: #0c3d68; }" +
    ".fb-dialog { position: fixed; inset: 0; margin: auto; height: fit-content; max-height: calc(100vh - 2rem); overflow: auto;" +
    " border: 0; border-radius: 12px; padding: 1.4rem; width: min(30rem, calc(100vw - 2rem)); box-shadow: 0 12px 40px rgba(0,0,0,0.2);" +
    " font-family: inherit; color: var(--ink, #1d2733); }" +
    ".fb-dialog::backdrop { background: rgba(29,39,51,0.35); }" +
    ".fb-dialog h2 { font-size: 1.15rem; margin: 0 0 0.4rem; }" +
    ".fb-dialog p { font-size: 0.9rem; color: var(--ink-soft, #4a5868); margin: 0 0 0.8rem; }" +
    ".fb-dialog label { display: block; font-size: 0.85rem; font-weight: 600; margin: 0.7rem 0 0.3rem; }" +
    ".fb-dialog textarea, .fb-dialog input { width: 100%; box-sizing: border-box; font: 0.95rem inherit; font-family: inherit;" +
    " border: 1px solid var(--line, #e4e4e4); border-radius: 8px; padding: 0.55rem; }" +
    ".fb-dialog textarea { min-height: 8rem; resize: vertical; }" +
    ".fb-hp { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }" +
    ".fb-actions { display: flex; gap: 0.6rem; justify-content: flex-end; margin-top: 1rem; }" +
    ".fb-actions button { border-radius: 999px; padding: 0.5rem 1rem; font: 600 0.9rem inherit; font-family: inherit; cursor: pointer;" +
    " border: 0; background: var(--accent-soft, #e8f0f7); color: var(--accent, #0f4c81); }" +
    ".fb-actions button[type=submit] { background: var(--accent, #0f4c81); color: #fff; }" +
    ".fb-status { min-height: 1.2rem; font-size: 0.9rem; margin-top: 0.6rem; }";
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  var button = document.createElement("button");
  button.type = "button";
  button.className = "fb-button";
  button.textContent = T.button;

  var dialog = document.createElement("dialog");
  dialog.className = "fb-dialog";
  dialog.setAttribute("aria-labelledby", "fb-title");
  dialog.innerHTML =
    '<form method="dialog" novalidate>' +
    '<h2 id="fb-title">' + T.title + "</h2>" +
    "<p>" + T.intro + "</p>" +
    '<label for="fb-message">' + T.message + "</label>" +
    '<textarea id="fb-message" name="message" maxlength="5000" required></textarea>' +
    '<label for="fb-contact">' + T.contact + "</label>" +
    '<input id="fb-contact" name="contact" type="email" maxlength="200" autocomplete="email">' +
    '<div class="fb-hp" aria-hidden="true"><label for="fb-website">' + T.leave + '</label><input id="fb-website" name="website" tabindex="-1" autocomplete="off"></div>' +
    '<p class="fb-status" role="status" aria-live="polite"></p>' +
    '<div class="fb-actions"><button type="button" value="cancel">' + T.close + '</button><button type="submit">' + T.send + "</button></div>" +
    "</form>";

  var form = dialog.querySelector("form");
  var status = dialog.querySelector(".fb-status");
  var send = form.querySelector("button[type=submit]");
  dialog.querySelector("button[value=cancel]").addEventListener("click", function () { dialog.close(); });
  button.addEventListener("click", function () { status.textContent = ""; dialog.showModal(); form.message.focus(); });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var message = form.message.value.trim();
    if (message.length < 3) { status.textContent = T.first; return; }
    send.disabled = true;
    status.textContent = T.sending;
    fetch(URL, { method: "POST", headers: { "Content-Type": "application/json" },
                 body: JSON.stringify({ message: message, contact: form.contact.value.trim(), website: form.website.value,
                                        page: location.pathname, lang: EN ? "en" : "no" }) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (out) { return { r: r, out: out }; }); })
      .then(function (x) {
        status.textContent = x.out.message || (x.r.ok ? T.thanks : T.fail);
        if (x.r.ok && x.out.ok) { form.reset(); setTimeout(function () { dialog.close(); }, 1800); }
      })
      .catch(function () { status.textContent = T.fail; })
      .then(function () { send.disabled = false; });
  });

  document.body.appendChild(button);
  document.body.appendChild(dialog);
})();
