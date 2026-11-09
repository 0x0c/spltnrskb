"""Show the open nrsk design assembled: move each part's occurrence to where the part sits in the case.

Each component is modelled in the frame its STL is exported in (make_case's Half methods): the wheel's bottom at
z = 0, the plate's bottom face at z = 0, the drum parts above the PCB top at z = 0. Shown as they are, the wheel sits
in the tray floor and the plate in the tray. This script only moves the occurrences (and captures the position);
NrskCaseExport meshes the components' own bodies, so the STLs do not change. Of the tilt stands only the 3 degree
one stays visible (the three share one place under the tray). Run it again any time: it sets the same positions.
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

SHOWN_STAND = 'stand-3'


def heights(p):
    """Part -> z offset (mm) from its export frame to its place in the assembled case (as make_case.write_half)."""
    z_pcb = p['FLOOR'] + p['STANDOFF']
    return {'wheel': p['FLOOR'] + p['WHEEL_GAP'],
            'plate': z_pcb + p['PCB_T'] + p['PLATE_GAP'],
            'drum': z_pcb + p['PCB_T'], 'drum-block': z_pcb + p['PCB_T'], 'drum-bezel': z_pcb + p['PCB_T']}


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    side = nf.design_side(design)
    log.side = side
    p = nf.stored_input(design)['params']
    dz = heights(p)
    moved = []
    for occ in design.rootComponent.occurrences:
        name = nf.get_attr(occ.component, 'part')
        if not name:
            continue
        m = adsk.core.Matrix3D.create()
        m.translation = adsk.core.Vector3D.create(0, 0, nf.cm(dz.get(name, 0.0)))
        occ.transform2 = m
        if name.startswith('stand-'):
            occ.isLightBulbOn = name == SHOWN_STAND
        moved.append(f'{name} z {dz.get(name, 0.0):+.2f}')
    if design.designType == adsk.fusion.DesignTypes.ParametricDesignType and design.snapshots.hasPendingSnapshot:
        design.snapshots.add()                 # capture the positions in the timeline
    app.activeDocument.save('NrskCaseLayout: assembled view')
    log('\n'.join(moved))
    return f'{side}: parts shown assembled (only {SHOWN_STAND} of the stands visible)'


def run(context):
    nrsk_fusion.run_script('NrskCaseLayout', body)
