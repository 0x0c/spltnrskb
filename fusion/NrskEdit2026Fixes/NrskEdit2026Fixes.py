"""One run for the fixes of the 2026-11 design review on the open nrsk design: NrskCaseSync (INSERT_D, BLOCK_PEG and
the other changed parameters of input.json), then the edits NrskEditWheelPin and NrskEditCapRelief (each skipped
if the design already has it), then NrskCaseExport. Each step is the other script's own body; this only saves
starting four scripts by hand per design. It stops at the first step that fails.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
STEPS = ('NrskCaseSync', 'NrskEditWheelPin', 'NrskEditCapRelief', 'NrskCaseExport')
for p in [HERE, os.path.join(HERE, '..', 'common')] + [os.path.join(HERE, '..', s) for s in STEPS]:
    if p not in sys.path:
        sys.path.insert(0, p)

import nrsk_fusion  # noqa: E402


def body(app, design, log):
    done = []
    for name in STEPS:
        mod = importlib.reload(importlib.import_module(name))
        log(f'--- {name}')
        try:
            done.append(mod.body(app, design, log))
        except RuntimeError as e:
            if 'is already in this design' not in str(e):
                raise
            log(f'skipped: {e}')
            done.append(f'{name}: already applied')
    return '\n'.join(done)


def run(context):
    nrsk_fusion.run_script('NrskEdit2026Fixes', body)
