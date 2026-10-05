"""3D model (VRML) of the 0.91" OLED module, which no library has -> lib/nrsk.3dshapes/.

Coordinates below are footprint mm (x right, y down as in the footprint, z up from the board's top
surface); they are converted to VRML (y up, 1 unit = 0.1 inch) on write. Models only need to look
right in the KiCad 3D viewer and the case viewer, so the module is a few boxes.
Switches, sockets and stabilizers come from kiswitch, the USB-C and TRRS jacks from LCSC (gen/fetch_3d.sh).
"""
import os

from layout import HERE

OUT = os.path.join(HERE, '..', 'lib', 'nrsk.3dshapes')
PCB_T = 1.6

GOLD = (0.83, 0.68, 0.30)
OLED_PCB = (0.05, 0.14, 0.38)
GLASS = (0.02, 0.02, 0.03)
SCREEN = (0.05, 0.07, 0.10)


def box(x0, y0, x1, y1, z0, z1):
    v = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    f = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    return v, f


def shape(parts, color, shine=0.3):
    pts, idx = [], []
    for v, f in parts:
        o = len(pts)
        pts += v
        idx += [tuple(o + i for i in face) for face in f]
    # mm, footprint y down -> VRML 0.1 inch, y up
    p = ', '.join(f'{x / 2.54:.4f} {-y / 2.54:.4f} {z / 2.54:.4f}' for x, y, z in pts)
    i = ', '.join(' '.join(str(k) for k in face) + ' -1' for face in idx)
    c = ' '.join(f'{c:.3f}' for c in color)
    return ('Shape {\n appearance Appearance { material Material { diffuseColor ' + c +
            f' specularColor 0.3 0.3 0.3 shininess {shine} }} }}\n'
            ' geometry IndexedFaceSet { solid FALSE creaseAngle 0.5\n'
            f'  coord Coordinate {{ point [ {p} ] }}\n  coordIndex [ {i} ] }}\n}}\n')


def oled():
    """0.91" module, origin at its centre, header at -X; glass top 2.5 mm above the board (under the taped 2 mm cover)."""
    z0 = 2.5 - 2.2
    pcb = [box(-19.0, -6.0, 19.0, 6.0, z0, z0 + 1.0)]
    gx = 19.0 - 15.0 - 1.0
    glass = [box(gx - 15.0, -5.75, gx + 15.0, 5.75, z0 + 1.0, z0 + 2.2)]
    screen = [box(gx - 11.5, -2.9, gx + 11.5, 2.9, z0 + 2.2, z0 + 2.21)]
    px = -19.0 + 1.6
    pins = [box(px - 0.32, (i - 1.5) * 2.54 - 0.32, px + 0.32, (i - 1.5) * 2.54 + 0.32, -PCB_T - 1.5, z0 + 1.6)
            for i in range(4)]
    return shape(pcb, OLED_PCB) + shape(glass, GLASS, 0.9) + shape(screen, SCREEN, 0.9) + shape(pins, GOLD, 0.6)


MODELS = {'OLED_0.91in_128x32.wrl': oled}

def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in MODELS.items():
        open(os.path.join(OUT, name), 'w').write('#VRML V2.0 utf8\n' + fn())
    print('wrote', list(MODELS))


if __name__ == '__main__':
    main()
