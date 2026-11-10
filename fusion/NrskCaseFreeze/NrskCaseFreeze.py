"""End the reproduction period of the open nrsk design (docs/specs/fusion-case.md): mark it nrsk.phase = edit, so
NrskCaseBuild refuses to rebuild it over hand edits, and save it. From here on: GUI edits, NrskCaseSync and
NrskCaseExport."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
for p in (HERE, os.path.join(HERE, '..', 'common')):
    if p not in sys.path:
        sys.path.insert(0, p)

import nrsk_fusion  # noqa: E402


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    side = nf.design_side(design)
    log.side = side
    nf.stored_input(design)                    # built by NrskCaseBuild
    was = nf.get_attr(design, 'phase')
    nf.set_attr(design, 'phase', 'edit')
    app.activeDocument.save('NrskCaseFreeze: edit period')
    log(f'phase {was} -> edit')
    return f'{side}: edit period (NrskCaseBuild now refuses this design)'


def run(context):
    nrsk_fusion.run_script('NrskCaseFreeze', body)
