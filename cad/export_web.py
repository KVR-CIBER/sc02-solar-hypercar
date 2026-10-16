#!/usr/bin/env python3
"""Exports the car + tyre mold as GLB (named parts) + parts.json for the web simulation (../web/models)."""
import json, math, os
import cadquery as cq
import build as B
from params import *
from gears import spur_gear

OUT = os.path.join(os.path.dirname(B.HERE), "web", "models")
os.makedirs(OUT, exist_ok=True)
C = cq.Color

def bearing(x, side):
    y_out = side * PLATE_HALF_W
    r = cq.Workplane("XY").add(cq.Solid.makeCylinder(BRG_OD / 2, BRG_W, cq.Vector(x, y_out - side * BRG_W if side > 0 else y_out, AXLE_Z), cq.Vector(0, 1, 0)))
    return r.cut(B.cyl_y(BRG_ID / 2 + 0.6, x, AXLE_Z, -80, 80))

def car():
    a = cq.Assembly(name="car")
    meta = []
    def add(name, wp, color, label, material, group="static", mass=None):
        a.add(wp, name=name, color=C(*color))
        meta.append(dict(name=name, label=label, material=material, group=group, mass_g=mass))
    ASA, PLA = 1.07, 1.24
    vol = lambda wp: wp.val().Volume() / 1000
    blue, orange, white = (0.12, 0.38, 0.85, 1), (0.95, 0.52, 0.12, 1), (0.93, 0.93, 0.9, 1)
    add("chassis", B.chassis(), blue, "Chassis", "ASA geprint", mass=round(vol(B.chassis()) * ASA * 0.9, 1))
    add("front_carrier", B.front_carrier(), blue, "Voorasdrager (uitlijnbaar)", "ASA geprint",
        mass=round(vol(B.front_carrier()) * ASA * 0.9, 1))
    add("motor_clamp", B.motor_clamp(), orange, "Motorklem", "ASA geprint", mass=round(vol(B.motor_clamp()) * ASA * 0.9, 1))
    cap = B.bearing_cap()
    for xc, tag in ((0, "R"), (WHEELBASE, "F")):
        add(f"cap_{tag}L", cap.translate((xc, 0, 0)), orange, "Lagerkap", "ASA geprint", mass=0.3)
        add(f"cap_{tag}R", B.mirror_y(cap.translate((xc, 0, 0))), orange, "Lagerkap", "ASA geprint", mass=0.3)
    add("panel_frame", B.panel_frame(), orange, "Paneelframe", "ASA geprint", mass=round(vol(B.panel_frame()) * ASA * 0.9, 1))
    bp = B.bought_parts()
    add("panel", bp["panel"], (0.05, 0.09, 0.3, 1), "Zonnepaneel (kit) 90×80", "kit", mass=25)
    add("battery_holders", bp["battery_holders"], (0.13, 0.13, 0.14, 1), "Batterijhouders (kit)", "kit", mass=16)
    add("cells", bp["cells"], (0.1, 0.62, 0.32, 1), "4× AA NiMH 2000 mAh", "kit", mass=108)
    add("esp32s3", bp["esp32s3"], (0.05, 0.33, 0.15, 1), "ESP32-S3 + boost", "elektronica", mass=14)
    add("power", bp["power"], (0.62, 0.1, 0.1, 1), "MOSFET-module, zekering, schakelaar", "elektronica", mass=14)
    for s, tag in ((1, "L"), (-1, "R")):
        cx = B.CENTRE_DIST if s > 0 else -B.CENTRE_DIST
        mot = B.cyl_y(MOT_W / 2, cx, AXLE_Z, B.MOT_FACE_Y, B.MOT_FACE_Y + MOT_L).intersect(
            B.box(cx - MOT_T / 2, cx + MOT_T / 2, B.MOT_FACE_Y, B.MOT_FACE_Y + MOT_L, 0, 60))
        mot = mot.union(B.cyl_y(MOT_BOSS_D / 2, cx, AXLE_Z, B.MOT_FACE_Y - 1.5, B.MOT_FACE_Y))
        add(f"motor_{'F' if s > 0 else 'B'}", mot, (0.78, 0.78, 0.8, 1), "Tamiya Hyper-Dash 3", "gekocht", mass=19)
        pin, _ = spur_gear(MODULE, PINION_Z, GEAR_W, 2.0)
        pin = pin.union(cq.Workplane("XY").circle(1.0).extrude(MOT_SHAFT_L))
        pin = pin.rotate((0, 0, 0), (0, 0, 1), 180 / PINION_Z).rotate((0, 0, 0), (1, 0, 0), 90) \
                 .translate((cx, SPUR_Y + GEAR_W / 2, AXLE_Z))
        add(f"pinion_{'F' if s > 0 else 'B'}", pin, (0.85, 0.68, 0.25, 1), "Pinion 8T m0.5 (messing)", "gekocht",
            group=f"pinion@{cx:.3f}", mass=0.5)
    sp, _ = spur_gear(MODULE, SPUR_Z, GEAR_W, PRESS_BORE, hub_d=7.0, hub_len=2.0, web_holes=6)
    add("spur", sp.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, SPUR_Y + GEAR_W / 2, AXLE_Z)), white,
        "Tandwiel 42T m0.5", "PLA geprint", group="rear", mass=1.3)
    for x, tag in ((0, "rear"), (WHEELBASE, "front")):
        add(f"axle_{tag}", B.cyl_y(AXLE_D / 2, x, AXLE_Z, -(TRACK + TYRE_W) / 2 - 0.5, (TRACK + TYRE_W) / 2 + 0.5),
            (0.08, 0.08, 0.09, 1), "As Ø3 carbon", "gekocht", group=tag, mass=1.5)
        for side, st in ((1, "L"), (-1, "R")):
            add(f"bearing_{tag}{st}", bearing(x, side), (0.7, 0.72, 0.75, 1), "Kogellager 683ZZ", "gekocht", mass=0.6)
            add(f"rim_{tag}{st}", B.place_wheel(B.rim("dovetail"), x, side), orange, "Velg", "PLA geprint", group=tag, mass=3.9)
            add(f"tyre_{tag}{st}", B.place_wheel(B.tyre_silicone_ref(), x, side), (0.07, 0.07, 0.075, 1),
                "Siliconen band (gegoten)", "siliconen Shore 25", group=tag, mass=3.0)
    return a, meta

