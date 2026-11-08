"""Builders of the 3D printed parts, one function per part (docs/specs/fusion-case.md, "部品と書き出す STL").

Each builder gets the new component and input.json, and makes the part as make_case.py's matching Half method does,
in the same frame. Feature distances that are make_case constants use the user parameter of the same name, so the
part follows a change of that parameter.
"""
import math

import adsk.core
import adsk.fusion

import nrsk_fusion as nf

NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
INTERSECT = adsk.fusion.FeatureOperations.IntersectFeatureOperation


def wheel(comp, inp, log):
    """Half.wheel3d(): knurled rim, bore from below, hub lowered under the encoder, hex pin on the hub.
    z = 0 is the wheel bottom."""
    p = inp['params']
    (x, y), r = inp['wheel']['xy'], inp['wheel']['r']
    teeth, depth, t = int(p['WHEEL_KNURLS']), p['TOOTH_DEPTH'], p['WHEEL_T']

    # rim: rounded teeth with crests at r. A spline through 6 points per tooth follows the cosine to ~0.001 mm;
    # more points only make the exported mesh larger (12 per tooth tripled the STL)
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.name = 'rim'
    n = teeth * 6
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r - depth * (1 - math.cos(teeth * a)) / 2
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    nf.closed_spline(sk, pts)
    body = nf.extrude(comp, nf.largest_profile(sk), t, NEW, expr='WHEEL_T').bodies.item(0)
    body.name = 'wheel'

    # axle bore from below
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.name = 'bore'
    nf.circle(sk, x, y, p['BORE_D'], expr='BORE_D')
    nf.extrude(comp, sk.profiles.item(0), p['BORE_DEPTH'], CUT, [body], expr='BORE_DEPTH')

    # hub: the top lowered within HUB_R (Half.hub_top() - WHEEL_GAP above the wheel bottom)
    hub = p['STANDOFF'] - p['ENC_H'] - p['HUB_CLEAR'] - p['WHEEL_GAP']
    plane = nf.plane_at(comp, hub)
    plane.name = 'hub'
    sk = comp.sketches.add(plane)
    sk.name = 'hub'
    nf.circle(sk, x, y, 2 * p['HUB_R'])
    nf.extrude(comp, sk.profiles.item(0), t - hub + 0.1, CUT, [body])

    # hex pin into the encoder's rotor, chamfered by a cone from the corners down to AF/2 - PIN_CHAMFER at the tip
    pin_len = p['PIN_ENGAGE'] + p['HUB_CLEAR']
    af = p['PIN_AF']
    corner = af / math.sqrt(3)
    sk = comp.sketches.add(plane)
    sk.name = 'pin'
    nf.polygon(sk, [(x + corner * math.cos(math.radians(60 * i)), y + corner * math.sin(math.radians(60 * i)))
                    for i in range(6)])
    pin = nf.extrude(comp, sk.profiles.item(0), pin_len, NEW).bodies.item(0)
    sk = comp.sketches.add(plane)
    sk.name = 'pin chamfer'
    nf.circle(sk, x, y, 2 * corner)
    tip = af / 2 - p['PIN_CHAMFER']
    taper = -math.degrees(math.atan((corner - tip) / pin_len))      # negative: narrows toward the tip
    nf.extrude(comp, sk.profiles.item(0), pin_len, INTERSECT, [pin], taper_deg=taper)
    nf.combine(comp, body, [pin], JOIN)
    log(f'wheel: centre ({x:.3f}, {y:.3f}), r {r}, {teeth} teeth, hub at {hub:.2f}, pin {pin_len:.2f} long')


def _heights(p):
    """The tray's heights make_case uses round the wheel: wall top, wheel opening top (z1), cap ledge (z_l)."""
    wall_top = p['FLOOR'] + p['STANDOFF'] + p['PCB_T'] + p['PLATE_GAP']
    wz0 = p['FLOOR'] + p['WHEEL_GAP']
    z1 = wz0 - 0.3 + p['WHEEL_T'] + 0.7
    return wall_top, z1, wall_top - p['CAP_LEDGE']


