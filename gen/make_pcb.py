"""Build <side>/nrsk-<side>.kicad_pcb from the schematic netlist (run with KiCad's Python)."""
import math
import os
import subprocess
import sys

import pcbnew

import sexpr
from layout import HERE, U, load

KICAD = os.path.expanduser('~/Applications/KiCad/KiCad.app/Contents')
KICAD_CLI = KICAD + '/MacOS/kicad-cli'
STD_FP = KICAD + '/SharedSupport/footprints'
ROOT = os.path.abspath(os.path.join(HERE, '..'))
ORIGIN = (30.0, 30.0)          # board placement on the page [mm]
MARGIN = 3.0                   # board edge outside the key grid [mm]
CORNER_R = 4.0

# Per-side geometry in board-local mm. Keys are shifted so the board starts at x = -MARGIN.
# Connectors sit on the front in key-free notches of the inner edge; the MCU sits on the back.
SIDES = {
    # connectors on the BACK so plugs pass under the PCB and the switch plate needs no cut-outs;
    # values are the y of each connector on the inner edge and the MCU centre
    # each board hugs its own key grid (3 mm margin); the TRRS jacks sit at the same height on both halves.
    # The OLEDs sit at the same height too (top two rows, flush with the inner edge): the left board is
    # 4.7 mm wider so its module clears the row-0/1 switches by the same 2.45 mm as on the right.
    'left': dict(key_shift=0.0, width=8.25 * U + MARGIN + 4.7, inner=+1, usb_y=19.0, trrs_y=112.3,
                 mcu=(152.8, 66.0), oled=(8.25 * U + MARGIN + 4.7 - 6.3, 19.05, 90), wheel='top-left'),
    'right': dict(key_shift=9.75 * U, width=9.5 * U + MARGIN, inner=-1, usb_y=81.0, trrs_y=112.3, mcu=(6.0, 94.0),
                  oled=(3.3, 19.05, 270), wheel='top-right'),
}

# Support parts: (ref, list of (footprint ref, pad) the part should sit close to)
SUPPORT = [
    ('Y1', [('U1', '16'), ('U1', '17')]),
    ('C1', [('Y1', '1')]), ('C2', [('Y1', '3')]),
    ('R2', [('U1', '4'), ('J2', 'A6')]), ('R3', [('U1', '3'), ('J2', 'A7')]),
    ('U2', [('J2', 'A6'), ('J2', 'A7')]),
    ('R4', [('J2', 'A5')]), ('R5', [('J2', 'B5')]),
    ('F1', [('J2', 'A4')]), ('D99', [('F1', '1'), ('U1', '14')]),
    ('C3', [('U1', '6')]), ('C4', [('U1', '2')]), ('C5', [('U1', '14')]), ('C6', [('U1', '24')]),
    ('C7', [('U1', '44')]), ('C8', [('U1', '34')]),
    ('R8', [('U1', '18')]), ('R9', [('U1', '19')]),
    ('C9', [('U3', '2')]), ('C10', [('U3', '1')]),
    ('R6', [('U1', '13')]), ('RSW1', [('U1', '13')]), ('R7', [('U1', '33')]), ('R1', [('U1', '21')]),
]


def mm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + x), pcbnew.FromMM(ORIGIN[1] + y))


def lib_path(nick):
    return os.path.join(ROOT, 'lib', 'nrsk.pretty') if nick == 'nrsk' else os.path.join(STD_FP, nick + '.pretty')


