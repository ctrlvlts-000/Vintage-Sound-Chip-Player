"""Starts Rev B from the Rev A layout: same parts in the same places, new design rules, no tracks.

Run: python3 revb.py ../ym2612_player/ym2612_player.kicad_pcb
Then route.py, gndvia.py, miter.py, stitch.py and silk.py, in that order (see README).
Rules leave margin over PCBWay's standard process (6/6 mil tracks, 0.15 mm via ring, 0.15 mm silkscreen stroke).
"""
import json
import os
import sys

import pcbnew

PCB = sys.argv[1]
PRO = os.path.splitext(PCB)[0] + ".kicad_pro"

pro = json.load(open(PRO))
nc = pro["net_settings"]["classes"][0]
nc.update(clearance=0.25, track_width=0.25, via_diameter=0.7, via_drill=0.3)
# The headphone amp (U8) is a 3 x 3 mm QFN with 0.5 mm pin pitch: its nets keep 0.2 mm, still over PCBWay's 0.15 mm.
HP_NETS = ["+4V5A", "HPVDD", "HPVSS", "HP_CPN", "HP_CPP", "HP_EN", "HP_L_IN", "HP_R_IN", "PHONE_L", "PHONE_R"]
fine = dict(nc, name="HP_amp", clearance=0.2, track_width=0.2)
pro["net_settings"]["classes"] = [nc, fine]
pro["net_settings"]["netclass_patterns"] = [{"netclass": "HP_amp", "pattern": n} for n in HP_NETS]
pro["board"]["design_settings"]["rules"].update(
    min_clearance=0.2, min_track_width=0.2, min_via_diameter=0.7, min_via_annular_width=0.2, min_through_hole_diameter=0.3,
    min_copper_edge_clearance=0.5, min_text_height=1.0, min_text_thickness=0.15, min_silk_clearance=0.1)
json.dump(pro, open(PRO, "w"), indent=2)

b = pcbnew.LoadBoard(PCB)
for t in list(b.GetTracks()):
    b.Remove(t)
pcbnew.SaveBoard(PCB, b)
text = open(PCB).read()  # the board label (BOARD.Drawings() isn't iterable from KiCad 7's Python)
open(PCB, "w").write(text.replace('"YM2612 Rev A"', '"YM2612 Rev B"'))
print("Rev B start: rules set, tracks cleared")
