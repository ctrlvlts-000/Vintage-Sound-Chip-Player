"""Routes the board with Freerouting, then fills the ground planes.

Run: python3 route.py ../ym2612_player/ym2612_player.kicad_pcb /path/to/freerouting.jar
Ground planes are taken out while Freerouting runs (it would treat them as solid copper). GND is left out of the
routing too: the planes carry it, so GND tracks would only duplicate them. gndvia.py then gives any GND pad the planes
can't reach its own via. Clearance and via size come from the project's Default net class.
"""
import os
import re
import subprocess
import sys
import tempfile

import pcbnew

PCB, JAR = sys.argv[1], sys.argv[2]
# +4V5A stays at 250 um so it can reach the TPA6132A2's 0.25 mm QFN pads.
SKIP = {"GND"}
POWER = {"+5V": 500, "+5V_YM": 400, "+4V5A": 250, "+3V3": 400}

def import_ses(board, path):
    """Adds Freerouting's tracks and vias to the board. (KiCad's own SES import needs the GUI.)"""
    from kigen import parse
    tree = parse(open(path).read())
    routes = next(x for x in tree if isinstance(x, list) and x[0] == "routes")
    res = next(x for x in routes if isinstance(x, list) and x[0] == "resolution")
    scale = {"um": 1000, "mm": 1000000}[res[1]] / float(res[2])  # session units -> nm
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    out = next(x for x in routes if isinstance(x, list) and x[0] == "network_out")
    for net in out[1:]:
        ni = board.FindNet(net[1])
        for item in net[2:]:
            if item[0] == "wire":
                path_ = item[1]
                layer, width = layers[path_[1]], int(float(path_[2]) * scale)
                pts = [(int(float(path_[i]) * scale), -int(float(path_[i + 1]) * scale)) for i in range(3, len(path_), 2)]
                for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(pcbnew.VECTOR2I(x0, y0))
                    t.SetEnd(pcbnew.VECTOR2I(x1, y1))
                    t.SetWidth(width)
                    t.SetLayer(layer)
                    t.SetNet(ni)
                    board.Add(t)
            elif item[0] == "via":
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(int(float(item[2]) * scale), -int(float(item[3]) * scale)))
                v.SetWidth(ds.GetViaDiameter())
                v.SetDrill(ds.GetViaDrill())
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNet(ni)
                board.Add(v)


board = pcbnew.LoadBoard(PCB)
ds = board.GetDesignSettings().m_NetSettings.m_DefaultNetClass
CLEAR = pcbnew.ToMM(ds.GetClearance()) * 1000 + 0.1  # um, just over the rule so DRC never sees it exact
tmp = tempfile.mkdtemp()
dsn, ses = os.path.join(tmp, "board.dsn"), os.path.join(tmp, "board.ses")

zones = list(board.Zones())
for z in zones:
    board.Remove(z)
assert pcbnew.ExportSpecctraDSN(board, dsn)

# Power nets get their own class with wider tracks (widths in um, the DSN's unit), keeping the clearance of the net
# class they came from. GND leaves every class.
text = open(dsn).read()
via = re.search(r'\(via "(Via\[0-1\]_\d+:\d+_um)"\)', text).group(1)
power_clear = {}
for m in list(re.finditer(r'\(class (\S+)(?: "")?(.*?)\(circuit.*?\(clearance ([\d.]+)\)', text, re.S)):
    names = m.group(2).split()
    for n in names:
        if n.strip('"') in POWER:
            power_clear[n.strip('"')] = float(m.group(3))
    keep = [n for n in names if n.strip('"') not in POWER and n.strip('"') not in SKIP]
    head = m.group(0)[:m.group(0).index("(circuit")]
    text = text.replace(head, f'(class {m.group(1)} "" ' + " ".join(keep) + "\n      ", 1)
cls = ""
for net, w in POWER.items():
    cls += (f'    (class pwr_{net.strip("+")} "{net}"\n      (circuit\n        (use_via {via})\n      )\n'
            f'      (rule\n        (width {w})\n        (clearance {power_clear.get(net, CLEAR):.1f})\n      )\n    )\n')
text = re.sub(r'(\n  \)\n  \(wiring)', "\n" + cls.rstrip("\n") + r"\1", text, count=1)
for net in SKIP:  # drop the net itself, so Freerouting treats its pads as plain obstacles
    text = re.sub(r'\n    \(net "?%s"?\n.*?\n    \)' % re.escape(net), "", text, count=1, flags=re.S)
open(dsn, "w").write(text)

if len(sys.argv) > 3:
    ses = sys.argv[3]  # reuse a finished Freerouting session
else:
    subprocess.run(["xvfb-run", "-a", "java", "-jar", JAR, "-de", dsn, "-do", ses, "-mp", os.environ.get("FR_PASSES", "40"), "-dct", "0"], check=True)

for z in zones:
    board.Add(z)
for t in list(board.GetTracks()):  # the session holds every wire, old and new
    board.Remove(t)
import_ses(board, ses)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("routed")