def wheel_cap(comp, inp, log):
    """Half.wheel_cap(): the wall above the wheel opening, a separate stepped part dropped in from above. It is the
    tray's wall (outer block with the small top round, minus the cavity) within the two tiers round the opening,
    each CAP_FIT smaller: the opening's own circle up to the ledge, the shoulder CAP_SHOULDER wider above it."""
    p = inp['params']
    wall_top, z1, z_l = _heights(p)
    (x, y), r = inp['wheel']['xy'], inp['wheel']['r']
    rc = r + p['WHEEL_CUT']

    plane = nf.plane_at(comp, z1)
    plane.name = 'opening top'
    sk = comp.sketches.add(plane)
    sk.name = 'outline'
    nf.rounded_rect(sk, inp['outer_box'])
    block = nf.extrude(comp, sk.profiles.item(0), wall_top - z1, NEW).bodies.item(0)
    block.name = 'wheel cap'
    top = nf.face_at_z(block, wall_top)
    nf.fillet(comp, list(top.edges), p['TRAY_TOP_FILLET'])
    sk = comp.sketches.add(plane)
    sk.name = 'cavity'
    nf.rounded_rect(sk, inp['inner'])
    nf.extrude(comp, sk.profiles.item(0), wall_top - z1 + 0.1, CUT, [block])

    sk = comp.sketches.add(plane)
    sk.name = 'lower tier'
    nf.circle(sk, x, y, 2 * (rc - p['CAP_FIT']))
    tiers = nf.extrude(comp, sk.profiles.item(0), z_l - z1, NEW).bodies.item(0)
    ledge = nf.plane_at(comp, z_l)
    ledge.name = 'cap ledge'
    sk = comp.sketches.add(ledge)
    sk.name = 'shoulder'
    nf.circle(sk, x, y, 2 * (rc + p['CAP_SHOULDER'] - p['CAP_FIT']))
    shoulder = nf.extrude(comp, sk.profiles.item(0), p['CAP_LEDGE'] + 0.01, NEW).bodies.item(0)
    nf.combine(comp, tiers, [shoulder], JOIN)
    nf.combine(comp, block, [tiers], INTERSECT)
    log(f'wheel cap: opening r {rc:.2f}, z {z1:.2f} .. {wall_top:.2f}, ledge at {z_l:.2f}')


def stand(deg):
    """Half.stand(deg) (the U): a band STAND_W wide along the outline, cut off STAND_PAST in front of the side foot,
    its top STAND_POCKET[1] above the feet's bottoms with the top edges rounded, cut at the desk of that tilt, and
    pockets for the feet it carries. Tray frame (under the untilted tray)."""
    def build(comp, inp, log):
        p = inp['params']
        st = inp['stand']
        proud = p['FOOT_H'] - p['FOOT_DEPTH']
        top = -proud + p['STAND_POCKET'][1]
        depth = 60.0                          # below the top: more than the 9 degree stand needs (22.9 mm)
        outer = inp['outer_box']

        plane = nf.plane_at(comp, top - depth)
        plane.name = 'stand bottom'
        sk = comp.sketches.add(plane)
        sk.name = 'band'
        nf.rounded_rect(sk, outer)
        nf.rounded_rect(sk, nf.offset_box(outer, -p['STAND_W']))
        band = min((pr for pr in sk.profiles), key=lambda pr: pr.areaProperties().area)
        body = nf.extrude(comp, band, depth, NEW).bodies.item(0)
        body.name = f'stand {deg}'
        # the U: keep the back (y above y_cut)
        sk = comp.sketches.add(plane)
        sk.name = 'front cut'
        nf.polygon(sk, [(outer['x0'] - 1, outer['y0'] - 1), (outer['x1'] + 1, outer['y0'] - 1),
                        (outer['x1'] + 1, st['y_cut']), (outer['x0'] - 1, st['y_cut'])])
        nf.extrude(comp, sk.profiles.item(0), depth + 1, CUT, [body])
        nf.fillet(comp, list(nf.face_at_z(body, top).edges), p['STAND_FILLET'])

        # the desk of this tilt: world z = s*y + c*z + t >= 0 in the tray frame (row 2 of the stand's pose). Cut away
        # what lies below it: a quadrilateral under the desk line drawn on the YZ plane, extruded through along x
        _, s, c, t = st['poses'][str(deg)][2]
        sk = comp.sketches.add(comp.yZConstructionPlane)
        sk.name = f'desk {deg}'
        ys = (-400.0, 400.0)
        zs = [(-t - s * yy) / c for yy in ys]
        quad = [(0, ys[0], zs[0]), (0, ys[1], zs[1]), (0, ys[1], zs[1] - 500), (0, ys[0], zs[0] - 500)]
        nf.polygon_model(sk, quad)
        feats = comp.features.extrudeFeatures
        einp = feats.createInput(sk.profiles.item(0), CUT)
        einp.setSymmetricExtent(nf.val(400), True)
        einp.participantBodies = [body]
        feats.add(einp)

        feet = {f['id']: f['xy'] for f in inp['feet']}
        fp = nf.plane_at(comp, -proud)
        fp.name = 'foot bottoms'
        sk = comp.sketches.add(fp)
        sk.name = 'pockets'
        for fid in st['feet']:
            nf.circle(sk, *feet[fid], p['STAND_POCKET'][0], ident=fid, expr='STAND_POCKET_0')
        nf.extrude(comp, list(sk.profiles), p['STAND_POCKET'][1] + 0.01, CUT, [body], expr='STAND_POCKET_1 + 0.01 mm')
        log(f'stand {deg}: top {top:.2f}, desk s {s:.4f} c {c:.4f} t {t:.3f}, pockets {", ".join(st["feet"])}')
    return build


