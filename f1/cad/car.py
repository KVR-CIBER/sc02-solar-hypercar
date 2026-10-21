"""SC-02 Solar F1 – every part except the body shell (body.py)."""
import math
import cadquery as cq
from p import *
from body import box, cyl, V
from gears import spur_gear

def cyl_y(r, x, z, y0, y1): return cyl(r, (x, y0, z), (0, 1, 0), y1 - y0)
def cyl_z(r, x, y, z0, z1): return cyl(r, (x, y, z0), (0, 0, 1), z1 - z0)
def cyl_x(r, y, z, x0, x1): return cyl(r, (x0, y, z), (1, 0, 0), x1 - x0)
def mir(wp): return wp.mirror("XZ")
def U(*ps):
    o = ps[0]
    for q in ps[1:]: o = o.union(q)
    return o
def rbox(x0, x1, y0, y1, z0, z1, r):
    b = box(x0, x1, y0, y1, z0, z1)
    try: return b.edges("|Z").fillet(r)
    except Exception: return b

FLOOR_HOLES = []                          # (x, y, d) collected from every floor-mounted part
def floor_screw(x, y, d=3.2, part=None, pilot=2.6, depth=6):
    """M3 countersunk from below through the acrylic into a pilot hole in the printed part."""
    FLOOR_HOLES.append((x, y, d))
    if part is not None:
        return part.cut(cyl_z(pilot / 2, x, y, FLOOR_TOP - 0.1, FLOOR_TOP + depth))
    return part

# ------------------------------------------------------------------ floor (black acrylic, laser cut)
def floor_outline():
    """Floor follows the body footprint exactly (clean edge) with notches for the four wheel arches."""
    import body as BD
    xs = [-50 + i * 2.0 for i in range(0, int((322 - -50) / 2) + 1)]
    notches = [(0.0, REAR_D / 2 + 4.0, 59.0), (WB, FRONT_D / 2 + 7.0, 51.0)]     # (x, half length, max |y| at the arch)
    half = []
    for x in xs:
        y = BD.bottom_halfwidth(x) + 0.4
        for (nx, hl, ymax) in notches:
            if abs(x - nx) <= hl:
                y = min(y, ymax)
        half.append((x, max(y, 3.0)))
    pts = [V(x, y, 0) for (x, y) in half] + [V(x, -y, 0) for (x, y) in reversed(half)]
    return cq.Wire.makePolygon(pts, close=True)

DIFF_X0 = -40.0                     # floor ends here, diffuser behind it
def floor_solid():
    f = cq.Workplane("XY").add(cq.Face.makeFromWires(floor_outline())).wires().toPending().extrude(FLOOR_T)
    return f.translate((0, 0, FLOOR_Z)).cut(box(-80, DIFF_X0, -120, 120, 0, 20))      # the diffuser forms the tail underside

# ------------------------------------------------------------------ rear module (inside the body): one 2435 brushless motor
MOT_FACE_Y = SPUR_Y + GEAR_W / 2 + 4.0                 # pinion -10..-6 + 2 mm hub, 2 mm air, then the motor face
MOT_R = MOT_D / 2
PLATE_Y = (MOT_FACE_Y - 3.0, MOT_FACE_Y)               # motor plate (the motor bolts against it with 2x M3)
SADDLE_Y = [(MOT_FACE_Y + 4, MOT_FACE_Y + 8), (MOT_FACE_Y + MOT_L - 9, MOT_FACE_Y + MOT_L - 5)]
CLAMP_Y = (MOT_FACE_Y + 12.0, MOT_FACE_Y + 21.0)       # strap over the can, between the two saddles
EAR_X = MOT_R + 2.6                                    # strap screws (M2.5) left and right of the can (inner one just clears the axle)
PYLON_X = (-38.0, -29.0)
PYLON_Y = (-19.0, 19.0)

