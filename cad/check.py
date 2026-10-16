#!/usr/bin/env python3
"""Interference check: every pair of parts in the assembly must not overlap (volume > 1 mm^3)."""
import itertools, os, sys
import cadquery as cq
import build as B
from params import *

def placed():
    P = {}
    P["chassis"] = B.chassis(); P["front_carrier"] = B.front_carrier(); P["motor_clamp"] = B.motor_clamp()
    cap = B.bearing_cap()
    for xc in (0, WHEELBASE):
        P[f"cap_{xc}_L"] = cap.translate((xc, 0, 0)); P[f"cap_{xc}_R"] = B.mirror_y(cap.translate((xc, 0, 0)))
    P["panel_frame"] = B.panel_frame()
    sp, _ = B.spur_gear(MODULE, SPUR_Z, GEAR_W, PRESS_BORE, hub_d=7.0, hub_len=2.0, web_holes=6)
    P["spur"] = sp.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, SPUR_Y + GEAR_W / 2, AXLE_Z))
    rim, ty = B.rim("dovetail"), B.tyre_silicone_ref()
    for x in (0, WHEELBASE):
        for s in (1, -1):
            P[f"wheel_{x}_{s}"] = B.place_wheel(rim, x, s).union(B.place_wheel(ty, x, s))
    P.update(B.bought_parts())
    return P

P = placed()
names = list(P)
# intended overlaps: press fits on the axle, 0.1 mm clamp preload on the motors, cells inside their holders
ALLOWED = {("motor_clamp", "motors"), ("spur", "axles"), ("battery_holders", "cells")} | \
          {(k, "axles") for k in P if k.startswith("wheel")}
bad = 0
for a, b in itertools.combinations(names, 2):
    ba, bb = P[a].val().BoundingBox(), P[b].val().BoundingBox()
    if ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin or ba.zmax < bb.zmin or bb.zmax < ba.zmin:
        continue
    v = P[a].intersect(P[b]).val().Volume()
    if v > 1.0 and (a, b) not in ALLOWED:
        bad += 1
        print(f"OVERLAP {a:16s} x {b:16s} {v:8.1f} mm3")
# ground clearance + width
lo = min(p.val().BoundingBox().zmin for k, p in P.items() if not k.startswith("wheel"))
w = max(abs(p.val().BoundingBox().ymin) for p in P.values()), max(p.val().BoundingBox().ymax for p in P.values())
print(f"lowest non-wheel point z={lo:.2f} mm, overall width {sum(w):.1f} mm (rule max 300)")
print("OK, no interferences" if bad == 0 else f"{bad} interferences")