def tray(comp, inp, log):
    """Half.tray(): the printed tray. Outer block with the rounded bottom (TRAY_FILLET) and top (TRAY_TOP_FILLET)
    edges, the cavity, PCB bosses with pilot holes, case screws from below (clearance hole, counterbore, pocket and
    nut trap at the wall top), the wheel opening with the cap's tiers taken out, the post the wheel turns on, the
    step under the OLED cover, the USB-C tunnels and openings, the reset hole and the foot recesses."""
    p = inp['params']
    wall_top, z1, z_l = _heights(p)
    z_pcb = p['FLOOR'] + p['STANDOFF']
    (wx, wy), wr = inp['wheel']['xy'], inp['wheel']['r']
    rc = wr + p['WHEEL_CUT']
    xy = comp.xYConstructionPlane

    def sketch(plane, name):
        sk = comp.sketches.add(plane)
        sk.name = name
        return sk

    def circles(plane, name, items, d, expr=None):
        """items: input.json entries ({id, xy}) or bare (x, y) points."""
        sk = sketch(plane, name)
        for it in items:
            xy, ident = (it['xy'], it['id']) if isinstance(it, dict) else (it, None)
            nf.circle(sk, *xy, d, ident=ident, expr=expr)
        return list(sk.profiles)

    # block, rounded edges, cavity
    sk = sketch(xy, 'outline')
    nf.rounded_rect(sk, inp['outer_box'])
    body = nf.extrude(comp, sk.profiles.item(0), wall_top, NEW).bodies.item(0)
    body.name = 'tray'
    nf.fillet(comp, list(nf.face_at_z(body, 0).edges), p['TRAY_FILLET'])
    nf.fillet(comp, list(nf.face_at_z(body, wall_top).edges), p['TRAY_TOP_FILLET'])
    floor = nf.plane_at(comp, p['FLOOR'])
    floor.name = 'floor'
    sk = sketch(floor, 'cavity')
    nf.rounded_rect(sk, inp['inner'])
    nf.extrude(comp, sk.profiles.item(0), wall_top, CUT, [body])

    # PCB bosses and their pilot holes (0.6 mm of floor left under them)
    holes = inp['pcb_holes']
    nf.extrude(comp, circles(floor, 'bosses', holes, p['BOSS_D'], 'BOSS_D'), p['STANDOFF'], JOIN, [body], expr='STANDOFF')
    pilot = nf.plane_at(comp, 0.6)
    pilot.name = 'pilot bottom'
    nf.extrude(comp, circles(pilot, 'pilot holes', holes, p['PILOT_D'], 'PILOT_D'), p['STANDOFF'] + p['FLOOR'] - 0.6, CUT, [body])

    # case screws from below (cuts from the bottom face take the depth as it is: the code starts them 0.01 below)
    screws = inp['screws']
    nf.extrude(comp, circles(xy, 'screw holes', screws, p['SCREW_D'], 'SCREW_D'), wall_top + 0.02, CUT, [body])
    nf.extrude(comp, circles(xy, 'counterbores', screws, p['SCREW_CB'][0], 'SCREW_CB_0'), p['SCREW_CB'][1], CUT, [body],
               expr='SCREW_CB_1')
    pk = nf.plane_at(comp, wall_top - p['BOSS_POCKET'][1])
    pk.name = 'boss pockets'
    nf.extrude(comp, circles(pk, 'boss pockets', screws, p['BOSS_POCKET'][0], 'BOSS_POCKET_0'), p['BOSS_POCKET'][1] + 0.01, CUT, [body])
    nt = nf.plane_at(comp, wall_top - p['BOSS_POCKET'][1] - p['NUT_TRAP'][1])
    nt.name = 'nut traps'
    sk = sketch(nt, 'nut traps')
    for q in screws:
        nf.polygon(sk, nf.hexagon_pts(*q['xy'], p['NUT_TRAP'][0] / math.sqrt(3)), ident=q['id'])
    nf.extrude(comp, list(sk.profiles), p['NUT_TRAP'][1] + 0.01, CUT, [body])

    # wheel opening, and the cap's tiers (the cap is a part of its own)
    wz0 = p['FLOOR'] + p['WHEEL_GAP']
    wo = nf.plane_at(comp, wz0 - 0.3)
    wo.name = 'wheel opening'
    nf.extrude(comp, circles(wo, 'wheel opening', [(wx, wy)], 2 * rc), p['WHEEL_T'] + 0.7, CUT, [body])
    t1 = nf.plane_at(comp, z1)
    t1.name = 'cap bottom'
    nf.extrude(comp, circles(t1, 'cap lower tier', [(wx, wy)], 2 * rc), z_l - z1, CUT, [body])
    t2 = nf.plane_at(comp, z_l)
    t2.name = 'cap ledge'
    nf.extrude(comp, circles(t2, 'cap shoulder', [(wx, wy)], 2 * (rc + p['CAP_SHOULDER'])), p['CAP_LEDGE'] + 0.1,
               CUT, [body])

    # step for the thicker OLED cover
    if 'oled' in inp:
        cp = nf.plane_at(comp, wall_top - p['WALL_POCKET'])
        cp.name = 'cover step'
        sk = sketch(cp, 'cover step')
        nf.rounded_rect(sk, nf.offset_box(inp['oled']['cover'], p['COVER_FIT']))
        nf.extrude(comp, nf.smallest_profile(sk), p['WALL_POCKET'] + 0.01, CUT, [body])

    # USB-C: tunnel for the tongue and the connector (closed above, PORT_LIFT of headroom), opening through the skin
    zt = z_pcb + p['PCB_T'] + p['CHANNEL_CLR'] + p['PORT_LIFT']
    depth = inp['port_skin'] + 1.0
    y_out = inp['outer_box']['y1']
    for sl in inp['slots']:
        if sl['edge'] != 'top':
            raise NotImplementedError(f"{sl['id']}: only ports on the top edge")
        zp = sl['z_bottom'] - 0.2
        tp = nf.plane_at(comp, zp)
        tp.name = f"{sl['name']} tunnel"
        sk = sketch(tp, f"{sl['name']} tunnel")
        for poly in sl['chan']:
            nf.polygon(sk, [tuple(q) for q in poly])
        nf.extrude(comp, list(sk.profiles), zt - zp, CUT, [body])
        plane, sign = nf.plane_y(comp, y_out - depth)
        plane.name = f"{sl['name']} opening"
        sk = sketch(plane, f"{sl['name']} opening")
        nf.stadium_xz(sk, sl['along'], sl['z_centre'], sl['width'], sl['height'], y_out - depth)
        nf.extrude(comp, sk.profiles.item(0), sign * (depth + 1), CUT, [body])

    # wheel post, reset hole, foot recesses
    nf.extrude(comp, circles(floor, 'wheel post', [(wx, wy)], p['POST_D'], 'POST_D'),
               p['WHEEL_GAP'] + p['BORE_DEPTH'] - 0.3, JOIN, [body])
    if 'reset' in inp:
        nf.extrude(comp, circles(xy, 'reset', [inp['reset']], p['RESET_D'], 'RESET_D'), p['FLOOR'] + 0.02, CUT, [body])
    feet = inp['feet']
    nf.extrude(comp, circles(xy, 'foot recesses', feet, p['FOOT_D'], 'FOOT_D'), p['FOOT_DEPTH'], CUT, [body],
               expr='FOOT_DEPTH')
    log(f"tray: wall top {wall_top:.2f}, {len(holes)} bosses, {len(screws)} screws, {len(inp['slots'])} ports, "
        f"{len(feet)} feet")


