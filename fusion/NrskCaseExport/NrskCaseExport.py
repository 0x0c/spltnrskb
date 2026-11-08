"""Export every part of the open nrsk design as case/fusion/<side>/<part>.stl, and the design as
case/fusion/nrsk-<side>-case.f3d (docs/specs/fusion-case.md). The STLs are in make_case's model frame, in mm.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
for p in (HERE, os.path.join(HERE, '..', 'common')):
    if p not in sys.path:
        sys.path.insert(0, p)

import adsk.core  # noqa: E402
import adsk.fusion  # noqa: E402

import nrsk_fusion  # noqa: E402

SURFACE_DEVIATION_MM = 0.01      # far under fusion_diff's thresholds, and the STLs stay near the code's in size
NORMAL_DEVIATION_DEG = 15.0
ASPECT_RATIO = 100.0
MAX_EDGE_MM = 500.0


def body(app, design, log):
    nf = importlib.reload(nrsk_fusion)
    side = nf.design_side(design)
    log.side = side
    out = nf.side_dir(side)
    em = design.exportManager
    parts = nf.part_components(design)
    if not parts:
        raise RuntimeError('no nrsk parts in this design')
    for name, comp in sorted(parts.items()):
        path = os.path.join(out, f'{name}.stl')
        opt = em.createSTLExportOptions(comp, path)
        opt.isBinaryFormat = True
        opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementCustom
        opt.surfaceDeviation = nf.cm(SURFACE_DEVIATION_MM)
        opt.normalDeviation = math.radians(NORMAL_DEVIATION_DEG)
        opt.aspectRatio = ASPECT_RATIO              # long thin triangles are fine on straight-walled faces
        opt.maximumEdgeLength = nf.cm(MAX_EDGE_MM)
        if not em.execute(opt):
            raise RuntimeError(f'{name}: STL export failed')
        log(f'{name}: {os.path.relpath(path, nf.ROOT)}, {comp.bRepBodies.count} bodies, '
            f'refinement {opt.meshRefinement}, surface {opt.surfaceDeviation * 10:.4f} mm, '
            f'normal {math.degrees(opt.normalDeviation):.1f} deg, aspect {opt.aspectRatio:g}, '
            f'edge {opt.maximumEdgeLength * 10:g} mm, {os.path.getsize(path) // 1024} KiB')
    f3d = os.path.join(nf.FUSION_OUT, f'nrsk-{side}-case.f3d')
    if not em.execute(em.createFusionArchiveExportOptions(f3d)):
        raise RuntimeError('f3d export failed')
    log(f'design: {os.path.relpath(f3d, nf.ROOT)}')
    return f'{side}: exported {", ".join(sorted(parts))}'


def run(context):
    nrsk_fusion.run_script('NrskCaseExport', body)
