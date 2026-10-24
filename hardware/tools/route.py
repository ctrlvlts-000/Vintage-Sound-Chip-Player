"""Routes the board with Freerouting, then fills the ground planes.

Run: python3 route.py ../ym2612_player/ym2612_player.kicad_pcb /path/to/freerouting.jar
Ground planes are taken out while Freerouting runs (it would treat them as solid copper), so it routes every net,
GND included, as tracks. The planes go back in afterwards and join up with those tracks.
"""
import os
import re
import subprocess
import sys
import tempfile

import pcbnew

PCB, JAR = sys.argv[1], sys.argv[2]
POWER = {"GND": 500, "GNDA": 500, "+5V": 500, "+5V_YM": 400, "+4V5A": 400, "+3V3": 400}

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
                v.SetWidth(pcbnew.FromMM(0.6))
                v.SetDrill(pcbnew.FromMM(0.3))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNet(ni)
                board.Add(v)


board = pcbnew.LoadBoard(PCB)
tmp = tempfile.mkdtemp()
dsn, ses = os.path.join(tmp, "board.dsn"), os.path.join(tmp, "board.ses")

zones = list(board.Zones())
for z in zones:
    board.Remove(z)
assert pcbnew.ExportSpecctraDSN(board, dsn)

# Power nets get their own class with wider tracks (widths in um, the DSN's unit).
text = open(dsn).read()
m = re.search(r'\(class kicad_default ""(.*?)\(circuit', text, re.S)
names = m.group(1).split()
keep = [n for n in names if n.strip('"') not in POWER]
text = text.replace(m.group(0), '(class kicad_default "" ' + " ".join(keep) + "\n      (circuit", 1)
cls = ""
for net, w in POWER.items():
    cls += (f'    (class pwr_{net.strip("+")} "{net}"\n      (circuit\n        (use_via Via[0-1]_600:300_um)\n      )\n'
            f'      (rule\n        (width {w})\n        (clearance 200.1)\n      )\n    )\n')
text = re.sub(r'(\n  \)\n  \(wiring)', "\n" + cls.rstrip("\n") + r"\1", text, count=1)
open(dsn, "w").write(text)

if len(sys.argv) > 3:
    ses = sys.argv[3]  # reuse a finished Freerouting session
else:
    subprocess.run(["xvfb-run", "-a", "java", "-jar", JAR, "-de", dsn, "-do", ses, "-mp", "40", "-dct", "0"], check=True)

for z in zones:
    board.Add(z)
import_ses(board, ses)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("routed", len(board.GetTracks()), "track segments and vias")
