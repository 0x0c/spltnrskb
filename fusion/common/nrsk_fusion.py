"""Shared by the nrsk Fusion scripts (docs/specs/fusion-case.md): paths, input.json, units, logging, the design's
nrsk attributes, and small geometry helpers.

Lengths in input.json are mm in make_case's model frame (z up, y = -board y). Fusion's API works in cm, so every
length goes through cm(). Sketches on the root XY plane (or a plane parallel to it) use the model x, y directly.
"""
import datetime
import json
import os
import traceback

import adsk.core
import adsk.fusion

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))
FUSION_OUT = os.path.join(ROOT, 'case', 'fusion')
INPUT_VERSION = 1
ATTR = 'nrsk'
SIDES = ('left', 'right')


def cm(mm):
    return mm / 10.0


def pt(x, y, z=0.0):
    """Model mm -> Fusion Point3D (cm)."""
    return adsk.core.Point3D.create(cm(x), cm(y), cm(z))


def val(mm):
    return adsk.core.ValueInput.createByReal(cm(mm))


def side_dir(side):
    d = os.path.join(FUSION_OUT, side)
    os.makedirs(d, exist_ok=True)
    return d


def load_input(side):
    path = os.path.join(FUSION_OUT, side, 'input.json')
    with open(path) as f:
        data = json.load(f)
    if data.get('version') != INPUT_VERSION:
        raise ValueError(f"{path}: version {data.get('version')}, the scripts read {INPUT_VERSION}: "
                         'run gen/fusion_input.py again or update the scripts')
    return data


class Log:
    """Writes case/fusion/<side>/<script>.log (or case/fusion/<script>.log before the side is known)."""

    def __init__(self, script):
        self.script, self.lines, self.side = script, [], None

    def __call__(self, msg):
        self.lines.append(str(msg))

    def write(self, ok):
        d = side_dir(self.side) if self.side else FUSION_OUT
        with open(os.path.join(d, f'{self.script}.log'), 'w') as f:
            f.write(f"{'ok' if ok else 'FAILED'} {datetime.datetime.now().isoformat(timespec='seconds')}\n")
            f.write('\n'.join(self.lines) + '\n')


def run_script(script, body):
    """Run body(app, design, log) with logging; any exception is logged and shown."""
    app = adsk.core.Application.get()
    ui = app.userInterface
    log = Log(script)
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('open a design first (the Design workspace)')
        summary = body(app, design, log)
        log.write(True)
        ui.messageBox(f'{script}: ok\n{summary or ""}')
    except Exception:
        log(traceback.format_exc())
        log.write(False)
        ui.messageBox(f'{script} failed:\n{traceback.format_exc()}')


# --- the design's nrsk attributes ------------------------------------------------------
def get_attr(entity, name):
    a = entity.attributes.itemByName(ATTR, name)
    return a.value if a else None


def set_attr(entity, name, value):
    entity.attributes.add(ATTR, name, str(value))


def design_side(design, ui=None, ask=False):
    side = get_attr(design, 'side')
    if side is None and ask:
        value, cancelled = ui.inputBox('Which half is this design? (left / right)', 'nrsk', 'left')
        if cancelled:
            raise RuntimeError('cancelled')
        side = value.strip().lower()
        if side not in SIDES:
            raise ValueError(f'{side!r}: left or right')
        set_attr(design, 'side', side)
    if side not in SIDES:
        raise RuntimeError('this design has no nrsk side: build it with NrskCaseBuild first')
    return side


def part_components(design):
    """{part name: component} for the components the build made (attribute nrsk.part)."""
    out = {}
    for occ in design.rootComponent.occurrences:
        name = get_attr(occ.component, 'part')
        if name:
            out[name] = occ.component
    return out


# --- geometry helpers ------------------------------------------------------------------
def plane_at(comp, z):
    """A construction plane parallel to XY at model height z (mm); the XY plane itself at 0."""
    if abs(z) < 1e-9:
        return comp.xYConstructionPlane
    inp = comp.constructionPlanes.createInput()
    inp.setByOffset(comp.xYConstructionPlane, val(z))
    return comp.constructionPlanes.add(inp)


def circle(sketch, x, y, d):
    return sketch.sketchCurves.sketchCircles.addByCenterRadius(pt(x, y), cm(d / 2))


def polygon(sketch, pts):
    lines = sketch.sketchCurves.sketchLines
    out = []
    for i, (x, y) in enumerate(pts):
        x1, y1 = pts[(i + 1) % len(pts)]
        out.append(lines.addByTwoPoints(pt(x, y), pt(x1, y1)))
    for a, b in zip(out, out[1:] + out[:1]):          # one closed loop: connect the shared corners
        sketch.geometricConstraints.addCoincident(a.endSketchPoint, b.startSketchPoint)
    return out


