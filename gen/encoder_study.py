"""Study: corner thumbwheel read by an Alps EC05E1220401 instead of AS5600 + magnet + ball plunger.

Builds the parts of both designs around each wheel (3D-print variant) without touching the main design:
  case/preview/encoder-study/<side>-<design>-<part>.stl      design = current | encoder
  case/preview/encoder-study/<side>-<design>-<part>-cut.stl  the same, cut through the wheel axis (section shot)
  case/preview/encoder-study/parts.json                      part -> material, plus the exploded-view offsets
Rendered by gen/render_encoder_study.py. See docs/specs/thumbwheel-encoder.md.

Run with the project venv:  .venv/bin/python gen/encoder_study.py
"""
import json
import math
import os

from manifold3d import CrossSection, Manifold

import make_case as mc
from make_case import (BORE_D, BORE_DEPTH, FLOOR, MAGNET_D, MAGNET_DEPTH, PCB_T, STANDOFF, TOOTH_DEPTH, WHEEL_GAP,
                       WHEEL_T, Half, write_stl)

OUT = os.path.join(mc.OUT, 'preview', 'encoder-study')

# Alps EC05E1220401 (catalog drawing No.3): body 5.7 wide (7.6 over the side tabs), 2.5 above / 3.7 below the
# rotor axis, 2.7 above the mounting surface; hollow rotor with a hex hole of 1.72-1.73 across flats, 2.7 deep,
# entered from the face away from the board (A face). The board needs a 3 mm square hole under the rotor.
ENC_W, ENC_TAB_W, ENC_UP, ENC_DOWN, ENC_H = 5.7, 7.6, 2.5, 3.7, 2.7
ENC_HEX_AF, ENC_ROTOR_D = 1.72, 2.2
ENC_PCB_HOLE = 3.0
# proposed wheel: the hub under the encoder is lowered so the body clears it, and a hex pin drives the rotor
HUB_R = 6.0                  # recess radius: covers the body, the side tabs and the terminals
HUB_CLEAR = 0.3              # encoder body to the recessed hub
PIN_AF = 1.66                # hex pin across flats (rotor hole 1.72): tune on a test print
PIN_ENGAGE = 2.0             # pin length inside the rotor
POST_D_NEW = 3.6             # floor post: 0.2 mm radial play in the 4.0 bore takes up board-to-tray misalignment
KNURLS = 32                  # rim teeth stay as the grip; the clicks now come from the encoder (12 per turn)


def hexagon(af, h):
    r = af / math.sqrt(3)
    return Manifold.extrude(CrossSection([[(r * math.cos(math.radians(60 * i)), r * math.sin(math.radians(60 * i)))
                                            for i in range(6)]]), h)


def wheel(hf, encoder):
    (x, y), r = hf.wheel_xy()
    pts = []
    n = KNURLS * 12
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r - TOOTH_DEPTH * (1 - math.cos(KNURLS * a)) / 2
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    w = Manifold.extrude(mc.cs_poly(pts), WHEEL_T)
    w = w - Manifold.cylinder(BORE_DEPTH, BORE_D / 2, BORE_D / 2, 48).translate((x, -y, 0))
    if not encoder:
        return w - Manifold.cylinder(MAGNET_DEPTH + 0.01, MAGNET_D / 2, MAGNET_D / 2, 48).translate(
            (x, -y, WHEEL_T - MAGNET_DEPTH))
    hub_top = hub_top_z() - (FLOOR + WHEEL_GAP)
    w = w - Manifold.cylinder(WHEEL_T, HUB_R, HUB_R, 96).translate((x, -y, hub_top))
    pin_len = enc_bottom_z() + PIN_ENGAGE - hub_top_z()
    pin = hexagon(PIN_AF, pin_len) ^ Manifold.cylinder(pin_len, PIN_AF / 2 / math.cos(math.radians(30)),
                                                       PIN_AF / 2 - 0.25, 24)   # chamfered tip
    return w + pin.translate((x, -y, hub_top))


