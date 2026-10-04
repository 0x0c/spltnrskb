#!/bin/bash
# README images: KiCad 3D renders of both boards, case/PCB overlays and the assembled section.
set -e
cd "$(dirname "$0")/.."
KICAD="$HOME/Applications/KiCad/KiCad.app/Contents"
[ -d "$KICAD" ] || KICAD=/Applications/KiCad/KiCad.app/Contents
KC="$KICAD/MacOS/kicad-cli"
for s in left right; do
  "$KC" pcb render --side top --quality basic -w 1800 -h 1100 -o "docs/img/$s-top.png" "$s/nrsk-$s.kicad_pcb" >/dev/null 2>&1
  "$KC" pcb render --side bottom --quality basic -w 1800 -h 1100 -o "docs/img/$s-bottom.png" "$s/nrsk-$s.kicad_pcb" >/dev/null 2>&1
done
VENV=.venv/bin/python
if [ -x "$VENV" ]; then
  "$VENV" gen/case_preview.py
  "$VENV" gen/case_section.py
  "$VENV" - <<'PY'
import os
from PIL import Image
import io, subprocess
# SVG overlays -> PNG via macOS Quick Look (no extra dependencies)
for s in ('left', 'right'):
    svg = f'case/preview/{s}-overlay.svg'
    subprocess.run(['qlmanage', '-t', '-s', '1800', '-o', 'docs/img', svg], capture_output=True)
    src = f'docs/img/{s}-overlay.svg.png'
    if os.path.exists(src):
        os.replace(src, f'docs/img/{s}-case-overlay.png')
PY
  cp case/preview/case-section.png docs/img/case-section.png
fi
echo "doc images updated"
