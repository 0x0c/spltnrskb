"""Generate QMK keyboard definition and default keymap under firmware/qmk/keyboards/nrsk."""
import json
import os

from layout import HERE, ROW_PINS, COL_PINS, SERIAL_PIN, HAND_PIN, I2C_SDA, I2C_SCL, WHEEL_PIN_A, WHEEL_PIN_B, N_ROWS, load

OUT = os.path.join(HERE, '..', 'firmware', 'qmk', 'keyboards', 'nrsk')

KC = {
    'Esc': 'KC_ESC', 'Tab': 'KC_TAB', 'Ctrl': 'KC_LCTL', 'Shift': 'KC_LSFT', 'Opt': 'KC_LALT', 'Cmd': 'KC_LGUI',
    'Space': 'KC_SPC', 'Backspace': 'KC_BSPC', 'Enter': 'KC_ENT', 'fn': 'MO(1)',
    '↑': 'KC_UP', '↓': 'KC_DOWN', '←': 'KC_LEFT', '→': 'KC_RGHT',
    '`': 'KC_GRV', '-': 'KC_MINS', '=': 'KC_EQL', '[': 'KC_LBRC', ']': 'KC_RBRC', '\\': 'KC_BSLS',
    ';': 'KC_SCLN', "'": 'KC_QUOT', ',': 'KC_COMM', '.': 'KC_DOT', '/': 'KC_SLSH',
}
RIGHT_MODS = {'Opt': 'KC_RALT', 'Cmd': 'KC_RGUI'}
FN = {'↑': 'KC_PGUP', '↓': 'KC_PGDN', '←': 'KC_HOME', '→': 'KC_END', 'Backspace': 'KC_DEL',
      '`': 'KC_ESC'}


def keycode(name, side):
    if side == 'right' and name in RIGHT_MODS:
        return RIGHT_MODS[name]
    if name in KC:
        return KC[name]
    if len(name) == 1 and name.isalnum():
        return 'KC_' + name.upper()
    if name.startswith('F') and name[1:].isdigit():
        return 'KC_' + name
    return 'KC_NO'   # unlabeled keys: assign as you like


ENCODER_KEYMAP_C = r'''
// Corner thumbwheels, one click = one call (index 0 = left half, 1 = right half; clockwise seen from above).
// Returning false skips QMK's default action (volume up / down).
bool encoder_update_user(uint8_t index, bool clockwise) {
    bool fn = get_highest_layer(layer_state) == 1;
    if (index == 0) {
        tap_code(fn ? (clockwise ? KC_BRIU : KC_BRID) : (clockwise ? KC_VOLU : KC_VOLD));
    } else {
        tap_code(fn ? (clockwise ? KC_RGHT : KC_LEFT) : (clockwise ? KC_PGDN : KC_PGUP));
    }
    return false;
}
'''

KB_CONFIG = r'''#pragma once

// RP2040: tap reset twice quickly to enter the USB bootloader (RPI-RP2 drive)
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 500U

// I2C1 on %s (SDA) / %s (SCL): OLED
#define I2C_DRIVER I2CD1
#define I2C1_SDA_PIN %s
#define I2C1_SCL_PIN %s
'''

HALCONF = '''#pragma once
#define HAL_USE_I2C TRUE
#include_next <halconf.h>
'''

MCUCONF = '''#pragma once
#include_next <mcuconf.h>
#undef RP_I2C_USE_I2C1
#define RP_I2C_USE_I2C1 TRUE
'''

OLED_C = r'''
#ifdef OLED_ENABLE
// 0.91" 128x32 OLED mounted vertically on both halves
oled_rotation_t oled_init_user(oled_rotation_t rotation) {
    return OLED_ROTATION_270;
}

static void render_status(void) {
    oled_write_ln_P(PSTR("nrsk"), false);
    oled_write_ln_P(PSTR(""), false);
    oled_write_P(PSTR("LAYR"), false);
    oled_write_char('0' + get_highest_layer(layer_state), false);
    oled_write_ln_P(PSTR(""), false);
    oled_write_ln_P(PSTR(""), false);
    led_t led = host_keyboard_led_state();
    oled_write_ln_P(PSTR("CAPS"), led.caps_lock);
}

static void render_wpm(void) {
    oled_write_ln_P(PSTR("nrsk"), false);
    oled_write_ln_P(PSTR(""), false);
    oled_write_ln_P(PSTR("WPM"), false);
    oled_write(get_u8_str(get_current_wpm(), ' '), false);
}

bool oled_task_user(void) {
    if (is_keyboard_master()) {
        render_status();
    } else {
        render_wpm();
    }
    return false;
}
#endif
'''


