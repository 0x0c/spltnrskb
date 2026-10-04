"""Self-contained 3D viewer of the assembled halves: case/preview/viewer.html."""
import base64
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifold3d import Manifold  # noqa: E402
from make_case import (Half, OUT, FLOOR, STANDOFF, PCB_T, PLATE_GAP, BOTTOM_T, FRAME_T,  # noqa: E402
                       N_FRAMES, PLATE_T, COVER_T, WHEEL_GAP)


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


def main():
    scenes = {}
    for variant in ('print', 'acrylic'):
        parts = []
        for side in ('left', 'right'):
            hf = Half(side)
            if variant == 'print':
                z_pcb = FLOOR + STANDOFF
                parts.append((side, 'tray', pack(hf.tray()), '#d9d4c7', 1.0))
            else:
                z_pcb = BOTTOM_T + STANDOFF
                parts.append((side, 'bottom', pack(Manifold.extrude(hf.bottom(), BOTTOM_T)), '#cfe8ff', 0.55))
                for i in range(N_FRAMES):
                    f = Manifold.extrude(hf.frame(i), FRAME_T).translate((0, 0, BOTTOM_T + i * FRAME_T))
                    parts.append((side, f'frame{i + 1}', pack(f), '#cfe8ff', 0.55))
            z_plate = z_pcb + PCB_T + PLATE_GAP
            parts.append((side, 'pcb', pack(hf.pcb3d().translate((0, 0, z_pcb))), '#1f6b3a', 1.0))
            parts.append((side, 'plate', pack(hf.plate3d().translate((0, 0, z_plate))), '#9aa4b1', 0.9))
            parts.append((side, 'switch', pack(switches(hf, z_plate + PLATE_T)), '#333333', 1.0))
            bx0, by0, bx1, by1 = hf.d['oled']['box']
            oled = Manifold.cube((bx1 - bx0 - 0.5, by1 - by0 - 0.5, 2.6)).translate((bx0 + 0.25, -by1 + 0.25, z_pcb + PCB_T + 2.0))
            parts.append((side, 'oled', pack(oled), '#11151a', 1.0))
            z_floor = FLOOR if variant == 'print' else BOTTOM_T
            parts.append((side, 'wheel', pack(hf.wheel3d().translate((0, 0, z_floor + WHEEL_GAP))), '#c9ccd1', 1.0))
            cover = Manifold.extrude(hf.cover(), COVER_T).translate((0, 0, z_plate + PLATE_T))
            parts.append((side, 'cover', pack(cover), '#bfe3ff', 0.35))
        scenes[variant] = parts
    rep = json.load(open(os.path.join(OUT, 'case_report.json')))
    size = ' / '.join(f"{'左' if k == 'left' else '右'} {v['case_mm'][0]:g} × {v['case_mm'][1]:g}" for k, v in rep.items())
    spec_data = {
        'print': dict(title='3D プリント版（トレイ + プレート）', rows=[
            ['外形 mm', size], ['高さ', f"{FLOOR + STANDOFF + PCB_T + PLATE_GAP + PLATE_T:g} mm（プレート上面まで）"],
            ['床 / 壁', f'{FLOOR:g} mm / 幅 8 mm'], ['基板の高さ', f'床から {STANDOFF:g} mm（ボス φ4.6）'],
            ['プレート固定', 'M2 ヒートセットインサート'], ['コネクタ', '基板裏面。プレートは切り欠きなし'], ['ホイール', '角にサムホイール × 2（AS5600）'],
            ['OLED', '0.91 インチ × 2、透明アクリル 2 mm のカバー']]),
        'acrylic': dict(title='アクリル版（積層サンドイッチ）', rows=[
            ['外形 mm', size], ['積層', f'底板 {BOTTOM_T:g} + 枠 {FRAME_T:g} × {N_FRAMES} + プレート {PLATE_T:g} mm'],
            ['高さ', f'{BOTTOM_T + N_FRAMES * FRAME_T + PLATE_T:g} mm'], ['基板の固定', f'M2 スペーサー {STANDOFF:g} mm × 8'], ['コネクタ', '基板裏面。プレートと最上段の枠は切り欠きなし'],
            ['外周', 'M2 × 20 mm + ナット'], ['ホイール', '角にサムホイール × 2（AS5600）'], ['OLED', '0.91 インチ × 2、透明アクリル 2 mm のカバー']]),
    }
    html = TEMPLATE.replace('__DATA__', json.dumps(scenes)).replace('__SPEC__', json.dumps(spec_data, ensure_ascii=False))
    path = os.path.join(OUT, 'preview', 'viewer.html')
    open(path, 'w').write(html)
    print('wrote', path, f'{os.path.getsize(path) / 1e6:.1f} MB')


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
</style>
<canvas id="view" aria-label="キーボード筐体の 3D 表示。ドラッグで回転、右ドラッグか 2 本指でパン、ホイールかピンチでズーム、ダブルクリックで視点リセット"></canvas>
<div id="ui" class="panel">
 <button id="v-print" data-v="print" class="on">3D プリント版</button><button id="v-acrylic" data-v="acrylic">アクリル版</button>
 <span class="sep"></span>
 <button id="t-switch" data-t="switch" class="on">スイッチ</button><button id="t-plate" data-t="plate" class="on">プレート</button>
 <button id="t-explode" data-t="explode">分解表示</button>
 <span class="sep"></span>
 <button id="t-reset" type="button">視点リセット</button>
</div>
<div id="spec" class="panel"><h1 id="spec-title"></h1><dl id="spec-dl"></dl></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
const DATA = __DATA__;
const SPEC = __SPEC__;
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
ctl.maxPolarAngle = Math.PI / 2 - 0.08;    // ... down to just above the desk
ctl.mouseButtons = {LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN};
ctl.touches = {ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN};
scene.add(new THREE.HemisphereLight(0xffffff, 0x666666, 0.9));
const dl = new THREE.DirectionalLight(0xffffff, 0.6); dl.position.set(200, -300, 400); scene.add(dl);
let group = null; const state = {v: 'print', switch: true, plate: true, explode: false};
const LIFT = {tray: 0, bottom: 0, frame1: 8, frame2: 16, frame3: 24, frame4: 32, pcb: 48, oled: 52, plate: 72, cover: 100, knob: 110, switch: 92};
const GAP = 25;   // mm between the halves
function bg() { scene.background = new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()); }
function spec() {
  const s = SPEC[state.v];
  document.getElementById('spec-title').textContent = s.title;
  document.getElementById('spec-dl').innerHTML = s.rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
}
function build() {
  if (group) scene.remove(group);
  group = new THREE.Group();
  const halves = {left: new THREE.Group(), right: new THREE.Group()};
  for (const [side, name, m, color, op] of DATA[state.v]) {
    if (!state[name] && (name === 'switch' || name === 'plate')) continue;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(b64(m.v, Float32Array), 3));
    g.setIndex(new THREE.BufferAttribute(b64(m.i, Uint32Array), 1));
    g.computeVertexNormals();
    const mat = new THREE.MeshStandardMaterial({color, transparent: op < 1, opacity: op, roughness: 0.6, metalness: 0.05, flatShading: true});
    const mesh = new THREE.Mesh(g, mat);
    if (state.explode) mesh.position.z = LIFT[name] || 0;
    halves[side].add(mesh);
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
  build(); if (b.dataset.v || b.dataset.t === 'explode') fit();
}));
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
