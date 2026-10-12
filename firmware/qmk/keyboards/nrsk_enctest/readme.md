# nrsk encoder test

Test board for the nrsk keyboard's two encoders (corner thumbwheel and drum dial), with a Waveshare RP2040-Zero
under the board on ConThrough stacking pins. Board and case: `enctest/`, `gen/make_enctest.py`; assembly and
checks: `docs/encoder-test-board.md`.

    firmware/qmk/compile.sh default nrsk_enctest

Flashing: the first time, before fitting the module, hold its BOOT button while plugging it in and copy the .uf2
to the RPI-RP2 drive. Once fitted, hold the board's tact switch while plugging in (bootmagic).
