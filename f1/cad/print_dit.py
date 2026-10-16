#!/usr/bin/env python3
"""As few P1S plates as possible (prototype: everything in PLA). One big part per plate in the back-right corner,
all small parts packed into the free strips around it. Reads out/step/onderdelen (run build.py first).
Writes f1/PRINT_DIT/: plaat_N.step (+ positioned STL for the slicer check)."""
import os, sys, math
import cadquery as cq, rectpack
from plates import PLATES

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out", "step", "onderdelen")
DST = os.path.join(os.path.dirname(HERE), "PRINT_DIT", "B_banden_in_TPU" if "--tpu" in sys.argv else "A_banden_gieten"); os.makedirs(DST, exist_ok=True)
BED, GAP, EDGE = 256.0, 2.0, 1.0
def margin(s, k=""):                    # tall parts get tree supports that spread: give them more room
    if k.startswith("rim"): return 8.0  # upside-down rims: supports under the bead hooks reach outside the rim
    return 4.5 if s.BoundingBox().zlen > 12 else 2.0
EXCL = (18.0, 28.0)                     # P1S bed exclude area (front left corner)
V = cq.Vector

_cache = {}
def part(k, rx=0, ry=0):
    if k not in _cache:
        _cache[k] = cq.importers.importStep(os.path.join(SRC, k + ".step")).val()
    s = _cache[k]
    if rx: s = s.rotate(V(0, 0, 0), V(1, 0, 0), rx)
    if ry: s = s.rotate(V(0, 0, 0), V(0, 1, 0), ry)
    bb = s.BoundingBox()
    return s.translate(V(-bb.xmin, -bb.ymin, -bb.zmin))

# all parts of plates 1-7b (TPU tyres stay separate: other material)
TPU = "--tpu" in sys.argv          # tyres printed in TPU -> no casting mold needed
items = [(k, rx, ry) for name, (fil, _, its) in PLATES.items() if fil != "tpu" for (k, rx, ry) in its
         if not (TPU and k.startswith("mold"))]
BIG = ["body_main", "body_nose"] + ([] if TPU else ["mold_bottom", "mold_top"])
small = [it for it in items if it[0] not in BIG]

def free_rects(w, h, split):
    """Big part at the back-right corner -> free rectangles (x, y, w, h) around it, avoiding the exclude area.
    split 0: left strip full height, front strip under the part; split 1: front strip full width, left strip beside the part."""
    x0, y0 = BED - EDGE - w, BED - EDGE - h
    L, F = x0 - GAP - EDGE, y0 - GAP - EDGE                     # left strip width, front strip depth
    if split == 0:
        rects = [(EDGE, EXCL[1] + GAP, L, BED - 2 * EDGE - EXCL[1] - GAP), (EXCL[0] + GAP, EDGE, L - EXCL[0] - GAP + EDGE, EXCL[1] + GAP - EDGE),
                 (x0, EDGE, w, F)]
    else:
        rects = [(EXCL[0] + GAP, EDGE, BED - 2 * EDGE - EXCL[0] - GAP, F), (EDGE, EXCL[1] + GAP, EXCL[0] + GAP - EDGE, F - EXCL[1] - GAP + EDGE),
                 (EDGE, y0, L, h)]
    return (x0, y0), [r for r in rects if r[2] > 5 and r[3] > 5]

def rotz(s):
    bb = s.BoundingBox()
    return s.rotate(V(0, 0, 0), V(0, 0, 1), 90).translate(V(bb.ylen, 0, 0))

shapes = {i: part(*it) for i, it in enumerate(small)}
import itertools
ALGOS = (rectpack.MaxRectsBssf, rectpack.MaxRectsBaf, rectpack.MaxRectsBlsf, rectpack.GuillotineBssfSas, rectpack.SkylineBlWm)
best = None
for rots in itertools.product((0, 1), repeat=len(BIG)):
    for splits in itertools.product((0, 1), repeat=len(BIG)):
        for algo in ALGOS:
            for srt in (rectpack.SORT_AREA, rectpack.SORT_LSIDE, rectpack.SORT_PERI):
                pk = rectpack.newPacker(mode=rectpack.PackingMode.Offline, bin_algo=rectpack.PackingBin.Global, rotation=True,
                                        pack_algo=algo, sort_algo=srt)
                bins, bigs = [], {}
                for b, rt, sp in zip(BIG, rots, splits):
                    s = part(b); s = rotz(s) if rt else s; bb = s.BoundingBox()
                    pos, rects = free_rects(bb.xlen, bb.ylen, sp)
                    bigs[b] = s.translate(V(pos[0], pos[1], 0))
                    for r in rects:
                        pk.add_bin(r[2], r[3], bid=len(bins)); bins.append((b, r))
                for _ in range(3):                              # spare empty plates if something does not fit
                    pk.add_bin(BED - 2 * EDGE - EXCL[0] - GAP, BED - 2 * EDGE, bid=len(bins)); bins.append((None, (EDGE + EXCL[0] + GAP, EDGE, 0, 0)))
                for i, s in shapes.items():
                    bb = s.BoundingBox(); m = margin(s, small[i][0]); pk.add_rect(bb.xlen + m, bb.ylen + m, rid=i)
                pk.pack()
                placed = [(ab.bid, r.x, r.y, r.width, r.height, r.rid) for ab in pk for r in ab]   # bin id, not open-order index
                if len(placed) != len(shapes): continue
                extra = len({bid for (bid, *_r) in placed if bins[bid][0] is None})
                score = (extra, sum(1 for (bid, *_r) in placed if bins[bid][0] is None))
                if best is None or score < best[0]:
                    best = (score, placed, bins, bigs)
                    if os.environ.get("DBG"): print(score, rots, splits, algo.__name__, srt)
                if best[0] == (0, 0): break
            if best and best[0] == (0, 0): break
        if best and best[0] == (0, 0): break
    if best and best[0] == (0, 0): break
