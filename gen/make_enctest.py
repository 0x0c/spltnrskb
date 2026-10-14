"""Encoder test board: the top-right corner of the right half, cut out with both encoders where the keyboard has them.

The board keeps the right half's coordinates (read from right/case_data.json), so the corner thumbwheel encoder
(ENC1, EC05E1220401 on the back), the drum dial encoder (ENC2, EC10E1220505 on the front) and the drum's bearing
block holes sit exactly where they are on the keyboard, and the keyboard's wheel, wheel cap, drum, bearing block
and bezel fit its case. The plate has no cut-out for the F12 key next to the drum (no key there). A tall tact
switch in the strip between the drum and the back wall, pressed through a hole in the plate, holds layer 1.

The MCU, a Waveshare RP2040-Zero, hangs under the board face down on Mac8 ConThrough stacking pins (XB-3-2: the
boards 2 mm apart), soldered to the module and plugged into 0.85 mm holes in this board. It lies along the left
edge with its USB-C on a board tongue in the left wall, the mouth just inside the case's outer surface, like the
keyboard's ports; the tunnel is open at the top, so the board drops in. The RP2040-Zero's pin rows bring out
GP0-GP8 and GP14/15/26-29 only, so the encoders go to GP5-GP8 and the switch to GP4 (keyboard: wheel GP19/GP20,
drum GP22/GP23).

  python3 gen/make_enctest.py sch       schematic + project files (enctest/)
  $KPY    gen/make_enctest.py pcb       board + enctest/case_data.json (KiCad's Python)
  .venv/bin/python gen/make_enctest.py case   case parts under enctest/case/ (and the checks)

./gen/build_enctest.sh runs all of it, routes the board and writes the fabrication files.
"""
import json
import math
import os
import sys

from layout import HERE

ROOT = os.path.abspath(os.path.join(HERE, '..'))
SIDE = 'enctest'
DIR = os.path.join(ROOT, SIDE)
SRC = os.path.join(ROOT, 'right', 'case_data.json')   # the right half's geometry this board is cut from

U = 19.05
MARGIN = 3.0                 # = make_pcb.MARGIN: board edge outside the key grid
KEY = 'F12'                  # the key left of the drum: sets the board's left edge; no switch, no plate cut-out
CASE_WALL = 8.5              # make_case CLEAR + WALL: board edge to the case's outer surface
# RP2040-Zero (Waveshare dimension drawing): 18.0 x 23.5 mm, two rows of 9 pins 15.24 mm apart, the first pin
# 1.59 mm from the USB end; the 5 castellated pads on the far end are off this grid and not used. Heights from
# Waveshare's STEP model, from the component face: PCB 1.1 thick, USB-C 3.24 above it and 0.92 into the board,
# 9.58 wide, 1.21 past the board's edge; BOOT / RESET 2.49; parts on the back 1.0
ZERO_W, ZERO_L, ZERO_ROW, ZERO_PIN0 = 18.0, 23.5, 15.24, 1.59
ZERO_T, USB_UP, USB_IN, USB_W, USB_OUT, ZERO_BACK = 1.1, 3.24, 0.92, 9.58, 1.21, 1.0
STACK_H = 2.0                # ConThrough XB-3-2: this board's bottom to the module's back
TONGUE_HW = ZERO_ROW / 2 + 2.75   # tongue half width: the pin rows, their pads well clear of the rounded tip
TONGUE_TIP_R, TONGUE_ROOT_R = 2.5, 1.5
PIN_KEEP = 1.5               # printed plate's web this far from the pin tips poking up through the board
SWITCH_Y = 4.5               # tact switch below the board's top edge, in the strip above the drum's bezel
ENC_HOLE_KEEP = 2.6          # track keep-out round the wheel encoder's 3 mm square hole (half diagonal 2.1 + 0.3 + margin)
WHEEL_RUN_Y, WHEEL_TURN_Y = 15.712, 7.975   # WHEEL_A as routed by hand: its run along the front, where it turns up
SCREW_SPACING = 15.0         # case screws of its own at least this far from the keyboard's
# RP2040-Zero pin rows, from the USB end (top view, USB up): J1 = left row, J2 = right row; net or None
ZERO_LEFT = [('5V', None), ('GND', 'GND'), ('3V3', None), ('GP29', None), ('GP28', None), ('GP27', None),
             ('GP26', None), ('GP15', None), ('GP14', None)]
