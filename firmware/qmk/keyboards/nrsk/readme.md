# nrsk

Split keyboard, RP2040 on each half (UF2 bootloader: double-tap reset), TRRS PIO serial.

Copy this folder to `qmk_firmware/keyboards/nrsk` and build:

    qmk compile -kb nrsk -km default
    qmk flash -kb nrsk -km default