def rear_module():
    base = rbox(-35, CD + EAR_X + 2.6, -23, MOT_FACE_Y + MOT_L - 2, FLOOR_TOP, FLOOR_TOP + 2.5, 4)
    parts = [base]
    zt = AXLE_RZ + MOT_R + 2.0
    # motor plate: stands between spur and motor, hole for the pinion hub + motor boss, 2x M3 slots
    plate = box(CD - MOT_R - 1.5, CD + MOT_R + 1.5, PLATE_Y[0], PLATE_Y[1], FLOOR_TOP, zt)
    for sx in (-1, 1):                                                                        # side ribs on the motor side
        plate = plate.union(box(CD + sx * (MOT_R + 0.3) - (1.2 if sx > 0 else 0), CD + sx * (MOT_R + 0.3) + (0 if sx > 0 else 1.2),
                                PLATE_Y[1], PLATE_Y[1] + 6, FLOOR_TOP, AXLE_RZ))
    plate = plate.cut(cyl_y(MOT_BOSS / 2 + 1.5, CD, AXLE_RZ, PLATE_Y[0] - 5, PLATE_Y[1] + 1))
    for sx in (-1, 1):
        x = CD + sx * MOT_HOLES / 2
        plate = plate.cut(cyl_y(1.65, x, AXLE_RZ - 0.6, PLATE_Y[0] - 5, PLATE_Y[1] + 1)).cut(cyl_y(1.65, x, AXLE_RZ + 0.6, PLATE_Y[0] - 5, PLATE_Y[1] + 1)) \
                     .cut(box(x - 1.65, x + 1.65, PLATE_Y[0] - 5, PLATE_Y[1] + 1, AXLE_RZ - 0.6, AXLE_RZ + 0.6))
    parts.append(plate)
    # two saddles under the can + ears for the strap
    for (y0, y1) in SADDLE_Y:
        parts.append(box(CD - MOT_R - 1.5, CD + MOT_R + 1.5, y0, y1, FLOOR_TOP, AXLE_RZ + 4))
    for sx in (-1, 1):
        parts.append(box(CD + sx * EAR_X - 2.2, CD + sx * EAR_X + 2.2, CLAMP_Y[0], CLAMP_Y[1], FLOOR_TOP, AXLE_RZ))
    # twin swan-neck pylons for the rear wing (pass through slots in the rear deck)
    for yp in PYLON_Y:
        parts.append(box(PYLON_X[0], PYLON_X[1], yp - 1.2, yp + 1.2, FLOOR_TOP, 50.0))
        parts.append(box(PYLON_X[0], PYLON_X[1] + 6, yp - 4, yp + 4, FLOOR_TOP, FLOOR_TOP + 10))
    # hall sensor post next to the spur (2 magnets in the spur gear)
    parts.append(box(-4, 4, SPUR_Y - 9, SPUR_Y - 4.5, FLOOR_TOP, AXLE_RZ - 5).cut(box(-2.3, 2.3, SPUR_Y - 7.5, SPUR_Y - 4.4, AXLE_RZ - 9, AXLE_RZ)))
    m = U(*parts)
    m = m.cut(cyl_y(MOT_R + 0.3, CD, AXLE_RZ, PLATE_Y[1], PLATE_Y[1] + MOT_L + 2))                 # the can
    for sx in (-1, 1):
        m = m.cut(cyl_z(1.05, CD + sx * EAR_X, sum(CLAMP_Y) / 2, AXLE_RZ - 7, AXLE_RZ + 1))          # M2.5 pilot
    m = m.cut(box(-2.3, 2.3, -23, MOT_FACE_Y + MOT_L, AXLE_RZ - 2.3, AXLE_RZ + 2.3))                 # axle tunnel
    rs = MODULE * (SPUR_Z + 2) / 2 + 1.0                                                              # slot in the base plate for the spur rim
    m = m.cut(box(-rs, rs, SPUR_Y - GEAR_W / 2 - 0.8, SPUR_Y + GEAR_W / 2 + 0.8, FLOOR_TOP - 1, FLOOR_TOP + 3))
    m = m.cut(cyl_y(MODULE * (PINION_Z + 2) / 2 + 0.8, CD, AXLE_RZ, SPUR_Y - GEAR_W / 2 - 1, PLATE_Y[0]))   # pinion runs free
    for (x, y) in ((-33, -17), (-33, 17), (CD + EAR_X + 1, -17), (CD + EAR_X + 1, MOT_FACE_Y + MOT_L - 6), (-5, -18), (-5, 18)):
        m = floor_screw(x, y, part=m)
    return m

def motor_clamp():
    """Strap over the top of the can, 2x M2.5 into the ears of the rear module."""
    y0, y1 = CLAMP_Y
    ring = cyl_y(MOT_R + 2.2, CD, AXLE_RZ, y0, y1).cut(cyl_y(MOT_R + 0.2, CD, AXLE_RZ, y0 - 1, y1 + 1))
    ring = ring.intersect(box(CD - 40, CD + 40, y0 - 1, y1 + 1, AXLE_RZ, 80))
    c = ring.union(rbox(CD - EAR_X - 2.2, CD + EAR_X + 2.2, y0, y1, AXLE_RZ, AXLE_RZ + 2.4, 1.5).cut(cyl_y(MOT_R + 0.2, CD, AXLE_RZ, y0 - 1, y1 + 1)))
    for sx in (-1, 1):
        c = c.cut(cyl_z(1.4, CD + sx * EAR_X, sum(CLAMP_Y) / 2, AXLE_RZ - 1, AXLE_RZ + 5))
    return c.cut(box(CD - 3, CD + 3, y0 - 1, y1 + 1, AXLE_RZ + MOT_R, AXLE_RZ + MOT_R + 3))                 # cooling window on top

# ------------------------------------------------------------------ rear bearing blocks (inside the body, hidden)
RB_Y = (52.0, 58.0)                       # 6 mm wide: floor screws at y = 55 keep 2.4 mm acrylic to the wheel notch
def rear_bearing_block(left=True):
    y0, y1 = RB_Y
    u = rbox(-9, 9, y0, y1, FLOOR_TOP, AXLE_RZ + 7, 2.5)
    u = u.cut(cyl_y(BRG_FIT / 2, 0, AXLE_RZ, y1 - BRG[2] - 0.1, y1 + 1))
    u = u.cut(box(-BRG_FIT / 2, BRG_FIT / 2, y1 - BRG[2] - 0.1, y1 + 1, AXLE_RZ, 60))           # drop-in slot
    u = u.cut(cyl_y(2.3, 0, AXLE_RZ, y0 - 1, y1 + 1)).cut(box(-2.3, 2.3, y0 - 1, y1 + 1, AXLE_RZ, 60))
    for x in (-6.5, 6.5):
        u = u.cut(cyl_z(0.85, x, (y0 + y1) / 2, AXLE_RZ + 7 - 7, AXLE_RZ + 8))
        u = floor_screw(x, (y0 + y1) / 2 - 0.0, part=u, depth=4) if x < 0 else floor_screw(x, (y0 + y1) / 2, part=u, depth=4)
    return u if left else mir(u)

