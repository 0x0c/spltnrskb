#!/usr/bin/env bash
# Third-party 3D models used by the footprints (kept in tools/, not committed):
#   kiswitch (CC-BY-SA 4.0 with a design exception)  MX switch, Kailh hotswap socket, 2u stabilizer
#   LCSC / EasyEDA via easyeda2kicad                  USB-C TYPE-C-31-M-12 (C165948), PJ-320D (C431535)
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d tools/kiswitch ] || git clone -q --depth 1 https://github.com/kiswitch/kiswitch tools/kiswitch
if [ ! -f tools/easyeda/nrsk_lcsc.3dshapes/AUDIO-SMD_PJ-320D-1.wrl ]; then
  .venv/bin/pip install -q easyeda2kicad
  for id in C165948 C431535; do
    .venv/bin/easyeda2kicad --3d --lcsc_id "$id" --output tools/easyeda/nrsk_lcsc --overwrite > /dev/null
  done
fi
echo "3D models ready"
