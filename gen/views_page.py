"""Design-review page for the orbit renders -> docs/views.html.

The renders come from gen/render_views.sh (docs/img/views/view-a<azimuth>-e<elevation>-<variant>.jpg);
the close-ups next to them are the A / B renders of gen/render_compare.sh. Open docs/views.html in a browser.
"""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DOCS = os.path.join(ROOT, 'docs')
VIEWS = os.path.join(DOCS, 'img', 'views')
# close-ups per variant: (label, file under docs/img)
DETAILS = {
    'a': [('全体', 'render-hero-top-acrylic-lowpan.png'), ('OLED', 'render-oled-top-acrylic-lowpan.png'),
          ('左のホイール', 'render-wheel-left-top-acrylic-lowpan.png'), ('USB-C × 2', 'render-ports.png')],
    'b': [('全体', 'render-hero-top-print.png'), ('OLED', 'render-oled-top-print.png'),
          ('左のホイール', 'render-wheel-left-top-print.png')],
}


def main():
    views = {}
    for f in sorted(os.listdir(VIEWS)):
        m = re.fullmatch(r'view-a(\d+)-e(\d+)-([ab])\.jpg', f)
        if m:
            views.setdefault(m[3], {})[f'{m[1]}-{m[2]}'] = f'img/views/{f}'
    details = {v: [(t, f'img/{f}') for t, f in items if os.path.exists(os.path.join(DOCS, 'img', f))]
               for v, items in DETAILS.items()}
    data = json.dumps({'views': views, 'details': details}, ensure_ascii=False)
    out = os.path.join(DOCS, 'views.html')
    with open(out, 'w') as fh:
        fh.write(TEMPLATE.replace('/*DATA*/null', data))
    print('wrote', out, sum(len(v) for v in views.values()), 'views')