ZERO_RIGHT = [('GP0', None), ('GP1', None), ('GP2', None), ('GP3', None), ('GP4', 'KEY'), ('GP5', 'WHEEL_A'),
              ('GP6', 'WHEEL_B'), ('GP7', 'DRUM_A'), ('GP8', 'DRUM_B')]

FP = {
    'wheel': 'nrsk:Alps_EC05E1220401',
    'drum': 'nrsk:Alps_EC10E',
    'switch': 'Button_Switch_THT:SW_PUSH_6mm_H9.5mm',  # 9.5 mm tall: the actuator stands 4.5 mm above the plate
    'socket': 'nrsk:ConThrough_1x09_P2.54mm_Contact',
}


def geometry():
    """Board outline, key, RP2040-Zero, tact switch and mounting holes in the right half's board-local mm (y down)."""
    src = json.load(open(SRC))
    o = src['outline']
    key = next(k for k in src['keys'] if k['name'] == KEY)
    x0 = key['cx'] - key['w'] * U / 2 - MARGIN
    y0, x1, y1 = o['y0'], o['x1'], key['cy'] + key['h'] * U / 2 + MARGIN + 1.0
    yc = (y0 + y1) / 2
    # RP2040-Zero along the left edge, face down, USB-C toward the left wall: its mouth PORT_SKIN inside the
    # case's outer surface; a tongue of the board reaches into the wall under its first pins
    mouth = x0 - CASE_WALL + src['port_skin']
    end = mouth + USB_OUT                                  # the module's USB end
    zx, zy = end + ZERO_L / 2, yc
    pins = [end + ZERO_PIN0 + 2.54 * k for k in range(9)]
    tongue = (end, zy - TONGUE_HW, x0, zy + TONGUE_HW)
    # M2 holes: the keyboard's one right of the drum (x 172, on the row boundary), one above and one below the
    # RP2040-Zero on the left corners' arc centres (4 mm from both edges and the rounded corner; the lower one 3 mm
    # below the module, clear of its boss), and one along the top edge between the module and the switch
    kx0 = key['cx'] - key['w'] * U / 2
    row = key['cy'] + key['h'] * U / 2
    real = [h for h in src['holes'] if x0 < h[0] < x1 and abs(h[1] - row) < 0.01]
    r = o['r']
    holes = [[x0 + r, y0 + r], [kx0 + 25.2, y0 + 4.5], [x0 + r, y1 - r]] + real
    switch = [kx0 + 32.6, y0 + SWITCH_Y]
    return dict(src=src, outline=dict(x0=x0, y0=y0, x1=x1, y1=y1, r=o['r']), key=key, holes=holes,
                mcu=(zx, zy), mouth=mouth, end=end, pins=pins, tongue=tongue, switch=switch)