def read_netlist(side):
    sch = os.path.join(ROOT, side, f'nrsk-{side}.kicad_sch')
    net = os.path.join(ROOT, side, f'nrsk-{side}.net')
    subprocess.run([KICAD_CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', net, sch],
                   check=True, capture_output=True)
    t = sexpr.parse(open(net).read())
    os.remove(net)
    comps = {}
    for c in sexpr.find(sexpr.find1(t, 'components'), 'comp'):
        ref = sexpr.find1(c, 'ref')[1]
        comps[ref] = dict(value=sexpr.find1(c, 'value')[1], fp=sexpr.find1(c, 'footprint')[1],
                          uuid=sexpr.find(c, 'tstamps')[-1][1])
    nets = {}
    for n in sexpr.find(sexpr.find1(t, 'nets'), 'net'):
        name = sexpr.find1(n, 'name')[1]
        nets[name] = [(sexpr.find1(x, 'ref')[1], sexpr.find1(x, 'pin')[1]) for x in sexpr.find(n, 'node')]
    return comps, nets


def outline(board, w, h):
    """Rounded rectangle on Edge.Cuts from (-MARGIN,-MARGIN) to (w,h)."""
    x0, y0, x1, y1, r = -MARGIN, -MARGIN, w, h, CORNER_R

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(mm(*a)); s.SetEnd(mm(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)

    def arc(c, a0):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        p = lambda a: (c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))
        s.SetArcGeometry(mm(*p(a0)), mm(*p(a0 + 45)), mm(*p(a0 + 90)))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)

    seg((x0 + r, y0), (x1 - r, y0)); seg((x1, y0 + r), (x1, y1 - r))
    seg((x1 - r, y1), (x0 + r, y1)); seg((x0, y1 - r), (x0, y0 + r))
    arc((x1 - r, y0 + r), 270); arc((x1 - r, y1 - r), 0); arc((x0 + r, y1 - r), 90); arc((x0 + r, y0 + r), 180)


def pad_box(p):
    bb = p.GetBoundingBox()
    return [pcbnew.ToMM(v) - o for v, o in ((bb.GetLeft(), ORIGIN[0]), (bb.GetTop(), ORIGIN[1]),
                                            (bb.GetRight(), ORIGIN[0]), (bb.GetBottom(), ORIGIN[1]))]


def box_dist(px, py, b):
    dx = max(b[0] - px, 0, px - b[2])
    dy = max(b[1] - py, 0, py - b[3])
    return math.hypot(dx, dy)


def mounting_holes(board, keys, w, h, shift):
    boxes = [(o[0] - ORIGIN[0], o[1] - ORIGIN[1], o[2] - ORIGIN[0], o[3] - ORIGIN[1])
             for o in obstacles(board, None, True, False) + obstacles(board, None, False, False)]
    bodies = [(k['cx'] - shift - 7, k['cy'] - 7, k['cx'] - shift + 7, k['cy'] + 7) for k in keys]
    cands = set()
    for k in keys:
        for sx in (-1, 0, 1):
            for sy in (-1, 1):
                cands.add((round(k['cx'] - shift + sx * k['w'] * U / 2, 3), round(k['cy'] + sy * k['h'] * U / 2, 3)))
        for sx in (-1, 1):   # midpoints of the vertical key edges
            cands.add((round(k['cx'] - shift + sx * k['w'] * U / 2, 3), round(k['cy'], 3)))
    for r in range(1, 6):    # along the boundaries between rows
        for i in range(int(w * 2)):
            cands.add((i * 0.5, round(r * U, 3)))
    wcx, wcy = wheel_centre(SIDE_NOW[0], w)
    ok = []
    for (x, y) in cands:
        if math.hypot(x - wcx, y - wcy) < WHEEL_R + WHEEL_CLEAR:
            continue
        if not (3 < x < w - 3 and 3 < y < h - 3):
            continue
        if min(box_dist(x, y, b) for b in bodies) < 2.5:   # M2 hole courtyard / pan head between switch housings
            continue
        # room for an M2 hex standoff (4 mm A/F) / printed boss (5.2 mm) under the board
        if min(box_dist(x, y, b) for b in boxes) < STANDOFF_CLR:
            continue
        ok.append((x, y))
    targets = [(w * fx, h * fy) for fy in (0.17, 0.83) for fx in (0.1, 0.37, 0.63, 0.9)]
    picked = []
    for tx, ty in targets:
        free = [c for c in ok if all(math.hypot(c[0] - p[0], c[1] - p[1]) > 30 for p in picked)]
        best = min(free, key=lambda c: math.hypot(c[0] - tx, c[1] - ty), default=None)
        if best and math.hypot(best[0] - tx, best[1] - ty) < 30:
            picked.append(best)
    return picked


