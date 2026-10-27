"""Generate the enclosure for each half from <side>/case_data.json.

Two variants share one geometry:
  * laser  - acrylic sandwich: bottom 3 mm + 4 frames x 3 mm + switch plate 1.5 mm  (DXF / SVG)
  * print  - 3D printed tray (floor + walls + bosses) + printed plate                (STL)

Heights (z, mm, bottom of case = 0)
  acrylic : bottom 0-3 | frames 3-15 | PCB 10.0-11.6 on 7 mm M2 standoffs | plate 15-16.5
  print   : floor 0-2  | walls 2-14.1 | PCB 9.0-10.6 on 7 mm bosses       | plate 14.1-15.6
MX spec: plate top to PCB top = 5.0 mm -> plate bottom 3.5 mm above the PCB.
Both USB-C receptacles (host and split link) sit on the back of the PCB, so the plugs pass below the PCB: the switch plate and
the top frame stay closed, only the wall below the PCB is opened.

Run with the project venv:  .venv/bin/python gen/make_case.py
"""
import json
import math
import os
import struct
import sys

from manifold3d import CrossSection, JoinType, Manifold, OpType, set_circular_segments

from footprints import DRUM_D, DRUM_GAP, DRUM_W

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
STANDOFF = 7.0       # PCB bottom above case floor (room for the USB-C plugs under the PCB)
# acrylic
BOTTOM_T = 3.0
FRAME_T = 3.0
N_FRAMES = 4
# connector ports: the PCB reaches into the wall on a tongue, the connector mouth sits PORT_SKIN inside the outer
# surface, and the wall shows only the connector outline. In the printed tray each port is a closed tunnel with
# PORT_LIFT of headroom over the tongue: the board goes in front edge slightly raised and PORT_LIFT high, slides
# tongue-first into the tunnels, then drops onto the bosses. In the acrylic stack the frames are notched.
USB_SHELL = (8.94, 3.26)     # HRO TYPE-C-31-M-12 shell w, h (hangs under the PCB); both ports use it
PORT_CLR = 0.2               # opening around the connector outline
CHANNEL_CLR = 0.3            # tongue / connector body to the tunnel
PORT_KEEP = 3.0              # case screws stay this far beyond the tunnel along the wall
PORT_LIFT = 2.0              # tunnel headroom: the board slides in this high, clear of the bosses (needs >= 1.5)
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
BUTTON_HOLE = 4.5            # plate hole for a tall tact switch's actuator (3.5 mm) poking through (encoder test board)
BUTTON_KEEP = 3.6            # printed plate's web kept off the 6 mm switch body (half size)
# 3D print: the wall above the wheel opening is a separate cap, so the wheel can be dropped in from above
CAP_SHOULDER = 2.0           # cap's top tier overhangs the opening by this much and rests on the wall
CAP_LEDGE = 3.0              # thickness of that top tier
CAP_FIT = 0.15
RIB_T = 2.0                  # all-printed variant: web under the printed plate (PCB top + 1.5)
TRAY_FILLET = 2.0     # 3D-printed tray: rounded bottom outer edge
TRAY_TOP_FILLET = 0.6 # small round on the top outer edge, under the plate
# rubber feet (3M CS-02, 9.5 x 3.8 mm) sit in round recesses under the tray (docs/specs/case-feet-tilt.md): near the
# corners, clear of the screw counterbores (the plate comes off without peeling a foot), the boss pilot holes, the
# reset hole and the corner wheel
FOOT_D = 10.0         # recess diameter (0.25 mm radial play round the foot)
FOOT_DEPTH = 1.0      # leaves a 1.0 mm floor; the foot stands 2.8 mm proud
FOOT_INSET = 8.0      # outline corner -> recess centre, first try
FOOT_KEEP = 1.0       # recess edge to counterbores, pilot holes, the reset hole and the wheel
FOOT_STEP = 0.5       # a blocked recess slides along the edge toward the middle in these steps
FOOT_H = 3.8          # the foot's height: it stands FOOT_PROUD below the tray bottom
FOOT_PROUD = FOOT_H - FOOT_DEPTH
# tilt stand (docs/specs/case-feet-tilt.md): a separate printed U along the back edge and both sides, its top sloped by
# the angle; the back three feet drop into pockets in it, the front two stay on the desk. One stand per angle.
STAND_ANGLES = (3, 6, 9)
STAND_W = 16.0        # band width in from the outline: the feet (8 mm in, 9.5 mm across) sit on it with 3 mm spare
STAND_POCKET = (10.1, 2.0)   # feet pockets: d, depth (0.8 mm left between the tray bottom and the stand top)
STAND_PAST = 15.0     # the side arms run this far toward the front past the foot beside the wheel
STAND_FILLET = TRAY_FILLET   # round on the stand's top edges: the same as the tray's bottom edge sitting on it
STAND_FLOOR = 1.5     # thinnest stand under a pocket
BED = 220.0           # printer bed, as for the tray (Ender-3, Bambu Lab A1 / P1 / X1, Prusa MK4)
PLATE_FILLET = 1.0    # all-printed plate: rounded top outer edge (prints fine top-down: 1 mm reach on the bed side)
SWITCH_CUT = 14.0
# OLED: window in the switch plate, filled by a half-mirror acrylic cover flush with the plate top. Half-mirror
# acrylic starts at 2 mm, so the cover reaches 0.5 mm below the 1.5 mm plate; it rests on the module's glass
# (soldered low, glass top 2.5 mm above the PCB) and is held by 0.5 mm clear double-sided tape. No screws,
# so the plate keeps its closed outer edge.
OLED_WINDOW_CLEAR = 0.15     # added to the module courtyard (courtyard = module + 0.25)
COVER_T = 2.0                # half-mirror acrylic; top flush with the plate top
COVER_FIT = 0.1              # cover edge to plate opening
COVER_BORDER = 5.0           # cover: at least this much wider than the OLED window on both sides
COVER_FRAME = 5.5            # plate band round the cover, the same on every side: to the case outline (top and
                             # inner edge) and to the keycaps (keys side and below); = make_pcb COVER_FRAME
