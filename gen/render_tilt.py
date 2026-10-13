"""Renders of the tilt-leg study (docs/specs/case-feet-tilt.md step 3), one mechanism per run, left half.

    blender -b -P gen/render_tilt.py -- --mech M [--samples 48] [--res 1000]

Geometry: case/preview/tilt-variants/<mech>/ (gen/tilt_variants.py) with the tray's plate, wheel and wheel cap
from case/print and the keys from left/case_data.json. Writes docs/img/tilt-study/<mech>-<shot>.jpg:
  side-<deg>   from the outer (wheel) side, standing on the desk at 0 / 3 / 6 / 9 degrees
  bottom-0     from below, legs off (F: folded)
  bottom-legs  from below, legs on at the steepest angle (F: both unfolded)
  back         behind the wheel corner at the steepest angle, with the USB-C plugs in
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
MM = 0.001
SIDE = 'left'
FLOOR, STANDOFF, PCB_T, PLATE_GAP, PLATE_T = 2.0, 7.0, 1.6, 3.5, 1.5      # as make_case.py
Z_PLATE_TOP = FLOOR + STANDOFF + PCB_T + PLATE_GAP + PLATE_T
CAP_BOTTOM, CAP_H = Z_PLATE_TOP + 5.6, 7.4                                # as render_blender.py
FOOT_D, FOOT_H, FOOT_DEPTH = 9.5, 3.8, 1.0
USB_Z = FLOOR + STANDOFF - 1.7

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def arg(name, default):
    return args[args.index(name) + 1] if name in args else default


MECH = arg('--mech', 'M')
SAMPLES = int(arg('--samples', '48'))
RES = int(arg('--res', '1000'))
VAR = os.path.join(ROOT, 'case', 'preview', 'tilt-variants')
OUT = os.path.join(ROOT, 'docs', 'img', 'tilt-study')


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def material(name, hexcolor, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(hexcolor), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def import_stl(path, mat, parent):
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[0]
    obj.scale = (MM, MM, MM)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
    obj.parent = parent
    return obj


def box(name, size, loc, mat, parent, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=[v * MM for v in loc])
    o = bpy.context.active_object
    o.name = name
    o.scale = [v * MM for v in size]
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel * MM
        mod.segments = 3
    o.data.materials.append(mat)
    o.parent = parent
    return o


def cylinder(name, d, h, loc, mat, parent):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=d / 2 * MM, depth=h * MM, location=[v * MM for v in loc])
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    o.parent = parent
    return o


def scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = 'GPU'
    except Exception:
        sc.cycles.device = 'CPU'
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'AgX'
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 88
    world = bpy.data.worlds.new('world')
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (*srgb('#f2f2ef'), 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
    sun = bpy.data.lights.new('sun', 'SUN')
    sun.energy = 2.5
    sun.angle = math.radians(8)
    so = link(bpy.data.objects.new('sun', sun))
    so.rotation_euler = (math.radians(35), math.radians(-20), math.radians(-30))
    under = bpy.data.lights.new('under', 'SUN')           # for the views from below
    under.energy = 2.5
    uo = link(bpy.data.objects.new('under', under))
    uo.rotation_euler = (math.radians(160), math.radians(15), 0)
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.05, -0.05, 0))
    floor = bpy.context.active_object
    floor.name = 'desk'
    floor.data.materials.append(material('desk', '#e9e8e4', 0.85))
    return so, uo, floor


def tilt(deg, front_y):
    """Tray frame -> world: raised at the back by deg about the front feet's contact line, standing on z = 0."""
    p = Vector((0, -front_y * MM, -(FOOT_H - FOOT_DEPTH) * MM))
    return (Matrix.Translation(Vector((0, 0, (FOOT_H - FOOT_DEPTH) * MM))) @ Matrix.Translation(p)
            @ Matrix.Rotation(math.radians(deg), 4, 'X') @ Matrix.Translation(-p))


def camera(name, loc, target, ortho=None, lens=50, roll=0.0):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho * MM
    else:
        cd.lens = lens
    cd.clip_start, cd.clip_end = 0.001, 10.0
    cam = link(bpy.data.objects.new(name, cd))
    cam.location = [v * MM for v in loc]
    q = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y')
    cam.rotation_euler = (q @ Matrix.Rotation(math.radians(roll), 4, 'Z').to_quaternion()).to_euler()
    return cam


