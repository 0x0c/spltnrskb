"""Edit (2026-11, edit period): the thumbwheel's hex pin keeps its across-flats (PIN_AF) over its whole length.

The build chamfered the pin with a cone from its corners down to AF/2 - PIN_CHAMFER at the tip. The cone narrows
all the way, so 0.9 mm above the hub the section is already a circle smaller than the rotor's hex hole (1.72 A/F):
of the 2 mm inside the rotor only the first 0.3 mm had corners, and the wheel would slip in the encoder instead
of turning it. The same fault was fixed on the drum by NrskEditDrumPin; this is that edit for the wheel.

Here the cone widens instead (+5 deg: clear of the prism's corners, so the intersection leaves the hex prism as it
is) and only the tip's six edges get a WHEEL_PIN_TIP chamfer, to find the rotor's hex hole. gen/pin_coupon.py
builds its test pins the same way. Applied once per design (nrsk.edits).

Not yet run in Fusion when it was written (2026-11-10): check the log and the exported wheel (the pin's section
must be a hexagon of PIN_AF up to 0.2 mm below the tip) after the first run.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
for p in (HERE, os.path.join(HERE, '..', 'common')):
    if p not in sys.path:
        sys.path.insert(0, p)

import adsk.core  # noqa: E402
import adsk.fusion  # noqa: E402

import nrsk_fusion  # noqa: E402

EDIT = 'wheel-pin-straight'
WHEEL_PIN_TIP = 0.2      # mm, chamfer on the tip's edges (= pin_coupon.PIN_TIP)


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    side = nf.design_side(design)
    log.side = side
    edits = (nf.get_attr(design, 'edits') or '').split()
    if EDIT in edits:
        raise RuntimeError(f'{EDIT} is already in this design')
    parts = nf.part_components(design)
    if 'wheel' not in parts:
        raise RuntimeError('this design has no wheel')
    wheel = parts['wheel']
    cones = [f for f in wheel.features.extrudeFeatures
             if f.operation == adsk.fusion.FeatureOperations.IntersectFeatureOperation]
    if len(cones) != 1:
        raise RuntimeError(f'expected one intersecting extrude (the pin chamfer cone), found {len(cones)}')
    cone = cones[0]
    taper = cone.taperAngleOne
    log(f'pin chamfer cone: taper {taper.expression} -> 5 deg (widening)')
    taper.expression = '5 deg'
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    # the pin's tip: the wheel body's highest planar face, a hexagon
    bodyd = wheel.bRepBodies.item(0)
    planes = [f for f in bodyd.faces if f.geometry.objectType == adsk.core.Plane.classType()
              and abs(abs(f.geometry.normal.z) - 1) < 1e-6]
    tip = max(planes, key=lambda f: f.boundingBox.maxPoint.z)
    log(f'{wheel.bRepBodies.count} bodies; tip face at z {tip.boundingBox.maxPoint.z * 10:.3f} with {tip.edges.count} edges')
    if tip.edges.count != 6:
        raise RuntimeError(f'the pin tip face has {tip.edges.count} edges, expected 6')
    tip_z = tip.boundingBox.maxPoint.z * 10
    feats = wheel.features.chamferFeatures
    if feats.count:                 # a run that stopped after the chamfer: do not chamfer twice
        log(f'the tip already has its chamfer ({feats.count} chamfer feature)')
    else:
        coll = adsk.core.ObjectCollection.create()
        for e in tip.edges:
            coll.add(e)
        inp = feats.createInput2()
        inp.chamferEdgeSets.addEqualDistanceChamferEdgeSet(coll, nf.val(WHEEL_PIN_TIP), False)
        feats.add(inp)
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    nf.set_attr(design, 'edits', ' '.join(edits + [EDIT]))
    app.activeDocument.save(f'NrskEditWheelPin: {EDIT}')
    log(f'{EDIT}: tip at z {tip_z:.3f}, {WHEEL_PIN_TIP} mm chamfer')
    return f'{side}: {EDIT} applied'


def run(context):
    nrsk_fusion.run_script('NrskEditWheelPin', body)