def bearing_cap(left=True):
    y0, y1 = RB_Y
    c = rbox(-9, 9, y0, y1, AXLE_RZ + 7, AXLE_RZ + 9, 2.5)
    tongue = box(-BRG_FIT / 2 + 0.1, BRG_FIT / 2 - 0.1, y1 - BRG[2], y1, AXLE_RZ, AXLE_RZ + 7).cut(cyl_y(BRG[0] / 2, 0, AXLE_RZ, y0, y1 + 1))
    c = c.union(tongue)
    for x in (-6.5, 6.5):
        c = c.cut(cyl_z(1.15, x, (y0 + y1) / 2, 0, 60))
    return c if left else mir(c)

def wheel_spacer():
    """Tube between the bearing and the rear wheel hub (passes through the arch liner)."""
    return cyl_y(2.9, 0, 0, 0, 65.0 - RB_Y[1] - 0.3).cut(cyl_y(1.65, 0, 0, -1, 20))

# ------------------------------------------------------------------ front: servo, lower wishbones, uprights, tie rods
SERVO_SHAFT = (SERVO_X, 0.0)
HORN_Z = (9.0, 10.8)
SERVO_Z0 = 12.0                         # servo body bottom (servo mounted upside down, shaft points down)
ARM_Z = (FLOOR_TOP, FLOOR_TOP + 2.6)    # lower wishbone plate

def front_module():
    sx, sl, sh, fl = SERVO
    x0 = SERVO_X - 5.9                   # shaft is 5.9 mm from one end of the MG90S body
    # servo cage: two posts carrying the flange screws + a top strap
    cage = U(rbox(x0 - 6, x0 - 0.3, -9, 9, FLOOR_TOP, SERVO_Z0 + 16.5, 1.5),
             rbox(x0 + sx + 0.3, x0 + sx + 6, -9, 9, FLOOR_TOP, SERVO_Z0 + 16.5, 1.5))
    for x in (x0 - 2.8, x0 + sx + 2.8):
        cage = cage.cut(cyl_z(0.9, x, 0, SERVO_Z0 + 8, SERVO_Z0 + 17))
    cage = cage.cut(box(x0 - 7, x0 + sx + 7, -1.6, 1.6, FLOOR_TOP - 1, SERVO_Z0 + 2))   # cable/horn clearance
    # lower wishbone plate: centre pad + A-arms to the kingpins
    pad = rbox(204, 248, -16, 16, ARM_Z[0], ARM_Z[1], 4)
    arms = []
    for s in (1, -1):
        kp = (WB, s * KINGPIN_Y)
        for (ax, ay) in ((206, s * 12), (244, s * 12)):
            L = math.hypot(kp[0] - ax, kp[1] - ay)
            ang = math.degrees(math.atan2(kp[1] - ay, kp[0] - ax))
            arm = (cq.Workplane("XY").rect(L, 3.4).extrude(ARM_Z[1] - ARM_Z[0])
                   .rotate((0, 0, 0), (0, 0, 1), ang).translate(((ax + kp[0]) / 2, (ay + kp[1]) / 2, ARM_Z[0])))
            arms.append(arm)
        arms.append(cyl_z(4.0, kp[0], kp[1], ARM_Z[0], ARM_Z[1]))
    m = U(cage, pad, *arms)
    m = m.cut(cyl_z(SERVO_X - SERVO_X + 5.5, SERVO_X, 0, ARM_Z[0] - 1, ARM_Z[1] + 1))      # horn hub clearance
    for s in (1, -1):
        m = m.cut(cyl_z(1.6, WB, s * KINGPIN_Y, ARM_Z[0] - 1, ARM_Z[1] + 1))               # M3 kingpin
    for (x, y) in ((207, -11), (207, 11), (245, -11), (245, 11)):
        m = floor_screw(x, y, part=m, depth=2.4)
    return m

def front_upright(left=True):
    kx, ky = WB, KINGPIN_Y
    u = rbox(kx - 5.5, kx + 5.5, ky - 4.5, ky + 5.5, ARM_Z[1] + 0.2, AXLE_FZ + 8, 2.5)
    u = u.union(cyl_y(4.2, kx, AXLE_FZ, ky, ky + 7.5))                                     # stub-axle boss
    # steering arm toward the tie rod (Ackermann: points to the rear axle centre)
    ex, ey = kx - 10.5, ky - 6.0
    L = math.hypot(kx - ex, ky - ey); ang = math.degrees(math.atan2(ey - ky, ex - kx))
    arm = (cq.Workplane("XY").rect(L, 4).extrude(1.8).rotate((0, 0, 0), (0, 0, 1), ang)
           .translate(((kx + ex) / 2, (ky + ey) / 2, ARM_Z[1] + 0.2)))
    u = u.union(arm).union(cyl_z(2.6, ex, ey, ARM_Z[1] + 0.2, ARM_Z[1] + 2.0))
    u = u.cut(cyl_z(1.65, kx, ky, 0, 60))                                                   # kingpin M3
    u = u.cut(cyl_z(1.0, ex, ey, 0, 60))                                                    # tie-rod pin M2 pilot
    u = u.cut(cyl_y(PRESS_BORE / 2, kx, AXLE_FZ, ky - 1, ky + 9))                           # 3 mm stub axle (press)
    return u if left else mir(u)

