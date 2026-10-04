"""Generate the enclosure for each half from <side>/case_data.json.

Two variants share one geometry:
  * laser  - acrylic sandwich: bottom 3 mm + 4 frames x 3 mm + switch plate 1.5 mm  (DXF / SVG)
  * print  - 3D printed tray (floor + walls + bosses) + printed plate                (STL)

Heights (z, mm, bottom of case = 0)
  acrylic : bottom 0-3 | frames 3-15 | PCB 10.0-11.6 on 7 mm M2 standoffs | plate 15-16.5
  print   : floor 0-2  | walls 2-14.1 | PCB 9.0-10.6 on 7 mm bosses       | plate 14.1-15.6
MX spec: plate top to PCB top = 5.0 mm -> plate bottom 3.5 mm above the PCB.
USB-C and TRRS sit on the back of the PCB, so the plugs pass below the PCB: the switch plate and
the top frame stay closed, only the wall below the PCB is opened.

Run with the project venv:  .venv/bin/python gen/make_case.py
"""
import json
import math
import os
import struct
import sys

from manifold3d import CrossSection, JoinType, Manifold, set_circular_segments

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'case')
set_circular_segments(96)

# --- parameters ---------------------------------------------------------------
CLEAR = 0.5          # PCB edge to frame inner wall
WALL = 8.0           # frame / wall width
SCREW_D = 2.2        # M2 clearance hole
PLATE_T = 1.5
PCB_T = 1.6
PLATE_GAP = 3.5      # PCB top -> plate bottom (MX: 5.0 - 1.5)
STANDOFF = 7.0       # PCB bottom above case floor (room for the TRRS / USB-C plugs under the PCB)
# acrylic
BOTTOM_T = 3.0
FRAME_T = 3.0
N_FRAMES = 4
PLUG_TOP = 0.3       # plug opening ends this far above the PCB top (USB-C overmold top = PCB top + 0.05)
# print
FLOOR = 2.0
BOSS_D = 4.6         # stays clear of back-side pads (>= 2.75 mm from hole centre)
PILOT_D = 1.6        # M2 self-tapping
INSERT_D = 3.2       # M2 heat-set insert in the wall top
INSERT_DEPTH = 4.0
RESET_D = 3.0
SWITCH_CUT = 14.0
STAB_CUT = (7.0, 15.4, 0.5)   # w, h, centre y offset (down) of each stabilizer housing cut-out
STAB_X = 11.938


def cs_poly(pts):
    # board coordinates are y-down; flipping y reverses the winding, so reverse the order too
    return CrossSection([[(x, -y) for x, y in reversed(pts)]])


def rect(x0, y0, x1, y1):
    return cs_poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def rounded_rect(x0, y0, x1, y1, r):
    return rect(x0 + r, y0 + r, x1 - r, y1 - r).offset(r, JoinType.Round)


def circle(x, y, d):
    return CrossSection.circle(d / 2).translate((x, -y))


