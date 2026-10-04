#pragma once

// Corner thumbwheel: AS5600 magnetic angle sensor (I2C, shared with the OLED)
#define DIAL_I2C_ADDR (0x36 << 1)
#define DIAL_STEP 128                 // 4096 counts per turn / 128 = 32 detents per turn
#define DIAL_POLL_MS 5
#define SPLIT_TRANSACTION_IDS_KB RPC_ID_DIAL
