"""Step captions + title + end card over the assembly frames: frames/NNNN.png -> final/NNNN.png"""
import os, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, 'captions.json')))
F = lambda w, s: ImageFont.truetype(os.path.join(HERE, 'fonts', f'Inter-{w}.ttf'), s)
NUM, CAP, TITLE, SUB = F('Light', 60), F('SemiBold', 96), F('Bold', 190), F('Medium', 62)
WHITE, GREY, RED = (245, 247, 250), (190, 196, 206), (230, 40, 50)


def shadow_text(lay, xy, s, font, fill, a, anchor='la'):
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0] + 3, xy[1] + 4), s, font=font, fill=(0, 0, 0, int(170 * a)), anchor=anchor)
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    ImageDraw.Draw(lay).text(xy, s, font=font, fill=(*fill, int(255 * a)), anchor=anchor)


def frame(f):
    im = Image.open(os.path.join(HERE, 'frames', f'{f:04d}.png')).convert('RGBA'); W, H = im.size
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    if f < C['steps'][0][0] + 20:                                            # title
        a = min(1, f / 12, (C['steps'][0][0] + 20 - f) / 12)
        shadow_text(lay, (200, 170), 'SC-02 · assemblage', CAP, WHITE, a)
        shadow_text(lay, (204, 300), 'Brushless 2435 · ESP32-S3 + ELRS · zonnepaneel', SUB, GREY, a)
    for i, (a0, b0, cap) in enumerate(C['steps']):
        if a0 <= f < b0 + 6:
            a = min(1, (f - a0) / 6, (b0 + 6 - f) / 6)
            d.rectangle((150, 1700, 160, 1930), fill=(*RED, int(255 * a)))
            shadow_text(lay, (200, 1700), f'{i + 1:02d} / {len(C["steps"])}', NUM, GREY, a)
            shadow_text(lay, (200, 1790), cap, CAP, WHITE, a)
    end0 = C['steps'][-1][1] + 30
    if f >= end0:
        a = min(1, (f - end0) / 20)
        shadow_text(lay, (W / 2, H - 420), 'SC-02', TITLE, WHITE, a, 'mm')
        shadow_text(lay, (W / 2, H - 270), 'Solar Hypercar · Kobe Van Robaeys', SUB, GREY, a, 'mm')
    return Image.alpha_composite(im, lay).convert('RGB')


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'final'), exist_ok=True)
    for f in range(1, C['n'] + 1):
        frame(f).save(os.path.join(HERE, 'final', f'{f:04d}.png'), compress_level=1)
    print('overlay done')