# --- schematic (plain Python) --------------------------------------------------------
def sch():
    import make_pro
    from make_sch import Sheet

    project = f'nrsk-{SIDE}'
    sh = Sheet(project)
    sh.text('Encoder test board (top-right corner of the right half; MCU: Waveshare RP2040-Zero on ConThrough pins)', 25.4, 25.4)
    X, Y = 50.8, 50.8
    sh.text('Thumbwheel encoder Alps EC05E1220401 (12 detents / 12 pulses, C = common)', X - 12.7, Y - 12.7, 1.27)
    sh.symbol('Device:RotaryEncoder', 'ENC1', 'EC05E1220401', X, Y, 0, FP['wheel'],
              {'A': 'WHEEL_A', 'B': 'WHEEL_B', 'C': 'GND'})
    sh.text('Drum dial encoder Alps EC10E1220505 (24 detents / 12 pulses, C = common)', X - 12.7, Y + 25.4 - 12.7, 1.27)
    sh.symbol('Device:RotaryEncoder', 'ENC2', 'EC10E1220505', X, Y + 25.4, 0, FP['drum'],
              {'A': 'DRUM_A', 'B': 'DRUM_B', 'C': 'GND'})
    sh.text('Tact switch above the drum: layer 1 while held (to GND; RP2040 internal pull-up)', X - 12.7, Y + 50.8 - 7.62, 1.27)
    sh.symbol('Switch:SW_Push', 'SW1', 'Layer 1', X, Y + 50.8, 0, FP['switch'], {'1': 'KEY', '2': 'GND'})
    HX, HY = 127.0, 50.8
    sh.text('RP2040-Zero, ConThrough plug-in holes (pin 1 = USB end; internal pull-ups on all inputs)', HX - 12.7, HY - 12.7, 1.27)
    for ref, row, x in (('J1', ZERO_LEFT, HX), ('J2', ZERO_RIGHT, HX + 50.8)):
        for i, (name, _) in enumerate(row):
            sh.text(name, x + 12.7, HY + i * 2.54 + 0.6, 1.0)
        sh.symbol('Connector_Generic:Conn_01x09', ref, f'RP2040-Zero {"left" if ref == "J1" else "right"}', x,
                  HY + 10.16, 0, FP['socket'], {str(i + 1): net for i, (_, net) in enumerate(row)})
    sh.power('PWR_FLAG', HX, HY + 30.48, 0)     # GND comes from the RP2040-Zero
    sh.attach('GND', (HX, HY + 30.48), (0, 1))
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, project + '.kicad_sch')
    sh.write(path, 'nrsk encoder test board')
    make_pro.write(SIDE)
    open(os.path.join(DIR, 'fp-lib-table'), 'w').write(
        '(fp_lib_table\n\t(version 7)\n\t(lib (name "nrsk") (type "KiCad") (uri "${KIPRJMOD}/../lib/nrsk.pretty") '
        '(options "") (descr "nrsk keyboard footprints"))\n)\n')
    open(os.path.join(DIR, 'sym-lib-table'), 'w').write(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "nrsk") (type "KiCad") (uri "${KIPRJMOD}/../lib/nrsk.kicad_sym") '
        '(options "") (descr "nrsk keyboard symbols"))\n)\n')
    print('wrote', path)


# --- board (KiCad's Python) ----------------------------------------------------------
def outline(board, mm, pts):
    """Closed Edge.Cuts path through axis-aligned corners [(x, y, r)], each rounded with radius r (convex or
    concave)."""
    import pcbnew

    def add(shape, *p):
        s = pcbnew.PCB_SHAPE(board, shape)
        if shape == pcbnew.SHAPE_T_SEGMENT:
            s.SetStart(mm(*p[0])); s.SetEnd(mm(*p[1]))
        else:
            s.SetArcGeometry(*(mm(*q) for q in p))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)

    ends = []
    n = len(pts)
    for i, (x, y, r) in enumerate(pts):
        (px, py, _), (nx, ny, _) = pts[i - 1], pts[(i + 1) % n]
        din = ((x - px) / math.dist((x, y), (px, py)), (y - py) / math.dist((x, y), (px, py)))
        dout = ((nx - x) / math.dist((x, y), (nx, ny)), (ny - y) / math.dist((x, y), (nx, ny)))
        a = (x - din[0] * r, y - din[1] * r)
        b = (x + dout[0] * r, y + dout[1] * r)
        c = (a[0] + dout[0] * r, a[1] + dout[1] * r)
        k = r / math.dist((x, y), c)
        add(pcbnew.SHAPE_T_ARC, a, (c[0] + (x - c[0]) * k, c[1] + (y - c[1]) * k), b)
        ends.append((a, b))
    for i in range(n):
        add(pcbnew.SHAPE_T_SEGMENT, ends[i][1], ends[(i + 1) % n][0])


def text(board, mm, s, x, y, layer, size, justify=None, mirror=False, angle=0):
    import pcbnew
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(size * 0.15))
    if justify is not None:
        t.SetHorizJustify(justify)
    t.SetMirrored(mirror)
    t.SetTextAngleDegrees(angle)
    t.SetPosition(mm(x, y))
    board.Add(t)


