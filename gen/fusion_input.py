"""Write case/fusion/<side>/input.json: everything the Fusion scripts need to build and sync the 3D printed parts.

The Fusion scripts (fusion/) cannot import make_case.py (Fusion's Python has no manifold3d), so this writes out the
dimensions and the values Half derives (the screw and foot placement, the port tunnels, the OLED cover, the drum
dial's openings) as plain JSON. Fusion only draws; it recomputes nothing.

Coordinates are make_case's model frame: mm, z up, y = -(board y). Rectangles are {x0, y0, x1, y1} with x0 < x1 and
y0 < y1 in that frame; rounded ones add r. Polygons are lists of [x, y] (outer loops counter-clockwise, holes
clockwise). Every point-like item carries an id that the sync script matches its sketch entities against.

Run with the project venv:  .venv/bin/python gen/fusion_input.py [left] [right]
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_case as mc  # noqa: E402
from make_case import STAND_ANGLES, Half, stand_pose  # noqa: E402

VERSION = 1
OUT = os.path.join(mc.OUT, 'fusion')
EPS = 1e-6


def r6(v):
    return round(float(v), 6)


def pt(x, y):
    """Board point -> model frame."""
    return [r6(x), r6(-y)]


def box(x0, y0, x1, y1, r=None):
    """Board rectangle -> model frame (the y range flips)."""
    out = dict(x0=r6(x0), y0=r6(-y1), x1=r6(x1), y1=r6(-y0))
    if r is not None:
        out['r'] = r6(r)
    return out


def polys(cs):
    return [[[r6(x), r6(y)] for x, y in p] for p in cs.to_polygons()]


def cs_box(cs, r):
    """A rounded rectangle given as a CrossSection (model frame) -> {x0, y0, x1, y1, r}."""
    x0, y0, x1, y1 = map(float, cs.bounds())
    return dict(x0=r6(x0), y0=r6(y0), x1=r6(x1), y1=r6(y1), r=r6(r))


def params():
    """make_case's module constants that shape the parts: numbers and tuples of numbers."""
    out = {}
    for k, v in vars(mc).items():
        if not k.isupper() or isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            out[k] = r6(v)
        elif isinstance(v, tuple) and v and all(isinstance(e, (int, float)) for e in v):
            out[k] = [r6(e) for e in v]
    return out


def points(prefix, pts):
    return [dict(id=f'{prefix}/{i}', xy=pt(x, y)) for i, (x, y) in enumerate(pts)]


def slot(hf, s):
    z_pcb = mc.FLOOR + mc.STANDOFF
    zb, zc, h = hf.port_z(s, z_pcb)
    return dict(id=f"slot/{s['name']}", name=s['name'], edge=s['edge'], along=r6(s['along']),
                width=r6(s['conn'].get('width', mc.USB_SHELL[0]) + 2 * mc.PORT_CLR),
                z_bottom=r6(zb), z_centre=r6(zc), height=r6(h), open_top=bool(s['conn'].get('open_top')),
                chan=polys(s['chan']), cap=polys(s['cap']), full=box(*s['full']))


