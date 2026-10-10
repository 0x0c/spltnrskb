#!/bin/bash
# Thumbwheel encoder study: geometry, section / exploded renders, exterior close-ups with the study wheel, sheet.
set -e
cd "$(dirname "$0")/.."
.venv/bin/python gen/encoder_study.py
blender -b -P gen/render_encoder_study.py -- --samples ${SAMPLES:-96} --res ${RES:-1600} > /dev/null 2>&1
blender -b -P gen/render_blender.py -- --samples ${SAMPLES:-96} --res ${RES:-1600} --shots wheel-left,wheel-right \
  --wheel-stl 'case/preview/encoder-study/{side}-encoder-wheel.stl' --suffix -encoder > /dev/null 2>&1
for s in left right; do mv "docs/img/render-wheel-$s-encoder.png" "docs/img/encoder-study/exterior-$s.png"; done
.venv/bin/python gen/encoder_sheet.py
