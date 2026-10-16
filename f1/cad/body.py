"""SC-02 body: Le-Mans-hypercar shell with closed wheel arches, flush solar deck, smoked canopy.
Shapes are CAD lofts; hollowing and all cuts are mesh booleans (manifold3d) because OCC fails on them."""
import math
import cadquery as cq
from p import *

V = cq.Vector

# (x, half width TOP, z bottom, z top, bottom/top width factor (<1 = undercut), top radius)
BODY_REAR = [
    (-52, 72, 8, 36.5, 0.93, 14),       # Kammback tail: closed rear panel
    (-45, 79, 6.5, 40.0, 0.94, 16),
    (-32, 82, 6, 42.5, 0.95, 18),
    (-6, 88, 6, 47.5, 0.96, 20),
    (20, 84, 6, 45.0, 0.95, 20),
    (36, 76, 6, 42.0, 0.90, 16),
]
DECK_X1 = 132.0
BODY_FRONT = [
    (132, 76, 6, 42.0, 0.90, 16),
    (156, 74, 6, 41.0, 0.90, 16),
    (196, 80, 6, 42.5, 0.92, 18),
    (230, 84, 7, 45.5, 0.95, 20),
    (262, 80, 8, 38.0, 0.92, 18),
    (296, 64, 8, 23.0, 0.90, 10),
    (324, 44, 8.5, 15.5, 0.92, 3),
]
CANOPY = [
    (136, 9, 34, 43.5, 1.0, 4),
    (154, 23, 34, 57.0, 1.0, 13),
    (180, 26, 34, 61.5, 1.0, 15),
    (206, 21, 34, 55.5, 1.0, 12),
    (226, 7, 34, 45.5, 1.0, 4),
]
# wheel wells: (x, |y| inner liner face, axle z, cut radius)
WELLS = [(0.0, 60.0, AXLE_RZ, REAR_D / 2 + 3.2), (WB, 52.0, AXLE_FZ, FRONT_D / 2 + 6.2)]

def section(x, hw, zb, zt, fb, rt, rb=1.5):
    h = zt - zb
    hb = hw * fb
    rt = max(0.6, min(rt, hw * 0.98 - 0.3, h * 0.9 - rb))
    rb = min(rb, hb * 0.4, h * 0.2)
    s = (cq.Sketch().polygon([(-hb, -h / 2), (hb, -h / 2), (hw, h / 2), (-hw, h / 2), (-hb, -h / 2)])
         .vertices(">Y").fillet(rt).reset().vertices("<Y").fillet(rb))
    return s.moved(cq.Location(V(0, (zb + zt) / 2, x)))

def loft(secs, ruled=False):
    """Direct OCC loft. cadquery's loft re-aligns the wires (compatibility check), which twisted the
    tail and nose skin back on itself; our sections are already compatible (same topology, same start)."""
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    b = BRepOffsetAPI_ThruSections(True, ruled, 1e-6)
    b.CheckCompatibility(False)
    for sec in secs:
        b.AddWire(cq.Workplane("YZ").placeSketch(section(*sec))._getFaces()[0].outerWire().wrapped)
    b.Build()
    return cq.Workplane("XY").add(cq.Shape.cast(b.Shape()))

def prism(sec, x1):
    return cq.Workplane("YZ").placeSketch(section(*sec)).extrude(x1 - sec[0])

def inset(secs, t, below=0.6):
    out = []
    for (x, hw, zb, zt, fb, rt) in secs:
        hw2, zt2, zb2 = hw - t, zt - t, zb - below
        target = hw * fb - t
        k = (zb - zb2) / (zt2 - zb2)
        hb2 = (target - k * hw2) / (1 - k)
        out.append((x, hw2, zb2, zt2, max(0.3, min(1.0, hb2 / hw2)), max(rt - t, 0.8)))
    return out

def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def cyl(r, p, d, h):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, V(*p), V(*d)))

def sphere(r, p):
    return cq.Workplane("XY").add(cq.Solid.makeSphere(r, V(*p), angleDegrees1=-90, angleDegrees2=90))

def largest(man):
    parts = man.decompose()
    return max(parts, key=lambda q: q.volume()) if len(parts) > 1 else man

TAIL_X, NOSE_X = BODY_REAR[0][0] + 2.4, 300.0     # closed rear panel / solid nose tip
MID = (84.0, *BODY_REAR[-1][1:])
def all_secs(sec_rear, sec_front):
    return sec_rear + [(MID[0], *sec_rear[-1][1:])] + sec_front

SKIN = all_secs(BODY_REAR, BODY_FRONT)

def outer_pieces():
    return [loft(SKIN)]

def outer_manifold():
    import mf
    out = None
    for pc in outer_pieces():
        out = mf.M(pc) if out is None else out + mf.M(pc)
    return out

