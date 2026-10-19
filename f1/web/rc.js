// SC-02 – RC transmitter as a USB joystick (RadioMaster Pocket / EdgeTX "USB Joystick (HID)").
// Every radio maps its channels to other HID axes, so the axes are learned once (sticks centred, steer right, full gas,
// boost switch on) and kept in localStorage. Without a learned mapping an Xbox-style pad works as before (app.js).
const KEY = "sc02.rc";
let map = null;
try { map = JSON.parse(localStorage.getItem(KEY) || "null"); } catch { }

export const rc = {
  get map() { return map; },
  pad() {                                           // the learned radio if present, else the first pad
    const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
    return (map && pads.find((p) => p.id === map.id)) || pads[0] || null;
  },
  // {steer -1..1 (right = -1), thr -1..1, boost bool} or null when no learned radio is connected
  read() {
    const p = this.pad();
    if (!map || !p || p.id !== map.id) return null;
    const ax = (m) => Math.max(-1, Math.min(1, ((p.axes[m.axis] ?? 0) - m.center) * m.scale));
    const dz = (v, d) => (Math.abs(v) < d ? 0 : (v - Math.sign(v) * d) / (1 - d));
    const b = map.boost;
    const boost = !b ? false : b.type === "button" ? !!p.buttons[b.idx]?.pressed : ((p.axes[b.idx] ?? 0) - b.off) * b.sign > 0.5;
    return { steer: -dz(ax(map.steer), 0.03), thr: dz(ax(map.thr), 0.05), boost };
  },
  save(m) { map = m; try { localStorage.setItem(KEY, JSON.stringify(m)); } catch { } },
  forget() { map = null; try { localStorage.removeItem(KEY); } catch { } },
};

// ------------------------------------------------------------------ learn panel
const STEPS = [
  ["Laat alle sticks los (in het midden) en zet de boost-schakelaar UIT.", "center"],
  ["Stuur volledig naar RECHTS en houd vast.", "steer"],
  ["Geef VOL GAS (stick naar boven) en houd vast.", "thr"],
  ["Zet de boost-schakelaar AAN (bv. SA of SB). Geen boost? Klik 'overslaan'.", "boost"],
];

export function bindRcPanel($) {
  const panel = $("rcpanel"), live = $("rclive"), msg = $("rcmsg"), stat = $("rcstat");
  let step = -1, rest = null, m = null, raf = 0;
  const pads = () => (navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : []);
  function drawLive() {
    const p = rc.pad();
    stat.textContent = p ? p.id.replace(/\(.*?\)/g, "").trim() : "geen controller: zet de Pocket op USB → 'USB Joystick (HID)' en beweeg een stick";
    live.innerHTML = p ? p.axes.map((a, i) => `<div class="ax"><span>${i}</span><b><i style="left:${(a + 1) * 50}%"></i></b></div>`).join("") +
      `<div class="bt">${p.buttons.map((b, i) => `<i class="${b.pressed ? "on" : ""}" title="${i}"></i>`).join("")}</div>` : "";
    if (!panel.classList.contains("hidden")) raf = requestAnimationFrame(drawLive);
  }
  function show(i) {
    step = i;
    msg.textContent = i < 0 ? (rc.map ? "Controller ingeleerd ✓ – je kan rijden." : "Klik 'inleren' om je zender te koppelen.") : `${i + 1}/4  ${STEPS[i][0]}`;
    $("rcgo").textContent = i < 0 ? "inleren" : "volgende";
    $("rcskip").style.display = i === 3 ? "" : "none";
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
    } else if (kind === "boost") {
      if (!skip) {
        const bi = p.buttons.findIndex((b, i) => b.pressed !== m.restButtons[i]);
        const [k, d] = biggest(p, rest);
        if (bi >= 0) m.boost = { type: "button", idx: bi };
        else if (d > 0.5 && k !== m.steer.axis && k !== m.thr.axis) m.boost = { type: "axis", idx: k, off: rest[k], sign: Math.sign(p.axes[k] - rest[k]) };
        else { msg.textContent = "Geen schakelaar gezien – zet hem om (of klik 'overslaan')."; return; }
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