TEMPLATE = r'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>nrsk Design Views</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+JP:wght@400;600&family=IBM+Plex+Mono:wght@400&display=swap">
<style>
/* Layout: one large stage (or A | B side by side) with the camera controls beside it, contact sheet and close-ups below */
:root{--bg:#eef1f4;--panel:#ffffff;--fg:#1b2129;--muted:#5d6773;--line:#c9d1da;--accent:#1f6b3a;--on-accent:#ffffff;
 --key:#f24d00;--stage:#f4f4f2;
 --sans:"IBM Plex Sans JP",system-ui,-apple-system,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#14181d;--panel:#1d232a;--fg:#e6eaee;--muted:#9aa5b1;--line:#34404c;--accent:#5fc285;--on-accent:#0d1a12;--key:#ff7a3d;--stage:#2a2f35;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#14181d;--panel:#1d232a;--fg:#e6eaee;--muted:#9aa5b1;--line:#34404c;--accent:#5fc285;--on-accent:#0d1a12;--key:#ff7a3d;--stage:#2a2f35;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 var(--sans)}
main{max-width:1320px;margin:0 auto;padding:28px 20px 64px;display:grid;gap:36px}
h1{font-size:22px;font-weight:600;margin:0;text-wrap:balance}
h2{font-size:15px;font-weight:600;margin:0 0 12px;text-wrap:balance}
header{display:flex;flex-wrap:wrap;align-items:end;justify-content:space-between;gap:16px}
header p{margin:4px 0 0;color:var(--muted);max-width:62ch}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--panel)}
.seg button{font:inherit;border:0;background:none;color:var(--fg);padding:7px 14px;cursor:pointer;white-space:nowrap}
.seg button+button{border-left:1px solid var(--line)}
.seg button[aria-pressed="true"]{background:var(--accent);color:var(--on-accent)}
.seg button:disabled{color:var(--line);cursor:default}
button:focus-visible,.thumb:focus-visible,.dot:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.viewer{display:grid;grid-template-columns:minmax(0,1fr) 220px;gap:20px;align-items:start}
.stages{display:grid;gap:12px;grid-template-columns:minmax(0,1fr)}
.stages.two{grid-template-columns:repeat(2,minmax(0,1fr))}
figure{margin:0;min-width:0}
.stage{position:relative;aspect-ratio:3/2;max-width:100%;background:var(--stage);border-radius:6px;overflow:hidden;cursor:grab;touch-action:pan-y;user-select:none}
.stage:active{cursor:grabbing}
.stage img{display:block;width:100%;height:100%;object-fit:cover;-webkit-user-drag:none}
.stage .tag{position:absolute;left:10px;top:10px;font:12px/1 var(--mono);background:var(--panel);color:var(--fg);padding:5px 7px;border-radius:4px;opacity:.92}
figcaption{font-size:12px;color:var(--muted);margin-top:6px}
.controls{display:grid;gap:18px;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px}
.label{font-size:11px;letter-spacing:.06em;color:var(--muted);text-transform:uppercase;margin-bottom:6px}
.compass{width:100%;max-width:188px;display:block;margin:0 auto}
.compass .ring{fill:none;stroke:var(--line)}
.compass .kb{fill:var(--stage);stroke:var(--muted)}
.compass .front{fill:var(--muted);font:9px var(--mono)}
.dot{cursor:pointer}
.dot circle{fill:var(--panel);stroke:var(--muted);stroke-width:1.5}
.dot.on circle{fill:var(--key);stroke:var(--key)}
.dot.off{cursor:default}.dot.off circle{stroke:var(--line);stroke-dasharray:2 2}
.elev{display:grid;gap:4px}
.elev button{font:inherit;text-align:left;border:1px solid var(--line);border-radius:6px;background:none;color:var(--fg);padding:6px 10px;cursor:pointer;display:flex;justify-content:space-between;gap:8px}
.elev button span:last-child{font-family:var(--mono);color:var(--muted)}
.elev button[aria-pressed="true"]{border-color:var(--accent);box-shadow:inset 3px 0 0 var(--accent)}
.readout{font:13px/1.5 var(--mono);font-variant-numeric:tabular-nums}
.hint{font-size:12px;color:var(--muted);margin:0}
.sheet{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px}
.thumb{border:0;padding:0;background:none;color:var(--fg);font:inherit;text-align:left;cursor:pointer;min-width:0}
.thumb img{display:block;width:100%;aspect-ratio:3/2;object-fit:cover;border-radius:5px;background:var(--stage);border:2px solid transparent}
.thumb[aria-current="true"] img{border-color:var(--key)}
.thumb span{display:block;font-size:12px;color:var(--muted);margin-top:3px}
.details{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
.details a{color:inherit;text-decoration:none}
.details img{display:block;width:100%;border-radius:5px;background:var(--stage)}
.empty{color:var(--muted)}
@media (max-width:860px){.viewer{grid-template-columns:minmax(0,1fr)}.controls{grid-template-columns:1fr 1fr}.controls .wide{grid-column:1/-1}}
@media (max-width:560px){.stages.two{grid-template-columns:minmax(0,1fr)}.controls{grid-template-columns:minmax(0,1fr)}.compass{max-width:150px}.seg button{padding:7px 10px}}
@media (prefers-reduced-motion:no-preference){.stage img{transition:opacity .12s}}
</style>
<main>
  <header>
    <div>
      <h1>nrsk デザイン確認</h1>
      <p>Blender（Cycles）で筐体 A・B を周囲 15 か所から撮った完成イメージです。方位と仰角を選ぶか、画像を左右にドラッグして視点を回します。</p>
    </div>
    <div class="seg" role="group" aria-label="筐体">
      <button id="v-a" data-v="a">A アクリル</button>
      <button id="v-b" data-v="b">B プリント</button>
      <button id="v-ab" data-v="ab">並べて比較</button>
    </div>
  </header>

  <section class="viewer" aria-label="視点">
    <div class="stages" id="stages"></div>
    <div class="controls">
      <div>
        <div class="label">方位</div>
        <svg class="compass" id="compass" viewBox="-100 -100 200 200" role="group" aria-label="方位"></svg>
      </div>
      <div>
        <div class="label">仰角</div>
        <div class="elev" id="elev"></div>
      </div>
      <div class="wide">
        <div class="readout" id="readout"></div>
        <p class="hint">← → で方位、↑ ↓ で仰角を切り替えます。</p>
      </div>
    </div>
  </section>

  <section>
    <h2 id="sheet-title">全視点</h2>
    <div class="sheet" id="sheet"></div>
  </section>

  <section>
    <h2>寄りの画像</h2>
    <div class="details" id="details"></div>
  </section>
</main>
<script>
const DATA = /*DATA*/null;
const AZ_NAME = {0:'正面', 45:'右前', 90:'右', 135:'右後ろ', 180:'背面', 225:'左後ろ', 270:'左', 315:'左前'};
const EL_NAME = {10:'低い視点', 30:'標準', 60:'見下ろし', 90:'真上'};
const V_NAME = {a:'A アクリル', b:'B 3D プリント'};
const keys = new Set(Object.values(DATA.views).flatMap(o => Object.keys(o)));
const views = [...keys].map(k => k.split('-').map(Number)).sort((p, q) => q[1] - p[1] || p[0] - q[0]);
const elevs = [...new Set(views.map(v => v[1]))].sort((a, b) => b - a);
const azsAt = el => views.filter(v => v[1] === el).map(v => v[0]).sort((a, b) => a - b);
const state = {v: 'a', az: 45, el: 30};
try { Object.assign(state, JSON.parse(localStorage.getItem('nrsk-views') || '{}')); } catch (e) {}
if (!keys.has(`${state.az}-${state.el}`)) { state.az = views[0]?.[0] ?? 0; state.el = views[0]?.[1] ?? 30; }
if (!(state.v in DATA.views) && state.v !== 'ab') state.v = Object.keys(DATA.views)[0] || 'a';

const $ = id => document.getElementById(id);
const name = (az, el) => el === 90 ? '真上' : `${AZ_NAME[az] ?? az + '°'}・${EL_NAME[el] ?? el + '°'}`;
const variants = () => state.v === 'ab' ? ['a', 'b'] : [state.v];

function buildCompass() {
  const svg = $('compass'), ns = 'http://www.w3.org/2000/svg';
  svg.innerHTML = '<circle class="ring" r="72"/>' +
    '<rect class="kb" x="-40" y="-14" width="34" height="26" rx="3" transform="rotate(-6 -23 -1)"/>' +
    '<rect class="kb" x="6" y="-14" width="38" height="26" rx="3" transform="rotate(6 25 -1)"/>' +
    '<text class="front" x="0" y="40" text-anchor="middle">FRONT</text>';
  for (let az = 0; az < 360; az += 45) {
    const a = az * Math.PI / 180, g = document.createElementNS(ns, 'g');
    g.setAttribute('class', 'dot'); g.dataset.az = az; g.setAttribute('tabindex', '0'); g.setAttribute('role', 'button');
    g.setAttribute('aria-label', AZ_NAME[az]);
    g.innerHTML = `<circle cx="${(72 * Math.sin(a)).toFixed(1)}" cy="${(72 * Math.cos(a)).toFixed(1)}" r="9"/>`;
    g.addEventListener('click', () => pick(az, state.el));
    g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(az, state.el); } });
    svg.appendChild(g);
  }
}

