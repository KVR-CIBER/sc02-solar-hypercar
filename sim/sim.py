#!/usr/bin/env python3
"""
Solar Olympiade 2027 - Challenger race simulation (12 m from standstill, max 30 cm wide).

Model (vectorised over every design combination at once):
  - Battery: 4x NiMH AA in series, open-circuit voltage Voc, internal resistance Rb
    (cells + holders + switch + fuse + wires).
  - Brushed DC motor: I = (d*Vbus - ke*w) / R, torque = ke*(I - I0). PWM duty d = launch control.
  - Tyres: Pacejka-like slip curve F = mu*N*sin(C*atan(B*kappa)); wheelspin loses grip.
  - Rolling resistance, bearing drag, aero drag, wheel inertia, rotor inertia.
  - Dynamic load transfer to the rear axle while accelerating.
Optimises per motor: gear ratio G, wheel diameter D and launch control (start duty d0, ramp time Tr).

Run:  ../.venv/bin/python sim.py        -> out/summary.json + out/grid_*.npy
      ../.venv/bin/python plots.py      -> out/*.png
"""
import json, time, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

P = dict(
    g=9.81, rho=1.2,
    distance=12.0,          # m
    m_base=0.228,           # kg: everything except motor and wheels (mass budget in README)
    tyre_width=0.010,       # m
    Crr=0.015,              # rolling resistance, silicone on sports-hall floor
    F_bearing=0.02,         # N, bearings + gear mesh (constant part)
    CdA=0.003,              # m^2
    wheelbase=0.170, h_cg=0.030, f_rear=0.68,   # centre of gravity
    mu=0.9, B=8.0, C=1.65, v_reg=0.3,           # tyre model
    Voc=5.2, Rb=0.35, I_aux=0.08, I_pv=0.0,     # battery / ESP32 draw / panel (ignored)
    R_mosfet=0.015, eta_gear=0.92, J_gear=2e-8,
    dt=1e-4, t_max=8.0,
    pinion_z=8, module=0.5, clearance=3.0,      # mm, for gear feasibility
)

def wheel_mass(D):
    """Rim (printed, lightened) + 2.5 mm silicone tyre. D in m -> kg."""
    Dmm = D * 1000
    tyre = np.pi / 4 * (Dmm**2 - (Dmm - 5) ** 2) * P["tyre_width"] * 1000 * 1.15e-6
    rim = 2.0e-3 + 1.6e-3 * (Dmm / 40) ** 2
    return tyre + rim

def simulate(motor, G, D, d0, Tr, p=P, extra_mass=0.0, extra_I=0.0, trace=False):
    """All design arguments may be numpy arrays (broadcast together)."""
    G, D, d0, Tr = (a.astype(float) for a in np.broadcast_arrays(*map(np.asarray, (G, D, d0, Tr))))
    r = D / 2
    mw = wheel_mass(D)
    Jw = 0.55 * mw * r**2
    m = p["m_base"] + motor["m"] + 4 * mw + extra_mass
    m_eff = m + 2 * Jw / r**2                      # free-rolling front wheels
    Jm = motor["J"] + p["J_gear"] + 2 * Jw / G**2  # driven rear axle reflected to motor shaft
    Rm = motor["R"] + p["R_mosfet"]
    ke, I0 = motor["ke"], motor["I0"]
    V0 = p["Voc"] - p["Rb"] * (p["I_aux"] + extra_I - p["I_pv"])

    z = np.zeros_like(G)
    x, v, w, a_prev = z.copy(), z.copy(), z.copy(), z.copy()
    t12, v12 = np.full_like(G, np.nan), np.full_like(G, np.nan)
    Ipk, Q, E = z.copy(), z.copy(), z.copy()
    Vmin = np.full_like(G, 99.0)
    done = np.zeros(G.shape, bool)
    dt = p["dt"]
    keys = ("t", "x", "v", "u", "I", "Vbus", "F", "d", "kappa")
    tr = {k: [] for k in keys} if trace else None
    for k in range(int(p["t_max"] / dt)):
        t = k * dt
        d = np.where(Tr > 0, np.clip(d0 + (1 - d0) * t / np.maximum(Tr, 1e-9), 0, 1), 1.0)
        Im = np.maximum((d * V0 - ke * w) / (Rm + d * d * p["Rb"]), 0.0)
        Vbus = V0 - p["Rb"] * d * Im
        tau = ke * (Im - I0)
        u = w / G * r                                   # rear tyre surface speed
        kappa = (u - v) / np.maximum(np.maximum(u, v), p["v_reg"])
        Nr = m * p["g"] * p["f_rear"] + m * a_prev * p["h_cg"] / p["wheelbase"]
        F = p["mu"] * Nr * np.sin(p["C"] * np.arctan(p["B"] * kappa))
        tau_load = F * r / (G * np.where(F > 0, p["eta_gear"], 1 / p["eta_gear"]))
        w = np.maximum(w + dt * (tau - tau_load) / Jm, 0.0)
        Fres = p["Crr"] * m * p["g"] + p["F_bearing"] + 0.5 * p["rho"] * p["CdA"] * v * v
        a = (F - np.where(v > 0, Fres, np.minimum(Fres, np.maximum(F, 0)))) / m_eff
        v = np.maximum(v + a * dt, 0.0)
        x = x + v * dt
        a_prev = a
        live = ~done
        Ib = d * Im
        Ipk = np.where(live, np.maximum(Ipk, Ib), Ipk)
        Vmin = np.where(live, np.minimum(Vmin, Vbus), Vmin)
        Q = np.where(live, Q + Ib * dt, Q)
        E = np.where(live, E + Ib * Vbus * dt, E)
        new = live & (x >= p["distance"])
        t12 = np.where(new, t + dt, t12); v12 = np.where(new, v, v12)
        done |= new
        if trace:
            for key, val in zip(keys, (t, x, v, u, Ib, Vbus, F, d, kappa)):
                tr[key].append(np.array(val, copy=True))
            if x.min() > p["distance"] + 1.0:
                break
        elif done.all():
            break
    res = dict(t12=t12, v12=v12, Ipk=Ipk, Vmin=Vmin, mAh=Q / 3.6, E=E, mass=m)
    if trace:
        res["trace"] = {k: np.array(vv) for k, vv in tr.items()}
    return res

