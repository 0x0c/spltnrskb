// SPDX-License-Identifier: GPL-2.0-or-later
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
    // the wheel rests in a detent (dial_acc ~ 0); count a step once it passes the crest half-way to the next
    // one, with a little hysteresis so a wheel balanced on the crest does not chatter
    int8_t steps = 0;
    while (dial_acc >= DIAL_STEP / 2 + DIAL_HYST) { steps++; dial_acc -= DIAL_STEP; }
    while (dial_acc <= -(DIAL_STEP / 2 + DIAL_HYST)) { steps--; dial_acc += DIAL_STEP; }
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
            if (transaction_rpc_recv(RPC_ID_DIAL, sizeof(remote), &remote)) {
                dial_emit(1 - self, remote);
            }
        } else {
            int16_t p = dial_pending + local;
            dial_pending = p > 100 ? 100 : (p < -100 ? -100 : p);
        }
    }
    housekeeping_task_user();
}