TIE_IN = (SERVO_X, 9.0)
def tie_rod(left=True):
    ex, ey = WB - 10.5, KINGPIN_Y - 6.0
    ax, ay = TIE_IN
    L = math.hypot(ex - ax, ey - ay); ang = math.degrees(math.atan2(ey - ay, ex - ax))
    z0 = ARM_Z[1] + 2.1
    rod = (cq.Workplane("XY").slot2D(L + 5, 4.2).extrude(1.6).rotate((0, 0, 0), (0, 0, 1), ang)
           .translate(((ax + ex) / 2, (ay + ey) / 2, z0)))
    rod = rod.cut(cyl_z(1.1, ex, ey, 0, 40)).cut(cyl_z(1.1, ax, ay, 0, 40))
    return rod if left else mir(rod)

def steering_horn():
    """Double horn, screws onto the servo's round horn; pins for both tie rods."""
    z0 = ARM_Z[1] + 2.1 - 1.8
    h = U(cyl_z(5.5, SERVO_X, 0, z0, z0 + 1.8), (cq.Workplane("XY").slot2D(2 * TIE_IN[1] + 6, 6).extrude(1.8)
          .rotate((0, 0, 0), (0, 0, 1), 90).translate((SERVO_X, 0, z0))))
    for s in (1, -1):
        h = h.cut(cyl_z(1.1, SERVO_X, s * TIE_IN[1], 0, 40))
    return h.cut(cyl_z(2.5, SERVO_X, 0, 0, 40))                         # over the servo spline (screwed to its round horn)

# ------------------------------------------------------------------ wheels: F1 wheel-cover rims + bike-style tyres
def tyre_profile(D, W):
    """Half cross-section of tyre + rim (r, y) with bead hooks. Returns dict of radii."""
    R = D / 2
    rf = R - TYRE_T          # flange top
    rb = rf - 1.6            # rim bed
    return dict(R=R, rf=rf, rb=rb, hook=0.8, flange=1.2, W=W)

def rim(D, W, front):
    g = tyre_profile(D, W)
    R, rf, rb, hk, fl = g["R"], g["rf"], g["rb"], g["hook"], g["flange"]
    # revolve the rim cross-section (in XZ: x = radius, z = axial 0..W)
    pts = [(2.0, 0), (rf, 0), (rf, fl), (rf - 0.7, fl + hk), (rb, fl + hk), (rb, W - fl - hk),
           (rf - 0.7, W - fl - hk), (rf, W - fl), (rf, W), (2.0, W)]
    r = cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    # hollow the inside; keep a flat F1 wheel cover on the outside (z=0 face) + hub
    r = r.cut(cq.Workplane("XY").circle(rb - 1.4).extrude(W - 1.6).translate((0, 0, 1.6)))
    hub_r = 5.5 if front else 4.0
    r = r.union(cq.Workplane("XY").circle(hub_r).extrude(W))
    for i in range(6):                                                                # inner spokes
        a = 60 * i
        r = r.union(box(hub_r - 1, rb - 1, -1.0, 1.0, 1.6, W - 4).rotate((0, 0, 0), (0, 0, 1), a))
    # cover detailing: ring groove + centre nut
    r = r.cut(cq.Workplane("XY").circle(rb - 3.0).circle(rb - 3.6).extrude(0.5))
    r = r.union(cq.Workplane("XY").polygon(6, 7.0).extrude(1.2).translate((0, 0, -1.2)))
    if front:   # two 683 bearings in the hub
        r = r.cut(cq.Workplane("XY").circle(1.7).extrude(W + 4).translate((0, 0, -2)))
        r = r.cut(cq.Workplane("XY").circle(BRG_FIT / 2).extrude(BRG[2] + 0.1).translate((0, 0, -1.2)))
        r = r.cut(cq.Workplane("XY").circle(BRG_FIT / 2).extrude(BRG[2] + 0.1).translate((0, 0, W - BRG[2])))
        r = r.cut(cq.Workplane("XY").polygon(6, 7.0).extrude(0.01).translate((0, 0, -1.2)))
    else:
        r = r.cut(cq.Workplane("XY").circle(PRESS_BORE / 2).extrude(W + 4).translate((0, 0, -2)))
    return r

def tyre(D, W):
    g = tyre_profile(D, W)
    R, rf, rb, hk, fl = g["R"], g["rf"], g["rb"], g["hook"], g["flange"]
    sh = 2.6   # shoulder radius
    # tyre section: crown + sidewalls over the flanges + base with bead toes under the hooks
    outer = cq.Workplane("XZ").polyline([(rf, 0), (R, 0), (R, W), (rf, W)]).close().revolve(360, (0, 0, 0), (0, 1, 0))
    try:
        outer = outer.edges(cq.selectors.RadiusNthSelector(0, directionMax=True)).fillet(sh) if False else outer
    except Exception:
        pass
    base = cq.Workplane("XZ").polyline([(rb, fl), (rf - 0.7, fl), (rf - 0.7, fl + hk), (rf, fl + hk), (rf, W - fl - hk),
                                         (rf - 0.7, W - fl - hk), (rf - 0.7, W - fl), (rb, W - fl)]).close() \
        .revolve(360, (0, 0, 0), (0, 1, 0))
    t = outer.union(base)
    # rounded shoulders: cut a torus-ish fillet via revolve of a corner profile
    for z0, sgn in ((0, 1), (W, -1)):
        corner = (cq.Workplane("XZ").moveTo(R, z0).lineTo(R - sh, z0).threePointArc(
            (R - sh * (1 - 0.7071), z0 + sgn * sh * (1 - 0.7071)), (R, z0 + sgn * sh)).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)))
        t = t.cut(corner)
    # tread: fine circumferential grooves would hurt grip -> slick
    return t

