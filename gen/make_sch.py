"""Generate the KiCad schematic for one half: <side>/nrsk-<side>.kicad_sch.

Each half carries its own ATmega32U4 (TQFP-44) with USB-C, crystal and support parts.
"""
import math
import os
import sys
import uuid

import sexpr
import make_pro
from layout import HERE, ROW_PINS, COL_PINS, SERIAL_PIN, HAND_PIN, N_ROWS, N_COLS, load
from footprints import WIDTHS

KI_SYM = os.path.expanduser('~/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/')

FP = {
    'diode': 'Diode_SMD:D_SOD-123',
    'trrs': 'Connector_Audio:Jack_3.5mm_PJ320D_Horizontal',
    'usb': 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
    'mcu': 'Package_QFP:TQFP-44_10x10mm_P0.8mm',
    'esd': 'Package_TO_SOT_SMD:SOT-23-6',
    'xtal': 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm_HandSoldering',
    'r': 'Resistor_SMD:R_0805_2012Metric',
    'c': 'Capacitor_SMD:C_0805_2012Metric',
    'fuse': 'Fuse:Fuse_1206_3216Metric',
    'reset': 'Button_Switch_SMD:SW_SPST_PTS810',
}

# ATmega32U4 TQFP-44 pin -> port name
MCU_PORTS = {1: 'E6', 8: 'B0', 9: 'B1', 10: 'B2', 11: 'B3', 12: 'B7', 18: 'D0', 19: 'D1', 20: 'D2', 21: 'D3',
             22: 'D5', 25: 'D4', 26: 'D6', 27: 'D7', 28: 'B4', 29: 'B5', 30: 'B6', 31: 'C6', 32: 'C7', 33: 'E2',
             36: 'F7', 37: 'F6', 38: 'F5', 39: 'F4', 40: 'F1', 41: 'F0'}


def key_fp(w):
    ws = min(WIDTHS, key=lambda x: abs(x - w))
    return f'nrsk:SW_MX_Hotswap_{ws:.2f}u'


class Lib:
    """Symbols from KiCad's standard libraries, with `extends` flattened."""

    def __init__(self):
        self.cache, self.used = {}, {}

    def _lib(self, lib):
        if lib not in self.cache:
            t = sexpr.parse(open(KI_SYM + lib + '.kicad_sym').read())
            self.cache[lib] = {s[1]: s for s in sexpr.find(t, 'symbol')}
        return self.cache[lib]

    def get(self, lib_id):
        if lib_id in self.used:
            return self.used[lib_id]
        lib, name = lib_id.split(':')
        src = self._lib(lib)[name]
        ext = sexpr.find1(src, 'extends')
        if ext:
            base = self._lib(lib)[ext[1]]
            sym = [x for x in base if not (isinstance(x, list) and x[0] == 'property')]
            sym = [sexpr.Sym('symbol'), lib_id] + [x for x in sym[2:]]
            sym += sexpr.find(src, 'property')
            for sub in sexpr.find(sym, 'symbol'):
                sub[1] = sub[1].replace(ext[1], name, 1)
        else:
            sym = list(src)
            sym[1] = lib_id
        self.used[lib_id] = sym
        return sym

    def pins(self, lib_id):
        out = []

        def walk(n):
            for x in n:
                if isinstance(x, list):
                    if x[0] == 'pin':
                        at = sexpr.find1(x, 'at')
                        out.append((sexpr.find1(x, 'number')[1], float(at[1]), float(at[2]), float(at[3])))
                    else:
                        walk(x)
        walk(self.get(lib_id))
        return out

    def dump(self):
        return '\t(lib_symbols\n\t\t' + '\n\t\t'.join(sexpr.dump(s, 1) for s in self.used.values()) + '\n\t)\n'


