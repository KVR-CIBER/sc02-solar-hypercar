"""SC-02 body: smooth spline-lofted F1 shell (spine + sculpted sidepods + airbox), solar deck, cockpit, helmet, halo."""
import math
import cadquery as cq
from p import *

V = cq.Vector

# (x, half width TOP, z bottom, z top, half width BOTTOM factor (<1 = F1 undercut), top radius)
SPINE_REAR = [
    (-40, 24, 6, 31, 1.00, 8),
    (-12, 36, 6, 40, 1.00, 10),
    (12, 46, 6, 45, 1.00, 9),
    (32, 50, 6, 47.5, 1.00, 7),
]
SPINE_DECK = (32, 130)
SPINE_FRONT = [
    (130, 50, 6, 47.5, 1.00, 7),
    (152, 36, 6, 50, 1.00, 12),
    (174, 32, 6, 50.5, 1.00, 13),
    (200, 31, 6, 46.5, 1.00, 12),
    (216, 24, 12.5, 44, 0.88, 11),
    (234, 19.5, 13, 40, 0.85, 10),
    (268, 13.5, 12, 31.5, 0.82, 7.5),
    (304, 9, 12.5, 24.5, 0.82, 5),
    (338, 4.2, 13.8, 19.2, 0.85, 2.5),
]
PODS_S = [
    (-18, 40, 6, 19, 0.86, 7),
    (14, 60, 6, 32, 0.80, 11),
    (48, 74, 6, 41.5, 0.76, 13),
    (140, 74, 6, 41.5, 0.76, 13),
    (166, 70, 6, 37, 0.80, 12),
    (178, 56, 6, 31, 0.84, 10),
]
AIRBOX_S = [
    (136, 5, 40, 49, 1.0, 4),
    (149, 12.5, 40, 70, 0.9, 11),
    (160, 13, 40, 72.5, 0.9, 11.5),
    (172, 7, 40, 55, 1.0, 6),
]

def section(x, hw, zb, zt, fb, rt, rb=1.5):
    h = zt - zb
    hb = hw * fb
    rt = max(0.6, min(rt, hw * 0.98 - 0.3, h * 0.9 - rb))
    rb = min(rb, hb * 0.4, h * 0.2)
    s = (cq.Sketch().polygon([(-hb, -h / 2), (hb, -h / 2), (hw, h / 2), (-hw, h / 2), (-hb, -h / 2)])
         .vertices(">Y").fillet(rt).reset().vertices("<Y").fillet(rb))
    return s.moved(cq.Location(V(0, (zb + zt) / 2, x)))

def loft(secs, ruled=False):
    return cq.Workplane("YZ").placeSketch(*[section(*s) for s in secs]).loft(ruled=ruled)

def prism(sec, x1):
    x0 = sec[0]
    return cq.Workplane("YZ").placeSketch(section(*sec)).extrude(x1 - x0)

def inset(secs, t, below=0.6):
    """Cavity sections: wall t everywhere; the cavity pokes `below` mm under the body edge (open bottom)
    while keeping its slanted side exactly t inside the outer side at the body edge."""
    out = []
    for (x, hw, zb, zt, fb, rt) in secs:
        hw2, zt2, zb2 = hw - t, zt - t, zb - below
        target = hw * fb - t                     # inner half width wanted at z = zb
        k = (zb - zb2) / (zt2 - zb2)
        hb2 = (target - k * hw2) / (1 - k)       # inner bottom half width at z = zb2
        out.append((x, hw2, zb2, zt2, max(0.3, min(1.0, hb2 / hw2)), max(rt - t, 0.8)))
    return out

def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def cyl(r, p, d, h):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, V(*p), V(*d)))

def sphere(r, p):
    return cq.Workplane("XY").add(cq.Solid.makeSphere(r, V(*p), angleDegrees1=-90, angleDegrees2=90))

def spine(secs_rear, secs_front, t=0.0):
    r = inset(secs_rear, t) if t else secs_rear
    f = inset(secs_front, t) if t else secs_front
    if t:   # closed tail and nose tip: start/stop the cavity 2.5 mm inside the end sections
        r = list(r); f = list(f)
        r[0] = (r[0][0] + 2.5, *r[0][1:])
        f = f[:-1]
    return loft(r).union(prism(r[-1], f[0][0])).union(loft(f))

def outer_solid():
    return spine(SPINE_REAR, SPINE_FRONT).union(loft(PODS_S)).union(loft(AIRBOX_S))

def cavity_pieces():
    """Separate cutters (one boolean cut with their union fails silently in OCC)."""
    pods = inset(PODS_S, WALL)
    pods[0] = (pods[0][0] + 3, *pods[0][1:]); pods[-1] = (pods[-1][0] - 3, *pods[-1][1:])
    ab = [(x, hw - WALL, zb - 6, zt - WALL, fb, max(rt - WALL, 0.8)) for (x, hw, zb, zt, fb, rt) in AIRBOX_S[1:-1]]  # buried in the body
    return [spine(SPINE_REAR, SPINE_FRONT, WALL), loft(pods), loft(ab)]

