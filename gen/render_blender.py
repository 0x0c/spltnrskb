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
SHOTS = arg('--shots', 'hero,detail,oled').split(',')
RES = int(arg('--res', '1800'))
OLED_H = arg('--oled-height', None)          # None = built design (cover on the plate); else variant height
OUT_SUFFIX = arg('--suffix', '')
SCREWS = arg('--screws', 'none')             # case screws on the plate: 'none', 'flat' (M2 countersunk, flush) or 'lowpan' (M2 low-head pan)
TOP = arg('--top', 'acrylic')                # switch plate: 'acrylic' (clear, laser cut) or 'print' (printed, with web)
VARIANTS = os.path.join(ROOT, 'case', 'preview', 'oled-variants')


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
    MAT['oled pcb'] = principled('oled pcb', srgb('#1b2a4a'), 0.5)
    MAT['pcb'] = principled('pcb', srgb('#1f4d34'), 0.45, coat=0.5)
    MAT['oled glass'] = principled('oled glass', srgb('#050607'), 0.08, coat=1.0)
    clear = principled('clear acrylic', (1, 1, 1), 0.0)
    b = clear.node_tree.nodes['Principled BSDF']
    b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['IOR'].default_value = 1.49
    MAT['acrylic'] = clear
    # half-mirror acrylic: dark tinted glass with a mirror coat; the OLED shows through where it lights up
    hm = principled('half mirror', (0.18, 0.19, 0.21), 0.02, metal=0.55, coat=1.0)
    hb = hm.node_tree.nodes['Principled BSDF']
    hb.inputs['Transmission Weight'].default_value = 0.6
    hb.inputs['IOR'].default_value = 1.49
    MAT['mirror'] = hm
    glow = bpy.data.materials.new('oled pixels')
    glow.use_nodes = True
    nt = glow.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.75, 0.9, 1.0, 1)
    em.inputs['Strength'].default_value = 25.0
    nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs[0])
    MAT['pixels'] = glow


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
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)     # all faces point outward
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


def oled(data, side, module=None, glass_top=None):
    """0.91 inch module: blue PCB, black glass, glowing status text.
    module = (x0, y0, x1, y1) board-local; glass_top = z of the glass top (default: built design)."""
    if module is None:
        bx0, by0, bx1, by1 = data['oled']['box']
        module = (bx0 + 0.25, by0 + 0.25, bx1 - 0.25, by1 - 0.25)
    x0, y0, x1, y1 = module
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    z = FLOOR + STANDOFF + PCB_T + 2.0 if glass_top is None else glass_top - 2.6
    pcb = box_mesh('oled pcb', x1 - x0, y1 - y0, 1.2, mat=MAT['oled pcb'])
    pcb.location = (cx * MM, -cy * MM, z * MM)
    horizontal = (x1 - x0) > (y1 - y0)
    pins_at_bottom = side == 'left'                 # header end; the glass sits toward the other end
    if horizontal:
        gx, gy = cx + 3.0, cy
        glass = box_mesh('oled glass', 30.0, 11.4, 1.4, bevel=0.2, mat=MAT['oled glass'])
        glass.location = (gx * MM, -gy * MM, (z + 1.2) * MM)
    else:
        gy = cy - 3.0 if pins_at_bottom else cy + 3.0
        glass = box_mesh('oled glass', 11.4, 30.0, 1.4, bevel=0.2, mat=MAT['oled glass'])
        glass.location = (cx * MM, -gy * MM, (z + 1.2) * MM)
    out = [pcb, glass]
    if horizontal:
        lines = ['nrsk  LAYER 0', 'CAPS'] if side == 'left' else ['nrsk  WPM 72', '']
        for i, line in enumerate(lines):
            if not line:
                continue
            cu = bpy.data.curves.new(f'oled text {i}', 'FONT')
            cu.body = line
            cu.size = 3.0 * MM
            t = link(bpy.data.objects.new(f'oled text {i}', cu))
            t.data.materials.append(MAT['pixels'])
            t.location = ((gx - 12.5) * MM, -(gy - 1.0 + i * 4.2) * MM, (z + 2.62) * MM)
            out.append(t)
        return out
    for i, line in enumerate(lines := (['nrsk', '', 'LAYR0', '', 'CAPS'] if side == 'left' else ['nrsk', '', 'WPM', ' 72'])):
        if not line:
            continue
        cu = bpy.data.curves.new(f'oled text {i}', 'FONT')
        cu.body = line
        cu.size = 2.6 * MM
        cu.align_x = 'LEFT'
        t = link(bpy.data.objects.new(f'oled text {i}', cu))
        t.data.materials.append(MAT['pixels'])
        # text runs across the 12 mm width, lines stack down the 30 mm glass (display rotated 270)
        t.location = ((cx - 4.6) * MM, -(gy - 12.5 + i * 3.6) * MM, (z + 2.62) * MM)
        out.append(t)
    return out


