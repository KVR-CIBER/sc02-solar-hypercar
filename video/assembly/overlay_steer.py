"""Steering film overlay: title + a live steering-angle gauge.  steer/NNNN.png -> steer_final/NNNN.png"""
import os, json, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
ANG = json.load(open(os.path.join(HERE, 'steer_angles.json')))
F = lambda w, s: ImageFont.truetype(os.path.join(HERE, 'fonts', f'Inter-{w}.ttf'), s)
TITLE, SUB, BIG, SM = F('SemiBold', 120), F('Regular', 56), F('SemiBold', 120), F('Medium', 44)
WHITE, GREY, RED = (245, 247, 250), (200, 206, 216), (235, 45, 55)


def ts(lay, xy, s, font, fill, a=1.0, anchor='la'):
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((xy[0] + 3, xy[1] + 4), s, font=font, fill=(0, 0, 0, int(170 * a)), anchor=anchor)
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6))); ImageDraw.Draw(lay).text(xy, s, font=font, fill=(*fill, int(255 * a)), anchor=anchor)


def frame(f):
    im = Image.open(os.path.join(HERE, 'steer', f'{f:04d}.png')).convert('RGBA'); W, H = im.size
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    a = min(1, f / 15, (len(ANG) + 1 - f) / 15)
    d.rectangle((150, 170, 160, 380), fill=(*RED, int(255 * a)))
    ts(lay, (200, 160), 'Sturen', TITLE, WHITE, a); ts(lay, (204, 310), 'MG90S-servo · stuurhoorn · stuurstangen · fuseepennen', SUB, GREY, a)
    ang = ANG[f - 1]
    cx, cy, R = W - 430, H - 360, 230                          # gauge: arc -30..+30 deg, needle = steering angle
    d.arc((cx - R, cy - R, cx + R, cy + R), 240, 300, fill=(255, 255, 255, int(70 * a)), width=14)
    sweep = 270 + ang * 1.0
    d.arc((cx - R, cy - R, cx + R, cy + R), min(270, sweep), max(270, sweep), fill=(*RED, int(255 * a)), width=14)
    nx, ny = cx + (R - 30) * math.cos(math.radians(sweep)), cy + (R - 30) * math.sin(math.radians(sweep))
    d.line((cx, cy, nx, ny), fill=(*WHITE, int(230 * a)), width=6); d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(*WHITE, int(230 * a)))
    ts(lay, (cx, cy + 90), f'{ang:+.0f}°', BIG, WHITE, a, 'mm'); ts(lay, (cx, cy + 190), 'stuurhoek', SM, GREY, a, 'mm')
    return Image.alpha_composite(im, lay).convert('RGB')


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'steer_final'), exist_ok=True)
    for f in range(1, len(ANG) + 1): frame(f).save(os.path.join(HERE, 'steer_final', f'{f:04d}.png'), compress_level=1)
    print('overlay done')
