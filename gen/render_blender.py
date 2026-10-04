"""Product renders of the finished keyboard (3D printed case variant) with Blender Cycles.

    blender -b -P gen/render_blender.py -- [--samples N] [--shots hero,detail] [--res 1800]

Output: docs/img/render-<shot>.png
Geometry comes from case/print/*.stl and <side>/case_data.json, so it always matches the design.
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
MM = 0.001

# heights of the printed case (must match make_case.py)
FLOOR, STANDOFF, PCB_T, PLATE_GAP, PLATE_T = 2.0, 7.0, 1.6, 3.5, 1.5
Z_PLATE_TOP = FLOOR + STANDOFF + PCB_T + PLATE_GAP + PLATE_T
CAP_BOTTOM = Z_PLATE_TOP + 5.6       # keycap skirt above the plate (MX stem + DSA-like cap)
CAP_H = 7.4
GAP_BETWEEN = 70.0                   # mm between the halves
SPLAY = 6.0                          # deg, halves turned outward a little

ORANGE_KEYS = {('left', 'Esc'), ('left', '41'), ('right', 'Backspace'), ('right', 'Enter'), ('right', '64')}

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def arg(name, default):
    return args[args.index(name) + 1] if name in args else default


SAMPLES = int(arg('--samples', '160'))
SHOTS = arg('--shots', 'hero,detail').split(',')
RES = int(arg('--res', '1800'))


# --- materials -----------------------------------------------------------------------
def principled(name, color, rough=0.5, metal=0.0, coat=0.0, sss=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if coat:
        b.inputs['Coat Weight'].default_value = coat
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (1.0, 0.6, 0.4)
        b.inputs['Subsurface Scale'].default_value = 0.002
    return m


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


MAT = {}


def materials():
    MAT['case'] = principled('case', srgb('#d9d8d3'), 0.62)
    MAT['white'] = principled('keycap white', srgb('#f4f3ef'), 0.42, sss=0.15)
    MAT['orange'] = principled('keycap orange', srgb('#f24d00'), 0.45, sss=0.1)
    MAT['switch'] = principled('switch', srgb('#2b2d30'), 0.5)
    MAT['cable'] = principled('cable', srgb('#f23f00'), 0.55)
    MAT['metal'] = principled('metal', srgb('#d7d9dc'), 0.22, metal=1.0)
    MAT['floor'] = principled('backdrop', srgb('#f7f7f7'), 0.9)


# --- geometry helpers -------------------------------------------------------------------
def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def import_stl(path, mat, name):
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[0]
    obj.name = name
    obj.scale = (MM, MM, MM)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
    return obj


def box_mesh(name, w, d, h, top_w=None, top_d=None, top_dy=0.0, bevel=0.0, mat=None):
    top_w = w if top_w is None else top_w
    top_d = d if top_d is None else top_d
    bm = bmesh.new()
    v = []
    for (ww, dd, z, dy) in ((w, d, 0, 0), (top_w, top_d, h, top_dy)):
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            v.append(bm.verts.new((sx * ww / 2 * MM, (sy * dd / 2 + dy) * MM, z * MM)))
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    for f in faces:
        bm.faces.new([v[i] for i in f])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = link(bpy.data.objects.new(name, me))
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        b = obj.modifiers.new('bevel', 'BEVEL')
        b.width = bevel * MM
        b.segments = 5
        b.limit_method = 'NONE'
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def keycap(k, side):
    w = k['w'] * 19.05 - 1.2
    d = k['h'] * 19.05 - 1.2
    color = 'orange' if (side, k['name']) in ORANGE_KEYS or (side, str(k.get('id', ''))) in ORANGE_KEYS else 'white'
    cap = box_mesh('keycap', w, d, CAP_H, w - 5.4, d - 5.4, top_dy=0.4, bevel=1.1, mat=MAT[color])
    cap.location = (k['cx'] * MM, -k['cy'] * MM, CAP_BOTTOM * MM)
    sw = box_mesh('switch', 14.0, 14.0, 6.6, 12.0, 12.0, mat=MAT['switch'])
    sw.location = (k['cx'] * MM, -k['cy'] * MM, Z_PLATE_TOP * MM)
    return [cap, sw]


def knurled_plug(name, length=16.0, radius=3.6):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius * MM, depth=length * MM)
    body = bpy.context.active_object
    body.name = name
    body.data.materials.append(MAT['metal'])
    # knurl: displace with a fine checker-like wave along the circumference
    tex = bpy.data.textures.new('knurl', 'WOOD')
    tex.wood_type = 'BANDNOISE'
    tex.noise_scale = 0.03
    sub = body.modifiers.new('sub', 'SUBSURF')
    sub.levels = sub.render_levels = 2
    sub.subdivision_type = 'SIMPLE'
    disp = body.modifiers.new('knurl', 'DISPLACE')
    disp.texture = tex
    disp.strength = 0.25 * MM
    for p in body.data.polygons:
        p.use_smooth = True
    return body


# --- one keyboard half ------------------------------------------------------------------
def build_half(side, world):
    data = json.load(open(os.path.join(ROOT, side, 'case_data.json')))
    sys.path.insert(0, HERE)
    from layout import load
    for k, src in zip(data['keys'], load(side)):   # same order as the KiCad footprints
        k['id'] = src['id']
    objs = [import_stl(os.path.join(ROOT, 'case', 'print', f'{side}-tray.stl'), MAT['case'], f'{side} tray')]
    plate = import_stl(os.path.join(ROOT, 'case', 'print', f'{side}-plate.stl'), MAT['case'], f'{side} plate')
    plate.location.z = (Z_PLATE_TOP - PLATE_T) * MM
    objs.append(plate)
    for k in data['keys']:
        objs += keycap(k, side)
    bpy.context.view_layer.update()
    for o in objs:
        o.matrix_world = world @ o.matrix_world
    return data


def board_point(world, x, y, z):
    return world @ Vector((x * MM, -y * MM, z * MM))


def cable_path(p0, t0, p3, t3, reach=0.05, floor=2.6 * MM, n=48):
    """Smooth path leaving p0 along t0 and arriving at p3 along -t3, resting on the floor in between."""
    c1, c2 = p0 + t0 * reach, p3 + t3 * reach
    pts = []
    for i in range(n + 1):
        t = i / n
        p = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * p3
        lift = max(0.0, 1 - 4 * min(t, 1 - t)) ** 2          # plug height only near the ends
        z0 = p0.z if t < 0.5 else p3.z
        p.z = floor + (z0 - floor) * lift
        pts.append(p)
    return pts


def cable(name, pts, radius=2.6):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius * MM
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for sp_pt, p in zip(sp.points, pts):
        sp_pt.co = (p.x, p.y, p.z, 1.0)
    obj = link(bpy.data.objects.new(name, cu))
    obj.data.materials.append(MAT['cable'])
    return obj


def plug_at(name, world, mouth_xy, z, outward, length=16.0):
    """Metal plug head sitting in the wall opening, axis along the board's +/-x."""
    x, y = mouth_xy
    head = knurled_plug(name, length)
    axis = (world.to_3x3() @ Vector((outward, 0, 0))).normalized()
    start = board_point(world, x, y, z)
    head.rotation_mode = 'QUATERNION'
    head.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(axis)
    head.location = start + axis * (length / 2 + 1.0) * MM
    tail = start + axis * (length + 1.0) * MM
    return tail, axis