class Half:
    def __init__(self, side):
        self.d = json.load(open(os.path.join(ROOT, side, 'case_data.json')))
        self.side = side
        o = self.d['outline']
        self.pcb = (o['x0'], o['y0'], o['x1'], o['y1'], o['r'])
        x0, y0, x1, y1, r = self.pcb
        self.inner = rounded_rect(x0 - CLEAR, y0 - CLEAR, x1 + CLEAR, y1 + CLEAR, r + CLEAR)
        e = CLEAR + WALL
        self.outer_box = (x0 - e, y0 - e, x1 + e, y1 + e, r + e)
        self.outer = rounded_rect(*self.outer_box)
        self.inner_right = self.d['inner_side'] == 'right'
        self.slots = self._slots()
        self.screws = self._screws()

    # connector openings through the inner wall -----------------------------------
    def _slots(self):
        out = []
        x0, _, x1, _, _ = self.outer_box
        for name, c in self.d['connectors'].items():
            bx0, by0, bx1, by1 = c['box']
            cy = (by0 + by1) / 2
            half = max(c['plug'][0], by1 - by0 + 1.0) / 2
            if self.inner_right:
                out.append(dict(name=name, y=cy, half=half, x0=bx0 - 0.5, x1=x1 + 5))
            else:
                out.append(dict(name=name, y=cy, half=half, x0=x0 - 5, x1=bx1 + 0.5))
        return out

    def slot_cs(self, pcb_side_too=True):
        cs = CrossSection()
        for s in self.slots:
            x0, x1 = s['x0'], s['x1']
            if not pcb_side_too:   # only through the wall (from the PCB edge outward)
                if self.inner_right:
                    x0 = self.pcb[2]
                else:
                    x1 = self.pcb[0]
            cs = cs + rect(x0, s['y'] - s['half'], x1, s['y'] + s['half'])
        return cs

    # perimeter screws on the wall centre line --------------------------------------
    def _screws(self):
        x0, y0, x1, y1, r = self.pcb
        m = CLEAR + WALL / 2
        X0, Y0, X1, Y1, R = x0 - m, y0 - m, x1 + m, y1 + m, r + m
        pts = []
        k = R * (1 - 1 / math.sqrt(2))
        pts += [(X0 + k, Y0 + k), (X1 - k, Y0 + k), (X0 + k, Y1 - k), (X1 - k, Y1 - k)]
        n = max(1, round((X1 - X0) / 55) - 1)
        for i in range(1, n + 1):
            x = X0 + (X1 - X0) * i / (n + 1)
            pts += [(x, Y0), (x, Y1)]
        # sides: outer side at mid height; inner side in every gap between slots
        outer_x, inner_x = (X0, X1) if self.inner_right else (X1, X0)
        pts.append((outer_x, (Y0 + Y1) / 2))
        edges = sorted([(s['y'] - s['half'], s['y'] + s['half']) for s in self.slots])
        free, last = [], Y0 + R
        for a, b in edges:
            free.append((last, a)); last = b
        free.append((last, Y1 - R))
        for a, b in free:
            a2, b2 = a + 3.5, b - 3.5
            if b2 - a2 >= 0:
                pts.append((inner_x, (a2 + b2) / 2))
        return pts

    # 2D layers ------------------------------------------------------------------------
    def holes(self, pts, d):
        cs = CrossSection()
        for x, y in pts:
            cs = cs + circle(x, y, d)
        return cs

    def plate(self):
        cut = CrossSection()
        for k in self.d['keys']:
            h = SWITCH_CUT / 2
            cut = cut + rect(k['cx'] - h, k['cy'] - h, k['cx'] + h, k['cy'] + h)
            if k['w'] >= 2:
                w, hh, dy = STAB_CUT
                for sx in (-1, 1):
                    cx = k['cx'] + sx * STAB_X
                    cut = cut + rect(cx - w / 2, k['cy'] + dy - hh / 2, cx + w / 2, k['cy'] + dy + hh / 2)
        return self.outer - cut - self.holes(self.screws, SCREW_D)

    def frame(self, layer):
        cs = self.outer - self.inner - self.holes(self.screws, SCREW_D)
        z0 = BOTTOM_T + layer * FRAME_T
        if z0 < BOTTOM_T + STANDOFF + PCB_T + PLUG_TOP:   # this frame is level with the plugs
            cs = cs - self.slot_cs(False)
        return cs

    def bottom(self):
        return (self.outer - self.holes(self.screws, SCREW_D) - self.holes(self.d['holes'], SCREW_D)
                - circle(*self.d['reset'], RESET_D))

    # 3D print -------------------------------------------------------------------------
    def tray(self):
        wall_top = FLOOR + STANDOFF + PCB_T + PLATE_GAP
        body = Manifold.extrude(self.outer, wall_top)
        body = body - Manifold.extrude(self.inner, wall_top).translate((0, 0, FLOOR))
        slot_top = FLOOR + STANDOFF + PCB_T + PLUG_TOP      # wall stays closed above this
        body = body - Manifold.extrude(self.slot_cs(False), slot_top - FLOOR).translate((0, 0, FLOOR))
        for x, y in self.d['holes']:
            boss = Manifold.cylinder(STANDOFF, BOSS_D / 2, BOSS_D / 2).translate((x, -y, FLOOR))
            body = body + boss
            body = body - Manifold.cylinder(STANDOFF + FLOOR - 0.6, PILOT_D / 2, PILOT_D / 2).translate((x, -y, 0.6))
        for x, y in self.screws:
            body = body - Manifold.cylinder(INSERT_DEPTH + 0.01, INSERT_D / 2, INSERT_D / 2).translate(
                (x, -y, wall_top - INSERT_DEPTH))
        rx, ry = self.d['reset']
        body = body - Manifold.cylinder(FLOOR + 0.02, RESET_D / 2, RESET_D / 2).translate((rx, -ry, -0.01))
        return body

    def plate3d(self):
        return Manifold.extrude(self.plate(), PLATE_T)

    def pcb3d(self):
        x0, y0, x1, y1, r = self.pcb
        cs = rounded_rect(x0, y0, x1, y1, r) - self.holes(self.d['holes'], 2.2)
        return Manifold.extrude(cs, PCB_T)


# --- writers -----------------------------------------------------------------------
def polygons(cs):
    return [[(float(x), float(y)) for x, y in poly] for poly in cs.to_polygons()]


def write_dxf(path, cs):
    lines = ['0', 'SECTION', '2', 'HEADER', '9', '$INSUNITS', '70', '4', '0', 'ENDSEC',
             '0', 'SECTION', '2', 'ENTITIES']
    for poly in polygons(cs):
        lines += ['0', 'POLYLINE', '8', 'CUT', '66', '1', '70', '1']
        for x, y in poly:
            lines += ['0', 'VERTEX', '8', 'CUT', '10', f'{x:.4f}', '20', f'{y:.4f}']
        lines += ['0', 'SEQEND']
    lines += ['0', 'ENDSEC', '0', 'EOF']
    open(path, 'w').write('\n'.join(lines) + '\n')


