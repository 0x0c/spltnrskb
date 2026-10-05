"""3D viewer of the assembled halves: case/preview/viewer.html + case/preview/model-data.js.

model-data.js holds every mesh (case parts, KiCad boards, screws and other hardware) and is shared with
the interactive assembly guide (gen/assembly_guide.py -> case/preview/assembly.html).

The boards are shown as KiCad exports them (gen/export_3d.py -> build/3d/*.glb, every part with its
3D model). Without those exports the viewer falls back to a plain board, OLED and switch blocks.
"""
import base64
import math
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifold3d import Manifold  # noqa: E402
import glb_mesh  # noqa: E402
import make_case as mc  # noqa: E402
from make_case import (Half, OUT, FLOOR, STANDOFF, PCB_T, PLATE_GAP, BOTTOM_T, FRAME_T,  # noqa: E402
                       N_FRAMES, PLATE_T, COVER_T, WHEEL_GAP, TRAY_FILLET, TRAY_TOP_FILLET,
                       WHEEL_T, MAGNET_D, MAGNET_DEPTH)


def screw(x, y, z_head, length, head_d=3.8, head_h=1.3, d=2.0, up=False):
    """Pan-head screw, head bottom at z_head; shank goes down (or up when the head is underneath)."""
    head = Manifold.cylinder(head_h, head_d / 2, head_d / 2 * 0.85, 24)
    shank = Manifold.cylinder(length, d / 2, d / 2, 12)
    if up:
        m = head.mirror((0, 0, 1)) + shank
    else:
        m = head + shank.translate((0, 0, -length))
    return m.translate((x, -y, z_head))


def hexagon(x, y, z0, h, af):
    return Manifold.cylinder(h, af / math.sqrt(3), af / math.sqrt(3), 6).translate((x, -y, z0))


def hardware(hf, variant):
    """Screws, inserts, standoffs, plunger and feet as [(name, mesh, colour)]."""
    out = []
    steel, brass, rubber = '#a9adb3', '#c8a24a', '#2a2d31'
    add = lambda name, ms, c: out.append((name, sum(ms[1:], ms[0]) if ms else None, c))
    z_pcb = (FLOOR if variant in PRINTED else BOTTOM_T) + STANDOFF
    z_plate_top = z_pcb + PCB_T + PLATE_GAP + PLATE_T
    holes, screws = hf.d['holes'], hf.screws
    if variant in PRINTED:
        wall_top = z_pcb + PCB_T + PLATE_GAP
        add('insert', [Manifold.cylinder(3.0, 1.6, 1.6, 16).translate((x, -y, wall_top - 3.0)) for x, y in screws], brass)
        add('plate_screw', [screw(x, y, z_plate_top, 5, head_d=4.0, head_h=0.5) for x, y in screws], steel)   # low-head pan
        add('pcb_screw', [screw(x, y, z_pcb + PCB_T, 6) for x, y in holes], steel)
        z_floor = FLOOR
    else:
        add('standoff', [hexagon(x, y, BOTTOM_T, STANDOFF, 3.5) for x, y in holes], brass)
        add('pcb_screw', [screw(x, y, z_pcb + PCB_T, 4) for x, y in holes], steel)
        add('bottom_screw', [screw(x, y, 0, 5, up=True) for x, y in holes], steel)
        add('case_screw', [screw(x, y, z_plate_top, 20) for x, y in screws], steel)
        add('nut', [hexagon(x, y, -1.6, 1.6, 4.0) for x, y in screws], steel)
        (wx, wy), _ = hf.wheel_xy()
        add('axle', [screw(wx, wy, 0, 8, head_d=5.5, head_h=1.8, d=3.0, up=True)], steel)
        add('block_screw', [screw(x, y, 0, 6, up=True) for x, y in hf.detent_screws_xy()], steel)
        z_floor = BOTTOM_T
    # ball plunger in the block, ball on the wheel's teeth
    block, zc = hf.detent_block(z_floor)
    (qx, qy), (ux, uy), _ = hf._detent_frame()
    ang = math.degrees(math.atan2(uy, ux))
    # NBK PAFS-3 (M3, L 6, ball 1.5, stroke 0.5): front face just clear of the crests, ball in a valley
    body = Manifold.cylinder(6.0, 1.5, 1.5, 20).rotate((0, 90, 0)).translate((0.05, 0, zc))
    ball = Manifold.sphere(0.75, 16).translate((0.3, 0, zc))
    add('plunger', [(body + ball).rotate((0, 0, ang)).translate((qx, qy, 0))], steel)
    x0, y0, x1, y1, _ = hf.outer_box
    feet = [(x0 + 14, y0 + 14), (x1 - 14, y0 + 14), (x0 + 14, y1 - 14), (x1 - 14, y1 - 14)]
    z_bottom = 0.0 if variant in PRINTED else -1.6
    add('feet', [Manifold.cylinder(3.8, 4.75, 4.75, 24).translate((x, -y, z_bottom - 3.8)) for x, y in feet], rubber)
    return out


