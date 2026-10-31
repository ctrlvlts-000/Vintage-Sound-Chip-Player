"""Cuts every 90 degree (or sharper) track corner into two 45 degree bends, then checks each cut with DRC.

Run after routing: python3 miter.py ../ym2612_player/ym2612_player.kicad_pcb
A corner is two track pieces of one net meeting end to end on one layer, with nothing else (pad, via, third track)
at that point. A cut that would break a clearance is tried again smaller, and left as it was if even that fails.
"""
import math
import os
import re
import sys
import tempfile

import pcbnew

P = sys.argv[1]
SIZES = (0.6, 0.35, 0.2)          # chamfer leg lengths to try, mm
mm, to_mm = pcbnew.FromMM, pcbnew.ToMM


def corners(b):
    ends = {}
    for t in b.GetTracks():
        key = None
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            ends.setdefault((p.x, p.y, pcbnew.F_Cu), []).append(None)
            ends.setdefault((p.x, p.y, pcbnew.B_Cu), []).append(None)
            continue
        for p, q in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
            ends.setdefault((p.x, p.y, t.GetLayer()), []).append((t, q))
    padpts = set()
    for f in b.GetFootprints():
        for pad in f.Pads():
            for (x, y, layer) in ends:
                if pad.IsOnLayer(layer) and pad.HitTest(pcbnew.VECTOR2I(x, y)):
                    padpts.add((x, y, layer))
    out = []
    for k, lst in ends.items():
        if len(lst) != 2 or None in lst or k in padpts:
            continue
        (ta, qa), (tb, qb) = lst
        ax, ay, bx, by = qa.x - k[0], qa.y - k[1], qb.x - k[0], qb.y - k[1]
        la, lb = math.hypot(ax, ay), math.hypot(bx, by)
        if la and lb and (ax * bx + ay * by) / la / lb > -0.01:      # angle between the legs <= ~90.5 degrees
            out.append((k, ta, tb, (ax / la, ay / la, la), (bx / lb, by / lb, lb)))
    return out


def cut(b, k, ta, tb, da, db, size):
    """Shortens both legs by `size` and joins the new ends with a diagonal. Returns the diagonal."""
    x, y, layer = k
    c = mm(size)
    c = min(c, 0.45 * da[2], 0.45 * db[2])
    pa = pcbnew.VECTOR2I(int(x + da[0] * c), int(y + da[1] * c))
    pb = pcbnew.VECTOR2I(int(x + db[0] * c), int(y + db[1] * c))
    for t, p in ((ta, pa), (tb, pb)):
        if (t.GetStart().x, t.GetStart().y) == (x, y):
            t.SetStart(p)
        else:
            t.SetEnd(p)
    d = pcbnew.PCB_TRACK(b)
    d.SetStart(pa)
    d.SetEnd(pb)
    d.SetWidth(min(ta.GetWidth(), tb.GetWidth()))
    d.SetLayer(layer)
    d.SetNet(ta.GetNet())
    b.Add(d)
    return d


def clearance_hits(b):
    """Positions (nm) of every track named in a DRC clearance or short violation."""
    rpt = os.path.join(tempfile.mkdtemp(), "drc.rpt")
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    hits = []
    for block in open(rpt).read().split("\n["):
        if block.startswith(("clearance", "shorting_items", "tracks_crossing", "hole_clearance")):
            for xs, ys in re.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): Track", block):
                hits.append((mm(float(xs)), mm(float(ys))))
    return hits


b = pcbnew.LoadBoard(P)
todo = corners(b)
print("corners at 90 degrees or sharper:", len(todo))
for size in SIZES:
    if not todo:
        break
    saved = []
    for k, ta, tb, da, db in todo:
        old = [(t, pcbnew.VECTOR2I(t.GetStart()), pcbnew.VECTOR2I(t.GetEnd())) for t in (ta, tb)]
        saved.append((k, ta, tb, da, db, old, cut(b, k, ta, tb, da, db, size)))
    hits = clearance_hits(b)
    todo = []
    for k, ta, tb, da, db, old, d in saved:
        if any(d.HitTest(pcbnew.VECTOR2I(int(x), int(y)), mm(0.05)) for x, y in hits):
            b.Remove(d)
            for t, s, e in old:
                t.SetStart(s)
                t.SetEnd(e)
            todo.append((k, ta, tb, da, db))
    print(f"  {size} mm cuts: {len(saved) - len(todo)} kept, {len(todo)} undone")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
print("corners left:", len(todo))
