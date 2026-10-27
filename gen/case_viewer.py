"""3D viewer of the assembled halves: case/preview/viewer.html + case/preview/model-data.js.

model-data.js holds every mesh (case parts, KiCad boards, screws and other hardware) and is shared with
the interactive assembly guide (gen/assembly_guide.py -> case/preview/assembly.html).

The boards are shown as KiCad exports them (gen/export_3d.py -> build/3d/*.glb, every part with its
3D model). Without those exports the viewer falls back to a plain board, OLED and switch blocks.
"""
import base64
import hashlib
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
                       )


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
    """Screws, inserts, standoffs and feet as [(name, mesh, colour)]."""
    out = []
    steel, brass, rubber = '#a9adb3', '#c8a24a', '#2a2d31'
    add = lambda name, ms, c: out.append((name, sum(ms[1:], ms[0]) if ms else None, c))
    z_pcb = (FLOOR if variant in PRINTED else BOTTOM_T) + STANDOFF
    z_plate_top = z_pcb + PCB_T + PLATE_GAP + PLATE_T
    holes, screws = hf.d['holes'], hf.screws
    if variant in PRINTED:
        wall_top = z_pcb + PCB_T + PLATE_GAP
        if variant == 'printtop':   # B: inserts in the bosses under the printed plate, M2 x 12 from the tray bottom
            add('insert', [Manifold.cylinder(3.0, 1.6, 1.6, 16).translate((x, -y, wall_top - 3.0)) for x, y in screws], brass)
            add('plate_screw', [screw(x, y, mc.SCREW_CB[1], 12, up=True) for x, y in screws], steel)
        else:                       # A: nut in the hex trap, M2 x 6 slim head from the top
            z_nut = wall_top - mc.BOSS_POCKET[1] - mc.NUT_TRAP[1]
            add('insert', [hexagon(x, y, z_nut, 1.6, 4.0) for x, y in screws], steel)
            add('plate_screw', [screw(x, y, z_plate_top, 6, head_d=4.0, head_h=0.5) for x, y in screws], steel)
        add('pcb_screw', [screw(x, y, z_pcb + PCB_T, 6) for x, y in holes], steel)
    else:
        add('standoff', [hexagon(x, y, BOTTOM_T, STANDOFF, 3.5) for x, y in holes], brass)
        add('pcb_screw', [screw(x, y, z_pcb + PCB_T, 4) for x, y in holes], steel)
        add('bottom_screw', [screw(x, y, 0, 5, up=True) for x, y in holes], steel)
        add('case_screw', [screw(x, y, z_plate_top, 20) for x, y in screws], steel)   # from the top through everything
        add('nut', [hexagon(x, y, -1.6, 1.6, 4.0) for x, y in screws], steel)
        (wx, wy), _ = hf.wheel_xy()
        add('axle', [screw(wx, wy, 0, 8, head_d=5.5, head_h=1.8, d=3.0, up=True)], steel)
    if variant in PRINTED:          # in the recesses under the tray (make_case.Half.feet)
        feet, z_top = hf.feet(), mc.FOOT_DEPTH
    else:                           # stuck flat under the bottom plate, below the nuts
        x0, y0, x1, y1, _ = hf.outer_box
        feet, z_top = [(x0 + 14, y0 + 14), (x1 - 14, y0 + 14), (x0 + 14, y1 - 14), (x1 - 14, y1 - 14)], -1.6
    add('feet', [Manifold.cylinder(mc.FOOT_H, 4.75, 4.75, 24).translate((x, -y, z_top - mc.FOOT_H)) for x, y in feet],
        rubber)
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
            else:
                z_pcb = BOTTOM_T + STANDOFF
                parts.append((side, 'bottom', pack(Manifold.extrude(hf.bottom(), BOTTOM_T)), 'matte', 0.6))
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
            if not boards:   # KiCad's board export carries the encoder (ENC1) with Alps' model
                parts.append((side, 'encoder', pack(hf.encoder3d(z_floor)), '#202225', 1.0))
            if 'drum' in hf.d:   # drum dial: bearing block, drum and bezel (KiCad's board carries the EC10E, ENC2)
                zt = z_pcb + PCB_T
                if not boards:
                    parts.append((side, 'drumenc', pack(hf.ec10e3d().translate((0, 0, zt))), '#202225', 1.0))
                parts.append((side, 'drumblock', pack(hf.drum_block3d().translate((0, 0, zt))), '#d9d4c7', 1.0))
                parts.append((side, 'drum', pack(hf.drum3d().translate((0, 0, zt))), '#c9ccd1', 1.0))
                parts.append((side, 'drumbezel', pack(hf.drum_bezel3d().translate((0, 0, zt))), '#d9d4c7', 1.0))
            for name, m, color in hardware(hf, variant):
                if m is not None:
                    parts.append((side, name, pack(m), color, 1.0))
            z_cover = z_plate + PLATE_T - COVER_T if variant in PRINTED else z_plate   # acrylic: on frame4, 0.5 mm proud
            cover = Manifold.extrude(hf.cover(), COVER_T).translate((0, 0, z_cover))
            parts.append((side, 'cover', pack(cover), 'mirror', 0.85))
            if variant in PRINTED:   # tilt stands, under the untilted tray (the page tilts the half onto them)
                for deg in mc.STAND_ANGLES:
                    parts.append((side, f'stand{deg}', pack(hf.stand(deg)[0]), '#d9d4c7', 1.0))
        scenes[variant] = parts
    rep = json.load(open(os.path.join(OUT, 'case_report.json')))
    STAND_ROW = ['ゴム足と台座', '底のくぼみにゴム足 × 5。U 字の台座（'
                 + '、'.join(f'{d}°' for d in mc.STAND_ANGLES) + '）に載せて奥を上げられる']
    size = ' / '.join(f"{'左' if k == 'left' else '右'} {v['case_mm'][0]:g} × {v['case_mm'][1]:g}" for k, v in rep.items())
    spec_data = {
        'print': dict(title='A：3D プリントのトレイ + 透明アクリルのプレート', rows=[
            ['外形 mm', size], ['高さ', f"{FLOOR + STANDOFF + PCB_T + PLATE_GAP + PLATE_T:g} mm（プレート上面まで）"],
            ['床 / 壁', f'{FLOOR:g} mm / 幅 8 mm'], ['基板の高さ', f'床から {STANDOFF:g} mm（ボス φ4.6）'],
            ['プレート', '透明アクリル 1.5 mm、上からスリムヘッドの M2 小ねじと壁の中の M2 ナットで固定'], ['トレイの角', f'外周の下端 R{TRAY_FILLET:g}・上端 R{TRAY_TOP_FILLET:g} のフィレット'], ['コネクタ', '基板裏面。プレートは切り欠きなし'], ['ホイール', '角にサムホイール × 2（ロータリーエンコーダー Alps EC05E1220401）'],
            ['OLED', f'ハーフミラーアクリル 2 mm、四隅 R{mc.CLEAR + mc.WALL + 4.0 - mc.COVER_FRAME:g}、周りの帯 {mc.COVER_FRAME:g} mm、両面テープで固定（プレートと面一）'],
            ['ドラム', '右上にドラム式ダイヤル（Alps EC10E1220505、24 クリック）、ベゼルはプレートの切り欠きにはめる'],
            STAND_ROW]),
        'printtop': dict(title='B：全部 3D プリント（プレートも印刷）', rows=[
            ['外形 mm', size], ['高さ', f"{FLOOR + STANDOFF + PCB_T + PLATE_GAP + PLATE_T:g} mm（プレート上面まで）"],
            ['プレート', f'3D プリント 1.5 mm + 裏の補強 {mc.RIB_T:g} mm（スイッチの周りだけ 1.5 mm）'],
            ['トレイの角', f'外周の下端 R{TRAY_FILLET:g}・上端 R{TRAY_TOP_FILLET:g} のフィレット'],
            ['ホイール', '角にサムホイール × 2（ロータリーエンコーダー Alps EC05E1220401）、壁の上は外せる角キャップ'],
            ['OLED', f'ハーフミラーアクリル 2 mm、四隅 R{mc.CLEAR + mc.WALL + 4.0 - mc.COVER_FRAME:g}、周りの帯 {mc.COVER_FRAME:g} mm、両面テープで固定（プレートと面一）'],
            ['ドラム', '右上にドラム式ダイヤル（Alps EC10E1220505、24 クリック）、ベゼルはプレートの切り欠きにはめる'],
            STAND_ROW]),
        'acrylic': dict(title='アクリル版（積層サンドイッチ）', rows=[
            ['外形 mm', size], ['材料', '枠と底板はマットクリア 3 mm、プレートは透明 1.5 mm、OLED カバーはハーフミラー 2 mm'], ['積層', f'底板 {BOTTOM_T:g} + 枠 {FRAME_T:g} × {N_FRAMES} + プレート {PLATE_T:g} mm'],
            ['高さ', f'{BOTTOM_T + N_FRAMES * FRAME_T + PLATE_T:g} mm'], ['基板の固定', f'M2 スペーサー {STANDOFF:g} mm × 8'], ['コネクタ', '基板裏面。プレートと最上段の枠は切り欠きなし'],
            ['外周', 'M2 × 20 mm + ナット'], ['ホイール', '角にサムホイール × 2（ロータリーエンコーダー Alps EC05E1220401）'], ['OLED', f'0.91 インチ × 2、ハーフミラーアクリル 2 mm（四隅 R{mc.CLEAR + mc.WALL + 4.0 - mc.COVER_FRAME:g}、プレートより 0.5 mm 高い）'],
            ['ドラム', '右上にドラム式ダイヤル（Alps EC10E1220505、24 クリック）、ベゼルはプレートの切り欠きにはめる']]),
    }
    z = {v: {'pcb': (FLOOR if v in PRINTED else BOTTOM_T) + STANDOFF} for v in VARIANTS}
    # a half on a stand: tray frame -> desk (3 x 4, row major), per side and angle
    tilt = {side: {deg: [round(v, 6) for row in mc.stand_pose(deg, Half(side).front_y()) for v in row]
                   for deg in mc.STAND_ANGLES} for side in ('left', 'right')}
    data = dict(DATA=scenes, POOL=pool, BOARDS=boards, SPEC=spec_data, Z=z, TILT=tilt)
    js = os.path.join(OUT, 'preview', 'model-data.js')
    text = 'window.NRSK = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n'
    open(js, 'w').write(text)
    path = os.path.join(OUT, 'preview', 'viewer.html')
    open(path, 'w').write(TEMPLATE.replace('__DATA_VER__', data_version(text)))
    print('wrote', path, 'and', js, f'{os.path.getsize(js) / 1e6:.1f} MB')


