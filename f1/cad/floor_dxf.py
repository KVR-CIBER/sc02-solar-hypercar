"""Clean laser file for the 2 mm acrylic floor: only cut lines (outline, holes, slots) on layer CUT, in mm.
The countersinks are left out (a laser cuts straight through); use M3 flat or button-head screws."""
import os, math
import cadquery as cq, ezdxf
from p import *
import car as C

HERE = os.path.dirname(os.path.abspath(__file__))
# every part that screws to the floor registers its holes in C.FLOOR_HOLES
for f in (C.rear_module, C.motor_clamp, C.front_module, C.pcb_posts, C.battery_tray, C.esc_tray, C.diffuser, C.splitter):
    f()
for side in (True, False):
    C.rear_bearing_block(side)
for (x, yi, yo) in C.BODY_CLIPS:
    C.body_clip(x, yi, yo, 1); C.body_clip(x, yi, yo, -1)
floor = C.floor_solid()
holes = sorted(set((round(x, 3), round(y, 3), round(d, 3)) for (x, y, d) in C.FLOOR_HOLES))
for (x, y, d) in holes:
    floor = floor.cut(C.cyl_z(d / 2, x, y, 0, 20))
floor = floor.cut(C.cyl_z(3.1, 100, -47, 0, 20))                                  # power switch
for i in range(4):                                                                 # ESC cooling slots
    floor = floor.cut(C.rbox(C.ESC_X[0] + 6 + i * 6, C.ESC_X[0] + 9 + i * 6, C.ESC_Y[0] + 6, C.ESC_Y[1] - 6, 0, 20, 1.4))

top = floor.faces('>Z').val()                                                      # the top face holds every cut line
doc = ezdxf.new('R2010', setup=True); doc.units = ezdxf.units.MM
doc.layers.add('CUT', color=1)
msp = doc.modelspace()
n_circ = n_edge = 0
A = {'layer': 'CUT'}
for w in [top.outerWire()] + list(top.innerWires()):
    for e in w.Edges():
        g = e.geomType()
        if g == 'CIRCLE':
            c = e.Center(); r = e.radius()
            p0, p1, pm = e.startPoint(), e.endPoint(), e.positionAt(0.5)
            if (p0 - p1).Length < 1e-6:
                msp.add_circle((c.x, c.y), r, dxfattribs=A); n_circ += 1; continue
            a0 = math.degrees(math.atan2(p0.y - c.y, p0.x - c.x)); a1 = math.degrees(math.atan2(p1.y - c.y, p1.x - c.x))
            am = math.degrees(math.atan2(pm.y - c.y, pm.x - c.x))
            ccw = ((am - a0) % 360) < ((a1 - a0) % 360)                     # does the arc run counter-clockwise from p0 to p1?
            msp.add_arc((c.x, c.y), r, a0 if ccw else a1, a1 if ccw else a0, dxfattribs=A)
        elif g == 'LINE':
            p0, p1 = e.startPoint(), e.endPoint(); msp.add_line((p0.x, p0.y), (p1.x, p1.y), dxfattribs=A)
        else:                                                                  # splines: fine polyline in edge order
            n = max(8, int(e.Length() / 0.2))
            msp.add_lwpolyline([(e.positionAt(i / n).x, e.positionAt(i / n).y) for i in range(n + 1)], dxfattribs=A)
        n_edge += 1
out = os.path.join(HERE, 'out', 'floor_2mm_acrylic_snijlijnen.dxf')
doc.saveas(out)
bb = top.BoundingBox()
print(f'{out}: {n_edge} edges + {n_circ} round holes, {bb.xlen:.1f} x {bb.ylen:.1f} mm')
