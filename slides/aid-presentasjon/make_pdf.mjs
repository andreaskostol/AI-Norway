// make_pdf.mjs: print the deck to PDF the way reveal.js documents it (?print-pdf), in headless Chrome.
// Waits for reveal.js to finish the print layout (one .pdf-page per slide) and for the animations
// to draw their last step, then prints with the page size from the deck's CSS (1280 x 720 px).
//
// Usage: node make_pdf.mjs dist/aid-2026-10-06.html dist/aid-2026-10-06.pdf

import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { launch } from "./cdp.mjs";

const [, , input, output] = process.argv;
if (!input || !output) { console.error("Bruk: node make_pdf.mjs <html> <pdf>"); process.exit(1); }

const url = pathToFileURL(resolve(input)).href + "?print-pdf";
const c = await launch({ port: 9334 });
try {
  await c.goto(url);
  await c.waitFor("document.querySelectorAll('.pdf-page').length > 0", 60000);
  await c.sleep(2500);                                   // the animations draw on the next frames
  const info = await c.evaluate(`({
    pages: document.querySelectorAll('.pdf-page').length,
    slides: document.querySelectorAll('.reveal .slides section').length,
    animations: [...Object.values(window.__pls || {}), ...Object.values(window.__maps || {})].length
  })`);
  const pdf = await c.send("Page.printToPDF", {
    printBackground: true, preferCSSPageSize: true,
    marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0,
  });
  writeFileSync(output, Buffer.from(pdf.data, "base64"));
  console.log(`PDF: ${output}. Sider: ${info.pages}. Animasjoner: ${info.animations}.`);
  if (c.consoleErrors.length) { console.log("Feil i konsollen:\n  " + c.consoleErrors.join("\n  ")); process.exitCode = 2; }
} finally {
  await c.close();
}
