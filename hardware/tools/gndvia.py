"""Connects every GND pad that the ground planes don't reach (or reach with a single thin spoke).

Run after route.py: python3 gndvia.py ../ym2612_player/ym2612_player.kicad_pcb
DRC lists those pads. A GND pin of a chip with a GND exposed pad gets a short track to that pad. A through-hole pad
gets a solid (no thermal relief) connection to the plane. Any other pad gets a short track to a via that drops to the
other layer's plane, at the nearest spot that keeps the Default net class clearance from every other net.
"""
import math
import os
import re
import sys
import tempfile

import pcbnew

P = sys.argv[1]
mm, to_mm = pcbnew.FromMM, pcbnew.ToMM
b = pcbnew.LoadBoard(P)
nc = b.GetDesignSettings().m_NetSettings.m_DefaultNetClass
CLR, VIA, DRILL = to_mm(nc.GetClearance()) + 0.02, to_mm(nc.GetViaDiameter()), to_mm(nc.GetViaDrill())
gnd = b.FindNet("GND")


def problem_pads():
    rpt = os.path.join(tempfile.mkdtemp(), "drc.rpt")
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    found = set()
    for block in open(rpt).read().split("\n["):
        if block.startswith(("unconnected_items", "starved_thermal")):
            found |= set(re.findall(r"[Pp]ad (\S+) \[GND\] of (\S+)", block))
    return found



def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_seg(a, c):
    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    a0, a1, c0, c1 = a[:2], a[2:], c[:2], c[2:]
    if side(a0, a1, c0) * side(a0, a1, c1) < 0 and side(c0, c1, a0) * side(c0, c1, a1) < 0:
        return 0.0  # they cross
    return min(seg_dist(*a[:2], *c), seg_dist(*a[2:], *c), seg_dist(*c[:2], *a), seg_dist(*c[2:], *a))


def obstacles(layer):
    """Other-net copper on `layer` (or on both layers for holes) as (segment, half width)."""
    out = []
    for f in b.GetFootprints():
        for pad in f.Pads():
            if pad.HasHole() and pad.GetNetname() == "GND":   # keep vias off GND holes too (hole to hole spacing)
                c = (to_mm(pad.GetPosition().x), to_mm(pad.GetPosition().y))
                out.append(((*c, *c), to_mm(pad.GetDrillSize().x) / 2 + 0.1, False))
                continue
            if pad.GetNetname() == "GND" or not (pad.IsOnLayer(layer) or pad.HasHole()):
                continue
            r = pad.GetBoundingBox()
            l, t, rr, bt = (to_mm(v) for v in (r.GetLeft(), r.GetTop(), r.GetRight(), r.GetBottom()))
            h = min(rr - l, bt - t) / 2
            cx, cy = (l + rr) / 2, (t + bt) / 2
            # A capsule over the pad's full length, wide enough to cover square corners too.
            if rr - l > bt - t:
                out.append(((l, cy, rr, cy), h * 1.415, pad.IsOnLayer(layer)))
            else:
                out.append(((cx, t, cx, bt), h * 1.415, pad.IsOnLayer(layer)))
    for t in b.GetTracks():
        if t.GetNetname() == "GND" and t.GetClass() != "PCB_VIA":
            continue
        s, e = t.GetStart(), t.GetEnd()
        on = t.GetClass() == "PCB_VIA" or t.GetLayer() == layer
        out.append(((to_mm(s.x), to_mm(s.y), to_mm(e.x), to_mm(e.y)), to_mm(t.GetWidth()) / 2,
                    on if t.GetNetname() != "GND" else False))
    return out