def enc_bottom_z():
    return FLOOR + STANDOFF - ENC_H


def hub_top_z():
    return enc_bottom_z() - HUB_CLEAR


def encoder_body(hf):
    """EC05E1220401 hanging from the PCB back, rotor on the wheel axis, terminals toward the board's front."""
    (x, y), _ = hf.wheel_xy()
    # local frame: rotor at the origin, +v toward the terminals (board front = 3D -y)
    body = CrossSection.circle(ENC_W / 2) ^ CrossSection.square((ENC_W, ENC_UP * 2), center=True)
    body = body + CrossSection.square((ENC_W, ENC_DOWN)).translate((-ENC_W / 2, -ENC_DOWN))
    m = Manifold.extrude(body, ENC_H - 0.15).translate((0, 0, 0.15))
    for sx in (-1, 1):   # metal side tabs, soldered to the big lands
        tab = Manifold.cube(((ENC_TAB_W - ENC_W) / 2, 1.6, ENC_H - 0.6)).translate(
            (ENC_W / 2 if sx > 0 else -ENC_TAB_W / 2, -0.8, 0.6))
        m = m + tab
    rotor = Manifold.cylinder(ENC_H, ENC_ROTOR_D / 2 + 0.25, ENC_ROTOR_D / 2 + 0.25, 48)
    m = m + rotor - hexagon(ENC_HEX_AF, ENC_H + 0.2).translate((0, 0, -0.1))
    for i in (-1, 0, 1):  # A, C, B terminals
        m = m + Manifold.cube((0.5, 0.9, 0.2)).translate((i * 1.5 - 0.25, -ENC_DOWN - 0.9, ENC_H - 0.2))
    # local z = 0 is the A face (toward the wheel); the mounting surface (PCB back) is at local z = ENC_H
    return m.translate((x, -y, enc_bottom_z()))


def as5600(hf):
    (x, y), _ = hf.wheel_xy()
    body = Manifold.cube((3.9, 4.9, 1.45)).translate((-1.95, -2.45, 0))
    for sx in (-1, 1):
        for i in range(4):
            body = body + Manifold.cube((1.0, 0.4, 0.2)).translate(
                (sx * 2.45 - 0.5, -1.905 + i * 1.27 - 0.2, 1.2))
    return body.translate((x, -y, FLOOR + STANDOFF - 1.45))


def magnet(hf):
    (x, y), _ = hf.wheel_xy()
    return Manifold.cylinder(1.5, (MAGNET_D - 0.1) / 2, (MAGNET_D - 0.1) / 2, 48).translate(
        (x, -y, FLOOR + WHEEL_GAP + WHEEL_T - MAGNET_DEPTH + 0.01))


def plunger(hf):
    block, zc = hf.detent_block(FLOOR)
    (qx, qy), (ux, uy), _ = hf._detent_frame()
    ang = math.degrees(math.atan2(uy, ux))
    body = Manifold.cylinder(6.0, 1.5, 1.5, 20).rotate((0, 90, 0)).translate((0.05, 0, zc))
    ball = Manifold.sphere(0.75, 16).translate((0.3, 0, zc))
    return (body + ball).rotate((0, 0, ang)).translate((qx, qy, 0))


def pcb(hf, encoder):
    m = hf.pcb3d()
    if encoder:
        (x, y), _ = hf.wheel_xy()
        m = m - Manifold.cube((ENC_PCB_HOLE, ENC_PCB_HOLE, PCB_T + 1), center=True).translate((x, -y, PCB_T / 2))
    return m.translate((0, 0, FLOOR + STANDOFF))


def tray(hf, encoder):
    if not encoder:
        return hf.tray()
    post_d, block = mc.POST_D, Half.detent_block
    mc.POST_D = POST_D_NEW
    Half.detent_block = lambda self, z: (Manifold(), 0.0)    # no plunger block
    try:
        return hf.tray()
    finally:
        mc.POST_D, Half.detent_block = post_d, block