def main():
    keys = [(s, k) for s in ('left', 'right') for k in load(s)]
    layout = []
    for side, k in keys:
        row = k['row'] + (N_ROWS if side == 'right' else 0)
        e = {'label': k['name'] or f"#{k['id']}", 'matrix': [row, k['col']], 'x': k['x'], 'y': k['y']}
        if k['w'] != 1:
            e['w'] = k['w']
        layout.append(e)
    # corner thumbwheel encoder (Alps EC05E1220401, one full A/B cycle per click: QMK's default resolution 4).
    # It sits upside down on the PCB back, so its own clockwise is counter-clockwise seen from above: A and B
    # are swapped here to report clockwise as seen by the user.
    wheel = {'pin_a': WHEEL_PIN_B, 'pin_b': WHEEL_PIN_A}
    kb = {
        'manufacturer': 'nrsk',
        'keyboard_name': 'nrsk',
        'maintainer': 'nrsk',
        'url': 'https://github.com/0x0c/spltnrskb',
        'processor': 'RP2040',
        'bootloader': 'rp2040',
        'usb': {'vid': '0xFEED', 'pid': '0x4E52', 'device_version': '1.0.0'},
        'features': {'bootmagic': True, 'encoder': True, 'extrakey': True, 'mousekey': False, 'nkro': True, 'oled': True,
                     'wpm': True},
        'diode_direction': 'COL2ROW',
        'matrix_pins': {'rows': ROW_PINS, 'cols': COL_PINS},
        'encoder': {'rotary': [wheel]},
        'split': {
            'enabled': True,
            'encoder': {'right': {'rotary': [wheel]}},
            'serial': {'driver': 'vendor', 'pin': SERIAL_PIN},
            'handedness': {'pin': HAND_PIN},
            'transport': {'sync': {'layer_state': True, 'indicators': True, 'wpm': True}},
        },
        'layouts': {'LAYOUT': {'layout': layout}},
    }
    os.makedirs(os.path.join(OUT, 'keymaps', 'default'), exist_ok=True)
    json.dump(kb, open(os.path.join(OUT, 'keyboard.json'), 'w'), indent=4, ensure_ascii=False)

    def rows(fn):
        lines, cur, cur_key = [], [], None
        for side, k in keys:
            if (side, k['prow']) != cur_key and cur:
                lines.append(cur); cur = []
            cur_key = (side, k['prow'])
            cur.append(fn(side, k))
        lines.append(cur)
        width = max(len(c) for line in lines for c in line) + 1
        return ',\n        '.join(', '.join(c.ljust(width) for c in line).rstrip() for line in lines)

    base = rows(lambda s, k: keycode(k['name'], s))
    fn = rows(lambda s, k: FN.get(k['name'], 'KC_TRNS'))
    c = f'''// SPDX-License-Identifier: GPL-2.0-or-later
// nrsk split keyboard - default keymap (generated by gen/make_qmk.py)
// Unlabeled keys in the KLE layout are KC_NO; assign them as you like.
#include QMK_KEYBOARD_H

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {{
    [0] = LAYOUT(
        {base}
    ),
    [1] = LAYOUT(
        {fn}
    )
}};

'''
    open(os.path.join(OUT, 'keymaps', 'default', 'keymap.c'), 'w').write(c + ENCODER_KEYMAP_C + OLED_C)
    rm = os.path.join(OUT, 'keymaps', 'default', 'rules.mk')
    if os.path.exists(rm):
        os.remove(rm)
    for stale in ('nrsk.h', 'nrsk.c', 'rules.mk'):   # AS5600 reader of the earlier thumbwheel; nothing left per keyboard
        if os.path.exists(os.path.join(OUT, stale)):
            os.remove(os.path.join(OUT, stale))
    open(os.path.join(OUT, 'config.h'), 'w').write(KB_CONFIG % (I2C_SDA, I2C_SCL, I2C_SDA, I2C_SCL))
    open(os.path.join(OUT, 'halconf.h'), 'w').write(HALCONF)
    open(os.path.join(OUT, 'mcuconf.h'), 'w').write(MCUCONF)
    open(os.path.join(OUT, 'readme.md'), 'w').write(
        '# nrsk\n\nSplit keyboard, RP2040 on each half (UF2 bootloader: double-tap reset), TRRS PIO serial.\n\n'
        'Copy this folder to `qmk_firmware/keyboards/nrsk` and build:\n\n'
        '    qmk compile -kb nrsk -km default\n    qmk flash -kb nrsk -km default\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
