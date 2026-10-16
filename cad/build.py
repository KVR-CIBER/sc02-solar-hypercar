#!/usr/bin/env python3
"""Builds every printable part (STL + STEP), a full assembly STEP with bought parts,
and the mass / centre-of-gravity report.   Run:  ../.venv/bin/python build.py"""
import json, math, os
import cadquery as cq
from params import *
from gears import spur_gear

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
STL = os.path.join(OUT, "stl")
os.makedirs(STL, exist_ok=True)

# ---------------------------------------------------------------- helpers
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def cyl(r, p, d, h):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, cq.Vector(*p), cq.Vector(*d)))

def cyl_y(r, x, z, y0, y1):
    return cyl(r, (x, y0, z), (0, 1, 0), y1 - y0)

def cyl_z(r, x, y, z0, z1):
    return cyl(r, (x, y, z0), (0, 0, 1), z1 - z0)

def mirror_y(wp):
    return wp.mirror("XZ")

def union_all(parts):
    out = parts[0]
    for p in parts[1:]:
        out = out.union(p)
    return out

# ---------------------------------------------------------------- shared features
BLOCK_TOP = AXLE_Z + 6.0

def bearing_block(xc, left=True, z0=PLATE_Z):
    """Upright with open-top U slot for a 683ZZ bearing, inner lip, two M2 pilot holes for the cap."""
    y_out, y_in = PLATE_HALF_W, PLATE_HALF_W - 4.0
    b = box(xc - 10, xc + 10, y_in, y_out, z0, BLOCK_TOP)
    pocket_y0 = y_out - BRG_W - 0.1
    b = b.cut(cyl_y(BRG_FIT / 2, xc, AXLE_Z, pocket_y0, y_out + 1))
    b = b.cut(box(xc - BRG_FIT / 2, xc + BRG_FIT / 2, pocket_y0, y_out + 1, AXLE_Z, BLOCK_TOP + 1))
    b = b.cut(cyl_y(2.3, xc, AXLE_Z, y_in - 1, y_out + 1))                       # axle clearance in lip
    b = b.cut(box(xc - 2.3, xc + 2.3, y_in - 1, y_out + 1, AXLE_Z, BLOCK_TOP + 1))
    for dx in (-7.0, 7.0):
        b = b.cut(cyl_z(M2_PILOT / 2, xc + dx, (y_in + y_out) / 2, BLOCK_TOP - 8, BLOCK_TOP + 1))
    return b if left else mirror_y(b)

def bearing_cap():
    """Cap that closes the U slot and clamps the bearing (print 4)."""
    y_in, y_out = PLATE_HALF_W - 4.0, PLATE_HALF_W
    c = box(-10, 10, y_in, y_out, BLOCK_TOP, BLOCK_TOP + 2.4)
    tongue = box(-BRG_FIT / 2 + 0.1, BRG_FIT / 2 - 0.1, y_out - BRG_W, y_out, AXLE_Z, BLOCK_TOP)
    tongue = tongue.cut(cyl_y(BRG_OD / 2 - 0.05, 0, AXLE_Z, y_out - BRG_W - 1, y_out + 1))
    lip = box(-2.2, 2.2, y_in, y_out - BRG_W - 0.1, AXLE_Z + 2.0, BLOCK_TOP)
    c = c.union(tongue).union(lip)
    for dx in (-7.0, 7.0):
        c = c.cut(cyl_z(1.15, dx, (y_in + y_out) / 2, BLOCK_TOP - 1, BLOCK_TOP + 3))
    return c

# ---------------------------------------------------------------- chassis
MOT_FACE_Y = SPUR_Y - GEAR_W / 2 + MOT_SHAFT_L       # motor face so the pinion sits centred on the spur
CRADLE_IN = MOT_T / 2 + MOT_FIT / 2                  # half inner width (flats)
CRADLE_R = MOT_W / 2 + MOT_FIT / 2
WALL_OUT, WALL_IN = 3.2, 1.2
CRADLE_TOP = AXLE_Z + MOT_W / 2 + 0.1
CRADLE_Y1 = MOT_FACE_Y + MOT_L + 1.0
CLAMP_SCREW_X = CENTRE_DIST + CRADLE_IN + 1.4 + 2.2     # boss (r 2.4) stays clear of the motor flat
CLAMP_SCREW_Y = (MOT_FACE_Y + 6.0, MOT_FACE_Y + MOT_L - 6.0)

