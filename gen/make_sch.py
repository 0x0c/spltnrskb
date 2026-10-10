"""Generate the KiCad schematic for one half: <side>/nrsk-<side>.kicad_sch.

Each half carries its own RP2040 (QFN-56) with QSPI flash, 12 MHz crystal, 3.3 V LDO and USB-C.
"""
import math
import os
import sys
import uuid

import sexpr
import make_pro
from layout import (HERE, ROW_PINS, COL_PINS, SERIAL_PIN, HAND_PIN, I2C_SDA, I2C_SCL, WHEEL_PIN_A, WHEEL_PIN_B,
                    N_ROWS, N_COLS, load)
from footprints import WIDTHS

KI_SYM = os.path.expanduser('~/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/')

FP = {
    'diode': 'Diode_SMD:D_SOD-123',
    'trrs': 'Connector_Audio:Jack_3.5mm_PJ320D_Horizontal',
    'usb': 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
    'mcu': 'Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm',
    'flash': 'Package_SO:SOIC-8_5.3x5.3mm_P1.27mm',
    'ldo': 'Package_TO_SOT_SMD:SOT-23-5',
    'boot': 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm',
    'esd': 'Package_TO_SOT_SMD:SOT-23-6',
    'xtal': 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm_HandSoldering',
    'r': 'Resistor_SMD:R_0805_2012Metric',
    'c': 'Capacitor_SMD:C_0805_2012Metric',
    'fuse': 'Fuse:Fuse_1206_3216Metric',
    'reset': 'Button_Switch_SMD:SW_SPST_PTS810',
    'oled': 'nrsk:OLED_0.91in_128x32_I2C',
    'encoder': 'nrsk:Alps_EC05E1220401',
}

# RP2040 QFN-56: GPIO number -> pin
RP_GPIO = {g: p for g, p in zip(range(16), [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18])}
RP_GPIO.update({g: p for g, p in zip(range(16, 30), [27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 40, 41])})


