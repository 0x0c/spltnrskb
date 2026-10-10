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
    s += prop('Datasheet', 'https://tech.alpsalpine.com/e/products/detail/EC05E1220401/', (0, 0), 'F.Fab', hide=True)
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


def main():
    os.makedirs(OUT, exist_ok=True)
    items = [mx_hotswap(w) for w in WIDTHS] + [oled_module(), alps_ec05e()]
    for name, s in items:
        open(os.path.join(OUT, name + '.kicad_mod'), 'w').write(s)
    print('wrote', [n for n, _ in items])


if __name__ == '__main__':
    main()
