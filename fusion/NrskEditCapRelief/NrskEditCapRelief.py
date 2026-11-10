"""Edit (2026-11, edit period): the wheel cap clear of the printed plate's bosses beside the wheel.

The two plate screws beside the wheel stand 19.6 mm from its axis, placed to clear the cap's top tier (r 17.05)
by the insert hole only. The pocket in the wall top (BOSS_POCKET, d 6.0) and the printed plate's boss in it
(PLATE_BOSS, d 5.6) reach 0.25 mm into the cap there, so the all-printed plate did not seat (make_case
check_plate_cap). Here the cap gets the same pocket: a cylinder of the pocket's diameter cut from its top, at each
of those two screws. Moving the screws out instead would move the feet and the stands with them.
Applied once per design (nrsk.edits).
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
for p in (HERE, os.path.join(HERE, '..', 'common')):
    if p not in sys.path:
        sys.path.insert(0, p)

import adsk.core  # noqa: E402
import adsk.fusion  # noqa: E402

import nrsk_fusion  # noqa: E402

EDIT = 'cap-boss-relief'
REACH = 6.0      # mm: a screw whose pocket comes this close to the cap's top tier gets a relief
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    side = nf.design_side(design)
    log.side = side
    edits = (nf.get_attr(design, 'edits') or '').split()
    if EDIT in edits:
        raise RuntimeError(f'{EDIT} is already in this design')
    parts = nf.part_components(design)
    if 'wheel-cap' not in parts:
        raise RuntimeError('this design has no wheel cap')
    cap = parts['wheel-cap']
    inp = nf.stored_input(design)
    p = inp['params']
    (wx, wy), r = inp['wheel']['xy'], inp['wheel']['r']
    tier = r + p['WHEEL_CUT'] + p['CAP_SHOULDER']                  # the cap's top tier (before CAP_FIT)
    pocket_d, pocket_h = p['BOSS_POCKET']
    near = [q for q in inp['screws'] if math.hypot(q['xy'][0] - wx, q['xy'][1] - wy) < tier + REACH]
    if len(near) != 2:
        raise RuntimeError(f'expected 2 screws beside the wheel, found {len(near)}')
    wall_top = p['FLOOR'] + p['STANDOFF'] + p['PCB_T'] + p['PLATE_GAP']
    bodyd = cap.bRepBodies.item(0)
    before = bodyd.volume
    plane = nf.plane_at(cap, wall_top - pocket_h)
    plane.name = 'boss relief'
    sk = cap.sketches.add(plane)
    sk.name = 'boss relief'
    for q in near:
        nf.circle(sk, *q['xy'], pocket_d, ident=q['id'], expr='BOSS_POCKET_0')
    nf.extrude(cap, list(sk.profiles), pocket_h + 0.1, CUT, [bodyd])
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    after = cap.bRepBodies.item(0).volume
    log(f'cap: relief d {pocket_d} x {pocket_h} at {[q["id"] for q in near]}, '
        f'{cap.bRepBodies.count} bodies, volume {before * 1000:.2f} -> {after * 1000:.2f} mm3')
    if cap.bRepBodies.count != 1 or not after < before:
        raise RuntimeError('the relief did not cut the cap as expected')
    nf.set_attr(design, 'edits', ' '.join(edits + [EDIT]))
    app.activeDocument.save(f'NrskEditCapRelief: {EDIT}')
    return f'{side}: {EDIT} applied'


def run(context):
    nrsk_fusion.run_script('NrskEditCapRelief', body)
