"""Turns KiCad's position file into PCBWay's placement (CPL) layout: Designator, Mid X, Mid Y, Layer, Rotation."""
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src)))
with open(dst, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in rows:
        if r["Ref"].startswith(("H", "TP", "NT")):
            continue  # mounting holes, bare test pads and the ground join have nothing to place
        w.writerow([r["Ref"], f'{float(r["PosX"]):.3f}mm', f'{float(r["PosY"]):.3f}mm',
                    "Top" if r["Side"] == "top" else "Bottom", f'{float(r["Rot"]):.0f}'])
print("wrote", dst, len(rows), "parts")
