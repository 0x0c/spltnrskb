"""KLE layout -> key list with physical position and electrical matrix position."""
import json
import os

U = 19.05  # 1u pitch [mm]
HERE = os.path.dirname(os.path.abspath(__file__))

# Pro Micro pin assignment (same on both halves)
ROW_PINS = ['F4', 'F5', 'F6', 'F7', 'B1', 'B3']          # A3 A2 A1 A0 15 14
COL_PINS = ['D4', 'C6', 'D7', 'E6', 'B4', 'B5', 'B6', 'B2']  # 4 5 6 7 8 9 10 16
SERIAL_PIN = 'D2'   # RX1, QMK soft serial (half duplex)
HAND_PIN = 'D3'     # TX0, tied to VCC on left / GND on right
# corner thumbwheel: AS5600 magnetic angle sensor on the I2C bus (PD0 / PD1, shared with the OLED)
WHEEL_I2C_ADDR = 0x36
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
