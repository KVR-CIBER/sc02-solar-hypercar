"""Robustness check: how do the best candidates hold up when the uncertain inputs change?"""
import json, os, numpy as np, sim
motors = sim.load_motors()
hd3 = motors["tamiya_hd3"]
motors["2x_hd3"] = dict(hd3, name="2x Hyper-Dash 3 (parallel)", R=hd3["R"]/2, I0=hd3["I0"]*2, J=hd3["J"]*2, m=hd3["m"]*2)
cands = {"tamiya_hd3": 0.040, "tamiya_ad2": 0.040, "2x_hd3": 0.040, "rs380_7v2": 0.044, "fa130": 0.040}
Gs = np.round(np.arange(1.0, 12.01, 0.25), 2)
cases = [("nominal", {}), ("Rb=0.25", {"Rb": 0.25}), ("Rb=0.50", {"Rb": 0.50}),
         ("mu=0.6", {"mu": 0.6}), ("mu=1.1", {"mu": 1.1}), ("Voc=4.9 (rested cells)", {"Voc": 4.9}),
         ("+60 g, +0.75 A (Pi 4 on board)", {"_pi": 1})]
out = {}
for key, D in cands.items():
    m = motors[key]; out[key] = {}
    for label, ch in cases:
        p = dict(sim.P, **{k: v for k, v in ch.items() if not k.startswith("_")})
        kw = dict(extra_mass=0.060, extra_I=0.75) if "_pi" in ch else {}
        GG, DD, AA, TT, t, res = sim.optimise(m, Gs, np.array([D]), sim.GRID["d0s"], sim.GRID["Trs"], p=p, **kw)
        t = np.where(GG <= sim.max_G(DD), t, 99)
        i = np.unravel_index(np.argmin(t), t.shape)
        out[key][label] = dict(t12=float(t[i]), G=float(GG[i]), d0=float(AA[i]), Tr=float(TT[i]),
                               Vmin=float(res["Vmin"][i]), Ipk=float(res["Ipk"][i]))
        print(f"{m['name']:28s} D={D*1000:.0f} {label:32s} t12={t[i]:.3f}s G={GG[i]:.2f} d0={AA[i]} Tr={TT[i]} Vmin={res['Vmin'][i]:.2f} Ipk={res['Ipk'][i]:.1f}", flush=True)
json.dump(out, open(os.path.join(sim.OUT, "sensitivity.json"), "w"), indent=1)
