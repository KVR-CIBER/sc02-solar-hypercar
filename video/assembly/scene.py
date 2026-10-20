"""SC-02 assembly film (4K, Cycles OptiX on lvdell): every part flies in along the same collision-free path as
f1/web/build.html.  blender -b -P scene.py -- [still FRAME [PCT] | captions | anim]"""
import bpy, os, sys, json, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['anim']
FPS, STEP_T, START, OUTRO = 30, 1.05, 1.5, 6.0
STEPS = [  # caption, parts, direction (CAD mm: x fwd, y left, z up) or "side", distance  (same order as build.html)
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
step_frames = [(F0 + int(i * STEP_T * FPS), F0 + int((i + 1) * STEP_T * FPS)) for i in range(len(STEPS))]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end, sc.render.fps = 1, N, FPS
sc.render.engine = 'CYCLES'
pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = 'OPTIX'; pr.get_devices()
for d in pr.devices:
    d.use = d.type == 'OPTIX'
sc.cycles.device = 'GPU'; sc.cycles.samples = 40; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.04
sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPTIX'
sc.render.resolution_x, sc.render.resolution_y = 3840, 2160
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.render.use_persistent_data = True


def mat(name, color, rough=0.5, metal=0.0, coat=0.0, alpha=1.0, emit=None, strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal; b.inputs['Coat Weight'].default_value = coat
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = strength
    return m


M = dict(body=mat('body', (0.55, 0.01, 0.025), 0.32, coat=0.8), canopy=mat('canopy', (0.01, 0.012, 0.018), 0.05, 0.3, 1.0),
         panel=mat('panel', (0.02, 0.04, 0.16), 0.15, 0.3, 1.0), floor=mat('floor', (0.01, 0.01, 0.012), 0.12, coat=0.6),
         printed=mat('pla', (0.42, 0.44, 0.48), 0.55), carbon=mat('carbon', (0.02, 0.02, 0.022), 0.3, coat=0.4),
         dark=mat('dark', (0.05, 0.05, 0.055), 0.45, 0.2), metal=mat('metal', (0.75, 0.76, 0.8), 0.18, 1.0),
         gold=mat('gold', (0.9, 0.65, 0.25), 0.25, 1.0), rim=mat('rim', (0.05, 0.05, 0.055), 0.3, 0.7),
         tyre=mat('tyre', (0.018, 0.018, 0.02), 0.85), pcb=mat('pcb', (0.01, 0.06, 0.03), 0.3, coat=0.4),
         esc=mat('esc', (0.03, 0.12, 0.45), 0.4), lipo=mat('lipo', (0.03, 0.03, 0.035), 0.35, coat=0.3),
         xt60=mat('xt60', (0.85, 0.65, 0.1), 0.4), servo=mat('servo', (0.05, 0.12, 0.5), 0.45), spur=mat('spur', (0.85, 0.85, 0.82), 0.35))


def pick(n):
    if n in M: return M[n]
    if n in ('splitter', 'rear_wing', 'diffuser'): return M['carbon']
    if n.startswith('rim_'): return M['rim']
    if n.startswith('tyre_'): return M['tyre']
    if n in ('battery',): return M['lipo']
    if n == 'pcb_xt60': return M['xt60']
    if n in ('pcb_esp32s3', 'pcb_elrs_c3', 'pcb_usbc') or n.endswith(('_can', '_shaft')) or n.startswith(('tie_rod', 'axle', 'steering')): return M['metal']
    if n.startswith('pcb_') or n.endswith('_cap'): return M['dark']
    if n.endswith('_term') or n.startswith('pinion'): return M['gold']
    if n.startswith(('rear_bearing', 'bearing_cap', 'front_upright')): return M['dark']
    return M['printed']


# ---------------------------------------------------------------- car
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, 'sc02.glb'))
ROOT = bpy.data.objects.new('ROOT', None); bpy.context.collection.objects.link(ROOT)
ROOT.scale = (0.001,) * 3
objs = {}
for o in list(bpy.context.selected_objects):
    if o.type != 'MESH':
        continue
    n = o.name.split('.')[0]
    mw = o.matrix_world.copy(); o.parent = ROOT; o.matrix_parent_inverse = ROOT.matrix_world.inverted(); o.matrix_world = mw
    o.data.materials.clear(); o.data.materials.append(pick(n))
    for p in o.data.polygons:
        p.use_smooth = True
    o.modifiers.new('ws', 'WEIGHTED_NORMAL') if len(o.data.polygons) < 200000 else None
    objs[n] = o
