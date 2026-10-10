"""Renders of the thumbwheel encoder study (geometry from gen/encoder_study.py).

    blender -b -P gen/render_encoder_study.py -- [--samples N] [--res 1600] [--shots section,exploded]

Output: docs/img/encoder-study/<shot>-<side>[-<design>].png
  section  : the corner cut through the wheel axis, current design and EC05E design (same camera)
  exploded : the EC05E corner with tray, wheel, encoder, PCB, cap and plate pulled apart
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
SRC = os.path.join(ROOT, 'case', 'preview', 'encoder-study')
OUT = os.path.join(ROOT, 'docs', 'img', 'encoder-study')
MM = 0.001

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def arg(name, default):
    return args[args.index(name) + 1] if name in args else default


SAMPLES = int(arg('--samples', '96'))
RES = int(arg('--res', '1600'))
SHOTS = arg('--shots', 'section,exploded').split(',')
SIDES = arg('--sides', 'left').split(',')


def srgb(h):
    h = h.lstrip('#')
    return tuple(((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92
                 for c in (int(h[i:i + 2], 16) for i in (0, 2, 4)))


def principled(name, hexcol, rough=0.5, metal=0.0, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(hexcol), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if transmission:
        b.inputs['Transmission Weight'].default_value = transmission
        b.inputs['IOR'].default_value = 1.49
    return m


def materials():
    return {
        'case': principled('case', '#d9d8d3', 0.62),
        'plate': principled('plate', '#cfd6dc', 0.05, transmission=0.85),
        'wheel': principled('wheel', '#8d939b', 0.45),
        'pcb': principled('pcb', '#1f4d34', 0.4),
        'chip': principled('chip', '#151618', 0.35),
        'magnet': principled('magnet', '#9a9fa6', 0.25, metal=1.0),
        'metal': principled('metal', '#8f959c', 0.3, metal=1.0),
        'encoder': principled('encoder', '#202225', 0.4),
        'floor': principled('backdrop', '#f7f7f7', 0.9),
    }


def import_stl(path, mat, name):
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[0]
    obj.name = name
    obj.scale = (MM, MM, MM)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)
    if obj.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


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
    sc.view_settings.exposure = -0.4
    sc.render.film_transparent = True
    world = bpy.data.worlds.new('world')
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35
    for name, loc, size, power in (('key', (-0.25, -0.30, 0.45), 0.5, 30), ('fill', (0.35, -0.10, 0.25), 0.5, 12),
                                   ('top', (0.0, 0.15, 0.6), 0.8, 18)):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.size, ld.energy = size, power
        lo = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def clear_meshes():
    for o in list(bpy.data.objects):
        if o.type == 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)


def camera(loc, target, lens):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new('cam')
    cd.lens = lens
    cd.clip_start = 0.002
    cam = bpy.data.objects.new('cam', cd)
    sc.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam


def render(path, w, h):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('rendered', path)


def floor(mat, z=0.0):
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0, 0, z))
    bpy.context.active_object.data.materials.append(mat)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mat = materials()
    studio()
    meta = json.load(open(os.path.join(SRC, 'parts.json')))
    os.makedirs(OUT, exist_ok=True)
    for side in SIDES:
        wh = meta['wheel'][side]
        c = Vector((wh['x'], wh['y'], 6.0)) * MM
        out_dir = -1 if side == 'left' else 1                 # the corner (rim exit) is on this x side
        if 'section' in SHOTS:
            for design in ('current', 'encoder'):
                clear_meshes()
                floor(mat['floor'], -0.0005)
                for key, m in meta['parts'].items():
                    if key.startswith(f'{side}-{design}-') and not key.endswith('-plate'):
                        import_stl(os.path.join(SRC, key + '-cut.stl'), mat[m], key)
                # the cut face looks toward +v: view it nearly straight on, a little from above
                v = Vector((*wh['v'], 0))
                u = Vector((*wh['u'], 0))
                t = c + u * 0.004
                camera(t + v * 0.130 + u * 0.010 + Vector((0, 0, 0.040)), t + Vector((0, 0, 0.0005)), 100)
                render(os.path.join(OUT, f'section-{side}-{design}.png'), RES, RES * 2 // 3)
        if 'exploded' in SHOTS:
            clear_meshes()
            floor(mat['floor'], -0.0005)
            lift = meta['explode'][side]
            for key, m in meta['parts'].items():
                if key.startswith(f'{side}-encoder-'):
                    part = key.split('-', 2)[2]
                    o = import_stl(os.path.join(SRC, key + '.stl'), mat[m], key)
                    o.location.z += lift.get(part, 0.0) * MM
            t = c + Vector((0, 0, 0.018))
            camera(t + Vector((-out_dir * 0.100, -0.125, 0.032)), t, 80)
            render(os.path.join(OUT, f'exploded-{side}.png'), RES * 2 // 3 * 1, RES)


main()
