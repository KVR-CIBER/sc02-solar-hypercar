#!/usr/bin/env python3
"""Slice every plate with Bambu Studio (P1S 0.4) -> ready-to-print .3mf + print_report.json."""
import json, os, re, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(HERE, "..", "out", "stl")
OUT = os.path.join(HERE, "..", "out", "print")
BAMBU = "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
PLATES = {
    "1_car_ASA":      ("asa", "std",  ["chassis", "front_carrier", "motor_clamp", "panel_frame"] + ["bearing_cap"] * 4),
    "2_wheels_PLA":   ("pla", "fine", ["rim_silicone"] * 5 + ["spur_42T_m05"] * 2 + ["spacer"] * 6),
    "3_tyre_mold_PLA": ("pla", "std", ["mold_base", "mold_lid"]),
    "4_option_TPU_tyres": ("tpu", "std", ["tyre_tpu"] * 4),
    "5_option_rims_for_TPU_PLA": ("pla", "fine", ["rim_tpu"] * 4),
}
os.makedirs(OUT, exist_ok=True)
report = {}
for name, (fil, proc, files) in PLATES.items():
    work = os.path.join(OUT, "_" + name); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    cmd = [BAMBU, "--debug", "1", "--arrange", "1", "--orient", "0",
           "--load-settings", f"{HERE}/machine.json;{HERE}/process_{proc}.json",
           "--load-filaments", f"{HERE}/filament_{fil}.json", "--slice", "0",
           "--export-3mf", name + ".3mf", "--outputdir", work] + [os.path.join(STL, f + ".stl") for f in files]
    r = subprocess.run(cmd, capture_output=True, text=True)
    g = os.path.join(work, "plate_1.gcode")
    if not os.path.exists(g):
        report[name] = dict(error=(r.stdout + r.stderr)[-400:]); print(name, "FAILED"); continue
    head = open(g, errors="ignore").read(20000)
    t = re.search(r"total estimated time: ([^\n;]+)", head).group(1).strip()
    w = float(re.search(r"total filament weight \[g\] : ([\d.]+)", head).group(1))
    m = os.path.join(work, name + ".3mf")
    if os.path.exists(m):
        shutil.move(m, os.path.join(OUT, name + ".3mf"))
    report[name] = dict(material=fil.upper(), profile=proc, parts=files, time=t, grams=w,
                        three_mf=os.path.exists(os.path.join(OUT, name + ".3mf")))
    print(f"{name:28s} {fil.upper():5s} {w:7.1f} g  {t}  3mf={'yes' if report[name]['three_mf'] else 'no'}")
json.dump(report, open(os.path.join(OUT, "print_report.json"), "w"), indent=1)
