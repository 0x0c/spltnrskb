"""How the board goes into the printed tray: tilted, PORT_LIFT high, slid tongue-first into the port tunnels, dropped.
Section through the left half's USB-C centre line, three poses side by side -> docs/img/port-slide.png.

Run with the venv python (exports section STLs, calls Blender on this same file, composes the panels):
    .venv/bin/python gen/port_slide.py
"""
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'docs', 'img', 'port-slide.png')
SLIDE = 8.0                  # mm: tongue depth into the wall plus a little
POSES = ('p1', 'p2', 'p3')
LABELS = {'p1': '1  手前を少し持ち上げ、基板を浮かせたまま奥の壁に近づける',
          'p2': f'2  奥へ {SLIDE:g} mm 滑らせ、舌とコネクタをトンネルに入れる',
          'p3': '3  手前を下ろしてボスに載せる（プレートを付けた状態）'}


def export(d):
    sys.path.insert(0, HERE)
    from make_case import (Half, Manifold, FLOOR, STANDOFF, PCB_T, PLATE_GAP, PORT_LIFT, rect, rounded_rect,
                           write_stl)
    hf = Half('left')
    z_pcb = FLOOR + STANDOFF
    z_plate = z_pcb + PCB_T + PLATE_GAP
    x0, y0, x1, y1, r = hf.pcb
    board = rounded_rect(x0, y0, x1, y1, r)
    for t in hf.d['tongues'].values():
        board = board + rect(*t)
    pcb = Manifold.extrude(board, PCB_T).translate((0, 0, z_pcb))
    conns = Manifold()
    for p in hf.slots:
        zb = hf.port_z(p, z_pcb)[0]
        conns = conns + Manifold.extrude(rect(*hf.d['connectors'][p['name']]['box']), z_pcb - zb).translate((0, 0, zb))
    cx = hf.slots[0]['along']
    cut = Manifold.cube((40, 200, 60)).translate((cx, -140, -10))       # keep x >= the USB-C centre line
    write_stl(os.path.join(d, 'tray.stl'), hf.tray() ^ cut)
    write_stl(os.path.join(d, 'plate.stl'), hf.plate3d().translate((0, 0, z_plate)) ^ cut)
    # tilt about the back edge so the front edge clears the front wall top while the back is PORT_LIFT high
    yb = -y0
    tilt = math.degrees(math.atan2(z_plate - (z_pcb + PORT_LIFT) + 0.6, y1 - y0))
    poses = dict(p1=(tilt, -SLIDE, PORT_LIFT), p2=(tilt, 0.0, PORT_LIFT), p3=(0.0, 0.0, 0.0))
    for name, (a, dy, dz) in poses.items():
        for kind, m in (('pcb', pcb), ('conn', conns)):
            m = m.translate((0, -yb, -z_pcb)).rotate((-a, 0, 0)).translate((0, yb + dy, z_pcb + dz))
            write_stl(os.path.join(d, f'{kind}-{name}.stl'), m ^ cut)


def render(d):
    import bpy
    from mathutils import Vector

    def mat(name, col, rough=0.55, trans=0.0):
        m = bpy.data.materials.new(name)
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*col, 1)
        b.inputs['Roughness'].default_value = rough
        if trans:
            b.inputs['Transmission Weight'].default_value = trans
            b.inputs['IOR'].default_value = 1.49
        return m

    def shot(parts, y, scale, res, out):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mats = dict(tray=mat('tray', (0.80, 0.77, 0.70)), plate=mat('acrylic', (0.75, 0.85, 0.95), 0.05, 0.6),
                    pcb=mat('pcb', (0.08, 0.35, 0.18)), conn=mat('conn', (0.70, 0.72, 0.76), 0.25))
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'
        sc.cycles.samples = 64
        sc.render.resolution_x, sc.render.resolution_y = res
        w = bpy.data.worlds.new('w')
        sc.world = w
        w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.95, 0.95, 0.96, 1)
        w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.7
        for fn, kind in parts:
            bpy.ops.wm.stl_import(filepath=os.path.join(d, fn))
            bpy.context.selected_objects[0].data.materials.append(mats[kind])
        tgt = Vector((140, y, 9))
        for loc, e in (((40, -60, 90), 3.5), ((250, 20, 60), 1.0), ((0, 0, 40), 1.5)):
            bpy.ops.object.light_add(type='SUN', location=loc)
            sun = bpy.context.object
            sun.data.energy = e
            sun.rotation_euler = (tgt - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        bpy.ops.object.camera_add(location=(0, y, 9))
        cam = bpy.context.object
        cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = scale
        sc.camera = cam
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)

    for p in POSES:
        parts = [('tray.stl', 'tray'), (f'pcb-{p}.stl', 'pcb'), (f'conn-{p}.stl', 'conn')]
        if p == 'p3':
            parts.append(('plate.stl', 'plate'))
        shot(parts, -55, 140, (1800, 360), os.path.join(d, f'wide-{p}.png'))      # whole depth of the case
        shot(parts, 2, 34, (1200, 800), os.path.join(d, f'close-{p}.png'))        # the back wall and the ports


def compose(d):
    from PIL import Image, ImageDraw, ImageFont
    font = None
    for f in ('/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc', '/System/Library/Fonts/Hiragino Sans GB.ttc'):
        if os.path.exists(f):
            font = ImageFont.truetype(f, 26)
            break
    font = font or ImageFont.load_default()
    rows = []
    for p in POSES:
        wide = Image.open(os.path.join(d, f'wide-{p}.png')).convert('RGB')
        close = Image.open(os.path.join(d, f'close-{p}.png')).convert('RGB')
        close = close.resize((close.width * 360 // close.height, 360))
        row = Image.new('RGB', (wide.width + 10 + close.width, 400), 'white')
        row.paste(wide, (0, 40))
        row.paste(close, (wide.width + 10, 40))
        ImageDraw.Draw(row).text((12, 6), LABELS[p], fill=(30, 30, 30), font=font)
        rows.append(row)
    out = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)), 'white')
    for i, row in enumerate(rows):
        out.paste(row, (0, i * row.height))
    out.save(OUT)
    print('wrote', OUT)


if __name__ == '__main__':
    if '--' in sys.argv:                 # inside Blender
        render(sys.argv[sys.argv.index('--') + 1])
    else:
        with tempfile.TemporaryDirectory() as d:
            export(d)
            subprocess.run(['blender', '-b', '-P', os.path.abspath(__file__), '--', d], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            compose(d)
