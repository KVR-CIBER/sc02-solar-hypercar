// SC-02 – live sound, synthesised with WebAudio from the physics state (no sound files):
// two brushed 130 motors (whine follows the motor speed, louder with current), 10:35 spur gear whine,
// tyre squeal from slip, wind from speed, and a boost layer + whoosh.
export function createAudio() {
  let ctx = null, on = false, muted = false, nodes = null, lastBoost = false;
  try { muted = localStorage.getItem("sc02.mute") === "1"; } catch { }

  function noiseBuffer(c) {
    const b = c.createBuffer(1, c.sampleRate * 2, c.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    return b;
  }
  function build() {
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    const master = ctx.createGain(); master.gain.value = muted ? 0 : 0.55;
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -16; comp.ratio.value = 4;
    master.connect(comp).connect(ctx.destination);
    const osc = (type, f) => { const o = ctx.createOscillator(); o.type = type; o.frequency.value = f; o.start(); return o; };
    const gain = (v = 0) => { const g = ctx.createGain(); g.gain.value = v; return g; };
    const nb = noiseBuffer(ctx);
    const noise = () => { const s = ctx.createBufferSource(); s.buffer = nb; s.loop = true; s.start(); return s; };
    // motor: saw + square an octave up through a low-pass (brushed motor buzz)
    const m1 = osc("sawtooth", 80), m2 = osc("square", 160), mlp = ctx.createBiquadFilter(), mg = gain();
    mlp.type = "lowpass"; mlp.frequency.value = 1800; mlp.Q.value = 3;
    const m2g = gain(0.35); m1.connect(mlp); m2.connect(m2g).connect(mlp); mlp.connect(mg).connect(master);
    // spur gear whine (pinion 10 teeth)
    const gw = osc("sine", 800), gg = gain(); gw.connect(gg).connect(master);
    // tyre squeal: band-passed noise
    const sq = noise(), sbp = ctx.createBiquadFilter(), sg = gain(); sbp.type = "bandpass"; sbp.frequency.value = 2100; sbp.Q.value = 9;
    sq.connect(sbp).connect(sg).connect(master);
    // wind / road
    const wn = noise(), wlp = ctx.createBiquadFilter(), wg = gain(); wlp.type = "lowpass"; wlp.frequency.value = 420;
    wn.connect(wlp).connect(wg).connect(master);
    // boost: detuned saw a fifth up + whoosh
    const b1 = osc("sawtooth", 120), bg = gain(), blp = ctx.createBiquadFilter(); blp.type = "lowpass"; blp.frequency.value = 2600;
    b1.connect(blp).connect(bg).connect(master);
    const wh = noise(), whf = ctx.createBiquadFilter(), whg = gain(); whf.type = "bandpass"; whf.frequency.value = 900; whf.Q.value = 0.8;
    wh.connect(whf).connect(whg).connect(master);
    nodes = { master, m1, m2, mlp, mg, gw, gg, sbp, sg, wg, wlp, b1, bg, whf, whg };
  }
  const set = (p, v, t = 0.04) => p.setTargetAtTime(v, ctx.currentTime, t);
  return {
    get muted() { return muted; },
    start() {                                        // must run inside a user gesture (browser autoplay rules)
      if (!ctx) build();
      if (ctx.state === "suspended") ctx.resume();
      on = true;
    },
    setMuted(v) {
      muted = v; try { localStorage.setItem("sc02.mute", v ? "1" : "0"); } catch { }
      if (ctx) set(nodes.master.gain, v ? 0 : 0.55, 0.05);
    },
    update(s, c, boost) {
      if (!on || !ctx || muted) return;
      const n = nodes, rps = Math.abs(s.w) / (2 * Math.PI);          // motor revolutions per second
      const load = Math.min(1, Math.abs(s.I) / 18), v = Math.abs(s.vx);
      const fm = 55 + rps * 0.9;                                       // audible motor buzz (commutator ~ 3x rps, scaled down)
      set(n.m1.frequency, fm); set(n.m2.frequency, fm * 2.01);
      set(n.mlp.frequency, 900 + rps * 4);
      set(n.mg.gain, (rps > 2 ? 0.05 : 0) + 0.22 * load + 0.04 * Math.min(1, rps / 300));
      set(n.gw.frequency, 300 + rps * 10 * 0.5); set(n.gg.gain, 0.025 * Math.min(1, rps / 250));
      const slip = Math.max(0, Math.abs(s.kappa) - 0.12) * 1.6 + Math.max(0, Math.max(Math.abs(s.alphaF), Math.abs(s.alphaR)) - 0.1) * 2.2;
      set(n.sg.gain, Math.min(0.22, slip * (v > 0.6 ? 1 : 0)), 0.03); set(n.sbp.frequency, 1800 + v * 60);
      set(n.wg.gain, Math.min(0.18, v * v * 0.0016)); set(n.wlp.frequency, 300 + v * 45);
      set(n.b1.frequency, fm * 1.5); set(n.bg.gain, boost ? 0.07 + 0.12 * load : 0, 0.06);
      if (boost && !lastBoost) {                                       // whoosh when the boost kicks in
        const t = ctx.currentTime; n.whg.gain.cancelScheduledValues(t);
        n.whg.gain.setValueAtTime(0.0, t); n.whg.gain.linearRampToValueAtTime(0.32, t + 0.06); n.whg.gain.exponentialRampToValueAtTime(0.001, t + 0.9);
        n.whf.frequency.setValueAtTime(500, t); n.whf.frequency.exponentialRampToValueAtTime(2600, t + 0.8);
      }
      lastBoost = boost;
    },
  };
}
