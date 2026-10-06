"""Interactive assembly guide: case/preview/assembly.html (uses model-data.js from case_viewer.py).

Each step names the groups of parts it adds; the page animates them into place, dims what is already
fitted and moves the camera to the view the step needs. Steps exist for both case variants.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_case import Half, OUT, STANDOFF, PORT_LIFT  # noqa: E402
from layout import WHEEL_DETENTS  # noqa: E402

BOARD = ['board', 'smd', 'sensor', 'conn', 'diode', 'socket', 'stab', 'oled']


def steps(variant, n_screws, n_holes, n_cover):
    s = []

    def add(title, text, new, view, parts=(), frm='top', board_only=False):
        s.append(dict(title=title, text=text, new=new, view=view, parts=list(parts), frm=frm, boardOnly=board_only))

    add('完成形', 'これから組み立てるキーボードの片側です。手順を進めると、部品が 1 つずつ所定の位置に入っていきます。'
        '下の「次へ」か、キーボードの → キーで進みます。', [], 'overview')
    add('基板', '製造した基板（2 層、1.6 mm）から始めます。部品はほぼすべて裏面に付きます。表面はスイッチと OLED だけです。',
        ['board'], 'top', ['プリント基板 × 1'], board_only=True)
    add('表面実装部品（裏面）',
        'RP2040、フラッシュ、3.3 V LDO、水晶、パスコンと抵抗、USB-C、TRRS ジャック、リセットスイッチを裏面に半田付けします。'
        'RP2040 は 0.4 mm ピッチで裏のサーマルパッドも GND につなぐ必要があるので、JLCPCB などの部品実装サービスを勧めます。'
        '手で付ける場合はホットエアかリフローを使ってください。部品番号は Fab 層の実装図（fab/&lt;side&gt;/nrsk-&lt;side&gt;-assembly-back.pdf）にあります。',
        ['smd', 'conn'], 'bottom',
        ['RP2040', 'W25Q128JVSIQ', 'AP2112K-3.3', '水晶 12 MHz', 'USB-C', 'PJ-320D', 'USBLC6-2SC6', '0805 の抵抗・コンデンサ',
         'ポリスイッチ', 'B5819W', 'PTS810'], 'bottom', True)
    add('ホイールのセンサー',
        '角に磁気角度センサー AS5600 と 2 個のコンデンサを付けます。ホイールの中心の真上にあたる位置です。1 番ピンの向きに注意してください。',
        ['sensor'], 'cornerBottom', ['AS5600-ASOM', '1 µF', '0.1 µF'], 'bottom', True)
    add('ダイオード',
        '各キーのダイオード 1N4148W を裏面に付けます（左 44 個、右 48 個）。カソード（帯のある側）の向きをシルクの線に合わせます。',
        ['diode'], 'bottom', ['1N4148W'], 'bottom', True)
    add('ホットスワップソケット',
        'Kailh の MX 用ホットスワップソケットを裏面に付けます。2 つのパッドに半田を盛り、ソケットを押し当てながら溶かすと浮きません。',
        ['socket'], 'bottom', ['Kailh CPG151101S11'], 'bottom', True)
    add('スタビライザー',
        '2 u 以上のキー（左 Shift、右 Backspace、右 Enter）に PCB マウントのスタビライザーをネジ止めします。プレートを付ける前に取り付けます。',
        ['stab'], 'top', ['ネジ止め式スタビライザー 2 u'], board_only=True)
    add('OLED',
        'OLED モジュールのピンヘッダの黒いスペーサーを外し、ガラス上面が基板から 2.5 mm になる高さで表面に半田付けします。'
        '上にハーフミラーのカバーが載り、プレートと面一になります。ピン順が GND / VCC / SCL / SDA であることを先に確認してください。',
        ['oled'], 'top', ['OLED 0.91 インチ'], board_only=True)
    n_plate = n_screws - n_cover
    if variant in ('print', 'printtop'):
        add('トレイ',
            f'3D プリントのトレイです（A と B で共通）。壁の中を縦にネジ穴（{n_screws} か所）が通り、上面には丸いくぼみ、その下に六角のナット受けがあります。'
            'A はナット受けに入れたナットへ上から、B はプレート裏のボスのインサートへ底からネジを締めます。',
            ['tray'], 'top', ['トレイ（3D プリント）'])
        add('ホイールと磁石',
            'ホイール上面のポケットに径方向着磁の磁石を接着し、ホイールの軸穴をトレイの床の軸に差し込みます。',
            ['wheel', 'magnet'], 'corner', ['ホイール', 'ネオジム磁石（径方向着磁）'])
        add('ボールプランジャー',
            f'ホイールの内側にあるブロックの穴に、M3 のボールプランジャーを外からねじ込みます。ホイールを回しながら少しずつ締め、'
            f'1 回転で {WHEEL_DETENTS} 回のクリックがはっきり出る位置で止めます。締めすぎると重くなります。',
            ['plunger'], 'corner', ['M3 ボールプランジャー'])
        add('角キャップ',
            'ホイールの上の壁は外せる部品（角キャップ）になっています。ホイールを入れたあと、段のある側を上にしてはめ込みます。'
            '上からプレートで押さえられるので、接着は要りません。',
            ['wheelcap'], 'corner', ['角キャップ（3D プリント）'])
        add('基板をトレイへ',
            f'USB-C と TRRS は基板の舌に載っていて、奥の壁の中のトンネルに収まります。基板は手前を少し持ち上げ、ボスより {PORT_LIFT:g} mm ほど浮かせて'
            '奥の壁に近づけ、舌を 2 つのトンネルに差し込みながら奥へ約 8 mm 滑らせます。舌が奥まで入ったら手前を下ろし、基板をボスの上に載せます。',
            BOARD, 'top', [], frm='slide')
        add('基板をネジ止め',
            f'{n_holes} 本の M2 × 6 mm タッピングネジで基板をボスに固定します。差込口は外面の穴のすぐ裏に来ます。',
            ['pcb_screw'], 'top', [f'M2 × 6 mm タッピングネジ × {n_holes}'])
        if variant == 'print':
            add('プレート',
                f'壁の上面のくぼみの奥にある六角のナット受け（{n_plate} か所）に M2 ナットを落とし込み、透明アクリルのプレートを載せて、'
                f'スリムヘッド小ねじ M2 × 6 mm で上から留めます。ナットは六角の穴で回り止めされます。',
                ['insert', 'plate', 'plate_screw'], 'top', ['プレート（透明アクリル 1.5 mm）', f'M2 ナット × {n_plate}', f'スリムヘッド M2 × 6 mm × {n_plate}'])
        else:
            add('プレート',
                f'3D プリントのプレートの裏のボス（{n_plate} か所）に、はんだごてで M2 ヒートセットインサートを押し込み、補強のある面を下にして載せます。'
                'スイッチの周りだけ 1.5 mm なので、スイッチの爪はアクリルのプレートと同じように掛かります。',
                ['insert', 'plate'], 'top', ['プレート（3D プリント）', f'M2 インサート × {n_plate}'])
            add('底からネジ止め',
                f'トレイを裏返し、底の座ぐりから M2 × 12 mm のなべネジ {n_plate} 本を締めてプレートを引き寄せます。プレートの上面にネジは見えません。',
                ['plate_screw'], 'bottom', [f'M2 × 12 mm × {n_plate}'], 'bottom')
    else:
        add('底板とホイール',
            '底板の角の穴に下から M3 × 8 mm のネジを通して軸にし、磁石を接着したホイールを差し込みます。',
            ['bottom', 'axle', 'wheel', 'magnet'], 'corner', ['底板（マットクリア 3 mm）', 'M3 × 8 mm', 'ホイール', '磁石'])
        add('プランジャーブロック',
            '3D プリントのブロックを底板の下から M2 × 6 mm のタッピングネジ 2 本で留め、M3 のボールプランジャーをねじ込みます。'
            f'ホイールを回しながら、1 回転 {WHEEL_DETENTS} クリックがはっきり出る位置まで締めます。',
            ['detent', 'block_screw', 'plunger'], 'corner', ['プランジャーブロック', 'M2 × 6 mm × 2', 'M3 ボールプランジャー'])
        add('スペーサー',
            f'底板の下から M2 × 5 mm のネジで、長さ {STANDOFF:g} mm のスペーサーを {n_holes} 本立てます。',
            ['standoff', 'bottom_screw'], 'top', [f'M2 スペーサー {STANDOFF:g} mm × {n_holes}', f'M2 × 5 mm × {n_holes}'])
        add('枠',
            'マットクリアの枠を frame1 から順に 4 枚重ねます。frame1〜3 にはプラグ用の切り欠きがあります。',
            ['frame1', 'frame2', 'frame3', 'frame4'], 'top', ['枠（マットクリア 3 mm）× 4'])
        add('基板',
            f'基板をスペーサーに載せ、M2 × 4 mm のネジ {n_holes} 本で留めます。',
            BOARD + ['pcb_screw'], 'top', [f'M2 × 4 mm × {n_holes}'])
        add('プレートと外周のネジ',
            f'プレートを載せ、外周の {n_screws} か所を上から M2 × 20 mm のネジで、底板の下のナットまで共締めします。',
            ['plate', 'case_screw', 'nut'], 'top', ['プレート（透明アクリル 1.5 mm）', f'M2 × 20 mm × {n_screws}', f'M2 ナット × {n_screws}'])
    add('OLED カバー',
        'OLED のガラス面と、カバーの縁が載る壁の上面に透明両面テープを貼り、角丸長方形のハーフミラーをプレートの切り欠きにはめて押さえます。ネジは使いません。'
        + ('3D プリント版は壁の上面が 0.5 mm 下がっているので、上面がプレートと面一になります。' if variant != 'acrylic'
           else 'アクリル版は最上段の枠に載るので、プレートより 0.5 mm 高くなります。'),
        ['cover'], 'top', ['ハーフミラーアクリル 2 mm', '透明両面テープ 0.5 mm'])
    add('キースイッチ',
        'MX 互換スイッチをプレートの上から差し込みます。ピンが曲がっていないか確かめ、まっすぐ押し込んでソケットに入れます。最後にキーキャップを付けます。',
        ['switch'], 'top', ['MX 互換スイッチ'])
    add('ゴム足', '底の四隅にゴム足を貼ります。', ['feet'], 'bottom', ['ゴム足 × 4'], 'bottom')
    add('接続と書き込み',
        '左右を TRRS ケーブルでつなぎ、片側を USB-C でパソコンにつなぎます。最初はフラッシュが空なので、USB を挿すと RPI-RP2 ドライブが出ます。'
        'QMK でビルドした nrsk_default.uf2 をコピーすれば完成です（左右とも同じファームウェア）。TRRS は USB を挿したまま抜き差ししないでください。',
        [], 'overview', ['TRRS ケーブル', 'USB-C ケーブル'])
    return s


def main():
    data = {}
    for variant in ('print', 'printtop', 'acrylic'):
        hf = Half('left')
        data[variant] = steps(variant, len(hf.screws), len(hf.d['holes']), len(hf.cover_screws))
    focus = {}
    for side in ('left', 'right'):
        (wx, wy), _ = Half(side).wheel_xy()
        focus[side] = [wx, -wy]
    html = TEMPLATE.replace('__STEPS__', json.dumps(data, ensure_ascii=False)).replace('__FOCUS__', json.dumps(focus)).replace('__LIFT__', f'{PORT_LIFT:g}')
    path = os.path.join(OUT, 'preview', 'assembly.html')
    open(path, 'w').write(html)
    print('wrote', path, len(data['print']), 'print steps,', len(data['acrylic']), 'acrylic steps')


TEMPLATE = r'''<title>nrsk Assembly Guide</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+JP:wght@400;600&family=IBM+Plex+Mono:wght@400&display=swap">
<style>
/* Full-bleed 3D stage; a toolbar at the top, the step list on the right (desktop) and the step card below */
:root{--bg:#eef1f4;--panel:#ffffffeb;--fg:#1b2129;--muted:#5d6773;--line:#c9d1da;--accent:#1f6b3a;--on-accent:#ffffff;--chip:#e3e9ee;
 --sans:"IBM Plex Sans JP",system-ui,-apple-system,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#14181d;--panel:#1d232aeb;--fg:#e6eaee;--muted:#9aa5b1;--line:#34404c;--accent:#5fc285;--on-accent:#0d1a12;--chip:#2a333d;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#14181d;--panel:#1d232aeb;--fg:#e6eaee;--muted:#9aa5b1;--line:#34404c;--accent:#5fc285;--on-accent:#0d1a12;--chip:#2a333d;color-scheme:dark}
html,body{height:100%}
body{background:var(--bg);color:var(--fg);font:14px/1.6 var(--sans);overflow:hidden}
#view{position:fixed;inset:0;width:100%;height:100%;touch-action:none}
.panel{position:fixed;background:var(--panel);border:1px solid var(--line);border-radius:10px;backdrop-filter:blur(6px);box-sizing:border-box}
#bar{left:16px;top:calc(16px + env(safe-area-inset-top,0px));display:flex;flex-wrap:wrap;align-items:center;gap:6px;padding:8px 10px;max-width:calc(100vw - 32px)}
#bar h1{font-size:14px;font-weight:600;margin:0 6px 0 2px;white-space:nowrap}
#bar a{color:var(--accent);font-size:13px;margin-left:4px}
.sep{width:1px;align-self:stretch;background:var(--line);margin:0 2px}
button{font:inherit;font-size:13px;border:1px solid var(--line);background:transparent;color:var(--fg);border-radius:6px;padding:4px 10px;cursor:pointer}
button.on{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button:disabled{opacity:.4;cursor:default}
#list{right:16px;top:calc(16px + env(safe-area-inset-top,0px));width:250px;max-height:calc(100vh - 300px);overflow:auto;padding:8px 6px}
#list ol{margin:0;padding:0;list-style:none;counter-reset:s}
#list li{counter-increment:s;display:flex;gap:8px;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:13px;line-height:1.4}
#list li::before{content:counter(s);font-family:var(--mono);color:var(--muted);min-width:1.6em;text-align:right;font-variant-numeric:tabular-nums}
#list li.done{color:var(--muted)}
#list li.cur{background:var(--accent);color:var(--on-accent)}#list li.cur::before{color:var(--on-accent)}
#card{left:50%;transform:translateX(-50%);bottom:calc(16px + env(safe-area-inset-bottom,0px));width:min(720px,calc(100vw - 32px));padding:12px 16px 12px}
#card .head{display:flex;align-items:baseline;gap:10px}
#card .num{font-family:var(--mono);font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
#card h2{margin:0;font-size:17px;font-weight:600;text-wrap:balance}
#card p{margin:6px 0 8px;max-width:65ch;font-size:13.5px}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin:0 0 10px;padding:0;list-style:none}
.chips li{background:var(--chip);border-radius:999px;padding:1px 9px;font-size:12px}
.controls{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.progress{flex:1;min-width:80px;height:4px;background:var(--line);border-radius:2px;overflow:hidden}
.progress i{display:block;height:100%;background:var(--accent);width:0;transition:width .3s}
@media (max-width:900px){#list{display:none}}
@media (max-width:560px){#card p{font-size:13px}#bar h1{display:none}}
</style>
<canvas id="view" aria-label="組み立て手順の 3D 表示。ドラッグで回転、右ドラッグか 2 本指でパン、ホイールかピンチでズーム"></canvas>
<div id="bar" class="panel">
 <h1>nrsk 組み立てガイド</h1>
 <button data-v="print" class="on">A：プリント + アクリル蓋</button><button data-v="printtop">B：全部プリント</button><button data-v="acrylic">アクリル版</button>
 <span class="sep"></span>
 <button data-s="left" class="on">左</button><button data-s="right">右</button>
 <span class="sep"></span>
 <button id="dim" class="on" aria-pressed="true">組み付け済みを薄く</button>
 <a href="./">ケースビューワー</a>
</div>
<nav id="list" class="panel" aria-label="手順の一覧"><ol id="steps"></ol></nav>
<section id="card" class="panel" aria-live="polite">
 <div class="head"><span class="num" id="num"></span><h2 id="title"></h2></div>
 <p id="text"></p>
 <ul class="chips" id="parts"></ul>
 <div class="controls">
  <button id="prev">◀ 前へ</button><button id="play">▶ 再生</button><button id="next">次へ ▶</button>
  <button id="again" title="この手順のアニメーションをもう一度">↻</button>
  <div class="progress"><i id="bar-i"></i></div>
 </div>
</section>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script src="model-data.js"></script>
<script>
const {DATA, POOL, BOARDS, Z} = window.NRSK;
const STEPS = __STEPS__;
const FOCUS = __FOCUS__;   // wheel centre per side (viewer frame)
const PCBA = ['board', 'smd', 'sensor', 'conn', 'diode', 'socket', 'stab', 'oled', 'switch'];
const MATERIAL = {matte: {color: '#e6edf1', roughness: 0.95, metalness: 0.0}, clear: {color: '#d8e6ee', roughness: 0.1, metalness: 0.0},
                  mirror: {color: '#3a4048', roughness: 0.08, metalness: 0.9}};
const OPACITY = {plate: 0.45, bottom: 0.6, frame1: 0.6, frame2: 0.6, frame3: 0.6, frame4: 0.6, cover: 0.85};
const b64 = (s, T) => { const b = atob(s), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return new T(u.buffer); };

const canvas = document.getElementById('view');
const renderer = new THREE.WebGLRenderer({canvas, antialias: true}); renderer.setPixelRatio(devicePixelRatio);
const scene = new THREE.Scene();
const cam = new THREE.PerspectiveCamera(35, 1, 1, 5000);
cam.up.set(0, 0, 1);
const ctl = new THREE.OrbitControls(cam, canvas);
ctl.enableDamping = true; ctl.dampingFactor = 0.12; ctl.rotateSpeed = 0.7; ctl.screenSpacePanning = true;
ctl.mouseButtons = {LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN};
ctl.touches = {ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN};
scene.add(new THREE.HemisphereLight(0xffffff, 0x666666, 0.9));
const dl = new THREE.DirectionalLight(0xffffff, 0.6); dl.position.set(200, -300, 400); scene.add(dl);
const dl2 = new THREE.DirectionalLight(0xffffff, 0.35); dl2.position.set(-150, 200, -300); scene.add(dl2);
function bg() { scene.background = new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()); }

// ---- geometry ----------------------------------------------------------------------------------------
const geoCache = [];
function poolGeo(id) {
  if (geoCache[id]) return geoCache[id];
  const p = POOL[id], q = b64(p.v, Int16Array), v = new Float32Array(q.length);
  for (let i = 0; i < q.length; i++) v[i] = q[i] * p.s[i % 3] + p.o[i % 3];
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(v, 3));
  g.setIndex(new THREE.BufferAttribute(b64(p.i, p.big ? Uint32Array : Uint16Array), 1));
  g.computeVertexNormals();
  return geoCache[id] = g;
}
function poolMat(id) {
  const p = POOL[id], [r, g, b, a] = p.mat.c;
  return new THREE.MeshStandardMaterial({color: new THREE.Color(r, g, b).convertLinearToSRGB(), metalness: Math.min(p.mat.m, 0.6),
    roughness: Math.max(p.mat.r, 0.25), transparent: true, opacity: a, side: THREE.DoubleSide});
}
function instanced(list) {
  const g = new THREE.Group(), m4 = new THREE.Matrix4();
  for (const [id, inst] of list) {
    const mats = b64(inst, Float32Array), n = mats.length / 16;
    const mesh = new THREE.InstancedMesh(poolGeo(id), poolMat(id), n);
    mesh.userData.base = mesh.material.opacity;
    for (let i = 0; i < n; i++) mesh.setMatrixAt(i, m4.fromArray(mats, i * 16));
    g.add(mesh);
  }
  return g;
}
function plain(m, color, op) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(b64(m.v, Float32Array), 3));
  g.setIndex(new THREE.BufferAttribute(b64(m.i, Uint32Array), 1));
  g.computeVertexNormals();
  const look = MATERIAL[color] || {color, roughness: 0.6, metalness: color === '#a9adb3' ? 0.7 : 0.05};
  const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial(Object.assign({transparent: true, opacity: op, flatShading: true}, look)));
  mesh.userData.base = op;
  return mesh;
}
// groups[name] = THREE.Group placed at its final position
let groups = {}, root = null;
const state = {v: 'print', side: 'left', step: 0, dim: true, playing: false};
function build() {
  if (root) scene.remove(root);
  root = new THREE.Group(); groups = {};
  const zp = Z[state.v].pcb;
  const put = (name, obj) => { if (!groups[name]) { groups[name] = new THREE.Group(); root.add(groups[name]); } groups[name].add(obj); };
  for (const [side, name, m, color, op] of DATA[state.v]) {
    if (side !== state.side) continue;
    if (name === 'pcba') {
      for (const [cat, list] of Object.entries(BOARDS[side].pcba)) { const o = instanced(list); o.position.z = zp; put(cat, o); }
      const sw = instanced(Object.values(BOARDS[side].switches).flat()); sw.position.z = zp; put('switch', sw);
      continue;
    }
    if (['pcb', 'oled'].includes(name) && BOARDS) continue;
    put(name, plain(m, color, OPACITY[name] || op));
  }
  for (const g of Object.values(groups)) g.userData.home = g.position.clone();
  scene.add(root);
}

// ---- steps -------------------------------------------------------------------------------------------
const anim = {t0: 0, dur: 0, items: []};
function opacityOf(group, f) { group.traverse(o => { if (o.material) o.material.opacity = (o.userData.base ?? 1) * f; }); }
// parts added in the current step glow in the accent colour so small ones (plunger, magnet, inserts) stand out
function glow(group, on) {
  const c = new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue('--accent').trim());
  group.traverse(o => { if (o.material && o.material.emissive) o.material.emissive.copy(on ? c : new THREE.Color(0)).multiplyScalar(on ? 0.45 : 0); });
}
function visibleAt(i) {
  // groups fitted up to step i (step 0 shows the finished keyboard)
  const steps = STEPS[state.v];
  if (i === 0 || i === steps.length - 1) return new Set(Object.keys(groups));
  const s = new Set();
  for (let k = 1; k <= i; k++) steps[k].new.forEach(n => s.add(n));
  // the board is built on the bench first, then the case; it joins the case at its own step
  const joins = steps.findIndex(st => !st.boardOnly && st.new.includes('board'));
  if (steps[i].boardOnly) { for (const n of [...s]) if (!PCBA.includes(n)) s.delete(n); }
  else if (i < joins) { for (const n of PCBA) s.delete(n); }
  return s;
}
function show(i, animate = true) {
  const steps = STEPS[state.v];
  state.step = i = Math.max(0, Math.min(steps.length - 1, i));
  const st = steps[i], vis = visibleAt(i), fresh = new Set(i === 0 || i === steps.length - 1 ? [] : st.new);
  anim.items = [];
  for (const [name, g] of Object.entries(groups)) {
    g.visible = vis.has(name);
    g.position.copy(g.userData.home);
    const isNew = fresh.has(name);
    glow(g, isNew);
    opacityOf(g, isNew || !state.dim || fresh.size === 0 ? 1 : 0.28);
    if (isNew && animate && g.visible) {
      anim.items.push(g);
      if (st.frm === 'slide') g.position.add(slidePos(0)); else g.position.z += st.frm === 'bottom' ? -45 : 45;
      opacityOf(g, 0);
    }
  }
  anim.t0 = performance.now(); anim.dur = anim.items.length ? (st.frm === 'slide' ? 2600 : 1100) : 0;
  view(st.view, animate);
  // card
  document.getElementById('num').textContent = `手順 ${i + 1} / ${steps.length}`;
  document.getElementById('title').textContent = st.title;
  document.getElementById('text').innerHTML = st.text;
  document.getElementById('parts').innerHTML = st.parts.map(p => `<li>${p}</li>`).join('');
  document.getElementById('bar-i').style.width = `${100 * i / (steps.length - 1)}%`;
  document.getElementById('prev').disabled = i === 0;
  document.getElementById('next').disabled = i === steps.length - 1;
  document.querySelectorAll('#steps li').forEach((li, k) => { li.classList.toggle('cur', k === i); li.classList.toggle('done', k < i); });
  const cur = document.querySelector('#steps li.cur'); if (cur) cur.scrollIntoView({block: 'nearest'});
}
// board into the port tunnels: down to just above the bosses, slide back tongue-first, then drop
const SLIDE = 8, LIFT = __LIFT__;
function slidePos(t) {
  const ease = u => 1 - Math.pow(1 - Math.max(0, Math.min(1, u)), 3);
  const a = ease(t / 0.4), b = ease((t - 0.45) / 0.35), c = ease((t - 0.85) / 0.15);
  return new THREE.Vector3(0, -SLIDE * (1 - b), LIFT * (1 - c) + 40 * (1 - a));
}
function tick(now) {
  if (!anim.dur) return;
  const t = Math.min(1, (now - anim.t0) / anim.dur), e = 1 - Math.pow(1 - t, 3);
  const st = STEPS[state.v][state.step], dz = st.frm === 'bottom' ? -45 : 45;
  for (const g of anim.items) {
    if (st.frm === 'slide') { g.position.copy(g.userData.home).add(slidePos(t)); opacityOf(g, Math.min(1, t * 4)); }
    else { g.position.z = g.userData.home.z + dz * (1 - e); opacityOf(g, e); }
  }
  if (t >= 1) anim.dur = 0;
}

// ---- camera ------------------------------------------------------------------------------------------
const camAnim = {t0: 0, from: null, to: null};
function view(kind, animate) {
  const st = STEPS[state.v][state.step];
  // instanced KiCad parts report no bounds to three.js, so frame on the case parts (or the case outline)
  let box = new THREE.Box3();
  for (const [n, g] of Object.entries(groups)) if (g.visible && !PCBA.includes(n)) box.expandByObject(g);
  if (st.boardOnly || box.isEmpty() || box.getSize(new THREE.Vector3()).x < 40) box = new THREE.Box3().setFromObject(groups.tray || groups.bottom);
  let c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
  let dir;
  if (kind === 'bottom') dir = new THREE.Vector3(0, -0.45, -1);
  else if (kind === 'top') dir = new THREE.Vector3(0, -0.6, 1);
  else if (kind === 'corner' || kind === 'cornerBottom') {
    const [fx, fy] = FOCUS[state.side];
    c = new THREE.Vector3(fx, fy, Z[state.v].pcb - 3); size = 90;
    dir = kind === 'corner' ? new THREE.Vector3(state.side === 'left' ? 0.5 : -0.5, -0.8, 0.9) : new THREE.Vector3(state.side === 'left' ? 0.4 : -0.4, -0.6, -1);
  } else dir = new THREE.Vector3(0.25, -0.75, 0.66);
  dir.normalize();
  const fov = THREE.MathUtils.degToRad(cam.fov), aspect = Math.max(cam.aspect, 0.6);
  const d = (size * 0.7) / Math.tan(fov / 2) / Math.min(1, aspect);
  if (!kind.startsWith('corner')) c.y -= size * 0.1;   // keep the model above the step card
  const to = {p: c.clone().addScaledVector(dir, d), t: c};
  if (!animate) { cam.position.copy(to.p); ctl.target.copy(to.t); camAnim.to = null; return; }
  camAnim.from = {p: cam.position.clone(), t: ctl.target.clone()}; camAnim.to = to; camAnim.t0 = performance.now();
}
function camTick(now) {
  if (!camAnim.to) return;
  const t = Math.min(1, (now - camAnim.t0) / 800), e = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  cam.position.lerpVectors(camAnim.from.p, camAnim.to.p, e); ctl.target.lerpVectors(camAnim.from.t, camAnim.to.t, e);
  if (t >= 1) camAnim.to = null;
}

// ---- UI ----------------------------------------------------------------------------------------------
function list() {
  document.getElementById('steps').innerHTML = STEPS[state.v].map(s => `<li tabindex="0">${s.title}</li>`).join('');
  document.querySelectorAll('#steps li').forEach((li, k) => {
    li.addEventListener('click', () => { stop(); show(k); });
    li.addEventListener('keydown', e => { if (e.key === 'Enter') { stop(); show(k); } });
  });
}
let timer = null;
function stop() { state.playing = false; clearTimeout(timer); document.getElementById('play').textContent = '▶ 再生'; }
function play() {
  if (state.step >= STEPS[state.v].length - 1) show(0);
  state.playing = true; document.getElementById('play').textContent = '❚❚ 一時停止';
  const nextLater = () => { timer = setTimeout(() => {
    if (!state.playing) return;
    if (state.step >= STEPS[state.v].length - 1) return stop();
    show(state.step + 1); nextLater(); }, 4200); };
  nextLater();
}
document.getElementById('prev').onclick = () => { stop(); show(state.step - 1); };
document.getElementById('next').onclick = () => { stop(); show(state.step + 1); };
document.getElementById('again').onclick = () => show(state.step);
document.getElementById('play').onclick = () => state.playing ? stop() : play();
document.getElementById('dim').onclick = e => { state.dim = !state.dim; e.target.classList.toggle('on', state.dim); e.target.setAttribute('aria-pressed', state.dim); show(state.step, false); };
document.querySelectorAll('[data-v]').forEach(b => b.onclick = () => {
  state.v = b.dataset.v; document.querySelectorAll('[data-v]').forEach(x => x.classList.toggle('on', x === b));
  stop(); build(); list(); show(Math.min(state.step, STEPS[state.v].length - 1), false);
});
document.querySelectorAll('[data-s]').forEach(b => b.onclick = () => {
  state.side = b.dataset.s; document.querySelectorAll('[data-s]').forEach(x => x.classList.toggle('on', x === b));
  build(); show(state.step, false);
});
addEventListener('keydown', e => {
  if (e.target.closest && e.target.closest('button,li')) return;
  if (e.key === 'ArrowRight') { stop(); show(state.step + 1); }
  if (e.key === 'ArrowLeft') { stop(); show(state.step - 1); }
  if (e.key === ' ') { e.preventDefault(); state.playing ? stop() : play(); }
});
function resize() {
  const w = document.documentElement.clientWidth || innerWidth, h = document.documentElement.clientHeight || innerHeight;
  renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix();
}
addEventListener('resize', () => { resize(); show(state.step, false); });
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', bg);
new MutationObserver(bg).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
bg(); resize(); build(); list(); show(0, false);
(function loop(now) { requestAnimationFrame(loop); tick(now || 0); camTick(now || 0); ctl.update(); renderer.render(scene, cam); })();
</script>
'''

if __name__ == '__main__':
    main()
