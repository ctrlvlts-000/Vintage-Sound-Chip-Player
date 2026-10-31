"""Puts Joey's CTRLVLTS logo on the front silkscreen, above the button row, clear of the LCD and the chip window."""
import pcbnew

PCB = "../ym2612_player/ym2612_player.kicad_pcb"
b = pcbnew.LoadBoard(PCB)
if not any(isinstance(d, pcbnew.PCB_TEXT) and "CTRLVLTS" in d.GetText() for d in b.GetDrawings()):
    t = pcbnew.PCB_TEXT(b)
    t.SetText("[-] CTRLVLTS [+]")
    t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(157), pcbnew.FromMM(128)))
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(2.2), pcbnew.FromMM(2.2)))
    t.SetTextThickness(pcbnew.FromMM(0.33))
    b.Add(t)
    b.Save(PCB)
print("logo on F.Silkscreen")
