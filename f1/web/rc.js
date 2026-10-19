// SC-02 – RC transmitter as a USB joystick (RadioMaster Pocket / EdgeTX "USB Joystick (HID)").
// Every radio maps its channels to other HID axes, so the axes are learned once (sticks centred, steer right, full gas,
// boost switch on) and kept in localStorage. Without a learned mapping an Xbox-style pad works as before (app.js).
const KEY = "sc02.rc";
export const LIMITS = [20, 40, 60, 80, 100, 0];                   // km/h, 0 = no limit (last wheel position)
// boost = switch SA, sent as channel 5 (AUX1). EdgeTX "USB Joystick" puts CH1..CH8 on axes 0..7, so CH5 = axis 4:
// SA up = -100 % (off), SA down = +100 % (boost). Same channel goes over ExpressLRS to the real car (CRSF ch 5).
const SA_BOOST = { type: "axis", idx: 4, off: 0, sign: 1 };      // only when SA is fully down (> +50 %)
const SB_REVERSE = { type: "axis", idx: 5, off: 0, sign: 1 };    // reverse gear: CH6 = SB fully down (POCKET model)
// one learned mapping per device: the Pocket over USB and over Bluetooth (ELRS 'BLE Joystick') are different devices
let maps = {};
try { const v = JSON.parse(localStorage.getItem(KEY) || "null"); maps = v && v.id ? { [v.id]: v } : (v || {}); } catch { }
const pads = () => (navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : []);
let map = null;                                     // mapping of the pad in use right now

// ---- bridge (pocket_bridge.py on :8091): reads the Pocket over USB or Bluetooth itself, channels already in CH1..CH8
// order. Works without the browser Gamepad API and without learning: CH1 steer, CH3 gas, CH5 boost, CH6 reverse, CH7 limit.
const br = { name: null, ch: null, btn: 0, t: 0, rest: null };
(function connectBridge() {
  try {
    const es = new EventSource("http://localhost:8091/");
    es.onmessage = (e) => { const d = JSON.parse(e.data);
      if (!d.name) { br.name = null; br.rest = null; return; }
      if (!br.rest) br.rest = [...d.ch];                      // switches as they are when the radio connects = 'off'
      Object.assign(br, { name: d.name, ch: d.ch, btn: d.btn, t: performance.now() }); };
    es.onerror = () => { es.close(); br.name = null; setTimeout(connectBridge, 3000); };
  } catch { setTimeout(connectBridge, 3000); }
})();
const bridgeLive = () => br.name && performance.now() - br.t < 600;
function bridgePad() {
  return { id: br.name + " (brug)", axes: br.ch, timestamp: br.t,
    buttons: Array.from({ length: 16 }, (_, i) => ({ pressed: !!(br.btn & (1 << i)), value: (br.btn >> i) & 1 })) };
}

