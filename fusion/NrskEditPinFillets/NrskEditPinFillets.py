"""Edit (2026-11, edit period): fillets at the roots of the wheel's and the drum's pins, then NrskCaseExport.

The pins met the part with a sharp inside corner, where a printed pin breaks first (the notch, and in FDM the
first layer of the pin). Each fillet is as large as the room next to the root allows with the part pushed all
the way toward its neighbour:
  wheel hex pin   WHEEL_PIN_ROOT  under the encoder's face, HUB_CLEAR (0.3) above the hub
  drum hex pin    DRUM_PIN_ROOT   between the drum and the encoder (1.05 from the drum face to the body, less
                                  DRUM_GAP 0.4 of end play)
  drum round pin  DRUM_ROUND_ROOT in DRUM_GAP (0.4) between the drum and the bearing block
The tray's axle post gets none: the wheel's bore (0.2 mm radial play) would ride up on it.
All edges are found before anything is changed, so a part that does not look as expected leaves the design
untouched. Applied once per design (nrsk.edits).
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
for p in (HERE, os.path.join(HERE, '..', 'common'), os.path.join(HERE, '..', 'NrskCaseExport')):
    if p not in sys.path:
        sys.path.insert(0, p)

import adsk.core  # noqa: E402
import adsk.fusion  # noqa: E402

import nrsk_fusion  # noqa: E402

EDIT = 'pin-root-fillets'
WHEEL_PIN_ROOT = 0.25    # mm
DRUM_PIN_ROOT = 0.6
DRUM_ROUND_ROOT = 0.3
TOL = 0.03               # mm, on the radius of a pin's corners / circle


def mm(p):
    return (p.x * 10, p.y * 10, p.z * 10)


def end_face(bodyd, ax, high):
    """The planar face normal to axis ax (0 x, 1 y, 2 z) at the body's high or low end: a pin's tip."""
    planes = [f for f in bodyd.faces if f.geometry.objectType == adsk.core.Plane.classType()
              and abs(abs(mm(f.geometry.normal)[ax]) - 10) < 1e-5]
    if not planes:
        raise RuntimeError(f'{bodyd.name}: no planar end face')
    key = (lambda f: mm(f.boundingBox.maxPoint)[ax]) if high else (lambda f: -mm(f.boundingBox.minPoint)[ax])
    return max(planes, key=key)


def centre(face):
    a, b = mm(face.boundingBox.minPoint), mm(face.boundingBox.maxPoint)
    return tuple((u + v) / 2 for u, v in zip(a, b))


def root_edges(bodyd, ax, tip, radius, round_pin):
    """The edges where a pin meets its part: at `radius` from the axis through the tip face's centre (the hex's
    corners, or the round pin's circle), in one plane normal to the axis, the furthest such plane from the tip."""
    c = centre(tip)

    def radial(p):
        return math.sqrt(sum((p[i] - c[i]) ** 2 for i in range(3) if i != ax))

    groups = {}
    for e in bodyd.edges:
        g = e.geometry
        if round_pin:
            if g.objectType not in (adsk.core.Circle3D.classType(), adsk.core.Arc3D.classType()):
                continue
            o = mm(g.center)
            if abs(g.radius * 10 - radius) > TOL or radial(o) > TOL:
                continue
            a = o[ax]
        else:
            if g.objectType != adsk.core.Line3D.classType():
                continue
            p, q = mm(e.startVertex.geometry), mm(e.endVertex.geometry)
            if abs(p[ax] - q[ax]) > 1e-3 or abs(radial(p) - radius) > TOL or abs(radial(q) - radius) > TOL:
                continue
            a = p[ax]
        if abs(a - c[ax]) < 1.0:          # the tip and its chamfer
            continue
        groups.setdefault(round(a, 2), []).append(e)
    if not groups:
        raise RuntimeError(f'{bodyd.name}: no root edges at radius {radius:.3f}')
    a = max(groups, key=lambda k: abs(k - c[ax]))
    return a, abs(a - c[ax]), groups[a]


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    side = nf.design_side(design)
    log.side = side
    edits = (nf.get_attr(design, 'edits') or '').split()
    if EDIT in edits:
        raise RuntimeError(f'{EDIT} is already in this design')
    parts = nf.part_components(design)
    p = nf.stored_input(design)['params']
    corner = p['PIN_AF'] / math.sqrt(3)
    jobs = []        # (label, component, edges, radius)

    def plan(label, comp, ax, high, radius, round_pin, n_tip, r_fillet, length):
        bodyd = comp.bRepBodies.item(0)
        tip = end_face(bodyd, ax, high)
        if n_tip and tip.edges.count != n_tip:
            raise RuntimeError(f'{label}: the tip face has {tip.edges.count} edges, expected {n_tip}')
        a, dist, edges = root_edges(bodyd, ax, tip, radius, round_pin)
        log(f'{label}: tip at {"xyz"[ax]} {centre(tip)[ax]:.3f}, root at {a:.3f} ({dist:.3f} long), '
            f'{len(edges)} edges, fillet {r_fillet}')
        if not round_pin and len(edges) != 6:
            raise RuntimeError(f'{label}: {len(edges)} root edges, expected 6')
        if abs(dist - length) > 0.05:
            raise RuntimeError(f'{label}: the pin is {dist:.3f} long, expected {length:.3f}')
        jobs.append((label, comp, edges, r_fillet))

    if 'wheel' not in parts:
        raise RuntimeError('this design has no wheel')
    plan('wheel hex pin', parts['wheel'], 2, True, corner, False, 6, WHEEL_PIN_ROOT,
         p['HUB_CLEAR'] + p['PIN_ENGAGE'])
    if 'drum' in parts:
        plan('drum hex pin', parts['drum'], 0, False, corner, False, 6, DRUM_PIN_ROOT,
             p['DRUM_GAP'] - p['EC10_ROTOR_FACE'] + p['DRUM_PIN_ENGAGE'])
        plan('drum round pin', parts['drum'], 0, True, p['DRUM_ROUND_PIN'][0] / 2, True, 0, DRUM_ROUND_ROOT,
             p['DRUM_ROUND_PIN'][1])
    before = {label: comp.bRepBodies.item(0).volume for label, comp, _, _ in jobs}
    for label, comp, edges, r in jobs:
        nf.fillet(comp, edges, r).name = f'{label} root'
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed')
    for label, comp, _, _ in jobs:
        after = comp.bRepBodies.item(0).volume
        log(f'{label}: {comp.bRepBodies.count} bodies, volume {before[label] * 1000:.3f} -> {after * 1000:.3f} mm3')
        if comp.bRepBodies.count != 1:
            raise RuntimeError(f'{label}: the fillet split the body')
    for comp in {id(c): c for _, c, _, _ in jobs}.values():
        b0 = min(before[label] for label, c, _, _ in jobs if c is comp)
        if not comp.bRepBodies.item(0).volume > b0:
            raise RuntimeError(f'{comp.name}: the fillets added no material')
    nf.set_attr(design, 'edits', ' '.join(edits + [EDIT]))
    app.activeDocument.save(f'NrskEditPinFillets: {EDIT}')
    log('--- NrskCaseExport')
    export = importlib.reload(importlib.import_module('NrskCaseExport'))
    return f'{side}: {EDIT} applied\n{export.body(app, design, log)}'


def run(context):
    nrsk_fusion.run_script('NrskEditPinFillets', body)
