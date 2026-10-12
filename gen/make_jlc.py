"""JLCPCB assembly files for each board -> fab/<side>/nrsk-<side>-jlc-bom.csv and nrsk-<side>-jlc-cpl.csv.

Halves: every part with an LCSC number (first source in bom_sources.json) is listed, except the ones assembled by
hand: the OLED module (glass height set by hand), the drum dial encoder (through-hole on the front), the hot-swap
sockets and the BOOTSEL pad (no part). All assembled parts sit on the back of the board.
Encoder test board (enctest): every part on it, the through-hole ones on the front included (EXTRA gives the LCSC
number of the tact switch, which the halves do not have). The ConThrough rows J1/J2 are only holes: the ConThrough
pins are soldered to the RP2040-Zero, not to this board, so they are no part to place.

JLCPCB places its own (EasyEDA) footprint for each LCSC part. Where that footprint is turned or has its origin
elsewhere than the KiCad one, the placement is corrected with JLC_FIX below. Values were found by fitting the
EasyEDA footprints (easyeda2kicad, 2026-10-10) onto the placed KiCad pads, pad by pad; the rotations agree with
the JLCKicadTools rotation table (SOT-23 -90, SOIC 270, 2-pad parts and the standard QFN-56 0) except the HRO
USB-C, whose current EasyEDA footprint has the same orientation as KiCad's (the table says 180).
Back-side convention as in kicad-jlcpcb-tools: rotation = 180 - KiCad rotation + correction, position = board
coordinates with y up (the gerbers are plotted in absolute coordinates too). Front side: rotation = KiCad rotation
+ correction.

Run:  NRSK_KC=<kicad-cli> python3 gen/make_jlc.py [left right]
"""
import csv
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_bom import ELEC, HERE, ROOT  # noqa: E402

HAND = ('nrsk:OLED_0.91in_128x32_I2C', 'nrsk:Alps_EC10E', 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm')
# KiCad footprint name -> (rotation correction in degrees, EasyEDA origin in KiCad footprint coordinates, mm)
JLC_FIX = {
    'SOT-23-5': (270, (0.0, 0.0)),
    'SOT-23-6': (270, (0.0, 0.0)),
    'SOIC-8_5.3x5.3mm_P1.27mm': (270, (0.0, 0.0)),
    'USB_C_Receptacle_HRO_TYPE-C-31-M-12': (0, (0.0, -1.575)),     # EasyEDA origin 2.47 mm behind the signal pads
    'Alps_EC05E1220401': (0, (0.0, 2.08)),                          # EasyEDA origin 2.08 mm toward the terminals
    'Alps_EC10E': (270, (-2.7, 0.0)),                               # EasyEDA origin between terminals and legs
    'SW_PUSH_6mm_H9.5mm': (0, (3.25, 2.25)),                        # KiCad origin on pin 1, EasyEDA's in the middle
}
# boards assembled completely: (value, footprint) -> LCSC number for parts the halves' BOM does not list
EXTRA = {
    'enctest': {('Layer 1', 'Button_Switch_THT:SW_PUSH_6mm_H9.5mm'): 'C87121'},   # Omron B3F-1072, 6x6 mm, 9.5 mm tall
}


def kicad_cli():
    for kc in (os.environ.get('NRSK_KC'),
               os.path.expanduser('~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'),
               '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'):
        if kc and os.path.exists(kc):
            return kc
    sys.exit('kicad-cli not found (set NRSK_KC)')


def lcsc_numbers(side):
    """(value, footprint) -> LCSC number, from the first source of each BOM part."""
    sources = json.load(open(os.path.join(HERE, 'bom_sources.json'), encoding='utf-8'))
    hand = () if side in EXTRA else HAND
    out = {}
    for key, (_, part, _) in ELEC.items():
        shop = (sources.get(part) or [{}])[0].get('shop', '')
        if key[1] not in hand and shop.startswith('LCSC '):
            out[key] = shop.split()[1]
    out.update(EXTRA.get(side, {}))
    return out


def positions(side):
    pcb = os.path.join(ROOT, side, f'nrsk-{side}.kicad_pcb')
    tmp = os.path.join(ROOT, 'build', f'{side}-pos.csv')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    subprocess.run([kicad_cli(), 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
                    '-o', tmp, pcb], check=True, capture_output=True)
    return {r['Ref']: r for r in csv.DictReader(open(tmp, encoding='utf-8'))}


def placement(row):
    """JLC (x, y, layer, rotation) of one part from its KiCad position row."""
    rot = float(row['Rot'])
    fix, (ox, oy) = JLC_FIX.get(row['Package'], (0, (0.0, 0.0)))
    if row['Side'] == 'bottom':
        # KiCad puts a back-side footprint at  T + R(180 - rot) . mirror-x . p  (y-down board coordinates)
        a = math.radians(180 - rot)
        dx, dy = -ox * math.cos(a) - oy * math.sin(a), -ox * math.sin(a) + oy * math.cos(a)
        layer, jrot = 'Bottom', 180 - rot + fix
    else:
        # and a front-side one at  T + R(-rot) . p  (y-down board coordinates, KiCad angles counter-clockwise)
        a = math.radians(-rot)
        dx, dy = ox * math.cos(a) - oy * math.sin(a), ox * math.sin(a) + oy * math.cos(a)
        layer, jrot = 'Top', rot + fix
    x, y_down = float(row['PosX']) + dx, -float(row['PosY']) + dy
    return x, -y_down, layer, jrot % 360


def main(sides):
    for side in sides:
        lcsc = lcsc_numbers(side)
        pos = positions(side)
        bom, cpl = [], []
        for r in csv.DictReader(open(os.path.join(ROOT, 'fab', side, f'nrsk-{side}-bom.csv'), encoding='utf-8')):
            key = (r['Value'], r['Footprint'])
            if key not in lcsc:
                continue
            refs = r['Refs'].split(',')
            bom.append((r['Value'], ','.join(refs), r['Footprint'].split(':')[1], lcsc[key]))
            for ref in refs:
                x, y, layer, rot = placement(pos[ref])
                cpl.append((ref, f'{x:.4f}', f'{y:.4f}', layer, f'{rot:g}'))
        out = os.path.join(ROOT, 'fab', side)
        with open(os.path.join(out, f'nrsk-{side}-jlc-bom.csv'), 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(('Comment', 'Designator', 'Footprint', 'LCSC Part #'))
            w.writerows(bom)
        with open(os.path.join(out, f'nrsk-{side}-jlc-cpl.csv'), 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(('Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'))
            w.writerows(sorted(cpl, key=lambda c: (c[0].rstrip('0123456789'), int(c[0][len(c[0].rstrip('0123456789')):]))))
        print(f'{side}: {len(bom)} BOM lines, {len(cpl)} placements')


if __name__ == '__main__':
    main(sys.argv[1:] or ['left', 'right'])