def motor_cradle(cx):
    s = 1 if cx > 0 else -1
    xin, xout = cx - s * (CRADLE_IN + WALL_IN), cx + s * (CRADLE_IN + WALL_OUT)
    c = box(min(xin, xout), max(xin, xout), MOT_FACE_Y - 2.0, CRADLE_Y1, PLATE_Z, CRADLE_TOP)
    # motor profile: circle intersected with the flats, plus straight up
    prof = cyl_y(CRADLE_R, cx, AXLE_Z, MOT_FACE_Y, CRADLE_Y1 + 1).intersect(
        box(cx - CRADLE_IN, cx + CRADLE_IN, MOT_FACE_Y, CRADLE_Y1 + 1, 0, 60))
    prof = prof.union(box(cx - CRADLE_IN, cx + CRADLE_IN, MOT_FACE_Y, CRADLE_Y1 + 1, AXLE_Z, 60))
    c = c.cut(prof)
    # slot in the front wall for boss + shaft
    c = c.cut(cyl_y(MOT_BOSS_D / 2 + 0.2, cx, AXLE_Z, MOT_FACE_Y - 3, MOT_FACE_Y + 0.1))
    c = c.cut(box(cx - MOT_BOSS_D / 2 - 0.2, cx + MOT_BOSS_D / 2 + 0.2, MOT_FACE_Y - 3, MOT_FACE_Y + 0.1, AXLE_Z, 60))
    # hollow the cradle: the motor sits on two saddles (front + rear) and the side walls
    c = c.cut(box(cx - CRADLE_IN, cx + CRADLE_IN, MOT_FACE_Y + 4, CRADLE_Y1 - 4, PLATE_TOP, AXLE_Z))
    c = c.cut(box(cx - 4, cx + 4, MOT_FACE_Y + 4, CRADLE_Y1 - 4, PLATE_Z - 1, PLATE_TOP + 1))
    # outer wall: thin, with two screw bosses
    xo = cx + s * (CRADLE_IN + 1.4)
    c = c.cut(box(min(xo, xout) - 0.01 * s, max(xo, xout) + 0.01, MOT_FACE_Y, CRADLE_Y1 + 1, PLATE_TOP + 3, CRADLE_TOP + 1))
    for y in CLAMP_SCREW_Y:
        c = c.union(cyl_z(2.4, s * CLAMP_SCREW_X, y, PLATE_Z, CRADLE_TOP))
    for y in CLAMP_SCREW_Y:
        c = c.cut(cyl_z(M2_PILOT / 2, s * CLAMP_SCREW_X, y, CRADLE_TOP - 8, CRADLE_TOP + 1))
    return c

def motor_clamp():
    """Bridge over both motors, 4x M2x8 screws (print 1)."""
    y0, y1 = CLAMP_SCREW_Y[0] - 3, CLAMP_SCREW_Y[1] + 3
    xw = CLAMP_SCREW_X + 2.4
    c = box(-xw, xw, y0, y1, CRADLE_TOP, CRADLE_TOP + 2.4)
    for s in (-1, 1):
        c = c.union(box(s * CENTRE_DIST - 4, s * CENTRE_DIST + 4, y0, y1, AXLE_Z + MOT_W / 2 - 0.1, CRADLE_TOP))
        for y in CLAMP_SCREW_Y:
            c = c.cut(cyl_z(1.15, s * CLAMP_SCREW_X, y, CRADLE_TOP - 1, CRADLE_TOP + 4))
    c = c.cut(box(-4.5, 4.5, y0 + 3, y1 - 3, CRADLE_TOP - 1, CRADLE_TOP + 4))   # lighten over the axle
    return c

PLATE_X0, PLATE_X1 = -REAR_OVERHANG, WHEELBASE + FRONT_OVERHANG
FRAME_T, FRAME_LIP = 2.4, 3.0
FRAME_X0 = PANEL_X0 - FRAME_T
FRAME_X1 = PANEL_X0 + PANEL[0] + 0.6 + FRAME_T
FRAME_Y = PANEL[1] / 2 + 0.3 + FRAME_T
POSTS = [(FRAME_X0 - 1.5, s * (FRAME_Y + 1.5)) for s in (-1, 1)] + [(FRAME_X1 + 1.5, s * (FRAME_Y + 1.5)) for s in (-1, 1)]
CARRIER_X0, CARRIER_X1 = WHEELBASE - 10, WHEELBASE + 10
TRIM_Y = 40.0
BATT_X1 = BATT_X0 + BATT_HOLDER[0]
BATT_Y = BATT_HOLDER[1]
DASH_X = BATT_X1 + 58.0

