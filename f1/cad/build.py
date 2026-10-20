#!/usr/bin/env python3
"""Builds SC-02: printable STLs (print orientation), floor DXF (laser), assembly GLB for the web sim, checks + mass."""
import json, math, os, sys, time
import numpy as np, trimesh
import cadquery as cq
from p import *
import body as BD
import car as C
import mf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); STL = os.path.join(OUT, "stl"); os.makedirs(STL, exist_ok=True)
WEB = os.path.join(os.path.dirname(HERE), "web", "models"); os.makedirs(WEB, exist_ok=True)
T0 = time.time()
def log(*a): print(f"[{time.time() - T0:5.1f}s]", *a, flush=True)

def tm(wp, tol=0.03, ang=0.12):
    return mf.to_mesh(wp, tol, ang)

# ---------------------------------------------------------------- build everything (car coordinates)
log("body")
BODY_CUTS = [
    C.cyl_y(3.4, 0, AXLE_RZ, -64, 64), C.box(-3.4, 3.4, -64, 64, 0, AXLE_RZ),          # rear axle + spacer through the liners (slot open downward)
    *[C.box(C.PYLON_X[0] - 0.4, C.PYLON_X[1] + 0.4, yp - 1.6, yp + 1.6, 0, 80) for yp in C.PYLON_Y],   # wing pylon slots
    *[C.box(216, 248, s * 46 - 7, s * 46 + 7, 0, 14.0) for s in (1, -1)],             # front lower arms + tie rods into the arches
]
body_m, body_outer = BD.shell(extra_cuts=BODY_CUTS)
# magnet bosses inside the body (match the floor clips)
bosses = None
for (x, yi, yo) in C.BODY_CLIPS:
    for s in (1, -1):
        yw = BD.bottom_halfwidth(x) + 8                                              # run out to the side wall (trimmed by the skin below)
        b = C.box(x - 4, x + 4, min(s * yi, s * yw), max(s * yi, s * yw), C.CLIP_Z + 0.2, C.CLIP_Z + 5.5)
        b = b.cut(C.cyl_z(3.1, x, s * (yi + yo) / 2, C.CLIP_Z, C.CLIP_Z + 3.4))
        bosses = b if bosses is None else bosses.union(b)
outer_m = body_outer
body_m = body_m + (mf.M(bosses) ^ outer_m)
assert len(body_m.decompose()) == 1, "magnet bosses not attached to the body"
log("body done", round(mf.vol(body_m), 1), "cm3")

P = {}
P["rear_module"] = C.rear_module(); P["motor_clamp"] = C.motor_clamp()
P["rear_bearing_L"] = C.rear_bearing_block(True); P["rear_bearing_R"] = C.rear_bearing_block(False)
P["bearing_cap_L"] = C.bearing_cap(True); P["bearing_cap_R"] = C.bearing_cap(False); P["wheel_spacer"] = C.wheel_spacer()
P["front_module"] = C.front_module()
P["front_upright_L"] = C.front_upright(True); P["front_upright_R"] = C.front_upright(False)
P["tie_rod_L"] = C.tie_rod(True); P["tie_rod_R"] = C.tie_rod(False)
P["steering_horn"] = C.steering_horn()
P["splitter"] = C.splitter(); P["rear_wing"] = C.rear_wing(); P["diffuser"] = C.diffuser()
CANOPY_M = BD.canopy_manifold()
P["pcb_posts"] = C.pcb_posts(); P["battery_tray"] = C.battery_tray(); P["esc_tray"] = C.esc_tray()
for i, (x, yi, yo) in enumerate(C.BODY_CLIPS):
    P[f"clip_{i}L"] = C.body_clip(x, yi, yo, 1); P[f"clip_{i}R"] = C.body_clip(x, yi, yo, -1)
