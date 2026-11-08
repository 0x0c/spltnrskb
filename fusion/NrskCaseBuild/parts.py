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


# part name (the exported STL) -> builder; the build makes them in this order
BUILDERS = {
    'wheel': wheel,
}