def largest(man):
    parts = man.decompose()
    return max(parts, key=lambda p: p.volume()) if len(parts) > 1 else man

def shell(extra_cuts=(), extra_adds=()):
    """Hollow body (open at the bottom): solar deck pocket, closed cockpit, closed inlets. Mesh booleans (manifold3d)."""
    import mf
    pieces = [loft(SPINE_REAR), prism(SPINE_REAR[-1], SPINE_FRONT[0][0]), loft(SPINE_FRONT), loft(PODS_S), loft(AIRBOX_S)]
    out = None
    for pc in pieces:
        out = mf.M(pc) if out is None else out + mf.M(pc)
    out_cq = out
    body = out
    for c in cavity_pieces():
        body = body - mf.M(c)
    body = largest(body)
    # solar panel pocket, flush with the deck (rule 4.5: panel only drops in) + 3 mm ledge
    px, py, pt = PANEL
    body = body - mf.M(box(PANEL_X0, PANEL_X0 + px + 0.6, -py / 2 - 0.3, py / 2 + 0.3, DECK_Z - pt - 0.2, DECK_Z + 5))
    body = body - mf.M(box(PANEL_X0 + 3, PANEL_X0 + px + 0.6 - 3, -py / 2 + 3, py / 2 - 3, DECK_Z - pt - 5, DECK_Z))
    # cockpit: recessed opening with a closed floor
    ck = loft([(167, 14, 41, 60, 1.0, 6), (186, 16.5, 41, 60, 1.0, 7), (207, 11, 41, 60, 1.0, 5)])
    body = body - mf.M(ck)
    body = body + (mf.M(box(164, 209, -17.5, 17.5, 39.6, 41.2)) ^ out)
    # airbox intake + sidepod inlets: recessed and closed at the back
    def recess(cut, cup):
        nonlocal body
        body = (body - mf.M(cut)) + ((mf.M(cup) - mf.M(cut)) ^ out)
    recess(cyl(6.0, (161, 0, 64.0), (1, 0, 0), 20).union(box(161, 181, -6, 6, 58, 64)),
           cyl(6.0 + WALL, (161 - WALL, 0, 64.0), (1, 0, 0), 20).union(box(161 - WALL, 181, -6 - WALL, 6 + WALL, 58 - WALL, 64)))
    for s in (1, -1):
        recess(box(171, 190, s * 52 - 12, s * 52 + 12, 13, 33).edges("|X").fillet(5),
               box(171 - WALL, 190, s * 52 - 12 - WALL, s * 52 + 12 + WALL, 13 - WALL, 33 + WALL).edges("|X").fillet(5 + WALL))
    for c in extra_cuts:
        body = body - mf.M(c)
    for a_ in extra_adds:
        body = body + (mf.M(a_) ^ out) if isinstance(a_, tuple) is False else body + mf.M(a_[0])
    return largest(body), out_cq

def helmet():
    h = sphere(10.5, (179, 0, 48.5)).intersect(box(165, 195, -20, 20, 40, 70))
    return h

def visor():
    v = sphere(10.7, (179, 0, 48.5)).intersect(box(183, 192, -8, 8, 47.5, 52))
    return v

def halo():
    """Titanium halo: ring over the cockpit + rear legs + centre pylon."""
    ring = cq.Workplane("XY").add(cq.Solid.makeTorus(16.5, 1.7, V(186, 0, 60.5), V(0, 0, 1)))
    ring = ring.cut(box(150, 177, -30, 30, 50, 70))
    legs = None
    for s in (1, -1):
        p0 = V(177.5, s * 13.2, 60); p1 = V(171, s * 18, 50)
        leg = cq.Workplane("XY").add(cq.Solid.makeCylinder(1.8, (p1 - p0).Length, p0, (p1 - p0).normalized()))
        legs = leg if legs is None else legs.union(leg)
    p0 = V(203.5, 0, 60); p1 = V(208, 0, 45.5)
    pylon = cq.Workplane("XY").add(cq.Solid.makeCylinder(2.0, (p1 - p0).Length, p0, (p1 - p0).normalized()))
    return ring.union(legs).union(pylon)

if __name__ == "__main__":
    import time, sys
    t = time.time()
    import mf
    b, o = shell()
    print("shell", round(mf.vol(b), 1), "cm3, genus", b.genus(), round(time.time() - t, 1), "s")
    mf.save(b, "/tmp/claude-body.stl")
    for name, wp in (("helmet", helmet()), ("halo", halo()), ("visor", visor())):
        cq.exporters.export(wp, f"/tmp/claude-{name}.stl", tolerance=0.05, angularTolerance=0.15)
