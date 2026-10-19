// SC-02 vehicle dynamics: planar bicycle model + slip tyres + DC motors + battery + power accounting.
// Same motor/battery/tyre equations as sim/sim.py, extended with steering, lateral grip, reverse, braking.

export const BATTERIES = {
  aa: { name: "4x AA NiMH", cells: 4, vFull: 1.38, vNom: 1.22, vEmpty: 1.05, Rb: 0.35, mAh: 2000, mass: 0.124 },
  lipo3s: { name: "3S LiPo 1300", cells: 3, vFull: 4.2, vNom: 3.75, vEmpty: 3.4, Rb: 0.045, mAh: 1300, mass: 0.110 },
};
const HD3 = { ke: 0.00148, R: 0.5, I0: 0.6, J: 1.1e-7 };   // Tamiya Hyper-Dash 3 (estimate, see motors.json)

export function createVehicle(o = {}) {
  const c = {
    mass: 0.715, wb: 0.230, cgFromRear: 0.098, hCg: 0.026, Iz: 0.0098,
    rRear: 0.022, rFront: 0.021, G: 35 / 10, nMot: 2, eta: 0.92, Rdrv: 0.06,
    mu: 0.95, B: 8, C: 1.45, muF: 0.9, BF: 6, Crr: 0.015, CdA: 0.0065, ClA: 0.006, rho: 1.2,   // front tyres narrower (15 vs 20 mm): less grip, softer → stable understeer
    steerMax: 20 * Math.PI / 180, steerRate: 9.0,
    battery: "lipo3s", vMotorMax: 4.8, tc: true, launch: true,
    pPi: 0, pEsp: 0.6, pServoIdle: 0.12, convEff: 0.9,         // no Pi anymore: ESP32-S3 + ELRS C3 ~0.6 W
    // boost ("overclock"): the firmware lets the H-bridge put boostGain x the normal motor voltage on the motors, but
    // only while the motors are cool enough and the battery holds its voltage. Same model runs in the car firmware,
    // with the current from the INA226: two 130 motors ~28 J/K, ~10 K/W to the air (better with airflow).
    boostGain: 1.6, Cth: 28, Rth: 10, Tamb: 22, Tlock: 90, Trearm: 70, vCellMin: 3.5, vCellRearm: 3.65,
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
    ax: 0, ay: 0, duty: 0, speed: 0, energyWh: 0, Tm: 22, boost: false, boostLock: '', Pheat: 0,
  };
  const g = 9.81;
  function voc() {
    const v = bat.vEmpty + (bat.vFull - bat.vEmpty) * (0.12 + 0.88 * Math.pow(s.soc, 0.8)) * 0.98;
    return bat.cells * Math.min(bat.vFull, v);
  }
  function tyre(Fz, slip) { return c.mu * Fz * Math.sin(c.C * Math.atan(c.B * slip)); }
  function tyreF(Fz, slip) { return c.mu * c.muF * Fz * Math.sin(c.C * Math.atan(c.BF * slip)); }

  const braking_ = (inp, thr) => inp.brake > 0.05 && Math.abs(thr) < 0.05;
  // input: throttle -1..1 (negative = reverse), brake 0..1, steer -1..1 (left positive), boost bool
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
    // traction control acts on the slip at the start of the step
    const slipOf = (w) => { const u = w / c.G * c.rRear; return (u - vx) / Math.max(Math.abs(u), Math.abs(vx), 0.3); };
    const kappa0 = slipOf(s.w);
    if (c.tc && Math.abs(kappa0) > 0.18 && Math.sign(kappa0) === Math.sign(thr)) thr *= Math.max(0.35, 1 - (Math.abs(kappa0) - 0.18) * 4);
    const braking = braking_(inp, thr);
    // boost: allowed until the motors are too hot or the battery sags; re-armed when cooled / recovered
    if (s.boostLock === 'heet' && s.Tm <= c.Trearm) s.boostLock = '';
    if (s.boostLock === 'batterij' && V0 / bat.cells >= c.vCellRearm && s.soc > 0.12) s.boostLock = '';
    s.boost = !!inp.boost && !s.boostLock && !braking_(inp, thr);
    const vLim = c.vMotorMax * (s.boost ? c.boostGain : 1);
    const Vm = braking_(inp, thr) ? 0 : thr * Math.min(vLim, V0);
    // brake = slip controller in the firmware (ABS-like): the H-bridge servoes the motor to a small
    // negative slip instead of locking the rear. Less slip while steering, so the tail keeps its grip.
    let wT = 0;
    if (braking) {
      const steerUse = Math.min(1, Math.abs(s.delta) / (c.steerMax * Math.max(0.22, Math.min(1, 2.2 / (Math.abs(vx) + 0.6)))));
      const kT = (c.tc ? -0.12 : -0.5) * inp.brake * (1 - steerUse) ** 2;
      wT = vx * (1 + kT) * c.G / c.rRear;
      if (Math.sign(wT) !== Math.sign(s.w)) wT = 0;
    }
    const Rm = mot.R + c.Rdrv;
    // --- loads
    const Fz = m * g + 0.5 * c.rho * c.ClA * vx * vx;
    const dFz = m * s.ax * c.hCg / c.wb;
    const FzR = Math.max(0.05, Fz * a / c.wb + dFz), FzF = Math.max(0.05, Fz * b / c.wb - dFz);
    // slip angles in each wheel's own frame: the lateral force always opposes the wheel's sideways
    // velocity, forwards and in reverse (the old sign trick pushed the car sideways when reversing)
    const cd = Math.cos(s.delta), sd = Math.sin(s.delta), vyF = s.vy + a * s.r, vyR = s.vy - b * s.r;
    const alphaF = -Math.atan2(-vx * sd + vyF * cd, Math.max(Math.abs(vx * cd + vyF * sd), 0.25));
    const alphaR = -Math.atan2(vyR, Math.max(Math.abs(vx), 0.25));
    const lim = c.mu * FzR;
    // net shaft torque and rear tyre forces as a function of motor speed w (body state frozen)
    function shaft(w) {
      let Im;
      let V = Vm;
      if (braking) { const Vx = Math.min(c.vMotorMax, V0); V = Math.max(-Vx, Math.min(Vx, mot.ke * wT + 0.2 * (wT - w))); }
      if (braking) Im = (V - mot.ke * w) / Rm;
      else { Im = (Vm - mot.ke * w) / Rm; if (Vm >= 0 && Im < 0 && thr >= 0) Im = 0; }   // freewheel (no regen)
      const tau = mot.ke * Im - Math.sign(w) * mot.ke * mot.I0 * Math.min(1, Math.abs(w) / 50);
      const k = slipOf(w);
      let Fx = tyre(FzR, k), Fy = tyre(FzR, alphaR);
      const tot = Math.hypot(Fx, Fy);
      if (tot > lim) { Fx *= lim / tot; Fy *= lim / tot; }
      const tauLoad = Fx * c.rRear / (c.G * (Fx * w >= 0 ? c.eta : 1 / c.eta));
      return { net: tau - tauLoad, Fx, Fy, Im, k, V };
    }
    // the wheel+motor inertia is tiny, so tyre slip makes this ODE very stiff:
    // explicit Euler oscillated (wheel-spin chatter). Linearised implicit step instead.
    const f0 = shaft(s.w), e = Math.max(0.5, Math.abs(s.w) * 1e-3);
    const dfdw = (shaft(s.w + e).net - shaft(s.w - e).net) / (2 * e);
    s.w += dt * f0.net / (Jm - dt * Math.min(0, dfdw));
    const sh = shaft(s.w);
    const FxR = sh.Fx, FyR = sh.Fy, kappa = sh.k, uSurf = s.w / c.G * c.rRear;
    const Pm = Math.max(0, (braking ? sh.V : Vm) * sh.Im);
    // --- motor temperature: copper losses I^2 R + brush/iron losses, cooled by the air (more with speed)
    s.Pheat = sh.Im * sh.Im * mot.R + Math.abs(mot.ke * mot.I0 * s.w) * 0.5;
    s.Tm += dt * (s.Pheat - (s.Tm - c.Tamb) * (1 + 0.08 * Math.abs(vx)) / c.Rth) / c.Cth;
    if (s.Tm >= c.Tlock) s.boostLock = 'heet';
    const FyF = tyreF(FzF, alphaF);
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
    if (s.boost && (s.Vbus / bat.cells < c.vCellMin || s.soc < 0.1)) s.boostLock = 'batterij';
    s.energyWh += Pel * dt / 3600;
    s.wheelR += uSurf / c.rRear * dt; s.wheelF += s.vx / c.rFront * dt;
    s.kappa = kappa; s.alphaF = alphaF; s.alphaR = alphaR; s.speed = Math.hypot(s.vx, s.vy); s.t += dt;
  }
  function reset(x = 0, y = 0, psi = 0) { Object.assign(s, { x, y, psi, vx: 0, vy: 0, r: 0, w: 0, delta: 0 }); }
  return { c, s, step, reset, bat, mass: m, voc };
}