edge = b.GetBoardEdgesBoundingBox()
x0, y0, x1, y1 = (to_mm(v) for v in (edge.GetLeft(), edge.GetTop(), edge.GetRight(), edge.GetBottom()))
added = 0
for num, ref in sorted(problem_pads()):
    fp = b.FindFootprintByReference(ref)
    pad = fp.FindPadByNumber(num)
    if pad.HasHole():
        pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        added += 1
        continue
    area = lambda p: p.GetSize().x * p.GetSize().y
    ep = [p for p in fp.Pads() if p.GetNetname() == "GND" and area(p) > 4 * area(pad)]
    if ep:  # exposed pad: run straight in from the pin, square to the chip's edge
        e, c = ep[0].GetBoundingBox(), pad.GetPosition()
        x = c.x if e.GetLeft() < c.x < e.GetRight() else e.GetCenter().x
        y = c.y if e.GetTop() < c.y < e.GetBottom() else e.GetCenter().y
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(c)
        t.SetEnd(pcbnew.VECTOR2I(x, y))
        t.SetWidth(mm(to_mm(min(pad.GetSize().x, pad.GetSize().y))))
        t.SetLayer(pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
        t.SetNet(gnd)
        b.Add(t)
        added += 1
        continue
    layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
    obs = obstacles(layer)
    px, py = to_mm(pad.GetPosition().x), to_mm(pad.GetPosition().y)
    w = min(0.4, to_mm(min(pad.GetSize().x, pad.GetSize().y)))
    best = None
    for dist in [0.8 + 0.1 * i for i in range(25)]:
        for k in range(16):
            a = k * math.pi / 8
            vx, vy = px + dist * math.cos(a), py + dist * math.sin(a)
            if not (x0 + 1 < vx < x1 - 1 and y0 + 1 < vy < y1 - 1):
                continue
            ok = True
            for s, h, on_layer in obs:
                # the via clears everything (holes and other-layer copper too); the stub clears this layer's copper
                if seg_dist(vx, vy, *s) < h + VIA / 2 + CLR:
                    ok = False
                    break
                if on_layer and seg_seg((px, py, vx, vy), s) < h + w / 2 + CLR:
                    ok = False
                    break
            if ok:
                best = (vx, vy)
                break
        if best:
            break
    if not best:
        print("no room for a via next to", ref, num)
        continue
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(best[0]), mm(best[1])))
    v.SetWidth(mm(VIA))
    v.SetDrill(mm(DRILL))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(gnd)
    b.Add(v)
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pad.GetPosition())
    t.SetEnd(v.GetPosition())
    t.SetWidth(mm(w))
    t.SetLayer(layer)
    t.SetNet(gnd)
    b.Add(t)
    added += 1


def tie_islands():
    """A via inside every piece of GND plane that nothing ties to the other layer yet."""
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    ties = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
    ties += [p.GetPosition() for f in b.GetFootprints() for p in f.Pads() if p.HasHole() and p.GetNetname() == "GND"]
    zones = {z.GetLayer(): z for z in b.Zones() if z.GetNetname() == "GND"}
    n = 0
    for layer, z in zones.items():
        other = zones[pcbnew.B_Cu if layer == pcbnew.F_Cu else pcbnew.F_Cu]
        polys = z.GetFilledPolysList(layer)
        obs = obstacles(layer) + obstacles(other.GetLayer())
        for i in range(polys.OutlineCount()):
            chain = polys.Outline(i)
            if any(chain.PointInside(v) for v in ties):
                continue
            bb = chain.BBox()
            spot = None
            y = to_mm(bb.GetTop())
            while y < to_mm(bb.GetBottom()) and not spot:
                x = to_mm(bb.GetLeft())
                while x < to_mm(bb.GetRight()):
                    v = pcbnew.VECTOR2I(mm(x), mm(y))
                    # the whole via pad must sit in the island, and in the other layer's plane
                    ring = [pcbnew.VECTOR2I(mm(x + dx * VIA / 2), mm(y + dy * VIA / 2))
                            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))]
                    if (all(chain.PointInside(r) for r in ring) and other.HitTestFilledArea(other.GetLayer(), v)
                            and all(seg_dist(x, y, *s_) >= h + VIA / 2 + CLR for s_, h, _ in obs)):
                        spot = v
                        break
                    x += 0.2
                y += 0.2
            if not spot:
                print("island with no room for a via at", to_mm(bb.GetCenter().x), to_mm(bb.GetCenter().y))
                continue
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(spot)
            v.SetWidth(mm(VIA))
            v.SetDrill(mm(DRILL))
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(gnd)
            b.Add(v)
            ties.append(spot)
            n += 1
    return n


added += tie_islands()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
print("GND fixes:", added, "still unreached:", len(problem_pads()))
