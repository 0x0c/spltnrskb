"""Overlay drawing: case layers + PCB features, for checking alignment (case/preview/<side>-overlay.svg)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_case import Half, OUT, polygons, rounded_rect, circle  # noqa: E402


def path(cs, x0, y1, pad):
    d = ''
    for poly in polygons(cs):
        d += 'M' + ' L'.join(f'{x - x0 + pad:.3f},{y1 - y + pad:.3f}' for x, y in poly) + ' Z '
    return d


def main(side):
    hf = Half(side)
    x0, y0, x1, y1 = map(float, hf.outer.bounds())
    pad = 3
    w, h = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
    px0, py0, px1, py1, r = hf.pcb
    pcb = rounded_rect(px0, py0, px1, py1, r)
    items = [
        (hf.bottom(), '#888', 0.25, 'none'),
        (hf.frame(1), '#2a7', 0.25, 'rgba(40,170,110,0.15)'),
        (pcb, '#06c', 0.3, 'rgba(0,100,200,0.10)'),
        (hf.plate(), '#d22', 0.2, 'none'),
        (hf.cover(), '#09c', 0.3, 'rgba(0,150,220,0.15)'),
        (hf.wheel_cut(0), '#a60', 0.4, 'rgba(250,160,0,0.25)'),
    ]
    body = ''
    for cs, col, sw, fill in items:
        body += f'<path d="{path(cs, x0, y1, pad)}" fill="{fill}" fill-rule="evenodd" stroke="{col}" stroke-width="{sw}"/>'
    for x, y in hf.d['holes']:
        body += f'<circle cx="{x - x0 + pad:.2f}" cy="{-y - y0 + pad + (y1 + y0) - (y1 + y0):.2f}" r="0"/>'
    for x, y in hf.d['holes']:
        cx, cy = x - x0 + pad, y1 - (-y) + pad
        body += f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="2.3" fill="none" stroke="#a0a" stroke-width="0.3"/>'
    rx, ry = hf.d['reset']
    body += f'<circle cx="{rx - x0 + pad:.2f}" cy="{y1 + ry + pad:.2f}" r="1.5" fill="#fa0"/>'
    for name, c in hf.d['connectors'].items():
        bx0, by0, bx1, by1 = c['box']
        body += (f'<rect x="{bx0 - x0 + pad:.2f}" y="{y1 + by0 + pad:.2f}" width="{bx1 - bx0:.2f}" height="{by1 - by0:.2f}" '
                 f'fill="rgba(250,160,0,0.4)" stroke="#a60" stroke-width="0.2"/>')
    open(os.path.join(OUT, 'preview', f'{side}-overlay.svg'), 'w').write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 4:.0f}" height="{h * 4:.0f}" viewBox="0 0 {w:.2f} {h:.2f}">'
        f'<rect width="100%" height="100%" fill="white"/>{body}</svg>')


if __name__ == '__main__':
    for s in sys.argv[1:] or ('left', 'right'):
        main(s)