score, placed, bins, bigs = best
print("extra plates:", score[0], "parts on extra plates:", score[1])

plates = {b: [(b, s)] for b, s in bigs.items()}                 # plate key -> list of (name, solid)
for (bid, x, y, w, h, i) in placed:
    big, r = bins[bid]
    key = big or f"extra_{bid}"
    s = shapes[i]; bb = s.BoundingBox(); m = margin(s, small[i][0])
    if abs(w - (bb.xlen + m)) > 1e-6:                           # rotated 90 deg about z
        s = rotz(s)
    plates.setdefault(key, []).append((small[i][0], s.translate(V(r[0] + x + m / 2, r[1] + y + m / 2, 0))))

# sanity: inside the bed, outside the exclude area, no overlaps
for key, ps in plates.items():
    boxes = [s.BoundingBox() for _, s in ps]
    for (n, _), b in zip(ps, boxes):
        assert b.xmin >= 0 and b.ymin >= 0 and b.xmax <= BED and b.ymax <= BED and b.zmax <= 250, (key, n, b.xmax, b.ymax, b.zmax)
        assert not (b.xmin < EXCL[0] and b.ymin < EXCL[1]), (key, n, "exclude area")
    for a in range(len(ps)):
        for c in range(a + 1, len(ps)):
            A, B = boxes[a], boxes[c]
            if not (A.xmax <= B.xmin + 1e-6 or B.xmax <= A.xmin + 1e-6 or A.ymax <= B.ymin + 1e-6 or B.ymax <= A.ymin + 1e-6):
                print("OVERLAP", key, ps[a][0], [round(v, 1) for v in (A.xmin, A.xmax, A.ymin, A.ymax)], ps[c][0], [round(v, 1) for v in (B.xmin, B.xmax, B.ymin, B.ymax)])
            assert A.xmax <= B.xmin + 1e-6 or B.xmax <= A.xmin + 1e-6 or A.ymax <= B.ymin + 1e-6 or B.ymax <= A.ymin + 1e-6, (key, ps[a][0], ps[c][0])

NAMES = {"body_main": "1_body_achter", "body_nose": "2_body_neus", "mold_bottom": "3_bandenmal_onder", "mold_top": "4_bandenmal_boven"}
order = [k for k in BIG if k in plates] + sorted(k for k in plates if k not in BIG)
for f in os.listdir(DST):
    if f.startswith("plaat_") and f.endswith((".step", ".stl")): os.remove(os.path.join(DST, f))
import shutil; shutil.rmtree(os.path.join(DST, "_stl"), ignore_errors=True); os.makedirs(os.path.join(DST, "_stl"))
for n, key in enumerate(order, 1):
    label = NAMES.get(key, f"{n}_extra")
    fn = f"plaat_{label}"
    asm = cq.Assembly(name=fn)
    for j, (nm, s) in enumerate(plates[key]):
        asm.add(s, name=f"{nm}_{j}")
    asm.save(os.path.join(DST, fn + ".step"))
    sd = os.path.join(DST, "_stl", fn); os.makedirs(sd, exist_ok=True)
    for j, (nm, s) in enumerate(plates[key]):
        cq.exporters.export(cq.Workplane("XY").add(s), os.path.join(sd, f"{j:02d}_{nm}.stl"), tolerance=0.02, angularTolerance=0.1)
    print(f"{fn:32s} {len(plates[key]):3d} parts: " + ", ".join(sorted({nm for nm, _ in plates[key]})))
if TPU:                                                          # the 4 tyres: separate small plate in TPU 95A
    shutil.copy(os.path.join(HERE, "out", "step", "8_option_TPU_tyres.step"), os.path.join(DST, "plaat_3_banden_TPU.step"))
    print("plaat_3_banden_TPU                 4 parts: tyre_front, tyre_rear (TPU)")
