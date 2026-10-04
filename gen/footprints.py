"""Generate the project footprint library lib/nrsk.pretty."""
import os
import uuid

from layout import HERE

OUT = os.path.join(HERE, '..', 'lib', 'nrsk.pretty')
WIDTHS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25]
U = 19.05


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
    s += ')\n'
    return name, s


# 0.91" 128x32 SSD1306 I2C module (38 x 12 mm), soldered ~2 mm above the PCB.
OLED_W, OLED_H = 38.0, 12.0
OLED_PIN_FROM_EDGE = 1.6      # header row centre to the module's short edge
OLED_GLASS = (30.0, 11.5)     # glass panel, toward the end away from the header


def oled_module():
    """Origin = module centre, long axis along X, header at -X end (pins 1..4 = GND VCC SCL SDA along +Y)."""
    name = 'OLED_0.91in_128x32_I2C'
    s = (f'(footprint "{name}"\n  (version 20241229)\n  (generator "nrsk-gen")\n  (layer "F.Cu")\n'
         '  (descr "0.91 inch 128x32 OLED module (SSD1306, I2C), 38 x 12 mm, 4-pin 2.54 mm header '
         '(GND VCC SCL SDA); mount ~2 mm above the PCB without the header spacer")\n'
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
    s += ')\n'
    return name, s


def main():
    os.makedirs(OUT, exist_ok=True)
    items = [mx_hotswap(w) for w in WIDTHS] + [oled_module()]
    for name, s in items:
        open(os.path.join(OUT, name + '.kicad_mod'), 'w').write(s)
    print('wrote', [n for n, _ in items])


if __name__ == '__main__':
    main()