# --- scene ---------------------------------------------------------------------------------
def studio():
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
    sc.view_settings.look = 'AgX - Punchy'
    sc.view_settings.exposure = -0.7
    world = bpy.data.worlds.new('world')
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.25
    # cyclorama: floor that curves up into a back wall
    bm = bmesh.new()
    prof = [(-1.5, 0.0)] + [(0.6 + 0.4 * math.sin(a), 0.4 - 0.4 * math.cos(a))
                            for a in [i * math.pi / 2 / 16 for i in range(17)]] + [(1.0, 1.4)]
    rows = []
    for x in (-2.0, 2.4):
        rows.append([bm.verts.new((x, y, z)) for y, z in prof])
    for i in range(len(prof) - 1):
        bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
    me = bpy.data.meshes.new('cyc')
    bm.to_mesh(me)
    for p in me.polygons:
        p.use_smooth = True
    cyc = link(bpy.data.objects.new('cyclorama', me))
    cyc.location = (0, 0.12, 0)
    cyc.data.materials.append(MAT['floor'])
    # lights: large soft key from the upper left, fill from the right, rim from the back
    for name, loc, size, power, rot in (
            ('key', (-0.45, -0.45, 0.75), 0.9, 70, (math.radians(40), 0, math.radians(-45))),
            ('fill', (0.75, -0.3, 0.4), 0.8, 22, (math.radians(60), 0, math.radians(65))),
            ('top', (0.1, 0.25, 1.0), 1.2, 35, (0, 0, 0))):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.shape = 'DISK'
        ld.size = size
        ld.energy = power
        lo = link(bpy.data.objects.new(name, ld))
        lo.location = loc
        lo.rotation_euler = rot


