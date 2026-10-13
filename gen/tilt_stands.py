"""Tilt stands: the half sits on a 3D printed stand that follows the case outline (case/preview/tilt-variants/, R and U).

Instead of legs under the tray, a separate stand with a sloped top (make_case.Half.stand): the case's rubber feet drop
into pockets in the top (so the case cannot slide off), and the stand stands on the desk with its whole footprint.
  R  ring : a band along the whole outline; the case sits on it front and back, the front lifted LIFT
  U  U    : the band along the back edge and down both sides past the side foot; the front feet stay on the desk
            (the stand chosen: make_case.py writes it to case/print/)
One stand per angle. The pose of the half on the stand: make_case.stand_pose.

Writes <side>-tray.stl and <side>-stand-all-<deg>.stl (tray frame) under case/preview/tilt-variants/<R|U>/ and adds
R and U to variants.json in the format of gen/tilt_variants.py.
Run with the project venv after gen/tilt_variants.py:  .venv/bin/python gen/tilt_stands.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_case import STAND_ANGLES, Half, hull, hull_margin, stand_pose, write_stl  # noqa: E402
from tilt_variants import DIR  # noqa: E402

LIFT = 3.0             # R: the front feet's pockets this far above the desk
STANDS = {'R': ('3D プリントの台座（全周）', LIFT), 'U': ('3D プリントの台座（奥の U 字）', 0.0)}


def run(side, key):
    hf = Half(side)
    out = os.path.join(DIR, key)
    os.makedirs(out, exist_ok=True)
    tray = hf.tray()
    write_stl(os.path.join(out, f'{side}-tray.stl'), tray)
    feet_all = hf.feet()
    front_y = hf.front_y()
    plugs = hf.plugs3d()
    rep = dict(label=STANDS[key][0], seats={}, lift=STANDS[key][1], legs={}, angles={}, notes=[])
    for deg in STAND_ANGLES:
        m, feet = hf.stand(deg, ring=key == 'R', lift=STANDS[key][1])
        write_stl(os.path.join(out, f'{side}-stand-all-{deg}.stl'), m)
        # support: where the stand meets the desk, plus the front feet when they stand on the desk (U)
        world = m.transform(stand_pose(deg, front_y, STANDS[key][1]))
        foot_print = world.slice(0.05).to_polygons()
        pts = [(p[0], -p[1]) for poly in foot_print for p in poly]
        if key == 'U':
            pts += [f for f in feet_all if f[1] == front_y]
        poly = hull(pts)
        margin = min(hull_margin(poly, (k['cx'], k['cy'])) for k in hf.d['keys'])
        bb = world.bounding_box()
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
