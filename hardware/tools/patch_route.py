"""Routes the few connections Freerouting leaves open, with a small grid maze router on both layers.

Run: python3 patch_route.py board.kicad_pcb REF.PAD:REF.PAD [...]
Each pair is joined by tracks (45 degree steps) and vias that keep the net's clearance from all other copper.
"""
import heapq
import json
import math
import os
import sys

import numpy as np
import pcbnew
from PIL import Image, ImageDraw

P = sys.argv[1]
b = pcbnew.LoadBoard(P)
to, mm = pcbnew.ToMM, pcbnew.FromMM
G = 0.05                                        # grid, mm
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)


CLASSES = {c["name"]: c for c in json.load(open(os.path.splitext(P)[0] + ".kicad_pro"))["net_settings"]["classes"]}


class netclass:
    """Clearance, width and via size of a net's class, in nm (KiCad 7's Python can't hand back the class itself)."""
    def __init__(self, net):
        c = CLASSES.get(b.FindNet(net).GetNetClassName() if net else "Default", CLASSES["Default"])
        self.c = c

    def GetClearance(self):
        return mm(self.c["clearance"])

    def GetTrackWidth(self):
        return mm(self.c["track_width"])

    def GetViaDiameter(self):
        return mm(self.c["via_diameter"])

    def GetViaDrill(self):
        return mm(self.c["via_drill"])


