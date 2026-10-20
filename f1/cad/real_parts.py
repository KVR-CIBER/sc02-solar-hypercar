"""Detailed models of bought parts (for renders / the web sim). Dimensions: Mabuchi FA-130 / Tamiya Mini 4WD
motor (Hyper-Dash 3 uses the same can), brass 8T m0.5 pinion. Motor axis = +y, front face at y = face_y."""
import math
import cadquery as cq
from p import *
from body import box, cyl, V
from gears import spur_gear

CAN_L, CAP_L = 21.6, 3.6          # (old 130 motor, kept for reference)
R, HALF_T = 20.1 / 2, 15.1 / 2

def _profile(cx, cz, y0, y1, inset=0.0):
    c = cyl(R - inset, (cx, y0, cz), (0, 1, 0), y1 - y0)
    return c.intersect(box(cx - HALF_T + inset, cx + HALF_T - inset, y0 - 1, y1 + 1, cz - 20, cz + 20))

def motor_130(cx, cz, face_y, flip=False):
    """Returns dict name->solid. flip=True: shaft points to -y (body toward -y) - not used here."""
    y0 = face_y
    can = _profile(cx, cz, y0, y0 + CAN_L)
    can = can.cut(_profile(cx, cz, y0 + 0.5, y0 + CAN_L + 1, inset=0.35))            # thin wall (looks right in x-ray)
    # front face details: bearing boss, embossed ring, two vent holes
    boss = cyl(MOT_BOSS / 2, (cx, y0 - 1.5, cz), (0, 1, 0), 1.5)
    ring = cyl(4.6, (cx, y0 - 0.25, cz), (0, 1, 0), 0.25).cut(cyl(3.9, (cx, y0 - 0.5, cz), (0, 1, 0), 1))
    can = can.union(boss).union(ring)
    for a in (35, 215):
        x = cx + 5.6 * math.cos(math.radians(a)); z = cz + 5.6 * math.sin(math.radians(a))
        can = can.cut(cyl(0.75, (x, y0 - 1, z), (0, 1, 0), 2))
    # crimp tabs at the back edge (4x) + label recess band on the flats
    for sx in (-1, 1):
        for sz in (-1, 1):
            can = can.cut(box(cx + sx * 4 - 1, cx + sx * 4 + 1, y0 + CAN_L - 1.2, y0 + CAN_L + 0.1, cz + sz * R - 1.2 * (sz > 0) - 0.0, cz + sz * R + 1.2 * (sz < 0)))
    for sx in (-1, 1):
        xa, xb = sorted((cx + sx * (HALF_T - 0.12), cx + sx * (HALF_T + 0.3)))
        can = can.cut(box(xa, xb, y0 + 4, y0 + 15, cz - 6, cz + 6))
    # plastic end bell (black) with brush-holder bumps and brass terminal tabs
    cap = _profile(cx, cz, y0 + CAN_L, y0 + CAN_L + CAP_L, inset=0.15)
    cap = cap.union(cyl(3.2, (cx, y0 + CAN_L + CAP_L, cz), (0, 1, 0), 0.9))           # rear bushing boss
    for sx in (-1, 1):
        cap = cap.union(box(cx + sx * 3.3 - 1.6, cx + sx * 3.3 + 1.6, y0 + CAN_L + CAP_L - 0.1, y0 + CAN_L + CAP_L + 0.7, cz - 7.5, cz - 3.5))
    terms = None
    for sx in (-1, 1):
        t = box(cx + sx * 6.2 - 1.0, cx + sx * 6.2 + 1.0, y0 + CAN_L + 1.0, y0 + CAN_L + CAP_L + 3.2, cz - 0.15, cz + 0.15)
        t = t.cut(cyl(0.55, (cx + sx * 6.2, y0 + CAN_L + CAP_L + 2.0, cz - 1), (0, 0, 1), 2))
        terms = t if terms is None else terms.union(t)
    shaft = cyl(1.0, (cx, y0 - MOT_SHAFT, cz), (0, 1, 0), MOT_SHAFT + CAN_L + CAP_L + 1.0)
    pin, _ = spur_gear(MODULE, PINION_Z, GEAR_W, 2.0)
    pin = pin.union(cq.Workplane("XY").circle(2.4).extrude(1.2).translate((0, 0, GEAR_W)))   # pinion collar
    ph = 180 / PINION_Z if (cx > 0 or SPUR_Z % 2 == 0) else 0.0         # odd spur: gap at the back pinion's contact
    pin = pin.rotate((0, 0, 0), (0, 0, 1), ph).rotate((0, 0, 0), (1, 0, 0), 90).translate((cx, SPUR_Y + GEAR_W / 2, cz))
    return dict(can=can, cap=cap, term=terms, shaft=shaft, pinion=pin)

