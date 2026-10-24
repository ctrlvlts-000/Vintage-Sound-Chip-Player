"""Checks the KiCad netlist export against what design.py intended."""
import sys
import xml.etree.ElementTree as ET
import design

root = ET.parse(sys.argv[1]).getroot()
actual = {}
for net in root.iter("net"):
    name = net.get("name").split("/")[-1]
    for node in net.iter("node"):
        actual[(node.get("ref"), node.get("pin"))] = name
refs = [c.get("ref") for c in root.iter("comp")]
bad = [r for r in refs if "?" in r]
dups = {r for r in refs if refs.count(r) > 1}
errors = 0
for sh in design.P.sheets:
    for p in sh.parts:
        if p.ref.startswith("#"):
            continue
        for pin, net in p.nets.items():
            got = actual.get((p.ref, pin))
            want = net
            if net == "NC":
                if got and not got.startswith("unconnected"):
                    print(f"{p.ref}.{pin}: expected NC, got {got}"); errors += 1
                continue
            if got != want:
                print(f"{p.ref}.{pin}: expected {want}, got {got}"); errors += 1
print(f"components {len(refs)}, nets {len(set(actual.values()))}, bad refs {bad}, duplicate refs {sorted(dups)}, mismatches {errors}")
