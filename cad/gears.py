"""Involute spur gear profile for CadQuery (20 deg pressure angle)."""
import math
import cadquery as cq

def _inv(a):
    return math.tan(a) - a

def gear_points(m, z, alpha_deg=20.0, backlash=0.05, n_flank=12, n_tip=4, n_root=6):
    a = math.radians(alpha_deg)
    rp = m * z / 2
    rb = rp * math.cos(a)
    ra = rp + m
    rf = rp - 1.25 * m
    s = math.pi * m / 2 - backlash / 2            # tooth thickness on pitch circle
    psi = s / (2 * rp) + _inv(a)                  # half angle measured to base-circle start of involute

    def theta(r):                                 # half tooth angle at radius r
        r = max(r, rb)
        return psi - _inv(math.acos(rb / r))

    r0 = max(rb, rf)
    radii = [r0 + (ra - r0) * (i / n_flank) ** 0.8 for i in range(n_flank + 1)]
    pts = []
    pitch = 2 * math.pi / z
    for k in range(z):
        c = k * pitch
        flank_r = [(r, c - theta(r)) for r in radii]
        if rf < rb:
            flank_r.insert(0, (rf, c - theta(rb)))
        tip = [(ra, c - theta(ra) + (2 * theta(ra)) * j / n_tip) for j in range(1, n_tip)]
        flank_l = [(r, c + theta(r)) for r, _ in reversed(flank_r)]
        tooth = flank_r + tip + flank_l
        pts += [(r * math.cos(t), r * math.sin(t)) for r, t in tooth]
        # root arc to next tooth
        t_end = c + theta(rb if rf < rb else r0)
        t_next = c + pitch - theta(rb if rf < rb else r0)
        for j in range(1, n_root):
            t = t_end + (t_next - t_end) * j / n_root
            pts.append((rf * math.cos(t), rf * math.sin(t)))
    return pts, dict(rp=rp, ra=ra, rf=rf, rb=rb)

def spur_gear(m, z, width, bore, hub_d=None, hub_len=0.0, backlash=0.05, web_holes=0):
    pts, g = gear_points(m, z, backlash=backlash)
    body = cq.Workplane("XY").polyline(pts).close().extrude(width)
    if web_holes and g["rf"] > 9:
        r_in, r_out = (hub_d or bore + 4) / 2 + 1.2, g["rf"] - 1.5
        rm, hd = (r_in + r_out) / 2, (r_out - r_in) * 0.9
        for i in range(web_holes):
            ang = 2 * math.pi * i / web_holes
            body = body.cut(cq.Workplane("XY").center(rm * math.cos(ang), rm * math.sin(ang))
                            .circle(hd / 2).extrude(width))
    if hub_d and hub_len > 0:
        body = body.union(cq.Workplane("XY").circle(hub_d / 2).extrude(width + hub_len))
    body = body.cut(cq.Workplane("XY").circle(bore / 2).extrude(width + hub_len + 1).translate((0, 0, -0.5)))
    return body, g