def closed_spline(sketch, pts):
    coll = adsk.core.ObjectCollection.create()
    for x, y in pts:
        coll.add(pt(x, y))
    s = sketch.sketchCurves.sketchFittedSplines.add(coll)
    s.isClosed = True
    return s


def smallest_profile(sketch):
    return min(sketch.profiles, key=lambda p: p.areaProperties().area)


def largest_profile(sketch):
    return max(sketch.profiles, key=lambda p: p.areaProperties().area)


def extrude(comp, profile, dist_mm, op, bodies=None, taper_deg=0.0, start_mm=None):
    """Extrude profile by dist_mm (positive = +z) with operation op (adsk.fusion.FeatureOperations)."""
    feats = comp.features.extrudeFeatures
    inp = feats.createInput(profile, op)
    direction = adsk.fusion.ExtentDirections.PositiveExtentDirection if dist_mm >= 0 else \
        adsk.fusion.ExtentDirections.NegativeExtentDirection
    extent = adsk.fusion.DistanceExtentDefinition.create(val(abs(dist_mm)))
    inp.setOneSideExtent(extent, direction, adsk.core.ValueInput.createByString(f'{taper_deg} deg'))
    if start_mm is not None:
        inp.startExtent = adsk.fusion.OffsetStartDefinition.create(val(start_mm))
    if bodies is not None:
        inp.participantBodies = list(bodies)
    return feats.add(inp)


def combine(comp, target, tools, op):
    coll = adsk.core.ObjectCollection.create()
    for b in tools:
        coll.add(b)
    inp = comp.features.combineFeatures.createInput(target, coll)
    inp.operation = op
    return comp.features.combineFeatures.add(inp)



def rounded_rect(sketch, box):
    """Closed rounded rectangle from an input.json box {x0, y0, x1, y1, r} (r may be 0 or missing)."""
    x0, y0, x1, y1, r = box['x0'], box['y0'], box['x1'], box['y1'], box.get('r', 0.0)
    if r <= 1e-9:
        return polygon(sketch, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    lines, arcs = sketch.sketchCurves.sketchLines, sketch.sketchCurves.sketchArcs
    b = lines.addByTwoPoints(pt(x0 + r, y0), pt(x1 - r, y0))
    rt = lines.addByTwoPoints(pt(x1, y0 + r), pt(x1, y1 - r))
    t = lines.addByTwoPoints(pt(x1 - r, y1), pt(x0 + r, y1))
    lf = lines.addByTwoPoints(pt(x0, y1 - r), pt(x0, y0 + r))
    k = r * (1 - 2 ** -0.5)
    arcs.addByThreePoints(b.endSketchPoint, pt(x1 - k, y0 + k), rt.startSketchPoint)
    arcs.addByThreePoints(rt.endSketchPoint, pt(x1 - k, y1 - k), t.startSketchPoint)
    arcs.addByThreePoints(t.endSketchPoint, pt(x0 + k, y1 - k), lf.startSketchPoint)
    arcs.addByThreePoints(lf.endSketchPoint, pt(x0 + k, y0 + k), b.startSketchPoint)
    return [b, rt, t, lf]


def offset_box(box, d):
    """Grow (d > 0) or shrink a rounded box; the corner radius changes by d and stops at 0 (sharp)."""
    return dict(x0=box['x0'] - d, y0=box['y0'] - d, x1=box['x1'] + d, y1=box['y1'] + d,
                r=max(box.get('r', 0.0) + d, 0.0))


def face_at_z(body, z_mm, tol=1e-4):
    """The planar face of body lying in the plane z = z_mm, facing up or down (the largest if several)."""
    best = None
    for f in body.faces:
        bb = f.boundingBox
        if abs(bb.minPoint.z - cm(z_mm)) < tol and abs(bb.maxPoint.z - cm(z_mm)) < tol:
            if best is None or f.area > best.area:
                best = f
    if best is None:
        raise RuntimeError(f'{body.name}: no face at z = {z_mm}')
    return best


def fillet(comp, edges, r_mm):
    coll = adsk.core.ObjectCollection.create()
    for e in edges:
        coll.add(e)
    feats = comp.features.filletFeatures
    inp = feats.createInput()
    inp.edgeSetInputs.addConstantRadiusEdgeSet(coll, val(r_mm), True)
    return feats.add(inp)



def polygon_model(sketch, pts):
    """Closed polygon through model points (x, y, z in mm), on any sketch plane."""
    lines = sketch.sketchCurves.sketchLines
    sp = [sketch.modelToSketchSpace(pt(*q)) for q in pts]
    out = [lines.addByTwoPoints(sp[i], sp[(i + 1) % len(sp)]) for i in range(len(sp))]
    for a, b in zip(out, out[1:] + out[:1]):
        sketch.geometricConstraints.addCoincident(a.endSketchPoint, b.startSketchPoint)
    return out
