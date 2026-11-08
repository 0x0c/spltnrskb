"""Build the nrsk case parts into the open design from case/fusion/<side>/input.json (docs/specs/fusion-case.md).

Only for the reproduction period: it deletes what an earlier build made (every root occurrence and every user
parameter) and builds again. It refuses to run once the design carries nrsk.phase = edit.
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
import parts  # noqa: E402

COUNTS = {'WHEEL_KNURLS', 'N_FRAMES', 'DRUM_GROOVES'}     # plain numbers, not lengths
ANGLES = {'DRUM_HELIX', 'STAND_ANGLES'}


def parameters(design, params, log):
    """make_case's constants as user parameters (tuples as NAME_0, NAME_1, ...)."""
    up = design.userParameters
    n = 0
    for name, v in params.items():
        values = v if isinstance(v, list) else [v]
        for i, x in enumerate(values):
            pname = name if not isinstance(v, list) else f'{name}_{i}'
            unit = '' if name in COUNTS else 'deg' if name in ANGLES else 'mm'
            up.add(pname, adsk.core.ValueInput.createByString(f'{x} {unit}'.strip()), unit, 'make_case.py')
            n += 1
    log(f'{n} user parameters')


def clear(design, log):
    root = design.rootComponent
    for i in range(root.occurrences.count - 1, -1, -1):
        root.occurrences.item(i).deleteMe()
    up = design.userParameters
    for i in range(up.count - 1, -1, -1):
        up.item(i).deleteMe()
    log('cleared the previous build')


def project(app):
    """The project to save in: the active one, else the first of the active hub (the data panel may not have
    picked one yet, and then activeProject raises)."""
    try:
        return app.data.activeProject
    except RuntimeError:
        return app.data.activeHub.dataProjects.item(0)


def save(app, side, log):
    """Save the design in the cloud as nrsk-<side>-case (the cloud design is the source of truth). A failure is
    logged, not raised: the parts are built, and the design can be saved by hand."""
    doc, name = app.activeDocument, f'nrsk-{side}-case'
    try:
        if not doc.isSaved:
            prj = project(app)
            doc.saveAs(name, prj.rootFolder, 'nrsk case (docs/specs/fusion-case.md)', '')
            log(f'saved as {name} in {prj.name}')
        else:
            doc.save('NrskCaseBuild')
            log(f'saved {doc.name}')
    except Exception as e:
        log(f'WARNING not saved ({e}): save it as {name} by hand')


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    importlib.reload(parts)
    if nf.get_attr(design, 'phase') == 'edit':
        raise RuntimeError('this design is in the edit period (nrsk.phase = edit): use NrskCaseSync, not the build')
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    side = nf.design_side(design, app.userInterface, ask=True)
    log.side = side
    inp = nf.load_input(side)
    log(f'side {side}, input version {inp["version"]}')
    clear(design, log)
    parameters(design, inp['params'], log)
    root = design.rootComponent
    made = []
    for name, build in parts.BUILDERS.items():
        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = occ.component
        comp.name = name
        nf.set_attr(comp, 'part', name)
        build(comp, inp, log)
        made.append(name)
    nf.set_attr(design, 'phase', 'reproduce')
    log('built: ' + ', '.join(made))
    save(app, side, log)
    return f'{side}: built {", ".join(made)}'


def run(context):
    nrsk_fusion.run_script('NrskCaseBuild', body)
