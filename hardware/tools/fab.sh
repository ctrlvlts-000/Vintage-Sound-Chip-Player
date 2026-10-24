#!/bin/sh
# Makes the files PCBWay asks for: Gerbers + drill (zipped), BOM, and the placement (CPL) file. Needs KiCad 7+.
set -e
cd "$(dirname "$0")"
PCB=../ym2612_player/ym2612_player.kicad_pcb
OUT=../ym2612_player/fab
mkdir -p $OUT/gerbers
kicad-cli pcb export gerbers -o $OUT/gerbers/ --no-x2 \
  -l F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts $PCB >/dev/null
kicad-cli pcb export drill -o $OUT/gerbers/ --format excellon --excellon-separate-th $PCB >/dev/null
(cd $OUT/gerbers && rm -f ../ym2612_player_gerbers.zip && zip -q ../ym2612_player_gerbers.zip *)
kicad-cli pcb export pos -o /tmp/ym2612_pos.csv --format csv --units mm --side both $PCB >/dev/null
python3 cpl.py /tmp/ym2612_pos.csv $OUT/ym2612_player_cpl.csv
cp ../ym2612_player/bom.csv $OUT/ym2612_player_bom.csv
ls $OUT
