#!/bin/bash
# High-quality renders: current design (hero, detail, oled) + OLED study + numbered grid.
set -e
cd "$(dirname "$0")/.."
export RES=${RES:-2400} SAMPLES=${SAMPLES:-160}
blender -b -P gen/render_blender.py -- --samples "$SAMPLES" --res "$RES" > /dev/null 2>&1
echo "rendered current design"
./gen/oled_study.sh
.venv/bin/python gen/render_grid.py
