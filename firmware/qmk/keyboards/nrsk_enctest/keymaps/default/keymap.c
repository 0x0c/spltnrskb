// SPDX-License-Identifier: GPL-2.0-or-later
// nrsk encoder test board with a Waveshare RP2040-Zero: the same encoder settings and assignments as the keyboard's
// right half (only the pins differ), so the test shows what the keyboard will do.
#include QMK_KEYBOARD_H

// The tact switch above the drum holds layer 1, to try the layer-1 assignments of both encoders. Holding it while
// plugging in USB enters the bootloader (bootmagic): the module's own BOOT button faces the floor once fitted.
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [0] = LAYOUT(MO(1)),
    [1] = LAYOUT(KC_TRNS)
};

// Encoders, one click = one call (clockwise seen from above / rolled away from the typist):
//   0 = thumbwheel (keyboard: index 1, right thumbwheel), 1 = drum dial (keyboard: index 2).
bool encoder_update_user(uint8_t index, bool clockwise) {
    bool fn = get_highest_layer(layer_state) == 1;
    if (index == 0) {
        tap_code(fn ? (clockwise ? KC_RGHT : KC_LEFT) : (clockwise ? KC_PGDN : KC_PGUP));
    } else {
        // drum: roll away = scroll up (layer 1: right), like a mouse wheel
        tap_code(fn ? (clockwise ? MS_WHLR : MS_WHLL) : (clockwise ? MS_WHLU : MS_WHLD));
    }
    return false;
}