P["spur"] = C.spur(); P["pinion"] = C.pinion()
log("parts")
RIM = {"R": C.rim(REAR_D, REAR_W, False), "F": C.rim(FRONT_D, FRONT_W, True)}
TYRE = {"R": C.tyre(REAR_D, REAR_W), "F": C.tyre(FRONT_D, FRONT_W)}
TYRE = {k: TYRE[k].cut(RIM[k]) for k in TYRE}                                # tyre hugs the rim exactly (no overlap)
log("wheels")
P["floor"] = C.floor_solid()
for (x, y, d) in C.FLOOR_HOLES:
    P["floor"] = P["floor"].cut(C.cyl_z(d / 2, x, y, 0, 20)).cut(
        cq.Workplane("XY").add(cq.Solid.makeCone(3.2, d / 2, 1.6, C.V(x, y, FLOOR_Z - 0.01), C.V(0, 0, 1))))
for (x, y) in ((100, -47),):                                                   # power switch from below
    P["floor"] = P["floor"].cut(C.cyl_z(3.1, x, y, 0, 20))
for i in range(4):                                                              # ESC heatsink cooling slots
    P["floor"] = P["floor"].cut(C.rbox(C.ESC_X[0] + 6 + i * 6, C.ESC_X[0] + 9 + i * 6, C.ESC_Y[0] + 6, C.ESC_Y[1] - 6, 0, 20, 1.4))
log("floor")
B = C.bought()
import real_parts as RP
MOTREAL = {}
for k, v in RP.motor_2435(C.CD, AXLE_RZ, C.MOT_FACE_Y).items():                 # one 2435 brushless (tag F kept for the web)
    MOTREAL[f"motor_F_{k}" if k != "pinion" else "pinion_F"] = v

def place_wheel(w, x, y, W, outer_left):
    """local wheel: axis +Z, z=0 = outer (cover) face. Put the cover facing outward."""
    if outer_left:      # left wheel: outer face toward +y
        return w.rotate((0, 0, 0), (1, 0, 0), -90).translate((x, y + W / 2, 0))
    return w.rotate((0, 0, 0), (1, 0, 0), 90).translate((x, y - W / 2, 0))

WHEELS = {}
for tag, x, D, W, tr in (("R", 0.0, REAR_D, REAR_W, TRACK_R), ("F", WB, FRONT_D, FRONT_W, TRACK_F)):
    for s, side in ((1, "L"), (-1, "R")):
        yc = s * tr / 2
        WHEELS[f"rim_{tag}{side}"] = place_wheel(RIM[tag], x, yc, W, s > 0).translate((0, 0, D / 2))
        WHEELS[f"tyre_{tag}{side}"] = place_wheel(TYRE[tag], x, yc, W, s > 0).translate((0, 0, D / 2))
log("placed")

# ---------------------------------------------------------------- export STL in print orientation + DXF
def stl(name, wp, flip=False, rot=None):
    m = tm(wp) if not isinstance(wp, trimesh.Trimesh) else wp
    if flip: m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    if rot is not None: m.apply_transform(rot)
    m.apply_translation(-m.bounds[0])
    m.export(os.path.join(STL, name + ".stl"))
    return m

body_tm = mf.to_trimesh(body_m)
# split the body for the 256 mm bed: main (x <= 206) and nose (x > 206)
cut_x = 150.0   # seam under the canopy edge; both halves fit the 256 mm bed
main_body = body_m ^ mf.M(C.box(-80, cut_x, -100, 100, -10, 120))
nose_body = body_m ^ mf.M(C.box(cut_x, 400, -100, 100, -10, 120))
stl("body_main", mf.to_trimesh(main_body))
stl("body_nose", mf.to_trimesh(nose_body))
stl("canopy", mf.to_trimesh(CANOPY_M))
FLIP = {"motor_clamp"}
for k, wp in P.items():
    if k in ("floor",): continue
    stl(k, wp, flip=k in FLIP)
stl("rim_rear", RIM["R"]); stl("rim_front", RIM["F"]); stl("tyre_rear", TYRE["R"]); stl("tyre_front", TYRE["F"])
log("stl")
# floor DXF for the laser cutter (section through the plate)
sec = P["floor"].section(FLOOR_Z + FLOOR_T / 2)
cq.exporters.export(sec, os.path.join(OUT, "floor_2mm_acrylic.dxf"))
cq.exporters.export(sec, os.path.join(OUT, "floor_2mm_acrylic.svg"), opt={"showAxes": False, "projectionDir": (0, 0, 1), "strokeWidth": 0.3,
                                                                           "width": 1600, "height": 900, "showHidden": False})