def bottom_halfwidth(x):
    """Half width of the body footprint at its bottom edge (used for the floor outline)."""
    secs = SKIN
    for (a, b) in zip(secs[:-1], secs[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return a[1] * a[4] + (b[1] * b[4] - a[1] * a[4]) * t
    return 0.0

def _intake(s, inset_by=0.0):
    y0 = s * (66 - inset_by)
    b = box(152 - inset_by, 184, min(y0, s * 110), max(y0, s * 110), 14 - inset_by, 30 + inset_by)
    return b.edges("|Y").fillet(5 + inset_by)

def shell(extra_cuts=()):
    """Hollow body, open at the bottom, wheels in closed arches (liners), flush panel deck, closed side intakes."""
    import mf
    out = outer_manifold()
    body = out
    # cavity = the same loft stations inset by WALL (so it never pierces the skin), stopped short of both ends:
    # the tail gets a closed rear panel and the nose a solid tip
    cav = mf.M(loft(inset(SKIN, WALL))) ^ mf.M(box(TAIL_X, NOSE_X, -120, 120, -10, 80))
    body = body - cav
    n = len(body.decompose())
    assert n == 1, f"body shell split into {n} pieces"

    # wheel arches with liners: nothing of the inside is visible through the arch
    for (x, yin, z, R) in WELLS:
        for s in (1, -1):
            y0 = yin if s > 0 else -140
            cut = cyl(R, (x, y0, z), (0, 1, 0), 140 - yin).union(box(x - R, x + R, y0, y0 + 140 - yin, -10, z))   # arch open at the bottom: body lifts off over the wheels
            y0l = (yin - WALL) if s > 0 else -140
            liner = cyl(R + WALL, (x, y0l, z), (0, 1, 0), 140 - yin + WALL)
            body = body - mf.M(cut)
            body = body + ((mf.M(liner) - mf.M(cut)) ^ out)
    # solar deck pocket (panel drops in flush and rests on a 3 mm ledge)
    px, py, pt = PANEL
    body = body - mf.M(box(PANEL_X0, PANEL_X0 + px + 0.6, -py / 2 - 0.3, py / 2 + 0.3, DECK_Z - pt - 0.2, DECK_Z + 8))
    body = body - mf.M(box(PANEL_X0 + 3, PANEL_X0 + px + 0.6 - 3, -py / 2 + 3, py / 2 - 3, DECK_Z - pt - 6, DECK_Z))
    # side intakes: recessed and closed at the back
    for s in (1, -1):
        cut = mf.M(_intake(s))
        body = (body - cut) + ((mf.M(_intake(s, WALL)) - cut) ^ out)
    body = body - mf.M(loft(inset(CANOPY, WALL)[1:-1]))           # cockpit opening under the canopy
    for c in extra_cuts:
        body = body - mf.M(c)
    return largest(body), out

def shell_brep(extra_cuts=(), adds=()):
    """Same body as shell(), as a real CAD solid (for STEP). Works now that the loft no longer folds."""
    out = loft(SKIN)
    b = out.cut(loft(inset(SKIN, WALL)).intersect(box(TAIL_X, NOSE_X, -120, 120, -10, 80)))
    for (x, yin, z, R) in WELLS:
        for s in (1, -1):
            y0 = yin if s > 0 else -140
            cut = cyl(R, (x, y0, z), (0, 1, 0), 140 - yin).union(box(x - R, x + R, y0, y0 + 140 - yin, -10, z))
            liner = cyl(R + WALL, (x, (yin - WALL) if s > 0 else -140, z), (0, 1, 0), 140 - yin + WALL)
            b = b.cut(cut).union(liner.cut(cut).intersect(out))
    px, py, pt = PANEL
    b = b.cut(box(PANEL_X0, PANEL_X0 + px + 0.6, -py / 2 - 0.3, py / 2 + 0.3, DECK_Z - pt - 0.2, DECK_Z + 8))
    b = b.cut(box(PANEL_X0 + 3, PANEL_X0 + px + 0.6 - 3, -py / 2 + 3, py / 2 - 3, DECK_Z - pt - 6, DECK_Z))
    for s in (1, -1):
        cut = _intake(s)
        b = b.cut(cut).union(_intake(s, WALL).cut(cut).intersect(out))
    b = b.cut(loft(inset(CANOPY, WALL)[1:-1]))
    for c in extra_cuts:
        b = b.cut(c)
    for a in adds:
        b = b.union(a.intersect(out))
    return b

def canopy_brep():
    return loft(CANOPY).cut(loft(inset(CANOPY, WALL)[1:-1])).cut(loft(SKIN))     # only above the deck

def canopy():
    """Smoked canopy (print in black or smoke PETG), hollow 1.2 mm, sits on the deck like a real hypercar cockpit."""
    return loft(CANOPY)

def canopy_manifold():
    import mf
    return largest(mf.M(loft(CANOPY)) - mf.M(loft(inset(CANOPY, WALL)[1:-1])) - outer_manifold())   # only above the deck

if __name__ == "__main__":
    import time, mf
    t = time.time()
    b, o = shell()
    print("shell", round(mf.vol(b), 1), "cm3, genus", b.genus(), round(time.time() - t, 1), "s")
    mf.save(b, "/tmp/claude-body.stl")
    cq.exporters.export(canopy(), "/tmp/claude-canopy.stl", tolerance=0.04, angularTolerance=0.12)