def max_G(D, p=P):
    """Largest single-stage ratio whose spur gear still clears the ground."""
    z_max = (D * 1000 - 2 * p["clearance"]) / p["module"] - 2
    return z_max / p["pinion_z"]

def optimise(motor, Gs, Ds, d0s, Trs, p=P, **kw):
    GG, DD, AA, TT = np.meshgrid(Gs, Ds, d0s, Trs, indexing="ij")
    res = simulate(motor, GG, DD, AA, TT, p=p, **kw)
    t = np.nan_to_num(res["t12"], nan=99.0)
    return GG, DD, AA, TT, t, res

GRID = dict(
    Gs=np.round(np.arange(1.0, 14.01, 0.5), 2),
    Ds=np.round(np.arange(0.028, 0.0701, 0.004), 3),
    d0s=np.array([0.35, 0.5, 0.65, 0.8, 1.0]),
    Trs=np.array([0.0, 0.15, 0.3, 0.5]),
)

def load_motors():
    return {k: v for k, v in json.load(open(os.path.join(HERE, "motors.json"))).items() if not k.startswith("_")}

if __name__ == "__main__":
    motors = load_motors()
    Gs, Ds = GRID["Gs"], GRID["Ds"]
    summary = {}
    t0 = time.time()
    for key, mot in motors.items():
        GG, DD, AA, TT, t, res = optimise(mot, **GRID)
        th = np.where(GG <= max_G(DD), t, 99)          # only buildable single-stage gearing
        i = np.unravel_index(np.argmin(th), th.shape)
        j = np.unravel_index(np.argmin(t), t.shape)
        nolc = simulate(mot, GG[i], DD[i], 1.0, 0.0)   # same car, full throttle from t=0
        summary[key] = dict(
            name=mot["name"], G=float(GG[i]), D_mm=float(DD[i] * 1000), d0=float(AA[i]), Tr=float(TT[i]),
            t12=float(t[i]), v12=float(res["v12"][i]), Ipk=float(res["Ipk"][i]), Vmin=float(res["Vmin"][i]),
            mAh=float(res["mAh"][i]), mass_g=float(res["mass"][i] * 1000),
            t12_no_launch_control=float(nolc["t12"]),
            t12_unconstrained=float(t[j]), G_unconstrained=float(GG[j]), D_unconstrained_mm=float(DD[j] * 1000),
        )
        np.save(os.path.join(OUT, f"grid_{key}.npy"), np.min(t.reshape(len(Gs), len(Ds), -1), axis=2))
        s = summary[key]
        print(f"{mot['name']:30s} t12={s['t12']:.3f}s G={s['G']:.1f} D={s['D_mm']:.0f}mm d0={s['d0']} Tr={s['Tr']} "
              f"Ipk={s['Ipk']:.1f}A Vmin={s['Vmin']:.2f}V v12={s['v12']:.1f}m/s m={s['mass_g']:.0f}g "
              f"| no-LC {s['t12_no_launch_control']:.3f}s | unconstr. {s['t12_unconstrained']:.3f}s "
              f"G={s['G_unconstrained']} D={s['D_unconstrained_mm']:.0f}  ({time.time()-t0:.0f}s)", flush=True)
    json.dump(dict(params=P, Gs=Gs.tolist(), Ds=Ds.tolist(), results=summary),
              open(os.path.join(OUT, "summary.json"), "w"), indent=1)