function buildElev() {
  $('elev').innerHTML = elevs.map(el =>
    `<button id="el-${el}" data-el="${el}"><span>${EL_NAME[el] ?? ''}</span><span>${el}°</span></button>`).join('');
  $('elev').querySelectorAll('button').forEach(b => b.addEventListener('click', () => pick(state.az, +b.dataset.el)));
}

function nearestAz(az, el) {
  const list = azsAt(el);
  const d = x => Math.min(Math.abs(x - az), 360 - Math.abs(x - az));
  return list.reduce((best, x) => d(x) < d(best) ? x : best, list[0]);
}

function pick(az, el) {
  if (!keys.has(`${az}-${el}`)) az = nearestAz(az, el);
  state.az = az; state.el = el;
  render();
}

function step(dir) {
  const list = azsAt(state.el);
  if (list.length < 2) return;
  const i = list.indexOf(state.az);
  pick(list[(i + dir + list.length) % list.length], state.el);
}

function stepElev(dir) {
  const i = elevs.indexOf(state.el), j = i - dir;
  if (j >= 0 && j < elevs.length) pick(state.az, elevs[j]);
}

function src(v, az, el) { return DATA.views[v]?.[`${az}-${el}`]; }

function renderStages() {
  const box = $('stages'), vs = variants();
  box.className = 'stages' + (vs.length > 1 ? ' two' : '');
  if (box.children.length !== vs.length) {
    box.innerHTML = vs.map(v => `<figure><div class="stage" data-v="${v}"><img alt=""><span class="tag"></span></div><figcaption></figcaption></figure>`).join('');
    box.querySelectorAll('.stage').forEach(dragToTurn);
  }
  box.querySelectorAll('figure').forEach((fig, i) => {
    const v = vs[i], s = fig.querySelector('.stage'), img = s.querySelector('img'), url = src(v, state.az, state.el);
    s.dataset.v = v;
    if (url && img.getAttribute('src') !== url) img.src = url;
    img.hidden = !url;
    img.alt = `${V_NAME[v]}、${name(state.az, state.el)}`;
    s.querySelector('.tag').textContent = vs.length > 1 ? V_NAME[v] : `${state.az}° / ${state.el}°`;
    fig.querySelector('figcaption').textContent = url ? '' : 'この視点の画像はまだありません（gen/render_views.sh で描画）';
  });
}

