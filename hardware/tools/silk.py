"""Moves each part's reference label to a clear spot next to it (no pads, vias, other labels or board edge under it).
Run after routing: python3 silk.py ../ym2612_player/ym2612_player.kicad_pcb"""
import sys
import pcbnew

P = sys.argv[1]
b = pcbnew.LoadBoard(P)
mm = pcbnew.FromMM
edge = b.GetBoardEdgesBoundingBox()
edge.Inflate(-mm(0.6))


def box(l, t, r, bt):
    return (l, t, r, bt)


def hit(a, c):
    return a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]


def bb(item, grow=0.2):
    r = item.GetBoundingBox()
    g = mm(grow)
    return (r.GetLeft() - g, r.GetTop() - g, r.GetRight() + g, r.GetBottom() + g)


copper = [bb(p) for f in b.GetFootprints() for p in f.Pads()]
copper += [bb(t) for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
silk = []
for f in b.GetFootprints():
    for g in f.GraphicalItems():
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() != "FP_TEXT":
            silk.append(bb(g, 0.15))
placed = []
moved = 0
for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    ref = f.Reference()
    if f.GetReference().startswith(("H", "NT")) or not ref.IsVisible():
        continue
    ref.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
    ref.SetTextThickness(mm(0.12))
    cy = f.GetCourtyard(pcbnew.F_CrtYd).BBox() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else f.GetBoundingBox(False, False)
    cx, cyy = cy.GetCenter().x, cy.GetCenter().y
    w = len(f.GetReference()) * mm(0.75) + mm(0.3)
    h = mm(1.1)
    cands = []
    for d in (0, 0.6, 1.4):
        dd = mm(d)
        cands += [(cx, cy.GetTop() - h // 2 - dd, 0), (cx, cy.GetBottom() + h // 2 + dd, 0),
                  (cy.GetLeft() - h // 2 - dd, cyy, 90), (cy.GetRight() + h // 2 + dd, cyy, 90)]
    best = None
    for x, y, rot in cands:
        hw, hh = (w // 2, h // 2) if rot == 0 else (h // 2, w // 2)
        r = (x - hw, y - hh, x + hw, y + hh)
        if not (edge.GetLeft() < r[0] and r[2] < edge.GetRight() and edge.GetTop() < r[1] and r[3] < edge.GetBottom()):
            continue
        score = sum(hit(r, c) for c in copper) * 10 + sum(hit(r, c) for c in placed) * 10 + sum(hit(r, c) for c in silk)
        if best is None or score < best[0]:
            best = (score, x, y, rot, r)
        if score == 0:
            break
    if best:
        _, x, y, rot, r = best
        ref.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
        ref.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        ref.SetKeepUpright(True)
        placed.append(r)
        moved += 1
    # values live on the fab layer only, so they never clash on the silkscreen
    if f.Value().GetLayer() == pcbnew.F_SilkS:
        f.Value().SetLayer(pcbnew.F_Fab)
b.Save(P)
print("placed", moved, "labels")
