#pragma once

// RP2040: tap reset twice quickly to enter the USB bootloader (RPI-RP2 drive)
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 500U

// I2C1 on GP2 (SDA) / GP3 (SCL): OLED and AS5600
#define I2C_DRIVER I2CD1
#define I2C1_SDA_PIN GP2
#define I2C1_SCL_PIN GP3

// Corner thumbwheel: AS5600 magnetic angle sensor (I2C, shared with the OLED)
#define DIAL_I2C_ADDR (0x36 << 1)
#define DIAL_STEP 128                 // 4096 counts per turn / 32 clicks of the wheel's detent
#define DIAL_HYST 12                  // counts past the half-way crest before a step counts
#define DIAL_POLL_MS 5
#define SPLIT_TRANSACTION_IDS_KB RPC_ID_DIAL
