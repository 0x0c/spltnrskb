"""Edit (2026-11, edit period): an anti-rotation lug on the wheel cap and its slot in the tray.

The cap is cut from the wall by circles, so it could turn in its round seat. A lug hangs from the cap's lower tier
into a slot in the tray under the ledge (make_case.py CAP_KEY, Half.cap_key; the shapes come from input.json
'cap_key'). Applied once per design (nrsk.edits); afterwards the design's stored input includes the lug, so
NrskCaseSync carries on as before.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
for p in (HERE, os.path.join(HERE, '..', 'common'), os.path.join(HERE, '..', 'NrskCaseSync')):
    if p not in sys.path:
        sys.path.insert(0, p)

import adsk.core  # noqa: E402
import adsk.fusion  # noqa: E402

import nrsk_fusion  # noqa: E402
import NrskCaseSync  # noqa: E402

EDIT = 'cap-key'
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    sync = importlib.reload(NrskCaseSync)
    side = nf.design_side(design)
    log.side = side
    edits = (nf.get_attr(design, 'edits') or '').split()
    if EDIT in edits:
        raise RuntimeError(f'{EDIT} is already in this design')
    old, new = nf.stored_input(design), nf.load_input(side)
    bad = [b for b in sync.unsupported(old, new) if b != 'cap_key changed']
    if bad or 'cap_key' not in new:
        raise RuntimeError('input.json differs from the design in more than the cap lug: run NrskCaseSync first\n'
                           + '\n'.join(bad))
    key = new['cap_key']
    parts = nf.part_components(design)
    tray, cap = parts['tray'], parts['wheel-cap']

    # the slot in the tray
    plane = nf.plane_at(tray, key['slot_z'])
    plane.name = 'cap lug slot'
    sk = tray.sketches.add(plane)
    sk.name = 'cap lug slot'
    for poly in key['slot']:
        nf.polygon(sk, [tuple(q) for q in poly])
    nf.extrude(tray, list(sk.profiles), key['top_z'] + 0.01 - key['slot_z'], CUT, [tray.bRepBodies.item(0)])

    # the lug on the cap
    plane = nf.plane_at(cap, key['lug_z'])
    plane.name = 'cap lug'
    sk = cap.sketches.add(plane)
    sk.name = 'cap lug'
    for poly in key['lug']:
        nf.polygon(sk, [tuple(q) for q in poly])
    capbody = cap.bRepBodies.item(0)
    nf.extrude(cap, list(sk.profiles), key['top_z'] - key['lug_z'], JOIN, [capbody])

    # the new constants as user parameters, and the input the design now matches
    up = design.userParameters
    for name, (x, unit) in nf.parameter_values(new['params']).items():
        if up.itemByName(name) is None:
            up.add(name, adsk.core.ValueInput.createByString(f'{x} {unit}'.strip()), unit, 'make_case.py')
            log(f'parameter {name} added = {x} {unit}')
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    nf.store_input(design, new)
    nf.set_attr(design, 'edits', ' '.join(edits + [EDIT]))
    app.activeDocument.save(f'NrskEditCapKey: {EDIT}')
    log(f'{EDIT}: slot from z {key["slot_z"]} and lug from z {key["lug_z"]} up to {key["top_z"]}')
    return f'{side}: {EDIT} applied'


def run(context):
    nrsk_fusion.run_script('NrskEditCapKey', body)
