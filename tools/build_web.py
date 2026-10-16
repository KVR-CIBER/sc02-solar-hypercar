#!/usr/bin/env python3
"""Collects downloadable files into web/files/ and writes web/files/files.json."""
import json, os, shutil, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, "web", "files")
os.makedirs(F, exist_ok=True)
def size(p):
    n = os.path.getsize(p)
    return f"{n/1e6:.1f} MB" if n > 1e6 else f"{n/1e3:.0f} kB"
sections = []
def add(title, items):
    out = []
    for src, label in items:
        if not os.path.exists(src):
            continue
        dst = os.path.join(F, os.path.basename(src))
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy2(src, dst)
        out.append(dict(path=os.path.basename(src), label=label, size=size(dst)))
    if out:
        sections.append(dict(title=title, items=out))
# zips
def zipdir(name, folder, pattern=None, base=None):
    z = os.path.join(F, name)
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for r, _, files in os.walk(folder):
            if "__pycache__" in r or ".venv" in r or "/_" in r:
                continue
            for f in files:
                if pattern and not f.endswith(pattern):
                    continue
                p = os.path.join(r, f)
                zf.write(p, os.path.relpath(p, base or folder))
    return z
P = os.path.join(ROOT, "cad", "out", "print")
add("Video", [(os.path.join(ROOT, "video", "solar_challenger_4k.mp4"), "4K simulatievideo (3840×2160, 60 fps)"),
              (os.path.join(ROOT, "video", "solar_challenger_1080p.mp4"), "Video 1080p (kleiner)")])
add("3D-printen (Bambu P1S, klaar om te printen)", [
    (os.path.join(P, "1_car_ASA.3mf"), "Plaat 1 – auto (ASA)"),
    (os.path.join(P, "2_wheels_PLA.3mf"), "Plaat 2 – velgen + tandwiel (PLA)"),
    (os.path.join(P, "3_tyre_mold_PLA.3mf"), "Plaat 3 – bandenmal (PLA)"),
    (os.path.join(P, "4_option_TPU_tyres.3mf"), "Optie – TPU-banden"),
    (os.path.join(P, "5_option_rims_for_TPU_PLA.3mf"), "Optie – velgen voor TPU-banden"),
    (zipdir("stl_alle_onderdelen.zip", os.path.join(ROOT, "cad", "out", "stl"), ".stl"), "Alle STL-bestanden (zip)"),
    (os.path.join(ROOT, "cad", "out", "step", "assembly.step"), "Volledige assemblage (STEP)")])
add("Documenten", [
    (os.path.join(ROOT, "docs", "build_guide.md"), "Bouwhandleiding"),
    (os.path.join(ROOT, "docs", "BOM.md"), "Onderdelenlijst + prijzen"),
    (os.path.join(ROOT, "docs", "design_report.md"), "Ontwerprapport (concept)"),
    (os.path.join(ROOT, "docs", "wiring.png"), "Elektrisch schema"),
    (os.path.join(ROOT, "docs", "wiring.md"), "Bedrading + pinout")])
add("Simulatie & code", [
    (os.path.join(ROOT, "sim", "out", "final_run.png"), "Simulatie: race met/zonder launch control"),
    (os.path.join(ROOT, "sim", "out", "motor_compare.png"), "Motorkeuze"),
    (os.path.join(ROOT, "sim", "out", "sensitivity.png"), "Wat-als-analyse"),
    (zipdir("simulatie_python.zip", os.path.join(ROOT, "sim")), "Python-simulatie (zip)"),
    (zipdir("firmware_esp32s3.zip", os.path.join(ROOT, "firmware")), "ESP32-S3 firmware (zip)"),
    (zipdir("pit_station_pi4.zip", os.path.join(ROOT, "pit")), "Pi 4 pit-station (zip)")])
json.dump(sections, open(os.path.join(F, "files.json"), "w"), indent=1)
print(sum(len(s["items"]) for s in sections), "files")
