"""Edit (2026-11, edit period): the wheel cap with straight end faces instead of round ones.

The cap was the wall cut out by two stacked circles round the wheel, so it could turn in its round seat (a hidden
lug, the earlier edit cap-key, stopped it). Now the cap is the corner of the wall cut off by two flat faces square
to the walls (make_case.py Half.cap_region, input.json 'cap'): its ends bear on the tray, so it cannot turn, and
outside the opening it sits on the wall below, so it needs no ledge.

On the tray: the circular tiers and the lug slot are suppressed and the straight seat is cut. The cap component is
replaced by one built the new way (parts.wheel_cap). Applied once per design (nrsk.edits).
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
for p in (HERE, os.path.join(HERE, '..', 'common'), os.path.join(HERE, '..', 'NrskCaseSync'),
          os.path.join(HERE, '..', 'NrskCaseBuild')):
    if p not in sys.path:
        sys.path.insert(0, p)

import adsk.core  # noqa: E402
import adsk.fusion  # noqa: E402

import nrsk_fusion  # noqa: E402
import NrskCaseSync  # noqa: E402
import parts  # noqa: E402

EDIT = 'cap-straight'
OLD_SKETCHES = {'cap lower tier', 'cap shoulder', 'cap lug slot'}     # the tray's cuts for the round cap and its lug


def profile_sketch(feature):
    prof = feature.profile
    if isinstance(prof, adsk.core.ObjectCollection):
        prof = prof.item(0)
    return prof.parentSketch.name if prof else None


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    sync = importlib.reload(NrskCaseSync)
    importlib.reload(parts)
    side = nf.design_side(design)
    log.side = side
    edits = (nf.get_attr(design, 'edits') or '').split()
    if EDIT in edits:
        raise RuntimeError(f'{EDIT} is already in this design')
    old, new = nf.stored_input(design), nf.load_input(side)
    bad = [b for b in sync.unsupported(old, new) if b != 'cap changed']
    if bad or 'cap' not in new:
        raise RuntimeError('input.json differs from the design in more than the cap: run NrskCaseSync first\n'
                           + '\n'.join(bad))
    root = design.rootComponent
    occs = {nf.get_attr(o.component, 'part'): o for o in root.occurrences}
    tray = occs['tray'].component

    # the tray: suppress the round cap's tiers and the lug slot
    gone = []
    for f in tray.features.extrudeFeatures:
        if profile_sketch(f) in OLD_SKETCHES and not f.timelineObject.isSuppressed:
            f.timelineObject.isSuppressed = True
            gone.append(profile_sketch(f))
    log('suppressed on the tray: ' + ', '.join(gone))
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')

    # the cap: a new component built the new way, in place of the old one
    transform = occs['wheel-cap'].transform2
    occs['wheel-cap'].deleteMe()
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.transform2 = transform
    cap = occ.component
    cap.name = 'wheel-cap'
    nf.set_attr(cap, 'part', 'wheel-cap')
    parts.wheel_cap(cap, new, log)

    # the tray: the straight seat
    parts.cut_cap_from_tray(tray, new, log)
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    nf.store_input(design, new)
    nf.set_attr(design, 'edits', ' '.join(edits + [EDIT]))
    app.activeDocument.save(f'NrskEditCapStraight: {EDIT}')
    log(f'{EDIT} applied')
    return f'{side}: {EDIT} applied'


def run(context):
    nrsk_fusion.run_script('NrskEditCapStraight', body)