def plate(comp, inp, log):
    """Half.plate3d_printed(): the all-printed switch plate, printed upside down. The 1.5 mm plate (top outer edge
    rounded by PLATE_FILLET; switch, stabilizer, OLED cover and drum bezel holes; no screw holes on top) on a RIB_T
    web that fills the cavity except round the switches, the stabilizers, the cover, the PCB screw heads and the drum
    bezel's ledge; bosses for heat-set inserts under the case screws. z = 0 is the plate's bottom face.
    The code also opens the web by 0.4 mm (drops slivers, rounds its convex corners); that changes ~0.03 % of the
    volume and is left out here."""
    p = inp['params']
    xy = comp.xYConstructionPlane
    pt_ = p['PLATE_T']

    def sketch(plane, name):
        sk = comp.sketches.add(plane)
        sk.name = name
        return sk

    def square(sk, x, y, hw, hh, ident):
        nf.polygon(sk, [(x - hw, y - hh), (x + hw, y - hh), (x + hw, y + hh), (x - hw, y + hh)], ident=ident)

    # the plate
    sk = sketch(xy, 'outline')
    nf.rounded_rect(sk, inp['outer_box'])
    body = nf.extrude(comp, sk.profiles.item(0), pt_, NEW, expr='PLATE_T').bodies.item(0)
    body.name = 'plate'
    nf.fillet(comp, list(nf.face_at_z(body, pt_).edges), p['PLATE_FILLET'])
    sk = sketch(xy, 'switch cut-outs')
    w, hh, dy = p['STAB_CUT']
    for k in inp['keys']:
        x, y = k['xy']
        square(sk, x, y, p['SWITCH_CUT'] / 2, p['SWITCH_CUT'] / 2, k['id'])
        if k['w'] >= 2:                   # stabilizer housings (board y down: dy below the key = -dy here)
            for sx in (-1, 1):
                square(sk, x + sx * p['STAB_X'], y - dy, w / 2, hh / 2, k['id'])
    if 'oled' in inp:
        nf.rounded_rect(sk, nf.offset_box(inp['oled']['cover'], p['COVER_FIT']))
    if 'drum' in inp:
        for poly in inp['drum']['plate_hole']:
            nf.polygon(sk, [tuple(q) for q in poly])
    nf.extrude(comp, list(sk.profiles), pt_ + 0.1, CUT, [body])

    # the web under it
    bottom = nf.plane_at(comp, -p['RIB_T'] - 0.1)
    bottom.name = 'web cuts'
    sk = sketch(xy, 'web')
    nf.rounded_rect(sk, nf.offset_box(inp['inner'], -0.3))
    web = nf.extrude(comp, sk.profiles.item(0), -p['RIB_T'], NEW, expr='RIB_T').bodies.item(0)
    sk = sketch(bottom, 'web cuts')
    g = p['SWITCH_CUT'] / 2 + 0.6
    for k in inp['keys']:
        x, y = k['xy']
        square(sk, x, y, g, g, k['id'])
        if k['w'] >= 2:
            for sx in (-1, 1):
                square(sk, x + sx * p['STAB_X'], y - dy, w / 2 + 1.0, hh / 2 + 1.0, k['id'])
    if 'oled' in inp:
        nf.rounded_rect(sk, nf.offset_box(inp['oled']['cover'], 1.0))
    for h in inp['pcb_holes']:
        nf.circle(sk, *h['xy'], p['BOSS_D'] + 2.0, ident=h['id'], expr='BOSS_D + 2 mm')
    if 'drum' in inp:
        for poly in inp['drum']['web_cut']:
            nf.polygon(sk, [tuple(q) for q in poly])
    nf.extrude(comp, list(sk.profiles), p['RIB_T'] + 0.2, CUT, [web])
    nf.combine(comp, body, [b for b in comp.bRepBodies if b != body], JOIN)

    # bosses with heat-set inserts under the case screws (the screws come from below)
    screws = inp['screws']
    sk = sketch(xy, 'plate bosses')
    for q in screws:
        nf.circle(sk, *q['xy'], p['PLATE_BOSS'][0], ident=q['id'], expr='PLATE_BOSS_0')
    nf.extrude(comp, list(sk.profiles), -p['PLATE_BOSS'][1], JOIN, [body], expr='PLATE_BOSS_1')
    sk = sketch(xy, 'inserts')
    for q in screws:
        nf.circle(sk, *q['xy'], p['INSERT_D'], ident=q['id'], expr='INSERT_D')
    nf.extrude(comp, list(sk.profiles), -(p['PLATE_BOSS'][1] + 0.01), CUT, [body], expr='PLATE_BOSS_1 + 0.01 mm')
    log(f"plate: {len(inp['keys'])} keys, {len(screws)} bosses, web {p['RIB_T']} under")


