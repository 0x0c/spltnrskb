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

