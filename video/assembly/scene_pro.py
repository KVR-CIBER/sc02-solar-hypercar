"""SC-02 'pro' renders (Cycles OptiX on lvdell): showroom studio, car paint, carbon weave, rubber, gunmetal rims.
blender -b -P scene_pro.py -- MODE [args]
  test FRAME PCT        one frame of the assembly film at PCT %
  anim                  assembly film (frames_pro/)
  beauty                hero stills of the finished car (beauty/)
  turntable             360 deg turntable of the finished car (turn/)"""
import bpy, os, sys, json, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['test', '400', '25']
MODE = args[0]
FPS, STEP_T, START, OUTRO = 30, 1.25, 2.0, 7.0
STEPS = [  # caption, parts, direction (CAD mm: x fwd, y left, z up) or "side", distance  (same paths as f1/web/build.html)
    ("Vloer · 2 mm zwart plexi", ["floor"], (0, 0, -1), 140),
    ("Achter- en voormodule", ["rear_module", "front_module"], (0, 0, 1), 120),
    ("Lagerblokken", ["rear_bearing_L", "rear_bearing_R"], (0, 0, 1), 100),
    ("Tandwiel 35T", ["spur"], (0, 0, 1), 90),
    ("Achteras door lagers en tandwiel", ["axle_rear"], (0, 1, 0), 170),
    ("Lagerkapjes", ["bearing_cap_L", "bearing_cap_R"], (0, 0, 1), 80),
    ("Brushless 2435 tegen de motorplaat", ["motor_F_can", "motor_F_cap", "motor_F_term", "motor_F_shaft", "pinion_F"], (0, 1, 0), 90),
    ("Motorklem", ["motor_clamp"], (0, 0, 1), 90),
    ("Stuurservo met stuurhoorn", ["servo", "steering_horn"], (0, 0, 1), 110),
    ("Fusees", ["front_upright_L", "front_upright_R"], "side", 60),
    ("Stuurstangen", ["tie_rod_L", "tie_rod_R"], (0, 0, 1), 60),
    ("ESC naast de motor", ["esc_tray", "esc"], (0, 0, 1), 110),
    ("Afstandsbussen", ["pcb_posts"], (0, 0, 1), 110),
    ("Stuurprint v3 · ESP32-S3 + ELRS", ["pcb", "pcb_xt60", "pcb_esp32s3", "pcb_elrs_c3", "pcb_elrs_e28", "pcb_coil", "pcb_usbc",
                                            "pcb_hdr_esc", "pcb_hdr_hall", "pcb_hdr_servo", "pcb_jst_solar"], (0, 0, 1), 130),
    ("Batterijbak boven de print", ["battery_tray"], (0, 0, 1), 130),
    ("LiPo 2S", ["battery"], (0, 0, 1), 130),
    ("Magneetclips", [f"clip_{i}{s}" for i in range(4) for s in "LR"], (0, 0, 1), 80),
    ("Splitter", ["splitter"], (0, 0, -1), 60),
    ("Diffuser", ["diffuser"], (-1, 0, 0), 80),
    ("Achterwielen", ["rim_RL", "tyre_RL", "rim_RR", "tyre_RR"], "side", 140),
    ("Voorwielen", ["rim_FL", "tyre_FL", "rim_FR", "tyre_FR"], "side", 140),
    ("Carrosserie klikt op de magneten", ["body"], (0, 0, 1), 220),
    ("Zonnepaneel", ["panel"], (0, 0, 1), 120),
    ("Koepel", ["canopy"], (0, 0, 1), 120),
    ("Achtervleugel door de sleuven", ["rear_wing"], (0, 0, 1), 150),
]
F0 = int(START * FPS)
N = int((START + len(STEPS) * STEP_T + OUTRO) * FPS)
SF = [(F0 + int(i * STEP_T * FPS), F0 + int((i + 1) * STEP_T * FPS)) for i in range(len(STEPS))]
CX = 0.14                                                  # car centre x (m)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = 'OPTIX'; pr.get_devices()
for d in pr.devices:
    d.use = d.type == 'OPTIX'
sc.cycles.device = 'GPU'
sc.cycles.samples = 96; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.025
sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPTIX'
sc.cycles.max_bounces = 10; sc.cycles.glossy_bounces = 6; sc.cycles.transmission_bounces = 8
sc.cycles.sample_clamp_indirect = 8.0
sc.render.resolution_x, sc.render.resolution_y = 3840, 2160
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
sc.render.use_persistent_data = True
sc.render.film_transparent = False


