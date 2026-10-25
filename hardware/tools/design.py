"""The YM2612 player Rev A schematic, described part by part. Run: python3 design.py ../ym2612_player"""
import os
import sys

from kigen import Project, Sheet

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "ym2612_player")
LOCAL = {"ym2612": os.path.join(OUT, "ym2612.kicad_sym")}

P = Project(LOCAL)

R, C, CP = "Device:R", "Device:C", "Device:C_Polarized"
FLAG = "power:PWR_FLAG"

# Footprints. Passives are 0603 unless noted, so PCBWay can fit any equivalent generic part.
FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0603_1608Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_CP5 = "Capacitor_SMD:CP_Elec_5x5.4"
FP_CP6 = "Capacitor_SMD:CP_Elec_6.3x7.7"
FP_FB = "Inductor_SMD:L_0603_1608Metric"


def f(fp, mpn="", spec=""):
    d = {"Footprint": fp}
    if mpn:
        d["MPN"] = mpn
    if spec:
        d["Spec"] = spec
    return d


def res(sh, value, x, y, a, b, sideways=False, spec="1%, 0603", dnp=False):
    return sh.add(R, "R", value, x, y, {"1": a, "2": b}, rot=90 if sideways else 0, fields=f(FP_R, spec=spec), dnp=dnp)


# Where layout.py must put each decoupling capacitor: cap ref -> (chip ref, pin). Parts that only touch power nets
# have nothing else to tell the placer where they belong.
NEAR = {}


def cap(sh, value, x, y, top, bottom="GND", polar=False, fp=None, spec="", sideways=False, mpn="", near=None):
    lib = CP if polar else C
    if fp is None:
        fp = FP_CP5 if polar else FP_C
    if not spec:
        spec = "electrolytic, 16V" if polar else ("X7R, 16V" if "n" in value else "X5R/X7R, 16V")
    c = sh.add(lib, "C", value, x, y, {"1": top, "2": bottom}, rot=90 if sideways else 0,
               fields=f(fp, mpn=mpn, spec=spec))
    if near:
        NEAR[c.ref] = near
    return c


def flag(sh, x, y, net):
    sh.add(FLAG, "#FLG", "PWR_FLAG", x, y, {"1": net})


# =============================================================== power
pw = Sheet(P, "power.kicad_sch", "Power", paper="A4")
fb_ym = pw.add("Device:FerriteBead", "FB", "220R@100MHz", 81.28, 63.5, {"1": "+5V", "2": "+5V_YM"}, rot=90,
               fields=f(FP_FB, "BLM18PG221SN1D", "ferrite bead, 0603, 1A+"))
cap(pw, "47uF", 109.22, 71.12, "+5V_YM", polar=True, near=("FB1", "2"))
cap(pw, "100nF", 121.92, 71.12, "+5V_YM", near=("FB1", "2"))
flag(pw, 137.16, 55.88, "+5V_YM")
cap(pw, "47uF", 50.8, 71.12, "+5V", polar=True, near=("U2", "40"))

pw.add("Device:FerriteBead", "FB", "220R@100MHz", 71.12, 104.14, {"1": "+5V", "2": "VA_RAW"}, rot=90,
       fields=f(FP_FB, "BLM18PG221SN1D", "ferrite bead, 0603, 1A+"))
pw.add("Device:L", "L", "10uH", 109.22, 104.14, {"1": "VA_RAW", "2": "VA_IN"}, rot=90,
       fields=f("Inductor_SMD:L_1210_3225Metric", "LQH32CN100K53L", "10uH, 1210, 300mA+"))
cap(pw, "22uF", 137.16, 114.3, "VA_IN", fp=FP_C0805, spec="X5R, 10V, 0805", near=("U1", "1"))
# The electrolytic's own resistance damps the 10uH / 22uF resonance (it peaked +6 dB at 15 kHz without it).
cap(pw, "47uF", 160.02, 114.3, "VA_IN", polar=True, near=("U1", "1"))
pw.add("Regulator_Linear:LP5907MFX-4.5", "U", "LP5907MFX-4.5", 182.88, 106.68,
       {"1": "VA_IN", "3": "VA_IN", "2": "GND", "4": "NC", "5": "+4V5A"},
       fields=f("Package_TO_SOT_SMD:SOT-23-5", "LP5907MFX-4.5/NOPB", "low-noise LDO, 4.5V, 250mA"))
