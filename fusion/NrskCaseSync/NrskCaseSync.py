"""Bring the open nrsk design up to date with case/fusion/<side>/input.json (docs/specs/fusion-case.md).

It compares the new input with the one the design was built or last synced from (the design's nrsk.input) and
  * sets the user parameters whose make_case constants changed,
  * moves the sketch entities tagged with the id of a point-like item that moved (screws, PCB holes, feet, keys,
    the drum's pegs, the reset hole): the features built on those sketches follow.
Anything else it cannot follow by itself: items added or removed, or a change of the outline, the ports, the OLED
cover, the wheel, the stands' cut or the drum dial's frame. Then it changes nothing, lists what differs, and stops:
edit those by hand in Fusion (or, in the reproduction period, build again).
"""
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
for p in (HERE, os.path.join(HERE, '..', 'common')):
    if p not in sys.path:
        sys.path.insert(0, p)

import adsk.core  # noqa: E402
import adsk.fusion  # noqa: E402

import nrsk_fusion  # noqa: E402

POINTS = ('screws', 'pcb_holes', 'feet', 'keys')            # lists of {id, xy}
# what the build used besides the parameters and the points; a change here needs a hand edit
SHAPES = ('outer_box', 'inner', 'port_skin', 'slots', 'wheel', 'cap')
DRUM_SHAPES = ('origin', 'drum_d', 'block_x', 'hood_ends', 'bezel_box', 'ledge_box', 'plate_hole', 'web_cut')


def points(inp):
    out = {e['id']: e['xy'] for k in POINTS for e in inp.get(k, [])}
    out.update({e['id']: e['xy'] for e in inp.get('drum', {}).get('pegs', [])})
    if 'reset' in inp:
        out['reset'] = inp['reset']['xy']
    return out


def close(a, b, tol=1e-6):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return a == b


def unsupported(old, new):
    """What changed that the sync cannot follow, as readable lines."""
    out = []
    po, pn = points(old), points(new)
    if po.keys() != pn.keys():
        added, removed = sorted(pn.keys() - po.keys()), sorted(po.keys() - pn.keys())
        out.append(f"items added: {', '.join(added) or '-'}; removed: {', '.join(removed) or '-'}")
    for k in SHAPES:
        if not close(old.get(k), new.get(k)):
            out.append(f'{k} changed')
    if not close(old.get('oled', {}).get('cover'), new.get('oled', {}).get('cover')):
        out.append('oled cover changed')
    so, sn = old.get('stand', {}), new.get('stand', {})
    for k in ('y_cut', 'poses', 'feet'):
        if not close(so.get(k), sn.get(k)):
            out.append(f'stand {k} changed')
    do, dn = old.get('drum', {}), new.get('drum', {})
    for k in DRUM_SHAPES:
        if not close(do.get(k), dn.get(k)):
            out.append(f'drum {k} changed')
    return out


def native(e):
    """The entity itself, not a proxy of it through an occurrence (findAttributes returns both)."""
    n = getattr(e, 'nativeObject', None)
    return n if n else e


def tagged(design):
    """{id: [sketch entities]} for every sketch entity the build tagged, each once."""
    out, seen = {}, set()
    for a in design.findAttributes(nrsk_fusion.ATTR, 'id'):
        if not a.parent:
            continue
        e = native(a.parent)
        if e.entityToken in seen:
            continue
        seen.add(e.entityToken)
        out.setdefault(a.value, []).append(e)
    return out


def move(entities, dx, dy):
    """Move the sketch points of these curves by (dx, dy) mm, each point once (a corner is shared by two lines)."""
    seen, pts = set(), []
    for e in entities:
        cands = [e.centerSketchPoint] if hasattr(e, 'centerSketchPoint') and e.objectType.endswith('SketchCircle') \
            else [e.startSketchPoint, e.endSketchPoint]
        for p in map(native, cands):
            if p.entityToken not in seen:
                seen.add(p.entityToken)
                pts.append(p)
    v = adsk.core.Vector3D.create(nrsk_fusion.cm(dx), nrsk_fusion.cm(dy), 0)
    for p in pts:
        p.move(v)
    return len(pts)


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    side = nf.design_side(design)
    log.side = side
    old, new = nf.stored_input(design), nf.load_input(side)
    bad = unsupported(old, new)
    if bad:
        for line in bad:
            log(f'NOT SYNCED: {line}')
        raise RuntimeError('cannot follow these changes by itself, nothing changed:\n' + '\n'.join(bad) +
                           '\nedit them by hand in Fusion (in the reproduction period: NrskCaseBuild)')
    # parameters
    up = design.userParameters
    vo, vn = nf.parameter_values(old['params']), nf.parameter_values(new['params'])
    changed = 0
    for name, (x, unit) in vn.items():
        prm = up.itemByName(name)
        if prm is None:
            prm = up.add(name, adsk.core.ValueInput.createByString(f'{x} {unit}'.strip()), unit, 'make_case.py')
            log(f'parameter {name} added = {x} {unit}')
            changed += 1
        elif name not in vo or not close(vo[name][0], x):
            prm.expression = f'{x} {unit}'.strip()
            log(f'parameter {name}: {vo.get(name, ("-",))[0]} -> {x} {unit}')
            changed += 1
    # points
    po, pn = points(old), points(new)
    ents = tagged(design)
    moved = 0
    for ident, (x, y) in pn.items():
        ox, oy = po[ident]
        if abs(x - ox) < 1e-6 and abs(y - oy) < 1e-6:
            continue
        if ident not in ents:
            log(f'{ident} moved but nothing in the design is tagged with it')
            continue
        n = move(ents[ident], x - ox, y - oy)
        log(f'{ident}: ({ox}, {oy}) -> ({x}, {y}), {n} sketch points in {len(ents[ident])} curves')
        moved += 1
    # editing a sketch through the API does not recompute the features built on it: recompute the whole timeline
    # (always, so a sync with nothing to change also brings the bodies up to date)
    if not design.computeAll():
        raise RuntimeError('recomputing the design failed: look at the timeline for features in error')
    nf.store_input(design, new)
    if changed or moved:
        app.activeDocument.save('NrskCaseSync')
    log(f'synced: {changed} parameters, {moved} items moved')
    return f'{side}: {changed} parameters, {moved} items moved'


def run(context):
    nrsk_fusion.run_script('NrskCaseSync', body)
