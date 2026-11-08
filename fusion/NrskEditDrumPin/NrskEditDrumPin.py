"""Edit (2026-11, edit period): the drum's hex pin keeps its across-flats (PIN_AF) over its whole length.

The build chamfered the pin with a cone from its corners down to AF/2 - PIN_CHAMFER at the tip, so it tapered all
the way and its tip was nearly round. Here the cone widens instead (+5 deg: clear of the prism's corners, so the
intersection leaves the hex prism as it is; at 0 deg the cylinder runs exactly through the corners and splits the
faces there) and only the tip's six edges get a DRUM_PIN_TIP chamfer, to find the rotor's hex hole. Applied once
per design (nrsk.edits).
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

EDIT = 'drum-pin-straight'
DRUM_PIN_TIP = 0.2       # mm, chamfer on the tip's edges


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    side = nf.design_side(design)
    log.side = side
    edits = (nf.get_attr(design, 'edits') or '').split()
    if EDIT in edits:
        raise RuntimeError(f'{EDIT} is already in this design')
    parts = nf.part_components(design)
    if 'drum' not in parts:
        raise RuntimeError('this design has no drum')
    drum = parts['drum']
    cones = [f for f in drum.features.extrudeFeatures
             if f.operation == adsk.fusion.FeatureOperations.IntersectFeatureOperation]
    if len(cones) != 1:
        raise RuntimeError(f'expected one intersecting extrude (the pin chamfer cone), found {len(cones)}')
    cone = cones[0]
    taper = cone.taperAngleOne
    log(f'pin chamfer cone: taper {taper.expression} -> 5 deg (widening)')
    taper.expression = '5 deg'
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    # the pin's tip: the drum body's planar face furthest toward -x, a hexagon
    bodyd = drum.bRepBodies.item(0)
    planes = [f for f in bodyd.faces if f.geometry.objectType == adsk.core.Plane.classType()
              and abs(abs(f.geometry.normal.x) - 1) < 1e-6]
    tip = min(planes, key=lambda f: f.boundingBox.minPoint.x)
    log(f'{drum.bRepBodies.count} bodies; tip face at x {tip.boundingBox.minPoint.x * 10:.3f} with {tip.edges.count} edges')
    if tip.edges.count != 6:
        raise RuntimeError(f'the pin tip face has {tip.edges.count} edges, expected 6')
    tip_x = tip.boundingBox.minPoint.x * 10
    feats = drum.features.chamferFeatures
    if feats.count:                 # a run that stopped after the chamfer: do not chamfer twice
        log(f'the tip already has its chamfer ({feats.count} chamfer feature)')
    else:
        coll = adsk.core.ObjectCollection.create()
        for e in tip.edges:
            coll.add(e)
        inp = feats.createInput2()
        inp.chamferEdgeSets.addEqualDistanceChamferEdgeSet(coll, nf.val(DRUM_PIN_TIP), False)
        feats.add(inp)
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    nf.set_attr(design, 'edits', ' '.join(edits + [EDIT]))
    app.activeDocument.save(f'NrskEditDrumPin: {EDIT}')
    log(f'{EDIT}: tip at x {tip_x:.3f}, {DRUM_PIN_TIP} mm chamfer')
    return f'{side}: {EDIT} applied'


def run(context):
    nrsk_fusion.run_script('NrskEditDrumPin', body)
