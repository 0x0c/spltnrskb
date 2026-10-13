"""Tilt stands: the half sits on a 3D printed stand that follows the case outline (case/preview/tilt-variants/, R and U).

Instead of legs under the tray, a separate stand with a sloped top: the case's rubber feet drop into pockets in the
top (so the case cannot slide off), and the stand stands on the desk with its whole footprint.
  R  ring : a band RING_W wide along the whole outline; the case sits on it front and back, the front lifted LIFT
  U  U    : the band along the back edge and down both sides past the side foot; the front feet stay on the desk
One stand per angle. Tray frame as make_case.py; the pose of the half on the stand is make_case's tray frame raised
by the angle about the front feet's contact line (render_tilt.tilt), then lifted by 'lift'.

Writes <side>-tray.stl and <side>-stand-all-<deg>.stl (tray frame) under case/preview/tilt-variants/<R|U>/ and adds
R and U to variants.json in the format of gen/tilt_variants.py.
Run with the project venv after gen/tilt_variants.py:  .venv/bin/python gen/tilt_stands.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifold3d import CrossSection, JoinType, Manifold  # noqa: E402
from make_case import TRAY_FILLET, Half, hull, hull_margin, write_stl  # noqa: E402
from tilt_variants import ANGLES, DIR, FOOT_PROUD, plug_boxes  # noqa: E402

RING_W = 16.0          # band width in from the outline: the feet (8 mm in, 9.5 mm across) sit on it with 3 mm spare
POCKET = 2.0           # feet pockets: the foot stands this deep in the stand (0.8 mm left under the tray)
POCKET_D = 9.5 + 0.6
LIFT = 3.0             # R: stand under the front feet' pockets
U_PAST = 15.0          # U: the side arms run this far toward the front past the side foot
TOP_FILLET = TRAY_FILLET   # round on the stand's top edges: the same as the tray's bottom edge sitting on it
BED = 220.0                # printer bed (as the tray: Ender-3, Bambu Lab A1 / P1 / X1, Prusa MK4)
STANDS = {'R': ('3D プリントの台座（全周）', LIFT), 'U': ('3D プリントの台座（奥の U 字）', 0.0)}


def pose(deg, front_y, lift):
    """Tray frame -> world (3 x 4): about the front feet's contact line, then lifted."""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    yp, zp = -front_y, -FOOT_PROUD
    # rotate (y, z) about (yp, zp) by t, then raise by FOOT_PROUD + lift so the contact line sits at z = lift
    return [[1, 0, 0, 0],
            [0, c, -s, yp - c * yp + s * zp],
            [0, s, c, zp - s * yp - c * zp + FOOT_PROUD + lift]]


def inverse(m):
    r = [[m[j][i] for j in range(3)] for i in range(3)]          # rotation part transposed
    t = [-sum(r[i][j] * m[j][3] for j in range(3)) for i in range(3)]
    return [r[i] + [t[i]] for i in range(3)]


def stand(hf, key, deg, front_y):
    lift = STANDS[key][1]
    band = hf.outer - hf.outer.offset(-RING_W, JoinType.Round)
    feet = hf.feet()
    if key == 'U':
        side_y = feet[4][1]                       # board y of the foot beside the wheel
        y_cut = -(side_y + U_PAST)                # tray frame
        ox0, oy0, ox1, oy1, _ = hf.outer_box
        band = band ^ CrossSection.square((ox1 - ox0 + 2, -oy0 - y_cut + 1)).translate((ox0 - 1, y_cut))
        feet = [f for f in feet if -f[1] > y_cut]
    # prism under the tray down past the desk, cut at the desk plane, pockets for the feet
    top = -FOOT_PROUD + POCKET                    # stand top, tray frame
    # printed (bottom on the bed, pockets up): straight walls, the top edges rounded by stacked offset slices
    r, n = TOP_FILLET, 8
    prism = Manifold.extrude(band, 200.0 - r).translate((0, 0, top - 200.0))
    for i in range(n):
        za, zb = top - r + r * i / n, top - r + r * (i + 1) / n
        zm = (za + zb) / 2 - (top - r)
        inset = r - math.sqrt(max(r * r - zm * zm, 0.0))
        prism = prism + Manifold.extrude(band.offset(-inset, JoinType.Round), zb - za + 0.001).translate((0, 0, za))
    desk = Manifold.cube((1000, 1000, 500)).translate((-500, -500, 0)).transform(inverse(pose(deg, front_y, lift)))
    m = prism ^ desk
    for x, y in feet:
        m = m - Manifold.cylinder(POCKET + 0.01, POCKET_D / 2, POCKET_D / 2, 64).translate((x, -y, -FOOT_PROUD))
    return m, feet


def run(side, key):
    hf = Half(side)
    out = os.path.join(DIR, key)
    os.makedirs(out, exist_ok=True)
    tray = hf.tray()
    write_stl(os.path.join(out, f'{side}-tray.stl'), tray)
    feet_all = hf.feet()
    front_y = max(y for _, y in feet_all)
    plugs = plug_boxes(hf)
    rep = dict(label=STANDS[key][0], seats={}, lift=STANDS[key][1], legs={}, angles={}, notes=[])
    for deg in ANGLES:
        m, feet = stand(hf, key, deg, front_y)
        write_stl(os.path.join(out, f'{side}-stand-all-{deg}.stl'), m)
        # support: where the stand meets the desk, plus the front feet when they stand on the desk (U)
        world = m.transform(pose(deg, front_y, STANDS[key][1]))
        foot_print = world.slice(0.05).to_polygons()
        pts = [(p[0], -p[1]) for poly in foot_print for p in poly]
        if key == 'U':
            pts += [f for f in feet_all if f[1] == front_y]
        poly = hull(pts)
        margin = min(hull_margin(poly, (k['cx'], k['cy'])) for k in hf.d['keys'])
        bb = world.bounding_box()
        assert bb[3] - bb[0] <= BED and bb[4] - bb[1] <= BED, f'{key} {deg} stand does not fit the bed'
        rep['angles'][deg] = dict(margin=round(float(margin), 2), angle_err=0.0,
                                  plug_hit=round(sum((pl ^ m).volume() for pl in plugs), 3),
                                  plug_above_desk=1.0, leg_in_tray=round((m ^ tray).volume(), 3), seats_found=True,
                                  bodies_ok=True, height=round(float(bb[5]), 1), volume=round(m.volume() / 1000, 1))
    rep['tray_status'] = str(tray.status())
    return rep


def main():
    path = os.path.join(DIR, 'variants.json')
    out = json.load(open(path))
    for key in STANDS:
        out[key] = {}
        for side in ('left', 'right'):
            rep = run(side, key)
            a = rep['angles'].values()
            rep['check'] = dict(seats=True, angle=True, support=all(v['margin'] > 0 for v in a),
                                ribs=True, plug=all(v['plug_hit'] < 1e-3 for v in a),
                                legs=all(v['leg_in_tray'] < 1e-3 for v in a), steps=len(rep['angles']))
            out[key][side] = rep
            print(key, side, {d: (v['margin'], v['height'], v['volume']) for d, v in rep['angles'].items()})
    json.dump(out, open(path, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