cap(pw, "4.7uF", 213.36, 114.3, "+4V5A", fp=FP_C0805, spec="X5R, 10V, 0805", near=("U1", "5"))
cap(pw, "47uF", 228.6, 114.3, "+4V5A", polar=True, near=("U1", "5"))
flag(pw, 152.4, 86.36, "VA_IN")

flag(pw, 88.9, 147.32, "GND")
for i in range(4):
    pw.add("Mechanical:MountingHole", "H", "M3", 50.8 + i * 15.24, 175.26, {}, fields=f("MountingHole:MountingHole_3.2mm_M3"))
for i in range(4):  # the LCD module's four standoffs
    pw.add("Mechanical:MountingHole", "H", "M3 (LCD)", 127 + i * 15.24, 175.26, {}, fields=f("MountingHole:MountingHole_3.2mm_M3"))
pw.text(25.4, 22.86,
        "POWER: everything runs from the Pico Plus 2's own USB-C port (VBUS, 5V, up to 500 mA from a computer).\n"
        "+5V     = VBUS from the Pico (pin 40). Feeds the LCD, backlight, window LEDs.\n"
        "+5V_YM  = +5V through a ferrite: YM2612 and the two 74HCT541 buffers.\n"
        "+4V5A   = quiet analog rail: ferrite + 10uH/22uF+47uF filter + LP5907 4.5V low-noise LDO. Op-amps and headphone amp.\n"
        "+3V3    = made by the regulator on the Pico board.\n"
        "GND is one solid plane on both layers. The audio parts are grouped on the left, away from USB and the LCD,\n"
        "so digital return currents don't flow under them. (A split ground put the YM2612 bus over the audio ground.)", size=1.5)
pw.text(25.4, 160.02, "Mounting holes: M3, positions set by the enclosure. H5-H8 hold the LCD module's standoffs.", size=1.5)

# =============================================================== controller
mc = Sheet(P, "controller.kicad_sch", "Controller")
pico = {
    "1": "MCU_D0", "2": "MCU_D1", "4": "MCU_D2", "5": "MCU_D3", "6": "MCU_D4", "7": "MCU_D5", "9": "MCU_D6",
    "10": "MCU_D7", "11": "MCU_A0", "12": "MCU_A1", "14": "MCU_WR", "15": "MCU_IC", "16": "HP_EN",
    "17": "SPARE_GP13", "19": "I2C_SDA", "20": "I2C_SCL",
    "21": "BTN_PLAY", "22": "BTN_STOP", "24": "BTN_LEFT", "25": "BTN_RIGHT", "26": "BTN_EDIT", "27": "MCU_CLK",
    "29": "BTN_EXIT", "31": "BTN_WRITE", "32": "ENC_A", "34": "ENC_B",
    "30": "NC", "35": "NC", "37": "NC", "39": "NC", "40": "+5V", "36": "+3V3", "33": "GND",
}
for g in ["3", "8", "13", "18", "23", "28", "38"]:
    pico[g] = "GND"
mc.add("ym2612:PicoPlus2", "U", "Pimoroni Pico Plus 2", 165.1, 139.7, pico,
       fields=f("ym2612:Pimoroni_PicoPlus2_Socketed", "PIM724",
                "Joey supplies the Pico Plus 2 and solders 2x 20-pin male headers to it; it plugs into sockets U2-SKT"),
       dnp=True)
