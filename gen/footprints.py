"""Generate the project footprint library lib/nrsk.pretty."""
import os
import uuid

from layout import HERE

OUT = os.path.join(HERE, '..', 'lib', 'nrsk.pretty')
WIDTHS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25]
U = 19.05
# 3D models (fetched by gen/fetch_3d.sh into tools/, which is not committed; see README)
KISWITCH = '${KIPRJMOD}/../tools/kiswitch/library/3dmodels/3d-library.3dshapes/'
NRSK_3D = '${KIPRJMOD}/../lib/nrsk.3dshapes/'
ALPS_3D = '${KIPRJMOD}/../tools/alps/'
STD_FP = os.path.expanduser('~/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
if not os.path.isdir(STD_FP):
    STD_FP = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'


def uid():
    return str(uuid.uuid4())


def prop(name, value, at, layer, hide=False, size=1.0):
    h = ' (hide yes)' if hide else ''
    return (f'  (property "{name}" "{value}" (at {at[0]} {at[1]} 0) (layer "{layer}"){h} (uuid "{uid()}")\n'
            f'    (effects (font (size {size} {size}) (thickness 0.15))))\n')


def line(x1, y1, x2, y2, layer, w=0.12):
    return (f'  (fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) '
            f'(stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{uid()}"))\n')


def rect(x1, y1, x2, y2, layer, w=0.12):
    return (f'  (fp_rect (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) '
            f'(stroke (width {w}) (type solid)) (fill no) (layer "{layer}") (uuid "{uid()}"))\n')


def npth(x, y, d):
    return (f'  (pad "" np_thru_hole circle (at {x:.3f} {y:.3f}) (size {d} {d}) (drill {d}) '
            f'(layers "*.Cu" "*.Mask") (uuid "{uid()}"))\n')


def text(s, x, y, layer, size=1.0, mirror=False):
    j = ' (justify mirror)' if mirror else ''
    return (f'  (fp_text user "{s}" (at {x:.3f} {y:.3f} 0) (layer "{layer}") (uuid "{uid()}")\n'
            f'    (effects (font (size {size} {size}) (thickness 0.15)){j}))\n')


def model(path, offset=(0, 0, 0), rotate=(0, 0, 0)):
    xyz = lambda v: ' '.join(f'{c:g}' for c in v)
    return (f'  (model "{path}"\n    (offset (xyz {xyz(offset)}))\n    (scale (xyz 1 1 1))\n'
            f'    (rotate (xyz {xyz(rotate)}))\n  )\n')


def mx_hotswap(w):
    name = f'SW_MX_Hotswap_{w:.2f}u'
    s = (f'(footprint "{name}"\n  (version 20241229)\n  (generator "nrsk-gen")\n  (layer "F.Cu")\n'
         f'  (descr "Cherry MX compatible switch, Kailh MX hotswap socket (CPG151101S11) on back, {w:.2f}u keycap'
         f'{", PCB-mount stabilizer" if w >= 2 else ""}")\n'
         f'  (tags "MX hotswap Kailh keyboard")\n  (attr smd)\n')
    s += prop('Reference', 'REF**', (0, 8.5), 'F.SilkS', hide=True)
    s += prop('Value', name, (0, -8.5), 'F.Fab', hide=True)
    s += prop('Footprint', '', (0, 0), 'F.Fab', hide=True)
    s += prop('Datasheet', '', (0, 0), 'F.Fab', hide=True)
    s += prop('Description', '', (0, 0), 'F.Fab', hide=True)
    # switch body (14 mm square) and keycap outline
    s += rect(-7, -7, 7, 7, 'F.SilkS')
    s += rect(-7, -7, 7, 7, 'F.CrtYd', 0.05)   # = switch housing; mounting holes may sit 2.5 mm outside
    s += rect(-w * U / 2, -U / 2, w * U / 2, U / 2, 'Dwgs.User', 0.1)
    # switch holes
    s += npth(0, 0, 4.0)
    s += npth(-5.08, 0, 1.75)
    s += npth(5.08, 0, 1.75)
    s += npth(-3.81, -2.54, 3.0)
    s += npth(2.54, -5.08, 3.0)
    # Kailh socket pads (back side)
    for num, (x, y) in (('1', (5.842, -5.08)), ('2', (-7.085, -2.54))):
        s += (f'  (pad "{num}" smd roundrect (at {x} {y}) (size 2.55 2.5) (roundrect_rratio 0.1) '
              f'(layers "B.Cu" "B.Paste" "B.Mask") (uuid "{uid()}"))\n')
    s += rect(-8.6, -7.4, 7.35, -0.6, 'B.CrtYd', 0.05)
    if w >= 2:
        for sx in (-11.9, 11.9):
            s += npth(sx, -7.0, 3.05)
            s += npth(sx, 8.24, 4.0)
    # same switch / socket geometry as kiswitch's SW_Hotswap_Kailh_MX footprints, so their models fit as-is
    s += model(KISWITCH + 'SW_Hotswap_Kailh_MX.stp')
    s += model(KISWITCH + 'SW_Cherry_MX_PCB.stp')
    if w >= 2:
        s += model(KISWITCH + 'Stabilizer_Cherry_MX_2.00u.stp')
    s += ')\n'
    return name, s


# 0.91" 128x32 SSD1306 I2C module (38 x 12 mm), soldered so its glass top is 2.5 mm above the PCB
# (the flush 2 mm half-mirror cover is taped onto it).
OLED_W, OLED_H = 38.0, 12.0
OLED_PIN_FROM_EDGE = 1.6      # header row centre to the module's short edge
OLED_GLASS = (30.0, 11.5)     # glass panel, toward the end away from the header


def oled_module():
    """Origin = module centre, long axis along X, header at -X end (pins 1..4 = GND VCC SCL SDA along +Y)."""
    name = 'OLED_0.91in_128x32_I2C'
    s = (f'(footprint "{name}"\n  (version 20241229)\n  (generator "nrsk-gen")\n  (layer "F.Cu")\n'
         '  (descr "0.91 inch 128x32 OLED module (SSD1306, I2C), 38 x 12 mm, 4-pin 2.54 mm header '
         '(GND VCC SCL SDA); glass top 2.5 mm above the PCB, header spacer removed")\n'
         '  (tags "OLED SSD1306 I2C 0.91 128x32")\n  (attr through_hole)\n')
    s += prop('Reference', 'REF**', (0, -7.5), 'F.SilkS')
    s += prop('Value', name, (0, 0), 'F.Fab')
    s += prop('Footprint', '', (0, 0), 'F.Fab', hide=True)
    s += prop('Datasheet', '', (0, 0), 'F.Fab', hide=True)
    s += prop('Description', '', (0, 0), 'F.Fab', hide=True)
    hw, hh = OLED_W / 2, OLED_H / 2
    s += rect(-hw, -hh, hw, hh, 'F.SilkS')
    s += rect(-hw - 0.25, -hh - 0.25, hw + 0.25, hh + 0.25, 'F.CrtYd', 0.05)
    gx = hw - OLED_GLASS[0] / 2 - 1.0
    s += rect(gx - OLED_GLASS[0] / 2, -OLED_GLASS[1] / 2, gx + OLED_GLASS[0] / 2, OLED_GLASS[1] / 2, 'F.Fab', 0.1)
    s += text('OLED', gx, 0, 'F.Fab', 1.5)
    px = -hw + OLED_PIN_FROM_EDGE
    for i, lbl in enumerate(('GND', 'VCC', 'SCL', 'SDA')):
        y = (i - 1.5) * 2.54
        shape = 'rect' if i == 0 else 'circle'
        s += (f'  (pad "{i + 1}" thru_hole {shape} (at {px:.2f} {y:.2f}) (size 1.7 1.7) (drill 1.0) '
              f'(layers "*.Cu" "*.Mask") (uuid "{uid()}"))\n')
        s += text(lbl, px + 3.2, y, 'F.SilkS', 0.8)
    s += model(NRSK_3D + 'OLED_0.91in_128x32.wrl')
    s += ')\n'
    return name, s


# Alps EC05E1220401: 5 mm hollow-shaft encoder, vertical, 12 detents / 12 pulses (catalog drawing No.3).
# Viewed from the mounting side with the rotor axis at the origin and the terminals toward +Y.
ENC_LAND = (3.8, 0.0, 1.7, 2.6)        # side tabs: centre x (+/-), centre y, w, h (5.9 mm between them)
ENC_PIN_PITCH, ENC_PIN_Y = 2.0, 4.15   # A C B in a row, 1.5 x 1.3 lands, 2.1 mm from the holes to the land edge
ENC_PIN = (1.5, 1.3)
ENC_HOLES = (1.2, 2.7, 0.67)            # locating holes: x (+/-), y, drill (0.62 +0.1/-0)
ENC_CUT = 1.55                          # half side of the 3 mm (+0.1) square hole under the rotor
ENC_CUT_LOBE = (0.5, 1.8)               # two R0.5 lobes on the Y axis, centres 3.6 mm apart
ENC_BODY = (-2.85, -2.5, 2.85, 3.7)     # resin body (5.7 wide, 2.5 / 3.7 from the axis), 2.7 mm high


def edge_cut_outline():
    """Square hole with the two rotor lobes, as Edge.Cuts lines and arcs (a board cut-out)."""
    c, (lr, ly) = ENC_CUT, ENC_CUT_LOBE
    s = ''
    for sy in (-1, 1):
        y = sy * c
        # half outline from the left side to the right side through the lobe on this side
        s += line(-c, y, -lr, y, 'Edge.Cuts', 0.05) + line(-lr, y, -lr, sy * ly, 'Edge.Cuts', 0.05)
        s += (f'  (fp_arc (start {-lr:.3f} {sy * ly:.3f}) (mid 0 {sy * (ly + lr):.3f}) (end {lr:.3f} {sy * ly:.3f}) '
              f'(stroke (width 0.05) (type solid)) (layer "Edge.Cuts") (uuid "{uid()}"))\n')
        s += line(lr, sy * ly, lr, y, 'Edge.Cuts', 0.05) + line(lr, y, c, y, 'Edge.Cuts', 0.05)
    s += line(-c, -c, -c, c, 'Edge.Cuts', 0.05) + line(c, -c, c, c, 'Edge.Cuts', 0.05)
    return s


def alps_ec05e():
    name = 'Alps_EC05E1220401'
    s = (f'(footprint "{name}"\n  (version 20241229)\n  (generator "nrsk-gen")\n  (layer "F.Cu")\n'
         '  (descr "Alps EC05E1220401 5 mm hollow-shaft rotary encoder, vertical, 12 detents / 12 pulses, '
         'hex shaft hole 1.72 mm A/F; 3 mm square board hole under the rotor")\n'
         '  (tags "rotary encoder Alps EC05E hollow shaft")\n  (attr smd)\n')
    s += prop('Reference', 'REF**', (0, -3.6), 'F.SilkS', size=0.8)
    s += prop('Value', name, (0, 6.2), 'F.Fab', size=0.6)
    s += prop('Footprint', '', (0, 0), 'F.Fab', hide=True)
    s += prop('Datasheet', '', (0, 0), 'F.Fab', hide=True)   # catalog: tech.alpsalpine.com, EC05E1220401
    s += prop('Description', '', (0, 0), 'F.Fab', hide=True)
    x0, y0, x1, y1 = ENC_BODY
    s += rect(x0, y0, x1, y1, 'F.Fab', 0.1)
    s += text('A', -ENC_PIN_PITCH, ENC_PIN_Y, 'F.Fab', 0.6)
    s += line(x0, y0 - 0.15, x1, y0 - 0.15, 'F.SilkS')          # top edge only: the lands cover the sides
    lx, ly, lw, lh = ENC_LAND
    s += rect(-lx - lw / 2 - 0.25, y0 - 0.25, lx + lw / 2 + 0.25, ENC_PIN_Y + ENC_PIN[1] / 2 + 0.25, 'F.CrtYd', 0.05)
    for sx in (-1, 1):   # side tabs: mechanical, no net
        s += (f'  (pad "" smd rect (at {sx * lx:.3f} {ly:.3f}) (size {lw} {lh}) '
              f'(layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid()}"))\n')
    for i, num in enumerate(('A', 'C', 'B')):
        s += (f'  (pad "{num}" smd rect (at {(i - 1) * ENC_PIN_PITCH:.3f} {ENC_PIN_Y:.3f}) '
              f'(size {ENC_PIN[0]} {ENC_PIN[1]}) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid()}"))\n')
    hx, hy, hd = ENC_HOLES
    s += npth(-hx, hy, hd) + npth(hx, hy, hd)
    s += edge_cut_outline()
    # Alps' STEP (fetched by gen/fetch_3d.sh): rotor axis at the origin, mounting surface at z = 0
    s += model(ALPS_3D + 'EC05E1220401.step')
    s += ')\n'
    return name, s


# Alps EC10E1220505: 10 mm hollow-shaft encoder, horizontal (axis parallel to the board, 7 mm above it),
# 24 detents / 12 pulses (catalog page EC10E). Origin = the rotor axis projected onto the board at the body's
# face on the shaft-insert side; +X points out of that face (toward the drum), so the body lies at x < 0.
# Seen from the shaft-insert side the terminals read A B C from left to right: A at +Y, C (common) at -Y.
EC10_BODY = (-6.1, -4.9, 0.0, 4.9)      # bracket footprint: 6.1 along the axis, 9.8 across
EC10_PIN_X, EC10_PIN_PITCH = -3.7, 2.5  # A B C, 3 x 1.0 mm holes, 3.7 mm from the insert-side face
EC10_LEG = (-1.7, 4.5, 2.1, 1.8)        # mounting legs: x, y (+/-), slot along x, across y (outer edges 10.8 apart)


def alps_ec10e():
    name = 'Alps_EC10E'
    s = (f'(footprint "{name}"\n  (version 20241229)\n  (generator "nrsk-gen")\n  (layer "F.Cu")\n'
         '  (descr "Alps EC10E 10 mm hollow-shaft rotary encoder, horizontal, axis 7 mm above the board '
         '(EC10E1220505: 24 detents / 12 pulses), hex shaft hole 1.73 mm A/F entered from +X")\n'
         '  (tags "rotary encoder Alps EC10E hollow shaft horizontal")\n  (attr through_hole)\n')
    s += prop('Reference', 'REF**', (-3.0, -6.6), 'F.SilkS', size=0.8)
    s += prop('Value', name, (-3.0, 6.6), 'F.Fab', size=0.6)
    s += prop('Footprint', '', (0, 0), 'F.Fab', hide=True)
    s += prop('Datasheet', '', (0, 0), 'F.Fab', hide=True)   # catalog: tech.alpsalpine.com, EC10E
    s += prop('Description', '', (0, 0), 'F.Fab', hide=True)
    x0, y0, x1, y1 = EC10_BODY
    lx, ly, lw, lh = EC10_LEG
    s += rect(x0, y0, x1, y1, 'F.Fab', 0.1)
    s += line(0.4, -1.0, 0.4, 1.0, 'F.Fab', 0.1)               # shaft-insert side
    s += text('A', EC10_PIN_X + 1.4, EC10_PIN_PITCH, 'F.Fab', 0.6)
    s += line(x0 - 0.15, y0 + 1.0, x0 - 0.15, y1 - 1.0, 'F.SilkS')   # back face; the legs cover the sides
    s += line(x1 + 0.15, -1.6, x1 + 0.15, 1.6, 'F.SilkS')
    s += rect(x0 - 0.3, -(ly + lh / 2 + 0.65), x1 + 0.3, ly + lh / 2 + 0.65, 'F.CrtYd', 0.05)
    for sy in (-1, 1):   # mounting legs: plated slots, no net
        s += (f'  (pad "" thru_hole roundrect (at {lx:.3f} {sy * ly:.3f}) (size {lw + 0.4:.2f} {lh + 0.4:.2f}) '
              f'(drill oval {lw} {lh}) (roundrect_rratio 0.25) (layers "*.Cu" "*.Mask") (uuid "{uid()}"))\n')
    for i, num in enumerate(('A', 'B', 'C')):
        shape = 'rect' if num == 'A' else 'circle'
        s += (f'  (pad "{num}" thru_hole {shape} (at {EC10_PIN_X:.3f} {(1 - i) * EC10_PIN_PITCH:.3f}) '
              f'(size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask") (uuid "{uid()}"))\n')
    s += model(NRSK_3D + 'Alps_EC10E.wrl')
    s += ')\n'
    return name, s


# Drum dial (right half): the printed drum spins between the EC10E rotor and a printed bearing block that
# stands on the PCB, located by two pegs in NPTH holes. Board-only footprint, same origin as Alps_EC10E
# (encoder's shaft-insert face on the axis); its courtyard covers drum + block so nothing is placed there.
DRUM_GAP, DRUM_W = 0.4, 23.8            # encoder face -> drum, drum width (~1.25 u: the most the free 2 u takes)
DRUM_D = 13.0
BLOCK_T = 3.0                           # bearing block thickness along the axis
BLOCK_PEGS = (2.0, 2.0)                 # NPTH diameter, peg offset across the axis (+/-)
DRUM_BLOCK_X = DRUM_GAP + DRUM_W + DRUM_GAP + BLOCK_T / 2   # block centre = 26.1


def drum_bearing():
    name = 'Drum_Dial_Bearing'
    s = (f'(footprint "{name}"\n  (version 20241229)\n  (generator "nrsk-gen")\n  (layer "F.Cu")\n'
         '  (descr "Drum dial: 13 mm drum and the printed bearing block beside an Alps EC10E; two NPTH for the '
         'block pegs. Origin = the encoder footprint origin")\n'
         '  (tags "drum dial bearing")\n  (attr board_only exclude_from_pos_files exclude_from_bom)\n')
    s += prop('Reference', 'REF**', (DRUM_BLOCK_X / 2, -8.0), 'F.Fab', hide=True, size=0.8)
    s += prop('Value', name, (DRUM_BLOCK_X / 2, 8.0), 'F.Fab', hide=True, size=0.6)
    s += prop('Footprint', '', (0, 0), 'F.Fab', hide=True)
    s += prop('Datasheet', '', (0, 0), 'F.Fab', hide=True)
    s += prop('Description', '', (0, 0), 'F.Fab', hide=True)
    r = DRUM_D / 2
    s += rect(DRUM_GAP, -r, DRUM_GAP + DRUM_W, r, 'F.Fab', 0.1)
    s += text('DRUM', DRUM_GAP + DRUM_W / 2, 0, 'F.Fab', 1.2)
    s += rect(DRUM_BLOCK_X - BLOCK_T / 2, -3.5, DRUM_BLOCK_X + BLOCK_T / 2, 3.5, 'F.Fab', 0.1)
    s += rect(0.35, -r - 0.5, DRUM_BLOCK_X + BLOCK_T / 2 + 0.25, r + 0.5, 'F.CrtYd', 0.05)   # clear of the EC10E's
    d, py = BLOCK_PEGS
    s += npth(DRUM_BLOCK_X, -py, d) + npth(DRUM_BLOCK_X, py, d)
    s += ')\n'
    return name, s


def usb_c():
    """KiCad's HRO TYPE-C-31-M-12 with its outline moved from the silkscreen to the Fab layer: on the board
    tongue the outline's front ends would run into the tongue's rounded corners (clipped silk)."""
    name = 'USB_C_Receptacle_HRO_TYPE-C-31-M-12'
    s = open(os.path.join(STD_FP, 'Connector_USB.pretty', name + '.kicad_mod')).read()
    head, sep, body = s.partition('(fp_line')       # the Reference text before the first line stays on silk
    return name, head + sep + body.replace('(layer "F.SilkS")', '(layer "F.Fab")')


def main():
    os.makedirs(OUT, exist_ok=True)
    items = [mx_hotswap(w) for w in WIDTHS] + [oled_module(), alps_ec05e(), alps_ec10e(), drum_bearing(), usb_c()]
    for name, s in items:
        open(os.path.join(OUT, name + '.kicad_mod'), 'w').write(s)
    print('wrote', [n for n, _ in items])


if __name__ == '__main__':
    main()