# the glb holds car mm coordinates (z up) written as glTF y-up: undo the importer's axis swap
for o in objs.values():
    o.matrix_parent_inverse.identity(); o.location = (0, 0, 0); o.rotation_mode = 'XYZ'; o.rotation_euler = (math.radians(-90), 0, 0); o.scale = (1, 1, 1)
bpy.context.view_layer.update()


def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3


captions = {}
for i, (cap, names, d, dist) in enumerate(STEPS):
    a, b = step_frames[i]
    for n in names:
        o = objs.get(n)
        if o is None:
            print('missing part', n); continue
        if d == 'side':
            cy = sum((o.matrix_world @ Vector(c)).y for c in o.bound_box) / 8     # blender y = car y
            dv = Vector((0, 1 if cy > 0 else -1, 0))
        else:
            dv = Vector(d)
        o.hide_render = True; o.keyframe_insert('hide_render', frame=1)
        o.hide_render = False; o.keyframe_insert('hide_render', frame=a)
        for k in range(0, 9):
            f = a + (b - a) * k / 8
            o.location = dv * dist * (1 - ease(k / 8)); o.keyframe_insert('location', frame=int(round(f)))
        o.location = (0, 0, 0); o.keyframe_insert('location', frame=b + 1)
    captions[i] = (a, b, cap)
json.dump(dict(fps=FPS, n=N, steps=[[a, b, c] for (a, b, c) in captions.values()]), open(os.path.join(HERE, 'captions.json'), 'w'))

# ---------------------------------------------------------------- camera: slow orbit around the car
TGT = bpy.data.objects.new('tgt', None); bpy.context.collection.objects.link(TGT); TGT.location = (0.12, 0, 0.03)
cd = bpy.data.cameras.new('cam'); cd.lens = 55; cd.dof.use_dof = True; cd.dof.focus_object = TGT; cd.dof.aperture_fstop = 11
CAM = bpy.data.objects.new('cam', cd); bpy.context.collection.objects.link(CAM); sc.camera = CAM
tr = CAM.constraints.new('TRACK_TO'); tr.target = TGT; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
for f in range(1, N + 1, 6):
    t = (f - 1) / (N - 1)
    ang = math.radians(-140 + 300 * t)
    r = 1.0 - 0.15 * math.sin(math.pi * t)
    h = 0.42 - 0.18 * t
    CAM.location = (0.12 + r * math.cos(ang), r * math.sin(ang), h); CAM.keyframe_insert('location', frame=f)
    TGT.location = (0.12, 0, 0.035 + 0.02 * (1 - t)); TGT.keyframe_insert('location', frame=f)

# ---------------------------------------------------------------- studio
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; wn = w.node_tree.nodes
hdr = os.path.join(HERE, 'studio.hdr')
if os.path.exists(hdr):
    env = wn.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(hdr)
    w.node_tree.links.new(env.outputs['Color'], wn['Background'].inputs['Color'])
wn['Background'].inputs['Strength'].default_value = 0.3
lp = wn.new('ShaderNodeLightPath'); dark = wn.new('ShaderNodeBackground'); dark.inputs['Color'].default_value = (0.006, 0.0065, 0.008, 1)
mx = wn.new('ShaderNodeMixShader')
w.node_tree.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); w.node_tree.links.new(wn['Background'].outputs[0], mx.inputs[1])
w.node_tree.links.new(dark.outputs[0], mx.inputs[2]); w.node_tree.links.new(mx.outputs[0], wn['World Output'].inputs['Surface'])
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
fm = mat('studio_floor', (0.025, 0.026, 0.03), 0.6); fm.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.25
bpy.context.object.data.materials.append(fm)


def area(name, loc, size, power, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, 'AREA'); l.size = size; l.energy = power; l.color = color
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o); o.location = loc
    c = o.constraints.new('TRACK_TO'); c.target = TGT; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'


area('key', (-0.6, -0.8, 1.0), 1.2, 70)
area('fill', (0.9, 0.6, 0.5), 1.4, 25, (0.85, 0.9, 1.0))
area('rim', (0.4, 1.0, 0.7), 0.8, 50, (0.7, 0.85, 1.0))
area('top', (0.1, 0.0, 1.4), 2.0, 35)
sc.render.filepath = os.path.join(HERE, 'frames', '')

if args[0] == 'still':
    f = int(args[1]); sc.frame_set(f); sc.render.filepath = os.path.join(HERE, f'still_{f:04d}.png')
    if len(args) > 2: sc.render.resolution_percentage = int(args[2])
    bpy.ops.render.render(write_still=True)
elif args[0] == 'anim':
    bpy.ops.render.render(animation=True)