function renderControls() {
  const avail = azsAt(state.el);
  $('compass').querySelectorAll('.dot').forEach(g => {
    const az = +g.dataset.az, ok = avail.includes(az) && state.el !== 90;
    g.classList.toggle('on', az === state.az && state.el !== 90);
    g.classList.toggle('off', !ok);
    g.setAttribute('aria-pressed', az === state.az);
    g.setAttribute('aria-disabled', !ok);
  });
  $('elev').querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', +b.dataset.el === state.el));
  document.querySelectorAll('header .seg button').forEach(b => {
    b.setAttribute('aria-pressed', b.dataset.v === state.v);
    b.disabled = b.dataset.v !== 'ab' && !(b.dataset.v in DATA.views);
  });
  $('readout').textContent = `${name(state.az, state.el)}　方位 ${state.az}° 仰角 ${state.el}°`;
}

function renderSheet() {
  const v = state.v === 'ab' ? 'a' : state.v;
  $('sheet-title').textContent = `全視点（${V_NAME[v]}）`;
  const list = views.filter(([az, el]) => src(v, az, el));
  $('sheet').innerHTML = list.length ? list.map(([az, el]) =>
    `<button class="thumb" data-az="${az}" data-el="${el}" aria-current="${az === state.az && el === state.el}">
       <img loading="lazy" src="${src(v, az, el)}" alt="${name(az, el)}"><span>${name(az, el)}　${az}° / ${el}°</span></button>`).join('')
    : '<p class="empty">まだ描画されていません。gen/render_views.sh を実行してください。</p>';
  $('sheet').querySelectorAll('.thumb').forEach(b => b.addEventListener('click', () => {
    pick(+b.dataset.az, +b.dataset.el);
    $('stages').scrollIntoView({behavior: 'smooth', block: 'nearest'});
  }));
}

function renderDetails() {
  const html = variants().flatMap(v => (DATA.details[v] || []).map(([t, url]) =>
    `<a href="${url}" target="_blank" rel="noopener"><figure><img loading="lazy" src="${url}" alt="${V_NAME[v]}、${t}"><figcaption>${V_NAME[v]}・${t}</figcaption></figure></a>`));
  $('details').innerHTML = html.join('') || '<p class="empty">寄りの画像はありません。</p>';
}

let lastV = null;
function render() {
  renderStages(); renderControls();
  if (lastV !== state.v) { renderSheet(); renderDetails(); preload(); lastV = state.v; }
  else $('sheet').querySelectorAll('.thumb').forEach(b =>
    b.setAttribute('aria-current', +b.dataset.az === state.az && +b.dataset.el === state.el));
  try { localStorage.setItem('nrsk-views', JSON.stringify(state)); } catch (e) {}
}

function preload() {
  variants().forEach(v => Object.values(DATA.views[v] || {}).forEach(u => { new Image().src = u; }));
}

function dragToTurn(el) {
  let x0 = null;
  el.addEventListener('pointerdown', e => { x0 = e.clientX; el.setPointerCapture(e.pointerId); });
  el.addEventListener('pointermove', e => {
    if (x0 === null) return;
    const dx = e.clientX - x0;
    if (Math.abs(dx) > 60) { step(dx < 0 ? 1 : -1); x0 = e.clientX; }
  });
  const end = () => { x0 = null; };
  el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
}

document.querySelectorAll('header .seg button').forEach(b => b.addEventListener('click', () => { state.v = b.dataset.v; render(); }));
document.addEventListener('keydown', e => {
  if (e.target.closest('input,textarea')) return;
  const k = {ArrowLeft: () => step(-1), ArrowRight: () => step(1), ArrowUp: () => stepElev(1), ArrowDown: () => stepElev(-1)}[e.key];
  if (k) { e.preventDefault(); k(); }
});
buildCompass(); buildElev(); render();
</script>
'''

if __name__ == '__main__':
    main()