# ---------------------------------------------------------------- materials
def mat(name, color, rough=0.5, metal=0.0, coat=0.0, coat_rough=0.03, spec=0.5, ior=1.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal; b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = coat_rough; b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['IOR'].default_value = ior
    return m


def nodes(m):
    return m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes['Principled BSDF']


def paint():                                                # deep red metallic paint under a mirror clear coat, fine flakes
    m = mat('lak', (0.42, 0.005, 0.015), 0.32, 0.55, coat=1.0, coat_rough=0.015)
    n, l, b = nodes(m)
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1800; nz.inputs['Detail'].default_value = 1
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.06; bump.inputs['Distance'].default_value = 0.00002
    l.new(nz.outputs['Fac'], bump.inputs['Height']); l.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


def carbon():                                               # 2x2 twill look: anisotropic stripes in two directions
    m = mat('carbon', (0.012, 0.012, 0.014), 0.28, 0.25, coat=1.0, coat_rough=0.02)
    n, l, b = nodes(m)
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (900, 900, 900)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    chk = n.new('ShaderNodeTexChecker'); chk.inputs['Scale'].default_value = 1.0
    chk.inputs['Color1'].default_value = (0.006, 0.006, 0.007, 1); chk.inputs['Color2'].default_value = (0.03, 0.03, 0.034, 1)
    l.new(mp.outputs['Vector'], chk.inputs['Vector']); l.new(chk.outputs['Color'], b.inputs['Base Color'])
    rr = n.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.2; rr.inputs['To Max'].default_value = 0.42
    l.new(chk.outputs['Fac'], rr.inputs['Value']); l.new(rr.outputs['Result'], b.inputs['Roughness'])
    return m


def rubber():
    m = mat('rubber', (0.016, 0.016, 0.018), 0.78, spec=0.35)
    n, l, b = nodes(m)
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 900
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.15; bump.inputs['Distance'].default_value = 0.00005
    l.new(nz.outputs['Fac'], bump.inputs['Height']); l.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


def brushed(name, color, rough=0.22):
    m = mat(name, color, rough, 1.0)
    n, l, b = nodes(m)
    b.inputs['Anisotropic'].default_value = 0.6
    return m


M = dict(body=paint(), canopy=mat('koepel', (0.004, 0.005, 0.008), 0.02, 0.0, coat=1.0, ior=1.52),
         panel=mat('zon', (0.01, 0.025, 0.11), 0.12, 0.35, coat=1.0, coat_rough=0.01), floor=mat('plexi', (0.004, 0.004, 0.005), 0.08, coat=1.0),
         printed=mat('pa_cf', (0.035, 0.036, 0.04), 0.62, spec=0.4), carbon=carbon(),
         dark=mat('anodised', (0.03, 0.03, 0.034), 0.35, 0.8), metal=brushed('alu', (0.8, 0.81, 0.84)),
         gold=brushed('brass', (0.92, 0.66, 0.3), 0.2), rim=brushed('gunmetal', (0.11, 0.11, 0.12), 0.18),
         tyre=rubber(), pcb=mat('pcb', (0.006, 0.035, 0.018), 0.3, coat=0.6),
         esc=mat('esc', (0.02, 0.06, 0.25), 0.3, 0.6), lipo=mat('lipo', (0.02, 0.02, 0.024), 0.3, coat=0.5),
         xt60=mat('xt60', (0.85, 0.6, 0.05), 0.35), servo=mat('servo', (0.01, 0.03, 0.12), 0.4),
         spur=mat('pom', (0.75, 0.75, 0.72), 0.4))


def pick(n):
    if n in M: return M[n]
    if n in ('splitter', 'rear_wing', 'diffuser'): return M['carbon']
    if n.startswith('rim_'): return M['rim']
    if n.startswith('tyre_'): return M['tyre']
    if n == 'battery': return M['lipo']
    if n == 'pcb_xt60': return M['xt60']
    if n in ('pcb_esp32s3', 'pcb_elrs_c3', 'pcb_usbc') or n.endswith(('_can', '_shaft')) or n.startswith(('tie_rod', 'axle', 'steering')): return M['metal']
    if n.startswith('pcb_') or n.endswith('_cap'): return M['dark']
    if n.endswith('_term') or n.startswith('pinion'): return M['gold']
    if n.startswith(('rear_bearing', 'bearing_cap', 'front_upright')): return M['dark']
    return M['printed']


# ---------------------------------------------------------------- car
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, 'sc02.glb'))
ROOT = bpy.data.objects.new('ROOT', None); bpy.context.collection.objects.link(ROOT); ROOT.scale = (0.001,) * 3
objs = {}
for o in list(bpy.context.selected_objects):
    if o.type != 'MESH':
        continue
    n = o.name.split('.')[0]
    o.parent = ROOT; o.matrix_parent_inverse.identity()
    o.location = (0, 0, 0); o.rotation_mode = 'XYZ'; o.rotation_euler = (math.radians(-90), 0, 0); o.scale = (1, 1, 1)
    o.data.materials.clear(); o.data.materials.append(pick(n))
    o.data.shade_smooth() if hasattr(o.data, 'shade_smooth') else None
    if len(o.data.polygons) < 400000:
        o.modifiers.new('ws', 'WEIGHTED_NORMAL').keep_sharp = True
    objs[n] = o
