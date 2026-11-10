"""Show the bought hardware in the open nrsk design: the plate screws, heat-set inserts, nuts and PCB screws, where
they sit when the case is assembled (as NrskCaseLayout shows the printed parts).

Display only: the hardware components carry nrsk.hardware, not nrsk.part, so NrskCaseExport, NrskCaseSync and
fusion_diff never see them. The shapes are plain cylinders and hexagons (no threads, no knurl) at the nominal sizes
below. Three groups, each a component under the root:
  hardware (common): the PCB's M2 x 6 tapping screws, from the PCB top down into the tray's bosses
  hardware (B):      M2 x 12 pan-head screws from the tray's counterbores into heat-set inserts in the plate's bosses
  hardware (A):      M2 nuts in the hex traps and M2 x 6 slim-head screws from the acrylic plate's top (hidden: the
                     design shows the printed plate B, and A's acrylic plate is not in it)
Positions come from the design's stored input (nrsk.input), so run NrskCaseSync first after the PCB moved. Run it
again any time: it deletes the hardware it made before and builds it anew.
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

NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation

# nominal sizes (mm)
SHANK_D = 2.0
PAN_HEAD = (3.5, 1.3)        # M2 pan head (JIS): diameter, height
SLIM_HEAD = (4.0, 0.5)       # the slim-head screw on A's acrylic plate
NUT = (4.0, 1.6)             # M2 nut: across flats, thickness
INSERT = (3.2, 3.0)          # heat-set insert (LCSC C51938879): outer diameter, length
PLATE_SCREW_L = 12.0         # B
SLIM_SCREW_L = 6.0           # A
PCB_SCREW_L = 6.0

APPEARANCES = {'steel': ['Steel - Satin', 'Steel - Polished'], 'brass': ['Brass - Polished', 'Brass - Satin']}
GROUPS = ('common', 'B', 'A')
SHOWN = {'common', 'B'}


def appearance(app, design, kind):
    """A library appearance copied into the design, or None (the names differ between Fusion versions)."""
    for name in APPEARANCES[kind]:
        a = design.appearances.itemByName(name)
        if a:
            return a
        for lib in app.materialLibraries:
            if 'Appearance' not in lib.name:
                continue
            try:
                a = lib.appearances.itemByName(name)
            except Exception:
                a = None
            if a:
                return design.appearances.addByCopy(a, name)
    return None


def disc(comp, d, z0, z1, op, hole=None, hexagon=None):
    """A cylinder of diameter d (or a hexagon `hexagon` across flats) from z0 to z1 round the component's z axis,
    with an optional round hole through it."""
    sk = comp.sketches.add(comp.xYConstructionPlane)
    if hexagon:
        nf.polygon(sk, nf.hexagon_pts(0.0, 0.0, hexagon / math.sqrt(3)))
    else:
        nf.circle(sk, 0.0, 0.0, d)
    if hole:
        nf.circle(sk, 0.0, 0.0, hole)
    prof = nf.largest_profile(sk)
    return nf.extrude(comp, prof, z1 - z0, op, start_mm=z0 if z0 else None)


def screw(parent, name, head, length):
    """A screw with its head's bearing face at z = 0, the head below and the shank up (+z)."""
    occ = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = name
    disc(comp, head[0], -head[1], 0.0, NEW)
    disc(comp, SHANK_D, 0.0, length, JOIN)
    return occ


def insert(parent):
    occ = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = f'M2 heat-set insert {INSERT[0]} x {INSERT[1]}'
    disc(occ.component, INSERT[0], 0.0, INSERT[1], NEW, hole=SHANK_D)
    return occ


def nut(parent):
    occ = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = 'M2 nut'
    disc(occ.component, None, 0.0, NUT[1], NEW, hole=SHANK_D, hexagon=NUT[0])
    return occ


def pose(x, y, z, down=False):
    """Move to (x, y, z) mm; down turns the part over (a screw driven from the top: head up, shank down)."""
    m = adsk.core.Matrix3D.create()
    if down:
        m.setToRotation(math.pi, adsk.core.Vector3D.create(1, 0, 0), adsk.core.Point3D.create(0, 0, 0))
    m.translation = adsk.core.Vector3D.create(nf.cm(x), nf.cm(y), nf.cm(z))
    return m