COVER_END = 1.5              # at least this much cover past both ends of the module (header end included)
COVER_BELOW = 2.5            # the band below the cover, to the row-2 keycap, may narrow to this
COVER_MARGIN = 3.0           # cover stays at least this far inside the case outline
WALL_POCKET = 0.5            # 3D print: wall top lowered under the cover (cover 2 mm vs plate 1.5 mm)
TAPE_T = 0.5                 # clear double-sided tape between glass and cover
OLED_GLASS_TOP = PLATE_GAP + PLATE_T - COVER_T - TAPE_T   # = 2.5: glass top above the PCB top
SWITCH_TOP_KEEPOUT = 8.4     # half size of an MX top housing (15.6 mm) + 0.6 mm
# corner thumbwheel: lies under the PCB, rim out of the corner. An Alps EC05E1220401 (hollow-shaft encoder,
# 12 detents) hangs from the PCB back on the wheel axis; a hex pin on the wheel top drives its rotor, and the
# clicks come from the encoder. The thumb's side force is taken by the floor post (acrylic: an M3 screw), which
# has radial play, so the board-to-tray tolerance does not bind the wheel between post and encoder.
WHEEL_T = 4.1
WHEEL_GAP = 0.3              # wheel bottom above the floor / bottom plate
WHEEL_CUT = 0.6              # radial clearance of the wall opening
WHEEL_KNURLS = 32            # rounded teeth on the rim: the grip
TOOTH_DEPTH = 0.5            # valley depth of the rim teeth
BORE_D, BORE_DEPTH = 4.0, 2.0          # axle bore from below
POST_D = 3.6                 # printed axle post (3D print variant): 0.2 mm radial play in the bore
AXLE_HOLE_D = 3.2            # M3 axle screw through the bottom plate (acrylic variant)
# Alps EC05E1220401 (catalog drawing No.3): body 5.7 wide (7.6 over the side tabs), 2.5 / 3.7 from the rotor
# axis, 2.7 below the PCB back; hex hole 1.72 A/F through the rotor, entered from the wheel side
ENC_W, ENC_TAB_W, ENC_UP, ENC_DOWN, ENC_H = 5.7, 7.6, 2.5, 3.7, 2.7
ENC_HEX_AF, ENC_ROTOR_D = 1.72, 2.2
HUB_R = 6.0                  # wheel top lowered within this radius: clears the body, tabs and terminals
HUB_CLEAR = 0.3              # encoder body to the lowered hub
PIN_AF = 1.66                # hex pin across flats: tune on a test print (play vs. fit)
PIN_ENGAGE = 2.0             # pin length inside the rotor
PIN_CHAMFER = 0.25
STAB_CUT = (7.0, 15.4, 0.5)   # w, h, centre y offset (down) of each stabilizer housing cut-out
STAB_X = 11.938
# drum dial (right half, docs/specs/drum-dial.md). Local frame: origin = Alps EC10E footprint origin (rotor axis
# projected onto the board at the encoder's shaft-insert face, from case_data 'drum'), +x along the axis toward
# the drum, y across (board y), z above the PCB top. The drum spins between the encoder rotor (hex pin) and a
# printed bearing block on the PCB (round pin in a snap-in U slot); a printed bezel clipped into a plate opening
# hoods the encoder and the block and holds the block down.
EC10_AXIS = 7.0                       # EC10E1220505: axis 7 mm above the board
EC10_BRACKET = (-6.1, -4.9, 0.0, 4.9, 2.0)    # metal bracket: x0, y0, x1, y1, top z
EC10_BODY = (-5.15, -4.9, -0.65, 4.9, EC10_AXIS + 3.6)   # upper body (top 3.6 above the axis)
EC10_ROTOR_FACE = -1.3                # hex hole entrance (1.73 A/F, 1.7 deep, then a 2.2 mm bore)
EC10_HEX_DEPTH = 1.7
DRUM_GROOVES, DRUM_GROOVE_DEPTH, DRUM_HELIX = 36, 0.4, 30.0   # diagonal knurl: rounded grooves, helix angle
DRUM_CHAMFER = 0.5
DRUM_PIN_ENGAGE = 1.6                 # hex pin length inside the rotor (<= EC10_HEX_DEPTH)
DRUM_ROUND_PIN = (2.0, 2.5)           # bearing end: diameter, length
BLOCK_T, BLOCK_HALF_W = 3.0, 3.5      # bearing block: thickness along the axis, half width across
BLOCK_R = 1.0                         # bearing block: radius of the top corners (seen along the axis)
BLOCK_TOP = EC10_AXIS + 1.5
BLOCK_SLOT_R, BLOCK_LIP = 1.1, 1.8    # slot radius around the round pin, snap-in mouth width
BLOCK_PEG = (1.9, 1.4)                # pegs into the 2.0 mm NPTH: diameter, length
PLATE_TOP_Z = PLATE_GAP + PLATE_T     # plate top above the PCB top (5.0)
DRUM_OPENING = (-7.1, -7.6, 2 * DRUM_GAP + DRUM_W + BLOCK_T + 0.6, 7.6, 1.0)   # plate opening: x0, y0, x1, y1, corner r
# the bezel's flange sits in a plate hole of its own outline, flush with the plate top (like the OLED cover); a
# ledge under the plate keeps it from lifting, the block hood's roof on the block and a leg under the encoder
# hood's far wall on the PCB carry it down
BEZEL_BORDER, BEZEL_R = 1.5, 2.3      # flange: beyond the opening, corner r (= the hoods' outer r)
BEZEL_FIT = 0.1                       # flange to the plate hole, all round
BEZEL_LEDGE, BEZEL_LEDGE_T = 1.0, 0.8  # ledge under the plate: beyond the flange, thickness
BEZEL_LEG_HW = 3.0                    # encoder-side leg down to the PCB: half width across the axis
BEZEL_WALL, BEZEL_CLEAR = 1.0, 0.3
HOOD_IN_R = 0.8                       # both hoods: inner radius of the top corners (clears the encoder's square edges)
HOOD_OUT_R = BLOCK_R + BEZEL_CLEAR + BEZEL_WALL   # both hoods: outer radius (2.3), concentric with the block's corners
BEZEL_FILLET = 1.2                    # concave fillet where each hood meets the flange
BEZEL_FLAT = 0.8                      # flat flange left beyond the fillet's foot at the short ends


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


def hull(pts):
    """Convex hull (monotone chain), counter-clockwise taking the coordinates as they are (y up)."""
    pts = sorted(set(pts))

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1]) -
                                     (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]
    return half(pts) + half(pts[::-1])


def hull_margin(poly, p):
    """Distance from p in to the nearest edge of the convex polygon poly (from hull()); negative outside."""
    m = math.inf
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        m = min(m, ((x1 - x0) * (p[1] - y0) - (y1 - y0) * (p[0] - x0)) / math.hypot(x1 - x0, y1 - y0))
    return m


def stand_pose(deg, front_y, lift=0.0):
    """Tray frame -> world (3 x 4 affine) of a half on a tilt stand: raised by deg about the front feet's contact line
    (board y front_y, FOOT_PROUD under the tray bottom), that line on the desk (z = 0), then lifted by lift."""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    yp, zp = -front_y, -FOOT_PROUD
    return [[1, 0, 0, 0],
            [0, c, -s, yp - c * yp + s * zp],
            [0, s, c, zp - s * yp - c * zp + FOOT_PROUD + lift]]


def affine_inverse(m):
    """Inverse of a rigid 3 x 4 affine."""
    r = [[m[j][i] for j in range(3)] for i in range(3)]
    t = [-sum(r[i][j] * m[j][3] for j in range(3)) for i in range(3)]
    return [r[i] + [t[i]] for i in range(3)]