TWIST_SIGN = 1      # Fusion's sweep twist against manifold's (counter-clockwise about +x seen from +x)


def _drum_frame(inp):
    """Drum dial local frame -> model: origin, and L(x, y) = (Ox + x, Oy - y) (local y is board y)."""
    ox, oy = inp['drum']['origin']
    return ox, oy, (lambda x, y=0.0: (ox + x, oy - y))


def drum(comp, inp, log):
    """Half.drum3d(): the knurled drum (36 rounded grooves, helix angle DRUM_HELIX) with chamfered ends, a hex pin
    into the EC10E rotor on the encoder side and a round pin into the bearing block on the other. z above the PCB
    top; the axis runs along +x, EC10_AXIS high, DRUM_GAP from the encoder face."""
    p, d = inp['params'], inp['drum']
    ox, oy, L = _drum_frame(inp)
    za, r = p['EC10_AXIS'], d['drum_d'] / 2
    xs, xe = ox + p['DRUM_GAP'], ox + p['DRUM_GAP'] + p['DRUM_W']
    grooves, gd = int(p['DRUM_GROOVES']), p['DRUM_GROOVE_DEPTH']

    # profile on the encoder-side face: local (u, v) of the code's cross-section -> model (y = oy + v, z = za - u)
    start, sgn = nf.plane_x(comp, xs)
    start.name = 'drum start'
    sk = comp.sketches.add(start)
    sk.name = 'grooves'
    pts = []
    for i in range(grooves * 6):
        a = 2 * math.pi * i / (grooves * 6)
        rr = r - gd * (1 - math.cos(grooves * a)) / 2
        pts.append((xs, oy + rr * math.sin(a), za - rr * math.cos(a)))
    nf.spline3(sk, pts)
    axis_plane, _ = nf.plane_y(comp, oy)
    axis_plane.name = 'drum axis'
    sk2 = comp.sketches.add(axis_plane)
    sk2.name = 'drum path'
    line = sk2.sketchCurves.sketchLines.addByTwoPoints(sk2.modelToSketchSpace(nf.pt(xs, oy, za)),
                                                       sk2.modelToSketchSpace(nf.pt(xe, oy, za)))
    twist = math.degrees(p['DRUM_W'] * math.tan(math.radians(p['DRUM_HELIX'])) / r)
    sweeps = comp.features.sweepFeatures
    si = sweeps.createInput(nf.largest_profile(sk), comp.features.createPath(line), NEW)
    si.twistAngle = adsk.core.ValueInput.createByString(f'{TWIST_SIGN * twist} deg')
    body = sweeps.add(si).bodies.item(0)
    body.name = 'drum'

    # chamfered ends: intersect with a revolved envelope
    c = p['DRUM_CHAMFER']
    sk3 = comp.sketches.add(axis_plane)
    sk3.name = 'drum envelope'
    env_lines = nf.polygon3(sk3, [(xs, oy, za), (xs, oy, za + r - c), (xs + c, oy, za + r + 0.01),
                                  (xe - c, oy, za + r + 0.01), (xe, oy, za + r - c), (xe, oy, za)])
    revs = comp.features.revolveFeatures
    ri = revs.createInput(sk3.profiles.item(0), env_lines[-1], NEW)
    ri.setAngleExtent(False, adsk.core.ValueInput.createByString('360 deg'))
    env = revs.add(ri).bodies.item(0)
    nf.combine(comp, body, [env], INTERSECT)

    # hex pin toward the encoder (a corner up), chamfered by a cone to AF/2 - PIN_CHAMFER at the tip
    pin_len = p['DRUM_GAP'] - p['EC10_ROTOR_FACE'] + p['DRUM_PIN_ENGAGE']
    af = p['PIN_AF']
    corner = af / math.sqrt(3)
    sk4 = comp.sketches.add(start)
    sk4.name = 'hex pin'
    nf.polygon3(sk4, [(xs, oy + corner * math.sin(math.radians(60 * i)), za + corner * math.cos(math.radians(60 * i)))
                      for i in range(6)])
    pin = nf.extrude(comp, sk4.profiles.item(0), -sgn * pin_len, NEW).bodies.item(0)
    sk5 = comp.sketches.add(start)
    sk5.name = 'hex pin chamfer'
    nf.circle3(sk5, (xs, oy, za), 2 * corner)
    taper = -math.degrees(math.atan((corner - (af / 2 - p['PIN_CHAMFER'])) / pin_len))
    nf.extrude(comp, sk5.profiles.item(0), -sgn * pin_len, INTERSECT, [pin], taper_deg=taper)
    nf.combine(comp, body, [pin], JOIN)

    # round pin into the block
    end, sgn2 = nf.plane_x(comp, xe)
    end.name = 'drum end'
    sk6 = comp.sketches.add(end)
    sk6.name = 'round pin'
    nf.circle3(sk6, (xe, oy, za), p['DRUM_ROUND_PIN'][0])
    nf.extrude(comp, sk6.profiles.item(0), sgn2 * p['DRUM_ROUND_PIN'][1], JOIN, [body])
    log(f'drum: x {xs:.3f} .. {xe:.3f}, axis z {za}, twist {TWIST_SIGN * twist:.2f} deg, hex pin {pin_len:.2f}')


