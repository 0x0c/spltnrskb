#!/bin/bash
# Tilt-leg study (docs/specs/case-feet-tilt.md): models, renders of the three mechanisms, comparison sheet and table.
set -e
cd "$(dirname "$0")/.."
.venv/bin/python gen/tilt_variants.py
for m in M F S; do
  blender -b -P gen/render_tilt.py -- --mech "$m" --samples ${SAMPLES:-64} --res ${RES:-1000} > /dev/null 2>&1
  echo "rendered $m"
done
.venv/bin/python gen/tilt_sheet.py