def write_svg(path, cs, label=''):
    x0, y0, x1, y1 = map(float, cs.bounds())
    pad = 2
    w, h = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
    d = ''
    for poly in polygons(cs):
        d += 'M' + ' L'.join(f'{x - x0 + pad:.3f},{y1 - y + pad:.3f}' for x, y in poly) + ' Z '
    open(path, 'w').write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" viewBox="0 0 {w:.3f} {h:.3f}">'
        f'<title>{label}</title><path d="{d}" fill="none" stroke="#ff0000" stroke-width="0.01"/></svg>\n')


def write_stl(path, man):
    mesh = man.to_mesh()
    v = mesh.vert_properties[:, :3]
    t = mesh.tri_verts
    with open(path, 'wb') as f:
        f.write(b'nrsk'.ljust(80, b' '))
        f.write(struct.pack('<I', len(t)))
        for a, b, c in t:
            p0, p1, p2 = v[a], v[b], v[c]
            ux, uy, uz = p1 - p0
            vx, vy, vz = p2 - p0
            n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
            f.write(struct.pack('<12fH', *n, *p0, *p1, *p2, 0))


def main(sides):
    report = {}
    for side in sides:
        hf = Half(side)
        for sub in ('laser', 'print', 'preview'):
            os.makedirs(os.path.join(OUT, sub), exist_ok=True)
        layers = {'plate': hf.plate(), 'bottom': hf.bottom()}
        for i in range(N_FRAMES):
            layers[f'frame{i + 1}'] = hf.frame(i)
        for name, cs in layers.items():
            write_dxf(os.path.join(OUT, 'laser', f'{side}-{name}.dxf'), cs)
            write_svg(os.path.join(OUT, 'laser', f'{side}-{name}.svg'), cs, f'{side} {name}')
        tray, plate = hf.tray(), hf.plate3d()
        write_stl(os.path.join(OUT, 'print', f'{side}-tray.stl'), tray)
        write_stl(os.path.join(OUT, 'print', f'{side}-plate.stl'), plate)
        # assembly preview (print variant): tray + PCB + plate in place
        z_pcb = FLOOR + STANDOFF
        write_stl(os.path.join(OUT, 'preview', f'{side}-pcb.stl'), hf.pcb3d().translate((0, 0, z_pcb)))
        write_stl(os.path.join(OUT, 'preview', f'{side}-plate-placed.stl'),
                  plate.translate((0, 0, z_pcb + PCB_T + PLATE_GAP)))
        ox0, oy0, ox1, oy1, _ = hf.outer_box
        report[side] = dict(case_mm=[round(ox1 - ox0, 1), round(oy1 - oy0, 1)],
                            height_print=round(FLOOR + STANDOFF + PCB_T + PLATE_GAP + PLATE_T, 2),
                            height_acrylic=BOTTOM_T + N_FRAMES * FRAME_T + PLATE_T,
                            screws=len(hf.screws), pcb_holes=len(hf.d['holes']),
                            tray_volume_cm3=round(tray.volume() / 1000, 1),
                            plate_genus=plate.genus(), tray_status=str(tray.status()))
        check(hf, layers)
    json.dump(report, open(os.path.join(OUT, 'case_report.json'), 'w'), indent=1)
    print(json.dumps(report, indent=1))


def check(hf, layers):
    """Sanity checks between case and PCB."""
    x0, y0, x1, y1, _ = hf.pcb
    for k in hf.d['keys']:
        assert x0 < k['cx'] - 7 and k['cx'] + 7 < x1, k
    for x, y in hf.screws:   # screws must sit in the wall, not over the PCB
        assert not (x0 - CLEAR < x < x1 + CLEAR and y0 - CLEAR < y < y1 + CLEAR), (x, y)
    for x, y in hf.d['holes']:  # PCB holes must be inside the PCB and inside every frame opening
        assert x0 + 2 < x < x1 - 2 and y0 + 2 < y < y1 - 2
    # every connector slot must leave the outer wall
    for s in hf.slots:
        assert (s['x1'] > hf.outer_box[2]) if hf.inner_right else (s['x0'] < hf.outer_box[0])
    for name, cs in layers.items():
        assert not cs.is_empty(), name

    def area(poly):
        return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2
    # the switch plate and the top frame must keep an unbroken outer edge (no connector notches)
    for name in ('plate', f'frame{N_FRAMES}'):
        outer_area = max(area(p) for p in polygons(layers[name]))
        assert abs(outer_area - hf.outer.area()) < 0.5, (name, outer_area, hf.outer.area())
    slotted = [n for n in layers if n.startswith('frame') and
               abs(max(area(p) for p in polygons(layers[n])) - hf.outer.area()) > 0.5]
    print(hf.side, 'closed: plate,', f'frame{N_FRAMES};', 'opened for plugs:', ', '.join(slotted) or '-')
    print(hf.side, 'checks ok;', len(hf.screws), 'case screws,', len(hf.d['holes']), 'PCB standoffs')


if __name__ == '__main__':
    main(sys.argv[1:] or ['left', 'right'])
