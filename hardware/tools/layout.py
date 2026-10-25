"""First-pass PCB for the YM2612 player Rev A: board outline, part placement, ground planes.

Run: python3 layout.py ../ym2612_player/ym2612_player.kicad_pcb
Front-panel parts (buttons, knob, jacks, Pico USB-C, LCD connector) are placed by hand below. The small parts are
placed automatically next to the chips they connect to. Routing is done afterwards by Freerouting (route.sh).
Once the board is edited in KiCad, the .kicad_pcb file is the real source and this script should not be rerun.
"""
import math
import os
import sys

import pcbnew

import design

OUT = sys.argv[1]
KICAD_FP = "/usr/share/kicad/footprints"
LOCAL_FP = os.path.join(os.path.dirname(os.path.abspath(OUT)), "ym2612.pretty")

W, D = 240.0, 120.0           # board size, mm. Rear edge is y = 0, front edge is y = D.
OX, OY = 50.0, 50.0           # where the board sits on KiCad's page
AUDIO_X = 62.0                # audio parts stay left of this line (one solid ground, partitioned by placement)
POWER_NETS = {"GND", "+5V", "+5V_YM", "+4V5A", "+3V3"}

mm = pcbnew.FromMM


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


# ------------------------------------------------------------------ parts from the schematic description
parts = {}
for sh in design.P.sheets:
    for p in sh.parts:
        if p.ref.startswith("#") or not p.fields.get("Footprint"):
            continue
        e = parts.setdefault(p.ref, {"fp": p.fields["Footprint"], "value": p.value, "nets": {}, "dnp": p.dnp,
                                     "mpn": p.fields.get("MPN", "")})
        e["nets"].update(p.nets)

board = pcbnew.BOARD()
netinfo = {}
for e in parts.values():
    for n in e["nets"].values():
        if n != "NC" and n not in netinfo:
            ni = pcbnew.NETINFO_ITEM(board, n)
            board.Add(ni)
            netinfo[n] = ni

# Design rules PCBWay's standard process handles easily.
ds = board.GetDesignSettings()
ds.m_TrackMinWidth = mm(0.2)
ds.m_MinClearance = mm(0.2)
ds.m_ViasMinSize = mm(0.6)
ds.m_MinThroughDrill = mm(0.3)
ds.SetCopperLayerCount(2)

footprints = {}


def load(ref):
    e = parts[ref]
    lib, name = e["fp"].split(":")
    path = LOCAL_FP if lib == "ym2612" else os.path.join(KICAD_FP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))      # keep the library nickname so KiCad can match it to the schematic
    fp.SetReference(ref)
    fp.SetValue(e["value"])
    for pad in fp.Pads():
        n = e["nets"].get(pad.GetNumber())
        if n and n != "NC":
            pad.SetNet(netinfo[n])
    for pad in fp.Pads():
        # Ground pins join the plane solidly: SMD decoupling pads and the YM2612 socket's ground pins (1, 12, 14, 19).
        if pad.GetNetname() == "GND" and (pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD or ref == "U5"):
            pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    fp.SetExcludedFromPosFiles(False)              # some stock footprints ship excluded; only DNP parts should be
    fp.SetExcludedFromBOM(False)
    if e["dnp"]:
        fp.SetExcludedFromPosFiles(True)
        fp.SetExcludedFromBOM(True)
        if hasattr(fp, "SetDNP"):
            fp.SetDNP(True)
    board.Add(fp)
    footprints[ref] = fp
    return fp


def place(ref, x, y, rot=0):
    fp = footprints.get(ref) or load(ref)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pt(x, y))
    return fp


def place_at_bbox(ref, x0, y0, rot=0, edge=None):
    """Place so the courtyard's top-left corner lands at (x0, y0); edge='rear' pins the courtyard to y=0, etc."""
    fp = place(ref, 0, 0, rot)
    bb = courtyard(fp)
    dx, dy = x0 - bb[0], y0 - bb[1]
    fp.Move(pt(dx, dy) - pt(0, 0))
    return fp


