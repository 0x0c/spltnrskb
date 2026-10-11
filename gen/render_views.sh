#!/bin/bash
# Design-review orbit: both case variants (A = clear acrylic plate + low-head screws, B = all printed) from all around,
# rendered to docs/img/views/view-a<azimuth>-e<elevation>-<a|b>.jpg, then gen/views_page.py writes docs/views.html.
# One Blender run per view (a long batch in one process crashes); views already rendered are skipped, FORCE=1 redoes them.
# Default 1600 px / 64 samples; RES and SAMPLES override.
set -e
cd "$(dirname "$0")/.."
RES=${RES:-1600} SAMPLES=${SAMPLES:-64}
OUT=docs/img/views
VIEWS="view-a0-e90"
for az in 0 45 90 135 180 225 270 315; do VIEWS="$VIEWS view-a$az-e30"; done
for az in 0 180; do VIEWS="$VIEWS view-a$az-e60"; done
for az in 0 90 180 270; do VIEWS="$VIEWS view-a$az-e10"; done
mkdir -p "$OUT"
for variant in a b; do
  if [ "$variant" = a ]; then case_args="--top acrylic --screws lowpan"; else case_args="--top print"; fi
  for v in $VIEWS; do
    f="$OUT/$v-$variant"
    [ -z "$FORCE" ] && [ -f "$f.jpg" ] && continue
    if [ -z "$FORCE" ] && [ -f "$f.png" ]; then :; else
      # shellcheck disable=SC2086
      blender -b -P gen/render_blender.py -- --samples "$SAMPLES" --res "$RES" --shots "$v" --views-dir "$OUT" \
        $case_args --suffix "-$variant" > /dev/null 2>&1 || { echo "failed: $v-$variant"; continue; }
    fi
    sips -s format jpeg -s formatOptions 85 "$f.png" --out "$f.jpg" > /dev/null && rm "$f.png"
    echo "rendered $v-$variant"
  done
done
echo "$(ls "$OUT"/*.jpg | wc -l | tr -d ' ') views in $OUT ($RES px, $SAMPLES samples)"
python3 gen/views_page.py
