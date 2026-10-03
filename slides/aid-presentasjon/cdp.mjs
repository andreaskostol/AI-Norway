// cdp.mjs: drive a headless Chrome through the DevTools protocol, without npm packages.
// Used by make_pdf.mjs (print-PDF) and snap.mjs (screenshots for checking the slides).
// Node 22 or newer (built-in WebSocket and fetch).

import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME_PATHS = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function launch({ port = 9333, width = 1280, height = 720 } = {}) {
  const { existsSync } = await import("node:fs");
  const exe = CHROME_PATHS.find((p) => existsSync(p));
  if (!exe) throw new Error("Fant ikke Chrome eller Edge");
  const profile = mkdtempSync(join(tmpdir(), "aid-cdp-"));
  const proc = spawn(exe, [
    "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
    "--no-default-browser-check", "--disable-extensions",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    `--window-size=${width},${height}`, "about:blank",
  ], { stdio: "ignore" });
  let ver;
  for (let i = 0; i < 100; i++) {
    try { ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break; }
    catch { await sleep(100); }
  }
  if (!ver) { proc.kill(); throw new Error("Chrome svarte ikke på DevTools-porten"); }
  const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = list.find((t) => t.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0;
  const pending = new Map();
  const listeners = [];
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { res, rej } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) rej(new Error(JSON.stringify(msg.error))); else res(msg.result);
    } else if (msg.method) {
      listeners.forEach((f) => f(msg));
    }
  };
  const send = (method, params = {}) => new Promise((res, rej) => {
    const mid = ++id;
    pending.set(mid, { res, rej });
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  const evaluate = async (expression) => {
    const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + " " + (r.exceptionDetails.exception?.description || ""));
    return r.result.value;
  };
  const consoleErrors = [];
  listeners.push((m) => {
    if (m.method === "Runtime.exceptionThrown") consoleErrors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
    if (m.method === "Runtime.consoleAPICalled" && (m.params.type === "error" || m.params.type === "warning")) {
      consoleErrors.push(m.params.type + ": " + m.params.args.map((a) => a.value ?? a.description).join(" "));
    }
  });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  const goto = async (url) => {
    const loaded = new Promise((res) => {
      const f = (m) => { if (m.method === "Page.loadEventFired") { listeners.splice(listeners.indexOf(f), 1); res(); } };
      listeners.push(f);
    });
    await send("Page.navigate", { url });
    await loaded;
  };
  const waitFor = async (expr, timeout = 30000) => {
    const t0 = Date.now();
    while (Date.now() - t0 < timeout) {
      if (await evaluate(expr)) return true;
      await sleep(150);
    }
    throw new Error("Tidsavbrudd: " + expr);
  };
  const close = async () => { try { ws.close(); } catch {} proc.kill(); };
  return { send, evaluate, goto, waitFor, close, sleep, consoleErrors };
}