def chassis():
    w = PLATE_HALF_W
    p = box(PLATE_X0, PLATE_X1, -w, w, PLATE_Z, PLATE_TOP).edges("|Z").fillet(6)
    e = 5.0                                                     # perimeter band width
    cuts = [
        # rear module: between motor cradles and bearing blocks (keeps posts + cradle footprints)
        box(-20, 7, 27, w - e, 0, 20), box(-20, 7, -w + e, -16, 0, 20),
        box(-12, 12, SPUR_Y - 3, SPUR_Y + 3, 0, 20),                                 # under the spur gear
        # battery bay: holders rest on the perimeter, the centre strip and the cross ribs
        box(BATT_X0 + 5, BATT_X1 - 5, 4, BATT_Y - 4, 0, 20), box(BATT_X0 + 5, BATT_X1 - 5, -BATT_Y + 4, -4, 0, 20),
        box(BATT_X0 + 2, BATT_X1 - 2, BATT_Y + 5, w - e, 0, 20), box(BATT_X0 + 2, BATT_X1 - 2, -w + e, -BATT_Y - 5, 0, 20),
        # electronics bay
        box(BATT_X1 + 6, DASH_X - 4, 26, w - e, 0, 20), box(BATT_X1 + 6, DASH_X - 4, -w + e, -26, 0, 20),
        # front
        box(DASH_X + 5, CARRIER_X0 - 4, -w + e, w - e, 0, 20),
        box(CARRIER_X0 + 3, CARRIER_X1 - 3, -TRIM_Y + 6, -6, 0, 20), box(CARRIER_X0 + 3, CARRIER_X1 - 3, 6, TRIM_Y - 6, 0, 20),
        box(CARRIER_X1 + 2, PLATE_X1 - 5, -w + 10, w - 10, 0, 20),
    ]
    # electronics bay: holes between the zip-tie rows
    ex = [BATT_X1 + 6 + 18 * i for i in range(3)]
    for x in ex:
        for (y0, y1) in ((-20, -9.5), (-6.5, 5), (8, 19.5)):
            cuts.append(box(x + 3, x + 13, y0, y1, 0, 20))
    for c in cuts:
        p = p.cut(c)
    # zip-tie slots (batteries + electronics)
    for x in (BATT_X0 + 14, BATT_X1 - 14):
        for y in (-BATT_Y - 3.2, -0.75, BATT_Y + 1.7):
            p = p.cut(box(x - 2, x + 2, y, y + 1.5, 0, 20))
    for x in ex + [ex[-1] + 18]:
        for y in (-22.5, -8.5, 6.0, 20.5):
            p = p.cut(box(x - 1.5, x + 1.5, y, y + 1.5, 0, 20))
    parts = [p]
    for s in (-1, 1):
        y0, y1 = (w - 1.6, w) if s > 0 else (-w, -w + 1.6)
        parts.append(box(12, CARRIER_X0 - 4, y0, y1, PLATE_Z, PLATE_TOP + 3.5))             # side rail
        yw0, yw1 = (w - 1.2, w) if s > 0 else (-w, -w + 1.2)
        parts.append(box(BATT_X0, BATT_X1 + 4, yw0, yw1, PLATE_Z, PLATE_Z + 21).edges("|Y").fillet(3))  # sticker wall
        parts.append(box(-24, -12, y0, y1, PLATE_Z, PLATE_TOP + 3.5))
    # battery bay: end stops and side stops
    parts += [box(BATT_X0 - 2, BATT_X0, -BATT_Y - 1.6, BATT_Y + 1.6, PLATE_Z, PLATE_TOP + 5),
              box(BATT_X1, BATT_X1 + 2, -BATT_Y - 1.6, BATT_Y + 1.6, PLATE_Z, PLATE_TOP + 5),
              box(BATT_X0, BATT_X1, BATT_Y, BATT_Y + 1.6, PLATE_Z, PLATE_TOP + 3),
              box(BATT_X0, BATT_X1, -BATT_Y - 1.6, -BATT_Y, PLATE_Z, PLATE_TOP + 3),
              box(BATT_X0, BATT_X1, -1.5, 1.5, PLATE_Z, PLATE_TOP)]
    parts += [box(CARRIER_X0 - 4, CARRIER_X0 - 2, -w, w, PLATE_Z, PLATE_TOP + 3)]
    parts += [bearing_block(0, True), bearing_block(0, False), motor_cradle(CENTRE_DIST), motor_cradle(-CENTRE_DIST)]
    for (x, y) in POSTS:                                         # hollow panel posts + locating pins
        parts.append(cyl_z(3.0, x, y, PLATE_Z, PANEL_Z).cut(cyl_z(1.6, x, y, PLATE_Z - 1, PANEL_Z - 3)))
        parts.append(cyl_z(1.4, x, y, PANEL_Z, PANEL_Z + 2.5))
    dash = box(DASH_X, DASH_X + 2.4, -20, 20, PLATE_Z, PLATE_TOP + 17)
    dash = dash.cut(cyl(3.1, (DASH_X - 1, -9, PLATE_TOP + 10), (1, 0, 0), 5))   # power toggle switch
    dash = dash.cut(cyl(3.6, (DASH_X - 1, 9, PLATE_TOP + 10), (1, 0, 0), 5))    # start button
    parts.append(dash)
    ch = union_all(parts)
    # free tunnel for the rear axle through the motor cradles (matters for small spur gears, e.g. 30T)
    ch = ch.cut(box(-2.3, 2.3, MOT_FACE_Y - 3, CRADLE_Y1 + 1, AXLE_Z - 2.3, AXLE_Z + 2.3))
    ch = ch.cut(cyl_z(M3_CLEAR / 2, WHEELBASE, 0, 0, 20))
    for y in (-TRIM_Y, TRIM_Y):
        ch = ch.cut(box(WHEELBASE - 1.8, WHEELBASE + 1.8, y - M3_CLEAR / 2, y + M3_CLEAR / 2, 0, PLATE_TOP + 0.01)
                    .edges("|Z").fillet(M3_CLEAR / 2 - 0.01))
    return ch