def data_version(text):
    """Short hash of model-data.js for its URL, so a browser never pairs a new page with cached old data."""
    return hashlib.sha256(text.encode()).hexdigest()[:10]


TEMPLATE = r'''<meta charset="utf-8">
<title>nrsk Case Viewer</title>
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
#spec-head{display:flex;align-items:flex-start;gap:8px;cursor:pointer}
#spec h1{font-size:14px;margin:0 0 4px;font-weight:600;text-wrap:balance;flex:1}
#spec-min{font-size:12px;line-height:1;padding:3px 7px;margin:-2px -4px 0 0;color:var(--muted)}
#spec.min{padding:6px 10px}#spec.min h1{margin:0;font-size:13px}#spec.min dl{display:none}
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
.checks{display:flex;flex-wrap:wrap;align-items:center;gap:2px 10px;border:0;margin:0;padding:0 2px;font-size:13px}
.checks label{display:flex;align-items:center;gap:4px;cursor:pointer;white-space:nowrap}
.checks input{accent-color:var(--accent);margin:0}
.checks label.off{color:var(--muted);cursor:default}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.seg{display:flex;align-items:center;gap:0}
.seg .lbl{font-size:13px;color:var(--muted);margin-right:6px}
.seg button{border-radius:0;margin-left:-1px}.seg button:first-of-type{border-radius:6px 0 0 6px;margin-left:0}.seg button:last-of-type{border-radius:0 6px 6px 0}
.seg[hidden]{display:none}
</style>
<canvas id="view" aria-label="キーボード筐体の 3D 表示。ドラッグで回転、右ドラッグか 2 本指でパン、ホイールかピンチでズーム、ダブルクリックで視点リセット"></canvas>
<div id="ui" class="panel">
 <button id="v-print" data-v="print" class="on">A：プリント + アクリル蓋</button><button id="v-printtop" data-v="printtop">B：全部プリント</button><button id="v-acrylic" data-v="acrylic">アクリル版</button><button id="v-board" data-v="board">基板のみ</button>
 <span class="sep"></span>
 <fieldset id="parts" class="checks"><legend class="sr">表示する部品</legend>
  <label><input type="checkbox" data-c="case" checked>ケース</label><label><input type="checkbox" data-c="plate" checked>プレート</label><label><input type="checkbox" data-c="board" checked>基板</label><label><input type="checkbox" data-c="switch" checked>スイッチ</label><label><input type="checkbox" data-c="wheel" checked>ダイヤル</label><label><input type="checkbox" data-c="feet" checked>ゴム足</label><label id="stand-lbl"><input type="checkbox" data-c="stand" checked>台座</label>
 </fieldset>
 <span class="sep"></span>
 <span id="angles" class="seg" role="group" aria-label="台座の角度"><span class="lbl">台座</span><button data-a="0" class="on">なし</button><button data-a="3">3°</button><button data-a="6">6°</button><button data-a="9">9°</button></span>
 <button id="t-explode" data-t="explode">分解表示</button>
 <label id="gap" class="gap" hidden>間隔 <input id="gap-in" type="range" min="0" max="40" step="1" value="10" aria-label="分解表示のレイヤー間隔（mm）"> <output id="gap-out">10 mm</output></label>
 <span class="sep"></span>
 <button id="t-reset" type="button">視点リセット</button>
 <a class="link" href="assembly.html">組み立てガイド</a>
 <a class="link" href="../../docs/views.html">レンダリング</a>
</div>
<div id="spec" class="panel"><div id="spec-head"><h1 id="spec-title"></h1><button id="spec-min" type="button" aria-expanded="true" aria-controls="spec-dl" aria-label="仕様を折りたたむ" title="仕様を折りたたむ">−</button></div><dl id="spec-dl"></dl></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script src="model-data.js?v=__DATA_VER__"></script>
<script>
// meshes are in model-data.js (shared with assembly.html)
const {DATA, POOL, BOARDS, SPEC, TILT} = window.NRSK;   // BOARDS: per side {pcba: {group: [[pool id, matrices]]}, switches}
const HIDDEN = ['insert', 'plate_screw', 'pcb_screw', 'standoff', 'bottom_screw', 'case_screw', 'nut',
                'axle'];   // screws and the like are shown in the assembly guide only
// each part goes with one checkbox
const CAT = n => n.startsWith('stand') ? 'stand' : n === 'feet' ? 'feet' : (n === 'plate' || n === 'cover') ? 'plate'
  : ['pcb', 'pcba', 'oled', 'encoder', 'drumenc'].includes(n) ? 'board' : n === 'switch' ? 'switch'
  : (n === 'wheel' || n.startsWith('drum')) ? 'wheel' : 'case';
// board-only view: the boards and what is soldered to them, taken from the A scene (same board height in B)
const BOARD_ONLY = ['board', 'switch'];
SPEC.board = {title: '基板のみ', rows: [['基板', 'FR-4 1.6 mm（左右 2 枚）'],
  ['実装', 'スイッチ・OLED・ロータリーエンコーダー（サムホイール用 EC05E、ドラム用 EC10E）']]};
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
let group = null;
const state = {v: 'print', angle: 0, explode: false, gap: 10,
               show: {case: true, plate: true, board: true, switch: true, wheel: true, feet: true, stand: true}};
// exploded view: each layer rises by its level x the gap set on the slider (mm)
const LEVEL = {stand3: -2, stand6: -2, stand9: -2, feet: -1, tray: 0, bottom: 0, wheel: 0, wheelcap: 2, encoder: 6, frame1: 1, frame2: 2, frame3: 3, frame4: 4, pcb: 6, pcba: 6, oled: 6.5,
               drumenc: 6, drumblock: 6.5, drum: 7, drumbezel: 8, plate: 9, switch: 11.5, cover: 12.5};
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
  const halves = {left: new THREE.Group(), right: new THREE.Group()}, tilted = {};
  // on a stand the half is turned about its front feet onto the stand (tray frame -> desk); the stand comes along
  for (const side of ['left', 'right']) {
    const t = tilted[side] = new THREE.Group(), p = state.angle && TILT[side][state.angle];
    t.matrixAutoUpdate = false;
    if (p) t.matrix.set(...p, 0, 0, 0, 1);
    halves[side].add(t);
  }
  const add = (side, layer, obj, z0 = 0) => { obj.userData = {layer, z0}; place(obj); tilted[side].add(obj); };
  const boardOnly = state.v === 'board';
  for (const [side, name, m, color, op] of DATA[boardOnly ? 'print' : state.v]) {
    if (HIDDEN.includes(name)) continue;
    if (name === 'pcba') {         // KiCad's board, with the switches as their own checkbox
      if (state.show.board) add(side, 'pcba', board(Object.values(BOARDS[side].pcba).flat()), m);
      if (state.show.switch) add(side, 'switch', board(Object.values(BOARDS[side].switches).flat()), m);
      continue;
    }
    const c = CAT(name);
    if (!state.show[c] || (boardOnly && !BOARD_ONLY.includes(c)) || (c === 'stand' && name !== `stand${state.angle}`)) continue;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(b64(m.v, Float32Array), 3));
    g.setIndex(new THREE.BufferAttribute(b64(m.i, Uint32Array), 1));
    g.computeVertexNormals();
    const look = MATERIAL[color] || {color, roughness: 0.6, metalness: 0.05};
    const mat = new THREE.MeshStandardMaterial(Object.assign({transparent: op < 1, opacity: op, flatShading: true}, look));
    add(side, name, new THREE.Mesh(g, mat));
  }
  group.add(halves.left, halves.right);
  group.userData.halves = halves; group.userData.tilted = tilted;
  scene.add(group); layout(); spec();
}
// world box including each instance of the KiCad boards (Box3.setFromObject in r128 skips instance matrices)
function bounds(obj) {
  obj.updateWorldMatrix(true, true);
  const box = new THREE.Box3(), b = new THREE.Box3(), m = new THREE.Matrix4();
  obj.traverse(o => {
    if (!o.geometry) return;
    if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
    const n = o.isInstancedMesh ? o.count : 1;
    for (let i = 0; i < n; i++) {
      if (o.isInstancedMesh) o.getMatrixAt(i, m); else m.identity();
      box.union(b.copy(o.geometry.boundingBox).applyMatrix4(m.premultiply(o.matrixWorld)));
    }
  });
  return box;
}
// side by side on wide screens, stacked on tall (phone) screens
function layout() {
  const {left, right} = group.userData.halves;
  right.position.set(0, 0, 0);
  const lb = bounds(left), rb = bounds(right);
  if (cam.aspect >= 1) right.position.set(lb.max.x + GAP - rb.min.x, lb.max.y - rb.max.y, 0);
  else right.position.set(lb.min.x - rb.min.x, lb.min.y - GAP - rb.max.y, 0);
}
function fit() {
  // place the camera on a fixed viewing direction and find the closest distance at which all
  // eight corners of the model's bounding box stay inside the frame (with a margin)
  const box = bounds(group);
  if (box.isEmpty()) return;               // every checkbox off
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
// stands exist for the printed trays only; the stand checkbox only matters with an angle chosen
function standUI() {
  const printed = state.v === 'print' || state.v === 'printtop';
  if (!printed) state.angle = 0;
  document.getElementById('angles').hidden = !printed;
  document.querySelectorAll('[data-a]').forEach(x => x.classList.toggle('on', +x.dataset.a === state.angle));
  const lbl = document.getElementById('stand-lbl'), box = lbl.querySelector('input');
  lbl.hidden = !printed; box.disabled = !state.angle; lbl.classList.toggle('off', !state.angle);
  lbl.title = state.angle ? '' : '台座の角度を選ぶと表示できます';
  // the board-only view leaves the case, plate, dials and feet out whatever their checkboxes say
  document.querySelectorAll('[data-c]').forEach(x => {
    if (!BOARD_ONLY.includes(x.dataset.c) && x.dataset.c !== 'stand') x.disabled = state.v === 'board'; x.parentElement.classList.toggle('off', x.disabled);
  });
}
document.querySelectorAll('button[data-v], button[data-t]').forEach(b => b.addEventListener('click', () => {
  if (b.dataset.v) { state.v = b.dataset.v; document.querySelectorAll('[data-v]').forEach(x => x.classList.toggle('on', x === b)); standUI(); }
  else { state[b.dataset.t] = !state[b.dataset.t]; b.classList.toggle('on', state[b.dataset.t]); }
  if (b.dataset.t === 'explode') document.getElementById('gap').hidden = !state.explode;
  build(); if (b.dataset.v || b.dataset.t === 'explode') fit();
}));
document.querySelectorAll('[data-a]').forEach(b => b.addEventListener('click', () => {
  state.angle = +b.dataset.a; standUI(); build(); fit();
}));
document.querySelectorAll('[data-c]').forEach(box => box.addEventListener('change', () => {
  state.show[box.dataset.c] = box.checked; build();
}));
const gapIn = document.getElementById('gap-in'), gapOut = document.getElementById('gap-out');
gapIn.addEventListener('input', () => {
  state.gap = +gapIn.value; gapOut.textContent = `${state.gap} mm`;
  for (const t of Object.values(group.userData.tilted)) t.children.forEach(place);
});
gapIn.addEventListener('change', fit);   // refit once the slider is released
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', bg);
new MutationObserver(bg).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
addEventListener('resize', onResize);
bg(); resize(); standUI(); build(); lastWide = cam.aspect >= 1; fit();
canvas.addEventListener('dblclick', fit);
document.getElementById('t-reset').addEventListener('click', fit);
// spec card collapses to its title line so it stays out of the way of the model; remembered per viewer
const specEl = document.getElementById('spec'), specMin = document.getElementById('spec-min');
function setSpecMin(min) {
  specEl.classList.toggle('min', min);
  specMin.textContent = min ? '+' : '−';
  specMin.setAttribute('aria-expanded', String(!min));
  const label = min ? '仕様を展開' : '仕様を折りたたむ';
  specMin.setAttribute('aria-label', label); specMin.title = label;
  try { localStorage.setItem('viewer.specMin', min ? '1' : '0'); } catch (e) {}
}
document.getElementById('spec-head').addEventListener('click', () => setSpecMin(!specEl.classList.contains('min')));
try { if (localStorage.getItem('viewer.specMin') === '1') setSpecMin(true); } catch (e) {}
(function loop() { requestAnimationFrame(loop); ctl.update(); renderer.render(scene, cam); })();
</script>
'''

if __name__ == '__main__':
    main()