class Sheet:
    def __init__(self, project):
        self.project = project
        self.root = self.u('root')
        self.items = []
        self.pwr = 0
        self.lib = Lib()

    def u(self, key):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f'nrsk/{self.project}/{key}'))

    @staticmethod
    def xform(px, py, x, y, rot):
        r = math.radians(rot)
        rx = px * math.cos(r) - py * math.sin(r)
        ry = px * math.sin(r) + py * math.cos(r)
        return round(x + rx, 2), round(y - ry, 2)

    def symbol(self, lib_id, ref, value, x, y, rot=0, fp='', nets=None, hide_val=False):
        """Place a symbol; `nets` maps pin number -> net name (None = no-connect)."""
        self.lib.get(lib_id)
        pins = self.lib.pins(lib_id)
        is_pwr = ref.startswith('#')
        key = f'sym/{ref}'
        if lib_id.startswith('power:'):
            vx, vy = x, y + (3.81 if lib_id == 'power:GND' else -3.81)
            rx, ry = x, y
        else:
            rx, ry = x + 2.54, y - 2.54
            vx, vy = x + 2.54, y + 2.54
        s = (f'(symbol (lib_id {sexpr.q(lib_id)}) (at {x:.2f} {y:.2f} {rot}) (unit 1) (exclude_from_sim no) '
             f'(in_bom {"no" if is_pwr else "yes"}) (on_board {"no" if is_pwr else "yes"}) (dnp no) '
             f'(uuid "{self.u(key)}")\n')
        hr = ' (hide yes)' if is_pwr else ''
        hv = ' (hide yes)' if hide_val else ''
        s += f'  (property "Reference" {sexpr.q(ref)} (at {rx:.2f} {ry:.2f} 0) (effects (font (size 1.27 1.27)) (justify left){hr}))\n'
        s += f'  (property "Value" {sexpr.q(value)} (at {vx:.2f} {vy:.2f} 0) (effects (font (size 1.27 1.27)) (justify left){hv}))\n'
        s += f'  (property "Footprint" {sexpr.q(fp)} (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
        s += f'  (property "Datasheet" "" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
        for num, *_ in pins:
            s += f'  (pin {sexpr.q(num)} (uuid "{self.u(key + "/pin/" + num)}"))\n'
        s += (f'  (instances (project {sexpr.q(self.project)} (path "/{self.root}" '
              f'(reference {sexpr.q(ref)}) (unit 1))))\n)')
        self.items.append(s)
        if nets is None:
            return
        done = set()
        for num, px, py, pa in pins:
            if num not in nets:
                continue
            pt = self.xform(px, py, x, y, rot)
            if pt in done:
                continue
            done.add(pt)
            # outward direction = opposite to the pin's drawing direction
            a = math.radians(pa + rot + 180)
            dx, dy = round(math.cos(a)), -round(math.sin(a))
            self.attach(nets[num], pt, (dx, dy))

    def attach(self, net, pt, d):
        x, y = pt
        if net is None:
            self.nc(x, y)
        elif net in ('GND', 'VCC'):
            ex, ey = x + d[0] * 5.08, y + d[1] * 5.08
            self.wire(x, y, ex, ey)
            rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[d] if net == 'GND' else \
                  {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}[d]
            self.power(net, ex, ey, rot)
        else:
            rot = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
            self.label(net, x, y, rot)

    def power(self, kind, x, y, rot=0):
        self.pwr += 1
        ref = f'#{"FLG" if kind == "PWR_FLAG" else "PWR"}{self.pwr:03d}'
        self.symbol(f'power:{kind}', ref, kind, x, y, rot)

    def label(self, name, x, y, rot=0):
        j = 'right' if rot in (180, 270) else 'left'
        self.items.append(f'(label {sexpr.q(name)} (at {x:.2f} {y:.2f} {rot}) '
                          f'(effects (font (size 1.27 1.27)) (justify {j} bottom)) (uuid "{self.u(f"lbl/{name}/{x}/{y}")}"))')

    def wire(self, x1, y1, x2, y2):
        self.items.append(f'(wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})) '
                          f'(stroke (width 0) (type default)) (uuid "{self.u(f"w/{x1}/{y1}/{x2}/{y2}")}"))')

    def nc(self, x, y):
        self.items.append(f'(no_connect (at {x:.2f} {y:.2f}) (uuid "{self.u(f"nc/{x}/{y}")}"))')

    def text(self, s, x, y, size=2.0):
        self.items.append(f'(text {sexpr.q(s)} (exclude_from_sim no) (at {x:.2f} {y:.2f} 0) '
                          f'(effects (font (size {size} {size}) (bold yes)) (justify left bottom)) (uuid "{self.u(f"t/{s}/{x}/{y}")}"))')

    def write(self, path, title):
        body_items = ''.join('\t' + it.replace('\n', '\n\t') + '\n' for it in self.items)
        hdr = ('(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n\t(generator_version "9.0")\n'
               f'\t(uuid "{self.root}")\n\t(paper "A2")\n'
               f'\t(title_block (title {sexpr.q(title)}) (rev "2.0") (company "nrsk"))\n')
        body = hdr + self.lib.dump() + body_items
        body += '\t(sheet_instances (path "/" (page "1")))\n\t(embedded_fonts no)\n)\n'
        open(path, 'w').write(body)


