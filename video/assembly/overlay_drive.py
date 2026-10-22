"""Driving film overlay: title, speed (km/h), motor rpm and an x-ray tag.  drive/NNNN.png -> drive_final/NNNN.png"""
import os, json, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
INFO = json.load(open(os.path.join(HERE, 'drive.json')))
F = lambda w, s: ImageFont.truetype(os.path.join(HERE, 'fonts', f'Inter-{w}.ttf'), s)
TITLE, SUB, BIG, SM = F('SemiBold', 120), F('Regular', 56), F('SemiBold', 130), F('Medium', 44)
WHITE, GREY, RED, BLUE = (245, 247, 250), (200, 206, 216), (235, 45, 55), (110, 180, 255)


def ts(lay, xy, s, font, fill, a=1.0, anchor='la'):
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((xy[0] + 3, xy[1] + 4), s, font=font, fill=(0, 0, 0, int(170 * a)), anchor=anchor)
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6))); ImageDraw.Draw(lay).text(xy, s, font=font, fill=(*fill, int(255 * a)), anchor=anchor)


def frame(f):
    im = Image.open(os.path.join(HERE, 'drive', f'{f:04d}.png')).convert('RGBA'); W, H = im.size
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    i = INFO[f - 1]; n = len(INFO)
    a = min(1, f / 15, (n + 1 - f) / 15)
    d.rectangle((150, 170, 160, 380), fill=(*(BLUE if i['xray'] else RED), int(255 * a)))
    if i['xray']:
        ts(lay, (200, 160), 'Binnenin', TITLE, WHITE, a); ts(lay, (204, 310), 'motor → tandwiel 11T → 35T → achteras', SUB, GREY, a)
    else:
        ts(lay, (200, 160), 'SC-02 rijdt', TITLE, WHITE, a); ts(lay, (204, 310), 'brushless 2435 · achterwielaandrijving · servo-sturing', SUB, GREY, a)
    # gauges bottom right: speed and motor rpm
    for k, (val, unit, mx) in enumerate(((i['v'] * 3.6, 'km/u', 10), (i['rpm'], 'rpm motor', 6000))):
        cx, cy, R = W - 900 + k * 480, H - 380, 190
        d.arc((cx - R, cy - R, cx + R, cy + R), 135, 405, fill=(255, 255, 255, int(60 * a)), width=14)
        d.arc((cx - R, cy - R, cx + R, cy + R), 135, 135 + 270 * min(1, val / mx), fill=(*(BLUE if k else RED), int(255 * a)), width=14)
        ts(lay, (cx, cy + 10), f'{val:.1f}' if k == 0 else f'{val:.0f}', BIG if k == 0 else F('SemiBold', 96), WHITE, a, 'mm')
        ts(lay, (cx, cy + 130), unit, SM, GREY, a, 'mm')
    return Image.alpha_composite(im, lay).convert('RGB')


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'drive_final'), exist_ok=True)
    for f in range(1, len(INFO) + 1): frame(f).save(os.path.join(HERE, 'drive_final', f'{f:04d}.png'), compress_level=1)
    print('overlay done')
