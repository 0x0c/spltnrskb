"""KLE layout -> key list with physical position and electrical matrix position."""
import json
import os

U = 19.05  # 1u pitch [mm]
HERE = os.path.dirname(os.path.abspath(__file__))

# RP2040 GPIO assignment (same on both halves)
ROW_PINS = ['GP4', 'GP5', 'GP6', 'GP7', 'GP8', 'GP9']
COL_PINS = ['GP10', 'GP11', 'GP12', 'GP13', 'GP14', 'GP16', 'GP17', 'GP18']   # GP15 skipped: corner pin next to TESTEN/XIN
SERIAL_PIN = 'GP1'  # QMK split serial (PIO, half duplex) on the TRRS tip
HAND_PIN = 'GP0'    # 10k to 3V3 on left / GND on right
I2C_SDA, I2C_SCL = 'GP2', 'GP3'   # I2C1: OLED
WHEEL_PIN_A, WHEEL_PIN_B = 'GP19', 'GP20'   # corner thumbwheel encoder (common to GND, internal pull-ups)
WHEEL_I2C_ADDR = 0x36
WHEEL_DETENTS = 12   # clicks (= pulses) per turn of the thumbwheel encoder, Alps EC05E1220401
N_ROWS, N_COLS = len(ROW_PINS), len(COL_PINS)


def parse_kle(path):
    data = json.load(open(path))
    keys = []
    y = 0.0
    for row in data:
        if isinstance(row, dict):
            continue
        x, w, h = 0.0, 1.0, 1.0
        idx = 0
        for item in row:
            if isinstance(item, dict):
                x += item.get('x', 0)
                y += item.get('y', 0)
                w = item.get('w', w)
                h = item.get('h', h)
                continue
            parts = item.split('\n')
            legend = [p for p in parts[1:] if p]
            name = next((parts[i] for i in (1, 6, 9) if len(parts) > i and parts[i]), '')
            keys.append(dict(id=parts[0], name=name, legends=legend, x=x, y=y, w=w, h=h,
                             prow=int(y), pidx=idx))
            idx += 1
            x += w
            w, h = 1.0, 1.0
        y += 1
    return keys


def load(side):
    keys = parse_kle(os.path.join(HERE, '..', 'kle', f'{side}.json'))
    for k in keys:
        r, c = k['prow'], k['pidx']
        if side == 'right' and r == 2 and c == 8:
            r, c = 0, 7   # "\" key: right half row2 has 9 keys, row0 only 7
        k['row'], k['col'] = r, c
        k['cx'] = (k['x'] + k['w'] / 2) * U
        k['cy'] = (k['y'] + k['h'] / 2) * U
    seen = set()
    for k in keys:
        assert (k['row'], k['col']) not in seen, k
        assert k['col'] < N_COLS and k['row'] < N_ROWS, k
        seen.add((k['row'], k['col']))
    return keys


if __name__ == '__main__':
    for side in ('left', 'right'):
        ks = load(side)
        print(side, len(ks))
        for r in range(N_ROWS):
            print(' ', ' '.join(f"{(next((k['name'] or k['id']) for k in ks if (k['row'], k['col']) == (r, c)) if (r, c) in {(k['row'], k['col']) for k in ks} else '-'):>5}" for c in range(N_COLS)))