if __name__ == "__main__":
    import mf
    m = motor_130(0, 0, 0)
    for k, v in m.items():
        print(k, round(v.val().Volume(), 1), v.val().isValid())
        cq.exporters.export(v, f"/tmp/claude-mot_{k}.stl", tolerance=0.01, angularTolerance=0.08)


def motor_2435(cx, cz, face_y):
    """2435 sensorless brushless inrunner (24 x 35 mm, 3.175 shaft), axis +y, front face at y = face_y.
    Returns can (anodised aluminium), cap (black end bells), term (3 gold bullet leads), shaft, pinion (11T m0.8)."""
    r = MOT_D / 2
    y0, y1 = face_y, face_y + MOT_L
    can = cyl(r, (cx, y0 + 2.0, cz), (0, 1, 0), MOT_L - 4.0)
    for i in range(6):                                                                # cooling grooves
        yg = y0 + 7 + i * 4.2
        can = can.cut(cyl(r + 1, (cx, yg, cz), (0, 1, 0), 1.0).cut(cyl(r - 0.5, (cx, yg - 1, cz), (0, 1, 0), 3)))
    front = cyl(r - 0.4, (cx, y0, cz), (0, 1, 0), 2.0).union(cyl(MOT_BOSS / 2, (cx, y0 - 1.2, cz), (0, 1, 0), 1.2))
    for sx in (-1, 1):
        front = front.cut(cyl(1.5, (cx + sx * MOT_HOLES / 2, y0 - 0.5, cz), (0, 1, 0), 2.6))
    back = cyl(r - 0.4, (cx, y1 - 2.0, cz), (0, 1, 0), 2.0).union(cyl(4.0, (cx, y1, cz), (0, 1, 0), 1.0))
    cap = front.union(back)
    terms = None
    for i, a in enumerate((-30, 0, 30)):                                             # 3 phase leads with 3.5 mm bullets
        x = cx + 6.5 * math.sin(math.radians(a)); z = cz + 6.5 * math.cos(math.radians(a))
        t = cyl(0.9, (x, y1 - 0.5, z), (0, 1, 0), 9.0).union(cyl(1.75, (x, y1 + 8.0, z), (0, 1, 0), 8.0))
        terms = t if terms is None else terms.union(t)
    shaft = cyl(MOT_SHAFT_D / 2, (cx, y0 - MOT_SHAFT, cz), (0, 1, 0), MOT_SHAFT + MOT_L + 1.5)
    pin, _ = spur_gear(MODULE, PINION_Z, GEAR_W, MOT_SHAFT_D)
    pin = pin.union(cq.Workplane("XY").circle(3.5).circle(MOT_SHAFT_D / 2).extrude(2.0).translate((0, 0, GEAR_W)))   # hub + grub screw
    ph = 180 / PINION_Z if SPUR_Z % 2 == 0 else 0.0
    pin = pin.rotate((0, 0, 0), (0, 0, 1), ph).rotate((0, 0, 0), (1, 0, 0), 90).translate((cx, SPUR_Y + GEAR_W / 2, cz))
    pin = pin.cut(shaft)
    return dict(can=can, cap=cap, term=terms, shaft=shaft, pinion=pin)