def route(pa, pb):
    net = pa.GetNetname()
    nc = netclass(net)
    w = to(nc.GetTrackWidth())
    via_d, via_h = to(nc.GetViaDiameter()), to(nc.GetViaDrill())
    own_clr = to(nc.GetClearance())

    def clr_of(item, fp_ref=None):
        # Clearance is the larger of the two net classes, except between U8's own pads (fine-pitch QFN, 0.2 mm).
        if fp_ref == "U8":
            return 0.2 + 0.04
        n = item.GetNetname()
        other = to(netclass(n).GetClearance()) if n else 0.25
        return max(own_clr, other) + 0.04
    x0 = min(to(pa.GetPosition().x), to(pb.GetPosition().x)) - 8
    y0 = min(to(pa.GetPosition().y), to(pb.GetPosition().y)) - 8
    x1 = max(to(pa.GetPosition().x), to(pb.GetPosition().x)) + 8
    y1 = max(to(pa.GetPosition().y), to(pb.GetPosition().y)) + 8
    W, H = int((x1 - x0) / G) + 1, int((y1 - y0) / G) + 1
    px = lambda x: (x - x0) / G
    py = lambda y: (y - y0) / G

    def blank():
        return Image.new("1", (W, H), 0)

    track_free = {l: blank() for l in LAYERS}     # where a track centre may go
    via_free = blank()                            # where a via centre may go
    dt = {l: ImageDraw.Draw(track_free[l]) for l in LAYERS}
    dv = ImageDraw.Draw(via_free)

    def disc(d, x, y, r):
        d.ellipse([px(x - r), py(y - r), px(x + r), py(y + r)], fill=1)

    def line(d, a, c, r):
        d.line([px(a[0]), py(a[1]), px(c[0]), py(c[1])], fill=1, width=int(math.ceil(2 * r / G)) + 1)
        disc(d, *a, r)
        disc(d, *c, r)

    def rect(d, bb, r):
        d.rounded_rectangle([px(bb[0] - r), py(bb[1] - r), px(bb[2] + r), py(bb[3] + r)], radius=r / G, fill=1)

    for f in b.GetFootprints():
        for pad in f.Pads():
            bb = pad.GetBoundingBox()
            box = (to(bb.GetLeft()), to(bb.GetTop()), to(bb.GetRight()), to(bb.GetBottom()))
            if pad.HasHole():
                hc = (to(pad.GetPosition().x), to(pad.GetPosition().y))
                disc(dv, *hc, to(pad.GetDrillSize().x) / 2 + via_h / 2 + 0.26)
            if pad.GetNetname() == net:
                continue
            clr = clr_of(pad, f.GetReference())
            for l in LAYERS:
                if pad.IsOnLayer(l):
                    rect(dt[l], box, clr + w / 2)
            rect(dv, box, clr + via_d / 2)
    for t in b.GetTracks():
        own = t.GetNetname() == net
        if t.GetClass() == "PCB_VIA":
            c = (to(t.GetPosition().x), to(t.GetPosition().y))
            disc(dv, *c, to(t.GetDrillValue()) / 2 + via_h / 2 + 0.26)
            if own:
                continue
            r = to(t.GetWidth()) / 2
            clr = clr_of(t)
            for l in LAYERS:
                disc(dt[l], *c, r + clr + w / 2)
            disc(dv, *c, r + clr + via_d / 2)
            continue
        if own:
            continue
        a = (to(t.GetStart().x), to(t.GetStart().y))
        c = (to(t.GetEnd().x), to(t.GetEnd().y))
        r = to(t.GetWidth()) / 2
        clr = clr_of(t)
        line(dt[t.GetLayer()], a, c, r + clr + w / 2)
        line(dv, a, c, r + clr + via_d / 2)
    blocked = {l: np.array(track_free[l], dtype=bool) for l in LAYERS}
    vblocked = np.array(via_free, dtype=bool) | blocked[LAYERS[0]] | blocked[LAYERS[1]]

    def cell(pad):
        return int(round(px(to(pad.GetPosition().x)))), int(round(py(to(pad.GetPosition().y))))

    def pad_cells(pad):
        bb = pad.GetBoundingBox()
        return (int(px(to(bb.GetLeft()))), int(py(to(bb.GetTop()))), int(px(to(bb.GetRight()))), int(py(to(bb.GetBottom()))))

    # Let the path leave and enter the two pads.
    for pad in (pa, pb):
        l0, t0, r0, b0 = pad_cells(pad)
        for l in LAYERS:
            if pad.IsOnLayer(l):
                blocked[l][t0:b0 + 1, l0:r0 + 1] = False
    start = [(cell(pa), l) for l in LAYERS if pa.IsOnLayer(l)]
    goal_box = pad_cells(pb)
    goal_layers = [l for l in LAYERS if pb.IsOnLayer(l)]
    gx, gy = cell(pb)
    moves = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    heap, seen, prev = [], {}, {}
    for (cx, cy), l in start:
        heapq.heappush(heap, (0, 0, cx, cy, l, -1))
        seen[(cx, cy, l, -1)] = 0
    end = None
    while heap:
        f_, g, cx, cy, l, d = heapq.heappop(heap)
        if l in goal_layers and goal_box[0] <= cx <= goal_box[2] and goal_box[1] <= cy <= goal_box[3]:
            end = (cx, cy, l, d)
            break
        if seen.get((cx, cy, l, d), 1e18) < g:
            continue
        nexts = []
        for k, (mx, my) in enumerate(moves):
            nx, ny = cx + mx, cy + my
            if 0 <= nx < W and 0 <= ny < H and not blocked[l][ny, nx]:
                step = math.hypot(mx, my)
                turn = 0 if d in (-1, k) else 2.0
                nexts.append((nx, ny, l, k, step + turn))
        if not vblocked[cy, cx]:
            other = LAYERS[1] if l == LAYERS[0] else LAYERS[0]
            nexts.append((cx, cy, other, -1, 60))
        for nx, ny, nl, nd, c in nexts:
            ng = g + c
            key = (nx, ny, nl, nd)
            if ng < seen.get(key, 1e18):
                seen[key] = ng
                prev[key] = (cx, cy, l, d)
                h = math.hypot(nx - gx, ny - gy)
                heapq.heappush(heap, (ng + h, ng, nx, ny, nl, nd))
    if not end:
        return False
    path = [end]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    # Turn the cell path into tracks and vias, merging straight runs.
    ni = b.FindNet(net)
    pts = [(x0 + c[0] * G, y0 + c[1] * G, c[2]) for c in path]
    run = [pts[0]]
    def emit(run):
        if len(run) < 2:
            return
        corners = [run[0]]
        for i in range(1, len(run) - 1):
            ax, ay = run[i][0] - corners[-1][0], run[i][1] - corners[-1][1]
            bx, by = run[i + 1][0] - run[i][0], run[i + 1][1] - run[i][1]
            if abs(ax * by - ay * bx) > 1e-9:
                corners.append(run[i])
        corners.append(run[-1])
        for a, c in zip(corners, corners[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
            t.SetEnd(pcbnew.VECTOR2I(mm(c[0]), mm(c[1])))
            t.SetWidth(mm(w))
            t.SetLayer(a[2])
            t.SetNet(ni)
            b.Add(t)
    for p in pts[1:]:
        if p[2] != run[-1][2]:
            emit(run)
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(mm(p[0]), mm(p[1])))
            v.SetWidth(mm(via_d))
            v.SetDrill(mm(via_h))
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(ni)
            b.Add(v)
            run = [p]
        else:
            run.append(p)
    emit(run)
    # Stubs from the pad centres to where the path leaves / enters them.
    for pad, p in ((pa, pts[0]), (pb, pts[-1])):
        c = (to(pad.GetPosition().x), to(pad.GetPosition().y))
        if math.hypot(c[0] - p[0], c[1] - p[1]) > 1e-6:
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(c[0]), mm(c[1])))
            t.SetEnd(pcbnew.VECTOR2I(mm(p[0]), mm(p[1])))
            t.SetWidth(mm(w))
            t.SetLayer(p[2])
            t.SetNet(ni)
            b.Add(t)
    return True


for pair in sys.argv[2:]:
    a, c = pair.split(":")
    pa = b.FindFootprintByReference(a.split(".")[0]).FindPadByNumber(a.split(".")[1])
    pb = b.FindFootprintByReference(c.split(".")[0]).FindPadByNumber(c.split(".")[1])
    print(pair, "routed" if route(pa, pb) else "NO PATH")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
