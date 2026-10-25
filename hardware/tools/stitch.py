"""Adds ground stitching vias that tie the top and bottom ground planes together, then refills the planes.

Run after routing: python3 stitch.py ../ym2612_player/ym2612_player.kicad_pcb
A via goes on an 8 mm grid wherever it clears every pad, track and other via, and stays only if both planes reach it.
"""
import math
import sys

import pcbnew

P = sys.argv[1]
STEP, VIA, DRILL, GAP = 8.0, 0.6, 0.3, 0.35          # mm
b = pcbnew.LoadBoard(P)
mm, to_mm = pcbnew.FromMM, pcbnew.ToMM
gnd = b.FindNet("GND")
edge = b.GetBoardEdgesBoundingBox()
x0, y0, x1, y1 = to_mm(edge.GetLeft()), to_mm(edge.GetTop()), to_mm(edge.GetRight()), to_mm(edge.GetBottom())

pads = []
for fp in b.GetFootprints():
    for pad in fp.Pads():
        bb = pad.GetBoundingBox()
        pads.append((to_mm(bb.GetLeft()), to_mm(bb.GetTop()), to_mm(bb.GetRight()), to_mm(bb.GetBottom())))
segs, vias = [], []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        vias.append((to_mm(t.GetPosition().x), to_mm(t.GetPosition().y), to_mm(t.GetWidth()) / 2))
    else:
        segs.append((to_mm(t.GetStart().x), to_mm(t.GetStart().y), to_mm(t.GetEnd().x), to_mm(t.GetEnd().y),
                     to_mm(t.GetWidth()) / 2))


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def clear(x, y):
    r = VIA / 2 + GAP
    if x - x0 < 2 or x1 - x < 2 or y - y0 < 2 or y1 - y < 2:
        return False
    if any(l - r < x < rr + r and t - r < y < bt + r for l, t, rr, bt in pads):
        return False
    if any(seg_dist(x, y, ax, ay, bx, by) < w + r for ax, ay, bx, by, w in segs):
        return False
    return all(math.hypot(x - vx, y - vy) > vr + r for vx, vy, vr in vias)


added = []
y = y0 + STEP / 2
while y < y1:
    x = x0 + STEP / 2
    while x < x1:
        if clear(x, y):
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            v.SetWidth(mm(VIA))
            v.SetDrill(mm(DRILL))
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(gnd)
            b.Add(v)
            added.append(v)
        x += STEP
    y += STEP

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
# Keep only vias that land in copper on both planes.
zones = [z for z in b.Zones() if z.GetNetname() == "GND"]
kept = 0
for v in added:
    layers = {z.GetLayer() for z in zones if z.HitTestFilledArea(z.GetLayer(), v.GetPosition())}
    if {pcbnew.F_Cu, pcbnew.B_Cu} <= layers:
        kept += 1
    else:
        b.Remove(v)
filler.Fill(b.Zones())
pcbnew.SaveBoard(P, b)
print("stitching vias:", kept)
