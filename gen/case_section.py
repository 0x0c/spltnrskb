import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from manifold3d import Manifold
from make_case import *
fig, axes = plt.subplots(2, 1, figsize=(14, 8))
for ax, (side, which) in zip(axes, [('left', 'usb'), ('left', 'holes')]):
    hf = Half(side)
    z_pcb = FLOOR + STANDOFF
    parts = [(hf.tray(), '#bbb'), (hf.pcb3d().translate((0, 0, z_pcb)), '#2a7'),
             (hf.plate3d().translate((0, 0, z_pcb + PCB_T + PLATE_GAP)), '#89a')]
    if which == 'usb':
        c = hf.d['connectors']['usb']; y = (c['box'][1] + c['box'][3]) / 2
    else:
        y = hf.d['holes'][0][1]
    for m, col in parts:
        # rotate so that the section plane (board y = const) becomes z = const
        r = m.rotate((90, 0, 0))   # (x, y, z) -> (x, -z, y)
        sec = r.slice(-y)
        for poly in sec.to_polygons():
            ax.add_patch(Polygon(poly, closed=True, fc=col, ec='k', lw=0.3))
    ax.set_title(f'{side}: section at board y={y:.1f} ({which})'); ax.set_aspect('equal'); ax.autoscale()
    x0, _, x1, _ = map(float, hf.outer.bounds())
    if which == 'usb':
        ax.set_xlim(x1 - 45, x1 + 3)
    ax.set_ylim(-16, 2); ax.grid(lw=0.2)
plt.tight_layout(); plt.savefig(os.path.join(OUT, 'preview', 'case-section.png'), dpi=110)
