import sys
"""Generate the KiCad schematic (labels on every pin, grouped in titled blocks) from design.py.
Footprint links use the same UUIDs as build_pcb.py, so 'Update PCB from schematic' is clean."""
import os, uuid, copy, math
import design, libs, symlib
from sexp import parse, dump, find, find1, Sym
from build_pcb import sym_uuid, ROOT_UUID, NAME, PRJ

GRID = 1.27
S = Sym


def snap(v, g=2.54):
    return round(v / g) * g


def uid(*k):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'sc02-drive-sch/' + '/'.join(map(str, k))))


def font(size=1.27, bold=False):
    f = [S('font'), [S('size'), size, size]]
    if bold:
        f.append([S('bold'), S('yes')])
    return f


LIBSYMS = {s[1]: s for s in find(parse(open(os.path.join(PRJ, 'sc02.kicad_sym')).read()), 'symbol')}
PWR = symlib.get('power:PWR_FLAG')


def sym_geom(sym):
    """pins [(unit, num, name, x, y, ang)] and bbox (in symbol coords, y up) per unit."""
    pins = [(u, n, nm, x, y, a) for (u, n, nm, t, x, y, a, l) in symlib.pins(sym)]
    pts = {}

    def walk(node, unit):
        for e in node:
            if isinstance(e, list) and e:
                if e[0] in ('start', 'end', 'xy', 'center') and len(e) >= 3 and not isinstance(e[1], list):
                    pts.setdefault(unit, []).append((float(e[1]), float(e[2])))
                walk(e, unit)
    for sub in find(sym, 'symbol'):
        u = int(sub[1].rsplit('_', 2)[-2])
        walk([e for e in sub if not (isinstance(e, list) and e[0] == 'pin')], u)
    return pins, pts


def bbox(pins, pts, unit):
    xs, ys = [], []
    for u, n, nm, x, y, a in pins:
        if u in (0, unit):
            xs.append(x); ys.append(y)
    for u in (0, unit):
        for x, y in pts.get(u, []):
            xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def glabel(net, x, y, ang, u):
    """Global label: net names in the netlist match the PCB exactly (no '/' sheet prefix)."""
    just = S('right') if ang in (180, 270) else S('left')
    return [S('global_label'), net, [S('shape'), S('passive')], [S('at'), round(x, 3), round(y, 3), ang],
            [S('fields_autoplaced'), S('yes')], [S('effects'), font(1.0), [S('justify'), just]], [S('uuid'), u],
            [S('property'), 'Intersheetrefs', '${INTERSHEET_REFS}', [S('at'), round(x, 3), round(y, 3), 0],
             [S('effects'), font(1.0), [S('hide'), S('yes')]]]]


def label_len(net):
    return 1.0 * len(net) + 3