# gear profiles for the CNC (2D, mm): pinion + spur, cut from 4 mm POM / aluminium
from gears import spur_gear
for nm, (z, bore) in {"cnc_pinion_m0.8_%dT" % PINION_Z: (PINION_Z, 1.95), "cnc_spur_m0.8_%dT" % SPUR_Z: (SPUR_Z, PRESS_BORE)}.items():
    g, _ = spur_gear(MODULE, z, GEAR_W, bore)
    cq.exporters.export(g.section(GEAR_W / 2), os.path.join(OUT, nm + ".dxf"))
log("dxf")

# ---------------------------------------------------------------- mold
if "--nomold" not in sys.argv:
    mb, mt, cores = C.mold_parts()
    stl("mold_bottom", mb); stl("mold_top", mt, flip=True)
    for i, c in enumerate(cores[::2]):
        stl(f"mold_core_{'rear' if i == 0 else 'front'}", c)
    MOLD = dict(bottom=mb, top=mt, cores=cores)
    log("mold")

# ---------------------------------------------------------------- checks
def overlap(a, b):
    try: return a.intersect(b).val().Volume()
    except Exception: return -1
pairs = [("rear_module", "rear_bearing_L"), ("rear_module", "pcb_posts"), ("rear_module", "motor_clamp"), ("battery_tray", "pcb_posts"),
         ("esc_tray", "pcb_posts"), ("front_module", "front_upright_L"), ("rear_module", "spur"), ("floor", "spur"), ("motor_clamp", "spur"), ("rear_bearing_L", "spur"), ("rear_bearing_R", "spur")]
for a, b in pairs:
    v = overlap(P[a], P[b])
    if v > 1: log(f"OVERLAP {a} x {b}: {v:.1f} mm3")
# body vs everything inside (mesh)
for k in ("rear_module", "motor_clamp", "pcb_posts", "battery_tray", "esc_tray", "front_module"):
    v = (body_m ^ mf.M(P[k])).volume()
    if v > 2: log(f"BODY OVERLAP {k}: {v:.1f} mm3")
for k in [k for k in B if k not in ("panel", "axle_rear")]:
    v = (body_m ^ mf.M(B[k])).volume()
    if v > 2: log(f"BODY OVERLAP bought {k}: {v:.1f} mm3")
for k in ("rim_RL", "tyre_RL", "rim_FL", "tyre_FL"):
    v = (body_m ^ mf.M(WHEELS[k])).volume()
    if v > 0.5: log(f"BODY x WHEEL {k}: {v:.1f}")
# steering clearance: front wheel + upright swept to +-20 deg about the kingpin must not touch the body
for side, sgn in (("L", 1), ("R", -1)):
    for ang in (-20, -10, 10, 20):
        w = WHEELS[f"tyre_F{side}"].union(WHEELS[f"rim_F{side}"]).union(P[f"front_upright_{side}"])
        w = w.rotate((WB, sgn * KINGPIN_Y, 0), (WB, sgn * KINGPIN_Y, 1), ang)
        v = (body_m ^ mf.M(w)).volume()
        if v > 0.5: log(f"STEER CLASH {side} {ang} deg: {v:.1f} mm3")
# every part against every other part (printed + bought + wheels): nothing may overlap except the intended press fits
ALL = {"body": body_m, "canopy": CANOPY_M}
for k, v in P.items():
    if k not in ("pinion",): ALL[k] = mf.M(v)
