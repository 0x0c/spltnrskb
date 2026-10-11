#!/bin/bash
# README comparison of case variants A (clear acrylic plate, low-head screws from the top) and B (all printed):
# whole board, OLED and left wheel for each, then gen/compare_ab.py puts them on one sheet.
# Also the USB-C / TRRS opening close-up (render-ports.png, variant A) and the board slide-in section (port-slide.png).
set -e
cd "$(dirname "$0")/.."
RES=${RES:-1800} SAMPLES=${SAMPLES:-160}
blender -b -P gen/render_blender.py -- --samples "$SAMPLES" --res "$RES" --shots hero,oled,wheel-left \
  --top acrylic --screws lowpan --suffix -top-acrylic-lowpan > /dev/null 2>&1
blender -b -P gen/render_blender.py -- --samples "$SAMPLES" --res "$RES" --shots hero,oled,wheel-left \
  --top print --suffix -top-print > /dev/null 2>&1
blender -b -P gen/render_blender.py -- --samples "$SAMPLES" --res "$RES" --shots ports \
  --top acrylic --screws lowpan > /dev/null 2>&1
echo "rendered A / B and ports ($RES px, $SAMPLES samples)"
.venv/bin/python gen/compare_ab.py
.venv/bin/python gen/port_slide.py
