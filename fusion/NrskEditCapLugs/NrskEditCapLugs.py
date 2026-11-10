"""Edit (2026-11, edit period): the wheel cap back to its round, stepped shape, held by two lugs.

History of the cap on the designs: the build made it round and stepped, so it could turn in its round seat; the
edit cap-key added one lug; the edit cap-straight cut its ends flat instead. This edit goes back to the round cap
and gives it a lug on each wall (make_case.py CAP_KEY, Half.cap_key; input.json 'cap_key'), reaching under the
ledge into slots in the tray.

On the tray: the straight seat (cap-straight) and the single lug slot (cap-key) are suppressed, the round tiers are
restored and the two slots cut. The cap component is rebuilt (parts.wheel_cap, with its lugs). Applied once per
design (nrsk.edits).
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

EDIT = 'cap-lugs'
RESTORE = {'cap lower tier', 'cap shoulder'}            # the round cap's tiers
DROP = {'cap lug slot', 'cap seat', 'cap seat cavity'}  # the single lug's slot, the straight seat


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
    bad = [b for b in sync.unsupported(old, new) if b != 'cap_key changed']
    if bad or 'cap_key' not in new:
        raise RuntimeError('input.json differs from the design in more than the cap lugs: run NrskCaseSync first\n'
                           + '\n'.join(bad))
    root = design.rootComponent
    occs = {nf.get_attr(o.component, 'part'): o for o in root.occurrences}
    tray = occs['tray'].component

    # the tray: tiers back, the old slot and the straight seat out (with the combine that cut the seat)
    seat_index = None
    for f in tray.features.extrudeFeatures:
        name = profile_sketch(f)
        to = f.timelineObject
        if name in RESTORE and to.isSuppressed:
            to.isSuppressed = False
            log(f'restored {name}')
        elif name in DROP and not to.isSuppressed:
            if name == 'cap seat':
                seat_index = to.index
            to.isSuppressed = True
            log(f'suppressed {name}')
    if seat_index is not None:
        for c in tray.features.combineFeatures:
            if c.timelineObject.index > seat_index and not c.timelineObject.isSuppressed:
                c.timelineObject.isSuppressed = True
                log('suppressed the combine that cut the straight seat')
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    parts.cut_cap_lug_slots(tray, new, tray.bRepBodies.item(0), log)

    # the cap: rebuilt round, with its lugs
    transform = occs['wheel-cap'].transform2
    occs['wheel-cap'].deleteMe()
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.transform2 = transform
    cap = occ.component
    cap.name = 'wheel-cap'
    nf.set_attr(cap, 'part', 'wheel-cap')
    parts.wheel_cap(cap, new, log)

    up = design.userParameters
    for name, (x, unit) in nf.parameter_values(new['params']).items():
        prm = up.itemByName(name)
        if prm is None:
            up.add(name, adsk.core.ValueInput.createByString(f'{x} {unit}'.strip()), unit, 'make_case.py')
        elif unit == 'mm' and abs(prm.value * 10 - x) > 1e-9:      # value is in cm
            prm.expression = f'{x} {unit}'
            log(f'parameter {name} = {x} {unit}')
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    nf.store_input(design, new)
    nf.set_attr(design, 'edits', ' '.join(edits + [EDIT]))
    app.activeDocument.save(f'NrskEditCapLugs: {EDIT}')
    log(f'{EDIT} applied')
    return f'{side}: {EDIT} applied'


def run(context):
    nrsk_fusion.run_script('NrskEditCapLugs', body)
