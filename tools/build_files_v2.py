#!/usr/bin/env python3
"""Collect SC-02 downloads into f1/files/ (+ a clean index.html)."""
import json, os, shutil, zipfile, html
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F1 = os.path.join(ROOT, "f1"); OUT = os.path.join(F1, "files")
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
def size(p):
    n = os.path.getsize(p); return f"{n/1e6:.1f} MB" if n > 1e6 else f"{n/1e3:.0f} kB"
def zipdir(name, folder, exts=None, skip=("__pycache__", "/_", "tmp")):
    z = os.path.join(OUT, name)
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for r, _, fs in os.walk(folder):
            if any(s in r for s in skip): continue
            for f in fs:
                if exts and not f.endswith(exts): continue
                p = os.path.join(r, f); zf.write(p, os.path.relpath(p, folder))
    return z
secs = []
def sec(title, items):
    out = []
    for src, label in items:
        if not src or not os.path.exists(src): continue
        dst = os.path.join(OUT, os.path.basename(src))
        if os.path.abspath(src) != os.path.abspath(dst): shutil.copy2(src, dst)
        out.append((os.path.basename(src), label, size(dst)))
    if out: secs.append((title, out))
P = os.path.join(F1, "cad", "out", "print")
vid = os.path.join(ROOT, "video")
sec("Video", [(os.path.join(vid, "sc02_4k.mp4"), "SC-02 · 4K (3840×2160, 60 fps)"), (os.path.join(vid, "sc02_1080p.mp4"), "SC-02 · 1080p"), (os.path.join(vid, "sc02_assemblage_1080p.mp4"), "SC-02 · assemblage-animatie")])
sec("Lasersnijden", [(os.path.join(F1, "cad", "out", "floor_2mm_acrylic.dxf"), "Vloer · 2 mm zwart plexi (DXF)"),
                     (os.path.join(F1, "cad", "out", "floor_2mm_acrylic.svg"), "Vloer · SVG-voorbeeld"),
                     (os.path.join(F1, "cad", "out", "cnc_pinion_m0.8_10T.dxf"), "CNC · motortandwiel 10T m0,8 (POM 4 mm)"),
                     (os.path.join(F1, "cad", "out", "cnc_spur_m0.8_35T.dxf"), "CNC · astandwiel 35T m0,8 (POM 4 mm)")])
sec("3D-printen · Bambu P1S", [(os.path.join(P, f), f[:-4].replace("_", " ")) for f in sorted(os.listdir(P)) if f.endswith(".3mf")] if os.path.isdir(P) else [])
sec("Bestanden", [(zipdir("sc02_printen_PLA_TPU.zip", os.path.join(ROOT, "PRINTEN_PLA_TPU"), (".stl", ".md")), "Printen · alle STL (PLA + TPU)"),
                  (zipdir("sc02_P1S_STEP.zip", os.path.join(F1, "P1S_STEP")), "STEP per P1S-plaat + per onderdeel + 3mf (zip)"),
                  (zipdir("sc02_stl.zip", os.path.join(F1, "cad", "out", "stl"), (".stl",)), "Alle STL (zip)"),
                  (zipdir("sc02_firmware_esp32s3.zip", os.path.join(F1, "firmware")), "ESP32-S3 firmware"),
                  (zipdir("sc02_pi4.zip", os.path.join(F1, "pi")), "Raspberry Pi 4 software"),
                  (os.path.join(F1, "docs", "wiring_sc02.png"), "Elektrisch schema"),
                  (os.path.join(F1, "README.md"), "Bouwhandleiding SC-02"),
                  (os.path.join(F1, "docs", "boodschappenlijst.md"), "Boodschappenlijst")])
rows = "".join(f"<h2>{html.escape(t)}</h2>" + "".join(f'<a href="{html.escape(f)}" download><span>{html.escape(l)}</span><small>{s}</small></a>' for f, l, s in it) for t, it in secs)
open(os.path.join(OUT, "index.html"), "w").write(f"""<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SC-02 · downloads</title><style>body{{margin:0;background:#07090d;color:#eef1f6;font:14px system-ui}}main{{max-width:640px;margin:auto;padding:32px 16px}}
h1{{font:200 30px system-ui;letter-spacing:.3em}}h1 b{{color:#ff2d3c;font-weight:400}}h2{{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#8a93a3;margin:28px 0 8px}}
a{{display:flex;justify-content:space-between;padding:12px 14px;margin:6px 0;border:1px solid rgba(255,255,255,.08);border-radius:12px;color:#eef1f6;text-decoration:none;background:rgba(255,255,255,.03)}}
a:hover{{background:rgba(255,255,255,.07)}}small{{color:#8a93a3}}</style></head><body><main><h1>SC<b>·</b>02</h1>{rows}
<p style="margin-top:32px"><a href="../"><span>← simulatie</span><small></small></a></p></main></body></html>""")
print(sum(len(i) for _, i in secs), "files")