def hexagon(af, h):
    """Hexagonal prism (across flats af), axis on z from 0 to h."""
    r = af / math.sqrt(3)
    return Manifold.extrude(CrossSection([[(r * math.cos(math.radians(60 * i)), r * math.sin(math.radians(60 * i)))
                                            for i in range(6)]]), h)


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
        self.window_box = self._oled() if 'oled' in self.d else None   # the encoder test board has no OLED
        self.cover_screws = self._cover_screws()
        # perimeter screws under the cover or in the plate band right next to it go (the cover has no screws of
        # its own): a screw head beside the rounded cover corner would spoil the even band
        cov = self.cover_shape().offset(COVER_FRAME + 2.0, JoinType.Round)
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
            e = PORT_KEEP
            if edge == 'top':
                a0, a1 = t[0] - CHANNEL_CLR - e, t[2] + CHANNEL_CLR + e
                cap = rect(a0, oy0 - 1, a1, self.pcb[1] - CLEAR + 0.01) ^ (self.outer - self.inner)
                full = (a0, oy0 - 1, a1, self.pcb[1])
                out.append(dict(name=name, edge='top', x=(t[0] + t[2]) / 2, half=(a1 - a0) / 2, full=full,
                                chan=chan, cap=cap, along=(t[0] + t[2]) / 2, conn=c))
            else:
                a0, a1 = t[1] - CHANNEL_CLR - e, t[3] + CHANNEL_CLR + e
                if self.inner_right:
                    cap = rect(self.pcb[2] + CLEAR - 0.01, a0, ox1 + 1, a1) ^ (self.outer - self.inner)
                    full = (self.pcb[2], a0, ox1 + 1, a1)
                else:
                    cap = rect(ox0 - 1, a0, self.pcb[0] - CLEAR + 0.01, a1) ^ (self.outer - self.inner)
                    full = (ox0 - 1, a0, self.pcb[0], a1)
                out.append(dict(name=name, edge='inner', y=(t[1] + t[3]) / 2, half=(a1 - a0) / 2, full=full,
                                chan=chan, cap=cap, along=(t[1] + t[3]) / 2, conn=c))
        # neighbouring ports on the top edge share one screw-free zone
        tops = sorted((sl for sl in out if sl['edge'] == 'top'), key=lambda sl: sl['full'][0])
        for a, b in zip(tops, tops[1:]):
            if b['full'][0] - a['full'][2] < 2 * PORT_KEEP:
                full = (a['full'][0], a['full'][1], b['full'][2], a['full'][3])
                cap = rect(full[0], full[1], full[2], self.pcb[1] - CLEAR + 0.01) ^ (self.outer - self.inner)
                for sl in (a, b):
                    sl.update(full=full, cap=cap, half=(full[2] - full[0]) / 2)
        return out

    def port_z(self, port, z_pcb):
        """(bottom of the connector, centre of its opening, opening height) for a PCB bottom at z_pcb. Both ports
        are the same USB-C receptacle, so both openings sit at the same height. A connector in case_data may give
        its own 'z' (bottom and opening centre below the PCB bottom, opening height; the encoder test board's
        RP2040-Zero hangs lower)."""
        if 'z' in port['conn']:
            zb, zc, h = port['conn']['z']
            return z_pcb - zb, z_pcb - zc, h + 2 * PORT_CLR
        return z_pcb - USB_SHELL[1], z_pcb - USB_SHELL[1] / 2, USB_SHELL[1] + 2 * PORT_CLR

    def port_hole(self, port, z_pcb):
        """The visible opening: connector outline + PORT_CLR (a rounded slot), through the skin in front of the
        mouth, on the top edge or on the inner edge (encoder test board)."""
        _, zc, hh = self.port_z(port, z_pcb)
        ox0, oy0, ox1, oy1, _ = self.outer_box
        depth = self.d.get('port_skin', 0.8) + 1.0
        w, h = port['conn'].get('width', USB_SHELL[0]) + 2 * PORT_CLR, hh
        r = h / 2
        cs = CrossSection.square((w - 2 * r, 0.001), center=True).offset(r, JoinType.Round)
        m = Manifold.extrude(cs, depth + 1).rotate((-90, 0, 0))        # along +y (3D) = outward on the top edge
        if port['edge'] == 'top':
            return m.translate((port['along'], -oy0 - depth, zc))
        if self.inner_right:                                           # outward = +x
            return m.rotate((0, 0, -90)).translate((ox1 - depth, -port['along'], zc))
        return m.rotate((0, 0, 90)).translate((ox0 + depth, -port['along'], zc))

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

    def keycaps(self):
        """Keycap outlines seen from above (18 mm keycaps on the 19.05 mm grid): (x0, y0, x1, y1) per key."""
        ins = (19.05 - 18.0) / 2
        return [(k['cx'] - k['w'] * 19.05 / 2 + ins, k['cy'] - k['h'] * 19.05 / 2 + ins,
                 k['cx'] + k['w'] * 19.05 / 2 - ins, k['cy'] + k['h'] * 19.05 / 2 - ins) for k in self.d['keys']]

    def cover_box(self):
        """Half-mirror inlay round the OLED window, with a plate band of COVER_FRAME on every side: to the case
        outline at the top and on the inner edge, to the nearest keycaps on the keys side, and to the top line of
        the keycap row below. Returns (x0, y0, x1, y1) and the outer-top corner."""
        wx0, wy0, wx1, wy1 = self.window_box
        ox0, oy0, ox1, oy1, _ = self.outer_box
        f, m = COVER_FRAME, COVER_BORDER
        top = oy0 + f
        caps = self.keycaps()
        rows = [c for c in caps if c[1] < wy1 + COVER_END and c[3] > top]  # keycaps level with the cover
        if self.inner_right:
            x1 = ox1 - f
            x0 = max(c[2] for c in rows if c[2] <= wx0) + f
        else:
            x0 = ox0 + f
            x1 = min(c[0] for c in rows if c[0] >= wx1) - f
        # bottom: COVER_END past the module's header end (the OLED is placed so its display is the cover's centre);
        # the band to the row-2 keycap below is narrower there (right half: the Y key), at least COVER_BELOW
        y1 = wy1 + COVER_END
        m -= 0.1    # the window comes from the courtyard's bounding box, which carries its 0.05 mm line width
        # along the module the cover only has to hide its ends (the display glass, 3 mm toward the top, is centred)
        assert x0 <= wx0 - m and x1 >= wx1 + m and top <= wy0 - COVER_END and y1 >= wy1 + COVER_END - 1e-9, \
            f'{self.side}: no room for COVER_BORDER round the OLED window'
        return (x0, top, x1, y1), ('tr' if self.inner_right else 'tl')

    def cover_shape(self):
        """The cover: rectangle from cover_box() with the same radius on all four corners: the one at the case
        corner is concentric with the case outline, so the plate band keeps its width round it."""
        if self.window_box is None:
            return CrossSection()
        (x0, y0, x1, y1), outer = self.cover_box()
        rc = self.outer_box[4] - COVER_FRAME
        cs = rect(x0, y0, x1, y1)
        for name, (cx, cy, sx, sy) in {'tl': (x0, y0, 1, 1), 'tr': (x1, y0, -1, 1),
                                       'br': (x1, y1, -1, -1), 'bl': (x0, y1, 1, -1)}.items():
            r = rc
            px, py = cx + sx * r, cy + sy * r          # corner circle centre
            cs = cs - rect(min(cx, px), min(cy, py), max(cx, px), max(cy, py)) + circle(px, py, 2 * r)
        return cs

    def _cover_screws(self):
        """The cover is held by clear double-sided tape (on the OLED glass and the wall ledge), not screws."""
        return []

    def cover(self):
        return self.cover_shape() - self.holes(self.cover_screws, SCREW_D)

    def _reset_cut(self, d):
        return circle(*self.d['reset'], d) if 'reset' in self.d else CrossSection()

    # rubber feet under the tray ----------------------------------------------------------
    def foot_keepout(self):
        """What a foot recess must stay FOOT_KEEP away from: counterbores, boss pilot holes, the reset hole, the wheel
        (its disc and wall opening, the axle post inside)."""
        cs = self.holes(self.screws, SCREW_CB[0]) + self.holes(self.d['holes'], PILOT_D) + self._reset_cut(RESET_D)
        return cs + self.wheel_cut() if 'wheel' in self.d else cs

    def foot_fits(self, p):
        x, y = p
        if (circle(x, y, FOOT_D + 2 * (TRAY_FILLET + 0.5)) - self.outer).area() > 1e-6:   # off the bottom fillet
            return False
        return (circle(x, y, FOOT_D + 2 * FOOT_KEEP) ^ self.foot_keepout()).area() < 1e-6

    def feet(self):
        """Foot recess centres (board coordinates). One per corner: it starts FOOT_INSET in from the outline corner
        and slides along the back / front edge toward the middle until it fits. The wheel fills its corner, so that
        foot ends up well along the back edge; a fifth foot slides down the outer side edge instead, so the corner
        keys stay inside the feet. The encoder test board (built from a keyboard half, case_data 'source') keeps a
        plain floor."""
        if 'source' in self.d:
            return []
        if not hasattr(self, '_feet'):
            ox0, oy0, ox1, oy1, _ = self.outer_box

            def slide(x, y, dx, dy):
                while not self.foot_fits((x, y)):
                    x, y = x + dx, y + dy
                    assert ox0 < x < ox1 and oy0 < y < oy1, 'no room for a foot'
                return x, y
            pts = [slide(x, y, step, 0) for y in (oy0 + FOOT_INSET, oy1 - FOOT_INSET)
                   for x, step in ((ox0 + FOOT_INSET, FOOT_STEP), (ox1 - FOOT_INSET, -FOOT_STEP))]
            if 'wheel' in self.d:
                (wx, _), _ = self.wheel_xy()
                x = ox0 + FOOT_INSET if wx < (ox0 + ox1) / 2 else ox1 - FOOT_INSET
                pts.append(slide(x, oy0 + FOOT_INSET, 0, FOOT_STEP))
            self._feet = pts
        return self._feet

    def front_y(self):
        """Board y of the front feet (the line the half tilts about on a stand)."""
        return max(y for _, y in self.feet())

    def stand(self, deg, ring=False, lift=0.0):
        """Tilt stand for deg (tray frame, under the tray): the band along the outline, its top STAND_POCKET above the
        feet's bottoms with the top edges rounded, cut at the desk, pockets for the feet it carries. The U (default)
        runs along the back edge and down both sides STAND_PAST past the foot beside the wheel; ring = the whole
        outline (tilt study), with the front lifted by lift."""
        key = (deg, ring, lift)
        if key in getattr(self, '_stands', {}):
            return self._stands[key]
        band = self.outer - self.outer.offset(-STAND_W, JoinType.Round)
        feet = self.feet()
        if not ring:
            ox0, oy0, ox1, oy1, _ = self.outer_box
            y_cut = -(feet[4][1] + STAND_PAST)                 # tray frame
            band = band ^ CrossSection.square((ox1 - ox0 + 2, -oy0 - y_cut + 1)).translate((ox0 - 1, y_cut))
            feet = [f for f in feet if -f[1] > y_cut]
        # printed bottom down, pockets up: straight walls, the top edges rounded by stacked offset slices
        top, r, n = -FOOT_PROUD + STAND_POCKET[1], STAND_FILLET, 8
        m = Manifold.extrude(band, 200.0 - r).translate((0, 0, top - 200.0))
        for i in range(n):
            za, zb = top - r + r * i / n, top - r + r * (i + 1) / n
            zm = (za + zb) / 2 - (top - r)
            inset = r - math.sqrt(max(r * r - zm * zm, 0.0))
            m = m + Manifold.extrude(band.offset(-inset, JoinType.Round), zb - za + 0.001).translate((0, 0, za))
        desk = Manifold.cube((1000, 1000, 500)).translate((-500, -500, 0)).transform(
            affine_inverse(stand_pose(deg, self.front_y(), lift)))
        m = m ^ desk
        d, depth = STAND_POCKET
        for x, y in feet:
            m = m - Manifold.cylinder(depth + 0.01, d / 2, d / 2, 64).translate((x, -y, -FOOT_PROUD))
        self._stands = {**getattr(self, '_stands', {}), key: (m, feet)}
        return m, feet

    def plugs3d(self):
        """USB-C plugs in the back-edge ports (tray frame): 12.5 x 7 mm, 25 mm out of the wall."""
        oy0 = self.outer_box[1]
        z = FLOOR + STANDOFF - 1.7
        return [Manifold.cube((12.5, 25.0, 7.0)).translate((c['center'][0] - 6.25, -oy0 - 2.0, z - 3.5))
                for c in self.d['connectors'].values() if c.get('edge') == 'top']


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
        if 'drum' in self.d:
            cut = cut + self.bezel_outline(BEZEL_FIT)
        cut = cut + self.extra_cuts()
        return self.outer - cut - self.cover_shape().offset(COVER_FIT, JoinType.Round) - self.holes(self.screws, SCREW_D)

    def extra_cuts(self):
        """Encoder test board: holes for the tact switches' actuators."""
        return self.holes(self.d.get('buttons', []), BUTTON_HOLE)

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
        cs = self.outer - self.holes(self.screws, SCREW_D) - self.holes(self.d['holes'], SCREW_D) - circle(wx, wy, AXLE_HOLE_D)
        return cs - self._reset_cut(RESET_D)

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
        if self.window_box is not None:
            body = body - Manifold.extrude(self.cover_shape().offset(COVER_FIT, JoinType.Round), WALL_POCKET + 0.01).translate(
                (0, 0, wall_top - WALL_POCKET))
        # port tunnels: closed above, with headroom so the board can slide in tongue-first
        z_pcb = FLOOR + STANDOFF
        for p in self.slots:
            zp = self.port_z(p, z_pcb)[0] - 0.2
            zt = z_pcb + PCB_T + CHANNEL_CLR + PORT_LIFT
            if p['conn'].get('open_top'):       # encoder test board: the board drops in, the plate closes the top
                zt = wall_top + 0.1
            body = body - Manifold.extrude(p['chan'], zt - zp).translate((0, 0, zp)) - self.port_hole(p, z_pcb)
        body = body + Manifold.cylinder(WHEEL_GAP + BORE_DEPTH - 0.3, POST_D / 2, POST_D / 2, 48).translate(
            (wx, -wy, FLOOR))
        if 'reset' in self.d:
            rx, ry = self.d['reset']
            body = body - Manifold.cylinder(FLOOR + 0.02, RESET_D / 2, RESET_D / 2).translate((rx, -ry, -0.01))
        for x, y in self.feet():
            body = body - Manifold.cylinder(FOOT_DEPTH + 0.01, FOOT_D / 2, FOOT_D / 2).translate((x, -y, -0.01))
        return body

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

    def wheel_cap(self):
        if not hasattr(self, '_cap'):
            self.tray()
        return self._cap

    def wheel3d(self):
        """Knurled thumbwheel (printable): bore from below; on top a lowered hub under the encoder and the hex pin
        that drives the encoder's rotor. z = 0 is the wheel bottom."""
        (x, y), r = self.wheel_xy()
        pts = []
        n = WHEEL_KNURLS * 12
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = r - TOOTH_DEPTH * (1 - math.cos(WHEEL_KNURLS * a)) / 2      # rounded teeth, crests at r
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        rim = cs_poly(pts)
        w = Manifold.extrude(rim, WHEEL_T)
        w = w - Manifold.cylinder(BORE_DEPTH, BORE_D / 2, BORE_D / 2, 48).translate((x, -y, 0))
        hub, pin_len = self.hub_top() - WHEEL_GAP, PIN_ENGAGE + HUB_CLEAR
        w = w - Manifold.cylinder(WHEEL_T, HUB_R, HUB_R, 96).translate((x, -y, hub))
        corner = PIN_AF / math.sqrt(3)
        pin = hexagon(PIN_AF, pin_len) ^ Manifold.cylinder(pin_len, corner, PIN_AF / 2 - PIN_CHAMFER, 24)
        return w + pin.translate((x, -y, hub))

    @staticmethod
    def enc_bottom():
        """Encoder's wheel-side face (rotor hole entrance) above the floor / bottom plate."""
        return STANDOFF - ENC_H

    def hub_top(self):
        return self.enc_bottom() - HUB_CLEAR

    def encoder3d(self, z_base):
        """EC05E1220401 hanging from the PCB back (floor / bottom plate top at z_base), terminals toward the board
        inside (board +y), as placed by make_pcb.py. A few boxes, for the checks and the viewer."""
        (x, y), _ = self.wheel_xy()
        body = CrossSection.circle(ENC_W / 2) ^ CrossSection.square((ENC_W, ENC_UP * 2), center=True)
        body = body + CrossSection.square((ENC_W, ENC_DOWN)).translate((-ENC_W / 2, -ENC_DOWN))
        m = Manifold.extrude(body, ENC_H - 0.15).translate((0, 0, 0.15))
        for sx in (-1, 1):   # metal side tabs, soldered to the big lands
            m = m + Manifold.cube(((ENC_TAB_W - ENC_W) / 2, 1.6, ENC_H - 0.6)).translate(
                (ENC_W / 2 if sx > 0 else -ENC_TAB_W / 2, -0.8, 0.6))
        m = m + Manifold.cylinder(ENC_H, ENC_ROTOR_D / 2 + 0.25, ENC_ROTOR_D / 2 + 0.25, 48)
        m = m - hexagon(ENC_HEX_AF, ENC_H + 0.2).translate((0, 0, -0.1))
        for i in (-1, 0, 1):  # A, C, B terminals
            m = m + Manifold.cube((0.5, 0.9, 0.2)).translate((i * 2.0 - 0.25, -ENC_DOWN - 0.9, ENC_H - 0.2))
        return m.translate((x, -y, z_base + self.enc_bottom()))

    # drum dial ---------------------------------------------------------------------
    def _dl(self, x, y):
        """Drum local (x along the axis, y across) -> board coordinates."""
        ox, oy = self.d['drum']['origin']
        return ox + x, oy + y

    def _dbox(self, x0, y0, z0, x1, y1, z1):
        """Box in the drum's local frame (z above the PCB top)."""
        bx0, by0 = self._dl(x0, y0)
        return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((bx0, -(by0 + y1 - y0), z0))

    def _daxis(self, m, x):
        """Place a solid built along +x on the drum axis, its x = 0 at local x."""
        bx, by = self._dl(x, 0)
        return m.translate((bx, -by, EC10_AXIS))

    @staticmethod
    def _along_x(m):
        return m.rotate((0, 90, 0))

    def drum_opening(self, grow=0.0):
        x0, y0, x1, y1, r = DRUM_OPENING
        (bx0, by0), (bx1, by1) = self._dl(x0, y0), self._dl(x1, y1)
        return rounded_rect(bx0 - grow, by0 - grow, bx1 + grow, by1 + grow, r + grow)

    def bezel_outline(self, grow=0.0):
        """The bezel's flange in plan (the plate hole is this grown by BEZEL_FIT)."""
        x0, y0, x1, y1, _ = DRUM_OPENING
        bb = BEZEL_BORDER
        # the short ends leave a flat strip beyond the foot of the hood fillets
        hx0, hx1 = self._hood_ends()
        reach = BEZEL_FILLET + BEZEL_FLAT
        x0, x1 = min(x0 - bb, hx0 - reach), max(x1 + bb, hx1 + reach)
        (bx0, by0), (bx1, by1) = self._dl(x0 - grow, y0 - bb - grow), self._dl(x1 + grow, y1 + bb + grow)
        return rounded_rect(bx0, by0, bx1, by1, BEZEL_R + grow)

    def _hood_ends(self):
        """Local x of the outer faces at the far ends of the encoder hood and the block hood. The block hood is as
        long as the encoder hood (drum-side face 0.2 mm off the encoder face, as the block hood's off the block)."""
        e_end = EC10_BRACKET[0] - BEZEL_CLEAR - BEZEL_WALL
        return e_end, self._block_x()[0] - 0.1 + (0.2 - e_end)

    def bezel_ledge(self):
        """The bezel's ledge under the plate in plan, notched round the PCB screw heads like the printed web."""
        return self.bezel_outline(BEZEL_LEDGE) - self.holes(self.d['holes'], BOSS_D + 2.0)

    def ec10e3d(self):
        """EC10E body as a few boxes (checks and viewer); bore along the axis for the drum's hex pin."""
        x0, y0, x1, y1, zt = EC10_BRACKET
        m = self._dbox(x0, y0, 0, x1, y1, zt)
        x0, y0, x1, y1, zt = EC10_BODY
        m = m + self._dbox(x0, y0, EC10_BRACKET[4], x1, y1, zt)
        m = m + self._daxis(self._along_x(Manifold.cylinder(-0.6 - EC10_ROTOR_FACE, 1.8, 1.8, 48)), EC10_ROTOR_FACE)
        bore = self._along_x(Manifold.cylinder(8.0, 1.1, 1.1, 32))
        return m - self._daxis(bore, -7.0)

    def drum3d(self):
        """Knurled drum: hex pin into the encoder rotor on the -x end, round pin into the block on the +x end."""
        r = DRUM_D / 2
        n = DRUM_GROOVES * 12
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = r - DRUM_GROOVE_DEPTH * (1 - math.cos(DRUM_GROOVES * a)) / 2
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        twist = math.degrees(DRUM_W * math.tan(math.radians(DRUM_HELIX)) / r)
        body = Manifold.extrude(CrossSection([pts]), DRUM_W, 48, twist)
        c = DRUM_CHAMFER
        env = (Manifold.cylinder(c, r - c, r + 0.01, 96) + Manifold.cylinder(DRUM_W - 2 * c, r + 0.01, r + 0.01, 96).translate((0, 0, c))
               + Manifold.cylinder(c, r + 0.01, r - c, 96).translate((0, 0, DRUM_W - c)))
        body = self._along_x(body ^ env)
        pin_len = DRUM_GAP - EC10_ROTOR_FACE + DRUM_PIN_ENGAGE
        corner = PIN_AF / math.sqrt(3)
        pin = hexagon(PIN_AF, pin_len) ^ Manifold.cylinder(pin_len, corner, PIN_AF / 2 - PIN_CHAMFER, 24)
        pin = pin.rotate((0, -90, 0))            # tip toward -x
        d, l = DRUM_ROUND_PIN
        rpin = self._along_x(Manifold.cylinder(l, d / 2, d / 2, 32))
        return self._daxis(body + pin + rpin.translate((DRUM_W, 0, 0)), DRUM_GAP)

    def _dbox_rounded(self, x0, hw, z0, x1, z1, r, end):
        """Box in the drum's local frame (x0..x1, |y| <= hw, z0..z1) rounded to r on every edge except the bottom
        and the end facing the drum: the top corners seen along the axis, and the far end (end = -1: at x0,
        +1: at x1) seen from above and from the side, as the hull of spheres, posts and a flat end slab."""
        def at(m, x, y, z):
            bx, by = self._dl(x, y)
            return m.translate((bx, -by, z))
        xr = x1 - r if end > 0 else x0 + r          # centre line of the rounded end
        xf = x0 if end > 0 else x1 - 0.01           # flat end, facing the drum
        parts = []
        for sy in (-1, 1):
            yc = sy * (hw - r)
            parts += [at(Manifold.sphere(r), xr, yc, z1 - r), at(Manifold.cylinder(z1 - r - z0, r), xr, yc, z0),
                      at(self._along_x(Manifold.cylinder(0.01, r)), xf, yc, z1 - r)]
        parts.append(self._dbox(xf, -hw, z0, xf + 0.01, hw, z1 - r))
        # a short box (x1 - x0 < 2 r) would let the end spheres poke past the flat end: trim to the box
        return Manifold.batch_hull(parts) ^ self._dbox(x0, -hw, z0, x1, hw, z1)

    def _hood_fillet(self, x0, hw, x1, r, end, z, f, xa, xb):
        """Concave fillet of radius f round the foot of a hood (plan: x0..x1, |y| <= hw, far end corners rounded
        to r as in _dbox_rounded) standing on a face at height z; kept to xa..xb so it stops at the drum side.
        A slab of the foot outline grown by f, less the tube of radius f swept along that outline f above the face
        (cylinders along the sides, a torus round each far corner) and less the hood itself."""
        core = (CrossSection.square((x1 - x0, 2 * (hw - r))).translate((x0 - r if end > 0 else x0 + r, -(hw - r)))
                .offset(r, JoinType.Round) ^ CrossSection.square((x1 - x0, 2 * hw)).translate((x0, -hw)))
        ox, oy = self._dl(0, 0)
        # the tube's centre line, built for the far end at +x, run on past the drum side, then mirrored if needed
        xs, xc, yc, rr = x0 - f - 1, x1 - r, hw - r, r + f
        if end < 0:
            xs, xc = x1 + f + 1, x0 + r
        sx = 1 if end > 0 else -1
        pts = [(xs, -(hw + f))]
        n = 32
        for cy, a0 in ((-yc, -math.pi / 2), (yc, 0.0)):       # far corners, quarter arcs round (xc, -/+yc)
            for i in range(n + 1):
                a = a0 + math.pi / 2 * i / n
                pts.append((xc + sx * rr * math.cos(a), cy + rr * math.sin(a)))
        pts.append((xs, hw + f))
        ball = Manifold.sphere(f, 96)
        balls = [ball.translate((ox + px, -oy + py, z + f)) for px, py in pts]
        tube = Manifold.batch_boolean([Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:])], OpType.Add)
        slab = Manifold.extrude(core.offset(f - 0.02, JoinType.Round), f + 0.01).translate((ox, -oy, z - 0.01))
        # the hood's own footprint, shrunk a hair so the fillet fuses with the wall, but kept full width across the
        # open drum-side end so no film is left over the opening
        xd = x0 if end > 0 else x1
        foot = core.offset(-0.01, JoinType.Miter) + CrossSection.square((0.1, 2 * hw)).translate((xd - 0.05, -hw))
        foot = Manifold.extrude(foot, f + 1).translate((ox, -oy, z - 0.5))
        return (slab - tube - foot) ^ self._dbox(xa, -hw - f - 1, z - 1, xb, hw + f + 1, z + f + 1)

    def _block_x(self):
        x0 = DRUM_GAP + DRUM_W + DRUM_GAP
        return x0, x0 + BLOCK_T

    def drum_block3d(self):
        """Bearing block on the PCB: U slot open upward with a narrowed (snap-in) mouth, two locating pegs.
        Seen along the axis the top corners are rounded; the flat bottom sits on the PCB."""
        x0, x1 = self._block_x()
        b = self._dbox_rounded(x0, BLOCK_HALF_W, 0, x1, BLOCK_TOP, BLOCK_R, 1)
        pin_end = DRUM_GAP + DRUM_W + DRUM_ROUND_PIN[1]
        slot_x1 = pin_end + 0.3
        b = b - self._daxis(self._along_x(Manifold.cylinder(slot_x1 - x0 + 0.1, BLOCK_SLOT_R, BLOCK_SLOT_R, 48)), x0 - 0.1)
        b = b - self._dbox(x0 - 0.1, -BLOCK_LIP / 2, EC10_AXIS, slot_x1, BLOCK_LIP / 2, BLOCK_TOP + 0.1)
        d, l = BLOCK_PEG
        for px, py in self.d['drum']['pegs']:
            b = b + Manifold.cylinder(l + 0.01, d / 2, d / 2, 24).translate((px, -py, -l))
        return b

    def drum_bezel3d(self):
        """Flange flush in the plate hole round the opening, with a ledge under the plate; a hood over the encoder
        (its far wall runs down to the PCB as a leg) and one over the block (its roof holds the block down), both
        open toward the drum. Laid on the PCB before the plate goes on."""
        zl, z0, z1 = PLATE_GAP - BEZEL_LEDGE_T, PLATE_GAP, PLATE_TOP_Z
        m = (Manifold.extrude(self.bezel_outline(), z1 - z0).translate((0, 0, z0))
             + Manifold.extrude(self.bezel_ledge(), BEZEL_LEDGE_T).translate((0, 0, zl)))
        w, c = BEZEL_WALL, BEZEL_CLEAR
        # encoder hood: top corners rounded like the block hood outside; inside the radius stays small enough
        # to clear the body's square top edges by the 0.3 mm clearance, and the block hood follows it
        ex0, ey, etop = EC10_BRACKET[0] - c, EC10_BODY[3] + c, EC10_BODY[4] + c
        m = m + (self._dbox_rounded(ex0 - w, ey + w, z0, 0.2, etop + w, HOOD_OUT_R, -1)
                 - self._dbox_rounded(ex0, ey, z0 - 0.1, 0.3, etop, HOOD_IN_R, -1))
        # leg: the encoder hood's far wall down to the PCB, clear of the bracket and the pads
        m = m + self._dbox(ex0 - w, -BEZEL_LEG_HW, 0, ex0, BEZEL_LEG_HW, zl + 0.01)
        # block hood: roof on the block top; its length, width, height and corners match the encoder hood's, so it
        # is solid above the block top and beyond the block's far end
        bx0, bx1 = self._block_x()
        by, btop = ey, BLOCK_TOP                         # as wide as the encoder hood
        bhood_top, bend = etop + w, self._hood_ends()[1]    # beyond the block the hood is solid
        m = m + (self._dbox_rounded(bx0 - 0.1, by + w, z0, bend, bhood_top, HOOD_OUT_R, 1)
                 - self._dbox_rounded(bx0 - 0.2, by, z0 - 0.1, bx1 + c, btop, HOOD_IN_R, 1))
        # fillets at the foot of both hoods, on the flange top; they end flush with the hoods' drum-side faces,
        # where the flange is cut away for the drum
        fr, ef, bf = BEZEL_FILLET, 0.2, bx0 - 0.1          # drum-side faces of the encoder / block hood
        m = m + self._hood_fillet(ex0 - w, ey + w, ef, HOOD_OUT_R, -1, z1, fr, ex0 - w - fr - 0.1, ef)
        m = m + self._hood_fillet(bf, by + w, bend, HOOD_OUT_R, 1, z1, fr, bf, bend + fr + 0.1)
        # through the flange and the ledge: under both hoods and the drum (between the hoods' drum-side faces)
        rr = DRUM_D / 2
        m = m - self._dbox(ef, -(rr + 0.2), zl - 0.1, bf, rr + 0.2, z1 + 0.1)
        m = m - self._dbox(ex0, -ey, zl - 0.1, 0.3, ey, z1 + 0.1)
        m = m - self._dbox(bx0 - 0.2, -by, zl - 0.1, bx1 + c, by, z1 + 0.1)
        return m

    def plate3d(self):
        return Manifold.extrude(self.plate(), PLATE_T)

    def plate3d_printed(self):
        """All-printed variant: the 1.5 mm switch plate plus a RIB_T web underneath, so a printed plate is stiff.
        The web fills the cavity except around the switch housings, the stabilizers, the OLED cover and the
        front-side MCU parts, and stays inside the walls. Print it upside down (top face on the bed)."""
        keep = CrossSection()
        g = SWITCH_CUT / 2 + 0.6
        for k in self.d['keys']:
            keep = keep + rect(k['cx'] - g, k['cy'] - g, k['cx'] + g, k['cy'] + g)
            if k['w'] >= 2:
                w, hh, dy = STAB_CUT
                for sx in (-1, 1):
                    cx = k['cx'] + sx * STAB_X
                    keep = keep + rect(cx - w / 2 - 1.0, k['cy'] + dy - hh / 2 - 1.0, cx + w / 2 + 1.0, k['cy'] + dy + hh / 2 + 1.0)
        for x0, y0, x1, y1 in self.d.get('web_keep', []):   # encoder test board: the MCU's pins through the board
            keep = keep + rect(x0, y0, x1, y1)
        for x, y in self.d.get('buttons', []):
            keep = keep + rect(x - BUTTON_KEEP, y - BUTTON_KEEP, x + BUTTON_KEEP, y + BUTTON_KEEP)
        web = self.inner.offset(-0.3, JoinType.Round) - keep - self.cover_shape().offset(1.0, JoinType.Round) \
            - self.holes(self.d['holes'], BOSS_D + 2.0)
        if 'drum' in self.d:   # room for the bezel's ledge and the encoder / block under the opening
            web = web - self.bezel_outline(BEZEL_LEDGE + 0.5)
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
    if os.path.basename(os.path.dirname(os.path.abspath(path))) == 'print':   # a printed part: redraw its three views
        from case_drawings import draw
        draw(os.path.abspath(path), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(path))), 'drawings'))