for k in B: ALL[k] = mf.M(B[k])
ALL["motor"] = mf.M(MOTREAL["motor_F_can"].union(MOTREAL["motor_F_cap"]).union(MOTREAL["motor_F_term"]))
ALL["motor_shaft"] = mf.M(MOTREAL["motor_F_shaft"]); ALL["pinion_F"] = mf.M(MOTREAL["pinion_F"])
for k, v in WHEELS.items(): ALL[k] = mf.M(v)
for k in [k for k in P if k.startswith("clip_")]: ALL[k] = mf.M(P[k])
PRESS = {frozenset(p) for p in [("axle_rear", "spur"), ("axle_rear", "rear_bearing_L"), ("axle_rear", "rear_bearing_R"), ("axle_rear", "wheel_spacer"),
                                ("axle_rear", "rim_RL"), ("axle_rear", "rim_RR"), ("axle_rear", "body"),
                                ("motor_shaft", "motor"), ("pcb", "pcb_xt60"), ("pcb", "pcb_hdr_esc"), ("pcb", "pcb_hdr_hall")]}
import itertools
bad = 0
for (a, ma), (b2, mb) in itertools.combinations(ALL.items(), 2):
    if frozenset((a, b2)) in PRESS: continue
    v = (ma ^ mb).volume()
    if v > 3.0:                                         # < 3 mm3 = faces that just touch (mesh round-off)
        bad += 1; log(f"INTERFERENCE {a} x {b2}: {v:.1f} mm3")
log("interference pairs:", bad)
log("checks done")

# ---------------------------------------------------------------- mass
dens = dict(ASA=1.07, PLA=1.24, PETG=1.27, ACRYLIC=1.19, RUBBER=1.15)
mass = {}
mass["body (ASA)"] = mf.vol(body_m) * dens["ASA"]
mass["canopy (smoke PETG)"] = mf.vol(CANOPY_M) * dens["PETG"]
for k, mat in (("rear_module", "ASA"), ("front_module", "ASA"), ("splitter", "ASA"), ("rear_wing", "ASA"), ("diffuser", "ASA"),
               ("pcb_posts", "ASA"), ("battery_tray", "ASA"), ("esc_tray", "ASA")):
    mass[k] = P[k].val().Volume() / 1000 * dens[mat] * 0.9
mass["uprights+clips+small"] = sum(P[k].val().Volume() for k in P if k.startswith(("rear_bearing", "bearing_cap", "wheel_spacer", "front_upright", "clip_", "tie_rod", "steering", "motor_clamp", "spur"))) / 1000 * 1.1
mass["floor (2 mm acrylic)"] = P["floor"].val().Volume() / 1000 * dens["ACRYLIC"]
mass["4 rims (PLA)"] = 2 * (RIM["R"].val().Volume() + RIM["F"].val().Volume()) / 1000 * dens["PLA"] * 0.9
mass["4 tyres (PU/silicone)"] = 2 * (TYRE["R"].val().Volume() + TYRE["F"].val().Volume()) / 1000 * dens["RUBBER"]
BOUGHT = {"kit panel": 25, "drive PCB v3 (S3 + ELRS)": 22, "servo MG90S": 14, "2435 brushless 4500 kV": 60, "ESC 35 A": 26,
          "LiPo 2S 1000 mAh": 62, "wires, screws, bearings, axles, magnets": 28}
mass.update(BOUGHT)
total = sum(mass.values())
json.dump(dict(parts={k: round(v, 1) for k, v in mass.items()}, total_g=round(total, 1),
               length=round(body_tm.bounds[1][0] - min(-55, body_tm.bounds[0][0]), 1), width=TRACK_R + REAR_W,
               floor_holes=len(C.FLOOR_HOLES)), open(os.path.join(OUT, "mass.json"), "w"), indent=1)
log(f"TOTAL {total:.0f} g")

