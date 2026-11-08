"""Export every part of the open nrsk design as case/fusion/<side>/<part>.stl, and the design as
case/fusion/nrsk-<side>-case.f3d (docs/specs/fusion-case.md). The STLs are in make_case's model frame, in mm.
"""
import importlib
import math
import os
import struct
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
# the drum's twisted knurl ignores the tolerances above (1.5 M triangles, 73 MB; GitHub refuses files over 100 MB):
# Fusion's High preset meshes it as finely as the code did (48 k triangles) and stays within fusion_diff's threshold
PART_MESH = {'drum': 'High'}     # part -> one of Fusion's presets (Low, Normal, High, VeryHigh)


def write_stl(path, comp, preset=None):
    """Mesh every body of comp with Fusion's mesh calculator (the tolerances above, or a preset) and write one binary
    STL in mm. The STL export ignored its tolerances on curved faces and wrote files twice the size."""
    tris = []
    for body in comp.bRepBodies:
        calc = body.meshManager.createMeshCalculator()
        if preset:
            calc.setQuality(getattr(adsk.fusion.TriangleMeshQualityOptions, f'{preset}QualityTriangleMesh'))
        else:
            calc.surfaceTolerance = SURFACE_DEVIATION_MM / 10
            calc.maxNormalDeviation = math.radians(NORMAL_DEVIATION_DEG)
            calc.maxAspectRatio = ASPECT_RATIO
            calc.maxSideLength = MAX_EDGE_MM / 10
        mesh = calc.calculate()
        xyz, idx = mesh.nodeCoordinatesAsDouble, mesh.nodeIndices
        for i in range(0, len(idx), 3):
            tris.append(tuple(tuple(xyz[3 * k + j] * 10 for j in range(3)) for k in idx[i:i + 3]))
    with open(path, 'wb') as f:
        f.write(b'nrsk fusion export'.ljust(80, b' '))
        f.write(struct.pack('<I', len(tris)))
        for a, b, c in tris:
            ux, uy, uz = (b[j] - a[j] for j in range(3))
            vx, vy, vz = (c[j] - a[j] for j in range(3))
            n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
            f.write(struct.pack('<12fH', *n, *a, *b, *c, 0))
    return len(tris)


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
        preset = PART_MESH.get(name)
        tris = write_stl(path, comp, preset)
        mesh = f'preset {preset}' if preset else f'surface {SURFACE_DEVIATION_MM} mm, normal {NORMAL_DEVIATION_DEG} deg'
        log(f'{name}: {os.path.relpath(path, nf.ROOT)}, {comp.bRepBodies.count} bodies, {mesh}, {tris} triangles, '
            f'{os.path.getsize(path) // 1024} KiB')
    f3d = os.path.join(nf.FUSION_OUT, f'nrsk-{side}-case.f3d')
    if not em.execute(em.createFusionArchiveExportOptions(f3d)):
        raise RuntimeError('f3d export failed')
    log(f'design: {os.path.relpath(f3d, nf.ROOT)}')
    return f'{side}: exported {", ".join(sorted(parts))}'


def run(context):
    nrsk_fusion.run_script('NrskCaseExport', body)