ROW_Y = 4.0   # row line offset below switch centre [mm]
STANDOFF_CLR = 2.5   # hole centre to (pad/track bbox grown by 0.25): >= 2.75 mm real clearance
KEEPOUT_R = 2.5      # no tracks/vias within this radius of a mounting hole [mm] (hex standoff: 2.31)


def keepout(board, x, y, r=KEEPOUT_R):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    o = z.Outline(); o.NewOutline()
    for i in range(24):
        a = 2 * math.pi * i / 24
        p = mm(x + r * math.cos(a), y + r * math.sin(a))
        o.Append(p.x, p.y)
    z.SetZoneName('standoff')
    board.Add(z)


def pad(fp, num):
    return [p for p in fp.Pads() if p.GetNumber() == num][0].GetPosition()


def padnet(fp, num):
    return [p for p in fp.Pads() if p.GetNumber() == num][0].GetNet()


def track(board, a, b, layer, net, width=0.25):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(a); t.SetEnd(b)
    t.SetWidth(pcbnew.FromMM(width)); t.SetLayer(layer); t.SetNet(net)
    t.SetLocked(True)
    board.Add(t)


def via(board, p, net):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(p); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3))
    v.SetNet(net); v.SetLocked(True)
    board.Add(v)


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def bbox_mm(bb, grow=0.0):
    return (pcbnew.ToMM(bb.GetLeft()) - grow, pcbnew.ToMM(bb.GetTop()) - grow,
            pcbnew.ToMM(bb.GetRight()) + grow, pcbnew.ToMM(bb.GetBottom()) + grow)


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def obstacles(board, skip, back=True, socket_courtyards=True):
    """Bounding boxes (absolute mm) that a back-side SMD part must not overlap."""
    layer = pcbnew.B_CrtYd if back else pcbnew.F_CrtYd
    cu = pcbnew.B_Cu if back else pcbnew.F_Cu
    out = []
    for fp in board.GetFootprints():
        if fp is skip:
            continue
        cy = fp.GetCourtyard(layer)
        if cy.OutlineCount() and (socket_courtyards or not fp.GetReference().startswith('SW')):
            out.append(bbox_mm(cy.BBox()))
        for p in fp.Pads():
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) or p.IsOnLayer(cu):
                out.append(bbox_mm(p.GetBoundingBox(), 0.25))
    for t in board.GetTracks():
        if t.IsOnLayer(cu):
            out.append(bbox_mm(t.GetBoundingBox(), 0.25))
    return out


def autoplace(board, fp, anchors, w, h):
    """Put a back-side part at the free spot closest to its anchor pads."""
    tx = sum(a.x for a in anchors) / len(anchors)
    ty = sum(a.y for a in anchors) / len(anchors)
    if not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    obs = obstacles(board, fp)
    lim = (ORIGIN[0] - MARGIN + 0.8, ORIGIN[1] - MARGIN + 0.8, ORIGIN[0] + w - 0.8, ORIGIN[1] + h - 0.8)
    best = None
    step = pcbnew.FromMM(0.25)
    for r in range(0, 160):          # spiral-ish search on rings of growing radius
        ring = []
        for i in range(-r, r + 1):
            for j in (-r, r):
                ring += [(i, j), (j, i)]
        for i, j in set(ring):
            for rot in (0, 90):
                fp.SetOrientationDegrees(rot)
                fp.SetPosition(pcbnew.VECTOR2I(int(tx + i * step), int(ty + j * step)))
                cy = fp.GetCourtyard(pcbnew.B_CrtYd)
                box = bbox_mm(cy.BBox(), 0.1)
                if not (lim[0] < box[0] and lim[1] < box[1] and box[2] < lim[2] and box[3] < lim[3]):
                    continue
                if any(overlap(box, o) for o in obs):
                    continue
                d = sum(dist(p.GetPosition(), a) for p in fp.Pads() for a in anchors)
                if best is None or d < best[0]:
                    best = (d, rot, fp.GetPosition())
        if best and r > 8:
            break
    assert best, f'no room for {fp.GetReference()}'
    fp.SetOrientationDegrees(best[1])
    fp.SetPosition(best[2])


