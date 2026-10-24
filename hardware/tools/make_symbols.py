"""Writes ym2612.kicad_sym: the YM2612 and the Pimoroni Pico Plus 2 module. Run: python3 make_symbols.py ../ym2612_player/ym2612.kicad_sym"""


def pin(kind, x, y, angle, name, number, hidden=False):
    return (f'      (pin {kind} line (at {x} {y} {angle}) (length 2.54){" hide" if hidden else ""}\n'
            f'        (name "{name}" (effects (font (size 1.27 1.27))))\n'
            f'        (number "{number}" (effects (font (size 1.27 1.27))))\n      )\n')


def symbol(name, ref, value, desc, footprint, x1, y1, pins, fp_filter=""):
    return (f'  (symbol "{name}" (in_bom yes) (on_board yes)\n'
            f'    (property "Reference" "{ref}" (at {x1} {y1 + 2.54} 0)\n'
            f'      (effects (font (size 1.27 1.27)) (justify left))\n    )\n'
            f'    (property "Value" "{value}" (at {x1} {-y1 - 2.54} 0)\n'
            f'      (effects (font (size 1.27 1.27)) (justify left))\n    )\n'
            f'    (property "Footprint" "{footprint}" (at 0 0 0)\n'
            f'      (effects (font (size 1.27 1.27)) hide)\n    )\n'
            f'    (property "Datasheet" "" (at 0 0 0)\n'
            f'      (effects (font (size 1.27 1.27)) hide)\n    )\n'
            f'    (property "ki_description" "{desc}" (at 0 0 0)\n'
            f'      (effects (font (size 1.27 1.27)) hide)\n    )\n'
            f'    (symbol "{name}_0_1"\n'
            f'      (rectangle (start {x1} {y1}) (end {-x1} {-y1})\n'
            f'        (stroke (width 0.254) (type default))\n        (fill (type background))\n      )\n    )\n'
            f'    (symbol "{name}_1_1"\n{"".join(pins)}    )\n  )\n')


def ym2612():
    # Pinout checked against the VGMPF wiki: 1/12 GND, 2-9 D0-D7, 10 NC, 11 /IC, 13 /IRQ, 14 /CS, 15 /WR,
    # 16 /RD, 17 A0, 18 A1, 19 A.GND, 20 MOL, 21 MOR, 22 A.Vcc, 23 Vcc, 24 phiM.
    pins = []
    left = [("D0", 2), ("D1", 3), ("D2", 4), ("D3", 5), ("D4", 6), ("D5", 7), ("D6", 8), ("D7", 9),
            ("A0", 17), ("A1", 18), ("~{CS}", 14), ("~{WR}", 15), ("~{RD}", 16), ("~{IC}", 11), ("ΦM", 24)]
    for i, (n, num) in enumerate(left):
        kind = "bidirectional" if n.startswith("D") else "input"
        pins.append(pin(kind, -12.7, round(17.78 - 2.54 * i, 2), 0, n, num))
    right = [("MOL", 20, "output", 7.62), ("MOR", 21, "output", 5.08), ("~{IRQ}", 13, "open_collector", 0),
             ("NC", 10, "no_connect", -5.08)]
    for n, num, kind, y in right:
        pins.append(pin(kind, 12.7, y, 180, n, num))
    pins.append(pin("power_in", -2.54, 22.86, 270, "VCC", 23))
    pins.append(pin("power_in", 2.54, 22.86, 270, "A.VCC", 22))
    pins.append(pin("power_in", -5.08, -22.86, 90, "GND", 1))
    pins.append(pin("power_in", -2.54, -22.86, 90, "GND", 12))
    pins.append(pin("power_in", 2.54, -22.86, 90, "A.GND", 19))
    return symbol("YM2612", "U", "YM2612", "Yamaha OPN2 FM sound chip, 6 channels, DIP-24, 5V NMOS",
                  "Package_DIP:DIP-24_W15.24mm_Socket", -10.16, 20.32, pins)


def pico_plus2():
    gp = {0: 1, 1: 2, 2: 4, 3: 5, 4: 6, 5: 7, 6: 9, 7: 10, 8: 11, 9: 12, 10: 14, 11: 15, 12: 16, 13: 17,
          14: 19, 15: 20, 16: 21, 17: 22, 18: 24, 19: 25, 20: 26, 21: 27, 22: 29, 26: 31, 27: 32, 28: 34}
    pins = []
    for i in range(16):
        pins.append(pin("bidirectional", -17.78, round(27.94 - 2.54 * i, 2), 0, f"GP{i}", gp[i]))
    right = [16, 17, 18, 19, 20, 21, 22, 26, 27, 28]
    for i, g in enumerate(right):
        pins.append(pin("bidirectional", 17.78, round(27.94 - 2.54 * i, 2), 180, f"GP{g}", gp[g]))
    for i, (n, num, kind) in enumerate([("RUN", 30, "input"), ("ADC_VREF", 35, "passive"), ("3V3_EN", 37, "input")]):
        pins.append(pin(kind, 17.78, round(-2.54 - 2.54 * i, 2), 180, n, num))
    pins.append(pin("power_out", -5.08, 33.02, 270, "VBUS", 40))
    pins.append(pin("passive", 0, 33.02, 270, "VSYS", 39))
    pins.append(pin("power_out", 5.08, 33.02, 270, "3V3", 36))
    for k, num in enumerate([3, 8, 13, 18, 23, 28, 38]):
        pins.append(pin("power_in" if k == 0 else "passive", -2.54, -33.02, 90, "GND", num, hidden=k > 0))
    pins.append(pin("passive", 2.54, -33.02, 90, "AGND", 33))
    return symbol("PicoPlus2", "U", "Pimoroni Pico Plus 2",
                  "Pimoroni Pico Plus 2 (PIM724): RP2350B, 16 MB flash, 8 MB PSRAM, USB-C, Pico pinout. VBUS is the USB-C 5V.",
                  "ym2612:Pimoroni_PicoPlus2_SMD", -15.24, 30.48, pins)


def power(net, base="+5V"):
    """A power symbol for a rail KiCad's library doesn't have. In KiCad 7 the net name comes from the pin name."""
    import re
    text = open("/usr/share/kicad/symbols/power.kicad_sym").read()
    start = text.find(f'\n  (symbol "{base}"') + 1
    depth, i = 0, start
    while True:
        depth += {"(": 1, ")": -1}.get(text[i], 0)
        if depth == 0 and text[i] == ")":
            break
        i += 1
    blk = text[start:i + 1]
    blk = blk.replace(f'"{base}', f'"{net}')
    blk = re.sub(r'\(property "ki_description" "(?:[^"\\\\]|\\\\.)*"', f'(property "ki_description" "Power symbol creates a global label with name \\"{net}\\""', blk)
    return blk + "\n"


if __name__ == "__main__":
    import sys
    out = sys.argv[1]
    with open(out, "w") as f:
        f.write("(kicad_symbol_lib (version 20220914) (generator kicad_symbol_editor)\n")
        f.write(ym2612())
        f.write(pico_plus2())
        f.write(power("+5V_YM"))
        f.write(power("+4V5A"))
        f.write(")\n")