def cap_and_plate(hf):
    hf.tray()                                     # builds the wheel cap
    z_plate = FLOOR + STANDOFF + PCB_T + mc.PLATE_GAP
    return hf.wheel_cap(), hf.plate3d().translate((0, 0, z_plate))


def corner_box(hf, size=60.0):
    """Region around the wheel kept for the close-up shots (the rest of the half would only hide it)."""
    (x, y), _ = hf.wheel_xy()
    return Manifold.cube((size, size, 40)).translate((x - size / 2, -y - size / 2, -1))


def cut_frame(hf):
    """Section plane through the wheel axis and the plunger axis (3D unit vectors u: toward the plunger, v: normal)."""
    _, (ux, uy), (vx, vy) = hf._detent_frame()
    return (ux, uy), (vx, vy)


def cut_box(hf):
    """Keep the half on the -v side of the section plane: the cut face (facing +v) shows the axis and the plunger."""
    (x, y), _ = hf.wheel_xy()
    (ux, uy), _ = cut_frame(hf)
    ang = math.degrees(math.atan2(uy, ux))
    return Manifold.cube((60, 30, 40)).translate((-30, -30, -1)).rotate((0, 0, ang)).translate((x, -y, 0))


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {'parts': {}, 'explode': {}, 'wheel': {}}
    for side in ('left', 'right'):
        hf = Half(side)
        (x, y), r = hf.wheel_xy()
        (ux, uy), (vx, vy) = cut_frame(hf)
        meta['wheel'][side] = dict(x=x, y=-y, r=r, z_pcb=FLOOR + STANDOFF, u=[ux, uy], v=[vx, vy])
        box, cut = corner_box(hf), cut_box(hf)
        cap, plate = cap_and_plate(hf)
        designs = {
            'current': {'tray': (tray(hf, False), 'case'), 'wheel': (wheel(hf, False), 'wheel'),
                        'pcb': (pcb(hf, False), 'pcb'), 'sensor': (as5600(hf), 'chip'),
                        'magnet': (magnet(hf), 'magnet'), 'plunger': (plunger(hf), 'metal'),
                        'cap': (cap, 'case'), 'plate': (plate, 'plate')},
            'encoder': {'tray': (tray(hf, True), 'case'), 'wheel': (wheel(hf, True), 'wheel'),
                        'pcb': (pcb(hf, True), 'pcb'), 'encoder': (encoder_body(hf), 'encoder'),
                        'cap': (cap, 'case'), 'plate': (plate, 'plate')},
        }
        for design, parts in designs.items():
            for name, (m, mat) in parts.items():
                key = f'{side}-{design}-{name}'
                write_stl(os.path.join(OUT, key + '.stl'), m ^ box)
                write_stl(os.path.join(OUT, key + '-cut.stl'), m ^ box ^ cut)
                meta['parts'][key] = mat
        # exploded view of the proposed corner: lift each part (mm)
        meta['explode'][side] = {'tray': 0.0, 'wheel': 7.0, 'encoder': 18.0, 'pcb': 28.0, 'cap': 44.0,
                                'plate': 44.0}
        # sanity: hub clears the encoder body, the pin reaches into the rotor
        assert hub_top_z() + HUB_CLEAR <= enc_bottom_z() + 1e-6
        assert (wheel(hf, True) ^ encoder_body(hf)).volume() < 0.05, 'wheel hits the encoder'
    json.dump(meta, open(os.path.join(OUT, 'parts.json'), 'w'), indent=1)
    print('wrote', OUT)
    print(f'encoder A face z={enc_bottom_z():.2f}, hub top z={hub_top_z():.2f} '
          f'(recess {FLOOR + WHEEL_GAP + WHEEL_T - hub_top_z():.2f} mm), pin engages {PIN_ENGAGE} mm')


if __name__ == '__main__':
    main()