export const rc = {
  get map() { return map; },
  pad() {                                           // the bridge first; else a learned pad (latest input wins), else the busiest
    if (bridgeLive()) { map = maps[bridgePad().id] || null; return bridgePad(); }
    const ps = pads(), known = ps.filter((p) => maps[p.id]).sort((a, b) => b.timestamp - a.timestamp);
    const p = known[0] || ps.sort((a, b) => b.timestamp - a.timestamp)[0] || null;
    map = p ? maps[p.id] || null : null;
    return p;
  },
  // {steer -1..1 (right = -1), thr -1..1 (stick centre = 0, back = brake), boost, rev} or null without a learned radio
  read() {
    if (bridgeLive() && !maps[bridgePad().id]) {      // bridge with the fixed POCKET channel layout
      const c = br.ch, r = br.rest, dz = (v, d) => (Math.abs(v) < d ? 0 : (v - Math.sign(v) * d) / (1 - d));
      const flip = (k) => Math.abs(c[k] - r[k]) > 1;      // switch moved to the other end
      const li = Math.min(LIMITS.length - 1, Math.max(0, Math.floor((c[6] + 1) / 2 * LIMITS.length)));
      return { steer: -dz(c[0], 0.03), thr: dz(c[2], 0.06), boost: flip(4) || !!(br.btn & 1), rev: flip(5), limit: LIMITS[li] };
    }
    const p = this.pad();
    if (!map || !p || p.id !== map.id) return null;
    const ax = (m) => Math.max(-1, Math.min(1, ((p.axes[m.axis] ?? 0) - m.center) * m.scale));
    const dz = (v, d) => (Math.abs(v) < d ? 0 : (v - Math.sign(v) * d) / (1 - d));
    const sw = (b) => b.type === "button" ? !!p.buttons[b.idx]?.pressed : ((p.axes[b.idx] ?? 0) - b.off) * b.sign > 0.5;
    // throttle: the HID axis is symmetric, so its centre (0) is neutral for a spring stick AND for the
    // non-centring throttle stick: forward = gas, back = brake (full back = full brake, never reverse by itself)
    const t = Math.max(-1, Math.min(1, (p.axes[map.thr.axis] ?? 0) * Math.sign(map.thr.scale)));
    // the Pocket sends its momentary SA button as HID button 0 (green dot), so that always counts as boost too
    const boost = sw(map.boost || SA_BOOST) || !!p.buttons[0]?.pressed;
    // speed limit: scroll wheel P1 on CH7 (axis 6), same 6 steps as the Lua screen on the Pocket (sc02.lua)
    const lm = map.limit || { axis: 6, sign: 1 }, a7 = p.axes[lm.axis] === undefined ? undefined : p.axes[lm.axis] * (lm.sign < 0 ? -1 : 1), li = a7 === undefined ? LIMITS.length - 1 : Math.min(LIMITS.length - 1, Math.max(0, Math.floor((a7 + 1) / 2 * LIMITS.length)));
    return { steer: -dz(ax(map.steer), 0.03), thr: dz(t, 0.06), boost, rev: sw(map.rev || SB_REVERSE), limit: LIMITS[li] };
  },
  save(m) { maps[m.id] = m; map = m; try { localStorage.setItem(KEY, JSON.stringify(maps)); } catch { } },
  forget() { const p = this.pad(); if (p) delete maps[p.id]; map = null; try { localStorage.setItem(KEY, JSON.stringify(maps)); } catch { } },
  isLearned(id) { return !!maps[id]; },
};

// ------------------------------------------------------------------ learn panel
const STEPS = [
  ["Linkerstick in het MIDDEN, rechterstick los, achterste knop los, knop vooraan UIT (niet ingedrukt).", "center"],
  ["STUREN: duw de RECHTERstick volledig naar rechts en houd vast.", "steer"],
  ["Geef VOL GAS: de GAS-stick (links) helemaal naar voren en houd vast.", "thr"],
  ["HOUD de achterste knop (SA, boost) ingedrukt en klik 'volgende'. ('overslaan' = kanaal 5)", "boost"],
  ["Druk de knop vooraan (SE, achteruit) diep in zodat hij blijft zitten, klik 'volgende'. ('overslaan' = kanaal 6)", "rev"],
  ["Draai het SCROLWIEL (snelheidslimiet) helemaal naar één kant, klik 'volgende'. ('overslaan' = kanaal 7)", "limit"],
];