cap(mc, "10uF", 241.3, 88.9, "+3V3", fp=FP_C0805, spec="X5R, 10V, 0805", near=("U2", "36"))
cap(mc, "100nF", 254, 88.9, "+3V3", near=("U2", "36"))
# Keep the YM2612 quiet while the Pico boots: /IC held low (reset), /WR high, address lines low.
# The pull-downs are 4.7k because of RP2350 erratum E9: a released pin can sit near 2.2 V unless an external
# pull-down of 8.2k or less holds it.
res(mc, "10k", 241.3, 190.5, "+3V3", "MCU_WR")
res(mc, "4.7k", 254, 190.5, "MCU_IC", "GND")
res(mc, "4.7k", 266.7, 190.5, "MCU_A0", "GND")
res(mc, "4.7k", 279.4, 190.5, "MCU_A1", "GND")
# Spare pins and test points.
mc.add("Connector_Generic:Conn_01x04", "J", "Spare GPIO (not fitted)", 81.28, 205.74,
       {"1": "+3V3", "2": "HP_EN", "3": "SPARE_GP13", "4": "GND"},
       fields=f("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"), dnp=True)
tps = ["MCU_D0", "MCU_D1", "MCU_D2", "MCU_D3", "MCU_D4", "MCU_D5", "MCU_D6", "MCU_D7",
       "MCU_A0", "MCU_A1", "MCU_WR", "MCU_IC", "YM_CLK", "GND", "GND"]
