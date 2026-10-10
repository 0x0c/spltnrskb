"""Test coupon for the thumbwheel's hex pin (case/print/pin-coupon.stl).

A strip with hex pins of several across-flats sizes around PIN_AF, each the same height and chamfer as the pin on
the wheel and printed the same way up (pins on top). Push the encoder (EC05E1220401, 1.72 A/F hex hole) onto each
pin from the wheel side and pick the largest one that slides in without force; set PIN_AF in make_case.py to it.
The raised two-digit label under each pin is the size in hundredths of a mm (66 = 1.66 mm).

Run with the project venv:  .venv/bin/python gen/pin_coupon.py
"""
import math
import os
import sys

from manifold3d import CrossSection, Manifold

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_case import HUB_CLEAR, OUT, PIN_AF, PIN_CHAMFER, PIN_ENGAGE, hexagon, write_stl  # noqa: E402

STEP = 0.02
SIZES = [round(PIN_AF + STEP * i, 2) for i in range(-3, 4)]   # 1.60 ... 1.72 around PIN_AF = 1.66
PITCH = 9.0                  # pin to pin: the encoder body (7.6 over the tabs) fits between neighbours
BASE_T = 2.0
BASE_W = 16.0
PIN_Y = 4.0                  # pin row above the strip's centre line; labels below
LABEL_H, LABEL_W, STROKE, LABEL_T = 4.0, 2.2, 0.6, 0.4

# seven-segment digits: segment -> (x0, y0, x1, y1) in a 1 x 2 box, y up
SEG = {'a': (0, 2, 1, 2), 'b': (1, 1, 1, 2), 'c': (1, 0, 1, 1), 'd': (0, 0, 1, 0),
       'e': (0, 0, 0, 1), 'f': (0, 1, 0, 2), 'g': (0, 1, 1, 1)}
DIGITS = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc',
          '7': 'abc', '8': 'abcdefg', '9': 'abcdfg'}


def digit(ch, x, y):
    """Seven-segment digit, lower-left corner at (x, y), LABEL_W x LABEL_H."""
    sx, sy, h = LABEL_W - STROKE, (LABEL_H - STROKE) / 2, STROKE / 2
    out = CrossSection()
    for s in DIGITS[ch]:
        x0, y0, x1, y1 = SEG[s]
        out = out + CrossSection.square((x1 * sx - x0 * sx + STROKE, y1 * sy - y0 * sy + STROKE)).translate(
            (x + x0 * sx, y + y0 * sy))
    return out


def label(text, cx, y):
    gap = 0.6
    w = len(text) * LABEL_W + (len(text) - 1) * gap
    out = CrossSection()
    for i, ch in enumerate(text):
        out = out + digit(ch, cx - w / 2 + i * (LABEL_W + gap), y)
    return out


def pin(af):
    """Same as the pin in Half.wheel3d: PIN_ENGAGE + HUB_CLEAR tall, tip chamfered by PIN_CHAMFER."""
    h = PIN_ENGAGE + HUB_CLEAR
    return hexagon(af, h) ^ Manifold.cylinder(h, af / math.sqrt(3), af / 2 - PIN_CHAMFER, 24)


def coupon():
    length = len(SIZES) * PITCH
    out = Manifold.extrude(CrossSection.square((length, BASE_W)).translate((0, -BASE_W / 2)), BASE_T)
    labels = CrossSection()
    for i, af in enumerate(SIZES):
        cx = PITCH * (i + 0.5)
        out = out + pin(af).translate((cx, PIN_Y, BASE_T))
        labels = labels + label(f'{round(af * 100) % 100:02d}', cx, -BASE_W / 2 + 1.2)
    return out + Manifold.extrude(labels, LABEL_T).translate((0, 0, BASE_T))


def main():
    os.makedirs(os.path.join(OUT, 'print'), exist_ok=True)
    m = coupon()
    path = os.path.join(OUT, 'print', 'pin-coupon.stl')
    write_stl(path, m)
    lo, hi = m.bounding_box()[:3], m.bounding_box()[3:]
    print(f'{os.path.relpath(path)}: pins ' + ', '.join(f'{a:.2f}' for a in SIZES)
          + f' mm A/F; {hi[0] - lo[0]:.1f} x {hi[1] - lo[1]:.1f} x {hi[2] - lo[2]:.1f} mm')


if __name__ == '__main__':
    main()
