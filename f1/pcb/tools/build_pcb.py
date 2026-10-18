import sys
"""Place the ARACHNE brain board in pcbnew: outline, footprints, nets, planes, keep-outs, artwork.
Routing is done afterwards by route.py (Freerouting)."""
import os, json, math, uuid, shutil
import pcbnew
import design, libs

PRJ = libs.PRJ
NAME = 'sc02_drive'
OX, OY = 150.0, 100.0          # board centre on the KiCad page
MM = pcbnew.FromMM
W, H, RC = design.BOARD_W, design.BOARD_H, design.CORNER_R
X0, Y0, X1, Y1 = -W / 2, -H / 2, W / 2, H / 2


def V(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


def sym_uuid(ref, unit=1):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'sc02-drive/{ref}/{unit}'))


ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, 'sc02-drive/root'))
OUTLINE = {k: [tuple(p) for p in v[:-1]] for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outline.json'))).items()}


# ---------------------------------------------------------------- project file
def write_project():
    tpl = json.load(open(os.path.expanduser('~/Documents/GitHub/tiltbox-kicad/tiltbox.kicad_pro')))
    tpl['meta']['filename'] = NAME + '.kicad_pro'
    tpl['sheets'] = [[ROOT_UUID, 'Root']]
    tpl['boards'] = []
    ds = tpl['board']['design_settings']
    ds['rules'].update({'min_clearance': 0.127, 'min_track_width': 0.1, 'min_via_diameter': 0.45,
                        'min_through_hole_diameter': 0.2, 'min_via_annular_width': 0.1,
                        'min_copper_edge_clearance': 0.3, 'min_hole_clearance': 0.2, 'min_hole_to_hole': 0.25,
                        'min_silk_clearance': 0.0})
    ds['track_widths'] = [0.0, 0.15, 0.25, 0.5, 1.0, 1.5]
    ds['via_dimensions'] = [{'diameter': 0.0, 'drill': 0.0}, {'diameter': 0.45, 'drill': 0.2},
                            {'diameter': 0.6, 'drill': 0.3}, {'diameter': 0.8, 'drill': 0.4}]
    sev = ds.setdefault('rule_severities', {})
    sev.update({'silk_overlap': 'ignore', 'silk_over_copper': 'ignore', 'silk_edge_clearance': 'ignore',
                'lib_footprint_mismatch': 'ignore', 'lib_footprint_issues': 'ignore', 'text_height': 'ignore',
                'footprint_symbol_mismatch': 'warning',
                'connection_width': 'ignore'})   # sub-0.1 mm slivers at the edge of the GND pours only
    base = dict(tpl['net_settings']['classes'][0])
    base.update({'name': 'Default', 'track_width': 0.15, 'clearance': 0.15, 'via_diameter': 0.45, 'via_drill': 0.2})
    classes = [base]
    pats = []
    for i, (cname, (nets, tw, cl)) in enumerate(design.NETCLASS.items()):
        c = dict(base); c.update({'name': cname, 'track_width': tw, 'clearance': cl, 'priority': i,
                                 'via_diameter': 0.6 if tw >= 0.5 else 0.45, 'via_drill': 0.3 if tw >= 0.5 else 0.2})
        classes.append(c)
        pats += [{'netclass': cname, 'pattern': n} for n in nets]
    tpl['net_settings']['classes'] = classes
    tpl['net_settings']['netclass_patterns'] = pats
    tpl['net_settings']['netclass_assignments'] = None
    json.dump(tpl, open(os.path.join(PRJ, NAME + '.kicad_pro'), 'w'), indent=2)


# ---------------------------------------------------------------- helpers
def shape_line(board, layer, a, b, w=0.15):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(layer); s.SetWidth(MM(w)); board.Add(s); return s


def shape_circle(board, layer, c, r, w=0.15, fill=False):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(V(*c)); s.SetEnd(V(c[0] + r, c[1])); s.SetLayer(layer); s.SetWidth(MM(w))
    s.SetFilled(fill); board.Add(s); return s


def shape_poly(board, layer, pts, w=0.0, fill=True):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_POLY)
    s.SetPolyPoints([V(*p) for p in pts]); s.SetLayer(layer); s.SetWidth(MM(w)); s.SetFilled(fill)
    board.Add(s); return s


