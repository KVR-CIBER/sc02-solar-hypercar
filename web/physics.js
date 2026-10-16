// Exact JavaScript port of sim/sim.py (one car, stepwise), so the browser and the Python model agree.
// Units: SI. Use createCar(opts) then car.step(dt) repeatedly; car.state holds everything for drawing.

export const MOTORS = {
  kit_1200rpm: { name: "Kitmotor (1200 rpm)", ke: 0.0239, R: 3.75, I0: 0.12, J: 1.0e-7, m: 0.017 },
  fa130: { name: "FA-130 generiek", ke: 0.00273, R: 1.30, I0: 0.18, J: 1.0e-7, m: 0.018 },
  tamiya_tt2: { name: "Tamiya Torque-Tuned 2", ke: 0.00215, R: 0.85, I0: 0.40, J: 1.1e-7, m: 0.019 },
  tamiya_ad2: { name: "Tamiya Atomic-Tuned 2", ke: 0.00199, R: 0.75, I0: 0.45, J: 1.1e-7, m: 0.019 },
  tamiya_hd3: { name: "Tamiya Hyper-Dash 3", ke: 0.00148, R: 0.50, I0: 0.60, J: 1.1e-7, m: 0.019 },
  re280_6v: { name: "RE-280 (6 V)", ke: 0.00520, R: 1.00, I0: 0.25, J: 3.0e-7, m: 0.040 },
  rs380_7v2: { name: "RS-380 (7.2 V)", ke: 0.00435, R: 0.15, I0: 0.80, J: 6.0e-7, m: 0.070 },
};

// defaults = the built car (CAD mass report + sim.P)
export const DEFAULTS = {
  motor: "tamiya_hd3", nMotors: 2, pinion: 8, spur: 42, D: 0.040,
  d0: 0.45, Tr: 0.35, launch: true,
  mu: 0.9, Rb: 0.35, Voc: 5.2, extraMass: 0.0, pi4: false,
  cadTotal: 0.3102, cadMotorMass: 0.038, fRear: 0.647, hCg: 0.024,
};

const P = { g: 9.81, rho: 1.2, distance: 12.0, tyreW: 0.010, Crr: 0.015, Fbearing: 0.02, CdA: 0.003,
  wheelbase: 0.170, B: 8.0, C: 1.65, vReg: 0.3, Iaux: 0.08, Ipv: 0.0, Rmosfet: 0.015, eta: 0.92, Jgear: 2e-8 };

export function wheelMass(D) {
  const Dmm = D * 1000;
  const tyre = Math.PI / 4 * (Dmm ** 2 - (Dmm - 5) ** 2) * P.tyreW * 1000 * 1.15e-6;
  const rim = 2.0e-3 + 1.6e-3 * (Dmm / 40) ** 2;
  return tyre + rim;
}

export function motorPack(key, n) {
  const m = MOTORS[key];
  return { ...m, R: m.R / n, I0: m.I0 * n, J: m.J * n, m: m.m * n, name: (n > 1 ? n + "× " : "") + m.name };
}

export function createCar(o = {}) {
  const c = { ...DEFAULTS, ...o };
  const mot = motorPack(c.motor, c.nMotors);
  const G = c.spur / c.pinion;
  const r = c.D / 2, mw = wheelMass(c.D), Jw = 0.55 * mw * r * r;
  const mBase = c.cadTotal - c.cadMotorMass - 4 * wheelMass(0.040);
  const extraM = c.extraMass + (c.pi4 ? 0.060 : 0);
  const extraI = c.pi4 ? 0.75 : 0;
  const m = mBase + mot.m + 4 * mw + extraM;
  const mEff = m + 2 * Jw / (r * r);
  const Jm = mot.J + P.Jgear + 2 * Jw / (G * G);
  const Rm = mot.R + P.Rmosfet;
  const V0 = c.Voc - c.Rb * (P.Iaux + extraI - P.Ipv);
  const s = { t: 0, x: 0, v: 0, w: 0, a: 0, u: 0, I: 0, Vbus: V0, F: 0, d: 0, kappa: 0, wheelAngleR: 0, wheelAngleF: 0,
    motorAngle: 0, t12: null, v12: null, Ipk: 0, Vmin: 99, mAh: 0, done: false };
  function step(dt) {
    const d = c.launch && c.Tr > 0 ? Math.min(1, Math.max(0, c.d0 + (1 - c.d0) * s.t / c.Tr)) : (c.launch ? c.d0 : 1);
    const dd = c.launch && c.Tr === 0 ? 1 : d;
    const Im = Math.max((dd * V0 - mot.ke * s.w) / (Rm + dd * dd * c.Rb), 0);
    const Vbus = V0 - c.Rb * dd * Im;
    const tau = mot.ke * (Im - mot.I0);
    const u = s.w / G * r;
    const kappa = (u - s.v) / Math.max(u, s.v, P.vReg);
    const Nr = m * P.g * c.fRear + m * s.a * c.hCg / P.wheelbase;
    const F = c.mu * Nr * Math.sin(P.C * Math.atan(P.B * kappa));
    const tauLoad = F * r / (G * (F > 0 ? P.eta : 1 / P.eta));
    s.w = Math.max(s.w + dt * (tau - tauLoad) / Jm, 0);
    const Fres = P.Crr * m * P.g + P.Fbearing + 0.5 * P.rho * P.CdA * s.v * s.v;
    const a = (F - (s.v > 0 ? Fres : Math.min(Fres, Math.max(F, 0)))) / mEff;
    s.v = Math.max(s.v + a * dt, 0);
    s.x += s.v * dt;
    s.a = a;
    s.t += dt;
    s.u = s.w / G * r; s.I = dd * Im; s.Vbus = Vbus; s.F = F; s.d = dd; s.kappa = kappa;
    s.wheelAngleR += s.u / r * dt; s.wheelAngleF += s.v / r * dt; s.motorAngle += s.w * dt;
    if (!s.done) {
      s.Ipk = Math.max(s.Ipk, s.I); s.Vmin = Math.min(s.Vmin, Vbus); s.mAh += s.I * dt / 3.6;
      if (s.x >= P.distance) { s.done = true; s.t12 = s.t; s.v12 = s.v; }
    }
  }
  return { cfg: c, motor: mot, G, mass: m, state: s, step };
}

// simulate to the finish (or tMax) and return the result + optional sampled trace
export function runToFinish(o, { dt = 1e-4, tMax = 8, sampleEvery = 0 } = {}) {
  const car = createCar(o);
  const tr = [];
  const n = Math.round(tMax / dt);
  for (let k = 0; k < n && !car.state.done; k++) {
    car.step(dt);
    if (sampleEvery && k % sampleEvery === 0) {
      const s = car.state;
      tr.push([s.t, s.x, s.v, s.u, s.I, s.Vbus, s.kappa, s.d]);
    }
  }
  return { car, t12: car.state.t12, trace: tr };
}

// grid search for the best launch control of a given hardware config (~0.3 s in a browser)
export function optimiseLaunch(o) {
  let best = { t: 99 };
  for (let d0 = 0.3; d0 <= 1.0001; d0 += 0.05) {
    for (let Tr = 0; Tr <= 0.8001; Tr += 0.05) {
      const r = runToFinish({ ...o, d0: +d0.toFixed(2), Tr: +Tr.toFixed(2), launch: true }, { dt: 2e-4 });
      if (r.t12 && r.t12 < best.t) best = { t: r.t12, d0: +d0.toFixed(2), Tr: +Tr.toFixed(2) };
    }
  }
  return best;
}