def front_carrier():
    """Front axle carrier; pivots on the centre screw, trim slots set the toe so the car runs straight."""
    base = box(CARRIER_X0, CARRIER_X1, -PLATE_HALF_W, PLATE_HALF_W, PLATE_TOP, PLATE_TOP + 3.0)
    base = base.cut(box(CARRIER_X0 + 3, CARRIER_X1 - 3, -TRIM_Y + 6, -6, 0, 30))
    base = base.cut(box(CARRIER_X0 + 3, CARRIER_X1 - 3, 6, TRIM_Y - 6, 0, 30))
    parts = [base, bearing_block(WHEELBASE, True, PLATE_TOP), bearing_block(WHEELBASE, False, PLATE_TOP)]
    # stiffening spine
    parts.append(box(CARRIER_X0, CARRIER_X0 + 2, -PLATE_HALF_W, PLATE_HALF_W, PLATE_TOP, PLATE_TOP + 7))
    # hall-sensor holder (A3144, TO-92 flat face toward the left wheel magnets at r = 11 mm)
    hx = WHEELBASE + 11
    arm = box(hx - 3.5, hx + 3.5, PLATE_HALF_W - 5, PLATE_HALF_W, PLATE_TOP, AXLE_Z + 4)
    arm = arm.cut(box(hx - 2.2, hx + 2.2, PLATE_HALF_W - 3.4, PLATE_HALF_W + 1, AXLE_Z - 2.6, AXLE_Z + 5))
    parts.append(arm)
    c = union_all(parts)
    c = c.cut(cyl_z(M3_PILOT / 2, WHEELBASE, 0, PLATE_TOP - 1, PLATE_TOP + 2.5))
    for y in (-TRIM_Y, TRIM_Y):
        c = c.cut(cyl_z(M3_PILOT / 2, WHEELBASE, y, PLATE_TOP - 1, PLATE_TOP + 2.5))
    c = c.cut(cyl_y(2.0, CARRIER_X0 + 1, PLATE_TOP + 5, -PLATE_HALF_W - 1, PLATE_HALF_W + 1).translate((0, 0, 0)))
    return c

def panel_frame():
    """Holds the kit panel without modifying it (rule 4.5). Panel drops in, two elastic bands / clips hold it."""
    h = FRAME_LIP + PANEL_T + 0.4
    f = box(FRAME_X0, FRAME_X1, -FRAME_Y, FRAME_Y, PANEL_Z, PANEL_Z + h)
    f = f.cut(box(PANEL_X0, PANEL_X0 + PANEL[0] + 0.6, -PANEL[1] / 2 - 0.3, PANEL[1] / 2 + 0.3, PANEL_Z + 1.2, PANEL_Z + h + 1))
    f = f.cut(box(PANEL_X0 + FRAME_LIP, PANEL_X0 + PANEL[0] + 0.6 - FRAME_LIP, -PANEL[1] / 2 + FRAME_LIP,
                  PANEL[1] / 2 - FRAME_LIP, PANEL_Z - 1, PANEL_Z + h + 1))
    # finger notches to lift the panel out + band grooves
    for s in (-1, 1):
        f = f.cut(cyl_z(6, PANEL_X0 + PANEL[0] / 2, s * (PANEL[1] / 2 + 0.3), PANEL_Z + 1.2, PANEL_Z + h + 1))
    for x in (FRAME_X0 + 20, FRAME_X1 - 20):
        for s in (-1, 1):
            f = f.cut(box(x - 2, x + 2, s * FRAME_Y - 0.8, s * FRAME_Y + 0.8, PANEL_Z - 1, PANEL_Z + h + 1))
    for (x, y) in POSTS:                                         # ears sit on the posts, outside the panel
        f = f.union(cyl_z(4.0, x, y, PANEL_Z, PANEL_Z + 4.0))
        f = f.cut(cyl_z(1.55, x, y, PANEL_Z - 1, PANEL_Z + 3.2))
    return f