def drum_block(comp, inp, log):
    """Half.drum_block3d(): bearing block on the PCB. Top and far end rounded to BLOCK_R; a U slot open upward round
    the drum's round pin with a narrowed snap-in mouth; two pegs into the PCB's holes. z = 0 is the PCB top."""
    p, d = inp['params'], inp['drum']
    ox, oy, L = _drum_frame(inp)
    bx0, bx1 = d['block_x']
    hw = p['BLOCK_HALF_W']
    body = nf.rounded_box(comp, ox + bx0, ox + bx1, oy - hw, oy + hw, 0, p['BLOCK_TOP'], p['BLOCK_R'], 1, 'drum block')
    slot_x1 = ox + p['DRUM_GAP'] + p['DRUM_W'] + p['DRUM_ROUND_PIN'][1] + 0.3
    sp, sgn = nf.plane_x(comp, ox + bx0 - 0.1)
    sp.name = 'slot start'
    sk = comp.sketches.add(sp)
    sk.name = 'slot'
    nf.circle3(sk, (ox + bx0 - 0.1, oy, p['EC10_AXIS']), 2 * p['BLOCK_SLOT_R'])
    nf.extrude(comp, sk.profiles.item(0), sgn * (slot_x1 - (ox + bx0 - 0.1)), CUT, [body])
    mouth = nf.box(comp, ox + bx0 - 0.1, slot_x1, oy - p['BLOCK_LIP'] / 2, oy + p['BLOCK_LIP'] / 2, p['EC10_AXIS'],
                   p['BLOCK_TOP'] + 0.1, 'mouth')
    nf.combine(comp, body, [mouth], CUT)
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.name = 'pegs'
    for peg in d['pegs']:
        nf.circle(sk, *peg['xy'], p['BLOCK_PEG'][0], ident=peg['id'], expr='BLOCK_PEG_0')
    nf.extrude(comp, list(sk.profiles), -p['BLOCK_PEG'][1], JOIN, [body], expr='BLOCK_PEG_1')
    log(f'drum block: x {ox + bx0:.3f} .. {ox + bx1:.3f}, slot to {slot_x1:.3f}')


