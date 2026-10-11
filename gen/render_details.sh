#!/bin/bash
# Close-ups for the design review page, for both case variants (A = clear acrylic plate + low-head screws, B = all printed):
# docs/img/details/<shot>-<a|b>.jpg, then gen/views_page.py rewrites docs/views.html.
# The whole board, OLED and left wheel come from gen/render_compare.sh (docs/img/render-*-top-*.png).
# A shot written <name>:nocable is rendered without the cables (and their plugs) as <name>-nocable-<a|b>.jpg.
# One Blender run per shot; shots already rendered are skipped, FORCE=1 redoes them. RES, SAMPLES and SHOTS override.
set -e
cd "$(dirname "$0")/.."
RES=${RES:-1800} SAMPLES=${SAMPLES:-128}
SHOTS=${SHOTS:-"user keys corner profile wheel-right detail ports back hero:nocable back:nocable ports:nocable"}
OUT=docs/img/details
mkdir -p "$OUT"
for variant in a b; do
  if [ "$variant" = a ]; then case_args="--top acrylic --screws lowpan"; else case_args="--top print"; fi
  for entry in $SHOTS; do
    shot=${entry%%:*} name=$shot extra=""
    if [ "$entry" != "$shot" ]; then name="$shot-nocable" extra="--no-cables"; fi
    f="$OUT/$name-$variant"
    [ -z "$FORCE" ] && [ -f "$f.jpg" ] && continue
    # shellcheck disable=SC2086
    blender -b -P gen/render_blender.py -- --samples "$SAMPLES" --res "$RES" --shots "$shot" --views-dir "$OUT" \
      $case_args $extra --suffix "${name#"$shot"}-$variant" > /dev/null 2>&1 || { echo "failed: $name-$variant"; continue; }
    sips -s format jpeg -s formatOptions 85 "$f.png" --out "$f.jpg" > /dev/null && rm "$f.png"
    echo "rendered $name-$variant"
  done
done
python3 gen/views_page.py