# ------------------------------------------------------------------ tyre mold: 3 parts (bottom, top, core = rim-shaped plug)
def mold_parts():
    cav = [("R", REAR_D, REAR_W, -34, -34), ("R", REAR_D, REAR_W, 34, -34),
           ("F", FRONT_D, FRONT_W, -34, 34), ("F", FRONT_D, FRONT_W, 34, 34)]
    H = 26.0                    # total mold height; parting plane at the tyre mid-plane (z = 13)
    zp = 13.0
    blk = rbox(-66, 66, -66, 66, 0, H, 8)
    bottom = blk.intersect(box(-70, 70, -70, 70, 0, zp))
    top = blk.intersect(box(-70, 70, -70, 70, zp, H))
    cores = []
    for i, (tag, D, W, cx, cy) in enumerate(cav):
        z0 = zp - W / 2
        t = tyre(D, W).translate((cx, cy, z0))
        bottom = bottom.cut(t); top = top.cut(t)
        g = tyre_profile(D, W)
        # core = rim-shaped plug (negative of the tyre's inner side) + locating spigot
        core = rim_core(D, W).translate((cx, cy, z0))
        core = core.union(cyl_z(4.0, cx, cy, z0 - 6, z0)).union(cyl_z(4.0, cx, cy, z0 + W, z0 + W + 6))
        cores.append(core)
        bottom = bottom.cut(cyl_z(4.1, cx, cy, z0 - 6.2, z0 + 0.1))
        top = top.cut(cyl_z(4.1, cx, cy, z0 + W - 0.1, z0 + W + 6.2))
        bottom = bottom.cut(core).cut(cyl_z(1.6, cx, cy, -1, z0))                         # push-out hole
        top = top.cut(core)
        # gate (bottom half, enters the lowest shoulder) + Luer socket on the side
        sx = 1 if cx > 0 else -1
        zg = z0 + 1.6
        ch = cq.Workplane("YZ").rect(2.0, 2.0).extrude(66 - (abs(cx) + g["R"] - 1)).rotate((0, 0, 0), (1, 0, 0), 45)
        ch = ch.translate((abs(cx) + g["R"] - 1, cy, zg)) if sx > 0 else ch.mirror("YZ").translate((-(abs(cx) + g["R"] - 1), cy, zg))
        if sx < 0:
            ch = cq.Workplane("YZ").rect(2.0, 2.0).extrude(66 - (abs(cx) + g["R"] - 1)).rotate((0, 0, 0), (1, 0, 0), 45) \
                .translate((-66, cy, zg))
        bottom = bottom.cut(ch)
        luer = cq.Workplane("XY").add(cq.Solid.makeCone(2.3, 2.0, 8, V(sx * 66.01, cy, zg), V(-sx, 0, 0)))
        bottom = bottom.cut(luer)
        # vents (top half) at the top shoulder, 6 around
        for k in range(6):
            a = math.radians(60 * k + 30)
            vx, vy = cx + (g["R"] - 1.2) * math.cos(a), cy + (g["R"] - 1.2) * math.sin(a)
            top = top.cut(cyl_z(0.75, vx, vy, z0 + W - 1, H + 1)).cut(cyl_z(2.2, vx, vy, H - 1.5, H + 1))
    # registration + bolts
    for (x, y) in ((-58, -58), (58, 58)):
        bottom = bottom.union(cyl_z(2.4, x, y, zp, zp + 4))
        top = top.cut(cyl_z(2.6, x, y, zp - 0.1, zp + 4.4))
    for (x, y) in ((0, -58), (0, 58), (-58, 0), (58, 0), (0, 0), (58, -58), (-58, 58)):
        bottom = bottom.cut(cyl_z(1.65, x, y, -1, H + 1)).cut(cq.Workplane("XY").polygon(6, 6.4).extrude(3).translate((x, y, -0.01)))
        top = top.cut(cyl_z(1.65, x, y, -1, H + 1)).cut(cyl_z(3.1, x, y, H - 3, H + 1))
    # engraved labels
    for (tag, D, W, cx, cy) in cav[::2]:
        txt = cq.Workplane("XY").text("REAR" if tag == "R" else "FRONT", 6, -0.8, halign="center", valign="center", font="Helvetica Neue",
                                      kind="bold").translate((0, cy, H))
        top = top.cut(txt)
    # mold material trapped between core and tyre cannot be printed (floating) -> it becomes part of the nearest core
    halves = []
    for half in (bottom, top):
        sols = sorted(half.solids().vals(), key=lambda q: -q.Volume())
        for fl in sols[1:]:
            c = fl.Center()
            i = min(range(len(cav)), key=lambda j: (cav[j][3] - c.x) ** 2 + (cav[j][4] - c.y) ** 2)
            cores[i] = cores[i].union(cq.Workplane("XY").add(fl))
        halves.append(cq.Workplane("XY").add(sols[0]))
    return halves[0], halves[1], cores

def rim_core(D, W):
    g = tyre_profile(D, W)
    rf, rb, hk, fl = g["rf"], g["rb"], g["hook"], g["flange"]
    pts = [(0.0, 0), (rf, 0), (rf, fl), (rf - 0.7, fl + hk), (rb, fl + hk), (rb, W - fl - hk),
           (rf - 0.7, W - fl - hk), (rf, W - fl), (rf, W), (0.0, W)]
    c = cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    return c

