#!/bin/bash
# Regenerate libraries, schematics, PCBs; autoroute; run ERC/DRC.
set -e
cd "$(dirname "$0")"
KICAD="$HOME/Applications/KiCad/KiCad.app/Contents"
[ -d "$KICAD" ] || KICAD=/Applications/KiCad/KiCad.app/Contents
KPY="$KICAD/Frameworks/Python.framework/Versions/Current/bin/python3"
KC="$KICAD/MacOS/kicad-cli"
export NRSK_WORK="${NRSK_WORK:-$(mktemp -d)}"
SIDES="${*:-left right}"

python3 gen/footprints.py
for s in $SIDES; do
  python3 gen/make_sch.py "$s"
  for i in $(seq 1 25); do
    "$KPY" gen/make_pcb.py "$s" >/dev/null 2>&1
    "$KPY" gen/route.py "$s" >/dev/null 2>&1
    u=$("$KC" pcb drc -o "$NRSK_WORK/u.rpt" "$s/nrsk-$s.kicad_pcb" 2>/dev/null | grep -oE "Found [0-9]+ unconnected" | grep -oE "[0-9]+")
    echo "$s: routing try $i -> $u unconnected"
    [ "$u" = "0" ] && break
  done
  "$KC" sch erc --severity-all -o "$s/erc.rpt" "$s/nrsk-$s.kicad_sch" 2>/dev/null | grep -i found || true
  "$KC" pcb drc --schematic-parity --severity-all -o "$s/drc.rpt" "$s/nrsk-$s.kicad_pcb" 2>/dev/null | grep -i found || true
done

# fabrication outputs
for s in $SIDES; do
  out="fab/$s"; rm -rf "${out:?}"; mkdir -p "$out/gerber"
  "$KC" pcb export gerbers -l F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts -o "$out/gerber/" "$s/nrsk-$s.kicad_pcb" >/dev/null 2>&1
  "$KC" pcb export drill --format excellon --excellon-separate-th -o "$out/gerber/" "$s/nrsk-$s.kicad_pcb" >/dev/null 2>&1
  (cd "$out/gerber" && zip -q -r "../nrsk-$s-gerber.zip" .)
  "$KC" sch export bom --fields 'Reference,Value,Footprint,${QUANTITY}' --labels 'Refs,Value,Footprint,Qty' \
    --group-by 'Value,Footprint' --ref-range-delimiter '' -o "$out/nrsk-$s-bom.csv" "$s/nrsk-$s.kicad_sch" >/dev/null 2>&1
  "$KC" sch export pdf -o "$out/nrsk-$s-schematic.pdf" "$s/nrsk-$s.kicad_sch" >/dev/null 2>&1
  # assembly drawing of the back side (MCU area references live on B.Fab)
  "$KC" pcb export pdf --mode-single -l B.Fab,B.SilkS,B.Cu,Edge.Cuts --mirror \
    -o "$out/nrsk-$s-assembly-back.pdf" "$s/nrsk-$s.kicad_pcb" >/dev/null 2>&1
done
python3 gen/make_qmk.py
VENV="$PWD/.venv/bin/python"
if [ -x "$VENV" ]; then "$VENV" gen/make_case.py && "$VENV" gen/case_preview.py && "$VENV" gen/case_section.py && "$VENV" gen/case_viewer.py; fi
python3 gen/make_bom.py >/dev/null
