"""SC-02 boot logo for the RadioMaster Pocket (EdgeTX, 128x64 1-bit): side silhouette of the car from the CAD + 'SC-02'.
Patches the splash block ('SPS\\0' 128 64 + 1024 bytes, LCD page format) of an EdgeTX firmware .bin.
usage: python make_splash.py <edgetx.bin> <out.bin>"""
import sys, os, numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); STL = os.path.join(HERE, '..', 'cad', 'out', 'stl')
S = 8                                                   # supersampling
W, H = 128 * S, 64 * S
img = Image.new('L', (W, H), 0); d = ImageDraw.Draw(img)
sc_ = trimesh.load(os.path.join(HERE, '..', 'web', 'models', 'sc02.glb'))
keep = ('body', 'canopy', 'splitter', 'rear_wing', 'diffuser', 'tyre', 'rim', 'wheel')
parts = []
for name in sc_.graph.nodes_geometry:
    if not name.startswith(keep):
        continue
    T, g = sc_.graph[name]
    m = sc_.geometry[g].copy(); m.apply_transform(T); parts.append((name, m))
V = np.vstack([m.vertices for _, m in parts])
# side view: x = forward (car x), up = z (the GLB is mm, z-up)
x0, x1, z0, z1 = V[:, 0].min(), V[:, 0].max(), V[:, 2].min(), V[:, 2].max()
box_w, box_h = 122 * S, 31 * S
sc = min(box_w / (x1 - x0), box_h / (z1 - z0))
ox, oy = (W - (x1 - x0) * sc) / 2, 3 * S + box_h
for name, m in parts:
    col = 0 if name.startswith(('tyre', 'wheel')) else 255     # tyres dark: they read as wheels under the bright body
    for tri in m.vertices[m.faces]:
        d.polygon([(ox + (x - x0) * sc, oy - (z - z0) * sc) for x, y, z in tri], fill=255)
    if name.startswith(('tyre', 'wheel', 'rim')):
        pass
# wheel arches: cut a dark ring around each wheel so the wheels stand out
for name, m in parts:
    if name.startswith('tyre'):
        bx0, bz0 = m.bounds[0][0], m.bounds[0][2]; bx1, bz1 = m.bounds[1][0], m.bounds[1][2]
        cx, cz, R = (bx0 + bx1) / 2, (bz0 + bz1) / 2, (bz1 - bz0) / 2
        X, Y, RR = ox + (cx - x0) * sc, oy - (cz - z0) * sc, R * sc
        d.ellipse([X - RR - 1.6 * S, Y - RR - 1.6 * S, X + RR + 1.6 * S, Y + RR + 1.6 * S], fill=0)
        d.ellipse([X - RR, Y - RR, X + RR, Y + RR], fill=255)
        d.ellipse([X - RR * 0.5, Y - RR * 0.5, X + RR * 0.5, Y + RR * 0.5], fill=0)
font = None
for f in ('/System/Library/Fonts/Supplemental/Arial Black.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/Library/Fonts/Arial Bold.ttf'):
    if os.path.exists(f):
        font = ImageFont.truetype(f, 19 * S); break
txt = 'SC-02'
tw = d.textlength(txt, font=font)
d.text(((W - tw) / 2, 38 * S), txt, fill=255, font=font)
small = img.resize((128, 64), Image.LANCZOS).point(lambda v: 255 if v > 110 else 0)
small.save(os.path.join(HERE, 'sc02_splash.png'))
px = np.array(small) > 0
data = bytearray(1024)
for y in range(64):
    for x in range(128):
        if px[y, x]:
            data[(y // 8) * 128 + x] |= 1 << (y % 8)
if len(sys.argv) == 3:
    fw = bytearray(open(sys.argv[1], 'rb').read())
    i = fw.find(b'SPS\x00\x80\x40'); assert i > 0 and fw[i + 6 + 1024:i + 6 + 1024 + 3] == b'SPE', 'splash block not found'
    fw[i + 6:i + 6 + 1024] = data
    open(sys.argv[2], 'wb').write(fw)
    print('patched splash at', hex(i), '->', sys.argv[2])
for y in range(0, 64, 2):
    print(''.join('#' if px[y, x] else ' ' for x in range(0, 128, 1)))