def pcb():
    import pcbnew
    from footprints import DRUM_W
    from make_pcb import keepout, lib_path, mm, pad, padnet, read_netlist, track

    g = geometry()
    src, o, key = g['src'], g['outline'], g['key']
    comps, nets = read_netlist(SIDE)
    path = os.path.join(DIR, f'nrsk-{SIDE}.kicad_pcb')
    if os.path.exists(path):
        os.remove(path)
    board = pcbnew.NewBoard(path)
    netinfo = {}
    for name in nets:
        netinfo[name] = pcbnew.NETINFO_ITEM(board, name)
        board.Add(netinfo[name])
    fps = {}
    for ref, c in comps.items():
        nick, name = c['fp'].split(':')
        fp = pcbnew.FootprintLoad(lib_path(nick), name)
        assert fp, c['fp']
        fp.SetFPID(pcbnew.LIB_ID(nick, name))
        fp.SetReference(ref)
        fp.SetValue(c['value'])
        fp.SetPath(pcbnew.KIID_PATH('/' + c['uuid']))
        fp.SetSheetname('/'); fp.SetSheetfile(f'nrsk-{SIDE}.kicad_sch')
        board.Add(fp)
        fps[ref] = fp
    for name, nodes in nets.items():
        for ref, pin in nodes:
            for p in fps[ref].Pads():
                if p.GetNumber() == pin:
                    p.SetNet(netinfo[name])

    def place(ref, x, y, rot=0, back=False):
        fp = fps[ref]
        fp.SetPosition(mm(x, y))
        if back:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        return fp

    # the same placement as make_pcb.build() on the right half
    wx, wy = src['wheel']['center']
    place('ENC1', wx, wy, 180, back=True)            # on the back, terminals toward +y
    keepout(board, wx, wy, ENC_HOLE_KEEP)            # no track along the 3 mm square hole under the rotor
    dx, dy = src['drum']['origin']
    place('ENC2', dx, dy, 0)
    brg = pcbnew.FootprintLoad(lib_path('nrsk'), 'Drum_Dial_Bearing')
    brg.SetFPID(pcbnew.LIB_ID('nrsk', 'Drum_Dial_Bearing'))
    brg.SetReference('DRUM1'); brg.SetValue('Drum_Dial_Bearing')
    brg.SetBoardOnly(True); brg.SetExcludedFromBOM(True)
    brg.SetPosition(mm(dx, dy))
    board.Add(brg)
    pegs = [[pcbnew.ToMM(p.GetPosition().x) - pcbnew.ToMM(mm(0, 0).x),
             pcbnew.ToMM(p.GetPosition().y) - pcbnew.ToMM(mm(0, 0).y)] for p in brg.Pads()]
    assert all(math.dist(a, b) < 1e-3 for a, b in zip(sorted(pegs), sorted(src['drum']['pegs']))), 'bearing pegs moved'

    # outline: the right half's top-right corner, the F12 column on the left, the tongue into the left wall
    x0, y0, x1, y1, r = o['x0'], o['y0'], o['x1'], o['y1'], o['r']
    tx0, ty0, _, ty1 = g['tongue']
    assert ty0 - TONGUE_ROOT_R >= y0 + r and ty1 + TONGUE_ROOT_R <= y1 - r, 'tongue root runs into the board corners'
    outline(board, mm, [(x0, y0, r), (x1, y0, r), (x1, y1, r), (x0, y1, r),
                        (x0, ty1, TONGUE_ROOT_R), (tx0, ty1, TONGUE_TIP_R), (tx0, ty0, TONGUE_TIP_R),
                        (x0, ty0, TONGUE_ROOT_R)])

    # RP2040-Zero under the board, face down, USB-C to the left: seen from above, its left row (5V, GND, ...; top
    # view, USB up) lies along the back (-y) as J1, its right row (GP0-GP8) along the front as J2; pin 1 of each at
    # the USB end. The ConThrough pins come up from below, so the holes' footprints go on the back.
    zx, zy = g['mcu']
    pins = g['pins']
    for ref, y in (('J1', zy - ZERO_ROW / 2), ('J2', zy + ZERO_ROW / 2)):
        j = place(ref, pins[0], y, 0, back=True)
        for rot in (0, 90, 180, 270):
            j.SetOrientationDegrees(rot)
            a, b = (pcbnew.ToMM(j.Pads()[i].GetPosition().x) - pcbnew.ToMM(mm(0, 0).x) for i in (0, -1))
            if b - a > 20:
                break
        assert abs(a - pins[0]) < 1e-3 and abs(b - pins[-1]) < 1e-3, f'{ref} pins not along +x'
        j.Reference().SetVisible(False)
        j.Value().SetVisible(False)
    # the RP2040-Zero's outline (0.5 mm outside, clear of the rows' own) on the back's silkscreen
    xa, xb = g['end'] - 0.5, g['end'] + ZERO_L + 0.5
    ya, yb = zy - ZERO_W / 2 - 0.5, zy + ZERO_W / 2 + 0.5
    for a, b in (((max(xa, x0 + 0.5), ya), (xb, ya)), ((xb, ya), (xb, yb)), ((xb, yb), (max(xa, x0 + 0.5), yb))):
        ln = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        ln.SetStart(mm(*a)); ln.SetEnd(mm(*b))
        ln.SetLayer(pcbnew.B_SilkS); ln.SetWidth(pcbnew.FromMM(0.15))
        board.Add(ln)
    text(board, mm, 'RP2040-Zero face down', zx + 2.0, zy - 1.2, pcbnew.B_SilkS, 1.0, mirror=True)
    text(board, mm, 'USB ->', zx + 2.0, zy + 1.2, pcbnew.B_SilkS, 1.0, mirror=True)   # read from the back: toward the tongue
    # tact switch above the drum (footprint origin = pad 1; the body's centre is 3.25, 2.25 from it)
    sx, sy = g['switch']
    sw = place('SW1', sx - 3.25, sy - 2.25, 0)
    sw.Reference().SetVisible(False)
    text(board, mm, 'LAYER 1', sx + 6.5, sy, pcbnew.F_SilkS, 0.8)
    # WHEEL_A as routed by hand on the back: 45 degrees off the RP2040-Zero's GP5, along the front, 45 degrees up
    # and straight into the wheel encoder's A. Locked, so Freerouting routes the rest round it
    p, a = pad(fps['J2'], '6'), pad(fps['ENC1'], 'A')
    run, turn = mm(0, WHEEL_RUN_Y).y, mm(0, WHEEL_TURN_Y).y
    pts = [p, pcbnew.VECTOR2I(p.x + run - p.y, run), pcbnew.VECTOR2I(a.x - (run - turn), run),
           pcbnew.VECTOR2I(a.x, turn), a]
    for s, e in zip(pts, pts[1:]):
        track(board, s, e, pcbnew.B_Cu, padnet(fps['J2'], '6'), 0.2)

    for i, (x, y) in enumerate(g['holes'], 1):
        keepout(board, x, y)
        fp = pcbnew.FootprintLoad(lib_path('MountingHole'), 'MountingHole_2.2mm_M2')
        fp.SetFPID(pcbnew.LIB_ID('MountingHole', 'MountingHole_2.2mm_M2'))
        fp.SetReference(f'H{i}'); fp.SetValue('M2')
        fp.SetBoardOnly(True); fp.SetExcludedFromBOM(True)
        fp.SetPosition(mm(x, y))
        fp.Reference().SetVisible(False)
        board.Add(fp)
    text(board, mm, 'nrsk encoder test v1', key['cx'] + 25.0, key['cy'] + 8.5, pcbnew.B_SilkS, 1.2, mirror=True)

    data = dict(side=SIDE, inner_side='left', source='right',
                outline=o, thickness=1.6, tongues={}, connectors={}, port_skin=src['port_skin'],
                holes=[[round(x, 3), round(y, 3)] for x, y in g['holes']],
                keys=[], wheel=src['wheel'],
                drum=dict(origin=[dx, dy], width=DRUM_W, pegs=src['drum']['pegs']),
                buttons=[g['switch']],
                web_keep=[[round(v, 3) for v in (pins[0] - PIN_KEEP, y - PIN_KEEP, pins[-1] + PIN_KEEP, y + PIN_KEEP)]
                          for y in (zy - ZERO_ROW / 2, zy + ZERO_ROW / 2)],
                mcu=dict(center=[round(zx, 3), round(zy, 3)], size=[ZERO_L, ZERO_W], stack=STACK_H, t=ZERO_T,
                         usb=dict(width=USB_W, up=USB_UP, into=USB_IN, out=USB_OUT),
                         pins=[[round(x, 3), round(zy + s * ZERO_ROW / 2, 3)] for s in (-1, 1) for x in pins]))
    # the RP2040-Zero's USB-C as a port of the case (make_case Half._slots): the tongue into the left wall, the
    # module and its USB-C as the connector, heights below this board's bottom, the tunnel open at the top
    low = STACK_H + ZERO_T + USB_UP                          # the USB-C's far side, the lowest point
    data['tongues'] = {'mcu': [round(v, 3) for v in g['tongue']]}
    data['connectors'] = {'mcu': dict(
        box=[round(g['mouth'], 3), round(zy - ZERO_W / 2, 3), round(g['end'] + ZERO_L, 3), round(zy + ZERO_W / 2, 3)],
        edge='inner', width=USB_W, open_top=True,
        z=[round(low, 3), round(low - (USB_UP + USB_IN) / 2, 3), round(USB_UP + USB_IN, 3)])}
    json.dump(data, open(os.path.join(DIR, 'case_data.json'), 'w'), indent=1)
    pcbnew.SaveBoard(path, board)
    print('wrote', path)


