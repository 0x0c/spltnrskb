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
from layout import WHEEL_DETENTS

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
# connector ports: the PCB reaches into the wall on a tongue, the connector mouth sits PORT_SKIN inside the outer
# surface, and the wall shows only the connector outline. In the printed tray the wall above each port is a
# removable port cap (the board is dropped in first); in the acrylic stack the frames are notched.
USB_SHELL = (8.94, 3.26)     # HRO TYPE-C-31-M-12 shell w, h (hangs under the PCB)
TRRS_H, TRRS_NOZZLE = 5.0, 5.0   # PJ-320D body height under the PCB, nozzle diameter
PORT_CLR = 0.2               # opening around the connector outline
CHANNEL_CLR = 0.3            # tongue / connector body to the cap channel
PORT_CAP_EXTRA = 3.0         # port cap reaches this far beyond the channel along the wall
# print
FLOOR = 2.0
BOSS_D = 4.6         # stays clear of back-side pads (>= 2.75 mm from hole centre)
PILOT_D = 1.6        # M2 self-tapping
INSERT_D = 3.2       # M2 heat-set insert (in the printed plate's bosses)
INSERT_DEPTH = 4.0
# plate screws (one tray for A and B):
#   B (printed plate): M2 x 12 from the tray bottom (counterbored) up the wall into a heat-set insert in a boss under
#     the plate, so the plate top shows no screws; the boss sits in a pocket at the wall top
#   A (acrylic plate): M2 x 6 slim-head screw from the top into an M2 nut dropped into the hex trap under that pocket
#   acrylic stack: M2 x 20 from the top through everything into a nut under the bottom plate
SCREW_CB = (4.6, 1.6)        # counterbore for the pan head under the tray (diameter, depth)
PLATE_BOSS = (5.6, 3.0)      # boss under the printed plate (diameter, height)
BOSS_POCKET = (6.0, 3.2)     # pocket in the wall top for the boss
NUT_TRAP = (4.15, 1.8)       # hex trap for an M2 nut under the pocket (across flats, depth)
RESET_D = 3.0
# 3D print: the wall above the wheel opening is a separate cap, so the wheel can be dropped in from above
CAP_SHOULDER = 2.0           # cap's top tier overhangs the opening by this much and rests on the wall
CAP_LEDGE = 3.0              # thickness of that top tier
CAP_FIT = 0.15
RIB_T = 2.0                  # all-printed variant: web under the printed plate (PCB top + 1.5)
TRAY_FILLET = 2.0     # 3D-printed tray: rounded bottom outer edge
TRAY_TOP_FILLET = 0.6 # small round on the top outer edge, under the plate
PLATE_FILLET = 1.0    # all-printed plate: rounded top outer edge (prints fine top-down: 1 mm reach on the bed side)
SWITCH_CUT = 14.0
# OLED: window in the switch plate, filled by a half-mirror acrylic cover flush with the plate top. Half-mirror
# acrylic starts at 2 mm, so the cover reaches 0.5 mm below the 1.5 mm plate; it rests on the module's glass
# (soldered low, glass top 2.5 mm above the PCB) and is held by 0.5 mm clear double-sided tape. No screws,
# so the plate keeps its closed outer edge.
OLED_WINDOW_CLEAR = 0.15     # added to the module courtyard (courtyard = module + 0.25)
COVER_T = 2.0                # half-mirror acrylic; top flush with the plate top
COVER_FIT = 0.1              # cover edge to plate opening
COVER_BORDER = 5.0           # cover: rounded rectangle, this much larger than the OLED window all round
COVER_R = 5.0                 # follows the rounded case corner it sits next to
COVER_MARGIN = 3.0           # cover stays at least this far inside the case outline
WALL_POCKET = 0.5            # 3D print: wall top lowered under the cover (cover 2 mm vs plate 1.5 mm)
TAPE_T = 0.5                 # clear double-sided tape between glass and cover
OLED_GLASS_TOP = PLATE_GAP + PLATE_T - COVER_T - TAPE_T   # = 2.5: glass top above the PCB top
SWITCH_TOP_KEEPOUT = 8.4     # half size of an MX top housing (15.6 mm) + 0.6 mm
# corner thumbwheel: lies under the PCB, rim out of the corner; magnet (6 x 1.5 mm, diametric) on top,
# read through the air gap by the AS5600 on the PCB back
WHEEL_T = 4.1
WHEEL_GAP = 0.3              # wheel bottom above the floor / bottom plate
WHEEL_CUT = 0.6              # radial clearance of the wall opening
BORE_D, BORE_DEPTH = 4.0, 2.0          # axle bore from below
MAGNET_D, MAGNET_DEPTH = 6.1, 1.6      # magnet pocket from the top
POST_D = 3.8                 # printed axle post (3D print variant)
AXLE_HOLE_D = 3.2            # M3 axle screw through the bottom plate (acrylic variant)
# tactile detent: the rim carries WHEEL_DETENTS rounded teeth (also the grip); inside the case an M3 ball
# plunger (steel spring + ball) is screwed sideways into a solid block and presses on the teeth, so the wheel
# clicks once per firmware step. The force is radial and taken by the axle, so the wheel is not lifted, and
# nothing printed has to flex. How far the plunger is screwed in sets the click force.
TOOTH_DEPTH = 0.5            # valley depth of the rim teeth
BLOCK_GAP = 0.4              # block face to the tooth crests
BLOCK_W, BLOCK_L = 8.0, 9.0  # plunger block across / along the plunger (NBK PAFS-3: L 6 + ball 0.5, hex 1.5 at the rear)
PLUNGER_TAP_D = 2.5          # M3 tapping hole (tap it, or let the plunger cut its own thread in PETG)
PLUNGER_WALL = 1.0           # material above the tapped hole
BLOCK_SCREWS = (-2.5, 2.5)   # acrylic variant: two M2 screws from below, across the block
STAB_CUT = (7.0, 15.4, 0.5)   # w, h, centre y offset (down) of each stabilizer housing cut-out
STAB_X = 11.938