def mold():
    a = cq.Assembly(name="mold")
    meta = []
    a.add(B.mold_base(), name="mold_base", color=C(0.85, 0.86, 0.9, 1))
    a.add(B.mold_lid(), name="mold_lid", color=C(0.55, 0.7, 0.95, 0.6))
    meta += [dict(name="mold_base", label="Malbasis (4 holtes)"), dict(name="mold_lid", label="Deksel met ontluchting")]
    for i, (cx, cy) in enumerate(B.CAVS):
        a.add(B.rim("dovetail").translate((cx, cy, B.MOLD_FLOOR)), name=f"mrim_{i}", color=C(0.95, 0.52, 0.12, 1))
        ring = B.cyl_z(WHEEL_D / 2 - 0.02, cx, cy, B.MOLD_FLOOR + 0.02, B.MOLD_FLOOR + TYRE_W - 0.02).cut(
            B.rim("dovetail").translate((cx, cy, B.MOLD_FLOOR))).cut(B.cyl_z(SEAT_D / 2 - 1.0, cx, cy, 0, 40))
        a.add(ring, name=f"silicone_{i}", color=C(0.1, 0.1, 0.11, 1))
    return a, meta

if __name__ == "__main__":
    a, meta = car()
    a.export(os.path.join(OUT, "car.glb"), tolerance=0.03, angularTolerance=0.12)
    m, mmeta = mold()
    m.export(os.path.join(OUT, "mold.glb"), tolerance=0.04, angularTolerance=0.15)
    info = dict(units="mm, x forward, y left, z up", wheelbase=WHEELBASE, axle_z=AXLE_Z, wheel_d=WHEEL_D,
                track=TRACK, pinion_z=PINION_Z, spur_z=SPUR_Z, centre_dist=B.CENTRE_DIST,
                mold=dict(floor=B.MOLD_FLOOR, tyre_w=TYRE_W, cavities=B.CAVS), parts=meta, mold_parts=mmeta)
    json.dump(info, open(os.path.join(OUT, "parts.json"), "w"), indent=1)
    for f in ("car.glb", "mold.glb"):
        print(f, round(os.path.getsize(os.path.join(OUT, f)) / 1e6, 2), "MB")