def main():
    sun, under, desk = scene()
    rep = json.load(open(os.path.join(VAR, 'variants.json')))[MECH][SIDE]
    data = json.load(open(os.path.join(ROOT, SIDE, 'case_data.json')))
    case_rep = json.load(open(os.path.join(ROOT, 'case', 'case_report.json')))[SIDE]
    front_y = max(y for _, y in case_rep['feet_xy'])
    angles = sorted(int(a) for a in rep['angles'])
    mats = dict(case=material('case', '#d9d8d3', 0.62), key=material('key', '#f4f3ef', 0.45),
                leg=material('leg', '#e07a2f', 0.55), rubber=material('rubber', '#2b2b2b', 0.8),
                metal=material('metal', '#c9ccd0', 0.25, 1.0), plug=material('plug', '#3a3d42', 0.5),
                switch=material('switch', '#2b2d30', 0.5))
    kb = link(bpy.data.objects.new('keyboard', None))
    import_stl(os.path.join(VAR, MECH, f'{SIDE}-tray.stl'), mats['case'], kb)
    plate = import_stl(os.path.join(ROOT, 'case', 'print', f'{SIDE}-plate.stl'), mats['case'], kb)
    plate.location.z = (Z_PLATE_TOP - PLATE_T) * MM
    import_stl(os.path.join(ROOT, 'case', 'print', f'{SIDE}-wheel-cap.stl'), mats['case'], kb)
    wheel = import_stl(os.path.join(ROOT, 'case', 'print', f'{SIDE}-wheel.stl'), mats['metal'], kb)
    wheel.location.z = (FLOOR + 0.3) * MM
    for k in data['keys']:
        w, d = k['w'] * 19.05 - 1.2, k['h'] * 19.05 - 1.2
        box('key', (w, d, CAP_H), (k['cx'], -k['cy'], CAP_BOTTOM + CAP_H / 2), mats['key'], kb, bevel=1.0)
        box('switch', (14.0, 14.0, 5.6), (k['cx'], -k['cy'], Z_PLATE_TOP + 2.8), mats['switch'], kb)
    feet = [cylinder('foot', FOOT_D, FOOT_H, (x, -y, FOOT_DEPTH - FOOT_H / 2), mats['rubber'], kb)
            for x, y in case_rep['feet_xy']]
    for c in data['connectors'].values():          # USB-C plugs in the back-edge ports
        if c.get('edge') == 'top':
            y0 = -data['outline']['y0'] + 8.5
            box('plug', (12.5, 22.0, 7.0), (c['center'][0], y0 + 11.0 - 2.0, USB_Z), mats['plug'], kb, bevel=1.5)
            cylinder('cable', 4.0, 30.0, (c['center'][0], y0 + 20.0 + 15.0, USB_Z), mats['plug'], kb).rotation_euler = (
                math.radians(90), 0, 0)
    legs = {}
    for fn in sorted(os.listdir(os.path.join(VAR, MECH))):
        if fn.startswith(f'{SIDE}-') and fn != f'{SIDE}-tray.stl':
            kind, *rest = fn[len(SIDE) + 1:-4].split('-')
            seat, deg = rest[0], int(rest[1])
            legs[(kind, seat, deg)] = import_stl(os.path.join(VAR, MECH, fn),
                                                 mats['rubber' if kind == 'legfoot' else 'leg'], kb)

    def show(deg, unfolded=None):
        """Legs for deg on (0: off; F: folded), feet always; unfolded overrides which F legs stand."""
        on = {deg} if unfolded is None else unfolded
        for (kind, seat, d), o in legs.items():
            vis = (kind in ('leg', 'legfoot') and d in on) or (kind == 'folded' and d not in on)
            o.hide_render = not vis
        kb.matrix_world = tilt(deg if unfolded is None else 0, front_y)

    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene

    def shot(name, cam, w, h, below=False):
        sc.camera = cam
        sc.render.resolution_x, sc.render.resolution_y = w, h
        desk.hide_render = below
        sun.hide_render, under.hide_render = below, not below
        sc.render.filepath = os.path.join(OUT, f'{MECH}-{name}.jpg')
        bpy.ops.render.render(write_still=True)
        print('wrote', sc.render.filepath)

    xs = [-11.5, data['outline']['x1'] + 8.5]
    cy = -(data['outline']['y0'] + data['outline']['y1']) / 2
    side = camera('side', (-600, cy, 22), (0, cy, 22), ortho=185)
    for deg in [0] + [3, 6, 9]:
        if deg and deg not in angles:
            continue
        show(deg)
        shot(f"side-{deg}", side, RES, int(RES * 0.42))
    # from below, the back of the half at the top of the picture (seen from below, left and right swap)
    below = camera('below', ((xs[0] + xs[1]) / 2, cy, -600), ((xs[0] + xs[1]) / 2, cy, 0), ortho=200, roll=180)
    show(0)
    shot('bottom-0', below, RES, int(RES * 0.8), below=True)
    show(0, unfolded=set(angles) if MECH == 'F' else {max(angles)})
    shot('bottom-legs', below, RES, int(RES * 0.8), below=True)
    show(max(angles))
    back = camera('back', (-70, 200, 75), (70, 5, 4), lens=40)
    shot('back', back, RES, int(RES * 0.66))


main()
