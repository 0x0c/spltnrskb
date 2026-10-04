"""OLED height study (case/preview/oled-variants/).

Display height h = glass/lens top above the switch-plate top.
  h = 0   : flush. Module stays at its PCB position, a 1 mm clear lens drops into the plate window.
  h > 0   : the module sits on a pod. The key-free notch is fully surrounded by keycaps that travel
            down to plate + 1.6 mm, so a pod cannot stand there; it is moved outward over the case
            wall instead (module wired to the PCB header), clear of every keycap and inside the
            case outline.

Writes <side>-pod-<h>.stl, <side>-lens-<h>.stl and variants.json (module rectangles).
Run with the project venv:  .venv/bin/python gen/oled_variants.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifold3d import CrossSection, JoinType, Manifold  # noqa: E402
from make_case import Half, OUT, rect, write_stl  # noqa: E402

HEIGHTS = [0.0, 3.5, 6.5, 13.0]
KEYCAP_CLEAR = 0.6        # pod wall to keycap skirt
LENS_T = 1.0
POD_WALL = 1.6            # pod rim around the module
MODULE = (12.0, 38.0)     # vertical 0.91" module (w, h)
# module centre for the raised variants (board-local mm), chosen clear of keycaps, over the wall
RAISED_CENTRE = {'left': (160.6, 53.5), 'right': (-0.2, 15.7)}

# tilted variants: module lies on a plane facing the typist, rising toward the back of the board.
#   cx     : module centre x (board-local)      yf : board y of the module's front edge
#   w, L   : module size across / along the slope   deg : tilt   zf : lens top at the front edge
TILTED = {
    'tilt-v': dict(w=12.0, L=38.0, deg=17.0, zf=1.5, cx={'left': 160.9, 'right': -0.6}, yf={'left': 37.0, 'right': 33.0}),
    'tilt-h': dict(w=38.0, L=12.0, deg=50.0, zf=4.0, cx={'left': 128.0, 'right': 33.0}, yf={'left': -1.7, 'right': -1.7}),
}


def tilted(hf, side, t):
    """Wedge pod + lens for a tilted module. Returns (pod, lens, frame) with frame for the renderer."""
    th = math.radians(t['deg'])
    w, L, cx, yf, zf = t['w'], t['L'], t['cx'][side], t['yf'][side], t['zf']
    depth = L * math.cos(th)
    foot = rect(cx - w / 2 - POD_WALL, yf - depth - POD_WALL, cx + w / 2 + POD_WALL, yf + POD_WALL)
    foot = foot.offset(-1.0, JoinType.Round).offset(1.0, JoinType.Round)
    assert (foot ^ keycaps(hf)).area() < 0.01, f'{side}: tilted pod hits a keycap'
    assert (foot - hf.outer).area() < 0.01, f'{side}: tilted pod sticks out of the case'
    tall = Manifold.extrude(foot, zf + L * math.sin(th) + 5)
    # keep everything below the slanted top plane through (front edge, zf)
    n = (0.0, math.tan(th), -1.0)
    norm = math.hypot(n[1], n[2])
    wyf = -yf
    pod = tall.trim_by_plane((0, n[1] / norm, n[2] / norm), (math.tan(th) * wyf - zf) / norm)

    def slab(ww, ll, d, top=0.0):
        # box in the tilted frame: x across, y' up the slope from the front edge, top face at z' = top
        b = Manifold.cube((ww, ll, d)).translate((-ww / 2, 0, top - d)).rotate((t['deg'], 0, 0))
        return b.translate((cx, wyf, zf))
    pod = pod - slab(w + 0.6, L + 0.6, 4.0).translate((0, -0.3 * math.cos(th), 0))
    lens = slab(w + 0.5, L + 0.5, LENS_T).translate((0, -0.25 * math.cos(th), 0))
    return pod, lens, dict(cx=cx, yf=yf, zf=zf, deg=t['deg'], w=w, L=L)


def keycaps(hf):
    cs = CrossSection()
    for k in hf.d['keys']:
        hw = k['w'] * 19.05 / 2 - 0.6 + KEYCAP_CLEAR
        hh = k['h'] * 19.05 / 2 - 0.6 + KEYCAP_CLEAR
        cs = cs + rect(k['cx'] - hw, k['cy'] - hh, k['cx'] + hw, k['cy'] + hh)
    return cs


def main():
    out = os.path.join(OUT, 'preview', 'oled-variants')
    os.makedirs(out, exist_ok=True)
    info = {'heights': HEIGHTS, 'lens_t': LENS_T}
    for side in ('left', 'right'):
        hf = Half(side)
        cx, cy = RAISED_CENTRE[side]
        mw, mh = MODULE
        module = (cx - mw / 2, cy - mh / 2, cx + mw / 2, cy + mh / 2)
        win = rect(module[0] + 0.3, module[1] + 0.3, module[2] - 0.3, module[3] - 0.3)
        foot = rect(module[0] - POD_WALL, module[1] - POD_WALL, module[2] + POD_WALL, module[3] + POD_WALL)
        foot = foot.offset(-1.0, JoinType.Round).offset(1.0, JoinType.Round)
        assert (foot ^ keycaps(hf)).area() < 0.01, f'{side}: pod hits a keycap'
        assert (foot - hf.outer).area() < 0.01, f'{side}: pod sticks out of the case'
        for h in HEIGHTS:
            tag = f'{h:g}'
            if h > 0:
                write_stl(os.path.join(out, f'{side}-pod-{tag}.stl'), Manifold.extrude(foot - win, h))
                lens = Manifold.extrude(win, LENS_T).translate((0, 0, h - LENS_T))
            else:   # flush: lens dropped into the plate window, top level with the plate
                lens = Manifold.extrude(hf.window_cs().offset(-0.1), LENS_T).translate((0, 0, -LENS_T))
            write_stl(os.path.join(out, f'{side}-lens-{tag}.stl'), lens)
        info[side] = dict(raised_module=module, flush_module=hf.d['oled']['box'], tilted={})
        for name, t in TILTED.items():
            pod, lens, frame = tilted(hf, side, t)
            write_stl(os.path.join(out, f'{side}-pod-{name}.stl'), pod)
            write_stl(os.path.join(out, f'{side}-lens-{name}.stl'), lens)
            info[side]['tilted'][name] = frame
    json.dump(info, open(os.path.join(out, 'variants.json'), 'w'), indent=1)
    print('wrote', out)


if __name__ == '__main__':
    main()