# ---------------------------------------------------------------- wheels
R_SEAT = SEAT_D / 2
BAND_T, WEB_T, HUB_R = 1.0, 2.2, 3.3
MAG_R = 11.0

def rim(lock="dovetail"):
    """Wheel rim, local axis = +Z, z=0 outer face, z=TYRE_W inner face (magnets on the inner face)."""
    r = cq.Workplane("XY").circle(R_SEAT).circle(R_SEAT - BAND_T).extrude(TYRE_W)
    r = r.union(cq.Workplane("XY").circle(R_SEAT - BAND_T + 0.01).circle(HUB_R).extrude(WEB_T).translate((0, 0, TYRE_W - WEB_T)))
    r = r.union(cq.Workplane("XY").circle(HUB_R).extrude(TYRE_W))
    if lock == "dovetail":
        zc = TYRE_W / 2
        prof = [(R_SEAT - 0.01, zc - 1.25), (R_SEAT + 1.0, zc - 1.75), (R_SEAT + 1.0, zc + 1.75), (R_SEAT - 0.01, zc + 1.25)]
        rib = cq.Workplane("XZ").polyline(prof).close().revolve(360, (0, 0, 0), (0, 1, 0))
        for i in range(12):                                   # notches = anti-rotation keys for the silicone
            a = 360 / 12 * i
            rib = rib.cut(box(R_SEAT - 1, R_SEAT + 2, -1.0, 1.0, 0, TYRE_W).rotate((0, 0, 0), (0, 0, 1), a))
        r = r.union(rib)
    for i in range(4):
        a = math.radians(45 + 90 * i)
        r = r.cut(cyl_z(3.0, 11.5 * math.cos(a), 11.5 * math.sin(a), TYRE_W - WEB_T - 1, TYRE_W + 1))
        a = math.radians(90 * i)
        r = r.cut(cyl_z(MAGNET[0] / 2, MAG_R * math.cos(a), MAG_R * math.sin(a), TYRE_W - MAGNET[1], TYRE_W + 1))
    r = r.cut(cyl_z(PRESS_BORE / 2, 0, 0, -1, TYRE_W + 1))
    return r

def tyre_tpu():
    """Alternative tyre printed in TPU 95A; glue onto rim(lock='plain')."""
    return cq.Workplane("XY").circle(WHEEL_D / 2).circle(R_SEAT - 0.15).extrude(TYRE_W)

def tyre_silicone_ref():
    """Shape of the cast silicone tyre (for render / volume only)."""
    t = cq.Workplane("XY").circle(WHEEL_D / 2).circle(R_SEAT).extrude(TYRE_W)
    return t

def spacer():
    return cq.Workplane("XY").circle(2.4).circle(1.65).extrude(1.0)

# ---------------------------------------------------------------- tyre mold (4 cavities, overmolds onto the rims)
MOLD_PITCH = WHEEL_D + 14
MOLD_FLOOR, MOLD_LID = 3.0, 3.0
MOLD_X = 2 * MOLD_PITCH + 26            # extra in x for the gates
MOLD_Y = 2 * MOLD_PITCH + 6
CAVS = [(sx * MOLD_PITCH / 2, sy * MOLD_PITCH / 2) for sx in (-1, 1) for sy in (-1, 1)]
BOLTS = [(0, 0), (0, MOLD_Y / 2 - 5), (0, -MOLD_Y / 2 + 5), (MOLD_X / 2 - 6, 0), (-MOLD_X / 2 + 6, 0)]
PINS = [(MOLD_X / 2 - 6, MOLD_Y / 2 - 6), (-MOLD_X / 2 + 6, -MOLD_Y / 2 + 6)]