def text(board, layer, s, at, size=1.0, th=0.15, rot=0, mirror=False, bold=False):
    t = pcbnew.PCB_TEXT(board); t.SetText(s); t.SetPosition(V(*at)); t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); t.SetTextThickness(MM(th)); t.SetTextAngleDegrees(rot)
    t.SetMirrored(mirror); t.SetBold(bold); board.Add(t); return t


def rounded_rect_pts(x0, y0, x1, y1, r, n=10):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def zone(board, net, layer, pts, prio=0, name='', connect='thermal', clearance=0.25, minw=0.2):
    z = pcbnew.ZONE(board); z.SetLayer(layer)
    if net:
        z.SetNet(board.FindNet(net))
    ol = z.Outline(); ol.NewOutline()
    for p in pts:
        ol.Append(MM(OX + p[0]), MM(OY + p[1]))
    z.SetAssignedPriority(prio); z.SetZoneName(name)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if connect == 'full' else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetLocalClearance(MM(clearance)); z.SetMinThickness(MM(minw))
    z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z); return z


def keepout(board, pts, layers, tracks=True, vias=True, pours=True, pads=False, fps=False, name=''):
    z = pcbnew.ZONE(board); z.SetIsRuleArea(True)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    ol = z.Outline(); ol.NewOutline()
    for p in pts:
        ol.Append(MM(OX + p[0]), MM(OY + p[1]))
    z.SetDoNotAllowTracks(tracks); z.SetDoNotAllowVias(vias); z.SetDoNotAllowZoneFills(pours)
    z.SetDoNotAllowPads(pads); z.SetDoNotAllowFootprints(fps); z.SetZoneName(name)
    board.Add(z); return z


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def via(board, net, at, d=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(board); v.SetPosition(V(*at)); v.SetDrill(MM(drill)); v.SetWidth(MM(d))
    v.SetNet(board.FindNet(net)); v.SetViaType(pcbnew.VIATYPE_THROUGH); board.Add(v); return v


def track(board, net, a, b, w, layer=pcbnew.F_Cu):
    t = pcbnew.PCB_TRACK(board); t.SetStart(V(*a)); t.SetEnd(V(*b)); t.SetWidth(MM(w)); t.SetLayer(layer)
    t.SetNet(board.FindNet(net)); board.Add(t); return t


def pad_pos(fp, num):
    out = []
    for p in fp.Pads():
        if p.GetNumber() == num:
            q = p.GetPosition(); out.append((pcbnew.ToMM(q.x) - OX, pcbnew.ToMM(q.y) - OY))
    return out


# ---------------------------------------------------------------- build
def build():
    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(MM(1.6))
    board.SetLayerName(pcbnew.In1_Cu, 'In1.Cu'); board.SetLayerName(pcbnew.In2_Cu, 'In2.Cu')
    # inner layers are solid planes (GND / 12 V): mark them 'power' so the autorouter keeps off them
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER); board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)

    for n in design.nets():
        board.Add(pcbnew.NETINFO_ITEM(board, n))

    fpdir = os.path.join(PRJ, 'sc02.pretty')
    fps = {}
    for p in design.parts:
        name = libs.fp_name(p['fp'])
        fp = pcbnew.FootprintLoad(fpdir, name)
        assert fp is not None, name
        fp.SetFPID(pcbnew.LIB_ID('sc02', name))
        board.Add(fp)
        fp.SetReference(p['ref']); fp.SetValue(p['value'])
        x, y, rot = p['at']
        fp.SetPosition(V(x, y))
        if p['side'] == 'B':
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        fp.SetPath(pcbnew.KIID_PATH('/' + sym_uuid(p['ref'], 1)))
        fp.SetProperties if False else None
        for prop, val in (('MPN', p['mpn']),):
            if val:
                f = pcbnew.PCB_FIELD(fp, pcbnew.FIELD_T_USER, prop) if hasattr(pcbnew, 'FIELD_T_USER') else None
                if f is not None:
                    f.SetText(val); f.SetVisible(False); f.SetLayer(pcbnew.F_Fab); fp.Add(f)
        for pad in fp.Pads():
            net = p['pins'].get(pad.GetNumber())
            if net:
                pad.SetNet(board.FindNet(net))
        fps[p['ref']] = fp
        # small, tidy reference text
        r = fp.Reference(); r.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8))); r.SetTextThickness(MM(0.12))
    for i in range(1, 5):
        fps[f'H{i}'].Reference().SetVisible(False)
    # sanity: the socket must match the Pi header (pin 1 inner row, pin 2 outer row, pins along +x)
    p1, p2, p3 = pad_pos(fps['J9'], '1')[0], pad_pos(fps['J9'], '2')[0], pad_pos(fps['J9'], '3')[0]
    assert abs(p1[0] - design.HDR1[0]) < .01 and abs(p2[1] - (design.HDR1[1] - 2.54)) < .01 and abs(p3[0] - (p1[0] + 2.54)) < .01, (p1, p2, p3)

    # ---------------- outline + camera flex slot
    edge = OUTLINE['edge']
    for a, b in zip(edge, edge[1:] + edge[:1]):
        if a != b:
            shape_line(board, pcbnew.Edge_Cuts, a, b, 0.1)
    cx0, cy0, cx1, cy1 = design.CAM_SLOT
    slot = rounded_rect_pts(cx0, cy0, cx1, cy1, 1.0, 4)
    for a, b in zip(slot, slot[1:] + slot[:1]):
        shape_line(board, pcbnew.Edge_Cuts, a, b, 0.1)
    inner = OUTLINE['inner']
    allcu = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]

    # ---------------- keep-outs: ESP32 antenna overhangs the bottom edge
    ex = design.ESP[0]
    keepout(board, rect(ex - 10.5, Y1 - 1.0, ex + 10.5, Y1 + 1), allcu, name='ESP antenne-rand')

    # ---------------- planes: In1 GND, In2 = battery bus (motors + buck input)
    zone(board, 'GND', pcbnew.In1_Cu, inner, prio=0, name='GND plane', connect='full')
    zone(board, 'VBUS', pcbnew.In2_Cu, inner, prio=0, name='VBUS plane (batterij)', connect='full')

    def box_of(pads, m):
        xs, ys = [], []
        for ref, num in pads:
            for p in fps[ref].Pads():
                if p.GetNumber() == num:
                    bb = p.GetBoundingBox()
                    xs += [pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetRight()) - OX]
                    ys += [pcbnew.ToMM(bb.GetY()) - OY, pcbnew.ToMM(bb.GetBottom()) - OY]
        return min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m

    def local(net, pads, m=0.3, prio=3, ko=True):
        x0, y0, x1, y1 = box_of(pads, m)
        zone(board, net, pcbnew.F_Cu, rect(x0, y0, x1, y1), prio=prio, name=net + ' lokaal', connect='full')
        if ko:
            keepout(board, rect(x0 + .4, y0 + .4, x1 - .4, y1 - .4), [pcbnew.F_Cu], tracks=True, vias=False, pours=False,
                    name=net + ': geen vreemde sporen')
        return x0, y0, x1, y1

    # camera slot: keep copper and stitching vias away from its edge
    keepout(board, rect(cx0 - 0.6, cy0 - 0.6, cx1 + 0.6, cy1 + 0.6), allcu, tracks=True, vias=True, pours=False, name='camera-sleuf')

    # high-current copper on the top layer
    # J1 pad 2 -> Q1 drain tab (L-shape: keeps clear of J1's GND pad and of Q1's gate/source legs)
    zone(board, 'VBAT_RAW', pcbnew.F_Cu, [(-30.7, -14.8), (-25.3, -14.8), (-25.3, -19.2), (-15.7, -19.2), (-15.7, -26.4),
                                          (-22.4, -26.4), (-22.4, -20.6), (-30.7, -20.6)], prio=3, name='VBAT_RAW lokaal', connect='full')
    keepout(board, [(-30.3, -15.2), (-25.7, -15.2), (-25.7, -19.6), (-16.1, -19.6), (-16.1, -26.0), (-22.0, -26.0), (-22.0, -21.0),
                     (-30.3, -21.0)], [pcbnew.F_Cu], tracks=True, vias=False, pours=False, name='VBAT_RAW: geen vreemde sporen')
    # Q1 source leg -> shunt (RS1 pad 1, right)
    zone(board, 'VBAT_P', pcbnew.F_Cu, rect(-17.7, -17.9, -15.0, -10.6), prio=3, name='VBAT_P lokaal', connect='full')
    keepout(board, rect(-17.3, -17.5, -15.4, -13.0), [pcbnew.F_Cu], tracks=True, vias=False, pours=False, name='VBAT_P: geen vreemde sporen')
    # the two small VBAT_P taps the autorouter cannot reach through the keep-out: INA226 Vin+ (Kelvin, at the shunt pad)
    # and the gate-clamp zener
    u6, rs = pad_pos(fps['U6'], '10')[0], pad_pos(fps['RS1'], '1')[0]
    xk = rs[0] + 0.45
    for a_, b_ in ((u6, (xk, u6[1])), ((xk, u6[1]), (xk, rs[1] + 1.5))):
        track(board, 'VBAT_P', a_, b_, 0.25)
    d2 = pad_pos(fps['D2'], '1')[0]
    for a_, b_ in ((d2, (d2[0], -18.6)), ((d2[0], -18.6), (-15.2, -17.7))):
        track(board, 'VBAT_P', a_, b_, 0.3)
    vb = local('VBUS', [('RS1', '2')], 0.4)
    local('SW', [('U1', '8'), ('L1', '1'), ('D4', '1')], 0.3, prio=4, ko=False)
    local('V5', [('L1', '2'), ('C9', '1'), ('C10', '1'), ('C11', '1')], 0.3, ko=False)
    # RS1 -> VBUS plane (2 x 2 vias inside the pad area)
    for dx in (0.7, 1.6):
        for dy in (-0.8, 0.8):
            via(board, 'VBUS', (vb[2] - dx, (vb[1] + vb[3]) / 2 + dy))
    # buck output -> bottom 5 V band: vias beside the inductor's 5 V pad (under the inductor body)
    for x in (21.0, 22.3):
        for y in (-16.6, -15.4):
            via(board, 'V5', (x, y))

    # 5 V on the bottom layer: buck output -> Pi header pins 2/4 -> servo
    v5 = [(-26.0, -34.6), (31.6, -34.6), (31.6, -1.0), (28.0, -1.0), (28.0, -10.0), (18.6, -10.0), (18.6, -19.0),
          (28.0, -19.0), (28.0, -28.6), (-26.0, -28.6)]
    zone(board, 'V5', pcbnew.B_Cu, v5, prio=2, name='5V bus (bottom)', connect='full')
    keepout(board, [(-9.8, -34.6)] + v5[1:-1] + [(-9.8, -28.6)], [pcbnew.B_Cu], tracks=True, vias=False, pours=False,
            name='5V bus: geen sporen')

    fanout(board, {'GND', 'VBUS', 'V5'}, {'V5': v5})

    # ---------------- artwork
    F, B = pcbnew.F_SilkS, pcbnew.B_SilkS
    text(board, F, 'SC-02 DRIVE', (-4.0, -1.6), size=1.2, th=0.22, bold=True)
    text(board, F, 'ESP32-S3 + 2x DRV8871  v1.0', (-4.0, 0.2), size=0.6, th=0.11)
    text(board, F, 'CAMERA', ((cx0 + cx1) / 2, cy0 - 1.0), size=0.7)
    text(board, F, 'RST', (-23.5, 25.2), size=0.6)
    text(board, F, 'BOOT', (-19.5, 25.2), size=0.6)
    text(board, F, 'MOTOR 1', (-27.5, -4.4), size=0.7, bold=True)
    text(board, F, 'MOTOR 2', (-27.5, 4.6), size=0.7, bold=True)
    text(board, F, 'G V S', (32.0, -3.5), size=0.6, rot=90)
    text(board, F, 'SERVO', (27.2, -9.2), size=0.7)
    text(board, F, 'HALL', (-29.5, 21.2), size=0.7)
    text(board, F, 'G V S', (-32.0, 24.0), size=0.6, rot=90)
    text(board, F, 'LICHT', (27.2, 6.0), size=0.7, rot=90)
    text(board, F, 'PANEEL', (21.6, 17.6), size=0.7)
    # back side: big name + spider
    back_art(board)
    silk_cleanup(board)
    board.SetFileName(os.path.join(PRJ, NAME + '.kicad_pcb'))
    pcbnew.SaveBoard(os.path.join(PRJ, NAME + '.kicad_pcb'), board)
    write_project()
    return board