def two_pin(sh, lib_id, ref, value, x, y, fp, n1, n2):
    """Vertical 2-pin part: pin 1 at top, pin 2 at bottom."""
    sh.symbol(lib_id, ref, value, x, y, 0, fp, {'1': n1, '2': n2})


def build(side):
    project = f'nrsk-{side}'
    keys = load(side)
    sh = Sheet(project)

    # --- key matrix ---------------------------------------------------------
    X0, Y0, DX, DY = 38.1, 50.8, 22.86, 20.32
    sh.text(f'Key matrix ({side} half, COL2ROW, {len(keys)} keys)', X0 - 10.16, Y0 - 12.7)
    for c in range(N_COLS):
        sh.text(f'COL{c}', X0 + c * DX - 7.62, Y0 - 6.35, 1.27)
    for r in range(N_ROWS):
        sh.text(f'ROW{r}', X0 - 20.32, Y0 + r * DY + 1.27, 1.27)
    for i, k in enumerate(keys, 1):
        x, y = X0 + k['col'] * DX, Y0 + k['row'] * DY
        sh.symbol('Switch:SW_Push', f'SW{i}', k['name'] or k['id'], x, y, 0, key_fp(k['w']),
                  {'1': f'COL{k["col"]}', '2': f'K{i}'})
        sh.symbol('Device:D', f'D{i}', '1N4148W', x + 5.08, y + 3.81, 90, FP['diode'],
                  {'1': f'ROW{k["row"]}', '2': f'K{i}'}, hide_val=True)

    # --- MCU ----------------------------------------------------------------
    MX, MY = 279.4, 116.84
    sh.text('MCU: ATmega32U4-AU (TQFP-44), 16 MHz, 5 V', MX - 25.4, MY - 55.88)
    mcu = {}
    for pin, port in MCU_PORTS.items():
        if port in ROW_PINS:
            mcu[str(pin)] = f'ROW{ROW_PINS.index(port)}'
        elif port in COL_PINS:
            mcu[str(pin)] = f'COL{COL_PINS.index(port)}'
        elif port == SERIAL_PIN:
            mcu[str(pin)] = 'DATA'
        elif port == HAND_PIN:
            mcu[str(pin)] = 'HAND'
        elif port == 'E2':
            mcu[str(pin)] = 'HWB'
        else:
            mcu[str(pin)] = None
    mcu.update({'2': 'VCC', '14': 'VCC', '24': 'VCC', '3': 'D-', '4': 'D+', '5': 'GND', '15': 'GND',
                '6': 'UCAP', '7': 'VBUS', '13': 'RST', '16': 'XTAL2', '17': 'XTAL1', '42': None})
    sh.symbol('MCU_Microchip_ATmega:ATmega32U4-A', 'U1', 'ATmega32U4-AU', MX, MY, 0, FP['mcu'], mcu)

    # crystal
    sh.text('Clock', 190.5, 63.5)
    sh.symbol('Device:Crystal_GND24', 'Y1', '16MHz', 203.2, 76.2, 0, FP['xtal'], {'1': 'XTAL1', '3': 'XTAL2', '2': 'GND'})
    two_pin(sh, 'Device:C', 'C1', '22pF', 190.5, 88.9, FP['c'], 'XTAL1', 'GND')
    two_pin(sh, 'Device:C', 'C2', '22pF', 215.9, 88.9, FP['c'], 'XTAL2', 'GND')

    # decoupling
    sh.text('Decoupling', 190.5, 109.22)
    for i, (ref, val) in enumerate([('C3', '1uF'), ('C4', '0.1uF'), ('C5', '0.1uF'), ('C6', '0.1uF'),
                                    ('C7', '0.1uF'), ('C8', '10uF')]):
        two_pin(sh, 'Device:C', ref, val, 182.88 + i * 10.16, 124.46, FP['c'], 'UCAP' if ref == 'C3' else 'VCC', 'GND')

    # reset / bootloader
    sh.text('Reset (press = DFU bootloader via HWB)', 190.5, 152.4)
    two_pin(sh, 'Device:R', 'R6', '10k', 190.5, 167.64, FP['r'], 'VCC', 'RST')
    sh.symbol('Switch:SW_Push', 'RSW1', 'Reset', 205.74, 180.34, 0, FP['reset'], {'1': 'RST', '2': 'GND'})
    two_pin(sh, 'Device:R', 'R7', '10k', 223.52, 167.64, FP['r'], 'HWB', 'GND')
    two_pin(sh, 'Device:R', 'R1', '10k', 238.76, 167.64, FP['r'], 'HAND', 'VCC' if side == 'left' else 'GND')
    sh.text(f'Handedness: PD3 {"high = left" if side == "left" else "low = right"}', 233.68, 182.88, 1.27)

    # USB-C
    UX, UY = 342.9, 60.96
    sh.text('USB-C (USB 2.0 device)', UX - 10.16, UY - 30.48)
    usb = {'A4': 'VBUS', 'A1': 'GND', 'A5': 'CC1', 'B5': 'CC2', 'A6': 'USB_D+', 'B6': 'USB_D+',
           'A7': 'USB_D-', 'B7': 'USB_D-', 'A8': None, 'B8': None, 'SH': 'GND'}
    sh.symbol('Connector:USB_C_Receptacle_USB2.0_16P', 'J2', 'USB-C', UX, UY, 0, FP['usb'], usb)
    two_pin(sh, 'Device:R', 'R4', '5.1k', 381.0, 50.8, FP['r'], 'CC1', 'GND')
    two_pin(sh, 'Device:R', 'R5', '5.1k', 391.16, 50.8, FP['r'], 'CC2', 'GND')
    sh.symbol('Power_Protection:USBLC6-2SC6', 'U2', 'USBLC6-2SC6', 381.0, 81.28, 0, FP['esd'],
              {'1': 'USB_D+', '6': 'USB_D+', '3': 'USB_D-', '4': 'USB_D-', '2': 'GND', '5': 'VBUS'})
    sh.symbol('Device:R', 'R2', '22', 406.4, 76.2, 90, FP['r'], {'1': 'D+', '2': 'USB_D+'})
    sh.symbol('Device:R', 'R3', '22', 406.4, 88.9, 90, FP['r'], {'1': 'D-', '2': 'USB_D-'})

    # power path: VBUS -> polyfuse -> Schottky -> VCC (no back-feed into the host / other half)
    sh.text('Power', 335.28, 109.22)
    sh.symbol('Device:Polyfuse', 'F1', '500mA', 342.9, 121.92, 90, FP['fuse'], {'1': 'VFUSE', '2': 'VBUS'})
    sh.symbol('Device:D_Schottky', 'D99', 'B5819W', 363.22, 121.92, 0, FP['diode'], {'1': 'VCC', '2': 'VFUSE'})
    for net, x in (('VBUS', 330.2), ('VCC', 375.92), ('GND', 388.62)):
        sh.label(net, x, 137.16, 0) if net == 'VBUS' else None
    sh.power('PWR_FLAG', 330.2, 137.16, 0)
    sh.power('PWR_FLAG', 375.92, 137.16, 0)
    sh.attach('VCC', (375.92, 137.16), (0, 1))
    sh.power('PWR_FLAG', 388.62, 137.16, 0)
    sh.attach('GND', (388.62, 137.16), (0, 1))

    # TRRS
    JX, JY = 342.9, 175.26
    sh.text('Split link: TRRS 3.5 mm (QMK soft serial)', JX - 12.7, JY - 15.24)
    sh.symbol('Connector_Audio:AudioJack4', 'J1', 'PJ-320D', JX, JY, 0, FP['trrs'],
              {'T': 'DATA', 'R1': None, 'R2': 'VCC', 'S': 'GND'})

    path = os.path.join(HERE, '..', side, project + '.kicad_sch')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sh.write(path, f'nrsk split keyboard - {side} half')
    d = os.path.dirname(path)
    make_pro.write(side)
    open(os.path.join(d, 'fp-lib-table'), 'w').write(
        '(fp_lib_table\n\t(version 7)\n\t(lib (name "nrsk") (type "KiCad") (uri "${KIPRJMOD}/../lib/nrsk.pretty") '
        '(options "") (descr "nrsk keyboard footprints"))\n)\n')
    sl = os.path.join(d, 'sym-lib-table')
    if os.path.exists(sl):
        os.remove(sl)
    print('wrote', path)


if __name__ == '__main__':
    for side in sys.argv[1:] or ('left', 'right'):
        build(side)
