"""Places each part's reference label on the silkscreen where it touches nothing: no pad, part outline, other
part's courtyard, other label or board edge. A label with no clear spot moves to the assembly (F.Fab) layer instead,
so the silkscreen stays clean; PCBWay places parts from the CPL file, not from the labels.
Run after routing: python3 silk.py ../ym2612_player/ym2612_player.kicad_pcb"""
import subprocess
import sys
import pcbnew

P = sys.argv[1]
b = pcbnew.LoadBoard(P)
mm = pcbnew.FromMM
SIZE, STROKE = 1.0, 0.15          # PCBWay's silkscreen minimums are about 1.0 mm text and a 0.15 mm stroke
edge = b.GetBoardEdgesBoundingBox()
edge.Inflate(-mm(0.6))


def hit(a, c):
    return a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]


def grow(r, g):
    g = mm(g)
    return (r.GetLeft() - g, r.GetTop() - g, r.GetRight() + g, r.GetBottom() + g)


def courtyard(f):
    c = f.GetCourtyard(pcbnew.F_CrtYd)
    return c.BBox() if c.OutlineCount() else f.GetBoundingBox(False, False)




def clip_outlines():
    """Cuts part outlines (silkscreen lines) wherever they would cross a pad or run off the board.
    Some stock footprints (the 12 mm buttons) draw their outline straight through their own pads."""
    pads = [grow(p.GetBoundingBox(), 0.1) for f in b.GetFootprints() for p in f.Pads()]
    # the headphone jack's footprint carries its own edge notch: keep outlines off its corners
    pads += [grow(g.GetBoundingBox(), 0.25) for f in b.GetFootprints() for g in f.GraphicalItems()
             if g.GetLayer() == pcbnew.Edge_Cuts]
    inside = grow(b.GetBoardEdgesBoundingBox(), -0.3)
    cut = 0
    lines = [(f, g) for f in b.GetFootprints() for g in f.GraphicalItems()   # list them all before changing any
             if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == "MGRAPHIC" and g.GetShape() == pcbnew.SHAPE_T_SEGMENT]
    for f, g in lines:
        if True:
            a, c = g.GetStart(), g.GetEnd()
            dx, dy = c.x - a.x, c.y - a.y
            keep = [(0.0, 1.0)]
            # inside the board: clip to the inset board box
            t0, t1 = 0.0, 1.0
            for p, q in ((-dx, a.x - inside[0]), (dx, inside[2] - a.x), (-dy, a.y - inside[1]), (dy, inside[3] - a.y)):
                if p == 0:
                    if q < 0:
                        t0, t1 = 1, 0
                elif p < 0:
                    t0 = max(t0, q / p)
                else:
                    t1 = min(t1, q / p)
            keep = [(t0, t1)] if t0 < t1 else []
            for box in pads:  # remove the stretch inside each pad box
                u0, u1 = 0.0, 1.0
                for p, q in ((-dx, a.x - box[0]), (dx, box[2] - a.x), (-dy, a.y - box[1]), (dy, box[3] - a.y)):
                    if p == 0:
                        if q < 0:
                            u0, u1 = 1, 0
                    elif p < 0:
                        u0 = max(u0, q / p)
                    else:
                        u1 = min(u1, q / p)
                if u0 >= u1:
                    continue
                keep = [piece for k0, k1 in keep for piece in ((k0, min(k1, u0)), (max(k0, u1), k1)) if piece[1] > piece[0]]
            length = (dx * dx + dy * dy) ** 0.5
            keep = [k for k in keep if (k[1] - k[0]) * length > mm(0.3)]
            if keep == [(0.0, 1.0)]:
                continue
            cut += 1
            for k0, k1 in keep:
                n = pcbnew.FP_SHAPE(f)
                n.SetShape(pcbnew.SHAPE_T_SEGMENT)
                n.SetStart(pcbnew.VECTOR2I(int(a.x + dx * k0), int(a.y + dy * k0)))
                n.SetEnd(pcbnew.VECTOR2I(int(a.x + dx * k1), int(a.y + dy * k1)))
                n.SetLayer(pcbnew.F_SilkS)
                n.SetWidth(g.GetWidth())
                n.SetLocalCoord()
                f.Add(n)
            f.Remove(g)
    return cut


