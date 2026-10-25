"""Writes ym2612_player/bom.csv in a layout PCBWay's turnkey quote accepts. Run after design.py."""
import csv
import os
import re
import sys

import design

MAKERS = {
    "BLM18PG221SN1D": "Murata", "LQH32CN100K53L": "Murata", "LP5907MFX-4.5/NOPB": "Texas Instruments",
    "PIM724": "Pimoroni", "74HCT541D,653": "Nexperia", "110-43-624-41-001000": "Mill-Max",
    "OPA2350UA": "Texas Instruments", "TPA6132A2RTER": "Texas Instruments", "NMJ6HCD2": "Neutrik",
    "SJ1-3523N": "CUI Devices / Same Sky", "PTA2044-2015DPA103": "Bourns", "B3F-4055": "Omron",
    "PEC11R-4215F-N0024": "Bourns", "BSS138": "onsemi", "B4B-XH-A(LF)(SN)": "JST", "B6B-XH-A(LF)(SN)": "JST",
    "LED3WAW": "Lumimax", "PPTC201LFBN-RC": "Sullins",
}
THT = ("Socketed", "DIP", "Jack", "LED_D3", "SW_PUSH", "RotaryEncoder", "JST", "PinHeader", "Oscillator_DIP")


def natural(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    return (m.group(1), int(m.group(2)))


groups = {}
for sh in design.P.sheets:
    for p in sh.parts:
        if p.ref.startswith("#") or p.lib_id.startswith("Mechanical:") or p.lib_id == "Device:NetTie_2":
            continue
        if p.lib_id == "Connector:TestPoint":
            continue
        fp = p.fields.get("Footprint", "")
        mpn = p.fields.get("MPN", "")
        key = (mpn or p.value, fp, mpn, p.fields.get("Spec", ""), p.dnp)
        groups.setdefault(key, {"refs": set(), "values": []})
        groups[key]["refs"].add(p.ref)
        if p.value not in groups[key]["values"]:
            groups[key]["values"].append(p.value)

rows = []
for (_, fp, mpn, spec, dnp), g in groups.items():
    refs = sorted(g["refs"], key=natural)
    value = " / ".join(g["values"])
    kind = "THT" if any(t in fp for t in THT) or not fp else "SMD"
    rows.append({
        "Designator": ",".join(refs), "Qty": 0 if dnp else len(refs), "Value": value,
        "Manufacturer": MAKERS.get(mpn, "Any" if not mpn else ""), "Manufacturer Part Number": mpn or "generic",
        "Description": spec, "Package / Footprint": fp.split(":")[-1] if fp else "TODO: footprint",
        "Type": kind, "Fit": "Do not fit" if dnp else "Fit",
    })
rows.sort(key=lambda r: natural(r["Designator"].split(",")[0]))
# The Pico Plus 2 stands on sockets (it has parts underneath). These have no symbol of their own. PCBWay fits the
# sockets; Joey supplies the Pico and its headers.
for ref, value, maker, mpn, spec, fit in [
        ("U2-SKT", "1x20 female socket, 2.54 mm", "Sullins", "PPTC201LFBN-RC",
         "Soldered to the board in U2's two rows of holes, 8.5 mm tall", True),
        ("U2-HDR", "1x20 male header, 2.54 mm", "Any", "generic",
         "Joey supplies and solders these to the Pico Plus 2 (U2) so it plugs into U2-SKT", False)]:
    rows.append({"Designator": ref, "Qty": 2 if fit else 0, "Value": value, "Manufacturer": maker,
                 "Manufacturer Part Number": mpn, "Description": spec, "Package / Footprint": "1x20 P2.54mm vertical",
                 "Type": "THT", "Fit": "Fit" if fit else "Do not fit"})
out = os.path.join(os.path.dirname(__file__), "..", "ym2612_player", "bom.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for i, r in enumerate(rows, 1):
        w.writerow(r)
print("wrote", out, len(rows), "lines,", sum(r["Qty"] for r in rows), "parts")