def build():
    items, libsyms_used = [], {}
    # ---------------------------------------------------------------- layout: groups -> blocks
    groups = []
    for p in design.parts:
        if p['group'] not in [g[0] for g in groups]:
            groups.append((p['group'], []))
        units = [1, 2] if p['ref'] == 'M1' else [1]
        for u in units:
            dict(groups)[p['group']].append((p, u))
    blocks = []
    for gname, members in groups:
        cells = []
        for p, u in members:
            sid = libs.sym_name(p['sym'])
            sym = LIBSYMS[sid]
            pins, pts = sym_geom(sym)
            x0, y0, x1, y1 = bbox(pins, pts, u)
            left = max([label_len(p['pins'].get(n, '')) for (uu, n, nm, x, y, a) in pins if uu in (0, u) and a == 0] or [0])
            right = max([label_len(p['pins'].get(n, '')) for (uu, n, nm, x, y, a) in pins if uu in (0, u) and a == 180] or [0])
            vert = 6 if any(a in (90, 270) for (uu, n, nm, x, y, a) in pins if uu in (0, u)) else 0
            w = (x1 - x0) + left + right + 8
            h = (y1 - y0) + 2 * vert + 9
            cells.append(dict(p=p, u=u, sym=sym, sid=sid, pins=pins, box=(x0, y0, x1, y1), left=left, vert=vert, w=w, h=h))
        maxw = 175 if gname != 'Raspberry Pi CM5' else 330
        # shelf-pack the cells
        x = y = rowh = 0; bw = 0
        for c in cells:
            if x + c['w'] > maxw and x > 0:
                x = 0; y += rowh; rowh = 0
            c['cx'], c['cy'] = x, y
            x += c['w']; rowh = max(rowh, c['h']); bw = max(bw, x)
        blocks.append(dict(name=gname, cells=cells, w=bw + 6, h=y + rowh + 12))
    # pack blocks into the sheet: columns
    PW, PH = 841, 594                        # A1 landscape
    colx, coly, colw = 15, 20, 0
    for bl in blocks:
        if coly + bl['h'] > PH - 40:
            colx += colw + 10; coly = 20; colw = 0
        bl['x'], bl['y'] = colx, coly
        coly += bl['h'] + 8; colw = max(colw, bl['w'])
    assert colx + colw < PW, 'sheet too small (%.0f)' % (colx + colw)

    # ---------------------------------------------------------------- emit
    for bl in blocks:
        bx, by = bl['x'], bl['y']
        items.append([S('rectangle'), [S('start'), bx, by], [S('end'), bx + bl['w'], by + bl['h']],
                      [S('stroke'), [S('width'), 0.35], [S('type'), S('dash')], [S('color'), 60, 90, 140, 1]],
                      [S('fill'), [S('type'), S('none')]], [S('uuid'), uid('blk', bl['name'])]])
        items.append([S('text'), bl['name'].upper(), [S('exclude_from_sim'), S('no')], [S('at'), bx + 2, by + 5, 0],
                      [S('effects'), font(2.5, True), [S('justify'), S('left'), S('bottom')]], [S('uuid'), uid('blkt', bl['name'])]])
        for c in bl['cells']:
            p, u = c['p'], c['u']
            x0, y0, x1, y1 = c['box']
            sx = snap(bx + 4 + c['cx'] + c['left'] - x0)
            sy = snap(by + 9 + c['cy'] + c['vert'] + 4 + y1)    # symbol y-up -> top of bbox at row top
            libid = 'sc02:' + c['sid']
            libsyms_used[libid] = c['sym']
            props = [('Reference', p['ref'], (sx, sy - y1 - 2.5), False),
                     ('Value', p['value'], (sx, sy - y0 + 2.5), False),
                     ('Footprint', 'sc02:' + libs.fp_name(p['fp']), (sx, sy), True),
                     ('Datasheet', '~', (sx, sy), True),
                     ] + ([('MPN', p['mpn'], (sx, sy), True)] if p['mpn'] else [])
            node = [S('symbol'), [S('lib_id'), libid], [S('at'), sx, sy, 0], [S('unit'), u],
                    [S('exclude_from_sim'), S('no')], [S('in_bom'), S('no') if p['ref'].startswith('H') else S('yes')],
                    [S('on_board'), S('yes')], [S('dnp'), S('yes') if p['dnp'] else S('no')], [S('uuid'), sym_uuid(p['ref'], u)]]
            for k, v, at, hide in props:
                eff = [S('effects'), font()]
                if hide:
                    eff.append([S('hide'), S('yes')])
                node.append([S('property'), k, v, [S('at'), at[0], at[1], 0], eff])
            for (uu, n, nm, px, py, a) in c['pins']:
                if uu in (0, u):
                    node.append([S('pin'), n, [S('uuid'), uid('pin', p['ref'], u, n)]])
            node.append([S('instances'), [S('project'), NAME, [S('path'), '/' + ROOT_UUID, [S('reference'), p['ref']], [S('unit'), u]]]])
            items.append(node)
            # labels / no-connects on every pin
            for (uu, n, nm, px, py, a) in c['pins']:
                if uu not in (0, u):
                    continue
                ax, ay = sx + px, sy - py
                net = p['pins'].get(n)
                if net:
                    la = {0: 180, 180: 0, 90: 270, 270: 90}[int(a)]
                    just = [S('justify'), S('right' if la in (180, 270) else 'left'), S('bottom')]
                    items.append(glabel(net, ax, ay, la, uid('lbl', p['ref'], u, n)))
                else:
                    items.append([S('no_connect'), [S('at'), round(ax, 3), round(ay, 3)], [S('uuid'), uid('nc', p['ref'], u, n)]])

    # ---------------------------------------------------------------- PWR_FLAGs on the supply nets (ERC)
    fx, fy = 15, 10
    libsyms_used['power:PWR_FLAG'] = PWR
    for i, net in enumerate(['GND', 'VBAT_RAW', 'VBUS', 'V5', 'V5_ESP', 'VBUS_USB']):
        x = 15.24 + 22.86 * i; y = 10.16
        node = [S('symbol'), [S('lib_id'), 'power:PWR_FLAG'], [S('at'), x, y, 0], [S('unit'), 1],
                [S('exclude_from_sim'), S('no')], [S('in_bom'), S('no')], [S('on_board'), S('no')], [S('dnp'), S('no')],
                [S('uuid'), uid('pf', net)],
                [S('property'), 'Reference', f'#FLG{i+1:02d}', [S('at'), x, y - 4, 0], [S('effects'), font(), [S('hide'), S('yes')]]],
                [S('property'), 'Value', 'PWR_FLAG', [S('at'), x, y - 3, 0], [S('effects'), font(1.0)]],
                [S('property'), 'Footprint', '', [S('at'), x, y, 0], [S('effects'), font(), [S('hide'), S('yes')]]],
                [S('property'), 'Datasheet', '~', [S('at'), x, y, 0], [S('effects'), font(), [S('hide'), S('yes')]]],
                [S('pin'), '1', [S('uuid'), uid('pfp', net)]],
                [S('instances'), [S('project'), NAME, [S('path'), '/' + ROOT_UUID, [S('reference'), f'#FLG{i+1:02d}'], [S('unit'), 1]]]]]
        items.append(node)
        items.append(glabel(net, x, y, 270, uid('pfl', net)))

    # ---------------------------------------------------------------- notes
    notes = [
        'SC-02 DRIVE BOARD v1.0 - ESP32-S3 + 2x DRV8871 + INA226 + 5 V 5 A buck, sits on the Raspberry Pi 4 like a HAT (generated by tools/build_sch.py from tools/design.py)',
        'Battery 3S LiPo (9-12.6 V) -> P-MOSFET reverse protection -> 2 mOhm shunt (INA226 @ 0x40, I2C IO1/IO2) -> VBUS: motors + buck. Buck 5 V -> Pi 4 header pins 2/4, servo, hall, lights.',
        'Motors: DRV8871 IN1/IN2 (M1: IO4/IO5, M2: IO6/IO7), current limit 64 / 18k = 3.55 A. Servo IO9 (100 R), hall A3144 IO10 (10k pull-up to 3V3), lights IO11 (AO3400A low side), panel ADC IO8 (100k/33k).',
        'Pi link: ESP IO17 (TX) -> 1k -> Pi GPIO15 RXD (pin 10), Pi GPIO14 TXD (pin 8) -> 1k -> ESP IO18 (RX). Pi GPIO4 (pin 7) resets the ESP, Pi GPIO17 (pin 11) holds BOOT: flash it from the Pi with esptool.',
        'The 40-pin socket sits on the BOTTOM side. Do not power the Pi from its own USB-C at the same time (the board feeds its 5 V pins directly).',
    ]
    for i, t in enumerate(notes):
        items.append([S('text'), t, [S('exclude_from_sim'), S('no')], [S('at'), 15, PH - 42 + 4 * i, 0],
                      [S('effects'), font(2.0), [S('justify'), S('left'), S('bottom')]], [S('uuid'), uid('note', i)]])

    lib_symbols = [S('lib_symbols')]
    for libid, sym in libsyms_used.items():
        s = copy.deepcopy(sym); s[1] = libid
        lib_symbols.append(s)
    doc = [S('kicad_sch'), [S('version'), 20250114], [S('generator'), 'eeschema'], [S('generator_version'), '9.0'],
           [S('uuid'), ROOT_UUID], [S('paper'), 'A1'],
           [S('title_block'), [S('title'), 'SC-02 drive board'], [S('date'), '2026-10-18'], [S('rev'), '1.0'],
            [S('company'), 'Kobe Van Robaeys'], [S('comment'), 1, 'ESP32-S3 + 2x DRV8871 + INA226, Pi 4 HAT']],
           lib_symbols] + items + [[S('sheet_instances'), [S('path'), '/', [S('page'), '1']]], [S('embedded_fonts'), S('no')]]
    open(os.path.join(PRJ, NAME + '.kicad_sch'), 'w').write(dump(doc) + '\n')
    print('schematic written: %d blocks' % len(blocks))


if __name__ == '__main__':
    build()
    sys.stdout.flush(); os._exit(0)   # KiCad's SWIG objects can crash Python at shutdown
