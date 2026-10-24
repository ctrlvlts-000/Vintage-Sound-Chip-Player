#!/bin/sh
# Regenerates the draft schematic, checks its netlist, and exports the PDF. Needs KiCad 7+ (kicad-cli, pcbnew python).
set -e
cd "$(dirname "$0")"
OUT=../ym2612_player
python3 make_symbols.py $OUT/ym2612.kicad_sym
python3 make_footprints.py $OUT/ym2612.pretty 2>/dev/null
python3 design.py $OUT
kicad-cli sch export netlist --format kicadxml -o /tmp/ym2612_player.xml $OUT/ym2612_player.kicad_sch >/dev/null
python3 verify.py /tmp/ym2612_player.xml
kicad-cli sch export pdf -o $OUT/ym2612_player.pdf $OUT/ym2612_player.kicad_sch >/dev/null
python3 bom.py
