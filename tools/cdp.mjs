// Headless Chrome helper (DevTools protocol, no npm deps).
//   node cdp.mjs shot <url> <out.png> [w] [h] [waitMs] [js-before-shot]
//   node cdp.mjs video <url> <out.mp4> [w] [h] [fps] [crf]
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const [mode, url, out, W = "1600", H = "900", a5, a6] = process.argv.slice(2);
const w = +W, h = +H;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const port = 9300 + Math.floor(Math.random() * 500);
const prof = mkdtempSync(join(tmpdir(), "cdp-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${prof}`,
  `--window-size=${w},${h}`, "--hide-scrollbars", "--enable-gpu", "--ignore-gpu-blocklist", "--use-angle=metal",
  "--enable-unsafe-swiftshader", "--force-device-scale-factor=1", "about:blank"], { stdio: "ignore" });

let ws, id = 0;
const pending = new Map(), events = [];
async function connect() {
  for (let i = 0; i < 60; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) { ws = new WebSocket(page.webSocketDebuggerUrl); break; }
    } catch (e) {}
    await sleep(250);
  }
  await new Promise((r) => (ws.onopen = r));
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
    else if (d.method) events.push(d);
  };
}
const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async (expr) => {
  const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 500));
  return r.result?.result?.value;
};

await connect();
await send("Runtime.enable"); await send("Page.enable"); await send("Log.enable");
const MOB = !!process.env.MOBILE;
await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: MOB ? 2 : 1, mobile: MOB });
if (MOB) await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
await send("Page.navigate", { url });

const logs = () => events.filter((e) => e.method === "Runtime.consoleAPICalled" || e.method === "Runtime.exceptionThrown" || e.method === "Log.entryAdded")
  .map((e) => JSON.stringify(e.params).slice(0, 300));

try {
  if (mode === "shot") {
    await sleep(+(a5 || 4000));
    if (a6) console.log("js:", await evaluate(a6));
    await sleep(600);
    const r = await send("Page.captureScreenshot", { format: "png" });
    writeFileSync(out, Buffer.from(r.result.data, "base64"));
    console.log("saved", out);
  } else if (mode === "video") {
    for (let i = 0; i < 240 && !(await evaluate("!!window.__ready")); i++) await sleep(250);
    const info = await evaluate("({frames: __video.frames, fps: __video.fps})");
    const fps = info.fps, frames = +(process.env.FRAMES || info.frames), crf = a6 || "16";
    console.log("rendering", frames, "frames @", fps, "fps", w + "x" + h);
    const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "mjpeg", "-i", "-",
      "-vf", "scale=in_range=full:out_range=tv,format=yuv420p", "-color_range", "tv", "-colorspace", "bt709", "-c:v", "libx264", "-preset", "slow", "-crf", crf, "-profile:v", "high", "-movflags", "+faststart",
      "-tag:v", "avc1", out], { stdio: ["pipe", "inherit", "inherit"] });
    const t0 = Date.now();
    for (let f = 0; f < frames; f++) {
      await evaluate(`__video.frame(${f})`);
      const r = await send("Page.captureScreenshot", { format: "jpeg", quality: 95, optimizeForSpeed: false });
      const buf = Buffer.from(r.result.data, "base64");
      if (!ff.stdin.write(buf)) await new Promise((res) => ff.stdin.once("drain", res));
      if (f % 60 === 0) console.log(`frame ${f}/${frames}  ${((Date.now() - t0) / 1000).toFixed(0)} s`);
    }
    ff.stdin.end();
    await new Promise((r) => ff.on("close", r));
    console.log("video done in", ((Date.now() - t0) / 1000).toFixed(0), "s ->", out);
  }
} catch (e) {
  console.error("ERROR", e.message);
}
const L = logs(); if (L.length) console.log("console:\n" + L.slice(-15).join("\n"));
ws.close(); chrome.kill();
process.exit(0);
