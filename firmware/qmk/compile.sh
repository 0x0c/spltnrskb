#!/bin/bash
# Copy the keyboard definition into qmk_firmware and run `qmk compile`.
# Usage: firmware/qmk/compile.sh [keymap] [keyboard]   (defaults: default, nrsk; nrsk_enctest = the encoder test board)
# The .uf2 is copied to firmware/qmk/build/.
set -e
cd "$(dirname "$0")"
KM="${1:-default}"
KB="${2:-nrsk}"

# qmk CLI: PATH, else the repo's .venv
command -v qmk >/dev/null || PATH="$(cd ../.. && pwd)/.venv/bin:$PATH"
command -v qmk >/dev/null || { echo "qmk not found (brew install qmk/qmk/qmk)" >&2; exit 1; }
QMK_HOME="${QMK_HOME:-$(qmk env | sed -n 's/^QMK_HOME="\(.*\)"$/\1/p')}"
[ -d "$QMK_HOME/keyboards" ] || { echo "qmk_firmware not found at '$QMK_HOME' (run qmk setup)" >&2; exit 1; }

# ARM toolchain with newlib: $ARM_TOOLCHAIN, else the newest Arm GNU Toolchain in
# ~/.local/opt or /Applications (Homebrew's arm-none-eabi-gcc has no libc).
if [ -z "$ARM_TOOLCHAIN" ]; then
    for d in "$HOME"/.local/opt/arm-gnu-toolchain-*-arm-none-eabi /Applications/ArmGNUToolchain/*/arm-none-eabi; do
        [ -x "$d/bin/arm-none-eabi-gcc" ] && ARM_TOOLCHAIN="$d"
    done
fi
[ -n "$ARM_TOOLCHAIN" ] && PATH="$ARM_TOOLCHAIN/bin:$PATH"
if [ "$(arm-none-eabi-gcc -print-file-name=libc.a)" = libc.a ]; then
    echo "$(command -v arm-none-eabi-gcc) has no newlib; install the Arm GNU Toolchain (see README)" >&2
    exit 1
fi

rsync -a --delete "keyboards/$KB/" "$QMK_HOME/keyboards/$KB/"
qmk compile -kb "$KB" -km "$KM"
mkdir -p build
cp "$QMK_HOME/${KB}_$KM.uf2" build/
echo "-> firmware/qmk/build/${KB}_$KM.uf2"