# --- case (project venv) -------------------------------------------------------------
def case():
    from manifold3d import CrossSection, JoinType, Manifold
    from make_case import (BOSS_D, BUTTON_KEEP, CLEAR, FLOOR, FOOT_D, SWITCH_CUT, PCB_T, PLATE_GAP, STANDOFF, Half, check, inside, rect,
                           write_half)

    hf = Half(SIDE)
    ref = Half(hf.d['source'])
    # case screws: the keyboard's wherever they fall in this case's walls (so the corner round the wheel is the
    # same), and this case's own only where none of those is near
    ring = hf.outer - hf.inner
    screws = [p for p in ref.screws if inside(ring, p) and
              not any(inside(sl['cap'].offset(2.0, JoinType.Miter), p) for sl in hf.slots)]
    hf.screws = screws + [p for p in hf.screws if min(math.dist(p, q) for q in screws) > SCREW_SPACING]
    out = os.path.join(DIR, 'case')
    # 3D printed only (tray + printed plate); wheel, wheel cap and drum parts: the keyboard's (right-*)
    layers, report = write_half(hf, out, parts=False, laser=False)
    check(hf, layers)
    # the RP2040-Zero under the board: its lowest point (the USB-C) above the floor, clear of the standoffs; the tact
    # switch's body clear of the bezel's ledge, the wall and the standoffs' screw heads
    m = hf.d['mcu']
    low = FLOOR + STANDOFF - (m['stack'] + m['t'] + m['usb']['up'])
    assert low >= FLOOR + 0.5, f'RP2040-Zero {low - FLOOR:.2f} mm above the floor'
    zero = rect(*hf.d['connectors']['mcu']['box'])
    assert (zero ^ hf.holes(hf.d['holes'], BOSS_D + 1.0)).area() < 0.01, 'RP2040-Zero on a standoff'
    # in 3D: the module, its USB-C and the ConThrough rows clear of the tray (0.2 mm) and the printed plate
    (zx, zy), (zl, zw), u = m['center'], m['size'], m['usb']
    zb = FLOOR + STANDOFF - m['stack']
    face = zb - m['t']

    def solid(x0, y0, z0, x1, y1, z1, g=0.2, mouth=False):
        x0 = x0 if mouth else x0 - g          # the USB-C's mouth meets the opening's skin: not grown there
        x1, y0, y1, z0, z1 = x1 + g, y0 - g, y1 + g, z0 - g, z1 + g
        return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, -y1, z0))
    parts = solid(zx - zl / 2, zy - zw / 2, face, zx + zl / 2, zy + zw / 2, zb)
    parts = parts + solid(zx - zl / 2 - u['out'], zy - u['width'] / 2, face - u['up'], zx - zl / 2 + 7.3,
                          zy + u['width'] / 2, face + u['into'], mouth=True)
    for y in sorted({p[1] for p in m['pins']}):
        xs = [p[0] for p in m['pins'] if p[1] == y]
        parts = parts + solid(min(xs) - 1.27, y - 1.0, zb, max(xs) + 1.27, y + 1.0, FLOOR + STANDOFF - 0.2)
    plate = hf.plate3d_printed().translate((0, 0, FLOOR + STANDOFF + PCB_T + PLATE_GAP))
    for name, other in (('tray', hf.tray()), ('plate', plate)):
        hit = parts ^ other
        assert hit.volume() < 1e-3, f'RP2040-Zero hits the {name} ({hit.volume():.3f} mm3)'
    for x, y in hf.d['buttons']:
        body = rect(x - 3.0, y - 3.0, x + 3.0, y + 3.0)
        assert (body.offset(0.5, JoinType.Miter) ^ hf.bezel_ledge()).area() < 0.01, 'tact switch under the bezel'
        assert (body - hf.inner.offset(-0.5, JoinType.Miter)).area() < 0.01, 'tact switch at the wall'
        assert (body ^ hf.holes(hf.d['holes'], 4.0 + 1.0)).area() < 0.01, 'tact switch on a screw head'
    # those parts must fit this case as they fit the keyboard: same shape at the same place
    for name, a, b in (('wheel', hf.wheel3d(), ref.wheel3d()), ('wheel cap', hf.wheel_cap(), ref.wheel_cap()),
                       ('drum', hf.drum3d(), ref.drum3d()), ('drum block', hf.drum_block3d(), ref.drum_block3d()),
                       ('drum bezel', hf.drum_bezel3d(), ref.drum_bezel3d())):
        assert str(a.status()) == str(b.status()) == 'Error.NoError' and a.volume() > 0, name
        diff = (a - b).volume() + (b - a).volume()
        assert diff < 1e-3, f'{name} differs from the keyboard ({diff:.4f} mm3)'
    # the plate round the drum and the tray round the wheel, too: from the top wall down to where this case's own
    # bottom corner starts, less the outer 0.1 mm, where the rounded corner of a smaller outline is split into
    # slightly different chords
    o = hf.d['outline']
    y_end = o['y1'] - o['r'] - CLEAR - 0.5
    box = Manifold.cube((60.0, y_end - o['y0'] + 20.0, 30.0)).translate((o['x1'] - 50.0, -y_end, -1.0))
    box = box ^ Manifold.extrude(hf.outer.offset(-0.1, JoinType.Round), 30.0).translate((0, 0, -1.0))
    # and this board's own standoffs (the keyboard has its boards' holes elsewhere), with the printed plate's web
    # cleared round them (BOSS_D + 2.0) and its 0.4 mm rounds where that clearance meets the bezel's
    for x, y in hf.d['holes']:
        if [x, y] not in ref.d['holes']:
            box = box - Manifold.cylinder(30.0, BOSS_D / 2 + 2.5, BOSS_D / 2 + 2.5).translate((x, -y, -1.0))
    # and where this board differs: no F12 cut-out (and so no web kept off it), the printed plate's web kept off
    # the RP2040-Zero's pin tips and the switch's body (1.5 mm more: a strip of web narrower than its 0.8 mm rounding next to those goes)
    own = CrossSection()
    k = next(k for k in ref.d['keys'] if k['name'] == KEY)    # the keyboard's F12 cut-out: closed here
    own = own + rect(k['cx'] - SWITCH_CUT / 2, k['cy'] - SWITCH_CUT / 2, k['cx'] + SWITCH_CUT / 2,
                     k['cy'] + SWITCH_CUT / 2).offset(1.5, JoinType.Miter)
    for r in hf.d['web_keep']:
        own = own + rect(*r).offset(1.5, JoinType.Miter)
    for x, y in hf.d['buttons']:
        own = own + rect(x - BUTTON_KEEP - 1.0, y - BUTTON_KEEP - 1.0, x + BUTTON_KEEP + 1.0, y + BUTTON_KEEP + 1.0)
    box = box - Manifold.extrude(own, 30.0).translate((0, 0, -1.0))
    # and the keyboard's rubber-foot recesses under the floor (this board's tray has none)
    for x, y in ref.feet():
        box = box - Manifold.cylinder(30.0, FOOT_D / 2 + 0.5, FOOT_D / 2 + 0.5).translate((x, -y, -1.0))
    for name, a, b in (('plate', hf.plate3d_printed(), ref.plate3d_printed()), ('tray', hf.tray(), ref.tray())):
        assert str(a.status()) == str(b.status()) == 'Error.NoError' and a.volume() > 0, name
        a, b = a ^ box, b ^ box
        diff = (a - b).volume() + (b - a).volume()
        assert diff < 1e-3, f'{name} round the encoders differs from the keyboard ({diff:.4f} mm3)'
    print(SIDE, 'wheel, wheel cap, drum, block, bezel and the plate / tray round them match the keyboard')
    json.dump({SIDE: report}, open(os.path.join(out, 'case_report.json'), 'w'), indent=1)
    print(json.dumps(report))


if __name__ == '__main__':
    {'sch': sch, 'pcb': pcb, 'case': case}[sys.argv[1]]()