bpy.context.view_layer.update()
for o in objs.values():                                     # auto smooth by angle (keeps hard CAD edges)
    bpy.context.view_layer.objects.active = o
    try:
        o.select_set(True); bpy.ops.object.shade_auto_smooth(angle=math.radians(32)); o.select_set(False)
    except Exception:
        pass


def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3


def dirvec(o, d):
    if d == 'side':
        cy = sum((o.matrix_world @ Vector(c)).y for c in o.bound_box) / 8
        return Vector((0, 1 if cy > 0 else -1, 0))
    return Vector(d)


if MODE in ('anim', 'test'):
    for i, (cap, names, d, dist) in enumerate(STEPS):
        a, b = SF[i]
        for n in names:
            o = objs.get(n)
            if o is None:
                continue
            dv = dirvec(o, d)
            o.hide_render = True; o.keyframe_insert('hide_render', frame=1)
            o.hide_render = False; o.keyframe_insert('hide_render', frame=a)
            for k in range(0, 13):
                o.location = dv * dist * (1 - ease(k / 12)); o.keyframe_insert('location', frame=int(round(a + (b - a) * k / 12)))
    json.dump(dict(fps=FPS, n=N, steps=[[a, b, c] for (a, b), (c, _, _, _) in zip(SF, STEPS)]), open(os.path.join(HERE, 'captions_pro.json'), 'w'))

# ---------------------------------------------------------------- showroom: dark glossy floor, strip softboxes, rim lights
TGT = bpy.data.objects.new('tgt', None); bpy.context.collection.objects.link(TGT); TGT.location = (CX, 0, 0.03)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; wn = w.node_tree.nodes
hdr = os.path.join(HERE, 'studio.hdr')
if os.path.exists(hdr):
    env = wn.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(hdr)
    w.node_tree.links.new(env.outputs['Color'], wn['Background'].inputs['Color'])
wn['Background'].inputs['Strength'].default_value = 0.07
lp = wn.new('ShaderNodeLightPath'); dark = wn.new('ShaderNodeBackground'); dark.inputs['Color'].default_value = (0.002, 0.0022, 0.003, 1)
mx = wn.new('ShaderNodeMixShader')
w.node_tree.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); w.node_tree.links.new(wn['Background'].outputs[0], mx.inputs[1])
w.node_tree.links.new(dark.outputs[0], mx.inputs[2]); w.node_tree.links.new(mx.outputs[0], wn['World Output'].inputs['Surface'])

bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0)); fl = bpy.context.object
fm = mat('showroom', (0.006, 0.0065, 0.008), 0.35, coat=0.15, coat_rough=0.2)
n_, l_, b_ = nodes(fm)
nz = n_.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6
rr = n_.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.3; rr.inputs['To Max'].default_value = 0.45
l_.new(nz.outputs['Fac'], rr.inputs['Value']); l_.new(rr.outputs['Result'], b_.inputs['Roughness'])
fl.data.materials.append(fm)


