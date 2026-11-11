"""Edit (2026-11, edit period): the roots of the wheel's and the drum's pins sunk into the part, for larger
fillets; then NrskCaseExport.

NrskEditPinFillets could only use the room above the part's surface (0.25 mm under the encoder on the wheel).
Here a round pocket is cut into the part round each pin, the pin now rises from the pocket's floor, and the
fillet there is as large as the pocket's depth plus the room above the surface:

                    pocket depth  pocket d  fillet  fillet ends above the surface (as before or less)
  wheel hex pin         0.5          4.0     0.7     0.2   (encoder face at 0.3)
  drum hex pin          0.6          4.8     1.2     0.6
  drum round pin        0.6          4.2     0.9     0.3   (bearing block at 0.4)

The wheel keeps 1.2 mm between the pocket and the axle bore below it. The cut also takes away the small fillets
of NrskEditPinFillets (it runs from the pocket's floor to above them, round the pin's own section).
Everything is measured before anything is changed. Applied once per design (nrsk.edits), after pin-root-fillets.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
for p in (HERE, os.path.join(HERE, '..', 'common'), os.path.join(HERE, '..', 'NrskCaseExport'),
          os.path.join(HERE, '..', 'NrskEditPinFillets')):
    if p not in sys.path:
        sys.path.insert(0, p)

import adsk.core  # noqa: E402
import adsk.fusion  # noqa: E402

import nrsk_fusion  # noqa: E402

EDIT = 'pin-root-recess'
AFTER = 'pin-root-fillets'
# depth of the pocket, its diameter, the fillet, how far above the surface the cut runs (over the old fillet)
WHEEL = (0.5, 4.0, 0.7, 0.3)
DRUM_HEX = (0.6, 4.8, 1.2, 0.7)
DRUM_ROUND = (0.6, 4.2, 0.9, 0.4)
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    pf = importlib.reload(importlib.import_module('NrskEditPinFillets'))
    side = nf.design_side(design)
    log.side = side
    edits = (nf.get_attr(design, 'edits') or '').split()
    if EDIT in edits:
        raise RuntimeError(f'{EDIT} is already in this design')
    if AFTER not in edits:
        raise RuntimeError(f'run NrskEditPinFillets first ({AFTER} is not in this design)')
    parts = nf.part_components(design)
    p = nf.stored_input(design)['params']
    corner = p['PIN_AF'] / math.sqrt(3)
    jobs = []

    def plan(label, comp, ax, high, round_pin, radius, length, dims):
        depth, pocket_d, r_fillet, over = dims
        bodyd = comp.bRepBodies.item(0)
        tip = pf.end_face(bodyd, ax, high)
        c = pf.centre(tip)
        dirn = 1 if high else -1                    # from the root toward the tip
        root = c[ax] - dirn * length
        others = [i for i in range(3) if i != ax]
        corners = []
        if not round_pin:
            seen = {}
            for e in bodyd.edges:
                if e.geometry.objectType != adsk.core.Line3D.classType():
                    continue
                a, b = pf.mm(e.startVertex.geometry), pf.mm(e.endVertex.geometry)
                if abs(a[ax] - b[ax]) < 0.5 or any(abs(a[i] - b[i]) > 1e-3 for i in others):
                    continue
                if abs(math.hypot(*(a[i] - c[i] for i in others)) - radius) > pf.TOL:
                    continue
                seen[tuple(round(a[i], 3) for i in others)] = tuple(a[i] for i in others)
            corners = sorted(seen.values(), key=lambda q: math.atan2(q[1] - c[others[1]], q[0] - c[others[0]]))
            if len(corners) != 6:
                raise RuntimeError(f'{label}: found {len(corners)} corner edges along the pin, expected 6')
        if (pocket_d / 2 - radius) < r_fillet:
            raise RuntimeError(f'{label}: the pocket is too narrow for the fillet')
        log(f'{label}: tip at {"xyz"[ax]} {c[ax]:.3f}, surface at {root:.3f}, pocket {depth} deep d {pocket_d}, '
            f'fillet {r_fillet}')
        jobs.append(dict(label=label, comp=comp, ax=ax, high=high, round_pin=round_pin, radius=radius,
                         length=length, depth=depth, pocket_d=pocket_d, r=r_fillet, over=over, c=c, dirn=dirn,
                         root=root, others=others, corners=corners))

    if 'wheel' not in parts:
        raise RuntimeError('this design has no wheel')
    plan('wheel hex pin', parts['wheel'], 2, True, False, corner, p['HUB_CLEAR'] + p['PIN_ENGAGE'], WHEEL)
    if 'drum' in parts:
        plan('drum hex pin', parts['drum'], 0, False, False, corner,
             p['DRUM_GAP'] - p['EC10_ROTOR_FACE'] + p['DRUM_PIN_ENGAGE'], DRUM_HEX)
        plan('drum round pin', parts['drum'], 0, True, True, p['DRUM_ROUND_PIN'][0] / 2, p['DRUM_ROUND_PIN'][1],
             DRUM_ROUND)
    before = {j['label']: j['comp'].bRepBodies.item(0).volume for j in jobs}

    def point(j, a, uv):
        q = [0.0, 0.0, 0.0]
        q[j['ax']] = a
        q[j['others'][0]], q[j['others'][1]] = uv
        return tuple(q)

    for j in jobs:                                   # the pockets
        comp, ax = j['comp'], j['ax']
        floor = j['root'] - j['dirn'] * j['depth']
        if ax == 2:
            plane, sign = nf.plane_at(comp, floor), 1
        else:
            plane, sign = nf.plane_x(comp, floor)
        plane.name = f'{j["label"]} pocket'
        sk = comp.sketches.add(plane)
        sk.name = f'{j["label"]} pocket'
        cuv = (j['c'][j['others'][0]], j['c'][j['others'][1]])
        nf.circle3(sk, point(j, floor, cuv), j['pocket_d'])
        if j['round_pin']:
            nf.circle3(sk, point(j, floor, cuv), 2 * j['radius'])
        else:
            nf.polygon3(sk, [point(j, floor, uv) for uv in j['corners']])
        rings = [pr for pr in sk.profiles if pr.profileLoops.count == 2]
        if len(rings) != 1:
            raise RuntimeError(f'{j["label"]}: {len(rings)} ring profiles in the pocket sketch, expected 1')
        nf.extrude(comp, rings[0], j['dirn'] * sign * (j['depth'] + j['over']), CUT, [comp.bRepBodies.item(0)])
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    for j in jobs:
        v = j['comp'].bRepBodies.item(0).volume
        log(f'{j["label"]}: pocket cut, {j["comp"].bRepBodies.count} bodies, volume {before[j["label"]] * 1000:.3f} '
            f'-> {v * 1000:.3f} mm3')
        if j['comp'].bRepBodies.count != 1 or not v < before[j['label']]:
            raise RuntimeError(f'{j["label"]}: the pocket did not cut the part as expected')
    for j in jobs:                                   # the fillets, each found on the body as it is now
        bodyd = j['comp'].bRepBodies.item(0)
        tip = pf.end_face(bodyd, j['ax'], j['high'])
        a, dist, edges = pf.root_edges(bodyd, j['ax'], tip, j['radius'], j['round_pin'])
        log(f'{j["label"]}: root at {a:.3f} ({dist:.3f} from the tip), {len(edges)} edges')
        if abs(dist - (j['length'] + j['depth'])) > 0.05:
            raise RuntimeError(f'{j["label"]}: the root is {dist:.3f} from the tip, expected '
                               f'{j["length"] + j["depth"]:.3f}')
        if not j['round_pin'] and len(edges) != 6:
            raise RuntimeError(f'{j["label"]}: {len(edges)} root edges, expected 6')
        mid = j['comp'].bRepBodies.item(0).volume
        nf.fillet(j['comp'], edges, j['r']).name = f'{j["label"]} recessed root'
        v = j['comp'].bRepBodies.item(0).volume
        log(f'{j["label"]}: fillet {j["r"]}, volume {mid * 1000:.3f} -> {v * 1000:.3f} mm3')
        if j['comp'].bRepBodies.count != 1 or not v > mid:
            raise RuntimeError(f'{j["label"]}: the fillet did not add to the part as expected')
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    nf.set_attr(design, 'edits', ' '.join(edits + [EDIT]))
    app.activeDocument.save(f'NrskEditPinRecess: {EDIT}')
    log('--- NrskCaseExport')
    export = importlib.reload(importlib.import_module('NrskCaseExport'))
    return f'{side}: {EDIT} applied\n{export.body(app, design, log)}'


def run(context):
    nrsk_fusion.run_script('NrskEditPinRecess', body)
