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


def dangling_tracks(board):
    """Track segments with an end that touches nothing (Freerouting leftovers, unused escape stubs)."""
    tracks = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
    vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]

    def connected(t, pt):
        if any(o is not t and o.GetNetCode() == t.GetNetCode() and o.GetLayer() == t.GetLayer() and
               (o.GetStart() == pt or o.GetEnd() == pt or o.HitTest(pt, 0)) for o in tracks):
            return True
        if any(v.GetNetCode() == t.GetNetCode() and v.GetPosition() == pt for v in vias):
            return True
        return any(p.GetNetCode() == t.GetNetCode() and p.IsOnLayer(t.GetLayer()) and p.HitTest(pt) for p in pads)
    # locked 0.2 mm tracks are the MCU escape stubs from make_pcb; drop the ones the router did not use
    removable = lambda t: not t.IsLocked() or t.GetWidth() == pcbnew.FromMM(0.2)
    return [t for t in tracks if removable(t) and not (connected(t, t.GetStart()) and connected(t, t.GetEnd()))]


def remove_dangling_tracks(pcb):
    """One pass: drop dangling stubs and save. Returns how many were removed. A board must not be loaded twice
    in one process (the second load returns a broken object), so the caller runs each pass in a new process."""
    board = pcbnew.LoadBoard(pcb)
    stubs = dangling_tracks(board)
    for t in stubs:
        board.Remove(t)
    if stubs:
        pcbnew.SaveBoard(pcb, board)
    print(f'removed {len(stubs)} dangling track(s)')
    return len(stubs)


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
    # reloading the board in this process returns a broken object; clean up in a fresh one
    for _ in range(5):
        r = subprocess.run([sys.executable, os.path.abspath(__file__), '--cleanup', side], check=True,
                           capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[-1])
        if 'removed 0 ' in r.stdout:
            break
    print('routed', pcb)


def cleanup(side):
    pcb = os.path.join(ROOT, side, f'nrsk-{side}.kicad_pcb')
    remove_dangling_tracks(pcb)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--cleanup']:
        for s in sys.argv[2:]:
            cleanup(s)
    else:
        for s in sys.argv[1:] or ('left', 'right'):
            route(s)
