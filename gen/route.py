"""Autoroute <side>/nrsk-<side>.kicad_pcb with Freerouting (run with KiCad's Python)."""
import math
import os
import subprocess
import sys

import pcbnew

from layout import HERE

ROOT = os.path.abspath(os.path.join(HERE, '..'))
JAVA = '/opt/homebrew/opt/openjdk/bin/java'
JAR = os.path.join(ROOT, 'tools', 'freerouting-2.4.1.jar')
WORK = os.environ.get('NRSK_WORK', '/private/tmp/claude-501/scratch-nrsk')
POUR_CLEARANCE = 0.3      # GND copper to other nets [mm]
POUR_MIN_WIDTH = 0.25     # thinnest GND copper kept [mm]
STITCH_PITCH = 5.0        # grid of the vias tying the two GND faces together [mm]
VIA_D, VIA_DRILL = 0.6, 0.3


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


def pour(side):
    """GND copper on both faces over the whole board, filled after routing (the routed GND tracks stay), tied
    together by vias. SMD pads join the copper solidly (JLC reflows them); through-hole pads, soldered by hand,
    get thermal spokes.

    Vias go on a STITCH_PITCH grid, and also on a finer grid wherever no via is within 3/4 pitch, so that
    narrow pieces of copper boxed in by tracks get one too. A via is placed only where a ring a little wider than
    it lies in the copper of both faces (it then clears every other net by POUR_CLEARANCE) and its drill keeps
    0.5 mm from every other hole. Copper still left unconnected is removed, and with it any via standing in it."""
    pcb = os.path.join(ROOT, side, f'nrsk-{side}.kicad_pcb')
    board = pcbnew.LoadBoard(pcb)
    gnd = board.FindNet('GND')
    bb = board.GetBoardEdgesBoundingBox()
    for fp in board.GetFootprints():      # the USB-C shell legs: through-hole, but JLC solders them; solid to GND
        if fp.GetReference() == 'J2':
            for p in fp.Pads():
                if p.GetNumber() == 'SH':
                    p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    zones = {}
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetZoneName('GND')
        z.SetLocalClearance(pcbnew.FromMM(POUR_CLEARANCE))
        z.SetMinThickness(pcbnew.FromMM(POUR_MIN_WIDTH))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)   # solid to SMD pads (reflowed), spokes to THT
        z.SetThermalReliefGap(pcbnew.FromMM(0.5))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)    # keep the islands while placing vias
        z.SetAssignedPriority(0)      # the mounting-hole keepouts still win
        o = z.Outline()
        o.NewOutline()
        for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()),
                     (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
            o.Append(x, y)
        board.Add(z)
        zones[layer] = z
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    ring = [(math.cos(2 * math.pi * i / 12), math.sin(2 * math.pi * i / 12)) for i in range(12)]
    rr = pcbnew.FromMM(VIA_D / 2 + 0.05)

    def in_copper(x, y):
        pts = [pcbnew.VECTOR2I(x, y)] + [pcbnew.VECTOR2I(int(x + rr * c), int(y + rr * s)) for c, s in ring]
        return all(zones[l].GetFilledPolysList(l).Contains(p) for l in zones for p in pts)
    holes = [(p.GetPosition(), max(p.GetDrillSize().x, p.GetDrillSize().y) / 2)
             for fp in board.GetFootprints() for p in fp.Pads() if p.GetDrillSize().x > 0]
    holes += [(v.GetPosition(), v.GetDrillValue() / 2) for v in board.GetTracks() if v.Type() == pcbnew.PCB_VIA_T]
    gap = pcbnew.FromMM(0.5 + VIA_DRILL / 2)
    stitch = []
    pitch = pcbnew.FromMM(STITCH_PITCH)
    for step, spacing in ((pitch, 0), (pitch // 4, pitch * 3 // 4)):   # 3/4 pitch: only where the grid left a gap
        for x in range(bb.GetLeft() + step // 2, bb.GetRight(), step):
            for y in range(bb.GetTop() + step // 2, bb.GetBottom(), step):
                if spacing and any(math.hypot(x - v.x, y - v.y) < spacing for v in stitch):
                    continue
                if any(math.hypot(x - h.x, y - h.y) - hr < gap for h, hr in holes) or not in_copper(x, y):
                    continue
                stitch.append(pcbnew.VECTOR2I(x, y))
                holes.append((stitch[-1], pcbnew.FromMM(VIA_DRILL / 2)))
    vias = []
    for pos in stitch:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pos)
        v.SetWidth(pcbnew.FromMM(VIA_D))
        v.SetDrill(pcbnew.FromMM(VIA_DRILL))
        v.SetNet(gnd)
        board.Add(v)
        vias.append(v)
    for z in zones.values():
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    filler.Fill(board.Zones())
    lone = [v for v in vias if not in_copper(v.GetPosition().x, v.GetPosition().y)]
    for v in lone:
        board.Remove(v)
    if lone:
        filler.Fill(board.Zones())
    pcbnew.SaveBoard(pcb, board)
    print(f'poured GND on both faces, {len(vias) - len(lone)} stitching vias')


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
    r = subprocess.run([sys.executable, os.path.abspath(__file__), '--pour', side], check=True,
                       capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1])
    print('routed', pcb)


def cleanup(side):
    pcb = os.path.join(ROOT, side, f'nrsk-{side}.kicad_pcb')
    remove_dangling_tracks(pcb)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--cleanup']:
        for s in sys.argv[2:]:
            cleanup(s)
    elif sys.argv[1:2] == ['--pour']:
        for s in sys.argv[2:]:
            pour(s)
    else:
        for s in sys.argv[1:] or ('left', 'right'):
            route(s)
