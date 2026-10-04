"""Autoroute <side>/nrsk-<side>.kicad_pcb with Freerouting (run with KiCad's Python)."""
import os
import subprocess
import sys

import pcbnew

from layout import HERE

ROOT = os.path.abspath(os.path.join(HERE, '..'))
JAVA = '/opt/homebrew/opt/openjdk/bin/java'
JAR = os.path.join(ROOT, 'tools', 'freerouting-2.4.1.jar')
WORK = os.environ.get('NRSK_WORK', '/private/tmp/claude-501/scratch-nrsk')


def remove_dangling_vias(board):
    """Drop vias that Freerouting left with copper on one layer only."""
    tracks = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    for v in [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]:
        if v.IsLocked():
            continue
        pos, r = v.GetPosition(), v.GetWidth() // 2
        layers = set()
        for t in tracks:
            if t.GetNetCode() == v.GetNetCode() and (t.GetStart() == pos or t.GetEnd() == pos or t.HitTest(pos, r)):
                layers.add(t.GetLayer())
        for p in pads:
            if p.GetNetCode() == v.GetNetCode() and p.HitTest(pos):
                layers.update([pcbnew.F_Cu, pcbnew.B_Cu] if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else
                              [l for l in (pcbnew.F_Cu, pcbnew.B_Cu) if p.IsOnLayer(l)])
        if len(layers) < 2:
            board.Remove(v)


def route(side, passes=100):
    pcb = os.path.join(ROOT, side, f'nrsk-{side}.kicad_pcb')
    board = pcbnew.LoadBoard(pcb)
    dsn = os.path.join(WORK, f'{side}.dsn')
    ses = os.path.join(WORK, f'{side}.ses')
    assert pcbnew.ExportSpecctraDSN(board, dsn)
    if os.path.exists(ses):
        os.remove(ses)
    subprocess.run([JAVA, '-jar', JAR, '-de', dsn, '-do', ses, '-mp', str(passes), '--gui.enabled=false'],
                   check=True, cwd=WORK)
    assert pcbnew.ImportSpecctraSES(board, ses)
    # Freerouting necks tracks down at fine-pitch pads; keep everything >= 0.15 mm (fab minimum 0.127 mm)
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T and t.GetWidth() < pcbnew.FromMM(0.15):
            t.SetWidth(pcbnew.FromMM(0.15))
    remove_dangling_vias(board)
    pcbnew.SaveBoard(pcb, board)
    print('routed', pcb)


if __name__ == '__main__':
    for s in sys.argv[1:] or ('left', 'right'):
        route(s)