def mold_base():
    h = MOLD_FLOOR + TYRE_W
    b = box(-MOLD_X / 2, MOLD_X / 2, -MOLD_Y / 2, MOLD_Y / 2, 0, h).edges("|Z").fillet(4)
    for (cx, cy) in CAVS:
        b = b.cut(cyl_z(WHEEL_D / 2, cx, cy, MOLD_FLOOR, h + 1))
        # centring ring: the rim band (inner radius R_SEAT - BAND_T) slides over it -> concentric tyre
        b = b.union(cyl_z(R_SEAT - BAND_T - 0.08, cx, cy, MOLD_FLOOR - 0.01, MOLD_FLOOR + 1.5)
                    .cut(cyl_z(HUB_R + 0.6, cx, cy, 0, h)))
        b = b.cut(cyl_z(AXLE_D / 2 + 0.2, cx, cy, -1, h + 1))        # knock-out hole: push the wheel out with the axle
        b = b.cut(cyl_z(4.5, cx, cy, -1, 1.0))
        # gate: diamond channel (prints without support) from the side wall to the cavity floor edge
        s = 1 if cx > 0 else -1
        x_wall = s * MOLD_X / 2
        x_cav = cx + s * (WHEEL_D / 2 - 0.5)
        zc = MOLD_FLOOR + 1.6
        L = abs(x_wall - x_cav) + 1
        ch = (cq.Workplane("YZ").rect(1.9, 1.9).extrude(L).rotate((0, 0, 0), (1, 0, 0), 45)
              .translate((min(x_wall, x_cav) - 0.5, cy, zc)))
        b = b.cut(ch)
        # Luer-slip socket for a syringe (6 % taper, 4.6 -> 4.0 mm over 8 mm)
        luer = cq.Workplane("XY").add(cq.Solid.makeCone(2.3, 2.0, 8.0, cq.Vector(x_wall + s * 0.01, cy, zc),
                                                         cq.Vector(-s, 0, 0)))
        b = b.cut(luer)
    for (x, y) in BOLTS:
        b = b.cut(cyl_z(M3_CLEAR / 2, x, y, -1, h + 1))
        b = b.cut(cq.Workplane("XY").polygon(6, 6.4).extrude(2.6).translate((x, y, -0.01)))   # M3 nut trap
    for (x, y) in PINS:
        b = b.cut(cyl_z(1.65, x, y, h - 4, h + 1))
    return b

def mold_lid():
    h0 = MOLD_FLOOR + TYRE_W
    l = box(-MOLD_X / 2, MOLD_X / 2, -MOLD_Y / 2, MOLD_Y / 2, h0, h0 + MOLD_LID).edges("|Z").fillet(4)
    for (cx, cy) in CAVS:
        l = l.cut(cyl_z(AXLE_D / 2 + 0.1, cx, cy, h0 - 1, h0 + MOLD_LID + 1))
        rv = (R_SEAT + 1.0 + WHEEL_D / 2) / 2                     # vents over the deepest part of the tyre
        for i in range(4):
            a = math.radians(90 * i + 45)
            l = l.cut(cyl_z(0.8, cx + rv * math.cos(a), cy + rv * math.sin(a), h0 - 1, h0 + MOLD_LID + 1))
            # small riser cup so overflow is visible and the vent stays full while curing
            l = l.cut(cyl_z(2.0, cx + rv * math.cos(a), cy + rv * math.sin(a), h0 + MOLD_LID - 1.2, h0 + MOLD_LID + 1))
    for (x, y) in BOLTS:
        l = l.cut(cyl_z(M3_CLEAR / 2, x, y, h0 - 1, h0 + MOLD_LID + 1))
    for (x, y) in PINS:
        l = l.union(cyl_z(1.45, x, y, h0 - 3.5, h0))
    return l

