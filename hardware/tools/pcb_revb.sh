#!/bin/sh
# Rebuilds the Rev B layout from the Rev A placement, in the order it was made. Needs KiCad 7+ (pcbnew Python),
# Java and Freerouting: sh pcb_revb.sh /path/to/freerouting.jar
# Freerouting is not fully repeatable, so a rerun can need different patch_route.py pairs. Check DRC afterwards.
set -e
cd "$(dirname "$0")"
PCB=../ym2612_player/ym2612_player.kicad_pcb
python3 revb.py $PCB                         # rules, tracks cleared, "Rev B" on the silkscreen
python3 route.py $PCB "$1"                   # every net but GND, 45 degree routing
python3 route.py $PCB "$1"                   # second pass picks up what the first left open
python3 patch_route.py $PCB U8.14:C30.1 R36.2:U7.7   # the two connections Freerouting couldn't finish
python3 gndvia.py $PCB                       # GND pads the planes miss: exposed pad, via or solid connection
python3 stitch.py $PCB                       # 8 mm grid of vias tying the two planes together
python3 gndvia.py $PCB                       # any plane island the stitching didn't reach
python3 patch_route.py $PCB C36.2:U7.4 C1.2:C2.2      # two islands with no room for a via of their own
python3 miter.py $PCB                        # 90 degree corners become two 45 degree bends
python3 silk.py $PCB                         # outlines off pads, labels 1.0 mm in clear spots
sh fab.sh