for i, net in enumerate(tps):
    mc.add("Connector:TestPoint", "TP", net.replace("MCU_", ""), 297.18 + (i % 5) * 20.32, 76.2 + (i // 5) * 33.02,
           {"1": net}, fields=f("TestPoint:TestPoint_Pad_D1.5mm"))
mc.text(25.4, 25.4,
        "CONTROLLER: Pimoroni Pico Plus 2 (RP2350, 16 MB flash, 8 MB PSRAM, USB-C). It has parts underneath, so it plugs into two 20-pin sockets.\n"
        "Its USB-C port is the player's only power and data connector: put it on the rear edge of the board.\n"
        "Pin plan (from docs/DESIGN.md 5.4)\n"
        "  GP0-GP7  YM2612 data D0-D7 (PIO, must stay in order)    GP8, GP9  A0, A1    GP10 /WR    GP11 /IC (reset)\n"
        "  GP21     7.67 MHz chip clock (GPOUT0: 153.33 MHz / 20)\n"
        "  GP14, GP15  I2C1 SDA / SCL to the LCD (through the level shifter on the Front panel page)\n"
        "  GP16 Play  GP17 Stop  GP18 Left  GP19 Right  GP20 Edit  GP22 Exit  GP26 Write   (buttons to GND, internal pull-ups)\n"
        "  GP27, GP28  data knob A / B\n"
        "  GP12     headphone amp enable (high = on), also on J1    GP13  spare, on J1 (not fitted)\n"
        "/RD is tied high and /CS low at the chip, so the bus only ever writes.", size=1.5)
mc.text(228.6, 220.98,
        "Boot-time pulls: until the firmware starts, these hold the\nYM2612 in reset and keep /WR idle. 4.7k pull-downs: RP2350 erratum E9.", size=1.5)
mc.text(292.1, 60.96, "Test points for the logic analyzer (milestone M1)", size=1.5)

# =============================================================== sound chip
sc = Sheet(P, "sound_chip.kicad_sch", "Sound chip")
# Data bus: 74HCT541 at 5V. Its TTL-level inputs read the Pico's 3.3V as high and drive full 5V out.
b1 = {"1": "GND", "19": "GND", "10": "GND", "20": "+5V_YM"}
for i in range(8):
    b1[str(2 + i)] = f"MCU_D{i}"
    b1[str(18 - i)] = f"YMB_D{i}"
sc.add("74xx:74HCT541", "U", "74HCT541", 76.2, 81.28, b1,
       fields=f("Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm", "74HCT541D,653", "octal buffer, HCT, SOIC-20"))
for i in range(8):
    res(sc, "100", 127, 58.42 + i * 7.62, f"YMB_D{i}", f"YM_D{i}", sideways=True)
b2 = {"1": "GND", "19": "GND", "10": "GND", "20": "+5V_YM",
      "2": "MCU_A0", "3": "MCU_A1", "4": "MCU_WR", "5": "MCU_IC", "6": "MCU_CLK", "7": "GND", "8": "GND", "9": "GND",
      "18": "YMB_A0", "17": "YMB_A1", "16": "YMB_WR", "15": "YMB_IC", "14": "YMB_CLK", "13": "NC", "12": "NC", "11": "NC"}
sc.add("74xx:74HCT541", "U", "74HCT541", 76.2, 165.1, b2,
       fields=f("Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm", "74HCT541D,653", "octal buffer, HCT, SOIC-20"), stagger=True)
for i, s in enumerate(["A0", "A1", "WR", "IC"]):
    res(sc, "100", 127, 147.32 + i * 7.62, f"YMB_{s}", f"YM_{s}", sideways=True)
# Clock: fit R14 for the Pico's clock (default) or R15 + X1 for an oscillator can. Never both.
res(sc, "33", 127, 182.88, "YMB_CLK", "YM_CLK", sideways=True)
res(sc, "33", 127, 213.36, "OSC_OUT", "YM_CLK", sideways=True, dnp=True)
sc.add("Oscillator:CXO_DIP8", "X", "7.670454 MHz, 5V (not fitted)", 81.28, 220.98,
       {"1": "+5V_YM", "4": "GND", "5": "OSC_OUT", "8": "+5V_YM"},
       fields=f("Oscillator:Oscillator_DIP-8", "", "half-size DIP-8 oscillator can, 5V CMOS, 7.670454 MHz"), dnp=True)
# The chip, in a turned-pin socket. Joey fits the YM2612.
ym = {"2": "YM_D0", "3": "YM_D1", "4": "YM_D2", "5": "YM_D3", "6": "YM_D4", "7": "YM_D5", "8": "YM_D6", "9": "YM_D7",
      "17": "YM_A0", "18": "YM_A1", "14": "GND", "15": "YM_WR", "16": "+5V_YM", "11": "YM_IC", "24": "YM_CLK",
      "20": "YM_MOL", "21": "YM_MOR", "13": "NC", "10": "NC",
      "23": "+5V_YM", "22": "YM_AVCC", "1": "GND", "12": "GND", "19": "GND"}
sc.add("ym2612:YM2612", "U", "YM2612 (socket only, chip fitted by hand)", 200.66, 111.76, ym,
       fields=f("Package_DIP:DIP-24_W15.24mm_Socket", "110-43-624-41-001000",
                "Mill-Max 24-pin 600 mil turned-pin DIP socket. PCBWay fits the socket only."), stagger=True)
# Window lights: two warm-white 3 mm LEDs, about 5 mA each, always on.
for i in range(2):
    res(sc, "430", 279.4 + i * 20.32, 76.2, "+5V", f"LED_WIN{i + 1}")
    sc.add("Device:LED", "D", "warm white 3 mm", 279.4 + i * 20.32, 111.76, {"2": f"LED_WIN{i + 1}", "1": "GND"}, rot=90,
           fields=f("LED_THT:LED_D3.0mm", "LED3WAW", "3 mm through-hole LED, warm white 2800K, 3.2V. Any 3 mm warm white will do. Order note for PCBWay: do not trim the leads, Joey bends them to aim the light"))
for i, near in enumerate([("U3", "20"), ("U4", "20"), ("U5", "23"), ("X1", "8")]):
    cap(sc, "100nF", 266.7 + i * 12.7, 180.34, "+5V_YM", near=near)
cap(sc, "10uF", 330.2, 180.34, "+5V_YM", fp=FP_C0805, spec="X5R, 16V, 0805", near=("U5", "23"))
# The chip's DAC supply (A.VCC, pin 22) gets its own RC filter: USB noise on +5V_YM would otherwise reach the audio.
res(sc, "10", 355.6, 165.1, "+5V_YM", "YM_AVCC", sideways=True, spec="1%, 0603 (A.VCC filter)")
cap(sc, "220uF", 368.3, 180.34, "YM_AVCC", polar=True, fp=FP_CP6, near=("U5", "22"))
cap(sc, "100nF", 381, 180.34, "YM_AVCC", near=("U5", "22"))
sc.text(25.4, 22.86,
        "SOUND CHIP: the YM2612 and the 3.3V to 5V buffers\n"
        "Two 74HCT541 buffers at 5V turn the Pico's 3.3V signals into solid 5V. 100 ohm resistors on every chip pin protect the YM2612.\n"
        "The bus is write-only: /RD is tied high and /CS low, so the chip listens whenever /WR pulses. /IRQ is not used.\n"
        "Clock: the Pico makes 7.667 MHz on GP21 and the buffer lifts it to 5V (its 33 ohm resistor is fitted). For exact Genesis pitch,\n"
        "fit a 7.670454 MHz 5V oscillator can in X1 and its 33 ohm resistor, and leave out the buffer's 33 ohm.\n"
        "Window lights: D1 and D2 sit beside the socket, angled across the chip, so its markings catch the light.", size=1.5)
sc.text(261.62, 193.04,
        "Decoupling: one 100nF at each 74HCT541, one at YM2612 VCC (pin 23) with 10uF bulk, one for X1.\n"
        "A.VCC (pin 22): 10 ohm + 220uF + 100nF filter, placed at pins 22 and 19.", size=1.5)

# =============================================================== audio
au = Sheet(P, "audio.kicad_sch", "Audio out", paper="A2")
# Per channel: 2.2k load (as in the Mega Amp), AC coupling, then an inverting low-pass that copies the
# Model 1 output filter: 47k in, 100k || 470pF feedback = first order at 3.39 kHz, gain about 2.1.
# Cold leg = filter out, hot leg = filter out inverted again, so hot has the chip's own polarity.
OPA = f("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "OPA2350UA", "dual rail-to-rail op-amp, 2.7-5.5V")
TPA = f("Package_DFN_QFN:WQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm", "TPA6132A2RTER",
        "TI DirectPath stereo headphone amp, 2.3-5.5V, WQFN-16 3x3 mm (RTE)")
# The dual slide pot either solders to the board (needs Bourns's footprint) or sits in the case top and plugs into a 6-pin header.
SLIDER_ON_BOARD = False
POT = f("", "PTA2044-2015DPA103",
        "Bourns 20 mm travel dual-gang slide pot, 10k audio taper, 15 mm metal lever. Footprint still to draw.")
for side, ch, mo, y0 in [(0, "L", "YM_MOL", 110.49), (1, "R", "YM_MOR", 270.51)]:
    filt_u, inv_u = ("U6", 1), ("U7", 1)
    if side:
        filt_u, inv_u = ("U6", 2), ("U7", 2)
    res(au, "2.2k", 35.56, y0 + 12.7, mo, "GND")
    cap(au, "1uF", 60.96, y0, mo, f"F{ch}_IN", sideways=True, fp="Capacitor_SMD:C_1206_3216Metric",
        spec="X7R, 50V, 1206")
    res(au, "47k", 96.52, y0, f"F{ch}_IN", f"F{ch}_SUM", sideways=True)
    res(au, "100k", 139.7, y0 - 15.24, f"F{ch}_SUM", f"COLD_{ch}", sideways=True)
    cap(au, "470pF", 139.7, y0 - 25.4, f"F{ch}_SUM", f"COLD_{ch}", sideways=True, spec="C0G, 50V")
    pins = {"2": f"F{ch}_SUM", "3": "VREF", "1": f"COLD_{ch}"} if not side else {"6": f"F{ch}_SUM", "5": "VREF", "7": f"COLD_{ch}"}
    au.add("Amplifier_Operational:OPA2340", "U", "OPA2350UA", 139.7, y0, pins, unit=filt_u[1], ref=filt_u[0], fields=OPA)
    # Inverter for the hot leg.
    res(au, "10k", 180.34, y0 + 20.32, f"COLD_{ch}", f"INV_{ch}", sideways=True)
    res(au, "10k", 223.52, y0 + 5.08, f"INV_{ch}", f"HOT_{ch}", sideways=True)
    pins = {"2": f"INV_{ch}", "3": "VREF", "1": f"HOT_{ch}"} if not side else {"6": f"INV_{ch}", "5": "VREF", "7": f"HOT_{ch}"}
    au.add("Amplifier_Operational:OPA2340", "U", "OPA2350UA", 223.52, y0 + 20.32, pins, unit=inv_u[1], ref=inv_u[0], fields=OPA)
    # Balanced outputs: 100 ohm + DC block + bleed, onto a 1/4" TRS jack.
    for k, leg in enumerate(["HOT", "COLD"]):
        yy = y0 + 45.72 + k * 20.32
        res(au, "100", 256.54, yy, f"{leg}_{ch}", f"{leg}_{ch}_R", sideways=True)
        au.add(CP, "C", "10uF", 289.56, yy, {"1": f"{leg}_{ch}_R", "2": f"{leg}_{ch}_OUT"}, rot=90,
               fields=f(FP_CP5, spec="electrolytic, 16V, low-leakage"))
        res(au, "100k", 322.58 + k * 17.78, yy + 10.16, f"{leg}_{ch}_OUT", "GND")
    au.add("Connector_Audio:AudioJack3_SwitchTR", "J", f'1/4" TRS balanced out {ch}', 388.62, y0 + 55.88,
           {"T": f"HOT_{ch}_OUT", "R": f"COLD_{ch}_OUT", "S": f"SLEEVE_{ch}", "TN": "NC", "RN": "NC"},
           fields=f("Connector_Audio:Jack_6.35mm_Neutrik_NMJ6HCD2_Horizontal", "NMJ6HCD2",
                    "Neutrik 1/4in stereo jack, horizontal PCB. The footprint's SN pad is left unconnected."))
    # Ground-lift footprint: fit 0 ohm. If an interface hums, try 10 ohm here (milestone M4).
    res(au, "0", 363.22, y0 + 86.36, f"SLEEVE_{ch}", "GND", sideways=True, spec="0 ohm, 0603 (ground lift option)")
    # Headphones: DC block, volume slider (headphones only), 1uF into the TPA6132A2's inverting input.
    yh = y0 - 48.26
    au.add(CP, "C", "10uF", 175.26, yh, {"1": f"COLD_{ch}", "2": f"VOL_{ch}_IN"}, rot=90,
           fields=f(FP_CP5, spec="electrolytic, 16V"))
    gang = {"1": "VOL_L_IN", "2": "VOL_L_W", "3": "GND"} if not side else {"4": "VOL_R_IN", "5": "VOL_R_W", "6": "GND"}
    if SLIDER_ON_BOARD:
        au.add("Device:R_Potentiometer_Dual_Separate", "RV", "10k audio, dual slide", 205.74, yh, gang, unit=1 + side,
               ref="RV1", fields=POT)
    cap(au, "1uF", 243.84, yh, f"VOL_{ch}_W", f"HP_{ch}_IN", sideways=True, fp="Capacitor_SMD:C_1206_3216Metric",
        spec="X7R, 25V, 1206")
# TPA6132A2 headphone amp on the quiet 4.5V rail. Its outputs sit at 0V (charge pump), so no output capacitors.
# Gain -6 dB (G0 = G1 = low): the filter's full 4.3 Vpp in gives 2.15 Vpp out, inside its swing into 32 ohm.
# EN comes from GP12, held low by 4.7k until the firmware turns the amp on, after the audio rail has settled (no pop).
tpa = {"1": "HP_L_IN", "2": "GND", "3": "GND", "4": "HP_R_IN", "5": "PHONE_R", "6": "GND", "7": "GND",
       "8": "HPVSS", "9": "HP_CPN", "10": "GND", "11": "HP_CPP", "12": "HPVDD", "13": "HP_EN", "14": "+4V5A",
       "15": "GND", "16": "PHONE_L", "17": "GND"}
au.add("Amplifier_Audio:TPA6132A2RTE", "U", "TPA6132A2RTER", 480.06, 101.6, tpa, ref="U8", fields=TPA)
P.counters["U"] = 8
cap(au, "2.2uF", 457.2, 139.7, "+4V5A", fp=FP_C0805, spec="X5R, 10V, 0805", near=("U8", "14"))
cap(au, "100nF", 469.9, 139.7, "+4V5A", near=("U8", "14"))
cap(au, "2.2uF", 482.6, 139.7, "HPVDD", fp=FP_C0805, spec="X5R, 10V, 0805", near=("U8", "12"))
cap(au, "2.2uF", 495.3, 139.7, "HPVSS", fp=FP_C0805, spec="X5R, 10V, 0805", near=("U8", "8"))
cap(au, "1uF", 508, 139.7, "HP_CPP", "HP_CPN", fp=FP_C0805, spec="X5R, 10V, 0805 (charge-pump flying cap)", near=("U8", "11"))
res(au, "4.7k", 520.7, 139.7, "HP_EN", "GND")
flag(au, 482.6, 154.94, "HPVDD")
flag(au, 495.3, 154.94, "HPVSS")
if not SLIDER_ON_BOARD:
    au.add("Connector_Generic:Conn_01x06", "J", "Volume slider (dual 10k audio taper, in the case)", 205.74, 160.02,
           {"1": "VOL_L_IN", "2": "VOL_L_W", "3": "GND", "4": "VOL_R_IN", "5": "VOL_R_W", "6": "GND"},
           fields=f("Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical", "B6B-XH-A(LF)(SN)",
                    "JST XH 6-pin header. Wire a dual 10k audio-taper slide pot: L top/wiper/bottom on 1-3, R on 4-6."),
           stagger=True)
au.add("Connector_Audio:AudioJack3", "J", "3.5 mm headphones (front)", 426.72, 101.6,
       {"T": "PHONE_L", "R": "PHONE_R", "S": "GND"},
       fields=f("Connector_Audio:Jack_3.5mm_CUI_SJ1-3523N_Horizontal", "SJ1-3523N", "CUI 3.5 mm stereo jack, horizontal"))
au.add("Amplifier_Operational:OPA2340", "U", "OPA2350UA", 60.96, 375.92, {"8": "+4V5A", "4": "GND"}, unit=3, ref="U6", fields=OPA)
au.add("Amplifier_Operational:OPA2340", "U", "OPA2350UA", 81.28, 375.92, {"8": "+4V5A", "4": "GND"}, unit=3, ref="U7", fields=OPA)
for i, near in enumerate([("U6", "8"), ("U7", "8")]):
    cap(au, "100nF", 124.46 + i * 12.7, 375.92, "+4V5A", near=near)
cap(au, "10uF", 162.56, 375.92, "+4V5A", fp=FP_C0805, spec="X5R, 10V, 0805", near=("U7", "8"))
# Mid-rail reference (2.25V), heavily filtered. Only high-impedance inputs use it.
res(au, "10k", 220.98, 365.76, "+4V5A", "VREF")
res(au, "10k", 220.98, 391.16, "VREF", "GND")
cap(au, "47uF", 236.22, 375.92, "VREF", "GND", polar=True)
cap(au, "100nF", 248.92, 375.92, "VREF", "GND")
au.text(25.4, 20.32,
        "AUDIO OUT (authentic Model 1 sound, no clean mode). Everything here runs on the quiet +4V5A rail around VREF = 2.25V.\n"
        "1. 2.2k load on MOL / MOR, as in the Mega Amp, so the chip's DAC works as it did in the console.\n"
        "2. Model 1 style low-pass: inverting OPA2350 stage, 47k in, 100k || 470pF feedback. First order, 3.39 kHz, gain about 2.1.\n"
        "   That matches the 47k / 1nF Model 1 filter used by MIDIbox. Change C to 560pF for 2.84 kHz (the VA3 knee) after the A/B test in M4.\n"
        "3. Balanced line outs: cold = filter out, hot = filter out inverted again by a 10k / 10k OPA2350 stage. 100 ohm + 10uF + 100k bleed\n"
        "   on each leg into a Neutrik 1/4in TRS (tip hot, ring cold, sleeve to GND through a 0 ohm ground-lift footprint).\n"
        "4. Headphones: 10uF DC block, dual slide pot on its 6-pin plug (volume, headphones only), 1uF into a TPA6132A2 at -6 dB gain.\n"
        "   Its outputs are ground-centred, so they go straight to the front 3.5 mm jack. GP12 (HP_EN) mutes it until the rail settles.", size=1.5)

# =============================================================== front panel
fp = Sheet(P, "panel.kicad_sch", "Front panel")
buttons = [("BTN_PLAY", "Play (red cap)"), ("BTN_STOP", "Stop"), ("BTN_LEFT", "Left"), ("BTN_RIGHT", "Right"),
           ("BTN_EDIT", "Edit"), ("BTN_EXIT", "Exit"), ("BTN_WRITE", "Write")]
for i, (net, name) in enumerate(buttons):
    fp.add("Switch:SW_Push", "SW", name, 45.72 + i * 22.86, 83.82, {"1": net, "2": "GND"}, rot=270,
           fields=f("Button_Switch_THT:SW_PUSH-12mm", "B3F-4055",
                    "Omron 12 mm tactile switch, 7.3 mm tall, with a B32-series snap-on round cap"))
fp.add("Device:RotaryEncoder", "SW", "Data knob", 66.04, 147.32, {"A": "ENC_A", "B": "ENC_B", "C": "GND"}, rot=90,
       fields=f("Rotary_Encoder:RotaryEncoder_Alps_EC11E_Vertical_H20mm", "PEC11R-4215F-N0024",
                "Bourns 24-step encoder, no push switch, 15 mm shaft (EC11 footprint)"), stagger=True)
res(fp, "10k", 114.3, 139.7, "+3V3", "ENC_A")
res(fp, "10k", 127, 139.7, "+3V3", "ENC_B")
cap(fp, "10nF", 114.3, 160.02, "ENC_A")
cap(fp, "10nF", 127, 160.02, "ENC_B")
# I2C level shifter: two BSS138 MOSFETs. 3.3V side on the Pico, 5V side to the LCD backpack.
for i, (lo, hi) in enumerate([("I2C_SDA", "LCD_SDA"), ("I2C_SCL", "LCD_SCL")]):
    x = 220.98 + i * 40.64
    fp.add("Transistor_FET:BSS138", "Q", "BSS138", x, 91.44, {"1": "+3V3", "2": lo, "3": hi}, rot=90,
           fields=f("Package_TO_SOT_SMD:SOT-23", "BSS138", "N-MOSFET, SOT-23"))
    res(fp, "4.7k", x - 12.7, 106.68, "+3V3", lo)
    res(fp, "4.7k", x + 12.7, 106.68, "+5V", hi)
fp.add("Connector_Generic:Conn_01x04", "J", "LCD (I2C backpack: GND, VCC, SDA, SCL)", 264.16, 147.32,
       {"1": "GND", "2": "+5V", "3": "LCD_SDA", "4": "LCD_SCL"},
       fields=f("Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", "B4B-XH-A(LF)(SN)", "JST XH 4-pin header"), stagger=True)
cap(fp, "10uF", 299.72, 147.32, "+5V", fp=FP_C0805, spec="X5R, 10V, 0805", near=("J6", "2"))
cap(fp, "100nF", 312.42, 147.32, "+5V", near=("J6", "2"))
fp.text(25.4, 25.4,
        "FRONT PANEL: 7 buttons, data knob, LCD connector\n"
        "Buttons: 12 mm tactile switches with snap-on caps (Joey, Oct 24). Each shorts its Pico pin to GND; the Pico's pull-ups are on.\n"
        "Data knob: turn-only encoder with 10k pull-ups and 10nF filters for clean steps.\n"
        "LCD: HiLetgo 20x4 HD44780 blue LCD with a PCF8574 I2C backpack, 5V, address 0x27 (or 0x3F).\n"
        "The LCD connector's pin order matches the backpack's GND, VCC, SDA, SCL. Make a short 4-wire cable, JST XH to Dupont.\n"
        "The BSS138 pair shifts I2C between the Pico's 3.3V and the backpack's 5V. Keep the LCD cable away from the audio corner.", size=1.5)

if __name__ == "__main__":
    probs = P.check()
    for p in probs:
        print("PROBLEM:", p)
    P.root_notes = ("How to read this schematic\n"
                    "Each box is a page. Wires end in name tags (labels): any two tags with the same name are connected,\n"
                    "even on different pages. The symbols marked +5V, +5V_YM, +4V5A, +3V3 and GND are power connections.\n"
                    "Parts marked DNP are not fitted by PCBWay. Pages: Power > Controller > Sound chip > Audio out > Front panel.")
    P.write(OUT)
    print("wrote", OUT, "problems:", len(probs))
