#!/usr/bin/env python3
"""Final-design simulation + all figures for the design report (out/*.png, out/final_design.json)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sim

OUT = sim.OUT
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True, "grid.alpha": 0.3})
motors = sim.load_motors()
hd3 = motors["tamiya_hd3"]
motors["2x_hd3"] = dict(hd3, name="2x Hyper-Dash 3 (parallel)", R=hd3["R"] / 2, I0=hd3["I0"] * 2,
                        J=hd3["J"] * 2, m=hd3["m"] * 2)

# ---- final design (must match cad/params.py); mass + CG come from the CAD model ----
_cad = os.path.join(os.path.dirname(sim.HERE), "cad", "out", "mass_report.json")
if os.path.exists(_cad):                       # keep a copy so the sim folder also works on its own
    import shutil; shutil.copy(_cad, os.path.join(sim.HERE, "cad_mass_report.json"))
CAD = json.load(open(os.path.join(sim.HERE, "cad_mass_report.json")))
FINAL = dict(motor="2x_hd3", D=0.040, pinion=8, spur=42)
_wheel = sim.wheel_mass(FINAL["D"])
sim.P["f_rear"] = CAD["rear_fraction"]
sim.P["m_base"] = CAD["total_g"] / 1000 - motors["2x_hd3"]["m"] - 4 * _wheel
sim.P["h_cg"] = 0.024
print(f"CAD: {CAD['total_g']} g, rear {CAD['rear_fraction']*100:.1f} % -> m_base {sim.P['m_base']*1000:.0f} g")
FINAL["G"] = FINAL["spur"] / FINAL["pinion"]
mot = motors[FINAL["motor"]]

# best launch control for the final hardware
d0s = np.round(np.arange(0.3, 1.01, 0.05), 2)
Trs = np.round(np.arange(0.0, 0.81, 0.05), 2)
AA, TT = np.meshgrid(d0s, Trs, indexing="ij")
r = sim.simulate(mot, FINAL["G"], FINAL["D"], AA, TT)
t = np.nan_to_num(r["t12"], nan=99)
i = np.unravel_index(np.argmin(t), t.shape)
FINAL.update(d0=float(AA[i]), Tr=float(TT[i]), t12=float(t[i]))
full = sim.simulate(mot, FINAL["G"], FINAL["D"], 1.0, 0.0)
FINAL["t12_full_throttle"] = float(full["t12"])

fig, ax = plt.subplots(figsize=(5.2, 3.6))
cs = ax.contourf(TT * 1000, AA * 100, np.clip(t, None, t.min() + 0.4), levels=20, cmap="viridis_r")
fig.colorbar(cs, label="time over 12 m (s)")
ax.plot(FINAL["Tr"] * 1000, FINAL["d0"] * 100, "r*", ms=12)
ax.set_xlabel("ramp time (ms)"); ax.set_ylabel("start duty (%)")
ax.set_title("Launch control map (final car)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "launch_map.png")); plt.close(fig)

# ---- traces: final with vs without launch control ----
tr = sim.simulate(mot, np.array([FINAL["G"], FINAL["G"]]), FINAL["D"], np.array([FINAL["d0"], 1.0]),
                  np.array([FINAL["Tr"], 0.0]), trace=True)
T = tr["trace"]
fig, axs = plt.subplots(2, 2, figsize=(9, 5.6), sharex=True)
lab = [f"launch control ({FINAL['d0']*100:.0f}% -> 100% in {FINAL['Tr']*1000:.0f} ms)", "full throttle at t=0"]
for k in range(2):
    sel = T["x"][:, k] <= 12.0
    tt = T["t"][sel]
    axs[0, 0].plot(tt, T["v"][sel, k], label=lab[k])
    axs[0, 0].plot(tt, T["u"][sel, k], "--", lw=0.8, color=f"C{k}")
    axs[0, 1].plot(tt, T["x"][sel, k])
    axs[1, 0].plot(tt, T["I"][sel, k]); axs[1, 0].plot(tt, T["Vbus"][sel, k], ":", color=f"C{k}")
    axs[1, 1].plot(tt, T["kappa"][sel, k] * 100)
axs[0, 0].set_ylabel("speed (m/s)  [dashed = tyre surface]"); axs[0, 0].legend(fontsize=7)
axs[0, 1].set_ylabel("distance (m)"); axs[0, 1].axhline(12, color="k", lw=0.5)
axs[1, 0].set_ylabel("battery current (A)  [dotted = Vbus (V)]")
axs[1, 1].set_ylabel("tyre slip (%)"); axs[1, 1].set_ylim(0, 100)
for a in axs[1]: a.set_xlabel("time (s)")
fig.suptitle(f"Final car: {mot['name']}, D={FINAL['D']*1000:.0f} mm, {FINAL['pinion']}T:{FINAL['spur']}T "
             f"(G={FINAL['G']:.2f})  ->  {FINAL['t12']:.3f} s")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "final_run.png")); plt.close(fig)
k0 = T["x"][:, 0] <= 12.0
_step = 20  # 2 ms, same rate as the car log
json.dump(dict(t=T["t"][k0][::_step].round(4).tolist(), v=T["v"][k0, 0][::_step].round(3).tolist(),
               x=T["x"][k0, 0][::_step].round(3).tolist(), vbus=T["Vbus"][k0, 0][::_step].round(3).tolist()),
          open(os.path.join(OUT, "sim_trace.json"), "w"))
FINAL.update(v_finish=float(T["v"][k0, 0][-1]), I_peak=float(T["I"][k0, 0].max()),
             V_min=float(T["Vbus"][k0, 0].min()), mass_g=float(tr["mass"][0] * 1000),
             mAh_used=float(tr["mAh"][0]))

# ---- motor comparison: time vs gear ratio at D=40 mm ----
Gs = np.round(np.arange(1.0, 12.01, 0.25), 2)
fig, ax = plt.subplots(figsize=(6.4, 3.8))
rows = []
for key, m in motors.items():
    GG, DD, A2, T2, tt, rr = sim.optimise(m, Gs, np.array([FINAL["D"]]), sim.GRID["d0s"], sim.GRID["Trs"])
    best = tt.reshape(len(Gs), -1).min(axis=1)
    ax.plot(Gs, np.where(best < 9, best, np.nan), label=m["name"], lw=2.2 if key == FINAL["motor"] else 1)
    j = np.argmin(best); rows.append((m["name"], float(Gs[j]), float(best[j])))
ax.axvline(sim.max_G(FINAL["D"]), color="k", ls=":", lw=0.8)
ax.text(sim.max_G(FINAL["D"]) + 0.1, 2.05, "spur gear would\nhit the ground", fontsize=7)
ax.set_ylim(2.0, 4.6); ax.set_xlabel("gear ratio G"); ax.set_ylabel("time over 12 m (s)")
ax.set_title("Motor choice (40 mm wheels, best launch control per point)")
ax.legend(fontsize=7, ncol=2, loc="upper center"); fig.tight_layout(); fig.savefig(os.path.join(OUT, "motor_compare.png")); plt.close(fig)
FINAL["motor_table"] = rows

# ---- wheel diameter x gear ratio map for the final motor ----
Ds = np.round(np.arange(0.028, 0.0601, 0.002), 3)
GG, DD, A2, T2, tt, rr = sim.optimise(mot, Gs, Ds, np.array([0.5, 0.65, 0.8, 1.0]), np.array([0.0, 0.15, 0.3]))
best = tt.reshape(len(Gs), len(Ds), -1).min(axis=2)
fig, ax = plt.subplots(figsize=(5.6, 3.8))
cs = ax.contourf(Ds * 1000, Gs, np.clip(best, None, best.min() + 0.5), levels=20, cmap="viridis_r")
fig.colorbar(cs, label="time over 12 m (s)")
ax.plot(Ds * 1000, sim.max_G(Ds), "w--", lw=1, label="max single-stage ratio")
ax.plot(FINAL["D"] * 1000, FINAL["G"], "r*", ms=12, label="chosen")
ax.set_xlabel("wheel diameter (mm)"); ax.set_ylabel("gear ratio G"); ax.legend(fontsize=7, loc="upper right")
ax.set_title(f"{mot['name']}: wheel size vs gearing")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "wheel_gear_map.png")); plt.close(fig)

# ---- sensitivity bars for the final car ----
cases = [("nominal", {}, {}), ("battery R 0.25 Ω", {"Rb": 0.25}, {}), ("battery R 0.50 Ω", {"Rb": 0.5}, {}),
         ("grip μ 0.6", {"mu": 0.6}, {}), ("grip μ 1.1", {"mu": 1.1}, {}), ("rested cells 4.9 V", {"Voc": 4.9}, {}),
         ("+20 g mass", {}, {"extra_mass": 0.02}), ("Pi 4 on board", {}, {"extra_mass": 0.06, "extra_I": 0.75}),
         ("one motor only", "single", {})]
names, vals = [], []
for lab_, ch, kw in cases:
    m = hd3 if ch == "single" else mot
    p = sim.P if ch == "single" else dict(sim.P, **ch)
    rr = sim.simulate(m, FINAL["G"], FINAL["D"], AA, TT, p=p, **kw)
    names.append(lab_); vals.append(float(np.nanmin(rr["t12"])))
fig, ax = plt.subplots(figsize=(6, 3.4))
ax.barh(names[::-1], vals[::-1], color=["C3" if n == "nominal" else "C0" for n in names[::-1]])
for y, vv in enumerate(vals[::-1]): ax.text(vv + 0.01, y, f"{vv:.2f} s", va="center", fontsize=7)
ax.set_xlim(2.0, max(vals) + 0.2); ax.set_xlabel("time over 12 m (s), same gearing, re-tuned launch")
ax.set_title("What if... (final car)"); fig.tight_layout(); fig.savefig(os.path.join(OUT, "sensitivity.png")); plt.close(fig)
FINAL["sensitivity"] = dict(zip(names, vals))

json.dump(FINAL, open(os.path.join(OUT, "final_design.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in FINAL.items() if k not in ("motor_table",)}, indent=1))
for row in rows: print(f"  {row[0]:30s} best G={row[1]:.2f}  t={row[2]:.3f}s")
