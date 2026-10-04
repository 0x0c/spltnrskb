"""Export each assembled board as GLB for the case viewer -> build/3d/<side>-{pcba,switches}.glb.

pcba     : board with silkscreen and solder mask, every component except the switches
switches : the MX switch models only, so the viewer can toggle them like the plate
Run with KiCad's python; NRSK_KC must point at kicad-cli. Coordinates are board-local (the board
origin, make_pcb.ORIGIN, is passed as the user origin), in metres, Y up as glTF expects.
"""
import os
import subprocess
import sys
import tempfile

import pcbnew

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'build', '3d')    # large; not committed, read by case_viewer.py
ORIGIN = '30x30mm'     # = make_pcb.ORIGIN


def copy_model(m, filename):
    n = pcbnew.FP_3DMODEL()
    n.m_Filename = filename
    n.m_Offset, n.m_Rotation, n.m_Scale = m.m_Offset, m.m_Rotation, m.m_Scale
    n.m_Show, n.m_Opacity = m.m_Show, m.m_Opacity
    return n


def export(side, kind, work):
    board = pcbnew.LoadBoard(os.path.join(ROOT, side, f'nrsk-{side}.kicad_pcb'))
    for fp in board.GetFootprints():
        keep = []
        for m in fp.Models():
            f = m.m_Filename.replace('${KIPRJMOD}', os.path.join(ROOT, side))
            if ('SW_Cherry_MX' in f) == (kind == 'switches'):
                keep.append(copy_model(m, f))
        fp.Models().clear()
        for m in keep:
            fp.Models().push_back(m)
    tmp = os.path.join(work, f'{side}-{kind}.kicad_pcb')
    board.Save(tmp)
    out = os.path.join(OUT, f'{side}-{kind}.glb')
    args = [os.environ['NRSK_KC'], 'pcb', 'export', 'glb', '-f', '--user-origin', ORIGIN, '-o', out, tmp]
    args += ['--include-silkscreen', '--include-soldermask'] if kind == 'pcba' else \
        ['--no-board-body', '--component-filter', 'SW*']
    r = subprocess.run(args, capture_output=True, text=True)
    missing = [line for line in r.stdout.splitlines() if 'File not found' in line]
    if r.returncode or missing or not os.path.exists(out):
        sys.exit(f'{side} {kind}: GLB export failed\n' + r.stdout[-2000:] + r.stderr[-2000:])
    print(f'wrote {out} {os.path.getsize(out) / 1e6:.1f} MB')


def main():
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        for side in sys.argv[1:] or ('left', 'right'):
            for kind in ('pcba', 'switches'):
                export(side, kind, work)


if __name__ == '__main__':
    main()
