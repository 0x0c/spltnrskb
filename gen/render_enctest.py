"""Render of the encoder test kit (3D printed tray and plate, the keyboard's wheel and drum parts, the RP2040-Zero
under the board with its USB-C in the left wall) with Blender.

    blender -b -P gen/render_enctest.py -- [--samples N] [--res 1400] [--shots enctest,enctest-wheel]

Output: docs/img/enctest.png (the kit from the front left) and docs/img/enctest-wheel.png (the thumbwheel's corner).
Geometry: enctest/case/ (tray, plate, PCB) and the keyboard's case/print/right-wheel*.stl
and case/preview/right-drum*-placed.stl, which make_enctest.py checks to fit the test case as they fit the keyboard.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
MM = 0.001
FLOOR, STANDOFF, PCB_T, PLATE_GAP, PLATE_T, WHEEL_GAP = 2.0, 7.0, 1.6, 3.5, 1.5, 0.3   # = make_case.py
Z_PCB = FLOOR + STANDOFF

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SAMPLES = int(args[args.index('--samples') + 1]) if '--samples' in args else 96
RES = int(args[args.index('--res') + 1]) if '--res' in args else 1400
SHOTS = args[args.index('--shots') + 1].split(',') if '--shots' in args else ['enctest', 'enctest-wheel']


def material(name, color, rough=0.5, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Alpha'].default_value = alpha
    b.inputs['Transmission Weight'].default_value = transmission
    return m


MAT = {}


def stl(path, mat, z=0.0):
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    o.scale = (MM, MM, MM)
    o.location.z = z * MM
    o.data.materials.append(mat)
    return o


def box(x0, y0, z0, x1, y1, z1, mat):
    """Box in board-local mm (y down), z up."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.scale = ((x1 - x0) * MM, (y1 - y0) * MM, (z1 - z0) * MM)
    o.location = ((x0 + x1) / 2 * MM, -(y0 + y1) / 2 * MM, (z0 + z1) / 2 * MM)
    o.data.materials.append(mat)
    return o


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MAT.update(tray=material('tray', (0.85, 0.85, 0.82), 0.6), pcb=material('pcb', (0.05, 0.18, 0.08), 0.4),
               plate=material('plate', (0.75, 0.76, 0.78), 0.6), zero=material('zero', (0.05, 0.15, 0.45), 0.4),
               usb=material('usb', (0.75, 0.75, 0.78), 0.25),
               wheel=material('wheel', (0.9, 0.35, 0.05), 0.5), drum=material('drum', (0.08, 0.08, 0.09), 0.35),
               bezel=material('bezel', (0.2, 0.2, 0.22), 0.6), cap=material('cap', (0.92, 0.92, 0.9), 0.5),
               pin=material('pin', (0.85, 0.7, 0.3), 0.3), black=material('black', (0.02, 0.02, 0.02), 0.5),
               floor=material('floor', (0.6, 0.6, 0.62), 0.9))
    d = json.load(open(os.path.join(ROOT, 'enctest', 'case_data.json')))
    case, kb = os.path.join(ROOT, 'enctest', 'case'), os.path.join(ROOT, 'case')
    stl(os.path.join(case, 'print', 'enctest-tray.stl'), MAT['tray'])
    stl(os.path.join(case, 'preview', 'enctest-pcb.stl'), MAT['pcb'])
    stl(os.path.join(case, 'preview', 'enctest-plate-placed.stl'), MAT['plate'])
    stl(os.path.join(kb, 'print', 'right-wheel.stl'), MAT['wheel'], FLOOR + WHEEL_GAP)
    stl(os.path.join(kb, 'print', 'right-wheel-cap.stl'), MAT['tray'])
    for name, mat in (('drum', 'drum'), ('drum-block', 'bezel'), ('drum-bezel', 'bezel')):
        stl(os.path.join(kb, 'preview', f'right-{name}-placed.stl'), MAT[mat])
    # the RP2040-Zero under the board, face down on its ConThrough pins, USB-C in the left wall's opening
    m = d['mcu']
    (zx, zy), (zl, zw), u = m['center'], m['size'], m['usb']
    zb = Z_PCB - m['stack']                          # the module's back, under this board
    for x, y in m['pins']:
        box(x - 0.3, y - 0.3, zb - m['t'] - 0.8, x + 0.3, y + 0.3, Z_PCB + PCB_T + 0.8, MAT['pin'])
    for y in sorted({p[1] for p in m['pins']}):
        xs = [p[0] for p in m['pins'] if p[1] == y]
        box(min(xs) - 1.27, y - 1.0, zb, max(xs) + 1.27, y + 1.0, Z_PCB, MAT['black'])
    box(zx - zl / 2, zy - zw / 2, zb - m['t'], zx + zl / 2, zy + zw / 2, zb, MAT['zero'])
    face = zb - m['t']
    box(zx - zl / 2 - u['out'], zy - u['width'] / 2, face - u['up'], zx - zl / 2 + 7.3, zy + u['width'] / 2,
        face + u['into'], MAT['usb'])
    sx, sy = d['buttons'][0]
    box(sx - 3.0, sy - 3.0, Z_PCB + PCB_T, sx + 3.0, sy + 3.0, Z_PCB + PCB_T + 3.5, MAT['black'])
    bpy.ops.mesh.primitive_cylinder_add(radius=1.75 * MM, depth=6.0 * MM,
                                        location=(sx * MM, -sy * MM, (Z_PCB + PCB_T + 3.5 + 3.0) * MM))
    bpy.context.object.data.materials.append(MAT['cap'])
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.14, -0.01, 0))
    bpy.context.object.data.materials.append(MAT['floor'])

    o = d['outline']
    c = Vector(((o['x0'] + o['x1']) / 2 * MM - 0.01, -(o['y0'] + o['y1']) / 2 * MM, 0.006))
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    for loc, energy, size in (((0.25, -0.2, 0.35), 12.0, 0.3), ((-0.1, 0.2, 0.25), 4.0, 0.4)):
        light = bpy.data.objects.new('light', bpy.data.lights.new('light', 'AREA'))
        light.data.energy, light.data.size = energy, size
        light.location = Vector(loc)
        light.rotation_euler = (c - light.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.collection.objects.link(light)
    world = bpy.data.worlds.new('world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.9, 0.9, 0.92, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.25
    s = bpy.context.scene
    s.world = world
    s.render.engine = 'CYCLES'
    s.cycles.samples = SAMPLES
    s.cycles.use_denoising = True
    s.render.resolution_x, s.render.resolution_y = RES, RES * 5 // 8
    # the whole kit from the front left; the thumbwheel from beside its corner, low, where it comes out of the case
    wx, wy = d['wheel']['center']
    w = Vector((wx * MM, -wy * MM, (FLOOR + WHEEL_GAP + 3.0) * MM))
    shots = {'enctest': (c, c + Vector((-0.17, -0.14, 0.11)), 70),
             'enctest-wheel': (w + Vector((-0.012, 0.004, 0.0)), w + Vector((0.11, 0.10, 0.045)), 70)}
    for name in SHOTS:
        target, eye, lens = shots[name]
        cam.location = eye
        cam.rotation_euler = (target - eye).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = lens
        s.render.filepath = os.path.join(ROOT, 'docs', 'img', name + '.png')
        bpy.ops.render.render(write_still=True)
        print('wrote', s.render.filepath)


main()