def corner_wheel(side):
    """Knurled thumbwheel lying under the PCB at the case corner (geometry from case/print)."""
    w = import_stl(os.path.join(ROOT, 'case', 'print', f'{side}-wheel.stl'), MAT['metal'], f'{side} wheel')
    w.location.z = (FLOOR + 0.3) * MM
    return [w]


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
def flat_screw(name, x, y):
    """M2 countersunk (90 deg) head flush with the plate top, with a Phillips recess."""
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=1.0 * MM, radius2=1.9 * MM, depth=0.9 * MM,
                                    location=(x * MM, -y * MM, (Z_PLATE_TOP - 0.45) * MM))
    head = bpy.context.active_object
    head.name = name
    head.data.materials.append(MAT['metal'])
    for o in bpy.context.selected_objects:
        o.select_set(False)
    parts = [head]
    for rot in (0, 90):
        r = box_mesh(name + ' recess', 0.45, 2.0, 0.25, mat=MAT['switch'])
        r.location = (x * MM, -y * MM, (Z_PLATE_TOP - 0.25) * MM)
        r.rotation_euler = (0, 0, math.radians(rot))
        parts.append(r)
    return parts


def lowpan_screw(name, x, y, d=4.0, h=0.5):
    """M2 slim-head (low-profile pan) screw, 4.0 mm x 0.5 mm, sitting on the plate, with a Phillips recess."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=d / 2 * MM, depth=h * MM,
                                        location=(x * MM, -y * MM, (Z_PLATE_TOP + h / 2) * MM))
    head = bpy.context.active_object
    head.name = name
    bev = head.modifiers.new('round', 'BEVEL')
    bev.width = 0.2 * MM
    bev.segments = 4
    head.data.materials.append(MAT['metal'])
    for o in bpy.context.selected_objects:
        o.select_set(False)
    parts = [head]
    for rot in (0, 90):
        r = box_mesh(name + ' recess', 0.45, 2.0, 0.2, mat=MAT['switch'])
        r.location = (x * MM, -y * MM, (Z_PLATE_TOP + h - 0.18) * MM)
        r.rotation_euler = (0, 0, math.radians(rot))
        parts.append(r)
    return parts


def build_half(side, world):
    data = json.load(open(os.path.join(ROOT, side, 'case_data.json')))
    sys.path.insert(0, HERE)
    from layout import load
    for k, src in zip(data['keys'], load(side)):   # same order as the KiCad footprints
        k['id'] = src['id']
    objs = [import_stl(os.path.join(ROOT, 'case', 'print', f'{side}-tray.stl'), MAT['case'], f'{side} tray')]
    if TOP == 'print':     # printed plate with its stiffening web (case/print/<side>-plate.stl)
        plate = import_stl(os.path.join(ROOT, 'case', 'print', f'{side}-plate.stl'), MAT['case'], f'{side} plate')
    else:                  # clear acrylic plate (the laser-cut part, placed by make_case.py)
        plate = import_stl(os.path.join(ROOT, 'case', 'preview', f'{side}-plate-placed.stl'), MAT['acrylic'], f'{side} plate')
        plate.location.z = -(FLOOR + STANDOFF + PCB_T + PLATE_GAP) * MM   # the placed STL already sits at plate height
    plate.location.z += (Z_PLATE_TOP - PLATE_T) * MM
    objs.append(plate)
    objs.append(import_stl(os.path.join(ROOT, 'case', 'print', f'{side}-wheel-cap.stl'), MAT['case'], f'{side} wheel cap'))
    if TOP != 'print':     # through the clear plate the board shows: green PCB slab
        pcb = import_stl(os.path.join(ROOT, 'case', 'preview', f'{side}-pcb.stl'), MAT['pcb'], f'{side} pcb')
        objs.append(pcb)
    for k in data['keys']:
        objs += keycap(k, side)
    if SCREWS in ('flat', 'lowpan'):
        rep = json.load(open(os.path.join(ROOT, 'case', 'case_report.json')))
        make = flat_screw if SCREWS == 'flat' else lowpan_screw
        for i, (x, y) in enumerate(rep[side]['screws_xy']):
            objs += make(f'{side} screw {i}', x, y)
    if OLED_H is None:
        objs += oled(data, side)
        cover = import_stl(os.path.join(ROOT, 'case', 'preview', f'{side}-oled-cover.stl'), MAT['mirror'], f'{side} cover')
        cover.location.z = (Z_PLATE_TOP - 2.0) * MM    # 2 mm half-mirror inlay, top flush with the plate
        objs.append(cover)
        data['oled_module'] = None
    objs += corner_wheel(side)
    if OLED_H is not None and OLED_H not in ('0', '0.0'):
        # the display moved away from the plate window: close the window (plate without it)
        fill = import_stl(os.path.join(VARIANTS, f'{side}-lens-0.stl'), MAT['case'], f'{side} window fill')
        fill.location.z = Z_PLATE_TOP * MM
        objs.append(fill)
    if OLED_H is None:
        pass
    elif OLED_H.startswith('tilt'):
        v = json.load(open(os.path.join(VARIANTS, 'variants.json')))
        f = v[side]['tilted'][OLED_H]
        for kind, mat in (('pod', MAT['case']), ('lens', MAT['acrylic'])):
            o = import_stl(os.path.join(VARIANTS, f'{side}-{kind}-{OLED_H}.stl'), mat, f'{side} {kind}')
            o.location.z = Z_PLATE_TOP * MM
            objs.append(o)
        # module built flat in a local frame (front edge at y=0, sloping up toward the back), then tilted
        w, L = f['w'], f['L']
        parts = oled(data, side, (-w / 2, -L, w / 2, 0.0), -v['lens_t'])
        bpy.context.view_layer.update()
        frame = (Matrix.Translation((f['cx'] * MM, -f['yf'] * MM, (Z_PLATE_TOP + f['zf']) * MM))
                 @ Matrix.Rotation(math.radians(f['deg']), 4, 'X'))
        for o in parts:
            o.matrix_world = frame @ o.matrix_world
        objs += parts
        depth = L * math.cos(math.radians(f['deg']))
        data['oled_module'] = (f['cx'] - w / 2, f['yf'] - depth, f['cx'] + w / 2, f['yf'])
    else:
        v = json.load(open(os.path.join(VARIANTS, 'variants.json')))
        h = float(OLED_H)
        tag = f'{h:g}'
        if h > 0:
            module = v[side]['raised_module']
            pod = import_stl(os.path.join(VARIANTS, f'{side}-pod-{tag}.stl'), MAT['case'], f'{side} pod')
            pod.location.z = Z_PLATE_TOP * MM
            objs.append(pod)
        else:
            bx0, by0, bx1, by1 = v[side]['flush_module']
            module = (bx0 + 0.25, by0 + 0.25, bx1 - 0.25, by1 - 0.25)
        objs += oled(data, side, module, Z_PLATE_TOP + h - v['lens_t'])
        lens = import_stl(os.path.join(VARIANTS, f'{side}-lens-{tag}.stl'), MAT['acrylic'], f'{side} lens')
        lens.location.z = Z_PLATE_TOP * MM
        objs.append(lens)
        data['oled_module'] = module
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
    """Metal plug head sitting in the wall opening; outward = (dx, dy) in board coordinates (y down)."""
    x, y = mouth_xy
    head = knurled_plug(name, length)
    axis = (world.to_3x3() @ Vector((outward[0], -outward[1], 0))).normalized()
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
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.005
    sc.render.film_transparent = False
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
    ob = data['left']['oled_module'] or data['left']['oled']['box']
    oled_c = board_point(W['left'], (ob[0] + ob[2]) / 2, (ob[1] + ob[3]) / 2, Z_PLATE_TOP)

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
            c = d['connectors'][kind]
            if c.get('edge') == 'top':     # USB-C on the back edge
                mouth, direction = (c['center'][0], d['outline']['y0'] - 8.5), (0, -1)
            else:
                mouth, direction = (edge, c['center'][1]), (out, 0)
            tail, axis = plug_at(f'{side} {kind}', W[side], mouth, z_conn, direction, 14.0 if kind == 'trrs' else 17.0)
            ends[(side, kind)] = (tail, axis)
    (a, aa), (b, ba) = ends[('left', 'trrs')], ends[('right', 'trrs')]
    cable('trrs cable', cable_path(a, aa, b, ba, reach=0.06))
    u, ua = ends[('left', 'usb')]
    # USB cable leaves the back edge and runs off behind the keyboard (to the computer)
    far = u + Vector((-0.06, 0.40, 0)); far.z = 2.6 * MM
    pts = cable_path(u, ua, far, Vector((-0.1, 0.99, 0)).normalized(), reach=0.12)
    for p in pts[6:]:
        p.z = max(p.z, 2.6 * MM)
    cable('usb cable', pts)

    sc = bpy.context.scene
    out_dir = os.path.join(ROOT, 'docs', 'img')
    shots = {
        # wide 3/4 view of both halves (like the second reference photo)
        'hero': dict(loc=(-0.10, -0.80, 0.55), target=(0.0, 0.0, 0.0), lens=62, focus=(-0.06, -0.03, 0.01),
                     fstop=5.6, res=(RES, int(RES * 2 / 3))),
        # close, low view of the left half's inner corner with the cables (like the first photo)
        'detail': dict(loc=(0.06, -0.30, 0.17), target=(-0.075, 0.005, 0.005), lens=55, focus=(-0.04, -0.02, 0.015),
                       fstop=5.6, res=(int(RES * 2 / 3), RES)),
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
    c = oled_c
    shots['oled'] = dict(loc=tuple(c + Vector((0.07, -0.13, 0.12))), target=tuple(c + Vector((-0.012, 0.0, 0.0))),
                         lens=90, focus=tuple(c), fstop=8.0, res=(RES, int(RES * 2 / 3)))
    # what a seated typist sees: from the front, ~45 cm away and ~30 cm above the desk
    shots['user'] = dict(loc=tuple(c + Vector((-0.10, -0.40, 0.30))), target=tuple(c + Vector((-0.03, -0.02, 0.0))),
                         lens=50, focus=tuple(c), fstop=8.0, res=(RES, int(RES * 2 / 3)))
    # close-ups of the corner wheels
    for side, sx in (('left', -1), ('right', 1)):
        o = data[side]['outline']
        cx = (o['x0'] - 6.0) if side == 'left' else (o['x1'] + 6.0)
        t = board_point(W[side], cx, o['y0'] - 6.0, 5.0)
        shots[f'wheel-{side}'] = dict(loc=tuple(t + Vector((sx * 0.12, 0.05, 0.10))), target=tuple(t),
                                      lens=75, focus=tuple(t), fstop=5.6, res=(RES, int(RES * 2 / 3)))
    for name in SHOTS:
        s = shots[name]
        sc.camera = camera(name, s['loc'], s['target'], s['lens'], s['focus'], s['fstop'])
        sc.render.resolution_x, sc.render.resolution_y = s['res']
        sc.render.filepath = os.path.join(out_dir, f'render-{name}{OUT_SUFFIX}.png')
        bpy.ops.render.render(write_still=True)
        print('rendered', sc.render.filepath)


main()
