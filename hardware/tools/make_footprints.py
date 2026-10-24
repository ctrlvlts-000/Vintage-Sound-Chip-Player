"""Writes ym2612.pretty/Pimoroni_PicoPlus2_SMD.kicad_mod with KiCad's own pcbnew module.
Pad positions follow KiCad's RaspberryPi_Pico_SMD footprint (Pico pinout, 2.54 mm pitch, rows 19.38 mm apart).
Only the 40 edge pads: the Pico Plus 2 has a JST-SH debug port instead of the Pico's three debug pads."""
import os
import sys
import pcbnew

out = sys.argv[1]
fp = pcbnew.FOOTPRINT(None)
fp.SetFPID(pcbnew.LIB_ID("ym2612", "Pimoroni_PicoPlus2_SMD"))
fp.SetDescription("Pimoroni Pico Plus 2 (PIM724), soldered flat by its castellated edge pads. USB-C at the top (pin 1 end). "
                  "Keep traces and vias out from under the module except GND.")
fp.SetKeywords("RP2350 Pico Plus 2 castellated module")
fp.Reference().SetText("U**")
fp.Value().SetText("Pimoroni_PicoPlus2_SMD")
mm = pcbnew.FromMM
for n in range(1, 41):
    if n <= 20:
        x, y = -9.69, -24.13 + (n - 1) * 2.54
    else:
        x, y = 9.69, 24.13 - (n - 21) * 2.54
    pad = pcbnew.PAD(fp)
    pad.SetNumber(str(n))
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
    pad.SetRoundRectRadiusRatio(0.25)
    pad.SetSize(pcbnew.VECTOR2I(mm(3.2), mm(1.6)))
    pad.SetLayerSet(pad.SMDMask())
    pad.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    fp.Add(pad)


def rect(layer, x1, y1, x2, y2, w):
    for a, b in [((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))]:
        s = pcbnew.FP_SHAPE(fp)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        fp.Add(s)


rect(pcbnew.F_Fab, -10.5, -25.5, 10.5, 25.5, 0.1)
rect(pcbnew.F_CrtYd, -11.55, -26.0, 11.55, 26.0, 0.05)
rect(pcbnew.F_SilkS, -10.61, -25.61, 10.61, 25.61, 0.12)
# USB-C outline on the fab layer, overhanging the top edge.
rect(pcbnew.F_Fab, -4.5, -26.8, 4.5, -21.0, 0.1)
t = pcbnew.FP_TEXT(fp)
t.SetText("USB-C")
t.SetLayer(pcbnew.F_SilkS)
t.SetPosition(pcbnew.VECTOR2I(0, mm(-22.5)))
fp.Add(t)
fp.Reference().SetPosition(pcbnew.VECTOR2I(0, mm(-28)))
fp.Value().SetPosition(pcbnew.VECTOR2I(0, mm(28)))
lib = os.path.abspath(out)
pcbnew.FootprintSave(lib, fp)
print("saved", lib)