# corner thumbwheel: concentric with the rounded case corner, 1 mm further in on both axes
WHEEL_R = 14.6            # rim protrudes 3.5 mm at the corner diagonal, ~1 mm on the two faces
WHEEL_CLEAR = 3.0         # keep standoffs / bosses this far outside the wheel


def wheel_centre(side, w):
    inset = CORNER_R + 1.0
    return (-MARGIN + inset, -MARGIN + inset) if SIDES[side]['wheel'] == 'top-left' else (w - inset, -MARGIN + inset)


def place_encoder(fp, x, y, rot=90):
    """EC11 on the front with its shaft (midpoint of the two mounting tabs) at (x, y)."""
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(mm(x, y))
    mp = [p.GetPosition() for p in fp.Pads() if p.GetNumber() == 'MP']
    cx, cy = (mp[0].x + mp[1].x) // 2, (mp[0].y + mp[1].y) // 2
    target = mm(x, y)
    fp.Move(pcbnew.VECTOR2I(target.x - cx, target.y - cy))


# courtyard overhang beyond the connector mouth (mouth ends flush with the board edge)
MOUTH_OVERHANG = {'usb': 0.5, 'trrs': 0.355}


# KiCad's library has no 3D model for these footprints; use LCSC's (gen/fetch_3d.sh), shifted so
# their pegs and shell legs land on KiCad's pads. Offsets are 3D (y up), in mm.
LCSC_3D = '${KIPRJMOD}/../tools/easyeda/nrsk_lcsc.3dshapes/'
MODELS = {
    'USB_C_Receptacle_HRO_TYPE-C-31-M-12': ('USB-C_SMD-TYPE-C-31-M-12_1.wrl', (0, 1.42, 0), (0, 0, 180)),
    'Jack_3.5mm_PJ320D_Horizontal': ('AUDIO-SMD_PJ-320D-1.wrl', (0.925, 0, 0), (0, 0, 0)),
}


def set_model(fp, name):
    if name not in MODELS:
        return
    f, off, rot = MODELS[name]
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = LCSC_3D + f
    m.m_Offset = pcbnew.VECTOR3D(*off)
    m.m_Rotation = pcbnew.VECTOR3D(*rot)
    fp.Models().clear()
    fp.Models().push_back(m)


