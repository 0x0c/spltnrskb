"""USB-C / TRRS opening study (case/preview/port-variants/): four ways to make the plug openings tidy.

Render-only geometry for the left half of the 3D-printed tray (variant B), compared by
gen/render_blender.py --ports <style>:
  current : today's openings, cut from the floor up to the PCB (plugs pass under the PCB)
  tidy    : 4 - same connector positions, rounded holes sized for the plug overmold
  stepped : 2 - same positions, overmold-sized counterbore 2.5 mm deep, shell-sized hole behind it
  flush   : 1 - PCB tongue brings the connector mouths to the outer surface; shell-sized holes,
                a removable port cap above each port (seam through the hole centre)
  panel   : 3 - panel-mount USB-C (flanged, 2 screws) and 3.5 mm jack (hex nut) in the wall
Writes left-<style>-*.stl and parts.json (file -> material).
Run with the project venv:  .venv/bin/python gen/port_variants.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifold3d import CrossSection, JoinType, Manifold  # noqa: E402
from make_case import (Half, OUT, FLOOR, STANDOFF, PCB_T, PLATE_GAP, CLEAR, WALL, rect,  # noqa: E402
                       write_stl)

STYLES = ['current', 'tidy', 'stepped', 'flush', 'panel']
USB_SHELL = (8.94, 3.26, 7.35)          # w, h, length of the HRO TYPE-C-31-M-12 shell
OVERMOLD = (13.0, 7.5)                  # USB-C plug overmold (USB-IF max 12.35 x 6.5) + clearance
TRRS_BODY = (6.1, 5.0, 12.1)            # PJ-320D body w, h, length; nozzle below
TRRS_NOZZLE = (5.0, 2.0)                # diameter, length
TRRS_PLUG = 9.5                         # 3.5 mm plug overmold + clearance
EPS = 0.05


def stadium(w, h):
    r = min(w, h) / 2
    return CrossSection.square((w - 2 * r, h - 2 * r), center=True).offset(r, JoinType.Round, circular_segments=48)


def prism(cs, length):
    """Cross-section in X (across) / Z (up), extruded along -Y from y=0 to y=-length."""
    return Manifold.extrude(cs, length).rotate((90, 0, 0))


def along(m, axis, origin):
    """Place a -Y prism so it points along `axis` ('y' = 3D +y, i.e. board top edge; 'x' = 3D +x) from origin."""
    if axis == 'x':
        m = m.rotate((0, 0, -90))
    return m.translate(origin)


def main():
    out = os.path.join(OUT, 'preview', 'port-variants')
    os.makedirs(out, exist_ok=True)
    hf = Half('left')
    d = hf.d
    x0, y0, x1, y1, _ = hf.pcb
    ox0, oy0, ox1, oy1, _ = hf.outer_box
    z_pcb = FLOOR + STANDOFF                    # PCB bottom (print variant)
    usb = d['connectors']['usb']
    trrs = d['connectors']['trrs']
    ux, uz = usb['center'][0], z_pcb - USB_SHELL[1] / 2           # USB axis: x, z; along 3D +y
    ty, tz = trrs['center'][1], z_pcb - TRRS_NOZZLE[0] / 2        # TRRS axis: board y, z; along 3D +x
    y_out, x_out = -oy0, ox1                                      # outer wall faces (3D frame)
    y_in, x_in = -(y0 - CLEAR), x1 + CLEAR                        # inner wall faces
    wall_top = FLOOR + STANDOFF + PCB_T + PLATE_GAP

    tray = hf.tray()
    ring = hf.outer - hf.inner
    full = tray + Manifold.extrude(hf.slot_cs(False) ^ ring, wall_top - FLOOR - 0.5).translate((0, 0, FLOOR))
    parts = {}

    def holes(usb_cs, usb_len, trrs_d, trrs_len, at_outer=True):
        """Openings cut inward from the outer faces."""
        u = along(prism(usb_cs, usb_len), 'y', (ux, y_out + EPS, uz))
        t = Manifold.cylinder(trrs_len, trrs_d / 2, trrs_d / 2, 48).rotate((0, 90, 0)).translate(
            (x_out + EPS - trrs_len, -ty, tz))
        return u + t

    def receptacles(mouth_inset):
        """USB shell + tongue and TRRS jack with their mouths `mouth_inset` from the outer faces
        (None = at the PCB edge, as built today)."""
        um = y_out - mouth_inset if mouth_inset is not None else -y0
        tm = x_out - mouth_inset if mouth_inset is not None else x1 + 0.355
        shell = prism(stadium(*USB_SHELL[:2]), USB_SHELL[2]) - prism(stadium(USB_SHELL[0] - 0.5, USB_SHELL[1] - 0.5),
                                                                     USB_SHELL[2] - 1).translate((0, 0.01, 0))
        shell = shell.translate((ux, um, uz))       # mouth at um, body running into the case
        tongue = Manifold.cube((6.6, USB_SHELL[2] - 1.5, 0.7), center=True).translate(
            (ux, um - (USB_SHELL[2] - 1.5) / 2 - 0.8, uz))
        nozzle = Manifold.cylinder(TRRS_NOZZLE[1], TRRS_NOZZLE[0] / 2, TRRS_NOZZLE[0] / 2, 48).rotate((0, 90, 0)).translate(
            (tm - TRRS_NOZZLE[1], -ty, tz))
        body = Manifold.cube((TRRS_BODY[2], TRRS_BODY[0], TRRS_BODY[1])).translate(
            (tm - TRRS_NOZZLE[1] - TRRS_BODY[2], -ty - TRRS_BODY[0] / 2, z_pcb - TRRS_BODY[1]))
        bore = Manifold.cylinder(6.0, 1.8, 1.8, 32).rotate((0, 90, 0)).translate((tm - 6.0 + 0.01, -ty, tz))
        return {'shell': shell, 'tongue': tongue, 'jack': nozzle + body - bore, 'bore': bore.scale((1, 0.98, 0.98))}

    for style in STYLES:
        rec = receptacles(None)
        extra = {}
        if style == 'current':
            case = tray
        elif style == 'tidy':
            case = full - holes(stadium(*OVERMOLD), WALL + 1, TRRS_PLUG, WALL + 1)
        elif style == 'stepped':
            case = full - holes(stadium(*OVERMOLD), 2.5, TRRS_PLUG, 2.5) \
                - holes(stadium(USB_SHELL[0] + 0.4, USB_SHELL[1] + 0.5), WALL + 1, 5.6, WALL + 1)
        elif style == 'flush':
            rec = receptacles(0.3)
            case = full - holes(stadium(USB_SHELL[0] + 0.4, USB_SHELL[1] + 0.5), WALL + 1, TRRS_NOZZLE[0] + 0.4, WALL + 1)
            # removable port caps: the wall above each port's centre line, separated by a fine seam
            caps = Manifold()
            for (cx, cy, cz, w, axis) in ((ux, None, uz, 18.0, 'y'), (None, ty, tz, 14.0, 'x')):
                if axis == 'y':
                    box = rect(cx - w / 2, oy0 - 1, cx + w / 2, y0 - CLEAR + 0.01)
                else:
                    box = rect(x1 + CLEAR - 0.01, cy - w / 2, ox1 + 1, cy + w / 2)
                caps = caps + Manifold.extrude(box ^ ring, wall_top - cz).translate((0, 0, cz))
            cap = case ^ caps
            case = case - caps
            extra['cap'] = cap - Manifold.extrude(hf.outer.offset(1, JoinType.Round) - hf.outer.offset(-0.12), 30).translate(
                (0, 0, -1))   # tiny shrink on the outside so the seam reads
        else:   # panel
            rec = receptacles(1.2)
            case = full - holes(stadium(USB_SHELL[0] + 0.6, USB_SHELL[1] + 0.8), WALL + 1, 6.2, WALL + 1)
            flange = prism(stadium(21.0, 8.0) - stadium(USB_SHELL[0] + 0.3, USB_SHELL[1] + 0.4), 1.0)
            flange = flange.translate((ux, y_out + 1.0, uz))   # on the outer face
            heads = Manifold()
            for sx in (-8.0, 8.0):
                heads = heads + Manifold.cylinder(0.9, 1.6, 1.3, 24).rotate((-90, 0, 0)).translate((ux + sx, y_out + 1.0, uz))
            nut = Manifold.cylinder(2.0, 4.0 / math.cos(math.pi / 6), 4.0 / math.cos(math.pi / 6), 6).rotate((0, 90, 0)) \
                - Manifold.cylinder(2.2, 3.0, 3.0, 32).rotate((0, 90, 0)).translate((-0.1, 0, 0))
            nut = nut.translate((x_out, -ty, tz))
            thread = Manifold.cylinder(2.6, 3.0, 3.0, 40).rotate((0, 90, 0)).translate((x_out - 0.6, -ty, tz)) \
                - Manifold.cylinder(3.0, 1.8, 1.8, 32).rotate((0, 90, 0)).translate((x_out - 0.7, -ty, tz))
            extra.update(flange=flange, heads=heads, nut=nut + thread)
        files = {}
        write_stl(os.path.join(out, f'left-{style}-case.stl'), case)
        files[f'left-{style}-case.stl'] = 'case'
        for name, m in list(rec.items()) + list(extra.items()):
            fn = f'left-{style}-{name}.stl'
            write_stl(os.path.join(out, fn), m)
            files[fn] = {'tongue': 'switch', 'bore': 'switch', 'cap': 'case', 'jack': 'switch'}.get(name, 'metal')
        parts[style] = files
    json.dump(dict(parts=parts, focus=[x1, y0, z_pcb]), open(os.path.join(out, 'parts.json'), 'w'), indent=1)
    print('wrote', out, list(parts))


if __name__ == '__main__':
    main()
