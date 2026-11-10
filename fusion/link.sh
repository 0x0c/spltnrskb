#!/bin/bash
# Link every script folder under fusion/ (fusion/Nrsk*) into Fusion's Scripts folder, so the scripts show up in
# Utilities > Add-Ins > Scripts and Add-Ins. The scripts resolve the link to find the repository.
set -e
cd "$(dirname "$0")"
DEST="$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts"
[ -d "$DEST" ] || { echo "no Fusion Scripts folder: $DEST (start Fusion once first)"; exit 1; }
for d in Nrsk*/; do
  d="${d%/}"
  ln -sfn "$PWD/$d" "$DEST/$d"
  echo "linked $d"
done