def strip(name, loc, size, power, rot=(0, 0, 0), color=(1, 1, 1)):
    """rectangular softbox: area light + a visible emissive panel (shows up as a clean streak in the paint)"""
    l = bpy.data.lights.new(name, 'AREA'); l.shape = 'RECTANGLE'; l.size, l.size_y = size; l.energy = power; l.color = color
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o); o.location = loc; o.rotation_euler = rot
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot); p = bpy.context.object
    p.scale = (size[0], size[1], 1); p.location = (loc[0], loc[1], loc[2] + 0.002)
    em = bpy.data.materials.new(name + '_panel'); em.use_nodes = True; nt = em.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF']); e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Strength'].default_value = 1.6
    e.inputs['Color'].default_value = (*color, 1); nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    p.data.materials.append(em); p.visible_camera = False; p.visible_shadow = False
    return o


strip('top_a', (CX - 0.18, 0, 0.95), (1.6, 0.12), 22)
strip('top_b', (CX + 0.18, 0, 0.95), (1.6, 0.12), 22)
strip('top_c', (CX, 0, 1.0), (0.12, 1.4), 12)
k = bpy.data.lights.new('key', 'AREA'); k.size = 1.6; k.energy = 22; ko = bpy.data.objects.new('key', k); bpy.context.collection.objects.link(ko)
ko.location = (CX - 1.1, -1.2, 0.8); c = ko.constraints.new('TRACK_TO'); c.target = TGT; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
for nm, loc, col, en in (('rim_l', (CX + 0.9, 1.1, 0.35), (0.55, 0.75, 1.0), 30), ('rim_r', (CX - 0.9, 1.0, 0.9), (1.0, 0.7, 0.6), 10)):
    r = bpy.data.lights.new(nm, 'AREA'); r.size = 0.5; r.energy = en; r.color = col
    ro = bpy.data.objects.new(nm, r); bpy.context.collection.objects.link(ro); ro.location = loc
    c = ro.constraints.new('TRACK_TO'); c.target = TGT; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'

# ---------------------------------------------------------------- camera
cd = bpy.data.cameras.new('cam'); cd.lens = 85; cd.sensor_width = 36
cd.dof.use_dof = True; cd.dof.focus_object = TGT; cd.dof.aperture_fstop = 6.3; cd.dof.aperture_blades = 7
CAM = bpy.data.objects.new('cam', cd); bpy.context.collection.objects.link(CAM); sc.camera = CAM
tr = CAM.constraints.new('TRACK_TO'); tr.target = TGT; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'


def polar(ang, r, h, tz=0.03, tx=CX):
    return (tx + r * math.cos(math.radians(ang)), r * math.sin(math.radians(ang)), h), (tx, 0, tz)


def shoot(path, f=None):
    sc.render.filepath = path
    if f is not None: sc.frame_set(f)
    bpy.ops.render.render(write_still=True)


if MODE in ('anim', 'test'):
    sc.frame_start, sc.frame_end, sc.render.fps = 1, N, FPS
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.35
    # slow, low, long-lens orbit; pulls in while the electronics go in, opens up for the body, hero push at the end
    keys = [(1, -150, 1.4, 0.5), (SF[6][0], -95, 1.15, 0.38), (SF[13][0], -20, 1.0, 0.45), (SF[16][1], 40, 1.1, 0.32),
            (SF[21][0], 95, 1.3, 0.27), (SF[24][1], 160, 1.25, 0.2), (N, 205, 1.05, 0.12)]
    for f in range(1, N + 1, 3):
        for (fa, aa, ra, ha), (fb, ab, rb, hb) in zip(keys, keys[1:]):
            if fa <= f <= fb:
                t = (f - fa) / max(1, fb - fa); t = t * t * (3 - 2 * t)
                p, tg = polar(aa + (ab - aa) * t, ra + (rb - ra) * t, ha + (hb - ha) * t, tz=0.035 - 0.012 * (f / N))
                CAM.location = p; CAM.keyframe_insert('location', frame=f); TGT.location = tg; TGT.keyframe_insert('location', frame=f)
                break
    sc.render.filepath = os.path.join(HERE, 'frames_pro', '')
    if MODE == 'test':
        f = int(args[1]); sc.render.resolution_percentage = int(args[2]) if len(args) > 2 else 25
        shoot(os.path.join(HERE, f'test_{f:04d}.png'), f)
    else:
        bpy.ops.render.render(animation=True)

