"""Titles + part labels for the SC-02 explainer: frames_explain/NNNN.png + explain.json -> final_explain/NNNN.png"""
import os, sys, json, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
J = json.load(open(os.path.join(HERE, 'explain.json')))
F = lambda w, s: ImageFont.truetype(os.path.join(HERE, 'fonts', f'Inter-{w}.ttf'), s)
TITLE, SUB, LBL, LBS = F('SemiBold', 120), F('Regular', 56), F('SemiBold', 54), F('Regular', 40)
WHITE, GREY, RED = (245, 247, 250), (200, 206, 216), (235, 45, 55)


def ts(lay, xy, s, font, fill, a, anchor='la'):
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((xy[0] + 3, xy[1] + 4), s, font=font, fill=(0, 0, 0, int(170 * a)), anchor=anchor)
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6))); ImageDraw.Draw(lay).text(xy, s, font=font, fill=(*fill, int(255 * a)), anchor=anchor)


def frame(f):
    im = Image.open(os.path.join(HERE, 'frames_explain', f'{f:04d}.png')).convert('RGBA'); W, H = im.size
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for sh in J['shots']:
        a = max(0, min(1, (f - sh['f0']) / 12, (sh['f1'] - f) / 12))
        if a <= 0: continue
        dy = int(30 * (1 - a))
        d.rectangle((150, 170 + dy, 160, 380 + dy), fill=(*RED, int(255 * a)))
        ts(lay, (200, 160 + dy), sh['title'], TITLE, WHITE, a); ts(lay, (204, 310 + dy), sh['sub'], SUB, GREY, a)
        for k, (nm, txt, sub) in enumerate(sh['labels']):
            al = max(0, min(1, (f - sh['f0'] - 10 - 12 * k) / 10, (sh['f1'] - f) / 10))
            p = J['pos'][str(f)].get(nm)
            if al <= 0 or not p or p[2] <= 0: continue
            x, y = p[0] * W, p[1] * H
            dx, dy2 = x - W * 0.5, y - H * 0.5; n = math.hypot(dx, dy2) or 1
            lx, ly = x + dx / n * 300, y + dy2 / n * 220 - 80; right = lx >= x
            d.ellipse((x - 12, y - 12, x + 12, y + 12), fill=(*RED, int(255 * al)))
            d.ellipse((x - 24, y - 24, x + 24, y + 24), outline=(*RED, int(140 * al)), width=3)
            ex = lx + (30 if right else -30); d.line([(x, y), (lx, ly), (ex, ly)], fill=(*WHITE, int(220 * al)), width=4)
            anc = 'ls' if right else 'rs'; tx = ex + (14 if right else -14)
            bb = [d.textbbox((tx, ly - 6), txt, font=LBL, anchor=anc), d.textbbox((tx, ly + 50), sub, font=LBS, anchor=anc)]
            d.rounded_rectangle((min(q[0] for q in bb) - 22, min(q[1] for q in bb) - 16, max(q[2] for q in bb) + 22, max(q[3] for q in bb) + 18), 18, fill=(8, 10, 14, int(190 * al)))
            ts(lay, (tx, ly - 6), txt, LBL, WHITE, al, anc); ts(lay, (tx, ly + 50), sub, LBS, GREY, al, anc)
    return Image.alpha_composite(im, lay).convert('RGB')


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'final_explain'), exist_ok=True)
    for f in range(1, J['n'] + 1): frame(f).save(os.path.join(HERE, 'final_explain', f'{f:04d}.png'), compress_level=1)
    print('overlay done')