# ---------------------------------------------------------------- bought parts (for assembly / render only)
def bought_parts():
    P = {}
    P["battery_holders"] = union_all([box(BATT_X0 + 0.5, BATT_X1 - 0.5, 0.3, BATT_Y - 0.3, PLATE_TOP, PLATE_TOP + 14),
                                      box(BATT_X0 + 0.5, BATT_X1 - 0.5, -BATT_Y + 0.3, -0.3, PLATE_TOP, PLATE_TOP + 14)])
    cells = []
    for yc in (-24, -8, 8, 24):
        cells.append(cyl(7.0, (BATT_X0 + 4, yc, PLATE_TOP + 8.5), (1, 0, 0), 50))
    P["cells"] = union_all(cells)
    P["panel"] = box(PANEL_X0 + 0.3, PANEL_X0 + PANEL[0] + 0.3, -PANEL[1] / 2, PANEL[1] / 2,
                     PANEL_Z + 1.2, PANEL_Z + 1.2 + PANEL_T)
    mots = []
    for cx in (CENTRE_DIST, -CENTRE_DIST):
        m = cyl_y(MOT_W / 2, cx, AXLE_Z, MOT_FACE_Y, MOT_FACE_Y + MOT_L).intersect(
            box(cx - MOT_T / 2, cx + MOT_T / 2, MOT_FACE_Y, MOT_FACE_Y + MOT_L, 0, 60))
        m = m.union(cyl_y(MOT_BOSS_D / 2, cx, AXLE_Z, MOT_FACE_Y - 1.5, MOT_FACE_Y))
        m = m.union(cyl_y(1.0, cx, AXLE_Z, SPUR_Y - GEAR_W / 2, MOT_FACE_Y))
        pin, _ = spur_gear(MODULE, PINION_Z, GEAR_W, 2.0)
        pin = pin.rotate((0, 0, 0), (0, 0, 1), 180 / PINION_Z)
        m = m.union(pin.rotate((0, 0, 0), (1, 0, 0), 90).translate((cx, SPUR_Y + GEAR_W / 2, AXLE_Z)))
        mots.append(m)
    P["motors"] = union_all(mots)
    P["axles"] = union_all([cyl_y(AXLE_D / 2, x, AXLE_Z, -(TRACK + TYRE_W) / 2 - 0.5, (TRACK + TYRE_W) / 2 + 0.5) for x in (0, WHEELBASE)])
    P["esp32s3"] = box(BATT_X1 + 7, BATT_X1 + 33, -34.5, 34.5, PLATE_TOP + 3, PLATE_TOP + 4.6).union(
        box(BATT_X1 + 7, BATT_X1 + 33, -6, 6, PLATE_TOP + 4.6, PLATE_TOP + 7.5))
    P["power"] = union_all([box(BATT_X1 + 37, BATT_X1 + 54, -18, 16, PLATE_TOP, PLATE_TOP + 10),
                            box(BATT_X1 + 37, BATT_X1 + 54, 18, 30, PLATE_TOP, PLATE_TOP + 6)])
    return P

# ---------------------------------------------------------------- build
def export(name, wp, step=True):
    cq.exporters.export(wp, os.path.join(STL, name + ".stl"), tolerance=0.02, angularTolerance=0.15)
    if step:
        cq.exporters.export(wp, os.path.join(OUT, "step", name + ".step"))

def place_wheel(w, x, side):
    """side=+1 left wheel (inner face toward -y)."""
    yc_in = side * (PLATE_HALF_W + 1.0)
    if side > 0:   # rotate +90 about X maps local +Z to -y: inner face (z=TYRE_W) ends up at yc_in
        w = w.rotate((0, 0, 0), (1, 0, 0), 90).translate((x, yc_in + TYRE_W, AXLE_Z))
    else:
        w = w.rotate((0, 0, 0), (1, 0, 0), -90).translate((x, yc_in - TYRE_W, AXLE_Z))
    return w