def place(parent, first, spots, look):
    """Put `first` (a new occurrence) on the first spot and copies of its component on the others."""
    comp = first.component
    if look:
        for b in comp.bRepBodies:
            b.appearance = look
    for i, m in enumerate(spots):
        if i == 0:
            first.transform2 = m
        else:
            parent.occurrences.addExistingComponent(comp, m)
    return len(spots)


def body(app, design, log):
    global nf
    nf = importlib.reload(nrsk_fusion)
    side = nf.design_side(design)
    log.side = side
    data = nf.stored_input(design)
    p = data['params']
    root = design.rootComponent

    old = [o for o in root.occurrences if nf.get_attr(o.component, 'hardware')]
    for o in old:
        o.deleteMe()
    if old:
        log(f'deleted {len(old)} old hardware groups')

    z_pcb = p['FLOOR'] + p['STANDOFF']                 # PCB bottom
    pcb_top = z_pcb + p['PCB_T']
    wall_top = pcb_top + p['PLATE_GAP']                # = the plate's bottom face
    plate_top = wall_top + p['PLATE_T']
    pocket_floor = wall_top - p['BOSS_POCKET'][1]
    trap_floor = pocket_floor - p['NUT_TRAP'][1]
    cb_top = p['SCREW_CB'][1]                          # the counterbore's ceiling: the pan head bears on it
    boss_bottom = wall_top - p['PLATE_BOSS'][1]
    screws = [q['xy'] for q in data['screws']]
    holes = [q['xy'] for q in data['pcb_holes']]

    steel, brass = appearance(app, design, 'steel'), appearance(app, design, 'brass')
    groups = {}
    for g in GROUPS:
        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = f'hardware ({g})'
        nf.set_attr(occ.component, 'hardware', g)
        groups[g] = occ

    c = groups['common'].component
    n = place(c, screw(c, f'M2 x {PCB_SCREW_L:g} tapping screw (PCB)', PAN_HEAD, PCB_SCREW_L),
              [pose(x, y, pcb_top, down=True) for x, y in holes], steel)
    log(f'common: {n} PCB screws, head on the PCB top z {pcb_top:.2f}, tip z {pcb_top - PCB_SCREW_L:.2f}')

    b = groups['B'].component
    n = place(b, screw(b, f'M2 x {PLATE_SCREW_L:g} pan-head screw', PAN_HEAD, PLATE_SCREW_L),
              [pose(x, y, cb_top) for x, y in screws], steel)
    place(b, insert(b), [pose(x, y, boss_bottom) for x, y in screws], brass)
    log(f'B: {n} screws, head in the counterbore z {cb_top - PAN_HEAD[1]:.2f} .. {cb_top:.2f}, tip z '
        f'{cb_top + PLATE_SCREW_L:.2f}; {n} inserts z {boss_bottom:.2f} .. {boss_bottom + INSERT[1]:.2f} '
        f'(thread engaged {cb_top + PLATE_SCREW_L - boss_bottom:.2f})')

    a = groups['A'].component
    n = place(a, nut(a), [pose(x, y, trap_floor) for x, y in screws], steel)
    place(a, screw(a, f'M2 x {SLIM_SCREW_L:g} slim-head screw', SLIM_HEAD, SLIM_SCREW_L),
          [pose(x, y, plate_top, down=True) for x, y in screws], steel)
    log(f'A: {n} nuts z {trap_floor:.2f} .. {trap_floor + NUT[1]:.2f} (trap to z {pocket_floor:.2f}, open above), '
        f'{n} slim-head screws, head on z {plate_top:.2f}, tip z {plate_top - SLIM_SCREW_L:.2f} (thread engaged '
        f'{trap_floor + NUT[1] - (plate_top - SLIM_SCREW_L):.2f})')

    for g, occ in groups.items():
        occ.isLightBulbOn = g in SHOWN
    if design.designType == adsk.fusion.DesignTypes.ParametricDesignType and design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
    app.activeDocument.save('NrskCaseHardware: screws, inserts and nuts')
    return f'{side}: hardware shown (common, B; A hidden), positions from the stored input'


def run(context):
    nrsk_fusion.run_script('NrskCaseHardware', body)
