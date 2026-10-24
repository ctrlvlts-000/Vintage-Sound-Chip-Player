"""Writes ym2612.pretty/Pimoroni_PicoPlus2_Socketed.kicad_mod with KiCad's own pcbnew module.
The Pico Plus 2 has parts on its underside (flash, PSRAM, an 8-pin JST-SH socket), so it can't be soldered flat.
It stands on two 1x20 female sockets instead. Holes follow the Raspberry Pi Pico: 2.54 mm pitch, rows 17.78 mm apart.
Pin numbers are the Pico's: 1-20 down the left side from the USB end, 21-40 back up the right side."""
import os
import sys
import pcbnew

out = sys.argv[1]
fp = pcbnew.FOOTPRINT(None)
fp.SetFPID(pcbnew.LIB_ID("ym2612", "Pimoroni_PicoPlus2_Socketed"))
fp.SetDescription("Pimoroni Pico Plus 2 (PIM724) on two 1x20 2.54 mm female sockets (Pico hole pattern). "
                  "USB-C at the top (pin 1 end). Leave room under the module for its underside parts.")
fp.SetKeywords("RP2350 Pico Plus 2 module socket")
fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
fp.Reference().SetText("U**")
fp.Value().SetText("Pimoroni_PicoPlus2_Socketed")
mm = pcbnew.FromMM
for n in range(1, 41):
    if n <= 20:
        x, y = -8.89, -24.13 + (n - 1) * 2.54
    else:
        x, y = 8.89, 24.13 - (n - 21) * 2.54
    pad = pcbnew.PAD(fp)
    pad.SetNumber(str(n))
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetShape(pcbnew.PAD_SHAPE_RECT if n == 1 else pcbnew.PAD_SHAPE_OVAL)
    pad.SetSize(pcbnew.VECTOR2I(mm(1.7), mm(1.7)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
    pad.SetLayerSet(pad.PTHMask())
    pad.SetPos0(pcbnew.VECTOR2I(int(round(x * 1e6)), int(round(y * 1e6))))
    pad.SetPosition(pcbnew.VECTOR2I(int(round(x * 1e6)), int(round(y * 1e6))))
    fp.Add(pad)


def rect(layer, x1, y1, x2, y2, w):
    for a, b in [((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))]:
        s = pcbnew.FP_SHAPE(fp)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart0(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        s.SetEnd0(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        fp.Add(s)


rect(pcbnew.F_Fab, -10.5, -25.5, 10.5, 25.5, 0.1)          # module outline, 21 x 51 mm
rect(pcbnew.F_CrtYd, -11.0, -27.0, 11.0, 26.0, 0.05)       # includes the USB-C plug overhang
rect(pcbnew.F_SilkS, -10.61, -25.61, 10.61, 25.61, 0.12)
# USB-C outline on the fab layer, overhanging the top edge.
rect(pcbnew.F_Fab, -4.5, -26.8, 4.5, -21.0, 0.1)
t = pcbnew.FP_TEXT(fp)
t.SetText("USB-C")
t.SetLayer(pcbnew.F_SilkS)
t.SetPos0(pcbnew.VECTOR2I(0, mm(-22.5)))
t.SetPosition(pcbnew.VECTOR2I(0, mm(-22.5)))
fp.Add(t)
for f, y in [(fp.Reference(), -28), (fp.Value(), 28)]:
    f.SetPos0(pcbnew.VECTOR2I(0, mm(y)))
    f.SetPosition(pcbnew.VECTOR2I(0, mm(y)))
lib = os.path.abspath(out)
os.makedirs(lib, exist_ok=True)
pcbnew.FootprintSave(lib, fp)
print("saved", lib)