def pack(man):
    mesh = man.to_mesh()
    v = np.asarray(mesh.vert_properties[:, :3], dtype=np.float32)
    t = np.asarray(mesh.tri_verts, dtype=np.uint32)
    return dict(v=base64.b64encode(v.tobytes()).decode(), i=base64.b64encode(t.tobytes()).decode())


def switches(hf, z):
    out = Manifold()
    for k in hf.d['keys']:
        out = out + Manifold.cube((14, 14, 11.6)).translate((k['cx'] - 7, -k['cy'] - 7, z - 5.0))
    return out


# print: printed tray + clear acrylic plate; printtop: everything printed (plate with a web); acrylic: laser-cut stack
VARIANTS = ('print', 'printtop', 'acrylic')
PRINTED = ('print', 'printtop')

GLB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', '3d')


def load_pcba():
    paths = {(s, k): os.path.join(GLB, f'{s}-{k}.glb') for s in ('left', 'right') for k in ('pcba', 'switches')}
    if not all(os.path.exists(p) for p in paths.values()):
        print('no KiCad 3D export in build/3d; using plain board blocks')
        return None, None
    pool = {}
    boards = {s: {k: glb_mesh.load(paths[s, k], pool) for k in ('pcba', 'switches')} for s in ('left', 'right')}
    return pool['items'], boards