def courtyard(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount():
        b = cy.BBox()
    else:
        b = fp.GetBoundingBox(False, False)
    return (pcbnew.ToMM(b.GetLeft()) - OX, pcbnew.ToMM(b.GetTop()) - OY,
            pcbnew.ToMM(b.GetRight()) - OX, pcbnew.ToMM(b.GetBottom()) - OY)


# ------------------------------------------------------------------ hand-placed parts
# Rear edge: two balanced 1/4" jacks (left), Pico Plus 2 with its USB-C port at the edge.
for ref, x in (("J2", 12), ("J3", 36)):
    fp = place(ref, 0, 0, 270)
    bb = courtyard(fp)
    # The ferrule pokes 2.9 mm past the body: let the body face sit on the rear edge.
    fp.Move(pt(x - bb[0], -bb[1] - 2.9) - pt(0, 0))
place("U2", 104.0, 25.5, 0)                       # Pico: body 21 x 51 mm, USB-C overhangs the rear edge 1.3 mm
# Front edge: headphone jack.
JX = 16.0
place("J5", JX, D - 4.5, 0)                      # its footprint puts the board edge 4.5 mm in front of the origin
place("J4", 36.0, 108.0, 0)                       # 6-pin plug for the volume slider in the case top
# Chip area, under the case's round window.
place("U5", 66.0, 60.0, 0)                        # YM2612 socket, pin 1 top left; centre is (73.6, 74)
place("D1", 59.0, 74.0, 90)                       # window LEDs either side of the chip
place("D2", 86.2, 74.0, 90)
place("U3", 84.0, 24.0, 180)                      # data buffer, between the Pico and the chip
place("U4", 84.0, 44.0, 180)                      # control/clock buffer
place("X1", 92.0, 96.0, 0)                        # optional oscillator can (not fitted)
place("FB1", 90.0, 8.0, 0)                        # ferrite from USB 5V to the chip and buffer rail, by the buffers
# Audio area, left.
place("U6", 46.0, 52.0, 0)                        # Model 1 filter, L and R
place("U7", 46.0, 70.0, 0)                        # inverters for the balanced hot legs
place("U8", 26.0, 96.0, 0)                        # TPA6132A2 headphone amp, next to the headphone jack
place("U1", 50.0, 36.0, 0)                        # 4.5 V analog LDO
# Right side: LCD connector, buttons, knob. The LCD module sits above this area on standoffs.
place("J6", 120.0, 8.0, 270)                      # LCD plug, beside the module rather than under its I2C backpack
for i in range(7):
    place(f"SW{i + 1}", 120.0 + i * 17.0, 98.0, 0)
place("SW8", 223.5, 77.5, 0)                      # data knob: shaft centre at (231, 80), below the LCD so the knob clears it
place("J1", 122.0, 40.0, 0)                       # spare GPIO header (not fitted)

holes = []
# Corner holes, then the LCD module's four standoffs (2004A: 93 x 55 mm hole pattern on its 98 x 60 mm board).
for i, (x, y) in enumerate([(4, 4), (W - 4, 4), (4, D - 4), (W - 4, D - 4),
                            (126.5, 10.5), (219.5, 10.5), (126.5, 65.5), (219.5, 65.5)]):
    ref = f"H{i + 1}"
    fp = place(ref, x, y, 0)
    holes.append(ref)

# ------------------------------------------------------------------ automatic placement of the small parts
fixed = set(footprints)
occupied = [courtyard(footprints[r]) for r in fixed]
# Keep small parts out from under the Pico and out of the button row.
occupied.append((93.0, 0.0, 116.0, 52.0))


def free(box, margin=0.4):
    x0, y0, x1, y1 = box
    if x0 < 1 or y0 < 1 or x1 > W - 1 or y1 > D - 1:
        return False
    for a in occupied:
        if x0 < a[2] + margin and x1 > a[0] - margin and y0 < a[3] + margin and y1 > a[1] - margin:
            return False
    return True


def net_targets(ref):
    if ref in design.NEAR:                        # decoupling: right at the supply pin it serves
        chip, pin = design.NEAR[ref]
        pad = footprints[chip].FindPadByNumber(pin)
        return [(pcbnew.ToMM(pad.GetPosition().x) - OX, pcbnew.ToMM(pad.GetPosition().y) - OY)]
    pts = []
    for n in parts[ref]["nets"].values():
        if n in POWER_NETS or n == "NC":
            continue
        for r, fp in footprints.items():
            if r == ref:
                continue
            for pad in fp.Pads():
                if pad.GetNetname() == n:
                    pts.append((pcbnew.ToMM(pad.GetPosition().x) - OX, pcbnew.ToMM(pad.GetPosition().y) - OY))
    return pts


def region_ok(ref, box):
    if ref in design.NEAR:
        return True
    nets = set(parts[ref]["nets"].values())
    audio = bool(nets & {"+4V5A", "VREF", "VA_RAW", "VA_IN"}) or any(n.startswith(("F", "HOT", "COLD", "INV", "HP", "VOL", "PHONE", "SLEEVE")) for n in nets)
    if audio:
        return box[2] < AUDIO_X + 6
    return box[0] > AUDIO_X - 2


def autoplace(ref):
    fp = place(ref, 0, 0, 0)
    targets = net_targets(ref)
    if not targets:
        targets = [(140.0, 70.0)]
    tx = sum(p[0] for p in targets) / len(targets)
    ty = sum(p[1] for p in targets) / len(targets)
    bb0 = courtyard(fp)
    w, h = bb0[2] - bb0[0], bb0[3] - bb0[1]
    best = None
    for rot in (0, 90):
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pt(0, 0))
        bb = courtyard(fp)
        offx, offy = -bb[0], -bb[1]
        bw, bh = bb[2] - bb[0], bb[3] - bb[1]
        step = 0.5
        for r in range(0, 400):
            ring = r * step
            n = max(8, int(2 * math.pi * ring / step))
            found = None
            for k in range(n):
                a = 2 * math.pi * k / n
                x = tx + ring * math.cos(a) - bw / 2
                y = ty + ring * math.sin(a) - bh / 2
                box = (x, y, x + bw, y + bh)
                if free(box) and region_ok(ref, box):
                    found = (ring, rot, x + offx, y + offy, box)
                    break
            if found:
                if best is None or found[0] < best[0]:
                    best = found
                break
    _, rot, x, y, box = best
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pt(x, y))
    occupied.append(box)