# ------------------------------------------------------------------ wings
def naca(code="6412", c=1.0, n=28, inverted=True):
    m, p, t = int(code[0]) / 100, int(code[1]) / 10, int(code[2:]) / 100
    xs = [(1 - math.cos(math.pi * i / n)) / 2 for i in range(n + 1)]
    up, lo = [], []
    for x in xs:
        yt = 5 * t * (0.2969 * math.sqrt(x) - 0.126 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1036 * x**4)
        if x < p: yc, dy = m / p**2 * (2 * p * x - x**2), 2 * m / p**2 * (p - x)
        else: yc, dy = m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * x - x**2), 2 * m / (1 - p)**2 * (p - x)
        th = math.atan(dy)
        up.append((x - yt * math.sin(th), yc + yt * math.cos(th)))
        lo.append((x + yt * math.sin(th), yc - yt * math.cos(th)))
    pts = up[::-1] + lo[1:-1]
    s = -1 if inverted else 1
    return [(px * c, s * py * c) for (px, py) in pts]

def wing_element(x_le, z_le, chord, aoa_deg, y0, y1, code="6412"):
    """Airfoil extruded along y. Leading edge at x_le (pointing +x = forward), trailing edge rearward."""
    pts = naca(code, chord)
    a = math.radians(aoa_deg)
    P = []
    for (u, w) in pts:                     # u along chord (rearward), w up
        xx = -u * math.cos(a) - w * math.sin(a) * 0
        zz = w + u * math.sin(a)
        P.append((x_le + xx, z_le + zz))
    wp = cq.Workplane("XZ", origin=(0, y1, 0)).polyline(P).close().extrude(y1 - y0)
    return wp

def front_wing():
    span = 86.0
    main = wing_element(326, 8.2, 22, 2, -span, span)
    flaps = []
    for s in (1, -1):
        y0, y1 = (22, span) if s > 0 else (-span, -22)
        flaps += [wing_element(310, 11.0, 11, 14, y0, y1), wing_element(302, 14.0, 9, 28, y0, y1)]
    plates = []
    for s in (1, -1):
        ep = rbox(296, 330, s * span - (0 if s > 0 else 1.2), s * span + (1.2 if s > 0 else 0), 5.0, 22, 0.5)
        ep = ep.cut(box(290, 304, -100, 100, 17, 30).rotate((300, 0, 17), (300, 1, 17), -20))
        plates.append(ep)
    pylons = [rbox(304, 316, s * 6 - 1, s * 6 + 1, 8, 14.5, 0.4) for s in (1, -1)]
    return U(main, *flaps, *plates, *pylons)

def rear_wing():
    span = 74.0
    main = wing_element(-26, 58, 30, 8, -span, span, "6412")
    flap = wing_element(-42, 65.5, 15, 32, -span, span, "6412")
    plates = []
    for s in (1, -1):
        ep = rbox(-62, -20, s * span - (0 if s > 0 else 1.6), s * span + (1.6 if s > 0 else 0), 47, 80, 0.7)
        ep = ep.cut(box(-80, -50, -100, 100, 40, 56).rotate((-62, 0, 56), (-62, 1, 56), 30))
        plates.append(ep)
    necks = []
    for yp in PYLON_Y:   # swan necks: hang the wing from above, socket onto the pylons
        neck = U(box(PYLON_X[0] - 1.6, PYLON_X[1] + 1.6, yp - 2.8, yp + 2.8, 44, 52).cut(
                 box(PYLON_X[0] - 0.15, PYLON_X[1] + 0.15, yp - 1.35, yp + 1.35, 43, 50.2)),
                 box(PYLON_X[0] - 1.6, PYLON_X[1] + 1.6, yp - 1.4, yp + 1.4, 52, 62))
        necks.append(neck)
    return U(main, flap, *plates, *necks)

def splitter():
    """Front splitter + canards (black), screwed under the floor nose."""
    import body as BD
    half = [(x, BD.bottom_halfwidth(x) + 4.0) for x in [250 + i * 2.0 for i in range(0, 39)]]
    pts = [V(x, y, 0) for (x, y) in half] + [V(x, -y, 0) for (x, y) in reversed(half)]
    sp = cq.Workplane("XY").add(cq.Face.makeFromWires(cq.Wire.makePolygon(pts, close=True))).wires().toPending().extrude(1.6)
    sp = sp.translate((0, 0, FLOOR_Z - 1.6 + 0.0))
    out = sp
    for y in (-14, 14):
        out = floor_screw(255, y, part=out, depth=1.6)
    return out

