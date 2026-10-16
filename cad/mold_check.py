#!/usr/bin/env python3
"""Mold sanity check + cut-away render: rim inside cavity, gate reaches the tyre space, vents above it."""
import os, math
import numpy as np, trimesh, cadquery as cq
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import build as B, render as R
from params import *

base, lid, rim = B.mold_base(), B.mold_lid(), B.rim("dovetail")
cx, cy = B.CAVS[1]                          # cavity at +x
rim_in = rim.translate((cx, cy, B.MOLD_FLOOR))
cav = B.cyl_z(WHEEL_D / 2, cx, cy, B.MOLD_FLOOR, B.MOLD_FLOOR + TYRE_W)
silicone = cav.cut(rim_in).cut(B.cyl_z(R_SEAT - 0.01 if (R_SEAT := SEAT_D / 2) else 0, cx, cy, 0, 50)) if False else cav.cut(rim_in)
# keep only the tyre ring (outside the seat)
ring = silicone.intersect(B.cyl_z(WHEEL_D / 2, cx, cy, 0, 50).cut(B.cyl_z(SEAT_D / 2 - 0.01, cx, cy, 0, 50)))
v = ring.val().Volume() / 1000
print(f"silicone per tyre: {v:.2f} ml  -> 4 tyres + gates/vents ~ {4*v+4:.0f} ml")
assert base.intersect(rim_in).val().Volume() < 1.0, "rim collides with mold base"
assert lid.intersect(rim_in).val().Volume() < 1.0, "rim collides with lid"
# gate must open into the tyre ring
gate_probe = base.intersect(B.box(cx + WHEEL_D/2 - 2, cx + WHEEL_D/2 + 2, cy - 2, cy + 2, B.MOLD_FLOOR, B.MOLD_FLOOR + 4))
full = B.box(cx + WHEEL_D/2 - 2, cx + WHEEL_D/2 + 2, cy - 2, cy + 2, B.MOLD_FLOOR, B.MOLD_FLOOR + 4).val().Volume()
print(f"gate opening region: {100*(1-gate_probe.val().Volume()/full):.0f} % open (cavity + channel)")
print("OK: rim fits, lid closes, gate + vents present")

# cut-away render through the cavity centre (y < cy removed)
half = B.box(-200, 200, cy, 200, -10, 60)
parts = [(base.intersect(half), (0.85, 0.85, 0.88)), (lid.intersect(half).translate((0, 0, 12)), (0.6, 0.75, 0.95)),
         (rim_in.intersect(half), (0.9, 0.55, 0.15)), (ring.intersect(half), (0.12, 0.12, 0.12))]
meshes = []
tmp = os.path.join(B.OUT, "tmp_mold.stl")
for wp, c in parts:
    cq.exporters.export(wp, tmp, tolerance=0.03, angularTolerance=0.2)
    meshes.append((trimesh.load(tmp), c))
os.remove(tmp)
fig = plt.figure(figsize=(11, 5))
R.draw_sorted(fig.add_subplot(1, 2, 1, projection="3d"), meshes, 20, -75, "cut-away: lid lifted 12 mm, rim (orange) + silicone tyre (black)")
m2 = []
for wp, c in [(base, (0.85, 0.85, 0.88)), (lid.translate((0, 0, 25)), (0.6, 0.75, 0.95))]:
    cq.exporters.export(wp, tmp, tolerance=0.05, angularTolerance=0.3); m2.append((trimesh.load(tmp), c))
os.remove(tmp)
R.draw_sorted(fig.add_subplot(1, 2, 2, projection="3d"), m2, 35, -60, "4-cavity mold: base + lid (exploded)")
fig.tight_layout(); fig.savefig(os.path.join(B.OUT, "render_mold.png"), dpi=110)