# Resistors, capacitors and other small parts first (in reference order, so each chain grows outward from its chip),
# test points last.
todo = [r for r in parts if r not in fixed]
for ref in sorted(todo, key=lambda r: (r not in design.NEAR, r.startswith("TP"), r[0] not in "RCLQDF",
                                      int("".join(c for c in r if c.isdigit()) or 0))):
    autoplace(ref)

# ------------------------------------------------------------------ outline, keep-outs and notes
def seg(layer, a, b, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pt(*a))
    s.SetEnd(pt(*b))
    s.SetLayer(layer)
    s.SetWidth(mm(w))
    board.Add(s)


def rect(layer, x0, y0, x1, y1, w=0.1):
    for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        seg(layer, a, b, w)


def text(layer, x, y, s, size=1.5):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetPosition(pt(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * 0.15))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    board.Add(t)


# The headphone jack's footprint carries its own small edge notch (6.5 mm either side of its centre), so the
# front edge stops there and joins it.
for a, b in [((0, 0), (W, 0)), ((W, 0), (W, D)), ((W, D), (JX + 6.5, D)), ((JX - 6.5, D), (0, D)), ((0, D), (0, 0))]:
    seg(pcbnew.Edge_Cuts, a, b, 0.1)
# LCD module outline (HiLetgo 2004A: 98 x 60 mm board) on the comments layer, for the case design.
rect(pcbnew.Cmts_User, 124, 8, 222, 68)
text(pcbnew.Cmts_User, 126, 64, "LCD module above (98 x 60 mm), on 15 mm standoffs")
# Round chip window, centred on the YM2612.
c = pcbnew.PCB_SHAPE(board)
c.SetShape(pcbnew.SHAPE_T_CIRCLE)
c.SetCenter(pt(73.62, 73.97))
c.SetEnd(pt(73.62 + 22, 73.97))
c.SetLayer(pcbnew.Cmts_User)
c.SetWidth(mm(0.1))
board.Add(c)
text(pcbnew.Cmts_User, 56, 99.5, "Chip window (44 mm)")
text(pcbnew.F_SilkS, 4, 30, "YM2612 Rev A", 2.0)
text(pcbnew.F_SilkS, 12, 29.5 - 3, "BAL L     BAL R", 1.2)

# ------------------------------------------------------------------ ground planes
def zone(net, layer, poly, priority=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(netinfo[net].GetNetCode())
    z.SetAssignedPriority(priority) if hasattr(z, "SetAssignedPriority") else z.SetPriority(priority)
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.4))
    z.SetThermalReliefSpokeWidth(mm(0.4))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in poly:
        ol.Append(mm(OX + x), mm(OY + y))
    board.Add(z)
    return z


# One unbroken ground on both layers. The audio parts sit together on the left, away from USB, the bus and the
# LCD, so digital return currents (which flow under their own tracks) stay out of the audio corner.
gnd_poly = [(0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, D - 0.5), (0.5, D - 0.5)]
for layer in (pcbnew.B_Cu, pcbnew.F_Cu):
    zone("GND", layer, gnd_poly)

pcbnew.SaveBoard(OUT, board)
print("placed", len(footprints), "footprints on a", W, "x", D, "mm board ->", OUT)