def cs_poly(pts):
    # board coordinates are y-down; flipping y reverses the winding, so reverse the order too
    return CrossSection([[(x, -y) for x, y in reversed(pts)]])


def rect(x0, y0, x1, y1):
    return cs_poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def rounded_rect(x0, y0, x1, y1, r):
    return rect(x0 + r, y0 + r, x1 - r, y1 - r).offset(r, JoinType.Round)


def inside(cs, p):
    """Point (board coordinates) inside a cross-section."""
    return (circle(p[0], p[1], 0.2) - cs).area() < 1e-4


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
        self.window_box = self._oled()
        self.cover_screws = self._cover_screws()
        # perimeter screws under the cover give way to the cover's own screws
        cov = self.cover_shape().offset(1.5, JoinType.Round)
        self.screws = [p for p in self.screws if not inside(cov, p) and
                       all(math.dist(p, c) > 8 for c in self.cover_screws)] + self.cover_screws

    # connector openings through the top wall -------------------------------------
    def _slots(self):
        """Connector ports (from the tongues in case_data). Each entry also carries the along-wall extent used to
        keep case screws away ('y'/'half' on the inner edge, 'full' rectangle on the top edge)."""
        out = []
        ox0, oy0, ox1, oy1, _ = self.outer_box
        skin = self.d.get('port_skin', 0.8)
        for name, t in self.d['tongues'].items():
            c = self.d['connectors'][name]
            edge = c.get('edge', 'inner')
            chan = (rect(*t) + rect(*c['box'])).offset(CHANNEL_CLR, JoinType.Miter) ^ self.outer.offset(-skin, JoinType.Miter)
            e = PORT_CAP_EXTRA
            if edge == 'top':
                a0, a1 = t[0] - CHANNEL_CLR - e, t[2] + CHANNEL_CLR + e
                cap = rect(a0, oy0 - 1, a1, self.pcb[1] - CLEAR + 0.01) ^ (self.outer - self.inner)
                full = (a0, oy0 - 1, a1, self.pcb[1])
                out.append(dict(name=name, edge='top', x=(t[0] + t[2]) / 2, half=(a1 - a0) / 2, full=full,
                                chan=chan, cap=cap, along=(t[0] + t[2]) / 2))
            else:
                a0, a1 = t[1] - CHANNEL_CLR - e, t[3] + CHANNEL_CLR + e
                if self.inner_right:
                    cap = rect(self.pcb[2] + CLEAR - 0.01, a0, ox1 + 1, a1) ^ (self.outer - self.inner)
                    full = (self.pcb[2], a0, ox1 + 1, a1)
                else:
                    cap = rect(ox0 - 1, a0, self.pcb[0] - CLEAR + 0.01, a1) ^ (self.outer - self.inner)
                    full = (ox0 - 1, a0, self.pcb[0], a1)
                out.append(dict(name=name, edge='inner', y=(t[1] + t[3]) / 2, half=(a1 - a0) / 2, full=full,
                                chan=chan, cap=cap, along=(t[1] + t[3]) / 2))
        # neighbouring ports on the top edge share one cap (no thin sliver of wall between two caps)
        tops = sorted((sl for sl in out if sl['edge'] == 'top'), key=lambda sl: sl['full'][0])
        for a, b in zip(tops, tops[1:]):
            if b['full'][0] - a['full'][2] < 2 * PORT_CAP_EXTRA:
                full = (a['full'][0], a['full'][1], b['full'][2], a['full'][3])
                cap = rect(full[0], full[1], full[2], self.pcb[1] - CLEAR + 0.01) ^ (self.outer - self.inner)
                for sl in (a, b):
                    sl.update(full=full, cap=cap, half=(full[2] - full[0]) / 2)
        return out

    def port_z(self, port, z_pcb):
        """(bottom of the connector, centre of its opening, opening height) for a PCB bottom at z_pcb."""
        if port['name'] == 'usb':
            return z_pcb - USB_SHELL[1], z_pcb - USB_SHELL[1] / 2, USB_SHELL[1] + 2 * PORT_CLR
        return z_pcb - TRRS_H, z_pcb - TRRS_NOZZLE / 2, TRRS_NOZZLE + 2 * PORT_CLR

    def port_hole(self, port, z_pcb):
        """The visible opening: connector outline + PORT_CLR, through the skin in front of the mouth."""
        _, zc, hh = self.port_z(port, z_pcb)
        ox0, oy0, ox1, oy1, _ = self.outer_box
        depth = self.d.get('port_skin', 0.8) + 1.0
        if port['name'] == 'usb':
            w, h = USB_SHELL[0] + 2 * PORT_CLR, hh
            r = h / 2
            cs = CrossSection.square((w - 2 * r, 0.001), center=True).offset(r, JoinType.Round)
            m = Manifold.extrude(cs, depth + 1).rotate((-90, 0, 0))        # along +y (3D) = outward on the top edge
            return m.translate((port['along'], -oy0 - depth, zc))
        m = Manifold.cylinder(depth + 1, hh / 2, hh / 2, 48).rotate((0, 90, 0))   # along +x
        if port['edge'] == 'top':
            return m.rotate((0, 0, 90)).translate((port['along'], -oy0 - depth, zc))
        if self.inner_right:
            return m.translate((ox1 - depth, -port['along'], zc))
        return m.rotate((0, 0, 180)).translate((ox0 + depth, -port['along'], zc))

    def slot_cs(self, pcb_side_too=True):
        cs = CrossSection()
        for s in self.slots:
            cs = cs + s['cap']
        return cs

    # OLED window and cover ---------------------------------------------------------------
    def _oled(self):
        bx0, by0, bx1, by1 = self.d['oled']['box']
        g = OLED_WINDOW_CLEAR
        return (bx0 - g, by0 - g, bx1 + g, by1 + g)

    def window_cs(self):
        return rect(*self.window_box)

    def wheel_xy(self):
        return self.d['wheel']['center'], self.d['wheel']['r']

    def wheel_cut(self, grow=WHEEL_CUT):
        (x, y), r = self.wheel_xy()
        return circle(x, y, 2 * (r + grow))

    def switch_tops(self):
        cs = CrossSection()
        h = SWITCH_TOP_KEEPOUT
        for k in self.d['keys']:
            cs = cs + rect(k['cx'] - h, k['cy'] - h, k['cx'] + h, k['cy'] + h)
        return cs

    def cover_shape(self):
        """Half-mirror inlay: rounded rectangle centred on the OLED window, COVER_BORDER wide all round."""
        x0, y0, x1, y1 = self.window_box
        m = COVER_BORDER
        return rounded_rect(x0 - m, y0 - m, x1 + m, y1 + m, COVER_R)

    def _cover_screws(self):
        """The cover is held by clear double-sided tape (on the OLED glass and the wall ledge), not screws."""
        return []

    def cover(self):
        return self.cover_shape() - self.holes(self.cover_screws, SCREW_D)

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
        edges = sorted([(s['y'] - s['half'], s['y'] + s['half']) for s in self.slots if s['edge'] == 'inner'])
        free, last = [], Y0 + R
        for a, b in edges:
            free.append((last, a)); last = b
        free.append((last, Y1 - R))
        for a, b in free:
            a2, b2 = a + 3.5, b - 3.5
            if b2 - a2 >= 0:
                pts.append((inner_x, (a2 + b2) / 2))
        # the corner wheel takes the corner screw; put one on each face just past the wheel opening
        (wx, wy), wr = self.d['wheel']['center'], self.d['wheel']['r']
        keep = wr + WHEEL_CUT + CAP_SHOULDER + INSERT_D / 2 + 0.8     # clear of the wheel cap's shoulder
        pts = [p for p in pts if math.hypot(p[0] - wx, p[1] - wy) > keep]
        d = math.sqrt(keep ** 2 - (wy - Y0) ** 2)
        side_x = X0 if wx < (X0 + X1) / 2 else X1
        pts.append((wx + d if side_x == X0 else wx - d, Y0))
        pts.append((side_x, wy + math.sqrt(keep ** 2 - (wx - side_x) ** 2)))
        tops = [rect(*sl['full']).offset(3.5, JoinType.Miter) for sl in self.slots if sl['edge'] == 'top']
        pts = [p for p in pts if not any(inside(t, p) for t in tops)]
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
        return self.outer - cut - self.cover_shape().offset(COVER_FIT, JoinType.Round) - self.holes(self.screws, SCREW_D)

    def frame(self, layer):
        cs = self.outer - self.inner - self.holes(self.screws, SCREW_D)
        z0 = BOTTOM_T + layer * FRAME_T
        wz0 = BOTTOM_T + WHEEL_GAP
        if z0 < wz0 + WHEEL_T + 0.4 and z0 + FRAME_T > wz0 - 0.3:   # this frame is level with the wheel
            cs = cs - self.wheel_cut()
        z_pcb = BOTTOM_T + STANDOFF
        for p in self.slots:       # notch for the tongue + connector, and the opening in front of the mouth
            zb, zc, hh = self.port_z(p, z_pcb)
            if z0 < z_pcb + PCB_T + 0.3 and z0 + FRAME_T > zb - 0.2:
                cs = cs - p['chan']
            if z0 < zc + hh / 2 and z0 + FRAME_T > zc - hh / 2:
                cs = cs - self.port_hole(p, z_pcb).project().offset(0.01, JoinType.Miter)
        return cs

    def bottom(self):
        (wx, wy), _ = self.wheel_xy()
        return (self.outer - self.holes(self.screws, SCREW_D) - self.holes(self.d['holes'], SCREW_D)
                - circle(*self.d['reset'], RESET_D) - circle(wx, wy, AXLE_HOLE_D)
                - self.holes(self.detent_screws_xy(), SCREW_D))

    # tactile detent -------------------------------------------------------------------
    def _detent_frame(self, turn=None):
        """Tip point on the rim (3D frame: x, -y), radial unit u (outward) and tangent v. The plunger points at
        the wheel from inside the case: toward the board centre, turned by the smallest angle that keeps the
        block clear of the standoffs and the reset hole."""
        (wx, wy), r = self.wheel_xy()
        if turn is None:
            turn = self._detent_turn()
        x0, y0, x1, y1, _ = self.pcb
        base = math.atan2(-((y0 + y1) / 2 - wy), (x0 + x1) / 2 - wx) + math.radians(turn)
        ux, uy = math.cos(base), math.sin(base)
        return (wx + r * ux, -wy + r * uy), (ux, uy), (-uy, ux)

    def _detent_turn(self):
        if not hasattr(self, '_turn'):
            for t in sorted(range(-60, 61, 2), key=abs):
                self._turn = t
                foot = self.detent_block(FLOOR)[0].project()
                inside = (foot - self.inner.offset(-0.5, JoinType.Round)).area() < 0.01
                clear = all((foot ^ circle(x, y, BOSS_D + 1.0)).area() < 0.01
                            for x, y in self.d['holes'] + [tuple(self.d['reset'])])
                if inside and clear:
                    break
            else:
                raise AssertionError('no room for the plunger block')
        return self._turn

    def _box(self, a0, a1, b0, b1, z0, z1):
        (qx, qy), (ux, uy), (vx, vy) = self._detent_frame()
        pts = [(qx + a * vx + b * ux, qy + a * vy + b * uy) for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]
        cs = CrossSection([pts])
        if cs.area() < 1e-6:
            cs = CrossSection([pts[::-1]])
        return Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))

    def detent_block(self, z_base):
        """Solid plunger block on the floor (z_base) with the M3 hole aimed at the wheel centre."""
        (qx, qy), (ux, uy), _ = self._detent_frame()
        top = z_base + WHEEL_GAP + WHEEL_T - 0.3
        zc = top - PLUNGER_WALL - PLUNGER_TAP_D / 2
        block = self._box(-BLOCK_W / 2, BLOCK_W / 2, BLOCK_GAP, BLOCK_GAP + BLOCK_L, z_base, top)
        ang = math.degrees(math.atan2(uy, ux))
        hole = Manifold.cylinder(BLOCK_L + 2, PLUNGER_TAP_D / 2, PLUNGER_TAP_D / 2, 24).rotate((0, 90, 0)).translate(
            (BLOCK_GAP - 1, 0, zc)).rotate((0, 0, ang)).translate((qx, qy, 0))
        return block - hole, zc

    def detent_screws_xy(self):
        """Board coordinates of the two M2 screws holding the separate block (acrylic variant)."""
        (qx, qy), (ux, uy), (vx, vy) = self._detent_frame()
        b = BLOCK_GAP + BLOCK_L / 2
        return [(qx + a * vx + b * ux, -(qy + a * vy + b * uy)) for a in BLOCK_SCREWS]

    def detent_part(self):
        """Separate printed plunger block for the acrylic variant: sits on the bottom plate, 2 x M2 from below."""
        block, _ = self.detent_block(BOTTOM_T)
        for x, y in self.detent_screws_xy():
            block = block - Manifold.cylinder(2.0, PILOT_D / 2, PILOT_D / 2, 24).translate((x, -y, BOTTOM_T - 0.01))
        return block

    # 3D print -------------------------------------------------------------------------
    def tray(self):
        wall_top = FLOOR + STANDOFF + PCB_T + PLATE_GAP
        body = self._filleted(wall_top)
        body = body - Manifold.extrude(self.inner, wall_top).translate((0, 0, FLOOR))
        for x, y in self.d['holes']:
            boss = Manifold.cylinder(STANDOFF, BOSS_D / 2, BOSS_D / 2).translate((x, -y, FLOOR))
            body = body + boss
            body = body - Manifold.cylinder(STANDOFF + FLOOR - 0.6, PILOT_D / 2, PILOT_D / 2).translate((x, -y, 0.6))
        for x, y in self.screws:     # screw from below: counterbore, clearance hole up the wall, pocket at the top
            body = body - Manifold.cylinder(wall_top + 0.02, SCREW_D / 2, SCREW_D / 2, 24).translate((x, -y, -0.01))
            body = body - Manifold.cylinder(SCREW_CB[1] + 0.01, SCREW_CB[0] / 2, SCREW_CB[0] / 2, 32).translate((x, -y, -0.01))
            body = body - Manifold.cylinder(BOSS_POCKET[1] + 0.01, BOSS_POCKET[0] / 2, BOSS_POCKET[0] / 2, 32).translate(
                (x, -y, wall_top - BOSS_POCKET[1]))
            r_hex = NUT_TRAP[0] / math.sqrt(3)
            body = body - Manifold.cylinder(NUT_TRAP[1] + 0.01, r_hex, r_hex, 6).translate(
                (x, -y, wall_top - BOSS_POCKET[1] - NUT_TRAP[1]))
        (wx, wy), wr = self.wheel_xy()
        wz0 = FLOOR + WHEEL_GAP
        body = body - Manifold.extrude(self.wheel_cut(), WHEEL_T + 0.7).translate((0, 0, wz0 - 0.3))
        # wall above the opening -> separate cap (stepped, rests on a ledge, held down by the plate)
        z1 = wz0 - 0.3 + WHEEL_T + 0.7
        cut = self.wheel_cut()
        z_l = wall_top - CAP_LEDGE

        def tiers(grow):
            return (Manifold.extrude(cut.offset(grow, JoinType.Round), z_l - z1).translate((0, 0, z1)) +
                    Manifold.extrude(cut.offset(CAP_SHOULDER + grow, JoinType.Round), CAP_LEDGE + 0.01).translate((0, 0, z_l)))
        self._cap = body ^ tiers(-CAP_FIT)
        body = body - tiers(0.0)
        # pocket for the thicker cover
        body = body - Manifold.extrude(self.cover_shape().offset(COVER_FIT, JoinType.Round), WALL_POCKET + 0.01).translate(
            (0, 0, wall_top - WALL_POCKET))
        # port caps: the wall above each connector, lifted out so the board (tongues and connectors) drops in
        z_pcb = FLOOR + STANDOFF
        self._portcaps = []
        groups = []        # ports sharing one cap
        for p in self.slots:
            g = next((g for g in groups if g[0]['cap'] is p['cap']), None)
            groups.append([p]) if g is None else g.append(p)
        for g in groups:
            zs = min(self.port_z(p, z_pcb)[0] for p in g) - 0.2
            vol = Manifold.extrude(g[0]['cap'], wall_top - zs + 0.01).translate((0, 0, zs))
            cap = body ^ vol
            for p in g:
                zp = self.port_z(p, z_pcb)[0] - 0.2
                cap = cap - Manifold.extrude(p['chan'], z_pcb + PCB_T + 0.3 - zp + 0.02).translate((0, 0, zp - 0.01)) \
                    - self.port_hole(p, z_pcb)
            self._portcaps.append(cap)
            body = body - vol
        body = body + Manifold.cylinder(WHEEL_GAP + BORE_DEPTH - 0.3, POST_D / 2, POST_D / 2, 48).translate(
            (wx, -wy, FLOOR))
        rx, ry = self.d['reset']
        body = body - Manifold.cylinder(FLOOR + 0.02, RESET_D / 2, RESET_D / 2).translate((rx, -ry, -0.01))
        return body + self.detent_block(FLOOR)[0]

    def _filleted(self, top):
        """Outer block of the tray with filleted bottom and top outer edges (stacked offset slices)."""
        def band(z0, z1, r, at_bottom):
            parts, n = [], 8
            for i in range(n):
                za, zb = z0 + (z1 - z0) * i / n, z0 + (z1 - z0) * (i + 1) / n
                zm = (za + zb) / 2 - z0 if at_bottom else z1 - (za + zb) / 2
                inset = r - math.sqrt(max(r * r - (r - zm) ** 2, 0))
                parts.append(Manifold.extrude(self.outer.offset(-inset, JoinType.Round), zb - za).translate((0, 0, za)))
            return parts
        rb, rt = TRAY_FILLET, TRAY_TOP_FILLET
        parts = band(0, rb, rb, True) + [Manifold.extrude(self.outer, top - rb - rt).translate((0, 0, rb))] + \
            band(top - rt, top, rt, False)
        out = parts[0]
        for m in parts[1:]:
            out = out + m
        return out

    def port_caps(self):
        if not hasattr(self, '_portcaps'):
            self.tray()
        out = Manifold()
        for c in self._portcaps:
            out = out + c
        return out

    def wheel_cap(self):
        if not hasattr(self, '_cap'):
            self.tray()
        return self._cap

    def wheel3d(self):
        """Knurled thumbwheel (printable or machined): bore from below, magnet pocket on top."""
        (x, y), r = self.wheel_xy()
        pts = []
        n = WHEEL_DETENTS * 12
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = r - TOOTH_DEPTH * (1 - math.cos(WHEEL_DETENTS * a)) / 2      # rounded teeth, crests at r
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        rim = cs_poly(pts)
        w = Manifold.extrude(rim, WHEEL_T)
        w = w - Manifold.cylinder(BORE_DEPTH, BORE_D / 2, BORE_D / 2, 48).translate((x, -y, 0))
        w = w - Manifold.cylinder(MAGNET_DEPTH + 0.01, MAGNET_D / 2, MAGNET_D / 2, 48).translate((x, -y, WHEEL_T - MAGNET_DEPTH))
        return w

    def plate3d(self):
        return Manifold.extrude(self.plate(), PLATE_T)

    def plate3d_printed(self):
        """All-printed variant: the 1.5 mm switch plate plus a RIB_T web underneath, so a printed plate is stiff.
        The web fills the cavity except around the switch housings, the stabilizers and the OLED cover, and
        stays inside the walls. Print it upside down (top face on the bed)."""
        keep = CrossSection()
        g = SWITCH_CUT / 2 + 0.6
        for k in self.d['keys']:
            keep = keep + rect(k['cx'] - g, k['cy'] - g, k['cx'] + g, k['cy'] + g)
            if k['w'] >= 2:
                w, hh, dy = STAB_CUT
                for sx in (-1, 1):
                    cx = k['cx'] + sx * STAB_X
                    keep = keep + rect(cx - w / 2 - 1.0, k['cy'] + dy - hh / 2 - 1.0, cx + w / 2 + 1.0, k['cy'] + dy + hh / 2 + 1.0)
        web = self.inner.offset(-0.3, JoinType.Round) - keep - self.cover_shape().offset(1.0, JoinType.Round) \
            - self.holes(self.d['holes'], BOSS_D + 2.0)
        web = web.offset(-0.4, JoinType.Round).offset(0.4, JoinType.Round)
        plate = self.plate3d() + Manifold.extrude(web, RIB_T).translate((0, 0, -RIB_T))
        plate = plate + Manifold.extrude(self.holes(self.screws, SCREW_D + 0.4), PLATE_T)   # no holes on top: fixed from below
        for x, y in self.screws:     # bosses with heat-set inserts (pressed in from below) for the screws from below
            plate = plate + Manifold.cylinder(PLATE_BOSS[1], PLATE_BOSS[0] / 2, PLATE_BOSS[0] / 2, 32).translate(
                (x, -y, -PLATE_BOSS[1]))
            plate = plate - Manifold.cylinder(PLATE_BOSS[1] + 0.01, INSERT_D / 2, INSERT_D / 2, 24).translate(
                (x, -y, -PLATE_BOSS[1] - 0.01))
        # fillet the top outer edge: clip with the outline inset along a quarter circle (stacked slices)
        r, n = PLATE_FILLET, 8
        env = Manifold.extrude(self.outer.offset(1.0, JoinType.Round), PLATE_T - r + 10).translate((0, 0, -10))
        for i in range(n):
            za, zb = PLATE_T - r + r * i / n, PLATE_T - r + r * (i + 1) / n
            zm = (za + zb) / 2 - (PLATE_T - r)
            inset = r - math.sqrt(max(r * r - zm * zm, 0))
            env = env + Manifold.extrude(self.outer.offset(-inset, JoinType.Round), zb - za).translate((0, 0, za))
        return plate ^ env

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
        layers = {'plate': hf.plate(), 'bottom': hf.bottom(), 'oled-cover': hf.cover()}
        for i in range(N_FRAMES):
            layers[f'frame{i + 1}'] = hf.frame(i)
        for name, cs in layers.items():
            write_dxf(os.path.join(OUT, 'laser', f'{side}-{name}.dxf'), cs)
            write_svg(os.path.join(OUT, 'laser', f'{side}-{name}.svg'), cs, f'{side} {name}')
        tray, plate = hf.tray(), hf.plate3d()
        write_stl(os.path.join(OUT, 'print', f'{side}-tray.stl'), tray)
        write_stl(os.path.join(OUT, 'print', f'{side}-plate.stl'), hf.plate3d_printed())   # all-printed variant
        write_stl(os.path.join(OUT, 'print', f'{side}-wheel.stl'), hf.wheel3d())
        write_stl(os.path.join(OUT, 'print', f'{side}-detent.stl'), hf.detent_part())   # acrylic variant only
        write_stl(os.path.join(OUT, 'print', f'{side}-wheel-cap.stl'), hf.wheel_cap())   # 3D-print variant
        write_stl(os.path.join(OUT, 'print', f'{side}-port-caps.stl'), hf.port_caps())   # 3D-print variant
        write_stl(os.path.join(OUT, 'preview', f'{side}-oled-cover.stl'), Manifold.extrude(hf.cover(), COVER_T))
        # assembly preview (print variant): tray + PCB + plate in place
        z_pcb = FLOOR + STANDOFF
        write_stl(os.path.join(OUT, 'preview', f'{side}-pcb.stl'), hf.pcb3d().translate((0, 0, z_pcb)))
        write_stl(os.path.join(OUT, 'preview', f'{side}-plate-placed.stl'),
                  plate.translate((0, 0, z_pcb + PCB_T + PLATE_GAP)))
        ox0, oy0, ox1, oy1, _ = hf.outer_box
        report[side] = dict(case_mm=[round(ox1 - ox0, 1), round(oy1 - oy0, 1)],
                            height_print=round(FLOOR + STANDOFF + PCB_T + PLATE_GAP + PLATE_T, 2),
                            height_acrylic=BOTTOM_T + N_FRAMES * FRAME_T + PLATE_T,
                            screws=len(hf.screws), screws_xy=[[round(float(x), 3), round(float(y), 3)] for x, y in hf.screws], pcb_holes=len(hf.d['holes']),
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
        hole = hf.port_hole(s, FLOOR + STANDOFF).project()
        assert (hole - hf.outer).area() > 0.5, f"{s['name']} opening does not reach the outside"
        assert (s['chan'] - hf.outer.offset(-hf.d.get('port_skin', 0.8) + 0.01)).area() < 0.01, f"{s['name']} tongue breaks the skin"
        for x, y in hf.screws:
            assert not inside(s['cap'].offset(2.0, JoinType.Miter), (x, y)), f"screw in the {s['name']} port cap"
    for name, cs in layers.items():
        assert not cs.is_empty(), name

    def area(poly):
        return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2
    # OLED: window clear of switch cut-outs, cover clear of switch tops and fully supported by the plate
    win = hf.window_cs()
    keys = CrossSection()
    for k in hf.d['keys']:
        h = SWITCH_CUT / 2 + 1.0
        keys = keys + rect(k['cx'] - h, k['cy'] - h, k['cx'] + h, k['cy'] + h)
    assert (win ^ keys).area() < 0.01, 'OLED window too close to a switch'
    assert (win - hf.cover_shape()).area() < 0.01, 'cover does not span the OLED window'
    assert (hf.cover_shape() ^ hf.switch_tops()).area() < 0.01, 'cover hits a switch'
    assert (hf.cover_shape() - hf.outer.offset(-COVER_MARGIN + 0.01)).area() < 0.01, 'cover leaves the case outline margin'

    # wheel: clear of standoffs, screws and the OLED; its rim must leave the case outline at the corner
    (wx, wy), wr = hf.wheel_xy()
    for x, y in hf.d['holes']:
        assert math.hypot(x - wx, y - wy) > wr + WHEEL_CUT + BOSS_D / 2, 'wheel hits a standoff'
    for x, y in hf.screws:
        assert math.hypot(x - wx, y - wy) > wr + WHEEL_CUT + SCREW_D / 2 + 0.8, 'wheel hits a case screw'
    assert (hf.wheel_cut(0) - hf.outer).area() > 20, 'wheel does not stick out of the corner'
    # plunger block: inside the cavity, clear of the standoffs, the reset hole and the wheel; hole within the teeth band
    block, zc = hf.detent_block(FLOOR)
    foot = block.project()
    assert (foot - hf.inner.offset(-0.5, JoinType.Round)).area() < 0.01, 'plunger block leaves the floor'
    for x, y in hf.d['holes'] + [tuple(hf.d['reset'])]:
        assert (foot ^ circle(x, y, BOSS_D + 1.0)).area() < 0.01, 'plunger block hits a standoff / reset hole'
    wheel = hf.wheel3d().translate((0, 0, FLOOR + WHEEL_GAP))
    assert (wheel ^ block).volume() < 1e-3, 'plunger block collides with the wheel'
    assert FLOOR + WHEEL_GAP + 0.8 < zc < FLOOR + WHEEL_GAP + WHEEL_T - 0.8, 'plunger misses the teeth'

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
