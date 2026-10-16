// SC-02 vehicle dynamics: planar bicycle model + slip tyres + DC motors + battery + power accounting.
// Same motor/battery/tyre equations as sim/sim.py, extended with steering, lateral grip, reverse, braking.

export const BATTERIES = {
  aa: { name: "4x AA NiMH", cells: 4, vFull: 1.38, vNom: 1.22, vEmpty: 1.05, Rb: 0.35, mAh: 2000, mass: 0.124 },
  lipo3s: { name: "3S LiPo 1300", cells: 3, vFull: 4.2, vNom: 3.75, vEmpty: 3.4, Rb: 0.045, mAh: 1300, mass: 0.110 },
};
const HD3 = { ke: 0.00148, R: 0.5, I0: 0.6, J: 1.1e-7 };   // Tamiya Hyper-Dash 3 (estimate, see motors.json)

export function createVehicle(o = {}) {
  const c = {
    mass: 0.745, wb: 0.230, cgFromRear: 0.098, hCg: 0.026, Iz: 0.0098,
    rRear: 0.022, rFront: 0.021, G: 35 / 10, nMot: 2, eta: 0.92, Rdrv: 0.06,
    mu: 0.95, B: 8, C: 1.45, Crr: 0.015, CdA: 0.0065, ClA: 0.006, rho: 1.2,
    steerMax: 20 * Math.PI / 180, steerRate: 9.0,
    battery: "lipo3s", vMotorMax: 4.8, tc: true, launch: true,
    pPi: 3.4, pEsp: 0.45, pServoIdle: 0.12, convEff: 0.9,
    ...o,
  };
  const bat = BATTERIES[c.battery];
  const m = c.mass - BATTERIES.lipo3s.mass + bat.mass;
  const a = c.wb - c.cgFromRear, b = c.cgFromRear;
  const mot = { ke: HD3.ke, R: HD3.R / c.nMot, I0: HD3.I0 * c.nMot, J: HD3.J * c.nMot };
  const Jw = 2 * 0.55 * 0.012 * c.rRear * c.rRear;           // two rear wheels on the axle
  const Jm = mot.J + Jw / (c.G * c.G);
  const s = {
    x: 0, y: 0, psi: 0, vx: 0, vy: 0, r: 0, w: 0, delta: 0, soc: 1, t: 0,
    wheelR: 0, wheelF: 0, I: 0, Vbus: 0, P: { motor: 0, pi: 0, esp: 0, servo: 0, total: 0 }, kappa: 0, alphaF: 0, alphaR: 0,
    ax: 0, ay: 0, duty: 0, speed: 0, energyWh: 0,
  };
  const g = 9.81;
  function voc() {
    const v = bat.vEmpty + (bat.vFull - bat.vEmpty) * (0.12 + 0.88 * Math.pow(s.soc, 0.8)) * 0.98;
    return bat.cells * Math.min(bat.vFull, v);
  }
  function tyre(Fz, slip) { return c.mu * Fz * Math.sin(c.C * Math.atan(c.B * slip)); }

  // input: throttle -1..1 (negative = reverse), brake 0..1, steer -1..1 (left positive)
  function step(dt, inp) {
    const V0 = voc();
    // --- steering servo (rate limited)
    const target = Math.max(-1, Math.min(1, inp.steer)) * c.steerMax;
    const dd = Math.max(-c.steerRate * dt, Math.min(c.steerRate * dt, target - s.delta));
    s.delta += dd;
    const servoP = c.pServoIdle + 2.2 * Math.abs(dd / dt) / c.steerRate;
    // --- motor drive (H-bridge; firmware caps the motor voltage)
    const vx = s.vx, spd = Math.abs(vx) + 1e-6;
    let thr = Math.max(-1, Math.min(1, inp.throttle));
    const uSurf = s.w / c.G * c.rRear;
    const kappa = (uSurf - vx) / Math.max(Math.abs(uSurf), Math.abs(vx), 0.3);
    if (c.tc && Math.abs(kappa) > 0.18 && Math.sign(kappa) === Math.sign(thr)) thr *= Math.max(0.35, 1 - (Math.abs(kappa) - 0.18) * 4);
    let Vm = thr * Math.min(c.vMotorMax, V0);
    let Im;
    const Rm = mot.R + c.Rdrv;
    if (inp.brake > 0.05 && Math.abs(thr) < 0.05) {
      Im = -mot.ke * s.w / Rm * inp.brake;                    // short-brake through the H-bridge
      Vm = 0;
    } else {
      Im = (Vm - mot.ke * s.w) / Rm;
      if (Vm >= 0 && Im < 0 && thr >= 0) Im = Math.max(Im, -mot.ke * s.w / Rm * 0.0);   // freewheel (no regen)
    }
    const Pm = Math.max(0, Vm * Im);
    let tau = mot.ke * Im - Math.sign(s.w) * mot.ke * mot.I0 * Math.min(1, Math.abs(s.w) / 50);
    // --- loads
    const Fz = m * g + 0.5 * c.rho * c.ClA * vx * vx;
    const dFz = m * s.ax * c.hCg / c.wb;
    const FzR = Math.max(0.05, Fz * a / c.wb + dFz), FzF = Math.max(0.05, Fz * b / c.wb - dFz);
    // --- tyre forces
    const vxr = Math.max(Math.abs(vx), 0.25) * (vx < 0 ? -1 : 1);
    const alphaF = s.delta - Math.atan2(s.vy + a * s.r, Math.abs(vxr)) * Math.sign(vxr || 1);
    const alphaR = -Math.atan2(s.vy - b * s.r, Math.abs(vxr)) * Math.sign(vxr || 1);
    let FxR = tyre(FzR, kappa);
    let FyR = tyre(FzR, alphaR);
    const lim = c.mu * FzR;
    const tot = Math.hypot(FxR, FyR);
    if (tot > lim) { FxR *= lim / tot; FyR *= lim / tot; }
    const FyF = tyre(FzF, alphaF);
    // --- motor shaft
    const tauLoad = FxR * c.rRear / (c.G * (FxR * s.w >= 0 ? c.eta : 1 / c.eta));
    s.w += dt * (tau - tauLoad) / Jm;
    // --- body (vehicle frame)
    const drag = 0.5 * c.rho * c.CdA * vx * Math.abs(vx);
    const roll = c.Crr * Fz * Math.tanh(vx / 0.05);
    const FxTot = FxR - FyF * Math.sin(s.delta) - drag - roll;
    const FyTot = FyR + FyF * Math.cos(s.delta);
    const axb = FxTot / m + s.vy * s.r, ayb = FyTot / m - s.vx * s.r;
    s.vx += axb * dt; s.vy += ayb * dt;
    s.r += dt * (a * FyF * Math.cos(s.delta) - b * FyR) / c.Iz;
    if (Math.abs(s.vx) < 0.02 && Math.abs(thr) < 0.02) { s.vy *= 0.9; s.r *= 0.9; }
    s.psi += s.r * dt;
    const cs = Math.cos(s.psi), sn = Math.sin(s.psi);
    s.x += (s.vx * cs - s.vy * sn) * dt; s.y += (s.vx * sn + s.vy * cs) * dt;
    s.ax = FxTot / m; s.ay = FyTot / m;
    // --- power + battery
    const Pel = (Pm / c.convEff) + (c.pPi + c.pEsp + servoP) / c.convEff;
    const I = Pel / Math.max(1, V0);
    s.Vbus = V0 - bat.Rb * I;
    s.I = I; s.duty = Math.abs(thr);
    s.P = { motor: Pm, pi: c.pPi, esp: c.pEsp, servo: servoP, total: Pel };
    s.soc = Math.max(0, s.soc - I * dt / 3.6 / bat.mAh);
    s.energyWh += Pel * dt / 3600;
    s.wheelR += uSurf / c.rRear * dt; s.wheelF += s.vx / c.rFront * dt;
    s.kappa = kappa; s.alphaF = alphaF; s.alphaR = alphaR; s.speed = Math.hypot(s.vx, s.vy); s.t += dt;
  }
  function reset(x = 0, y = 0, psi = 0) { Object.assign(s, { x, y, psi, vx: 0, vy: 0, r: 0, w: 0, delta: 0 }); }
  return { c, s, step, reset, bat, mass: m, voc };
}