elif MODE == 'beauty':
    sc.cycles.samples = 512; sc.cycles.adaptive_threshold = 0.01
    out = os.path.join(HERE, 'beauty'); os.makedirs(out, exist_ok=True)
    SHOTS = [('01_voor_driekwart', -35, 1.35, 0.16, 0.03, CX), ('02_achter_driekwart', 145, 1.35, 0.2, 0.035, CX),
             ('03_zijkant', -90, 1.7, 0.06, 0.03, CX), ('04_laag_neus', -12, 0.95, 0.05, 0.025, CX + 0.12),
             ('05_boven', -60, 0.9, 1.25, 0.0, CX), ('06_achtervleugel', 160, 0.75, 0.12, 0.05, CX - 0.12),
             ('07_wiel_voor', -70, 0.55, 0.06, 0.02, CX + 0.12), ('08_zonnepaneel', 200, 0.95, 0.65, 0.04, CX)]
    if len(args) > 1:                                       # quick look: first shot at 25 %
        SHOTS = SHOTS[:1]; sc.render.resolution_percentage = 25; sc.cycles.samples = 64
    for name, ang, r, h, tz, tx in SHOTS:
        p, tg = polar(ang, r, h, tz, tx); CAM.location = p; TGT.location = tg
        shoot(os.path.join(out, name + '.png'))
    if len(args) > 1:
        sys.exit(0)
    # x-ray: body + canopy + panel see-through glass, the electronics visible
    for nm in ('body', 'canopy', 'panel'):
        o = objs.get(nm)
        if o:
            g = mat('xray_' + nm, (0.9, 0.95, 1.0), 0.05); g.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 1.0
            g.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.25
            o.data.materials.clear(); o.data.materials.append(g)
    p, tg = polar(-50, 1.1, 0.5, 0.03, CX + 0.02); CAM.location = p; TGT.location = tg
    shoot(os.path.join(out, '09_rontgen.png'))
    for nm in ('body', 'canopy', 'panel'):
        if objs.get(nm): objs[nm].data.materials.clear(); objs[nm].data.materials.append(pick(nm))
    # exploded view: every part pulled out along its assembly path
    for cap, names, d, dist in STEPS:
        for n in names:
            o = objs.get(n)
            if o: o.location = dirvec(o, d) * dist * 0.55
    p, tg = polar(-40, 2.0, 0.85, 0.06, CX); CAM.location = p; TGT.location = tg; cd.dof.aperture_fstop = 11
    shoot(os.path.join(out, '10_explosie.png'))

elif MODE == 'turntable':
    sc.frame_start, sc.frame_end, sc.render.fps = 1, 360, FPS
    for f in (1, 361):
        p, tg = polar(-150 + (f - 1), 1.45, 0.22); CAM.location = p; TGT.location = tg
        CAM.keyframe_insert('location', frame=f)
    for fc in CAM.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    # the location keys interpolate on a straight line; drive it on the circle instead
    CAM.animation_data_clear()
    for f in range(1, 361):
        p, tg = polar(-150 + (f - 1), 1.45, 0.22); CAM.location = p; CAM.keyframe_insert('location', frame=f)
    sc.render.filepath = os.path.join(HERE, 'turn', '')
    bpy.ops.render.render(animation=True)