def diffuser():
    """Tail underside: ramp from the floor end up into the tail, 5 strakes + 2 side fences, screwed onto the floor."""
    x0, x1, hw = DIFF_X0, -49.0, 38.0
    ramp = cq.Workplane("XZ").polyline([(x0, FLOOR_Z), (x1, FLOOR_Z), (x1, 20), (x1 + 2.5, 20), (x0, FLOOR_Z + 2.4)]).close().extrude(hw, both=True)
    strakes = U(*[box(x1, x0, y - 0.6, y + 0.6, FLOOR_Z, 18) for y in (-26, -13, 0, 13, 26)])
    strakes = strakes.cut(cq.Workplane("XZ").polyline([(x0, FLOOR_Z + 2.4), (x1, 18.5), (x1, 40), (x0 + 6, 40), (x0 + 6, FLOOR_Z + 2.4)]).close()
                          .extrude(50, both=True))
    side = U(*[box(x1, x0, y - 0.6, y + 0.6, FLOOR_Z, 20) for y in (-hw + 0.6, hw - 0.6)])
    tabs = U(box(x0, x0 + 4.4, -12, 12, FLOOR_TOP, FLOOR_TOP + 2.2), *[box(x0, x0 + 4.4, min(s * 25, s * 36), max(s * 25, s * 36), FLOOR_TOP, FLOOR_TOP + 2.2) for s in (1, -1)],
             *[box(x0, x0 + 7.0, min(s * 31, s * 37), max(s * 31, s * 37), FLOOR_TOP, FLOOR_TOP + 2.2) for s in (1, -1)],   # screw ears, clear of the rear module (|y| < 30.5)
             )
    out = U(ramp, strakes, side, tabs, box(x0 - 1.0, x0, -hw, hw, FLOOR_Z, FLOOR_TOP + 2.2))
    for y in (-34, 34):                        # no centre screw: the rear module sits right behind the floor end there
        out = floor_screw(x0 + 4.5, y, part=out, depth=2.2, d=2.6, pilot=2.0)      # 3.2 mm acrylic to the floor end
    return out

# ------------------------------------------------------------------ inside: trays + body clips
BODY_CLIPS = [(48, 58, 63), (140, 57, 63), (-40, 40, 52), (186, 55, 61)]   # (x, y_in, y_out) per side
CLIP_Z = 14.0
def body_clip(x, yi, yo, s):
    dx = max(0.0, DIFF_X0 + 5.0 - x)          # clip at the floor end: screw 5 mm in from the edge, magnet (body boss) stays put
    c = rbox(x - 4, x + 4 + dx, min(s * yi, s * yo), max(s * yi, s * yo), FLOOR_TOP, CLIP_Z, 1)
    c = c.cut(cyl_z(3.1, x, s * (yi + yo) / 2, CLIP_Z - 3.1, CLIP_Z + 1))      # 6x3 magnet
    return floor_screw(x + dx, s * (yi + yo) / 2, part=c, depth=4)

def pcb_xy(bx, by):
    """f1/pcb design coordinates -> car coordinates"""
    return PCB_X0 + (by - BOARD_Y0), bx - PCB_YC

PCB_HOLES = [pcb_xy(*h) for h in PCB_HOLES_B]
TRAY_X = (PCB_X0 + 5.0, PCB_X0 + 5.0 + LIPO[0] + 3.2)          # battery tray along the car
TRAY_Y = (0.4, 0.4 + LIPO[1] + 3.2)                             # left half (the tall connectors sit on the right edge)

def pcb_posts():
    """4 standoffs (4 mm) between the acrylic floor and the drive PCB; M3 bolts come up through the floor."""
    t = None
    for (x, y) in PCB_HOLES:
        p = cyl_z(3.2, x, y, FLOOR_TOP, PCB_Z0).cut(cyl_z(1.65, x, y, FLOOR_TOP - 1, PCB_Z0 + 1))
        t = p if t is None else t.union(p)
        floor_screw(x, y, d=3.2)
    return t

def battery_tray():
    """Tray for the 2S LiPo above the PCB: sleeves stand on the board at two mount holes (the M3 bolts from below clamp
    floor + post + PCB + sleeve + tray), side walls + velcro strap slots."""
    x0, x1 = TRAY_X; y0, y1 = TRAY_Y
    zt = TRAY_Z + 1.6
    t = rbox(x0, x1, y0, y1, TRAY_Z, zt, 3)
    t = t.union(box(x0, x1, y0, y1, TRAY_Z, zt + 5).cut(box(x0 + 1.6, x1 - 1.6, y0 + 1.6, y1 - 1.6, TRAY_Z, 60)))
    t = t.cut(rbox(x0 + 10, x1 - 10, y0 + 7, y1 - 7, TRAY_Z - 1, zt + 1, 3))                # lighter + air
    for x in (x0 + 20, x1 - 30):                                                            # velcro strap slots
        t = t.cut(box(x, x + 10, y0 - 1, y1 + 1, zt, zt + 3.2)).cut(box(x, x + 10, y0 + 2.2, y0 + 4.2, TRAY_Z - 1, zt + 1)) \
             .cut(box(x, x + 10, y1 - 4.2, y1 - 2.2, TRAY_Z - 1, zt + 1))
    zp = PCB_Z0 + PCB_T
    for (x, y) in (PCB_HOLES[1], PCB_HOLES[3]):                                          # arms to two PCB mount holes
        cx = min(max(x, x0 + 6), x1 - 6); cy = min(max(y, y0 + 6), y1 - 6)
        arm = U(rbox(min(x, cx) - 3.4, max(x, cx) + 3.4, min(y, cy) - 3.4, max(y, cy) + 3.4, TRAY_Z, zt, 2), cyl_z(3.4, x, y, zp, zt))
        t = t.union(arm).cut(cyl_z(1.65, x, y, zp - 1, zt + 6))
    return t