if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "step"), exist_ok=True)
    print("building parts ...", flush=True)
    parts = {}
    parts["chassis"] = chassis()
    parts["front_carrier"] = front_carrier()
    parts["motor_clamp"] = motor_clamp()
    parts["bearing_cap"] = bearing_cap()
    parts["panel_frame"] = panel_frame()
    parts["rim_silicone"] = rim("dovetail")
    parts["rim_tpu"] = rim("plain")
    parts["tyre_tpu"] = tyre_tpu()
    sp, g = spur_gear(MODULE, SPUR_Z, GEAR_W, PRESS_BORE, hub_d=7.0, hub_len=2.0, web_holes=6)
    parts["spur_42T_m05"] = sp
    parts["spacer"] = spacer()
    parts["mold_base"] = mold_base()
    parts["mold_lid"] = mold_lid()
    # export in print orientation (flat face on the bed, no supports needed)
    FLIP = {"motor_clamp", "bearing_cap", "rim_silicone", "rim_tpu", "mold_lid"}
    for k, v in parts.items():
        export(k, v.rotate((0, 0, 0), (1, 0, 0), 180) if k in FLIP else v)
        print(f"  {k:16s} {v.val().Volume()/1000:7.2f} cm3", flush=True)

    # -------- assembly (positions in car coordinates)
    asm = cq.Assembly(name="solar_challenger")
    col = lambda *c: cq.Color(*c)
    asm.add(parts["chassis"], name="chassis", color=col(0.15, 0.45, 0.85))
    asm.add(parts["front_carrier"], name="front_carrier", color=col(0.15, 0.45, 0.85))
    asm.add(parts["motor_clamp"], name="motor_clamp", color=col(0.9, 0.5, 0.1))
    for xc in (0, WHEELBASE):
        for s in (1, -1):
            cap = parts["bearing_cap"].translate((xc, 0, 0))
            asm.add(cap if s > 0 else mirror_y(cap), name=f"cap_{xc}_{s}", color=col(0.9, 0.5, 0.1))
    asm.add(parts["panel_frame"], name="panel_frame", color=col(0.9, 0.5, 0.1))
    spur_pl = sp.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, SPUR_Y + GEAR_W / 2, AXLE_Z))
    asm.add(spur_pl, name="spur", color=col(0.95, 0.95, 0.95))
    tyre = tyre_silicone_ref()
    for x in (0, WHEELBASE):
        for s in (1, -1):
            asm.add(place_wheel(parts["rim_silicone"], x, s), name=f"rim_{x}_{s}", color=col(0.9, 0.5, 0.1))
            asm.add(place_wheel(tyre, x, s), name=f"tyre_{x}_{s}", color=col(0.1, 0.1, 0.1))
    bp = bought_parts()
    colors = dict(battery_holders=col(0.2, 0.2, 0.2), cells=col(0.1, 0.6, 0.3), panel=col(0.05, 0.1, 0.35),
                  motors=col(0.75, 0.75, 0.78), axles=col(0.6, 0.6, 0.6), esp32s3=col(0.1, 0.35, 0.15),
                  power=col(0.6, 0.1, 0.1))
    for k, v in bp.items():
        asm.add(v, name=k, color=colors[k])
    asm.save(os.path.join(OUT, "step", "assembly.step"))
    # STLs of the placed assembly for rendering
    rend = os.path.join(OUT, "render_parts")
    os.makedirs(rend, exist_ok=True)
    meta = {}
    for ch in asm.children:
        fn = os.path.join(rend, ch.name + ".stl")
        cq.exporters.export(ch.obj, fn, tolerance=0.05, angularTolerance=0.3)
        meta[ch.name] = ch.color.toTuple() if ch.color else (0.5, 0.5, 0.5, 1)
    json.dump(meta, open(os.path.join(rend, "colors.json"), "w"))

    # -------- mass + centre of gravity
    ASA, PLA = 1.07, 1.24  # g/cm3; fill factor 0.9: these parts are mostly walls/solid layers
    printed = {
        "chassis (ASA)": (parts["chassis"], ASA), "front carrier (ASA)": (parts["front_carrier"], ASA),
        "motor clamp (ASA)": (parts["motor_clamp"], ASA), "panel frame (ASA)": (parts["panel_frame"], ASA),
        "spur gear (PLA)": (spur_pl, PLA),
    }
    items = []
    for k, (wp, rho) in printed.items():
        v = wp.val()
        items.append((k, v.Volume() / 1000 * rho * 0.9, v.Center().x))
    capv = parts["bearing_cap"].val().Volume() / 1000 * ASA
    items.append(("4x bearing cap (ASA)", 4 * capv, WHEELBASE / 2))
    rimv = parts["rim_silicone"].val().Volume() / 1000 * PLA * 0.9
    tyrev = (math.pi / 4 * (WHEEL_D**2 - SEAT_D**2) * TYRE_W) / 1000 * 1.15
    items.append(("2x rear wheel (rim+silicone)", 2 * (rimv + tyrev), 0.0))
    items.append(("2x front wheel (rim+silicone)", 2 * (rimv + tyrev), WHEELBASE))
    for k, (mg, x) in BOUGHT.items():
        items.append((k, mg, x))
    M = sum(i[1] for i in items)
    xcg = sum(i[1] * i[2] for i in items) / M
    report = dict(items=[dict(part=a, mass_g=round(b, 1), x_mm=round(c, 1)) for a, b, c in items],
                  total_g=round(M, 1), x_cg_mm=round(xcg, 1), rear_fraction=round(1 - xcg / WHEELBASE, 3),
                  overall_width_mm=TRACK + TYRE_W, overall_length_mm=PLATE_X1 - PLATE_X0,
                  spur=dict(z=SPUR_Z, od=round(2 * g["ra"], 2), clearance_mm=round(AXLE_Z - g["ra"], 2)),
                  centre_distance=CENTRE_DIST,
                  silicone_ml_per_tyre=round(math.pi / 4 * (WHEEL_D**2 - SEAT_D**2) * TYRE_W / 1000, 2))
    json.dump(report, open(os.path.join(OUT, "mass_report.json"), "w"), indent=1)
    for it in report["items"]:
        print(f"  {it['part']:38s} {it['mass_g']:6.1f} g  @ x={it['x_mm']:6.1f}")
    print(f"TOTAL {M:.1f} g, CG x={xcg:.1f} mm -> rear axle carries {100*(1-xcg/WHEELBASE):.1f} %")
    print(f"width {TRACK + TYRE_W} mm (max {MAX_WIDTH}), length {PLATE_X1 - PLATE_X0} mm, spur OD {2*g['ra']:.2f}")
