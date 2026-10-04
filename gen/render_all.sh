#!/bin/bash
# Renders of the current design (hero, detail, oled, corner wheels) + OLED study + numbered grid.
# Default is a quick preview (1200 px, 32 samples); FINAL=1 renders the high-resolution set (2400 px, 160 samples).
set -e
cd "$(dirname "$0")/.."
if [ -n "$FINAL" ]; then
  export RES=${RES:-2400} SAMPLES=${SAMPLES:-160}
else
  export RES=${RES:-1200} SAMPLES=${SAMPLES:-32}
fi
blender -b -P gen/render_blender.py -- --samples "$SAMPLES" --res "$RES" --shots hero,detail,oled,wheel-left,wheel-right > /dev/null 2>&1
echo "rendered current design ($RES px, $SAMPLES samples)"
./gen/oled_study.sh
.venv/bin/python gen/render_grid.py