ESC_X = (3.0, 3.0 + ESC[0])
ESC_Y = (-24.6 - ESC[1], -24.6)                                 # right of the motor, behind the PCB: short motor leads
def esc_tray():
    x0, x1 = ESC_X; y0, y1 = ESC_Y
    t = rbox(x0 - 1.6, x1 + 1.6, y0 - 1.6, y1 + 1.6, FLOOR_TOP, FLOOR_TOP + 1.6, 2)
    t = t.union(box(x0 - 1.6, x1 + 1.6, y0 - 1.6, y1 + 1.6, FLOOR_TOP, FLOOR_TOP + 5).cut(box(x0, x1, y0, y1, FLOOR_TOP + 1.6, 40)))
    t = t.cut(box(x0 + 4, x1 - 4, y0 + 4, y1 - 4, FLOOR_TOP - 1, FLOOR_TOP + 2))            # heatsink sits over the floor slots
    for x in (x0 + 8, x1 - 14):
        t = t.cut(box(x, x + 6, y0 - 3, y1 + 3, FLOOR_TOP + 1.6, FLOOR_TOP + 3.2))
    for (x, y) in ((x0 + 2, y0 + 2), (x1 - 2, y1 - 2)):
        t = floor_screw(x, y, part=t, depth=1.6)
    return t

def pcb_model():
    """Drive PCB v3 with its tall parts (for checks, the assembly and the renders)."""
    zb, zt = PCB_Z0, PCB_Z0 + PCB_T
    x0, y0 = pcb_xy(52.0, -68.0); x1, y1 = pcb_xy(138.0, 22.0)
    b = rbox(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), zb, zt, 2)
    for (x, y) in PCB_HOLES:
        b = b.cut(cyl_z(1.6, x, y, zb - 1, zt + 1))
    parts = {}
    for name, (bx, by, sx, sy, h) in {                     # design centre, size along bx / by, height above the board
            "xt60": (58.5, -63.0, 8.2, 15.6, 16.0), "esp32s3": (93.0, 9.0, 18.0, 25.5, 3.2), "elrs_c3": (127.0, -10.0, 13.2, 16.6, 2.5),
            "elrs_e28": (120.5, 12.0, 24.0, 15.0, 2.8), "coil": (129.5, -57.5, 10.0, 10.0, 3.8), "usbc": (73.0, 18.2, 8.9, 7.3, 3.2),
            "hdr_esc": (60.0, -16.0, 2.5, 7.6, 8.5), "hdr_hall": (57.0, 7.5, 2.5, 7.6, 8.5), "hdr_servo": (110.0, -22.5, 7.6, 8.0, 2.6),
            "jst_solar": (70.0, -33.0, 7.4, 5.8, 9.8)}.items():
        cx, cy = pcb_xy(bx, by)
        parts[name] = box(cx - sy / 2, cx + sy / 2, cy - sx / 2, cy + sx / 2, zt, zt + h)
    return b, parts

# ------------------------------------------------------------------ bought parts (for the assembly / web only)
def bought():
    B = {}
    px, py, pt = PANEL
    B["panel"] = box(PANEL_X0 + 0.3, PANEL_X0 + px + 0.3, -py / 2, py / 2, DECK_Z - pt, DECK_Z - 0.05)
    x0, x1 = TRAY_X; y0, y1 = TRAY_Y
    lx, ly, lz = LIPO
    B["battery"] = rbox(x0 + 1.6, x0 + 1.6 + lx, y0 + 1.6, y0 + 1.6 + ly, TRAY_Z + 1.6, TRAY_Z + 1.6 + lz, 2)      # 2S 1000 mAh
    B["pcb"], PCBP = pcb_model()
    B.update({"pcb_" + k: v for k, v in PCBP.items()})
    ex0, ex1 = ESC_X; ey0, ey1 = ESC_Y
    B["esc"] = U(rbox(ex0, ex1, ey0, ey1, FLOOR_TOP + 1.6, FLOOR_TOP + 1.6 + ESC[2] - 4, 2),
                 *[box(ex0 + 2 + i * 3.2, ex0 + 3.6 + i * 3.2, ey0 + 1, ey1 - 1, FLOOR_TOP + 1.6 + ESC[2] - 4, FLOOR_TOP + 1.6 + ESC[2]) for i in range(9)])
    sx, sl, sh, fl = SERVO
    x0s = SERVO_X - 5.9
    B["servo"] = U(box(x0s, x0s + sx, -sl / 2, sl / 2, SERVO_Z0, SERVO_Z0 + sh),
                   box(x0s - 4.75, x0s + sx + 4.75, -sl / 2, sl / 2, SERVO_Z0 + 16.5, SERVO_Z0 + 19),
                   cyl_z(2.4, SERVO_X, 0, SERVO_Z0 - 4, SERVO_Z0))
    B["axle_rear"] = cyl_y(AXLE_D / 2, 0, AXLE_RZ, -TRACK_R / 2 - 8, TRACK_R / 2 + 8)
    return B

def pinion():
    """Motor pinion 11T m0.8 (mill from POM/aluminium or buy): 3.175 mm bore + grub screw boss."""
    p, _ = spur_gear(MODULE, PINION_Z, GEAR_W, MOT_SHAFT_D + 0.05, hub_d=7.0, hub_len=2.0)
    return p

def spur():
    sp, _ = spur_gear(MODULE, SPUR_Z, GEAR_W, PRESS_BORE, hub_d=7.0, hub_len=2.0, web_holes=6)
    for a in (0, 180):                                     # 2 magnets for the hall sensor
        sp = sp.cut(cyl_z(1.05, 8.0 * math.cos(math.radians(a)), 8.0 * math.sin(math.radians(a)), GEAR_W - 1.6, GEAR_W + 1))
    return sp.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, SPUR_Y + GEAR_W / 2, AXLE_RZ))
