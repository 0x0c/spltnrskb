"""Test coupon for the rubber-foot recesses (case/print/foot-coupon.stl, docs/specs/case-feet-tilt.md).

Two strips side by side, each printed the same way up as the part it stands for:
  tray  : FOOT_BASE thick like the tray floor, recesses FOOT_DEPTH deep opening on the bed side (as under the tray),
          diameters FOOT_D - 0.2, FOOT_D, FOOT_D + 0.2
  stand : as thick as the stand under its pockets, pockets STAND_POCKET deep opening on top (as on the tilt stand),
          diameters STAND_POCKET[0] - 0.2 ... + 0.2
Press a 3M CS-02 foot (9.5 mm) into each and pick, for the tray, the smallest recess it drops into without force, and
for the stand, the smallest pocket it sits in loosely; set FOOT_D and STAND_POCKET in make_case.py to them. The raised
label next to each is the diameter in tenths of a mm (101 = 10.1 mm).

Run with the project venv:  .venv/bin/python gen/foot_coupon.py
"""
import os
import sys

from manifold3d import CrossSection, Manifold

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_case import FLOOR, FOOT_D, FOOT_DEPTH, OUT, STAND_FLOOR, STAND_POCKET, write_stl  # noqa: E402
from pin_coupon import LABEL_H, LABEL_T, label  # noqa: E402

STEP = 0.2
PITCH = 14.0                 # recess to recess
STRIP_W = 20.0               # recess row above the strip's centre line, labels below
HOLE_Y = 3.0
GAP = 2.0                    # between the two strips


def sizes(d):
    return [round(d + STEP * i, 1) for i in (-1, 0, 1)]


def strip(diams, thick, depth, from_top):
    length = len(diams) * PITCH
    m = Manifold.extrude(CrossSection.square((length, STRIP_W)).translate((0, -STRIP_W / 2)), thick)
    labels = CrossSection()
    for i, d in enumerate(diams):
        cx = PITCH * (i + 0.5)
        z = thick - depth if from_top else -0.01
        m = m - Manifold.cylinder(depth + 0.01, d / 2, d / 2, 96).translate((cx, HOLE_Y, z))
        labels = labels + label(f'{round(d * 10)}', cx, -STRIP_W / 2 + 1.2)
    return m + Manifold.extrude(labels, LABEL_T).translate((0, 0, thick))


def coupon():
    tray = strip(sizes(FOOT_D), FLOOR, FOOT_DEPTH, from_top=False)
    stand = strip(sizes(STAND_POCKET[0]), STAND_FLOOR + STAND_POCKET[1], STAND_POCKET[1], from_top=True)
    return tray + stand.translate((0, STRIP_W + GAP, 0))


def main():
    os.makedirs(os.path.join(OUT, 'print'), exist_ok=True)
    m = coupon()
    path = os.path.join(OUT, 'print', 'foot-coupon.stl')
    write_stl(path, m)
    b = m.bounding_box()
    assert LABEL_H + 1.2 < STRIP_W / 2 + HOLE_Y - max(sizes(STAND_POCKET[0])) / 2, 'labels run into the recesses'
    print(f'{os.path.relpath(path)}: tray recesses ' + ', '.join(f'{d:.1f}' for d in sizes(FOOT_D))
          + ' mm, stand pockets ' + ', '.join(f'{d:.1f}' for d in sizes(STAND_POCKET[0]))
          + f' mm; {b[3] - b[0]:.1f} x {b[4] - b[1]:.1f} x {b[5] - b[2]:.1f} mm')


if __name__ == '__main__':
    main()