def camera(name, loc, target, lens, focus, fstop):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.dof.use_dof = True
    cd.dof.focus_distance = (Vector(loc) - Vector(focus)).length
    cd.dof.aperture_fstop = fstop
    cam = link(bpy.data.objects.new(name, cd))
    cam.location = loc
    direction = Vector(target) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return cam


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials()
    studio()

    # place halves: left at origin, right beside it, both turned slightly outward
    dl = json.load(open(os.path.join(ROOT, 'left', 'case_data.json')))
    wl = dl['outline']['x1'] - dl['outline']['x0'] + 2 * 8.5
    W = {}
    for side, sgn in (('left', -1), ('right', 1)):
        o = json.load(open(os.path.join(ROOT, side, 'case_data.json')))['outline']
        w = o['x1'] - o['x0'] + 17.0
        cx, cy = (o['x0'] + o['x1']) / 2, (o['y0'] + o['y1']) / 2
        place = Vector((sgn * (w / 2 + GAP_BETWEEN / 2) * MM, 0, 0))
        W[side] = (Matrix.Translation(place) @ Matrix.Rotation(math.radians(-sgn * SPLAY), 4, 'Z')
                   @ Matrix.Translation(Vector((-cx * MM, cy * MM, 0))))
    data = {s: build_half(s, W[s]) for s in ('left', 'right')}

    # cables ------------------------------------------------------------------------------
    z_conn = FLOOR + STANDOFF - 1.7          # back-side connectors: axis just below the PCB
    ends = {}
    for side in ('left', 'right'):
        d = data[side]
        out = 1 if d['inner_side'] == 'right' else -1
        edge = d['outline']['x1'] + 8.5 if out > 0 else d['outline']['x0'] - 8.5
        for kind in ('trrs', 'usb'):
            if side == 'right' and kind == 'usb':
                continue
            y = d['connectors'][kind]['center'][1]
            tail, axis = plug_at(f'{side} {kind}', W[side], (edge, y), z_conn, out, 14.0 if kind == 'trrs' else 17.0)
            ends[(side, kind)] = (tail, axis)
    (a, aa), (b, ba) = ends[('left', 'trrs')], ends[('right', 'trrs')]
    cable('trrs cable', cable_path(a, aa, b, ba, reach=0.06))
    u, ua = ends[('left', 'usb')]
    # USB cable loops behind the left half and ends on the desk in front, plug lying free (like the photo)
    loose = u + Vector((-0.17, -0.20, 0))
    loose.z = 4.0 * MM
    end_dir = Vector((0.95, 0.3, 0)).normalized()          # direction the loose plug points to
    back = u + Vector((-0.12, 0.15, 0)); back.z = 2.6 * MM  # behind the left half
    side = u + Vector((-0.30, -0.02, 0)); side.z = 2.6 * MM  # around its left end
    pts = cable_path(u, ua, back, Vector((0.9, 0.2, 0)).normalized(), reach=0.08)
    pts += cable_path(back, Vector((-0.95, -0.1, 0)).normalized(), side, Vector((0.1, 0.99, 0)).normalized(), reach=0.10)[1:]
    pts += cable_path(side, Vector((-0.1, -0.99, 0)).normalized(), loose, -end_dir, reach=0.10)[1:]
    for p in pts[10:]:
        p.z = max(p.z, 2.6 * MM)
    cable('usb cable', pts)
    head = knurled_plug('usb loose head', 17.0)
    head.rotation_mode = 'QUATERNION'
    head.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(end_dir)
    head.location = loose + end_dir * 9.0 * MM + Vector((0, 0, 0.6 * MM))
    tongue = box_mesh('usb-c tongue', 8.3, 2.5, 6.6, bevel=1.0, mat=MAT['metal'])
    tongue.rotation_mode = 'QUATERNION'
    tongue.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(end_dir) @ \
        Vector((0, 0, 1)).rotation_difference(Vector((0, 0, 1)))
    tongue.location = loose + end_dir * 17.5 * MM + Vector((0, 0, 0.6 * MM))

    sc = bpy.context.scene
    out_dir = os.path.join(ROOT, 'docs', 'img')
    shots = {
        # wide 3/4 view of both halves (like the second reference photo)
        'hero': dict(loc=(-0.10, -0.80, 0.55), target=(0.0, 0.0, 0.0), lens=62, focus=(-0.06, -0.03, 0.01),
                     fstop=5.6, res=(RES, int(RES * 2 / 3))),
        # close, low view of the left half's inner corner with the cables (like the first photo)
        'detail': dict(loc=(0.06, -0.30, 0.17), target=(-0.075, 0.005, 0.005), lens=55, focus=(-0.04, -0.02, 0.015),
                       fstop=2.8, res=(int(RES * 2 / 3), RES)),
    }
    if '--debug' in args:
        for o in bpy.data.objects:
            if o.type in ('MESH', 'CURVE') and not o.name.startswith(('keycap', 'switch')):
                bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
                lo = [min(v[i] for v in bb) for i in range(3)]
                hi = [max(v[i] for v in bb) for i in range(3)]
                print('OBJ', o.name, [round(v, 3) for v in lo], [round(v, 3) for v in hi])
        bpy.context.view_layer.update()
        n = sum(1 for o in bpy.data.objects if o.name.startswith('keycap'))
        print('keycaps', n)
        return
    for name in SHOTS:
        s = shots[name]
        sc.camera = camera(name, s['loc'], s['target'], s['lens'], s['focus'], s['fstop'])
        sc.render.resolution_x, sc.render.resolution_y = s['res']
        sc.render.filepath = os.path.join(out_dir, f'render-{name}.png')
        bpy.ops.render.render(write_still=True)
        print('rendered', sc.render.filepath)


main()
