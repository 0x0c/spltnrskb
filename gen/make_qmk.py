"""Generate QMK keyboard definition and default keymap under firmware/qmk/keyboards/nrsk."""
import json
import os

from layout import HERE, ROW_PINS, COL_PINS, SERIAL_PIN, HAND_PIN, WHEEL_I2C_ADDR, N_ROWS, load

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


DIAL_KEYMAP_C = r'''
// Corner thumbwheels (index 0 = left half, 1 = right half). Return value is ignored.
bool dial_update_user(uint8_t index, bool clockwise) {
    bool fn = get_highest_layer(layer_state) == 1;
    if (index == 0) {
        tap_code(fn ? (clockwise ? KC_BRIU : KC_BRID) : (clockwise ? KC_VOLU : KC_VOLD));
    } else {
        tap_code(fn ? (clockwise ? KC_RGHT : KC_LEFT) : (clockwise ? KC_PGDN : KC_PGUP));
    }
    return true;
}
'''

KB_H = r'''#pragma once
#include "quantum.h"

// Called once per detent of a corner thumbwheel (index 0 = left half, 1 = right half);
// clockwise = turned clockwise seen from above.
bool dial_update_user(uint8_t index, bool clockwise);
'''

KB_CONFIG = r'''#pragma once

// Corner thumbwheel: AS5600 magnetic angle sensor (I2C, shared with the OLED)
#define DIAL_I2C_ADDR (0x%02X << 1)
#define DIAL_STEP 128                 // 4096 counts per turn / 128 = 32 detents per turn
#define DIAL_POLL_MS 5
#define SPLIT_TRANSACTION_IDS_KB RPC_ID_DIAL
'''

KB_C = r'''// SPDX-License-Identifier: GPL-2.0-or-later
// nrsk: corner thumbwheels read through AS5600 magnetic angle sensors.
// The half with USB (master) handles its own wheel and fetches the other half's steps over the split link.
#include "nrsk.h"
#include "i2c_master.h"
#include "transactions.h"

#define AS5600_REG_ANGLE 0x0E

static int16_t dial_last = -1;
static int16_t dial_acc = 0;
static int8_t dial_pending = 0;           // slave: steps not yet sent to the master

static int16_t dial_read(void) {
    uint8_t buf[2];
    if (i2c_read_register(DIAL_I2C_ADDR, AS5600_REG_ANGLE, buf, 2, 5) != I2C_STATUS_SUCCESS) {
        return -1;
    }
    return ((int16_t)(buf[0] & 0x0F) << 8) | buf[1];
}

// Detents since the last call, positive = clockwise seen from above.
// The sensor faces down toward the magnet, so its own clockwise is our counter-clockwise.
static int8_t dial_poll(void) {
    int16_t a = dial_read();
    if (a < 0) return 0;
    if (dial_last < 0) {
        dial_last = a;
        return 0;
    }
    int16_t d = a - dial_last;
    if (d > 2048) d -= 4096;
    if (d < -2048) d += 4096;
    dial_last = a;
    dial_acc -= d;
    int8_t steps = dial_acc / DIAL_STEP;
    dial_acc -= steps * DIAL_STEP;
    return steps;
}

__attribute__((weak)) bool dial_update_user(uint8_t index, bool clockwise) {
    return true;
}

static void dial_emit(uint8_t index, int8_t steps) {
    for (; steps > 0; steps--) dial_update_user(index, true);
    for (; steps < 0; steps++) dial_update_user(index, false);
}

static void dial_slave_handler(uint8_t in_len, const void *in, uint8_t out_len, void *out) {
    *(int8_t *)out = dial_pending;
    dial_pending = 0;
}

void keyboard_post_init_kb(void) {
    i2c_init();
    transaction_register_rpc(RPC_ID_DIAL, dial_slave_handler);
    keyboard_post_init_user();
}

void housekeeping_task_kb(void) {
    static uint16_t last = 0;
    if (timer_elapsed(last) >= DIAL_POLL_MS) {
        last = timer_read();
        int8_t local = dial_poll();
        uint8_t self = is_keyboard_left() ? 0 : 1;
        if (is_keyboard_master()) {
            dial_emit(self, local);
            int8_t remote = 0;
            if (transaction_rpc_recv(RPC_ID_DIAL, 0, NULL, sizeof(remote), &remote)) {
                dial_emit(1 - self, remote);
            }
        } else {
            int16_t p = dial_pending + local;
            dial_pending = p > 100 ? 100 : (p < -100 ? -100 : p);
        }
    }
    housekeeping_task_user();
}
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
    kb = {
        'manufacturer': 'nrsk',
        'keyboard_name': 'nrsk',
        'maintainer': 'nrsk',
        'url': '',
        'processor': 'atmega32u4',
        'bootloader': 'atmel-dfu',
        'usb': {'vid': '0xFEED', 'pid': '0x4E52', 'device_version': '1.0.0'},
        'features': {'bootmagic': True, 'extrakey': True, 'mousekey': False, 'nkro': True, 'oled': True, 'wpm': True},
        'diode_direction': 'COL2ROW',
        'matrix_pins': {'rows': ROW_PINS, 'cols': COL_PINS},
        'split': {
            'enabled': True,
            'serial': {'driver': 'bitbang', 'pin': SERIAL_PIN},
            'handedness': {'pin': HAND_PIN},
            'transport': {'sync': {'layer_state': True, 'led_state': True, 'wpm': True}},
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
    open(os.path.join(OUT, 'keymaps', 'default', 'keymap.c'), 'w').write(c + DIAL_KEYMAP_C + OLED_C)
    rm = os.path.join(OUT, 'keymaps', 'default', 'rules.mk')
    if os.path.exists(rm):
        os.remove(rm)
    open(os.path.join(OUT, 'nrsk.h'), 'w').write(KB_H)
    open(os.path.join(OUT, 'nrsk.c'), 'w').write(KB_C)
    open(os.path.join(OUT, 'config.h'), 'w').write(KB_CONFIG % WHEEL_I2C_ADDR)
    open(os.path.join(OUT, 'rules.mk'), 'w').write('I2C_DRIVER_REQUIRED = yes\n')
    open(os.path.join(OUT, 'readme.md'), 'w').write(
        '# nrsk\n\nSplit keyboard, ATmega32U4 on each half (Atmel DFU bootloader), TRRS soft serial.\n\n'
        'Copy this folder to `qmk_firmware/keyboards/nrsk` and build:\n\n'
        '    qmk compile -kb nrsk -km default\n    qmk flash -kb nrsk -km default\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