CUSTOM = {}   # project symbols (lib/nrsk.kicad_sym); everything comes from KiCad's libraries at the moment


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
        if lib_id in CUSTOM:
            self.used[lib_id] = sexpr.parse(CUSTOM[lib_id])
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
    sh.text('MCU: RP2040 (QFN-56), 12 MHz, 3.3 V I/O, 16 MB QSPI flash', MX - 25.4, MY - 55.88)
    roles = {SERIAL_PIN: 'DATA', HAND_PIN: 'HAND', I2C_SDA: 'SDA', I2C_SCL: 'SCL', WHEEL_PIN_A: 'ENC_A', WHEEL_PIN_B: 'ENC_B'}
    roles.update({p: f'ROW{i}' for i, p in enumerate(ROW_PINS)})
    roles.update({p: f'COL{i}' for i, p in enumerate(COL_PINS)})
    mcu = {str(pin): roles.get(f'GP{g}') for g, pin in RP_GPIO.items()}
    mcu.update({str(p): '3V3' for p in (1, 10, 22, 33, 42, 49, 43, 44, 48)})   # IOVDD, ADC_AVDD, VREG_VIN, USB_VDD
    mcu.update({'23': '1V1', '50': '1V1', '45': '1V1',                       # DVDD <- internal regulator
                '19': 'GND', '57': 'GND', '20': 'XIN', '21': 'XOUT', '24': None, '25': None, '26': 'RUN',
                '46': 'D-', '47': 'D+', '51': 'QSPI_SD3', '52': 'QSPI_SCLK', '53': 'QSPI_SD0', '54': 'QSPI_SD2',
                '55': 'QSPI_SD1', '56': 'QSPI_SS'})
    sh.symbol('MCU_RaspberryPi:RP2040', 'U1', 'RP2040', MX, MY, 0, FP['mcu'], mcu)

    # QSPI flash
    sh.text('Flash', 228.6, 15.24)
    sh.symbol('Memory_Flash:W25Q128JVS', 'U5', 'W25Q128JVS', 241.3, 30.48, 0, FP['flash'],
              {'1': 'QSPI_SS', '2': 'QSPI_SD1', '3': 'QSPI_SD2', '4': 'GND', '5': 'QSPI_SD0', '6': 'QSPI_SCLK',
               '7': 'QSPI_SD3', '8': '3V3'})

    # crystal (Raspberry Pi reference: 1k in series with XOUT, 15 pF loads)
    sh.text('Clock', 190.5, 63.5)
    sh.symbol('Device:Crystal_GND24', 'Y1', '12MHz', 203.2, 76.2, 0, FP['xtal'], {'1': 'XIN', '3': 'XTAL', '2': 'GND', '4': 'GND'})
    two_pin(sh, 'Device:C', 'C1', '15pF', 190.5, 88.9, FP['c'], 'XIN', 'GND')
    two_pin(sh, 'Device:C', 'C2', '15pF', 215.9, 88.9, FP['c'], 'XTAL', 'GND')
    sh.symbol('Device:R', 'R10', '1k', 228.6, 76.2, 90, FP['r'], {'1': 'XTAL', '2': 'XOUT'})

    # decoupling
    sh.text('Decoupling', 190.5, 109.22)
    caps = [('C3', '1uF', '3V3'), ('C4', '1uF', '1V1'), ('C5', '0.1uF', '1V1'), ('C6', '0.1uF', '1V1'),
            ('C7', '0.1uF', '3V3'), ('C8', '0.1uF', '3V3'), ('C11', '0.1uF', '3V3'), ('C12', '0.1uF', '3V3'),
            ('C13', '0.1uF', '3V3'), ('C14', '0.1uF', '3V3'), ('C15', '0.1uF', '3V3'), ('C18', '0.1uF', '3V3'),
            ('C19', '10uF', '3V3'), ('C20', '0.1uF', '3V3')]
    for i, (ref, val, net) in enumerate(caps):
        two_pin(sh, 'Device:C', ref, val, 182.88 + (i % 7) * 10.16, 124.46 + (i // 7) * 15.24, FP['c'], net, 'GND')

    # reset / bootloader
    sh.text('Reset (double-tap = bootloader) / BOOTSEL pads', 190.5, 160.02)
    two_pin(sh, 'Device:R', 'R6', '10k', 190.5, 175.26, FP['r'], '3V3', 'RUN')
    sh.symbol('Switch:SW_Push', 'RSW1', 'Reset', 205.74, 187.96, 0, FP['reset'], {'1': 'RUN', '2': 'GND'})
    two_pin(sh, 'Device:R', 'R7', '1k', 223.52, 175.26, FP['r'], 'QSPI_SS', 'BOOT')
    sh.symbol('Jumper:SolderJumper_2_Open', 'JP1', 'BOOTSEL', 236.22, 187.96, 0, FP['boot'], {'1': 'BOOT', '2': 'GND'})
    two_pin(sh, 'Device:R', 'R1', '10k', 251.46, 175.26, FP['r'], 'HAND', '3V3' if side == 'left' else 'GND')
    sh.text(f'Handedness: {HAND_PIN} {"high = left" if side == "left" else "low = right"}', 246.38, 190.5, 1.27)

    # 3.3 V regulator
    sh.text('3.3 V LDO', 190.5, 205.74)
    sh.symbol('Regulator_Linear:AP2112K-3.3', 'U4', 'AP2112K-3.3', 210.82, 220.98, 0, FP['ldo'],
              {'1': 'VCC', '3': 'VCC', '2': 'GND', '4': None, '5': '3V3'})
    two_pin(sh, 'Device:C', 'C16', '1uF', 193.04, 228.6, FP['c'], 'VCC', 'GND')
    two_pin(sh, 'Device:C', 'C17', '1uF', 228.6, 228.6, FP['c'], '3V3', 'GND')

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
    sh.symbol('Device:R', 'R2', '27', 406.4, 76.2, 90, FP['r'], {'1': 'D+', '2': 'USB_D+'})
    sh.symbol('Device:R', 'R3', '27', 406.4, 88.9, 90, FP['r'], {'1': 'D-', '2': 'USB_D-'})

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
    sh.text('Split link: TRRS 3.5 mm (5 V + QMK serial)', JX - 12.7, JY - 15.24)
    sh.symbol('Connector_Audio:AudioJack4', 'J1', 'PJ-320D', JX, JY, 0, FP['trrs'],
              {'T': 'DATA', 'R1': None, 'R2': 'VCC', 'S': 'GND'})

    # OLED (0.91" SSD1306, I2C on PD0/PD1)
    OX, OY = 342.9, 215.9
    sh.text('OLED 0.91" 128x32 (I2C, SSD1306, 3.3 V)', OX - 12.7, OY - 15.24)
    sh.symbol('Connector_Generic:Conn_01x04', 'J3', 'OLED 128x32', OX, OY, 0, FP['oled'],
              {'1': 'GND', '2': '3V3', '3': 'SCL', '4': 'SDA'})
    two_pin(sh, 'Device:R', 'R8', '4.7k', OX + 25.4, OY - 2.54, FP['r'], '3V3', 'SCL')
    two_pin(sh, 'Device:R', 'R9', '4.7k', OX + 35.56, OY - 2.54, FP['r'], '3V3', 'SDA')

    # corner thumbwheel: Alps EC05E1220401 on the back under the wheel; RP2040 internal pull-ups on A and B
    AX, AY = 342.9, 254.0
    sh.text('Thumbwheel encoder Alps EC05E1220401 (12 detents / 12 pulses, C = common)', AX - 12.7, AY - 12.7)
    sh.symbol('Device:RotaryEncoder', 'ENC1', 'EC05E1220401', AX, AY, 0, FP['encoder'],
              {'A': 'ENC_A', 'B': 'ENC_B', 'C': 'GND'})

    path = os.path.join(HERE, '..', side, project + '.kicad_sch')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sh.write(path, f'nrsk split keyboard - {side} half')
    d = os.path.dirname(path)
    make_pro.write(side)
    open(os.path.join(d, 'fp-lib-table'), 'w').write(
        '(fp_lib_table\n\t(version 7)\n\t(lib (name "nrsk") (type "KiCad") (uri "${KIPRJMOD}/../lib/nrsk.pretty") '
        '(options "") (descr "nrsk keyboard footprints"))\n)\n')
    # project symbol library (custom symbols, if any)
    lib_sym = os.path.join(HERE, '..', 'lib', 'nrsk.kicad_sym')
    body = '\n'.join(v.replace('"nrsk:', '"', 1) for v in CUSTOM.values())
    open(lib_sym, 'w').write('(kicad_symbol_lib (version 20241209) (generator "nrsk-gen") (generator_version "10.0")\n'
                             + body + '\n)\n')
    open(os.path.join(d, 'sym-lib-table'), 'w').write(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "nrsk") (type "KiCad") (uri "${KIPRJMOD}/../lib/nrsk.kicad_sym") '
        '(options "") (descr "nrsk keyboard symbols"))\n)\n')
    print('wrote', path)


if __name__ == '__main__':
    for side in sys.argv[1:] or ('left', 'right'):
        build(side)
