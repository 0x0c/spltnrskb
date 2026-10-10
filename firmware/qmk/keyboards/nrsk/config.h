#pragma once

// RP2040: tap reset twice quickly to enter the USB bootloader (RPI-RP2 drive)
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 500U

// I2C1 on GP2 (SDA) / GP3 (SCL): OLED
#define I2C_DRIVER I2CD1
#define I2C1_SDA_PIN GP2
#define I2C1_SCL_PIN GP3