# ---------------------------------------------------------------- GLB for the web (named nodes, mm, z-up)
if "--noweb" not in sys.argv:
    scene = trimesh.Scene()
    def add(name, obj, color, rough=0.5, metal=0.0, tol=0.04):
        m = obj if isinstance(obj, trimesh.Trimesh) else tm(obj, tol, 0.15)
        m = m.copy()
        m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[*color, 1.0], roughnessFactor=rough, metallicFactor=metal))
        scene.add_geometry(m, node_name=name, geom_name=name)
    add("body", mf.to_trimesh(body_m), (0.75, 0.02, 0.04), 0.25)
    add("canopy", mf.to_trimesh(CANOPY_M), (0.01, 0.012, 0.018), 0.04, 0.2)
    add("splitter", P["splitter"], (0.05, 0.05, 0.055), 0.35); add("rear_wing", P["rear_wing"], (0.05, 0.05, 0.055), 0.35)
    add("diffuser", P["diffuser"], (0.06, 0.06, 0.07), 0.6)
    add("floor", P["floor"], (0.03, 0.03, 0.035), 0.15)
    for k in ("rear_module", "motor_clamp", "front_module", "pcb_posts", "battery_tray", "esc_tray"):
        add(k, P[k], (0.2, 0.21, 0.23), 0.6)
    for k in P:
        if k.startswith("clip_"): add(k, P[k], (0.2, 0.21, 0.23), 0.6)
    for k in ("rear_bearing_L", "rear_bearing_R", "bearing_cap_L", "bearing_cap_R", "front_upright_L", "front_upright_R"):
        add(k, P[k], (0.09, 0.09, 0.1), 0.45, 0.2)
    for k in ("tie_rod_L", "tie_rod_R", "steering_horn"):
        add(k, P[k], (0.5, 0.5, 0.52), 0.3, 0.8)
    add("spur", P["spur"], (0.9, 0.9, 0.88), 0.5)
    add("panel", B["panel"], (0.04, 0.07, 0.22), 0.1, 0.3)
    add("battery", B["battery"], (0.1, 0.1, 0.12), 0.5); add("pcb", B["pcb"], (0.02, 0.09, 0.05), 0.35)
    add("esc", B["esc"], (0.08, 0.22, 0.6), 0.45)
    for k in [k for k in B if k.startswith("pcb_")]:
        add(k, B[k], (0.75, 0.76, 0.78) if k in ("pcb_esp32s3", "pcb_elrs_c3", "pcb_usbc") else (0.85, 0.75, 0.2) if k == "pcb_xt60"
            else (0.12, 0.12, 0.13), 0.3, 0.8 if k in ("pcb_esp32s3", "pcb_elrs_c3", "pcb_usbc") else 0.0)
    add("servo", B["servo"], (0.1, 0.25, 0.75), 0.5)
    for k, v in MOTREAL.items():
        mat = {"can": ((0.78, 0.79, 0.82), 0.22, 1.0), "cap": ((0.04, 0.04, 0.045), 0.55, 0.0), "term": ((0.8, 0.62, 0.28), 0.3, 1.0),
               "shaft": ((0.8, 0.81, 0.84), 0.15, 1.0)}.get(k.split("_")[-1], ((0.8, 0.62, 0.28), 0.3, 1.0))
        add(k, v, *mat, tol=0.015)
    add("axle_rear", B["axle_rear"], (0.1, 0.1, 0.1), 0.4)
    for k, w in WHEELS.items():
        if k.startswith("rim"): add(k, w, (0.12, 0.12, 0.13), 0.35, 0.6)
        else: add(k, w, (0.035, 0.035, 0.04), 0.88)
    scene.export(os.path.join(WEB, "sc02.glb"))
    if "--nomold" not in sys.argv:
        ms = trimesh.Scene()
        def madd(name, obj, color, rough=0.5, op=1.0):
            m = tm(obj, 0.04, 0.15)
            m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
                baseColorFactor=[*color, op], roughnessFactor=rough, alphaMode="BLEND" if op < 1 else "OPAQUE"))
            ms.add_geometry(m, node_name=name, geom_name=name)
        madd("mold_bottom", MOLD["bottom"], (0.86, 0.87, 0.9), 0.35)
        madd("mold_top", MOLD["top"], (0.86, 0.87, 0.9), 0.35)
        for i, c in enumerate(MOLD["cores"]): madd(f"core_{i}", c, (0.95, 0.55, 0.12), 0.4)
        for i, (tag, D, W, cx, cy) in enumerate([("R", REAR_D, REAR_W, -34, -34), ("R", REAR_D, REAR_W, 34, -34),
                                                  ("F", FRONT_D, FRONT_W, -34, 34), ("F", FRONT_D, FRONT_W, 34, 34)]):
            madd(f"tyre_{i}", TYRE[tag].translate((cx, cy, 13.0 - W / 2)), (0.04, 0.04, 0.045), 0.85)
        ms.export(os.path.join(WEB, "mold2.glb"))
    json.dump(dict(wb=WB, axle_rz=AXLE_RZ, axle_fz=AXLE_FZ, track_r=TRACK_R, track_f=TRACK_F, rear_d=REAR_D, front_d=FRONT_D,
                   kingpin_y=KINGPIN_Y, servo_x=SERVO_X, cd=C.CD, spur_z=SPUR_Z, pinion_z=PINION_Z, tie_in=C.TIE_IN,
                   arm_end=(WB - 10.5, KINGPIN_Y - 6.0), mass=mass, total_g=total), open(os.path.join(WEB, "sc02.json"), "w"), indent=1)
    log("glb")

