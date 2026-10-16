#!/usr/bin/env python3
"""Slice every SC-02 plate for the Bambu P1S (0.4) -> .3mf + print_report.json"""
import json, os, re, shutil, subprocess, sys, math
import trimesh
HERE = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(HERE, "..", "out", "stl"); OUT = os.path.join(HERE, "..", "out", "print"); os.makedirs(OUT, exist_ok=True)
PREP = os.path.join(OUT, "_stl"); os.makedirs(PREP, exist_ok=True)
BAMBU = "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
def prep(name, rx=0, ry=0):
    m = trimesh.load(os.path.join(STL, name + ".stl"))
    if rx: m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(rx), [1, 0, 0]))
    if ry: m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(ry), [0, 1, 0]))
    m.apply_translation(-m.bounds[0]); p = os.path.join(PREP, f"{name}_{rx}_{ry}.stl"); m.export(p); return p
sys.path.insert(0, os.path.join(HERE, ".."))
from plates import PLATES
report = {}
for name, (fil, proc, items) in PLATES.items():
    files = [prep(*it) for it in items]
    work = os.path.join(OUT, "_" + name); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    cmd = [BAMBU, "--debug", "1", "--arrange", "1", "--orient", "0",
           "--load-settings", f"{HERE}/machine.json;{HERE}/process_{proc}.json", "--load-filaments", f"{HERE}/filament_{fil}.json",
           "--slice", "0", "--export-3mf", name + ".3mf", "--outputdir", work] + files
    r = subprocess.run(cmd, capture_output=True, text=True)
    g = os.path.join(work, "plate_1.gcode")
    if not os.path.exists(g):
        report[name] = dict(error=(r.stdout + r.stderr)[-300:]); print(name, "FAILED", (r.stdout + r.stderr)[-200:].replace("\n", " ")); continue
    head = open(g, errors="ignore").read(20000)
    t = re.search(r"total estimated time: ([^\n;]+)", head).group(1).strip()
    w = float(re.search(r"total filament weight \[g\] : ([\d.]+)", head).group(1))
    m3 = os.path.join(work, name + ".3mf")
    if os.path.exists(m3): shutil.move(m3, os.path.join(OUT, name + ".3mf"))
    report[name] = dict(material=fil.upper(), profile=proc, time=t, grams=w)
    print(f"{name:26s} {fil.upper():5s} {w:7.1f} g  {t}")
json.dump(report, open(os.path.join(OUT, "print_report.json"), "w"), indent=1)
