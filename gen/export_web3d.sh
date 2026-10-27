#!/bin/bash
# Assets of the 3D design-review page (docs/views.html) from the same Blender scene as the renders:
#   docs/3d/<a|b>.glb                    the model, A = clear acrylic plate + low-head screws (with KiCad's assembled
#                                        boards under it), B = all printed
#   docs/3d/studio.hdr                   the studio lighting as an equirectangular HDR
#   docs/3d/shadow-<a|b>[-nocable].jpg   the floor shadow (ambient occlusion map of the floor)
# then gen/views_page.py writes docs/views.html.
#   ./gen/export_web3d.sh enctest        the encoder test kit's page instead (docs/enctest-views.html, gen/render_enctest.py):
#   docs/3d/enctest.glb, docs/3d/shadow-enctest[-noplate][-notray].jpg (lit by the studio.hdr above)
set -e
cd "$(dirname "$0")/.."
OUT=docs/3d
mkdir -p "$OUT"
if [ "$1" = enctest ]; then
  blender -b -P gen/render_enctest.py -- --web "glb:$OUT/enctest.glb" > /dev/null 2>&1 || { echo "failed: glb"; exit 1; }
  for hide in "" plate tray plate,tray; do
    suffix=$(echo "$hide" | sed -e 's/plate/-noplate/' -e 's/tray/-notray/' -e 's/,//')
    blender -b -P gen/render_enctest.py -- --samples 128 --web "shadow:$OUT/shadow-enctest$suffix.jpg" ${hide:+--hide $hide} \
      > /dev/null 2>&1 || { echo "failed: shadow $hide"; exit 1; }
  done
  ls -la "$OUT"/*enctest*
  python3 gen/views_page.py enctest
  exit 0
fi
# the boards with their parts come from KiCad (gen/export_3d.py, part of build.sh); without them a plain green slab
[ -f build/3d/left-pcba.glb ] || echo "build/3d/*-pcba.glb missing: run gen/export_3d.py (see build.sh) to show the parts"
run() { blender -b -P gen/render_blender.py -- "$@" > /dev/null 2>&1 || { echo "failed: $*"; exit 1; }; }
run --samples 512 --web "env:$OUT/studio.hdr"
for variant in a b; do
  if [ "$variant" = a ]; then case_args="--top acrylic --screws lowpan"; else case_args="--top print"; fi
  # shellcheck disable=SC2086
  run $case_args --web "glb:$OUT/$variant.glb"
  # shellcheck disable=SC2086
  run $case_args --samples 256 --web "shadow:$OUT/shadow-$variant.jpg"
  # shellcheck disable=SC2086
  run $case_args --samples 256 --no-cables --web "shadow:$OUT/shadow-$variant-nocable.jpg"
  echo "exported $variant"
done
ls -la "$OUT"
python3 gen/views_page.py keyboard