# ---------------------------------------------------------------- plane fan-out
def _pt_in_poly(px, py, poly):
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
            c = not c
    return c


def _dist_seg(px, py, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L = dx * dx + dy * dy or 1e-12
    t = max(0, min(1, ((px - a[0]) * dx + (py - a[1]) * dy) / L))
    return math.hypot(a[0] + t * dx - px, a[1] + t * dy - py)


def _edge_dist(px, py):
    e = OUTLINE['edge']
    return min(_dist_seg(px, py, a, b) for a, b in zip(e, e[1:] + e[:1]))


def _rect_seg_hit(r, a, b, m):
    """segment a-b within m of rectangle r=(x0,y0,x1,y1)?"""
    x0, y0, x1, y1 = r[0] - m, r[1] - m, r[2] + m, r[3] + m
    for i in range(21):
        t = i / 20; x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
        if x0 < x < x1 and y0 < y < y1:
            return True
    return False


def fanout(board, plane_nets, regions):
    """Drop a via (+ short track) next to every SMD pad of a plane net that is not already on its own copper."""
    pads = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            r = (pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY, pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY)
            pads.append((p, r, p.GetNetname(), p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD))
    vias = [(pcbnew.ToMM(v.GetPosition().x) - OX, pcbnew.ToMM(v.GetPosition().y) - OY, pcbnew.ToMM(v.GetWidth(pcbnew.F_Cu)) / 2, v.GetNetname())
            for v in board.GetTracks() if v.GetClass() == 'PCB_VIA']
    segs = [((pcbnew.ToMM(t.GetStart().x) - OX, pcbnew.ToMM(t.GetStart().y) - OY), (pcbnew.ToMM(t.GetEnd().x) - OX, pcbnew.ToMM(t.GetEnd().y) - OY),
             pcbnew.ToMM(t.GetWidth()) / 2, t.GetNetname()) for t in board.GetTracks() if t.GetClass() == 'PCB_TRACK']
    blocked = []                         # (poly, allowed_net)
    for z in board.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowVias():
            blocked.append(([(pcbnew.ToMM(z.Outline().CVertex(i).x) - OX, pcbnew.ToMM(z.Outline().CVertex(i).y) - OY)
                             for i in range(z.Outline().TotalVertices())], None))
        elif not z.GetIsRuleArea() and z.GetLayer() == pcbnew.F_Cu:
            blocked.append(([(pcbnew.ToMM(z.Outline().CVertex(i).x) - OX, pcbnew.ToMM(z.Outline().CVertex(i).y) - OY)
                             for i in range(z.Outline().TotalVertices())], z.GetNetname()))
    fps_under = []                       # no vias under the CM5 connectors themselves
    n_ok, n_fail = 0, []
    for p, r, net, smd in pads:
        if net not in plane_nets or not smd or not p.IsOnLayer(pcbnew.F_Cu):
            continue
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        if net in regions and not _pt_in_poly(cx, cy, regions[net]):
            continue
        if any(_pt_in_poly(cx, cy, poly) for poly, an in blocked if an == net):
            continue                     # pad sits on its own copper zone already
        ref = p.GetParentFootprint().GetReference()
        if (ref, p.GetNumber()) in (('U1', '2'),):
            continue
        big = net in ('V12', 'V5')
        vd, vdr, tw = (0.6, 0.3, 0.6) if big else (0.45, 0.2, 0.3)
        hw, hh = (r[2] - r[0]) / 2, (r[3] - r[1]) / 2
        cands = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            for extra in (0.45, 0.75, 1.1, 1.6, 2.2):
                d = (abs(math.cos(a)) * hw + abs(math.sin(a)) * hh) + vd / 2 + extra
                cands.append((extra, k, cx + d * math.cos(a), cy + d * math.sin(a)))
        cands.sort()
        done = False
        for extra, k, vx, vy in cands:
            if _edge_dist(vx, vy) < vd / 2 + 0.5:
                continue
            if any(_pt_in_poly(vx, vy, poly) and an != net for poly, an in blocked):
                continue
            if any(math.hypot(vx - x, vy - y) < rr + vd / 2 + 0.2 for x, y, rr, nn in vias):
                continue
            if any(nn != net and _dist_seg(vx, vy, sa, sb) < sw + vd / 2 + 0.22 for sa, sb, sw, nn in segs):
                continue
            bad = False
            for q, rq, nq, sq in pads:
                if q is p:
                    continue
                if nq == net and not big:
                    m = 0.05
                else:
                    m = 0.2
                # via body
                if rq[0] - m - vd / 2 < vx < rq[2] + m + vd / 2 and rq[1] - m - vd / 2 < vy < rq[3] + m + vd / 2:
                    bad = True; break
                if nq != net and _rect_seg_hit(rq, (cx, cy), (vx, vy), 0.18 + tw / 2):
                    bad = True; break
            if bad:
                continue
            track(board, net, (cx, cy), (vx, vy), tw)
            via(board, net, (vx, vy), d=vd, drill=vdr)
            vias.append((vx, vy, vd / 2, net)); n_ok += 1; done = True
            break
        if not done:
            n_fail.append((ref, p.GetNumber(), net))
    print('fan-out vias:', n_ok, 'failed:', n_fail)


def silk_cleanup(board):
    """Clean silkscreen: only connectors and buttons keep a visible reference (JLC places the rest);
    every leg connector gets a big L1..L6 label on its outer side."""
    import design
    legs = {p['ref']: p['value'].split()[0] for p in design.parts if p['value'].endswith('servo')}
    old = [t for t in board.Drawings() if t.GetClass() == 'PCB_TEXT' and t.GetText().startswith('BUS ')]
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fp.Reference().SetVisible(False)
        if ref in legs:
            x = pcbnew.ToMM(fp.GetPosition().x) - OX; y = pcbnew.ToMM(fp.GetPosition().y) - OY
            sx = 1 if x > 0 else -1
            cy = y - 2.5 if sx > 0 else y + 2.5
            text(board, pcbnew.F_SilkS, legs[ref], (x + sx * 4.1, cy), size=1.2, th=0.22, rot=90 * sx, bold=True)
    for t in old:                     # removing last: KiCad's SWIG proxies go stale after a Remove()
        board.Remove(t)


def back_art(board):
    B = pcbnew.B_SilkS
    text(board, B, 'SC-02', (0, 25.0), size=3.0, th=0.45, mirror=True, bold=True)
    text(board, B, 'solar hypercar drive board', (0, 28.6), size=1.0, th=0.16, mirror=True)
    text(board, B, 'Kobe Van Robaeys  ·  2026', (0, 30.8), size=0.9, th=0.15, mirror=True)


def spider(board, layer, c, s):
    cx, cy = c
    # body (thorax + abdomen) as filled polygons, 6 legs as polylines (mirrored left/right)
    def ell(x, y, rx, ry, n=36):
        return [(x + rx * math.cos(2 * math.pi * i / n), y + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
    shape_poly(board, layer, ell(cx, cy, 5 * s, 6.5 * s))
    shape_poly(board, layer, ell(cx, cy - 8.5 * s, 3.2 * s, 3.0 * s))
    legs = [((3.5, -4), (12, -9), (20, -5)), ((4.5, 0), (14, -1), (23, 4)), ((3.5, 4), (12, 9), (20, 15))]
    for sx in (1, -1):
        for a, b, d in legs:
            pts = [(cx + sx * a[0] * s, cy + a[1] * s), (cx + sx * b[0] * s, cy + b[1] * s), (cx + sx * d[0] * s, cy + d[1] * s)]
            shape_line(board, layer, pts[0], pts[1], 1.0 * s); shape_line(board, layer, pts[1], pts[2], 0.7 * s)


if __name__ == '__main__':
    build()
    print('board written')
    sys.stdout.flush(); os._exit(0)   # KiCad's SWIG objects can crash Python at shutdown
