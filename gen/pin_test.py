"""Test prints for the shape of the pin that drives an encoder's rotor (case/print/pin-test-*.stl).

A pin made to slide into the rotor's hex hole (EC05E1220401: 1.72 A/F; EC10E1220505: 1.73 A/F) spins in it when
the printer rounds its corners. These strips carry pins that are pressed in instead, in four shapes, each in
several sizes, to find on the user's own printer the one that holds the rotor and still goes in:

  1x  straight   hex prism, across flats from the sliding size up to well over the hole
  2x  tapered    hex that grows from the tip to the rotor's face: wedges at some depth
  3x  lobed      hex with clearance on its flats and corners that stand proud: only the corners press
  4x  round      cylinder over the hole's across-flats: presses on the six flats' middles

Every pin stands as the wheel's does (NrskEditPinRecess): in a pocket POCKET_DEPTH deep with a fillet at its
root, HUB_CLEAR + PIN_ENGAGE above the strip's top, the tip's edges chamfered. The raised number under each pin
is its id (docs/thumbwheel-check.md has the table); the strips print pins up, like the wheel.

Run with the project venv:  .venv/bin/python gen/pin_test.py
"""
import math
import os
import sys

from manifold3d import CrossSection, JoinType, Manifold

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_case import ENC_HEX_AF, HUB_CLEAR, OUT, PIN_ENGAGE, write_stl  # noqa: E402
from pin_coupon import LABEL_T, label  # noqa: E402

PIN_TIP = 0.2                 # chamfer on the tip's edges
POCKET_DEPTH, POCKET_D, ROOT_R = 0.5, 4.0, 0.7     # = NrskEditPinRecess.WHEEL
PITCH = 11.0                  # pin to pin: either encoder's body fits between neighbours
BASE_T = 2.5
BASE_W = 16.0
PIN_Y = 4.0                   # pin row above the strip's centre line; labels below
FLAT_AF = 1.66                # lobed pins: across flats (clear of the hole)

# id -> parameters, per shape
STRAIGHT = {11: 1.66, 12: 1.70, 13: 1.74, 14: 1.78, 15: 1.82, 16: 1.86, 17: 1.90}          # across flats
TAPERED = {21: (1.60, 1.76), 22: (1.64, 1.80), 23: (1.68, 1.84), 24: (1.72, 1.88),         # A/F at the tip,
           25: (1.60, 1.90), 26: (1.66, 1.96)}                                             # at the rotor's face
LOBED = {31: 0.98, 32: 1.00, 33: 1.02, 34: 1.04, 35: 1.06, 36: 1.08}                       # corner radius
ROUND = {41: 1.74, 42: 1.78, 43: 1.82, 44: 1.86, 45: 1.90, 46: 1.94}                       # diameter
FAMILIES = (('straight', STRAIGHT), ('tapered', TAPERED), ('lobed', LOBED), ('round', ROUND))


def hexagon(af):
    return CrossSection.circle(af / math.sqrt(3), 6)


def lobed(corner):
    """Twelve corners: the hexagon's own at radius `corner`, and the middles of its flats at FLAT_AF / 2."""
    pts = []
    for i in range(6):
        a = math.radians(60 * i)
        pts.append((corner * math.cos(a), corner * math.sin(a)))
        a += math.radians(30)
        pts.append((FLAT_AF / 2 * math.cos(a), FLAT_AF / 2 * math.sin(a)))
    return CrossSection([pts])


def section(kind, v):
    """The pin's section where it sits in the rotor (for the tapered pins: at the rotor's face)."""
    if kind == 'straight':
        return hexagon(v)
    if kind == 'tapered':
        return hexagon(v[1])
    if kind == 'lobed':
        return lobed(v)
    return CrossSection.circle(v / 2)


def pin(kind, v):
    """One pin, z = 0 at the pocket's floor: root fillet, a straight part up to the rotor's face, the part in the
    rotor (tapered or not) and the chamfered tip."""
    cs = section(kind, v)
    face = POCKET_DEPTH + HUB_CLEAR               # rotor's face above the pocket's floor
    body = PIN_ENGAGE - PIN_TIP                   # in the rotor, below the tip's chamfer
    size = v[1] if kind == 'tapered' else v if kind != 'lobed' else FLAT_AF      # across the section
    m = Manifold.extrude(cs, face)
    if kind == 'tapered':
        tip_af = v[0]
        s = tip_af / v[1]
        s_body = 1 + (s - 1) * body / PIN_ENGAGE  # the taper runs on through the chamfer's height
        m = m + Manifold.extrude(cs, body, scale_top=(s_body, s_body)).translate((0, 0, face))
        top, size = cs.scale((s_body, s_body)), v[1] * s_body
    else:
        m = m + Manifold.extrude(cs, body).translate((0, 0, face))
        top = cs
    s = (size / 2 - PIN_TIP) / (size / 2)
    m = m + Manifold.extrude(top, PIN_TIP, scale_top=(s, s)).translate((0, 0, face + body))
    steps = 14                                    # the root fillet, as a stack of widened sections
    for i in range(steps):
        z0, z1 = ROOT_R * i / steps, ROOT_R * (i + 1) / steps
        d = ROOT_R - math.sqrt(ROOT_R ** 2 - (ROOT_R - z0) ** 2)
        if d > 1e-4:
            m = m + Manifold.extrude(cs.offset(d, JoinType.Round), z1 - z0).translate((0, 0, z0))
    return m


def strip(kind, pins):
    length = len(pins) * PITCH
    out = Manifold.extrude(CrossSection.square((length, BASE_W)).translate((0, -BASE_W / 2)), BASE_T)
    labels = CrossSection()
    for i, (ident, v) in enumerate(sorted(pins.items())):
        cx = PITCH * (i + 0.5)
        out = out - Manifold.cylinder(POCKET_DEPTH + 0.01, POCKET_D / 2, POCKET_D / 2, 64).translate(
            (cx, PIN_Y, BASE_T - POCKET_DEPTH))
        out = out + pin(kind, v).translate((cx, PIN_Y, BASE_T - POCKET_DEPTH))
        labels = labels + label(f'{ident:02d}', cx, -BASE_W / 2 + 1.2)
    return out + Manifold.extrude(labels, LABEL_T).translate((0, 0, BASE_T))


def main():
    os.makedirs(os.path.join(OUT, 'print'), exist_ok=True)
    every = Manifold()
    for row, (kind, pins) in enumerate(FAMILIES):
        m = strip(kind, pins)
        path = os.path.join(OUT, 'print', f'pin-test-{kind}.stl')
        write_stl(path, m)
        b = m.bounding_box()
        print(f'{os.path.relpath(path)}: ids {min(pins)}..{max(pins)}, '
              f'{b[3] - b[0]:.1f} x {b[4] - b[1]:.1f} x {b[5] - b[2]:.1f} mm, {m.status()}')
        every = every + m.translate((0, -row * (BASE_W + 2.0), 0))
    # one plate with the four strips, joined by a thin web so they print as one part
    b = every.bounding_box()
    web = Manifold.cube((10.0, b[4] - b[1], 1.0)).translate((b[0], b[1], 0))
    path = os.path.join(OUT, 'print', 'pin-test-all.stl')
    write_stl(path, every + web)
    b = (every + web).bounding_box()
    print(f'{os.path.relpath(path)}: {b[3] - b[0]:.1f} x {b[4] - b[1]:.1f} x {b[5] - b[2]:.1f} mm; '
          f'hole {ENC_HEX_AF} A/F, pins {POCKET_DEPTH + HUB_CLEAR + PIN_ENGAGE} above the pocket floor')


if __name__ == '__main__':
    main()
