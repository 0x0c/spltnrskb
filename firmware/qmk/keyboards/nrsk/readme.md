# nrsk

Split keyboard, ATmega32U4 on each half (Atmel DFU bootloader), TRRS soft serial.

Copy this folder to `qmk_firmware/keyboards/nrsk` and build:

    qmk compile -kb nrsk -km default
    qmk flash -kb nrsk -km default