if "--labels" not in sys.argv:
    # KiCad 7's Python loses track of the footprint list once footprints change, so the labels get a fresh process.
    print("outline lines trimmed:", clip_outlines())
    b.Save(P)
    sys.exit(subprocess.run([sys.executable, __file__, P, "--labels"]).returncode)
copper = [grow(p.GetBoundingBox(), 0.25) for f in b.GetFootprints() for p in f.Pads()]
# Vias are tented (covered by solder mask), so a label may cross one.
silk = [grow(g.GetBoundingBox(), 0.15) for f in b.GetFootprints() for g in f.GraphicalItems()
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() != "FP_TEXT"]
silk += [grow(d.GetBoundingBox(), 0.3) for d in b.Drawings() if d.GetLayer() == pcbnew.F_SilkS]  # board labels
yards = {f.GetReference(): grow(courtyard(f), 0.1) for f in b.GetFootprints()}
placed, moved, to_fab = [], 0, []
for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    ref = f.Reference()
    if f.GetReference().startswith(("H", "NT")):
        ref.SetVisible(False)               # mounting holes need no label
        continue
    if not ref.IsVisible():
        continue
    ref.SetLayer(pcbnew.F_SilkS)
    ref.SetTextSize(pcbnew.VECTOR2I(mm(SIZE), mm(SIZE)))
    ref.SetTextThickness(mm(STROKE))
    ref.SetKeepUpright(True)
    cy = courtyard(f)
    cx, cyy = cy.GetCenter().x, cy.GetCenter().y
    others = [r for k, r in yards.items() if k != f.GetReference()]
    best = None
    for d in (0.35, 0.7, 1.2, 2.0, 2.8):
        for slide in (0, -1.5, 1.5, -3, 3):
            dd, s = mm(d), mm(slide)
            for side in ("top", "bottom", "left", "right"):
                rot = 0 if side in ("top", "bottom") else 90
                ref.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
                ref.SetPosition(pcbnew.VECTOR2I(0, 0))
                bb = ref.GetBoundingBox()
                hw, hh = bb.GetWidth() // 2, bb.GetHeight() // 2
                x, y = {"top": (cx + s, cy.GetTop() - hh - dd), "bottom": (cx + s, cy.GetBottom() + hh + dd),
                        "left": (cy.GetLeft() - hw - dd, cyy + s), "right": (cy.GetRight() + hw + dd, cyy + s)}[side]
                r = (x - hw, y - hh, x + hw, y + hh)
                if not (edge.GetLeft() < r[0] and r[2] < edge.GetRight() and edge.GetTop() < r[1] and r[3] < edge.GetBottom()):
                    continue
                score = sum(hit(r, c) for c in copper + placed + silk + others)
                if best is None or score < best[0]:
                    best = (score, x, y, rot, r)
                if score == 0:
                    break
            if best and best[0] == 0:
                break
        if best and best[0] == 0:
            break
    if best and best[0] == 0:
        _, x, y, rot, r = best
        ref.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
        ref.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        placed.append(r)
        moved += 1
    else:
        ref.SetLayer(pcbnew.F_Fab)          # no clean spot: keep the label for assembly drawings only
        ref.SetPosition(pcbnew.VECTOR2I(cx, cyy))
        ref.SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
        to_fab.append(f.GetReference())
    # values live on the fab layer only, so they never clash on the silkscreen
    if f.Value().GetLayer() == pcbnew.F_SilkS:
        f.Value().SetLayer(pcbnew.F_Fab)
# Gerbers: cut silkscreen away wherever there's no solder mask (pads), so no ink can land on a pad.
pp = b.GetPlotOptions()
pp.SetSubtractMaskFromSilk(True)
b.SetPlotOptions(pp)
b.Save(P)
print("labels on silkscreen:", moved, "moved to the assembly layer:", len(to_fab), " ".join(to_fab))