export function bindRcPanel($) {
  const panel = $("rcpanel"), live = $("rclive"), msg = $("rcmsg"), stat = $("rcstat");
  let step = -1, rest = null, m = null, raf = 0;
  function drawLive() {
    const p = rc.pad();
    const all = pads();
    stat.textContent = p ? `${p.id.replace(/\(.*?\)/g, "").trim()}${all.length > 1 ? `  (+${all.length - 1} andere)` : ""}` : "geen controller: Pocket via USB ('USB Joystick (HID)') of Bluetooth ('BLE Joystick'), beweeg een stick";
    const st = rc.read();
    live.innerHTML = (st ? `<div class="st">boost: <b class="${st.boost ? "on" : ""}">${st.boost ? "AAN" : "uit"}</b> · achteruit: <b class="${st.rev ? "on" : ""}">${st.rev ? "AAN" : "uit"}</b> · gas ${Math.round(st.thr * 100)} %</div>` : "") + (p ? p.axes.map((a, i) => `<div class="ax"><span>${i}</span><b><i style="left:${(a + 1) * 50}%"></i></b></div>`).join("") +
      `<div class="bt">${p.buttons.map((b, i) => `<i class="${b.pressed ? "on" : ""}" title="${i}"></i>`).join("")}</div>` : "");
    if (!panel.classList.contains("hidden")) raf = requestAnimationFrame(drawLive);
  }
  function show(i) {
    step = i;
    msg.textContent = i < 0 ? (rc.map ? "Controller ingeleerd ✓ – je kan rijden." : "Klik 'inleren' om je zender te koppelen.") : `${i + 1}/${STEPS.length}  ${STEPS[i][0]}`;
    $("rcgo").textContent = i < 0 ? "inleren" : "volgende";
    $("rcskip").style.display = i >= 3 ? "" : "none";
  }
  function biggest(p, base) {                       // axis that moved most from the rest position
    let best = -1, bd = 0;
    p.axes.forEach((a, k) => { const d = Math.abs(a - base[k]); if (d > bd) { bd = d; best = k; } });
    return [best, bd];
  }
  function next(skip = false) {
    const p = rc.pad();
    if (!p) { msg.textContent = "Geen controller gevonden. Pocket via USB, kies 'USB Joystick (HID)', beweeg een stick."; return; }
    if (step < 0) { m = { id: p.id }; show(0); return; }
    const kind = STEPS[step][1];
    if (kind === "center") { rest = [...p.axes]; m.restButtons = p.buttons.map((b) => b.pressed); }
    else if (kind === "steer" || kind === "thr") {
      const [k, d] = biggest(p, rest);
      if (d < 0.3) { msg.textContent = "Ik zie geen stick bewegen – houd hem volledig uit en klik opnieuw."; return; }
      m[kind] = { axis: k, center: rest[k], scale: 1 / (p.axes[k] - rest[k]) };   // sign included in scale
    } else if (kind === "boost" || kind === "rev") {
      if (skip) {
        const k = kind === "boost" ? 4 : 5, r0 = rest[k] ?? -1, sg = r0 > 0 ? -1 : 1;
        m[kind] = { type: "axis", idx: k, off: r0 + sg * 0.5, sign: sg };
      } else {
        const bi = p.buttons.findIndex((b, i) => b.pressed !== m.restButtons[i]);
        const used = [m.steer.axis, m.thr.axis, m.boost?.type === "axis" ? m.boost.idx : -1];
        let k = -1, d = 0;
        p.axes.forEach((a, j) => { const dd = Math.abs(a - rest[j]); if (!used.includes(j) && dd > d) { d = dd; k = j; } });
        if (bi >= 0) m[kind] = { type: "button", idx: bi };
        else if (d > 0.5) m[kind] = { type: "axis", idx: k, off: (rest[k] + p.axes[k]) / 2 - Math.sign(p.axes[k] - rest[k]) * 0.5, sign: Math.sign(p.axes[k] - rest[k]) };
        else { msg.textContent = "Geen schakelaar gezien – zet hem om (of klik 'overslaan')."; return; }
        if (kind === "boost") rest = [...p.axes];                // the boost switch stays on: new rest for the next step
      }
      if (kind === "rev") rest = [...p.axes];
    } else if (kind === "limit") {
      if (!skip) {
        const used = [m.steer.axis, m.thr.axis, m.boost?.type === "axis" ? m.boost.idx : -1, m.rev?.type === "axis" ? m.rev.idx : -1];
        let k = -1, d = 0;
        p.axes.forEach((a, j) => { const dd = Math.abs(a - rest[j]); if (!used.includes(j) && dd > d) { d = dd; k = j; } });
        if (d < 0.3) { msg.textContent = "Ik zie het wiel niet bewegen – draai verder (of klik 'overslaan')."; return; }
        m.limit = { axis: k, sign: Math.sign(p.axes[k] - rest[k]) };
      }
      delete m.restButtons; rc.save(m); show(-1); return;
    }
    show(step + 1);
  }
  $("brc").onclick = () => { panel.classList.toggle("hidden"); if (!panel.classList.contains("hidden")) { show(-1); cancelAnimationFrame(raf); drawLive(); } };
  $("rcgo").onclick = () => next();
  $("rcskip").onclick = () => next(true);
  $("rcforget").onclick = () => { rc.forget(); show(-1); };
  $("rcclose").onclick = () => panel.classList.add("hidden");
  const dot = () => $("brc").classList.toggle("live", pads().length > 0);
  addEventListener("gamepadconnected", dot); addEventListener("gamepaddisconnected", dot);
  setInterval(dot, 1500);
}