def write_half(hf, out, parts=True, laser=True):
    """Every output of one half under out/{laser,print,preview}; returns the layers (for check) and its report entry.
    parts=False leaves out the wheel, its cap and the drum parts (the encoder test board uses the keyboard's);
    laser=False makes a 3D printed case only (no laser-cut layers; the preview shows the printed plate)."""
    side = hf.side
    for sub in ('laser', 'print', 'preview') if laser else ('print', 'preview'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    layers = {'plate': hf.plate(), 'bottom': hf.bottom()}
    if hf.window_box is not None:
        layers['oled-cover'] = hf.cover()
    for i in range(N_FRAMES):
        layers[f'frame{i + 1}'] = hf.frame(i)
    for name, cs in layers.items() if laser else ():
        write_dxf(os.path.join(out, 'laser', f'{side}-{name}.dxf'), cs)
        write_svg(os.path.join(out, 'laser', f'{side}-{name}.svg'), cs, f'{side} {name}')
    tray, plate = hf.tray(), hf.plate3d()
    write_stl(os.path.join(out, 'print', f'{side}-tray.stl'), tray)
    write_stl(os.path.join(out, 'print', f'{side}-plate.stl'), hf.plate3d_printed())   # all-printed variant
    if parts:
        write_stl(os.path.join(out, 'print', f'{side}-wheel.stl'), hf.wheel3d())
        write_stl(os.path.join(out, 'print', f'{side}-wheel-cap.stl'), hf.wheel_cap())   # 3D-print variant
    stands = {}
    if parts and hf.feet():        # tilt stands: printed bottom down (print/), under the untilted tray (preview/)
        for deg in STAND_ANGLES:
            m, _ = hf.stand(deg)
            w = m.transform(stand_pose(deg, hf.front_y()))
            write_stl(os.path.join(out, 'print', f'{side}-stand-{deg}.stl'), w)
            write_stl(os.path.join(out, 'preview', f'{side}-stand-{deg}-placed.stl'), m)
            stands[deg] = dict(height=round(float(w.bounding_box()[5]), 1), volume_cm3=round(w.volume() / 1000, 1))
    if parts and 'drum' in hf.d:   # drum dial: drum (resin print), bearing block and bezel, each with its bottom at z = 0
        for name, m in (('drum', hf.drum3d()), ('drum-block', hf.drum_block3d()), ('drum-bezel', hf.drum_bezel3d())):
            write_stl(os.path.join(out, 'print', f'{side}-{name}.stl'), m.translate((0, 0, -m.bounding_box()[2])))
    if hf.window_box is not None:
        write_stl(os.path.join(out, 'preview', f'{side}-oled-cover.stl'), Manifold.extrude(hf.cover(), COVER_T))
    # assembly preview (print variant): tray + PCB + plate in place
    z_pcb = FLOOR + STANDOFF
    write_stl(os.path.join(out, 'preview', f'{side}-pcb.stl'), hf.pcb3d().translate((0, 0, z_pcb)))
    write_stl(os.path.join(out, 'preview', f'{side}-plate-placed.stl'),
              (plate if laser else hf.plate3d_printed()).translate((0, 0, z_pcb + PCB_T + PLATE_GAP)))
    if parts and 'drum' in hf.d:   # drum dial parts in place (print variant), for the renders
        for name, m in (('drum', hf.drum3d()), ('drum-block', hf.drum_block3d()), ('drum-bezel', hf.drum_bezel3d())):
            write_stl(os.path.join(out, 'preview', f'{side}-{name}-placed.stl'), m.translate((0, 0, z_pcb + PCB_T)))
    ox0, oy0, ox1, oy1, _ = hf.outer_box
    report = dict(case_mm=[round(ox1 - ox0, 1), round(oy1 - oy0, 1)],
                  height_print=round(FLOOR + STANDOFF + PCB_T + PLATE_GAP + PLATE_T, 2),
                  height_acrylic=BOTTOM_T + N_FRAMES * FRAME_T + PLATE_T,
                  screws=len(hf.screws), screws_xy=[[round(float(x), 3), round(float(y), 3)] for x, y in hf.screws], pcb_holes=len(hf.d['holes']),
                  tray_volume_cm3=round(tray.volume() / 1000, 1),
                  feet_xy=[[round(float(x), 3), round(float(y), 3)] for x, y in hf.feet()], stands=stands,
                  plate_genus=plate.genus(), tray_status=str(tray.status()))
    return layers, report


def main(sides):
    report = {}
    for side in sides:
        hf = Half(side)
        layers, report[side] = write_half(hf, OUT)
        check(hf, layers)
    json.dump(report, open(os.path.join(OUT, 'case_report.json'), 'w'), indent=1)
    print(json.dumps(report, indent=1))


def check_drum(hf):
    """Drum dial: parts clear of each other and of the plate, pin into the rotor, hood clear of the neighbours."""
    drum, enc, block, bezel = hf.drum3d(), hf.ec10e3d(), hf.drum_block3d(), hf.drum_bezel3d()
    plate = hf.plate3d().translate((0, 0, PLATE_GAP))
    for a, b, name in ((drum, enc, 'drum hits the encoder'), (drum, block, 'drum hits the block'),
                       (drum, bezel, 'drum hits the bezel'), (bezel, enc, 'bezel hits the encoder'),
                       (bezel, block, 'bezel hits the block'), (bezel, plate, 'bezel hits the plate'),
                       (drum, plate, 'drum hits the plate'), (enc, plate, 'encoder hits the plate'),
                       (block, plate, 'block hits the plate'), (block, enc, 'block hits the encoder')):
        assert (a ^ b).volume() < 1e-3, name
    assert drum.bounding_box()[2] >= 0.3, 'drum too close to the PCB'
    tip = DRUM_GAP - (DRUM_GAP - EC10_ROTOR_FACE + DRUM_PIN_ENGAGE)
    assert abs((EC10_ROTOR_FACE - tip) - DRUM_PIN_ENGAGE) < 1e-9 and DRUM_PIN_ENGAGE <= EC10_HEX_DEPTH
    assert abs(float(drum.bounding_box()[0]) - (hf._dl(tip, 0)[0])) < 0.01, 'hex pin does not reach the rotor'
    # the bezel's footprint above the plate stays off the switch tops; the hoods stay off the keycaps
    above = bezel.trim_by_plane((0, 0, 1), PLATE_TOP_Z + 0.01).project()
    assert (above ^ hf.switch_tops()).area() < 0.01, 'bezel hits a switch top'
    caps = CrossSection()
    for k in hf.d['keys']:
        hw = k['w'] * 19.05 / 2 - 0.5
        caps = caps + rect(k['cx'] - hw, k['cy'] - 8.9, k['cx'] + hw, k['cy'] + 8.9)
    assert (above ^ caps).area() < 0.01, 'bezel hood under a keycap'
    # the opening leaves a web to the switch and stabilizer cut-outs; no PCB mounting hole under it
    cut = CrossSection()
    for k in hf.d['keys']:
        h = SWITCH_CUT / 2
        cut = cut + rect(k['cx'] - h, k['cy'] - h, k['cx'] + h, k['cy'] + h)
        if k['w'] >= 2:
            w, hh, dy = STAB_CUT
            for sx in (-1, 1):
                cx = k['cx'] + sx * STAB_X
                cut = cut + rect(cx - w / 2, k['cy'] + dy - hh / 2, cx + w / 2, k['cy'] + dy + hh / 2)
    assert (hf.bezel_outline(BEZEL_FIT + 1.5) ^ cut).area() < 0.01, 'bezel hole too close to a switch / stabilizer cut-out'
    # the ledge under the plate stays off the switch housings, the walls and the PCB screw heads
    ledge = hf.bezel_ledge()
    assert (ledge ^ cut.offset(0.5, JoinType.Miter)).area() < 0.01, 'bezel ledge under a switch / stabilizer'
    assert (ledge - hf.inner).area() < 0.01, 'bezel ledge outside the walls'
    assert (ledge ^ hf.holes(hf.d['holes'], BOSS_D + 1.9)).area() < 0.01, 'bezel ledge over a PCB screw head'
    for p in hf.d['holes']:
        assert not inside(hf.drum_opening(), p), 'PCB mounting hole under the drum opening'
    # flush: the flange top is the plate top; only the hoods stand above it
    assert abs(float(bezel.bounding_box()[2])) < 1e-9, 'bezel leg does not reach the PCB'
    print(hf.side, 'drum dial checks ok')


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
            assert not inside(s['cap'].offset(2.0, JoinType.Miter), (x, y)), f"screw next to the {s['name']} port tunnel"
    for name, cs in layers.items():
        assert not cs.is_empty(), name
    # tunnel roof stays printable (thinnest where the OLED cover's pocket lowers the wall top)
    roof = PLATE_GAP - CHANNEL_CLR - PORT_LIFT
    for s in hf.slots:
        if s['conn'].get('open_top'):
            continue
        if (s['chan'] ^ hf.cover_shape().offset(COVER_FIT, JoinType.Round)).area() > 0.01:
            roof = min(roof, PLATE_GAP - CHANNEL_CLR - PORT_LIFT - WALL_POCKET)
    assert roof >= 0.6, f'port tunnel roof {roof:.2f} mm too thin'
    if hf.window_box is not None:
        check_oled(hf)
    check_wheel(hf)
    check_feet(hf)
    check_tilt(hf)
    if 'drum' in hf.d:
        check_drum(hf)
    check_closed(hf, layers)


def check_oled(hf):
    """OLED: window clear of switch cut-outs, cover clear of switch tops and fully supported by the plate."""
    win = hf.window_cs()
    keys = CrossSection()
    for k in hf.d['keys']:
        h = SWITCH_CUT / 2 + 1.0
        keys = keys + rect(k['cx'] - h, k['cy'] - h, k['cx'] + h, k['cy'] + h)
    assert (win ^ keys).area() < 0.01, 'OLED window too close to a switch'
    assert (win - hf.cover_shape()).area() < 0.01, 'cover does not span the OLED window'
    assert (hf.cover_shape() ^ hf.switch_tops()).area() < 0.01, 'cover hits a switch'
    assert (hf.cover_shape() - hf.outer.offset(-COVER_MARGIN + 0.01)).area() < 0.01, 'cover leaves the case outline margin'
    caps = CrossSection()
    for c in hf.keycaps():
        caps = caps + rect(*c)
    (cx0, cy0, cx1, cy1), _ = hf.cover_box()
    beside = CrossSection()
    for c in hf.keycaps():
        if c[1] < cy1:      # keycaps level with the cover: the full band; those below it: at least COVER_BELOW
            beside = beside + rect(*c)
    assert (hf.cover_shape().offset(COVER_FRAME - 0.01, JoinType.Round) ^ beside).area() < 0.01, 'cover closer than COVER_FRAME to a keycap'
    assert (hf.cover_shape().offset(COVER_BELOW - 0.01, JoinType.Round) ^ caps).area() < 0.01, 'cover closer than COVER_BELOW to a keycap'
    assert (hf.cover_shape().offset(COVER_FRAME - 0.01, JoinType.Round) - hf.outer).area() < 0.01, 'cover closer than COVER_FRAME to the outline'


def check_wheel(hf):
    """Wheel: clear of standoffs and screws, its rim leaves the case outline at the corner, pin into the rotor."""
    (wx, wy), wr = hf.wheel_xy()
    for x, y in hf.d['holes']:
        assert math.hypot(x - wx, y - wy) > wr + WHEEL_CUT + BOSS_D / 2, 'wheel hits a standoff'
    for x, y in hf.screws:
        assert math.hypot(x - wx, y - wy) > wr + WHEEL_CUT + SCREW_D / 2 + 0.8, 'wheel hits a case screw'
    assert (hf.wheel_cut(0) - hf.outer).area() > 20, 'wheel does not stick out of the corner'
    # encoder: the lowered hub clears it, the hex pin reaches PIN_ENGAGE into the rotor
    wheel = hf.wheel3d().translate((0, 0, FLOOR + WHEEL_GAP))
    enc = hf.encoder3d(FLOOR)
    assert (wheel ^ enc).volume() < 1e-3, 'wheel hits the encoder'
    assert hf.hub_top() + HUB_CLEAR <= hf.enc_bottom() + 1e-6, 'hub too high for the encoder'
    pin_top = float(wheel.bounding_box()[5])
    assert abs(pin_top - (FLOOR + hf.enc_bottom() + PIN_ENGAGE)) < 1e-6, 'pin does not reach into the rotor'
    assert pin_top < FLOOR + STANDOFF - 0.3, 'pin reaches the PCB'
    assert FLOOR + WHEEL_GAP + WHEEL_T > FLOOR + hf.enc_bottom(), 'rim no longer overlaps the encoder (hub not needed)'


def check_feet(hf):
    """Foot recesses: off the bottom fillet, clear of counterbores, pilot holes, the reset hole and the wheel, a floor
    left above them, and every key centre inside the feet (no key press lifts a corner)."""
    feet = hf.feet()
    if not feet:
        return
    assert len(feet) == 5, feet
    assert FLOOR - FOOT_DEPTH >= 1.0 - 1e-9, 'floor above the foot recesses too thin'
    for p in feet:
        assert hf.foot_fits(p), f'foot recess at {p} hits the fillet, a hole or the wheel'
    for a in feet:
        for b in feet:
            assert a == b or math.dist(a, b) > FOOT_D + 1.0, f'foot recesses at {a} and {b} run together'
    support = hull(feet)
    for k in hf.d['keys']:
        assert hull_margin(support, (k['cx'], k['cy'])) > 0, f"key at ({k['cx']}, {k['cy']}) outside the feet"


def check_tilt(hf):
    """Tilt stands: the pocket floors and the front feet's contact line on one plane at the angle, every key inside
    the support (the stand's footprint and the front feet), a floor under the pockets, clear of the tray and the plugs,
    on the printer bed."""
    if not hf.feet():
        return
    tray = hf.tray()
    front = [(x, y) for x, y in hf.feet() if y == hf.front_y()]
    for deg in STAND_ANGLES:
        m, feet = hf.stand(deg)
        pose = stand_pose(deg, hf.front_y())
        w = m.transform(pose)
        for x, y in feet:                   # pocket floor: where the foot's bottom lands
            p = [sum(pose[i][j] * v for j, v in enumerate((x, -y, -FOOT_PROUD))) + pose[i][3] for i in range(3)]
            a = math.degrees(math.atan2(p[2], p[1] + hf.front_y()))
            assert abs(a - deg) <= 0.2, f'{deg} deg stand: foot at ({x}, {y}) lands at {a:.2f} deg'
            assert p[2] >= STAND_FLOOR, f'{deg} deg stand: {p[2]:.2f} mm under the pocket at ({x}, {y})'
        pts = [(q[0], -q[1]) for poly in w.slice(0.05).to_polygons() for q in poly] + front
        support = hull(pts)
        for k in hf.d['keys']:
            assert hull_margin(support, (k['cx'], k['cy'])) > 0, f"{deg} deg: key at ({k['cx']}, {k['cy']}) outside"
        assert (m ^ tray).volume() < 1e-3, f'{deg} deg stand hits the tray'
        assert all((m ^ pl).volume() < 1e-3 for pl in hf.plugs3d()), f'{deg} deg stand hits a plug'
        b = w.bounding_box()
        assert b[3] - b[0] <= BED and b[4] - b[1] <= BED and abs(b[2]) < 1e-6, f'{deg} deg stand off the bed'


def check_closed(hf, layers):
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