def place_connector(fp, edge_x, y, inner, kind):
    """Back-side connector on the inner edge, mouth flush with the edge."""
    fp.SetPosition(mm(0, y))
    if not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)

    def outwardness(rot):
        fp.SetOrientationDegrees(rot)
        c = fp.GetPosition()
        if kind == 'usb':      # contacts sit at the back, away from the mouth
            pads = [p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
            return -inner * (sum(p.GetPosition().x for p in pads) / len(pads) - c.x)
        pegs = [p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]   # pegs sit toward the nozzle
        return inner * (sum(p.GetPosition().x for p in pegs) / len(pegs) - c.x)

    fp.SetOrientationDegrees(max((0, 90, 180, 270), key=outwardness))
    b = bbox_mm(fp.GetCourtyard(pcbnew.B_CrtYd).BBox())
    target = ORIGIN[0] + edge_x + inner * MOUTH_OVERHANG[kind]
    dx = target - (b[2] if inner > 0 else b[0])
    fp.Move(pcbnew.VECTOR2I(pcbnew.FromMM(dx), 0))
    cy = (b[1] + b[3]) / 2 - ORIGIN[1]
    fp.Move(pcbnew.VECTOR2I(0, pcbnew.FromMM(y - cy)))


def write_case_data(side, board, fps, keys, holes, w, h, shift):
    """Geometry the enclosure generator needs, in board-local mm (y down)."""
    def local_box(fp):
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        b = bbox_mm(cy.BBox())
        return [b[0] - ORIGIN[0], b[1] - ORIGIN[1], b[2] - ORIGIN[0], b[3] - ORIGIN[1]]

    def local(p):
        return [pcbnew.ToMM(p.x) - ORIGIN[0], pcbnew.ToMM(p.y) - ORIGIN[1]]

    inner_side = 'right' if side == 'left' else 'left'
    data = dict(
        side=side, inner_side=inner_side,
        outline=dict(x0=-MARGIN, y0=-MARGIN, x1=w, y1=h, r=CORNER_R), thickness=1.6,
        holes=[[round(x, 3), round(y, 3)] for x, y in holes],
        keys=[dict(cx=round(k['cx'] - shift, 3), cy=round(k['cy'], 3), w=k['w'], h=k['h'], name=k['name'])
              for k in keys.values()],
        connectors=dict(
            usb=dict(center=local(fps['J2'].GetPosition()), box=local_box(fps['J2']), plug=[12.5, 7.0]),
            trrs=dict(center=local(fps['J1'].GetPosition()), box=local_box(fps['J1']), plug=[9.0, 9.0]),
        ),
        reset=local(fps['RSW1'].GetPosition()),
        oled=dict(box=local_box(fps['J3'])),
        wheel=dict(center=list(wheel_centre(side, w)), r=WHEEL_R),
    )
    import json
    json.dump(data, open(os.path.join(ROOT, side, 'case_data.json'), 'w'), indent=1, ensure_ascii=False)


SIDE_NOW = [None]


def build(side):
    SIDE_NOW[0] = side
    cfg = SIDES[side]
    shift = cfg['key_shift']
    keys = {f'SW{i}': k for i, k in enumerate(load(side), 1)}
    comps, nets = read_netlist(side)
    pcb_path = os.path.join(ROOT, side, f'nrsk-{side}.kicad_pcb')
    if os.path.exists(pcb_path):
        os.remove(pcb_path)
    board = pcbnew.NewBoard(pcb_path)
    w, h = cfg['width'], 6 * U + MARGIN

    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni

    fps = {}
    for ref, c in comps.items():
        nick, name = c['fp'].split(':')
        fp = pcbnew.FootprintLoad(lib_path(nick), name)
        assert fp, c['fp']
        fp.SetFPID(pcbnew.LIB_ID(nick, name))
        fp.SetReference(ref)
        fp.SetValue(c['value'])
        fp.SetPath(pcbnew.KIID_PATH('/' + c['uuid']))
        fp.SetSheetname('/'); fp.SetSheetfile(f'nrsk-{side}.kicad_sch')
        set_model(fp, name)
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

    # switches + diodes
    row_vias = {}
    # a key whose socket would sit on the wheel sensor is turned 180 deg (south-facing switch, socket below
    # the stem); its diode moves above the stem and its row link is left to the autorouter
    wcx, wcy = wheel_centre(side, w)
    turned = {ref for ref, k in keys.items() if math.hypot(k['cx'] - shift - wcx, k['cy'] - wcy) < 12.0}
    for ref, k in keys.items():
        x, y = k['cx'] - shift, k['cy']
        flip = ref in turned
        sw = place(ref, x, y, 180 if flip else 0)
        sw.Reference().SetVisible(False)
        dref = 'D' + ref[2:]
        dx, dy = (7.2, -5.0) if flip else (-7.2, 5.0)
        d = place(dref, x + dx, y + dy, 90, back=True)
        anode_up = pad(d, '2').y < pad(d, '1').y
        if anode_up == flip:                # anode toward the socket
            d.SetOrientationDegrees(270)
        d.Reference().SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
        d.Reference().SetPosition(mm(x + dx - (1.8 if not flip else -1.8), y + dy))
        d.Reference().SetTextAngleDegrees(90)
        # fixed pre-route: socket pad 2 -> anode, cathode -> via on the row line
        a, kp, sp = pad(d, '2'), pad(d, '1'), pad(sw, '2')
        track(board, a, sp, pcbnew.B_Cu, padnet(d, '2'))
        if not flip:
            row_vias.setdefault((k['row'], round(y, 2)), []).append((mm(x - 5.6, y + ROW_Y), kp, padnet(d, '1')))

    # cathode -> via, and row lines on F.Cu through each physical row
    # (a key wired to a row in another physical row is left to the autorouter)
    for (r, _), items in row_vias.items():
        if len(items) < 2:
            continue
        for via_pt, kp, net in items:
            corner = pcbnew.VECTOR2I(via_pt.x, kp.y)
            track(board, kp, corner, pcbnew.B_Cu, net)
            track(board, corner, via_pt, pcbnew.B_Cu, net)
            via(board, via_pt, net)
        pts = sorted((it[0] for it in items), key=lambda p: p.x)
        net = board.FindNet(f'/ROW{r}')
        for p0, p1 in zip(pts, pts[1:]):
            track(board, p0, p1, pcbnew.F_Cu, net)

    # pre-routed copper is an obstacle for part placement
    outline(board, w, h)

    # connectors (front) and MCU (back)
    edge_x = w if cfg['inner'] > 0 else -MARGIN
    place_connector(fps['J2'], edge_x, cfg['usb_y'], cfg['inner'], 'usb')
    place_connector(fps['J1'], edge_x, cfg['trrs_y'], cfg['inner'], 'trrs')
    place('J3', *cfg['oled'])          # OLED module on the front, in a key-free notch
    wx, wy = wheel_centre(side, w)
    place('U3', wx, wy, 0, back=True)    # AS5600 right above the wheel's magnet
    u1 = place('U1', *cfg['mcu'], 0, back=True)
    a6 = pad(fps['J2'], 'A6')
    best = min((0, 90, 180, 270), key=lambda r: (u1.SetOrientationDegrees(r), dist(pad(u1, '4'), a6))[1])
    u1.SetOrientationDegrees(best)

    for ref, anchors in SUPPORT:
        autoplace(board, fps[ref], [pad(fps[r], p) for r, p in anchors], w, h)
    # dense MCU area: references go to the assembly (Fab) layer instead of silkscreen
    for ref in ['U1', 'J1', 'J2'] + [r for r, _ in SUPPORT]:
        f = fps[ref].Reference()
        f.SetLayer(pcbnew.B_Fab)
        f.SetPosition(fps[ref].GetPosition())
        f.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.6), pcbnew.FromMM(0.6)))
        f.SetTextThickness(pcbnew.FromMM(0.1))

    # any remaining silkscreen reference that lands on another part's pads moves to the Fab layer
    pad_boxes = [(fp, bbox_mm(p.GetBoundingBox(), 0.15)) for fp in board.GetFootprints() for p in fp.Pads()]
    for fp in board.GetFootprints():
        f = fp.Reference()
        if f.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS) or not f.IsVisible():
            continue
        rb = bbox_mm(f.GetBoundingBox())
        if any(o is not fp and overlap(rb, b) for o, b in pad_boxes):
            f.SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)

    # mounting holes (board only, M2)
    holes = mounting_holes(board, list(keys.values()), w, h, shift)
    print(side, 'mounting holes:', len(holes))
    for i, (x, y) in enumerate(holes, 1):
        keepout(board, x, y)
        fp = pcbnew.FootprintLoad(lib_path('MountingHole'), 'MountingHole_2.2mm_M2')
        fp.SetFPID(pcbnew.LIB_ID('MountingHole', 'MountingHole_2.2mm_M2'))
        fp.SetReference(f'H{i}'); fp.SetValue('M2')
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetPosition(mm(x, y))
        fp.Reference().SetVisible(False)
        board.Add(fp)

    # silkscreen title
    t = pcbnew.PCB_TEXT(board)
    t.SetText(f'nrsk {side.upper()} v2.0')
    t.SetLayer(pcbnew.B_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.5), pcbnew.FromMM(1.5)))
    t.SetMirrored(True)
    obs = obstacles(board, None, True)
    for fy in range(5, int(h) - 5, 2):
        for fx in range(int(w * 0.3), int(w), 4):
            t.SetPosition(mm(fx, fy))
            tb = bbox_mm(t.GetBoundingBox(), 0.3)
            if tb[2] < ORIGIN[0] + w - 1 and not any(overlap(tb, o) for o in obs):
                break
        else:
            continue
        break
    board.Add(t)

    write_case_data(side, board, fps, keys, holes, w, h, shift)
    pcbnew.SaveBoard(pcb_path, board)
    print('wrote', pcb_path)


if __name__ == '__main__':
    for s in sys.argv[1:] or ('left', 'right'):
        build(s)
