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
    body = nf.extrude(comp, nf.largest_profile(sk), t, NEW).bodies.item(0)
    body.name = 'wheel'

    # axle bore from below
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.name = 'bore'
    nf.circle(sk, x, y, p['BORE_D'])
    nf.extrude(comp, sk.profiles.item(0), p['BORE_DEPTH'], CUT, [body])

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
            nf.circle(sk, *feet[fid], p['STAND_POCKET'][0])
        for pr in sk.profiles:
            nf.extrude(comp, pr, p['STAND_POCKET'][1] + 0.01, CUT, [body])
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

    def circles(plane, name, pts, d):
        sk = sketch(plane, name)
        for q in pts:
            nf.circle(sk, *q, d)
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
    holes = [h['xy'] for h in inp['pcb_holes']]
    nf.extrude(comp, circles(floor, 'bosses', holes, p['BOSS_D']), p['STANDOFF'], JOIN, [body])
    pilot = nf.plane_at(comp, 0.6)
    pilot.name = 'pilot bottom'
    nf.extrude(comp, circles(pilot, 'pilot holes', holes, p['PILOT_D']), p['STANDOFF'] + p['FLOOR'] - 0.6, CUT, [body])

    # case screws from below (cuts from the bottom face take the depth as it is: the code starts them 0.01 below)
    screws = [q['xy'] for q in inp['screws']]
    nf.extrude(comp, circles(xy, 'screw holes', screws, p['SCREW_D']), wall_top + 0.02, CUT, [body])
    nf.extrude(comp, circles(xy, 'counterbores', screws, p['SCREW_CB'][0]), p['SCREW_CB'][1], CUT, [body])
    pk = nf.plane_at(comp, wall_top - p['BOSS_POCKET'][1])
    pk.name = 'boss pockets'
    nf.extrude(comp, circles(pk, 'boss pockets', screws, p['BOSS_POCKET'][0]), p['BOSS_POCKET'][1] + 0.01, CUT, [body])
    nt = nf.plane_at(comp, wall_top - p['BOSS_POCKET'][1] - p['NUT_TRAP'][1])
    nt.name = 'nut traps'
    sk = sketch(nt, 'nut traps')
    for x, y in screws:
        nf.polygon(sk, nf.hexagon_pts(x, y, p['NUT_TRAP'][0] / math.sqrt(3)))
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
    nf.extrude(comp, circles(floor, 'wheel post', [(wx, wy)], p['POST_D']), p['WHEEL_GAP'] + p['BORE_DEPTH'] - 0.3,
               JOIN, [body])
    if 'reset' in inp:
        nf.extrude(comp, circles(xy, 'reset', [inp['reset']['xy']], p['RESET_D']), p['FLOOR'] + 0.02, CUT, [body])
    feet = [f['xy'] for f in inp['feet']]
    nf.extrude(comp, circles(xy, 'foot recesses', feet, p['FOOT_D']), p['FOOT_DEPTH'], CUT, [body])
    log(f"tray: wall top {wall_top:.2f}, {len(holes)} bosses, {len(screws)} screws, {len(inp['slots'])} ports, "
        f"{len(feet)} feet")


# part name (the exported STL) -> builder; the build makes them in this order
BUILDERS = {
    'tray': tray,
    'wheel': wheel,
    'wheel-cap': wheel_cap,
    'stand-3': stand(3),
    'stand-6': stand(6),
    'stand-9': stand(9),
}