# ---------------------------------------------------------------- STEP: real CAD solids, one file per P1S plate + every part
if "--nostep" not in sys.argv:
    from plates import PLATES
    STEP = os.path.join(OUT, "step"); os.makedirs(os.path.join(STEP, "onderdelen"), exist_ok=True)
    body_b = BD.shell_brep(BODY_CUTS, [bosses])
    BR = {k: v for k, v in P.items() if k != "floor"}
    BR["body_main"] = body_b.intersect(C.box(-80, cut_x, -100, 100, -10, 120))
    BR["body_nose"] = body_b.intersect(C.box(cut_x, 400, -100, 100, -10, 120))
    BR["canopy"] = BD.canopy_brep()
    BR.update(rim_rear=RIM["R"], rim_front=RIM["F"], tyre_rear=TYRE["R"], tyre_front=TYRE["F"])
    if "--nomold" not in sys.argv:
        BR.update(mold_bottom=MOLD["bottom"], mold_top=MOLD["top"], mold_core_rear=MOLD["cores"][0], mold_core_front=MOLD["cores"][2])
    FLIPS = FLIP | {"mold_top"}
    def oriented(k, rx=0, ry=0):
        s = BR[k].val()
        if k in FLIPS: s = s.rotate(C.V(0, 0, 0), C.V(1, 0, 0), 180)
        if rx: s = s.rotate(C.V(0, 0, 0), C.V(1, 0, 0), rx)
        if ry: s = s.rotate(C.V(0, 0, 0), C.V(0, 1, 0), ry)
        bb = s.BoundingBox()
        return s.translate(C.V(-bb.xmin, -bb.ymin, -bb.zmin)), bb
    for k in BR:
        cq.exporters.export(cq.Workplane("XY").add(oriented(k)[0]), os.path.join(STEP, "onderdelen", k + ".step"))
    BED, GAP = 255.0, 4.0
    for name, (fil, proc, items) in PLATES.items():
        sol = [(k, *oriented(k, rx, ry)) for (k, rx, ry) in items if k in BR]
        import rectpack                                                   # MaxRects packing on the 256 x 256 bed
        pk = rectpack.newPacker(rotation=True); pk.add_bin(BED, BED)
        for i, (k, s, bb) in enumerate(sol):
            pk.add_rect(bb.xlen + GAP, bb.ylen + GAP, rid=i)
        pk.pack()
        placed = pk.rect_list()
        assert len(placed) == len(sol), f"{name}: only {len(placed)}/{len(sol)} parts fit"
        asm = cq.Assembly(name=name)
        for (_, x, y, w, h, i) in placed:
            k, s, bb = sol[i]
            if abs(w - (bb.xlen + GAP)) > 1e-6 or (abs(h - (bb.ylen + GAP)) > 1e-6):     # rotated 90 deg about z
                s = s.rotate(C.V(0, 0, 0), C.V(0, 0, 1), 90).translate(C.V(bb.ylen, 0, 0))
            asm.add(s.translate(C.V(x + GAP / 2, y + GAP / 2, 0)), name=f"{k}_{i}")
        asm.save(os.path.join(STEP, name + ".step"))
        log("step", name, len(sol), "parts")