elif MODE == 'steer':
    # servo -> horn -> tie rods -> uprights: front wheels steer +-20 deg about the kingpins while all four wheels roll
    WB, KP, SX, AFZ, ARZ, TF, TR = 230.0, 64.0, 214.0, 21.0, 22.0, 146.0, 150.0
    NFR = 300; sc.frame_start, sc.frame_end, sc.render.fps = 1, NFR, FPS
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.3
    bpy.context.view_layer.update()

    def pivot(name, loc, parent=ROOT):
        e = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(e); e.parent = parent; e.location = loc
        e.rotation_mode = 'XYZ'; return e

    def attach(o, e):
        bpy.context.view_layer.update(); mw = o.matrix_world.copy(); o.parent = e; o.matrix_parent_inverse = e.matrix_world.inverted() @ o.parent.parent.matrix_world if False else e.matrix_world.inverted() @ ROOT.matrix_world; o.matrix_world = mw

    steer, spin = {}, {}
    for side, s in (('L', 1), ('R', -1)):
        k = pivot('kingpin_' + side, (WB, s * KP, 0))
        sp = pivot('spinF_' + side, (0, s * (TF / 2 - KP), AFZ), k)
        steer[side] = k; spin['F' + side] = sp
        spr = pivot('spinR_' + side, (0, s * TR / 2, ARZ)); spin['R' + side] = spr
    bpy.context.view_layer.update()
    for side in 'LR':
        for nm in ('rim_F' + side, 'tyre_F' + side):
            o = objs.get(nm)
            if o: attach(o, spin['F' + side])
        o = objs.get('front_upright_' + side)
        if o: attach(o, steer[side])
        for nm in ('rim_R' + side, 'tyre_R' + side):
            o = objs.get(nm)
            if o: attach(o, spin['R' + side])
    horn = pivot('horn', (SX, 0, 0)); bpy.context.view_layer.update()
    if objs.get('steering_horn'): attach(objs['steering_horn'], horn)
    rods = [objs.get('tie_rod_L'), objs.get('tie_rod_R')]
    # body and wing off so the mechanism is visible; floor, modules, servo stay
    for nm in ('body', 'canopy', 'panel', 'rear_wing'):
        if objs.get(nm): objs[nm].hide_render = True
    for f in range(1, NFR + 1):
        t = (f - 1) / FPS
        a = math.radians(20) * math.sin(2 * math.pi * t / 3.3) * min(1, t / 0.8)
        roll = -t * 2 * math.pi * 0.9                       # ~0.9 wheel turns per second
        for side in 'LR':
            steer[side].rotation_euler = (0, 0, a); steer[side].keyframe_insert('rotation_euler', frame=f)
        for key, e in spin.items():
            e.rotation_euler = (0, roll, 0); e.keyframe_insert('rotation_euler', frame=f)
        horn.rotation_euler = (0, 0, a * 1.15); horn.keyframe_insert('rotation_euler', frame=f)
        for r in rods:
            if r:
                r.location = (0, 9.0 * math.sin(a * 1.15) / 0.001 * 0.001, 0); r.keyframe_insert('location', frame=f)
    for fc in [fc for o in list(steer.values()) + list(spin.values()) + [horn] + [r for r in rods if r] for fc in o.animation_data.action.fcurves]:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    # camera: high front three-quarter, slowly drifting
    for f in (1, NFR):
        u = (f - 1) / (NFR - 1)
        p, tg = polar(-25 + 40 * u, 0.62, 0.38 - 0.08 * u, tz=0.015, tx=0.215); CAM.location = p; TGT.location = tg
        CAM.keyframe_insert('location', frame=f); TGT.keyframe_insert('location', frame=f)
    cd.dof.aperture_fstop = 8
    sc.render.filepath = os.path.join(HERE, 'steer', '')
    if len(args) > 1:
        sc.render.resolution_percentage = 25; shoot(os.path.join(HERE, f'test_steer_{int(args[1]):04d}.png'), int(args[1]))
    else:
        bpy.ops.render.render(animation=True)

