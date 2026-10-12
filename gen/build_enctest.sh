#!/bin/bash
# Encoder test board (enctest/): schematic, board, autoroute, ERC/DRC, fabrication files, case parts.
# Reads right/case_data.json, so run ./build.sh right first when the right half has changed.
set -e
cd "$(dirname "$0")/.."
KICAD="$HOME/Applications/KiCad/KiCad.app/Contents"
[ -d "$KICAD" ] || KICAD=/Applications/KiCad/KiCad.app/Contents
KPY="$KICAD/Frameworks/Python.framework/Versions/Current/bin/python3"
KC="$KICAD/MacOS/kicad-cli"
export NRSK_WORK="${NRSK_WORK:-$(mktemp -d)}"
S=enctest
PCB="$S/nrsk-$S.kicad_pcb"

python3 gen/make_enctest.py sch
for i in $(seq 1 10); do
  "$KPY" gen/make_enctest.py pcb > "$NRSK_WORK/make_pcb.log" 2>&1 || { tail -5 "$NRSK_WORK/make_pcb.log"; exit 1; }
  if ! "$KPY" gen/route.py "$S" > "$NRSK_WORK/route.log" 2>&1; then
    echo "routing try $i failed"; continue
  fi
  r=$("$KC" pcb drc --schematic-parity --severity-all -o "$NRSK_WORK/u.rpt" "$PCB" 2>/dev/null)
  u=$(echo "$r" | grep -oE "Found [0-9]+ unconnected" | grep -oE "[0-9]+" || echo "?")
  v=$(echo "$r" | grep -oE "Found [0-9]+ violations" | grep -oE "[0-9]+" || echo "?")
  echo "routing try $i -> $u unconnected, $v violations"
  [ "$u" = "0" ] && [ "$v" = "0" ] && break
done
"$KC" sch erc --severity-all -o "$S/erc.rpt" "$S/nrsk-$S.kicad_sch" 2>/dev/null | grep -i found || true
"$KC" pcb drc --schematic-parity --severity-all -o "$S/drc.rpt" "$PCB" 2>/dev/null | grep -i found || true

out="fab/$S"; rm -rf "${out:?}"; mkdir -p "$out/gerber"
"$KC" pcb export gerbers -l F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts -o "$out/gerber/" "$PCB" >/dev/null 2>&1
"$KC" pcb export drill --format excellon --excellon-separate-th -o "$out/gerber/" "$PCB" >/dev/null 2>&1
(cd "$out/gerber" && zip -q -r "../nrsk-$S-gerber.zip" .)
"$KC" sch export bom --fields 'Reference,Value,Footprint,${QUANTITY}' --labels 'Refs,Value,Footprint,Qty' \
  --group-by 'Value,Footprint' --ref-range-delimiter '' -o "$out/nrsk-$S-bom.csv" "$S/nrsk-$S.kicad_sch" >/dev/null 2>&1
"$KC" sch export pdf -o "$out/nrsk-$S-schematic.pdf" "$S/nrsk-$S.kicad_sch" >/dev/null 2>&1
"$KC" pcb export pdf --mode-single -l F.Fab,F.SilkS,F.Cu,Edge.Cuts -o "$out/nrsk-$S-assembly-front.pdf" "$PCB" >/dev/null 2>&1
"$KC" pcb export pdf --mode-single -l B.Fab,B.SilkS,B.Cu,Edge.Cuts --mirror -o "$out/nrsk-$S-assembly-back.pdf" "$PCB" >/dev/null 2>&1

[ -x .venv/bin/python ] && .venv/bin/python gen/make_enctest.py case