def drum_bezel(comp, inp, log):
    """Half.drum_bezel3d(): the flange flush in the plate hole with a ledge under the plate, a hood over the encoder
    (its far wall a leg down to the PCB) and one over the block, both open toward the drum, through-cuts under the
    hoods and the drum, and a BEZEL_FILLET round the hoods' feet on the flange. z = 0 is the PCB top."""
    p, d = inp['params'], inp['drum']
    ox, oy, L = _drum_frame(inp)
    zl, z0, z1 = p['PLATE_GAP'] - p['BEZEL_LEDGE_T'], p['PLATE_GAP'], p['PLATE_GAP'] + p['PLATE_T']

    pl = nf.plane_at(comp, z0)
    pl.name = 'flange bottom'
    sk = comp.sketches.add(pl)
    sk.name = 'flange'
    nf.rounded_rect(sk, d['bezel_box'])
    body = nf.extrude(comp, sk.profiles.item(0), z1 - z0, NEW).bodies.item(0)
    body.name = 'drum bezel'
    ll = nf.plane_at(comp, zl)
    ll.name = 'ledge bottom'
    sk = comp.sketches.add(ll)
    sk.name = 'ledge'
    nf.rounded_rect(sk, d['ledge_box'])
    ledge = nf.extrude(comp, sk.profiles.item(0), p['BEZEL_LEDGE_T'], NEW).bodies.item(0)
    sk = comp.sketches.add(ll)
    sk.name = 'ledge notches'
    for h in inp['pcb_holes']:
        nf.circle(sk, *h['xy'], p['BOSS_D'] + 2.0, ident=h['id'], expr='BOSS_D + 2 mm')
    nf.extrude(comp, list(sk.profiles), p['BEZEL_LEDGE_T'] + 0.1, CUT, [ledge])
    nf.combine(comp, body, [ledge], JOIN)

    w, c = p['BEZEL_WALL'], p['BEZEL_CLEAR']
    ex0, ey, etop = p['EC10_BRACKET'][0] - c, p['EC10_BODY'][3] + c, p['EC10_BODY'][4] + c
    outer = nf.rounded_box(comp, ox + ex0 - w, ox + 0.2, oy - ey - w, oy + ey + w, z0, etop + w, p['HOOD_OUT_R'], -1,
                           'encoder hood')
    inner = nf.rounded_box(comp, ox + ex0, ox + 0.3, oy - ey, oy + ey, z0 - 0.1, etop, p['HOOD_IN_R'], -1, 'encoder hood in')
    nf.combine(comp, outer, [inner], CUT)
    nf.combine(comp, body, [outer], JOIN)
    leg = nf.box(comp, ox + ex0 - w, ox + ex0, oy - p['BEZEL_LEG_HW'], oy + p['BEZEL_LEG_HW'], 0, zl + 0.01, 'leg')
    nf.combine(comp, body, [leg], JOIN)
    bx0, bx1 = d['block_x']
    bend = d['hood_ends'][1]
    outer = nf.rounded_box(comp, ox + bx0 - 0.1, ox + bend, oy - ey - w, oy + ey + w, z0, etop + w, p['HOOD_OUT_R'], 1,
                           'block hood')
    inner = nf.rounded_box(comp, ox + bx0 - 0.2, ox + bx1 + c, oy - ey, oy + ey, z0 - 0.1, p['BLOCK_TOP'],
                           p['HOOD_IN_R'], 1, 'block hood in')
    nf.combine(comp, outer, [inner], CUT)
    nf.combine(comp, body, [outer], JOIN)

    rr = d['drum_d'] / 2
    cuts = [nf.box(comp, ox + 0.2, ox + bx0 - 0.1, oy - rr - 0.2, oy + rr + 0.2, zl - 0.1, z1 + 0.1, 'drum gap'),
            nf.box(comp, ox + ex0, ox + 0.3, oy - ey, oy + ey, zl - 0.1, z1 + 0.1, 'under encoder hood'),
            nf.box(comp, ox + bx0 - 0.2, ox + bx1 + c, oy - ey, oy + ey, zl - 0.1, z1 + 0.1, 'under block hood')]
    nf.combine(comp, body, cuts, CUT)

    # fillet where the hoods stand on the flange: edges in the flange top next to a face that rises above it
    def foot(e):
        bb = e.boundingBox
        if abs(bb.minPoint.z * 10 - z1) > 1e-3 or abs(bb.maxPoint.z * 10 - z1) > 1e-3:
            return False
        return any(f.boundingBox.maxPoint.z * 10 > z1 + 0.5 for f in e.faces)
    edges = [e for e in body.edges if foot(e)]
    nf.fillet(comp, edges, p['BEZEL_FILLET'])
    log(f'drum bezel: flange z {z0} .. {z1}, ledge from {zl}, {len(edges)} hood foot edges filleted')


# part name (the exported STL) -> builder; the build makes them in this order
BUILDERS = {
    'tray': tray,
    'plate': plate,
    'wheel': wheel,
    'wheel-cap': wheel_cap,
    'stand-3': stand(3),
    'stand-6': stand(6),
    'stand-9': stand(9),
    'drum': drum,
    'drum-block': drum_block,
    'drum-bezel': drum_bezel,
}
DRUM_PARTS = {'drum', 'drum-block', 'drum-bezel'}     # only for a half with the drum dial (input.json 'drum')