elif MODE == 'explain':
    # explainer: the camera flies from part to part, labels + explanation are drawn by overlay_explain.py
    from bpy_extras.object_utils import world_to_camera_view
    mm = lambda x, y, z: Vector((x / 1000, y / 1000, z / 1000))
    SH = [  # title, subtitle, target mm, cam angle, radius m, height m, body visible, labels [(name, anchor mm, text, sub)]
        ("SC-02 Solar Hypercar", "3D-geprint · brushless · ESP32-S3 + ExpressLRS", (140, 0, 30), -35, 1.25, 0.2, True, []),
        ("Onder de carrosserie", "Alles op een zwarte plexi vloer van 2 mm", (140, 0, 20), -60, 1.1, 0.55, False, []),
        ("Aandrijving", "Brushless 2435 · 4500 kV, sim: ~80 km/u, boost ~120", (12, 12, 22), -40, 0.42, 0.22, False,
         [("Motor 2435", (18.5, 16, 34), "Brushless 2435", "4500 kV, op een motorplaat"), ("Tandwiel", (0, -8, 37), "35T + 11T", "module 0.8, 3,18 : 1")]),
        ("Snelheidsregelaar", "ESC naast de motor: korte motordraden", (19, -37, 16), -110, 0.42, 0.25, False,
         [("ESC", (19, -37, 23), "ESC 35 A", "signaal van de ESP32-S3")]),
        ("Het brein", "Stuurprint v3 op afstandsbussen", (95, 5, 14), -150, 0.5, 0.33, False,
         [("ESP32-S3", (115, -2, 15), "ESP32-S3", "rijlogica, boost, limiet"), ("ELRS", (118, 25, 15), "ExpressLRS", "ESP32-C3 + E28, 2,4 GHz"),
          ("XT60", (43, -36, 27), "XT60", "batterij + zonnepaneel in")]),
        ("Batterij", "2S LiPo 1000 mAh op een bakje boven de print", (80, 19, 28), 140, 0.55, 0.35, False,
         [("LiPo", (80, 19, 35), "LiPo 2S", "1000 mAh, 7,4 V")]),
        ("Sturen", "MG90S-servo, stuurhoorn en stuurstangen", (220, 0, 15), -20, 0.45, 0.3, False,
         [("Servo", (214, 0, 31), "Servo MG90S", "±20° stuurhoek"), ("Fusee", (230, 64, 26), "Fusee", "draait om de fuseepen")]),
        ("Zonnepaneel", "1 W paneel laadt de batterij bij", (84, 0, 42), 160, 0.75, 0.55, True,
         [("Paneel", (84, 0, 43), "Zonnepaneel", "5 V, 110 x 60 mm")]),
        ("Aerodynamica", "Carbon-look vleugel door sleuven in de carrosserie", (-33, 0, 45), 155, 0.6, 0.22, True,
         [("Vleugel", (-33, 40, 52), "Achtervleugel", "NACA 6412, twee elementen")]),
        ("Klaar om te racen", "Kobe Van Robaeys · SC-02", (140, 0, 30), 20, 1.3, 0.16, True, []),
    ]
    HOLD, MOVE = 110, 30
    NE = len(SH) * (HOLD + MOVE); sc.frame_start, sc.frame_end, sc.render.fps = 1, NE, FPS
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.3
    body_objs = [objs[n] for n in ('body', 'canopy', 'panel', 'rear_wing', 'splitter', 'diffuser') if n in objs]
    ANCH = {}
    meta = []
    for i, (t, sub, tg, ang, r, h, vis, labels) in enumerate(SH):
        f0 = 1 + i * (HOLD + MOVE); f1 = f0 + MOVE; f2 = f0 + MOVE + HOLD - 1
        p, _ = polar(ang, r, h, tz=tg[2] / 1000, tx=tg[0] / 1000)
        p = (p[0], p[1] + tg[1] / 1000, p[2])
        for f, ang2 in ((f1, ang), (f2, ang + 12)):
            q, _ = polar(ang2, r * (1 if f == f1 else 0.93), h, tz=tg[2] / 1000, tx=tg[0] / 1000)
            CAM.location = (q[0], q[1] + tg[1] / 1000, q[2]); CAM.keyframe_insert('location', frame=f)
            TGT.location = mm(*tg); TGT.keyframe_insert('location', frame=f)
        for o in body_objs:
            o.hide_render = not vis
            o.keyframe_insert('hide_render', frame=f0 + MOVE // 2)
        meta.append(dict(f0=f1, f1=f2, title=t, sub=sub, labels=[[nm, txt, s2] for nm, _, txt, s2 in labels]))
        for nm, a, _, _ in labels:
            e = bpy.data.objects.new('a_' + nm, None); bpy.context.collection.objects.link(e); e.location = mm(*a); ANCH[nm] = e
    for fc in [fc for o in (CAM, TGT) for fc in o.animation_data.action.fcurves]:
        for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'; kp.easing = 'EASE_IN_OUT'
    cd.dof.aperture_fstop = 5.6
    pos = {}
    for f in range(1, NE + 1):
        sc.frame_set(f); row = {}
        for nm, e in ANCH.items():
            v = world_to_camera_view(sc, CAM, e.matrix_world.translation); row[nm] = [round(v.x, 4), round(1 - v.y, 4), round(v.z, 4)]
        pos[f] = row
    json.dump(dict(n=NE, shots=meta, pos=pos), open(os.path.join(HERE, 'explain.json'), 'w'))
    sc.render.filepath = os.path.join(HERE, 'frames_explain', '')
    if len(args) > 1:
        sc.render.resolution_percentage = 25
        for f in [int(a) for a in args[1:]]: shoot(os.path.join(HERE, f'test_explain_{f:04d}.png'), f)
    else:
        bpy.ops.render.render(animation=True)