def main():
    pool, boards = load_pcba()
    scenes = {}
    for variant in VARIANTS:
        parts = []
        for side in ('left', 'right'):
            hf = Half(side)
            if variant in PRINTED:
                z_pcb = FLOOR + STANDOFF
                parts.append((side, 'tray', pack(hf.tray()), '#d9d4c7', 1.0))
                parts.append((side, 'wheelcap', pack(hf.wheel_cap()), '#d9d4c7', 1.0))
                parts.append((side, 'portcap', pack(hf.port_caps()), '#d9d4c7', 1.0))
            else:
                z_pcb = BOTTOM_T + STANDOFF
                parts.append((side, 'bottom', pack(Manifold.extrude(hf.bottom(), BOTTOM_T)), 'matte', 0.6))
                parts.append((side, 'detent', pack(hf.detent_part()), '#d9d4c7', 1.0))   # printed plunger block
                for i in range(N_FRAMES):
                    f = Manifold.extrude(hf.frame(i), FRAME_T).translate((0, 0, BOTTOM_T + i * FRAME_T))
                    parts.append((side, f'frame{i + 1}', pack(f), 'matte', 0.6))
            z_plate = z_pcb + PCB_T + PLATE_GAP
            if variant == 'printtop':
                parts.append((side, 'plate', pack(hf.plate3d_printed().translate((0, 0, z_plate))), '#d9d4c7', 1.0))
            else:
                parts.append((side, 'plate', pack(hf.plate3d().translate((0, 0, z_plate))), 'clear', 0.45))
            if boards:     # KiCad's assembled board is placed at z_pcb by the page
                parts.append((side, 'pcba', z_pcb, None, None))
            else:
                parts.append((side, 'pcb', pack(hf.pcb3d().translate((0, 0, z_pcb))), '#1f6b3a', 1.0))
                parts.append((side, 'switch', pack(switches(hf, z_plate + PLATE_T)), '#333333', 1.0))
                bx0, by0, bx1, by1 = hf.d['oled']['box']
                oled = Manifold.cube((bx1 - bx0 - 0.5, by1 - by0 - 0.5, 2.6)).translate(
                    (bx0 + 0.25, -by1 + 0.25, z_pcb + PCB_T + PLATE_GAP + PLATE_T - COVER_T - 0.5 - 2.6))
                parts.append((side, 'oled', pack(oled), '#11151a', 1.0))
            z_floor = FLOOR if variant in PRINTED else BOTTOM_T
            parts.append((side, 'wheel', pack(hf.wheel3d().translate((0, 0, z_floor + WHEEL_GAP))), '#c9ccd1', 1.0))
            # diametric magnet in the wheel's top pocket, read by the AS5600 (U3) on the PCB back right above it
            (mx, my), _ = hf.wheel_xy()
            magnet = Manifold.cylinder(MAGNET_DEPTH, (MAGNET_D - 0.1) / 2, (MAGNET_D - 0.1) / 2, 48).translate(
                (mx, -my, z_floor + WHEEL_GAP + WHEEL_T - MAGNET_DEPTH + 0.01))
            parts.append((side, 'magnet', pack(magnet), '#7a2630', 1.0))
            for name, m, color in hardware(hf, variant):
                if m is not None:
                    parts.append((side, name, pack(m), color, 1.0))
            z_cover = z_plate + PLATE_T - COVER_T if variant in PRINTED else z_plate   # acrylic: on frame4, 0.5 mm proud
            cover = Manifold.extrude(hf.cover(), COVER_T).translate((0, 0, z_cover))
            parts.append((side, 'cover', pack(cover), 'mirror', 0.85))
        scenes[variant] = parts
    rep = json.load(open(os.path.join(OUT, 'case_report.json')))
    size = ' / '.join(f"{'左' if k == 'left' else '右'} {v['case_mm'][0]:g} × {v['case_mm'][1]:g}" for k, v in rep.items())
    spec_data = {
        'print': dict(title='A：3D プリントのトレイ + 透明アクリルのプレート', rows=[
            ['外形 mm', size], ['高さ', f"{FLOOR + STANDOFF + PCB_T + PLATE_GAP + PLATE_T:g} mm（プレート上面まで）"],
            ['床 / 壁', f'{FLOOR:g} mm / 幅 8 mm'], ['基板の高さ', f'床から {STANDOFF:g} mm（ボス φ4.6）'],
            ['プレート', '透明アクリル 1.5 mm、M2 ヒートセットインサートで固定'], ['トレイの角', f'外周の下端 R{TRAY_FILLET:g}・上端 R{TRAY_TOP_FILLET:g} のフィレット'], ['コネクタ', '基板裏面。プレートは切り欠きなし'], ['ホイール', '角にサムホイール × 2（AS5600）'],
            ['OLED', 'ハーフミラーアクリル 2 mm の角丸長方形、両面テープで固定（プレートと面一）']]),
        'printtop': dict(title='B：全部 3D プリント（プレートも印刷）', rows=[
            ['外形 mm', size], ['高さ', f"{FLOOR + STANDOFF + PCB_T + PLATE_GAP + PLATE_T:g} mm（プレート上面まで）"],
            ['プレート', f'3D プリント 1.5 mm + 裏の補強 {mc.RIB_T:g} mm（スイッチの周りだけ 1.5 mm）'],
            ['トレイの角', f'外周の下端 R{TRAY_FILLET:g}・上端 R{TRAY_TOP_FILLET:g} のフィレット'],
            ['ホイール', '角にサムホイール × 2（AS5600）、壁の上は外せる角キャップ'],
            ['OLED', 'ハーフミラーアクリル 2 mm の角丸長方形、両面テープで固定（プレートと面一）']]),
        'acrylic': dict(title='アクリル版（積層サンドイッチ）', rows=[
            ['外形 mm', size], ['材料', '枠と底板はマットクリア 3 mm、プレートは透明 1.5 mm、OLED カバーはハーフミラー 2 mm'], ['積層', f'底板 {BOTTOM_T:g} + 枠 {FRAME_T:g} × {N_FRAMES} + プレート {PLATE_T:g} mm'],
            ['高さ', f'{BOTTOM_T + N_FRAMES * FRAME_T + PLATE_T:g} mm'], ['基板の固定', f'M2 スペーサー {STANDOFF:g} mm × 8'], ['コネクタ', '基板裏面。プレートと最上段の枠は切り欠きなし'],
            ['外周', 'M2 × 20 mm + ナット'], ['ホイール', '角にサムホイール × 2（AS5600）'], ['OLED', '0.91 インチ × 2、プレートと面一のハーフミラーアクリル 2 mm']]),
    }
    z = {v: {'pcb': (FLOOR if v in PRINTED else BOTTOM_T) + STANDOFF} for v in VARIANTS}
    data = dict(DATA=scenes, POOL=pool, BOARDS=boards, SPEC=spec_data, Z=z)
    js = os.path.join(OUT, 'preview', 'model-data.js')
    open(js, 'w').write('window.NRSK = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
    path = os.path.join(OUT, 'preview', 'viewer.html')
    open(path, 'w').write(TEMPLATE)
    print('wrote', path, 'and', js, f'{os.path.getsize(js) / 1e6:.1f} MB')


TEMPLATE = r'''<title>nrsk Case Viewer</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+JP:wght@400;600&family=IBM+Plex+Mono:wght@400&display=swap">
<style>
/* Layout: full-bleed WebGL canvas, one control panel and one spec card floating on it */
:root{--bg:#eef1f4;--panel:#ffffffe6;--fg:#1b2129;--muted:#5d6773;--line:#c9d1da;--accent:#1f6b3a;--on-accent:#ffffff;
 --sans:"IBM Plex Sans JP",system-ui,-apple-system,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#14181d;--panel:#1d232ae6;--fg:#e6eaee;--muted:#9aa5b1;--line:#34404c;--accent:#5fc285;--on-accent:#0d1a12;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#14181d;--panel:#1d232ae6;--fg:#e6eaee;--muted:#9aa5b1;--line:#34404c;--accent:#5fc285;--on-accent:#0d1a12;color-scheme:dark}
html,body{height:100%}
body{background:var(--bg);color:var(--fg);font:14px/1.5 var(--sans);overflow:hidden}
#view{position:fixed;inset:0;width:100%;height:100%;touch-action:none}
.panel{position:fixed;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;backdrop-filter:blur(6px)}
#ui{left:16px;top:calc(16px + env(safe-area-inset-top,0px));display:flex;flex-wrap:wrap;gap:6px;max-width:calc(100vw - 32px);box-sizing:border-box}
#spec{left:16px;bottom:calc(16px + env(safe-area-inset-bottom,0px));font-size:12px;max-width:min(360px,calc(100vw - 32px));box-sizing:border-box}
#spec h1{font-size:14px;margin:0 0 4px;font-weight:600;text-wrap:balance}
#spec dl{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;margin:0;font-size:12px}
@media (max-height:520px){#spec{display:none}}
#spec dt{color:var(--muted)}#spec dd{margin:0;font-family:var(--mono);font-variant-numeric:tabular-nums}
.sep{width:1px;background:var(--line);margin:0 2px}
button{font:inherit;font-size:13px;border:1px solid var(--line);background:transparent;color:var(--fg);border-radius:6px;padding:4px 10px;cursor:pointer}
button.on{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.gap[hidden]{display:none}
.link{color:var(--accent);font-size:13px;align-self:center;margin-left:4px}
.gap{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--muted)}
.gap input{width:min(160px,40vw);accent-color:var(--accent)}
.gap output{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--fg);min-width:4.5em}
</style>
<canvas id="view" aria-label="キーボード筐体の 3D 表示。ドラッグで回転、右ドラッグか 2 本指でパン、ホイールかピンチでズーム、ダブルクリックで視点リセット"></canvas>
<div id="ui" class="panel">
 <button id="v-print" data-v="print" class="on">A：プリント + アクリル蓋</button><button id="v-printtop" data-v="printtop">B：全部プリント</button><button id="v-acrylic" data-v="acrylic">アクリル版</button>
 <span class="sep"></span>
 <button id="t-switch" data-t="switch" class="on">スイッチ</button><button id="t-plate" data-t="plate" class="on">プレート</button><button id="t-wheel" data-t="wheel" class="on">ホイール</button>
 <button id="t-explode" data-t="explode">分解表示</button>
 <label id="gap" class="gap" hidden>間隔 <input id="gap-in" type="range" min="0" max="40" step="1" value="10" aria-label="分解表示のレイヤー間隔（mm）"> <output id="gap-out">10 mm</output></label>
 <span class="sep"></span>
 <button id="t-reset" type="button">視点リセット</button>
 <a class="link" href="assembly.html">組み立てガイド</a>
</div>
<div id="spec" class="panel"><h1 id="spec-title"></h1><dl id="spec-dl"></dl></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script src="model-data.js"></script>
<script>
// meshes are in model-data.js (shared with assembly.html)
const {DATA, POOL, BOARDS, SPEC} = window.NRSK;   // BOARDS: per side {pcba: {group: [[pool id, matrices]]}, switches}
const HIDDEN = ['insert', 'plate_screw', 'pcb_screw', 'standoff', 'bottom_screw', 'case_screw', 'nut', 'axle',
                'block_screw', 'feet'];   // hardware is shown in the assembly guide only
const b64 = (s, T) => { const b = atob(s), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return new T(u.buffer); };
const canvas = document.getElementById('view');
const renderer = new THREE.WebGLRenderer({canvas, antialias: true}); renderer.setPixelRatio(devicePixelRatio);
const scene = new THREE.Scene();
const cam = new THREE.PerspectiveCamera(35, 1, 1, 5000);
cam.up.set(0, 0, 1);                       // Z is up; must be set before OrbitControls is created
const ctl = new THREE.OrbitControls(cam, canvas);
ctl.enableDamping = true;
ctl.dampingFactor = 0.12;
ctl.rotateSpeed = 0.7;
ctl.screenSpacePanning = true;
ctl.minPolarAngle = 0.05;                  // from straight above ...
ctl.maxPolarAngle = Math.PI - 0.05;        // ... to straight below, so the bottom can be inspected
ctl.mouseButtons = {LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN};
ctl.touches = {ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN};
scene.add(new THREE.HemisphereLight(0xffffff, 0x666666, 0.9));
const dl = new THREE.DirectionalLight(0xffffff, 0.6); dl.position.set(200, -300, 400); scene.add(dl);
let group = null; const state = {v: 'print', switch: true, plate: true, wheel: true, explode: false, gap: 10};
// exploded view: each layer rises by its level x the gap set on the slider (mm)
const LEVEL = {tray: 0, bottom: 0, wheel: 0, magnet: 0, detent: 0, plunger: 0, wheelcap: 2, portcap: 8, frame1: 1, frame2: 2, frame3: 3, frame4: 4, pcb: 6, pcba: 6, oled: 6.5,
               plate: 9, switch: 11.5, cover: 12.5};
const GAP = 25;   // mm between the halves
// matte (frosted) and clear acrylic, and the half-mirror OLED cover
const MATERIAL = {matte: {color: '#e6edf1', roughness: 0.95, metalness: 0.0},
                  clear: {color: '#d8e6ee', roughness: 0.1, metalness: 0.0},
                  mirror: {color: '#3a4048', roughness: 0.08, metalness: 0.9}};
function bg() { scene.background = new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()); }
function spec() {
  const s = SPEC[state.v];
  document.getElementById('spec-title').textContent = s.title;
  document.getElementById('spec-dl').innerHTML = s.rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
}
// pool geometry: int16 positions over the part's box, normals computed here
const geoCache = [], matCache = [];
function poolGeo(id) {
  if (geoCache[id]) return geoCache[id];
  const p = POOL[id], q = b64(p.v, Int16Array), v = new Float32Array(q.length);
  for (let i = 0; i < q.length; i++) v[i] = q[i] * p.s[i % 3] + p.o[i % 3];
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(v, 3));
  g.setIndex(new THREE.BufferAttribute(b64(p.i, p.big ? Uint32Array : Uint16Array), 1));
  g.computeVertexNormals();
  const [r, gr, b, a] = p.mat.c;
  const color = new THREE.Color(r, gr, b).convertLinearToSRGB();
  matCache[id] = new THREE.MeshStandardMaterial({color, metalness: Math.min(p.mat.m, 0.6), roughness: Math.max(p.mat.r, 0.25),
                                                 transparent: a < 1, opacity: a, side: THREE.DoubleSide});
  return geoCache[id] = g;
}
function board(list) {
  const g = new THREE.Group(), m4 = new THREE.Matrix4();
  for (const [id, inst] of list) {
    const mats = b64(inst, Float32Array), n = mats.length / 16;
    const mesh = new THREE.InstancedMesh(poolGeo(id), matCache[id], n);
    for (let i = 0; i < n; i++) mesh.setMatrixAt(i, m4.fromArray(mats, i * 16));
    g.add(mesh);
  }
  return g;
}
function place(obj) { obj.position.z = obj.userData.z0 + (state.explode ? (LEVEL[obj.userData.layer] || 0) * state.gap : 0); }
function build() {
  if (group) scene.remove(group);
  group = new THREE.Group();
  const halves = {left: new THREE.Group(), right: new THREE.Group()};
  const add = (side, layer, obj, z0 = 0) => { obj.userData = {layer, z0}; place(obj); halves[side].add(obj); };
  for (const [side, name, m, color, op] of DATA[state.v]) {
    if (HIDDEN.includes(name)) continue;
    const key = {magnet: 'wheel', detent: 'wheel', plunger: 'wheel'}[name] || name;
    if (!state[key] && (key === 'switch' || key === 'plate' || key === 'wheel')) continue;
    if (name === 'pcba') {
      add(side, 'pcba', board(Object.values(BOARDS[side].pcba).flat()), m);
      if (state.switch) add(side, 'switch', board(Object.values(BOARDS[side].switches).flat()), m);
      continue;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(b64(m.v, Float32Array), 3));
    g.setIndex(new THREE.BufferAttribute(b64(m.i, Uint32Array), 1));
    g.computeVertexNormals();
    const look = MATERIAL[color] || {color, roughness: 0.6, metalness: 0.05};
    const mat = new THREE.MeshStandardMaterial(Object.assign({transparent: op < 1, opacity: op, flatShading: true}, look));
    add(side, name, new THREE.Mesh(g, mat));
  }
  group.add(halves.left, halves.right);
  group.userData.halves = halves;
  scene.add(group); layout(); spec();
}
// side by side on wide screens, stacked on tall (phone) screens
function layout() {
  const {left, right} = group.userData.halves;
  right.position.set(0, 0, 0);
  const lb = new THREE.Box3().setFromObject(left), rb = new THREE.Box3().setFromObject(right);
  if (cam.aspect >= 1) right.position.set(lb.max.x + GAP - rb.min.x, lb.max.y - rb.max.y, 0);
  else right.position.set(lb.min.x - rb.min.x, lb.min.y - GAP - rb.max.y, 0);
}
function fit() {
  // place the camera on a fixed viewing direction and find the closest distance at which all
  // eight corners of the model's bounding box stay inside the frame (with a margin)
  const box = new THREE.Box3().setFromObject(group);
  const c = box.getCenter(new THREE.Vector3());
  const corners = [];
  for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) corners.push(new THREE.Vector3(x, y, z));
  const dir = new THREE.Vector3(0, -0.75, 0.66).normalize();
  ctl.target.copy(c);
  const fits = d => {
    cam.position.copy(c).addScaledVector(dir, d); cam.lookAt(c); cam.near = d / 50; cam.far = d * 10;
    cam.updateMatrixWorld(); cam.updateProjectionMatrix();
    return corners.every(p => { const q = p.clone().project(cam); return Math.abs(q.x) < 0.9 && Math.abs(q.y) < 0.8 && q.z < 1; });
  };
  let lo = 10, hi = 20000;
  for (let i = 0; i < 40; i++) { const m = (lo + hi) / 2; if (fits(m)) hi = m; else lo = m; }
  fits(hi);
  ctl.minDistance = hi * 0.15; ctl.maxDistance = hi * 3;
  ctl.update();
}
function resize() {
  const w = document.documentElement.clientWidth || innerWidth, h = document.documentElement.clientHeight || innerHeight;
  renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix();
}
let lastWide = null;
function onResize() {
  resize();
  const wide = cam.aspect >= 1;
  if (wide !== lastWide) { lastWide = wide; layout(); fit(); }
}
document.querySelectorAll('button[data-v], button[data-t]').forEach(b => b.addEventListener('click', () => {
  if (b.dataset.v) { state.v = b.dataset.v; document.querySelectorAll('[data-v]').forEach(x => x.classList.toggle('on', x === b)); }
  else { state[b.dataset.t] = !state[b.dataset.t]; b.classList.toggle('on', state[b.dataset.t]); }
  if (b.dataset.t === 'explode') document.getElementById('gap').hidden = !state.explode;
  build(); if (b.dataset.v || b.dataset.t === 'explode') fit();
}));
const gapIn = document.getElementById('gap-in'), gapOut = document.getElementById('gap-out');
gapIn.addEventListener('input', () => {
  state.gap = +gapIn.value; gapOut.textContent = `${state.gap} mm`;
  for (const h of Object.values(group.userData.halves)) h.children.forEach(place);
});
gapIn.addEventListener('change', fit);   // refit once the slider is released
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', bg);
new MutationObserver(bg).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
addEventListener('resize', onResize);
bg(); resize(); build(); lastWide = cam.aspect >= 1; fit();
canvas.addEventListener('dblclick', fit);
document.getElementById('t-reset').addEventListener('click', fit);
(function loop() { requestAnimationFrame(loop); ctl.update(); renderer.render(scene, cam); })();
</script>
'''

if __name__ == '__main__':
    main()
