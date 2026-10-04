#!/bin/bash
# Render the OLED height/tilt study (same typist-eye camera for every variant) and a comparison sheet.
set -e
cd "$(dirname "$0")/.."
.venv/bin/python gen/oled_variants.py
for v in 0 3.5 6.5 13 tilt-v tilt-h; do
  blender -b -P gen/render_blender.py -- --samples ${SAMPLES:-96} --res ${RES:-1200} --shots user,oled \
    --oled-height "$v" --suffix "-$v" > /dev/null 2>&1
  mv "docs/img/render-user-$v.png" "docs/img/oled-study/user-$v.png"
  mv "docs/img/render-oled-$v.png" "docs/img/oled-study/close-$v.png"
  echo "rendered $v"
done
.venv/bin/python gen/oled_sheet.py