def build(side):
    hf = Half(side)
    d = hf.d
    x0, y0, x1, y1, r = hf.pcb
    (wx, wy), wr = hf.wheel_xy()
    out = dict(version=VERSION, side=side, inner_right=hf.inner_right, params=params(),
               port_skin=r6(d.get('port_skin', 0.8)),
               pcb=box(*hf.pcb[:4], r),
               inner=box(x0 - mc.CLEAR, y0 - mc.CLEAR, x1 + mc.CLEAR, y1 + mc.CLEAR, r + mc.CLEAR),
               outer_box=box(*hf.outer_box),
               screws=points('screw', hf.screws), pcb_holes=points('hole', d['holes']),
               keys=[dict(id=f'key/{i}', name=k['name'], xy=pt(k['cx'], k['cy']), w=r6(k['w']), h=r6(k['h']))
                     for i, k in enumerate(d['keys'])],      # names are keycap legends and repeat (Space, Ctrl)
               slots=[slot(hf, s) for s in hf.slots],
               feet=points('foot', hf.feet()),
               wheel=dict(id='wheel', xy=pt(wx, wy), r=r6(wr)))
    if 'reset' in d:
        out['reset'] = dict(id='reset', xy=pt(*d['reset']))
    wall_top = mc.FLOOR + mc.STANDOFF + mc.PCB_T + mc.PLATE_GAP
    z_l = wall_top - mc.CAP_LEDGE
    out['cap_key'] = dict(slot=polys(hf.cap_key_footprint()), lug=polys(hf.cap_key_footprint(-mc.CAP_FIT)),
                          slot_z=r6(z_l - mc.CAP_KEY[2]), lug_z=r6(z_l - mc.CAP_KEY[2] + mc.CAP_FIT), top_z=r6(z_l))
    if hf.window_box is not None:
        (cx0, cy0, cx1, cy1), corner = hf.cover_box()
        out['oled'] = dict(window=box(*hf.window_box),
                           cover=box(cx0, cy0, cx1, cy1, hf.outer_box[4] - mc.COVER_FRAME), outer_corner=corner)
    if hf.feet():
        feet = hf.feet()
        y_cut = -(feet[4][1] + mc.STAND_PAST)          # tray frame, as in Half.stand()
        out['stand'] = dict(front_y=r6(-hf.front_y()), y_cut=r6(y_cut),
                            feet=[f'foot/{i}' for i, (_, y) in enumerate(feet) if -y > y_cut],
                            poses={str(deg): [[r6(e) for e in row] for row in stand_pose(deg, hf.front_y())]
                                   for deg in STAND_ANGLES})
    if 'drum' in d:
        hx0, hx1 = hf._hood_ends()
        bx0, bx1 = hf._block_x()
        out['drum'] = dict(origin=pt(*d['drum']['origin']), width=r6(d['drum']['width']),
                           pegs=points('peg', d['drum']['pegs']),
                           opening=polys(hf.drum_opening()), bezel_outline=polys(hf.bezel_outline()),
                           plate_hole=polys(hf.bezel_outline(mc.BEZEL_FIT)), ledge=polys(hf.bezel_ledge()),
                           web_cut=polys(hf.bezel_outline(mc.BEZEL_LEDGE + 0.5)),
                           bezel_box=cs_box(hf.bezel_outline(), mc.BEZEL_R),
                           ledge_box=cs_box(hf.bezel_outline(mc.BEZEL_LEDGE), mc.BEZEL_R + mc.BEZEL_LEDGE),
                           hood_ends=[r6(hx0), r6(hx1)], block_x=[r6(bx0), r6(bx1)],
                           drum_d=r6(mc.DRUM_D), drum_gap=r6(mc.DRUM_GAP), drum_w=r6(mc.DRUM_W))
    return hf, out


def check(hf, out):
    """The JSON says what Half says: ids are unique, and the placed items match Half's own values."""
    ids = [e['id'] for k in ('screws', 'pcb_holes', 'keys', 'slots', 'feet') for e in out[k]]
    ids += [e['id'] for e in out.get('drum', {}).get('pegs', [])]
    assert len(ids) == len(set(ids)), f'{hf.side}: duplicate ids'

    def same(a, b):
        return all(abs(p - q) < 1e-5 for p, q in zip(a, b))
    for e, (x, y) in zip(out['screws'], hf.screws):
        assert same(e['xy'], (x, -y)), e
    assert len(out['screws']) == len(hf.screws) and len(out['feet']) == len(hf.feet())
    assert len(out['keys']) == len(hf.d['keys']) and len(out['pcb_holes']) == len(hf.d['holes'])
    for e, (x, y) in zip(out['feet'], hf.feet()):
        assert same(e['xy'], (x, -y)), e
    ob = out['outer_box']
    bx0, by0, bx1, by1 = map(float, hf.outer.bounds())
    assert same((ob['x0'], ob['y0'], ob['x1'], ob['y1']), (bx0, by0, bx1, by1)), (ob, hf.outer.bounds())
    for s, e in zip(hf.slots, out['slots']):
        area = sum(abs(poly_area(p)) * (1 if poly_area(p) > 0 else -1) for p in e['chan'])
        assert abs(area - s['chan'].area()) < 1e-3, e['id']
    if 'oled' in out:
        c = out['oled']['cover']
        # rectangle with four corners of radius r
        area = (c['x1'] - c['x0']) * (c['y1'] - c['y0']) - (4 - math.pi) * c['r'] ** 2
        assert abs(area - hf.cover_shape().area()) / area < 2e-3, (area, hf.cover_shape().area())
    for p in out['params'].values():
        assert all(math.isfinite(v) for v in (p if isinstance(p, list) else [p]))
    json.loads(json.dumps(out))


def poly_area(p):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(p, p[1:] + p[:1])) / 2


def main(sides):
    for side in sides:
        hf, out = build(side)
        check(hf, out)
        os.makedirs(os.path.join(OUT, side), exist_ok=True)
        path = os.path.join(OUT, side, 'input.json')
        with open(path, 'w') as f:
            json.dump(out, f, indent=1)
            f.write('\n')
        print(f"{side}: {os.path.relpath(path, mc.ROOT)}  screws {len(out['screws'])}, holes {len(out['pcb_holes'])}, "
              f"keys {len(out['keys'])}, slots {len(out['slots'])}, feet {len(out['feet'])}, "
              f"params {len(out['params'])}{', drum' if 'drum' in out else ''}")


if __name__ == '__main__':
    main(sys.argv[1:] or ['left', 'right'])
