"""The Chip Shrine schematic, described part by part. Run: python3 design.py ../chip_shrine"""
import os
import sys

from kigen import Project, Sheet

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "chip_shrine")
LOCAL = {"chip_shrine": os.path.join(OUT, "chip_shrine.kicad_sym")}

P = Project(LOCAL)

R, C, CP = "Device:R", "Device:C", "Device:C_Polarized"
FLAG = "power:PWR_FLAG"


def r_series(sh, value, x, y, a, b):
    """Resistor drawn sideways between two signals: pin 1 on the left."""
    return sh.add(R, "R", value, x, y, {"1": a, "2": b}, rot=90)


def r_pull(sh, value, x, y, top, bottom):
    return sh.add(R, "R", value, x, y, {"1": top, "2": bottom})


def cap(sh, value, x, y, top, bottom="GND", polar=False):
    return sh.add(CP if polar else C, "C", value, x, y, {"1": top, "2": bottom})


def decouple_row(sh, x, y, items, step=12.7):
    for i, (value, net, polar) in enumerate(items):
        cap(sh, value, x + i * step, y, net, polar=polar)


# =============================================================== power
pw = Sheet(P, "power.kicad_sch", "Power", paper="A4")
pw.add("Connector:USB_C_Receptacle_PowerOnly_6P", "J", "USB-C power in (5V, 3A)", 45.72, 80.01,
       {"A9": "VBUS_IN", "B9": "VBUS_IN", "A12": "GND", "B12": "GND", "A5": "CC1", "B5": "CC2", "S1": "GND"})
r_pull(pw, "5.1k", 88.9, 110.49, "CC1", "GND")
r_pull(pw, "5.1k", 101.6, 110.49, "CC2", "GND")
pw.add("Device:Polyfuse", "F", "PTC fuse 3A hold", 116.84, 72.39, {"1": "VBUS_IN", "2": "+5V"}, rot=90)
cap(pw, "220uF", 139.7, 87.63, "+5V", polar=True)
pw.add(FLAG, "#FLG", "PWR_FLAG", 139.7, 69.85, {"1": "+5V"})
pw.add(FLAG, "#FLG", "PWR_FLAG", 154.94, 101.6, {"1": "GND"})
pw.add("Device:D_Schottky", "D", "1N5817", 175.26, 72.39, {"1": "VSYS", "2": "+5V"})
pw.add(FLAG, "#FLG", "PWR_FLAG", 196.85, 62.23, {"1": "VSYS"})
pw.add("Device:FerriteBead", "FB", "Ferrite bead 600R@100MHz", 175.26, 115.57, {"1": "+5V", "2": "+5VA"}, rot=90)
cap(pw, "100uF", 205.74, 128.27, "+5VA", polar=True)
cap(pw, "100nF", 218.44, 128.27, "+5VA")
pw.add(FLAG, "#FLG", "PWR_FLAG", 205.74, 107.95, {"1": "+5VA"})
pw.text(25.4, 25.4,
        "POWER\n"
        "USB-C in, 5V. The two 5.1k resistors on CC tell the charger to send 5V.\n"
        "Use a 5V 3A USB-C supply: the LED grid can pull a lot of current (firmware caps brightness).\n"
        "+5V   = digital 5V and LEDs (straight from USB through the fuse)\n"
        "+5VA  = quiet 5V for the YM2612 and the audio circuit (through a ferrite bead)\n"
        "VSYS  = feeds the Pico through a diode, so plugging USB into the Pico for\n"
        "        programming and the main USB-C at the same time is safe\n"
        "+3V3  = made by the regulator on the Pico board (see Controller page)\n"
        "All grounds are one net. On protoboard, run the audio ground and the LED ground\n"
        "as separate wires back to the USB-C connector (star ground).", size=1.5)

# =============================================================== controller
mc = Sheet(P, "controller.kicad_sch", "Controller")
pico = {
    "1": "MCU_D0", "2": "MCU_D1", "4": "MCU_D2", "5": "MCU_D3", "6": "MCU_D4", "7": "MCU_D5", "9": "MCU_D6",
    "10": "MCU_D7", "11": "MCU_A0", "12": "MCU_A1", "14": "MCU_WR", "15": "MCU_RD", "16": "MCU_IC",
    "17": "ADC_CS", "19": "SPI1_SCK", "20": "SPI1_MOSI",
    "21": "SD_MISO", "22": "SD_CS", "24": "SD_SCK", "25": "SD_MOSI", "26": "I2C_SDA", "27": "I2C_SCL",
    "29": "LCD_CS", "31": "LCD_DC", "32": "LED_DATA", "34": "SPI1_MISO",
    "30": "NC", "35": "NC", "37": "NC", "40": "NC", "39": "VSYS", "36": "+3V3",
}
for g in ["3", "8", "13", "18", "23", "28", "33", "38"]:
    pico[g] = "GND"
mc.add("chip_shrine:Pico2_Module", "U", "Pico Plus 2 (RP2350 + PSRAM)", 165.1, 139.7, pico)
r_pull(mc, "4.7k", 241.3, 77.47, "+3V3", "I2C_SDA")
r_pull(mc, "4.7k", 254, 77.47, "+3V3", "I2C_SCL")
cap(mc, "10uF", 279.4, 77.47, "+3V3", polar=True)
cap(mc, "100nF", 292.1, 77.47, "+3V3")
# Keep the sound chip idle while the Pico boots: /WR and /RD high, /IC low (held in reset), A0/A1 low.
r_pull(mc, "10k", 241.3, 200.66, "+3V3", "MCU_WR")
r_pull(mc, "10k", 254, 200.66, "+3V3", "MCU_RD")
r_pull(mc, "10k", 279.4, 200.66, "MCU_IC", "GND")
r_pull(mc, "10k", 292.1, 200.66, "MCU_A0", "GND")
r_pull(mc, "10k", 304.8, 200.66, "MCU_A1", "GND")
mc.text(25.4, 25.4,
        "CONTROLLER: Raspberry Pi Pico 2 sized board (Pimoroni Pico Plus 2 recommended for its 8 MB PSRAM)\n"
        "Pin plan\n"
        "  GP0-GP7    sound chip data bus D0-D7 (driven by PIO, must stay in order)\n"
        "  GP8, GP9   sound chip A0, A1        GP10 /WR    GP11 /RD (also flips the data buffer)    GP12 /IC (reset)\n"
        "  GP13       knob ADC chip select\n"
        "  GP14, GP15, GP28   SPI1 SCK / MOSI / MISO: screen, knob ADC, volume chip\n"
        "  GP16-GP19  SPI0 to the microSD card (MISO, CS, SCK, MOSI)\n"
        "  GP20, GP21 I2C0 SDA / SCL to the two button expanders\n"
        "  GP22, GP26 screen CS and DC        GP27 LED data (grid + indicator LEDs, one chain)\n"
        "Every Pico GPIO is used. Spare inputs are left on the button expanders.", size=1.5)
mc.text(228.6, 223.52,
        "Boot-time pulls: until the firmware starts, these keep the YM2612 in reset\n"
        "and stop the buffers from seeing floating inputs.", size=1.5)

# =============================================================== sound chip
sc = Sheet(P, "sound_chip.kicad_sch", "Sound chip")
# Data bus buffer: 74LVC245A powered at 3.3V. Its inputs take 5V, its 3.3V outputs are enough for the YM2612's TTL inputs.
buf = {"1": "MCU_RD", "19": "GND", "10": "GND", "20": "+3V3"}
for i, pinA in enumerate(["2", "3", "4", "5", "6", "7", "8", "9"]):
    buf[pinA] = f"MCU_D{i}"
for i, pinB in enumerate(["18", "17", "16", "15", "14", "13", "12", "11"]):
    buf[pinB] = f"YMB_D{i}"
sc.add("74xx:74LS245", "U", "74LVC245A (3.3V, 5V-tolerant)", 76.2, 76.2, buf)
for i in range(8):
    r_series(sc, "100", 139.7, 48.26 + i * 7.62, f"YMB_D{i}", f"YM_D{i}")
# Control lines: 74HCT541 at 5V turns the Pico's 3.3V signals into solid 5V.
ctl = {"1": "GND", "19": "GND", "10": "GND", "20": "+5V",
       "2": "MCU_A0", "3": "MCU_A1", "4": "MCU_WR", "5": "MCU_RD", "6": "MCU_IC", "7": "GND", "8": "GND", "9": "GND",
       "18": "YMB_A0", "17": "YMB_A1", "16": "YMB_WR", "15": "YMB_RD", "14": "YMB_IC", "13": "NC", "12": "NC", "11": "NC"}
sc.add("74xx:74LS541", "U", "74HCT541", 76.2, 152.4, ctl)
for i, s in enumerate(["A0", "A1", "WR", "RD", "IC"]):
    r_series(sc, "100", 139.7, 139.7 + i * 7.62, f"YMB_{s}", f"YM_{s}")
# The chip.
ym = {"2": "YM_D0", "3": "YM_D1", "4": "YM_D2", "5": "YM_D3", "6": "YM_D4", "7": "YM_D5", "8": "YM_D6", "9": "YM_D7",
      "17": "YM_A0", "18": "YM_A1", "14": "GND", "15": "YM_WR", "16": "YM_RD", "11": "YM_IC", "24": "YM_CLK",
      "20": "YM_MOL", "21": "YM_MOR", "13": "NC", "10": "NC",
      "23": "+5VA", "22": "+5VA", "1": "GND", "12": "GND", "19": "GND"}
sc.add("chip_shrine:YM2612", "U", "YM2612 (socketed)", 190.5, 101.6, ym,
       fields={"Footprint": "Package_DIP:DIP-24_W15.24mm_Socket"})
# Clock.
sc.add("Oscillator:DGOF5S3", "X", "7.670454 MHz oscillator can, 5V", 190.5, 172.72,
       {"1": "NC", "14": "+5V", "7": "GND", "8": "OSC_OUT"})
r_series(sc, "33", 228.6, 172.72, "OSC_OUT", "YM_CLK")
# 5V helpers: 74HCT125 lifts the volume chip's SPI lines and the LED data line to 5V.
for unit, (oe, a, y, src, dst) in enumerate([("1", "2", "3", "SPI1_SCK", "POT_SCK"), ("4", "5", "6", "SPI1_MOSI", "POT_SDI"),
                                             ("10", "9", "8", "POT_CS", "POT_CS5"), ("13", "12", "11", "LED_DATA", "LED_DATA5")]):
    sc.add("74xx:74LS125", "U", "74HCT125", 297.18 + (unit % 2) * 45.72, 76.2 + (unit // 2) * 30.48,
           {oe: "GND", a: src, y: dst}, unit=unit + 1, ref="U5")
sc.add("74xx:74LS125", "U", "74HCT125", 375.92, 91.44, {"14": "+5V", "7": "GND"}, unit=5, ref="U5")
P.counters["U"] = max(P.counters["U"], 5)
decouple_row(sc, 271.78, 180.34, [("100nF", "+3V3", False), ("100nF", "+5V", False), ("100nF", "+5V", False),
                                  ("100nF", "+5V", False), ("100nF", "+5VA", False), ("47uF", "+5VA", True)])
sc.text(25.4, 22.86,
        "SOUND CHIP: the YM2612 and the level shifters that let the 3.3V Pico talk to the 5V chip\n"
        "Data bus: 74LVC245A at 3.3V. GP11 (/RD) sets its direction: high = Pico writes to the chip, low = Pico reads the\n"
        "busy flag. The firmware must switch GP0-GP7 to inputs before pulling /RD low.\n"
        "Control lines: 74HCT541 at 5V. 100 ohm series resistors on every chip pin protect the YM2612.\n"
        "/CS is tied low, so the chip listens whenever /WR or /RD is pulsed. /IRQ is not used.\n"
        "Clock: full-size or half-size oscillator can at 7.670454 MHz (NTSC Genesis), 33 ohm series resistor.\n"
        "Put the YM2612 in a socket. Keep the clock wire short and away from the audio wiring.", size=1.5)
sc.text(266.7, 193.04, "One 100nF capacitor right at each chip's power pin:\nU2, U3, X1, U5, U4 = YM2612 (plus 47uF at the YM2612)", size=1.5)

# =============================================================== audio
au = Sheet(P, "audio.kicad_sch", "Audio out")
# The YM2612 outputs are high impedance (about 1k), so the circuit buffers them before the jack.
for side, (mo, y0, potA, potB, potW, opu, plus, minus, outp, tip) in enumerate([
        ("YM_MOL", 63.5, "8", "10", "9", 1, "3", "2", "1", "PHONE_L"),
        ("YM_MOR", 139.7, "7", "5", "6", 2, "5", "6", "7", "PHONE_R")]):
    ch = "L" if side == 0 else "R"
    r_pull(au, "4.7k (fit if quiet)", 50.8, y0 + 17.78, mo, "GND").dnp = True
    au.add(C, "C", "1uF film", 60.96, y0, {"1": mo, "2": f"A{ch}_AC"}, rot=90)
    r_series(au, "4.7k", 91.44, y0, f"A{ch}_AC", f"A{ch}_LPF")
    cap(au, "2.2nF", 114.3, y0 + 10.16, f"A{ch}_LPF")
    au.add("Amplifier_Operational:LM2904", "U", "NJM4556A", 200.66, y0, {plus: f"A{ch}_VOL", minus: f"A{ch}_OUT", outp: f"A{ch}_OUT"},
           unit=opu, ref="U7")
    au.add(CP, "C", "220uF", 233.68, y0, {"1": f"A{ch}_OUT", "2": f"A{ch}_DC"}, rot=90)
    r_pull(au, "10k", 248.92, y0 + 12.7, f"A{ch}_DC", "GND")
    r_series(au, "33", 264.16, y0, f"A{ch}_DC", tip)
au.add("Potentiometer_Digital:MCP4251-xxxx-P", "U", "MCP4251-503 (50k, volume)", 147.32, 101.6,
       {"8": "AL_LPF", "10": "VREF", "9": "AL_VOL", "7": "AR_LPF", "5": "VREF", "6": "AR_VOL",
        "1": "POT_CS5", "2": "POT_SCK", "3": "POT_SDI", "13": "NC", "11": "+5VA", "12": "+5VA", "14": "+5VA", "4": "GND"},
       ref="U6")
au.add("Amplifier_Operational:LM2904", "U", "NJM4556A", 200.66, 101.6, {"8": "+5VA", "4": "GND"}, unit=3, ref="U7")
au.add("Connector_Audio:AudioJack3", "J", "3.5mm stereo jack (headphones / line out)", 304.8, 101.6,
       {"T": "PHONE_L", "R": "PHONE_R", "S": "GND"})
# Mid-rail reference: the signal swings around 2.5V.
r_pull(au, "10k", 50.8, 203.2, "+5VA", "VREF")
r_pull(au, "10k", 50.8, 218.44, "VREF", "GND")
cap(au, "47uF", 66.04, 210.82, "VREF", polar=True)
cap(au, "100nF", 78.74, 210.82, "VREF")
decouple_row(au, 114.3, 210.82, [("100nF", "+5VA", False), ("100nF", "+5VA", False), ("10uF", "+5VA", True)])
P.counters["U"] = max(P.counters["U"], 7)
au.text(25.4, 22.86,
        "AUDIO OUT: one 3.5mm jack that drives headphones and also works as a line out\n"
        "Per side: AC-coupling cap > 4.7k + 2.2nF low-pass (about 15 kHz, smooths the DAC steps a little)\n"
        "> MCP4251 digital pot (volume, set from the encoder over SPI) > NJM4556A buffer (made to drive headphones)\n"
        "> 220uF output cap > 33 ohm > jack. The 10k resistors bleed the output cap so plugging in doesn't pop.\n"
        "Everything runs from the quiet +5VA rail around a 2.5V mid-point (VREF).\n"
        "The 4.7k load resistors on MOL/MOR are marked 'do not fit'. Try without first; fit them if the chip's\n"
        "output is weak or distorted on the breadboard (milestone M1). Gain is 1x; change it after listening.", size=1.5)

# =============================================================== front panel
fp = Sheet(P, "panel.kicad_sch", "Front panel", paper="A2")
# LED grid connector and its power reservoir.
r_series(fp, "330", 50.8, 60.96, "LED_DATA5", "GRID_DIN")
fp.add("Connector_Generic:Conn_01x03", "J", "To 32x8 LED panel IN (5V, DIN, GND)", 81.28, 63.5,
       {"1": "+5V", "2": "GRID_DIN", "3": "GND"})
cap(fp, "1000uF", 104.14, 66.04, "+5V", polar=True)
fp.add("Connector_Generic:Conn_01x02", "J", "From 32x8 LED panel OUT (DOUT, GND)", 81.28, 88.9,
       {"1": "GRID_DOUT", "2": "GND"})
leds = ([f"bus D{i}" for i in range(7, -1, -1)] + ["bus A1", "bus A0", "bus /WR"]
        + [f"key-on CH{i}" for i in range(1, 7)] + ["key-on DAC"]
        + ["Assign Timbre", "Assign Timbre EG", "Assign Amp EG", "Assign Pitch"])
prev = "GRID_DOUT"
for i, name in enumerate(leds):
    x = 139.7 + (i % 8) * 45.72
    y = 63.5 + (i // 8) * 30.48
    nxt = f"LED_CHAIN{i + 1}" if i < len(leds) - 1 else "NC"
    fp.add("LED:WS2812B", "D", f"WS2812 {name}", x, y, {"1": "+5V", "3": "GND", "4": prev, "2": nxt})
    prev = nxt
for i in range(0, len(leds), 2):
    cap(fp, "100nF", 139.7 + (i // 2) * 15.24, 162.56, "+5V")
for i in range(1, len(leds), 2):
    cap(fp, "100nF", 139.7 + (i // 2) * 15.24, 182.88, "+5V")
# Knobs.
knobs = ["KNOB_TIMBRE", "KNOB_TIMBRE_EG", "KNOB_AMP_EG", "KNOB_PITCH"]
for i, k in enumerate(knobs):
    fp.add("Device:R_Potentiometer", "RV", "10k lin, center detent",
           45.72, 223.52 + i * 22.86, {"1": "+3V3", "2": k, "3": "GND"})
fp.add("Analog_ADC:MCP3204", "U", "MCP3204 (knob ADC)", 127, 254,
       {"1": knobs[0], "2": knobs[1], "3": knobs[2], "4": knobs[3], "14": "+3V3", "13": "+3V3", "12": "GND",
        "7": "GND", "8": "ADC_CS", "11": "SPI1_SCK", "9": "SPI1_MOSI", "10": "SPI1_MISO"})
# Button expanders. GPA7/GPB7 are output-only on current MCP23017 silicon, so they only drive outputs or stay unused.
exp1 = {"9": "+3V3", "10": "GND", "12": "I2C_SCL", "13": "I2C_SDA", "18": "+3V3", "15": "GND", "16": "GND", "17": "GND",
        "19": "NC", "20": "NC", "28": "NC", "8": "NC"}
btn1 = ["BTN_PREV", "BTN_REW", "BTN_PLAY", "BTN_STOP", "BTN_FF", "BTN_NEXT", "BTN_LOOP"]
btn1b = ["BTN_CH1", "BTN_CH2", "BTN_CH3", "BTN_CH4", "BTN_CH5", "BTN_CH6", "BTN_DAC"]
for i, b in enumerate(btn1):
    exp1[str(21 + i)] = b
for i, b in enumerate(btn1b):
    exp1[str(1 + i)] = b
fp.add("Interface_Expansion:MCP23017_SP", "U", "MCP23017 (address 0x20)", 205.74, 248.92, exp1)
exp2 = {"9": "+3V3", "10": "GND", "12": "I2C_SCL", "13": "I2C_SDA", "18": "+3V3", "15": "+3V3", "16": "GND", "17": "GND",
        "19": "NC", "20": "NC",
        "21": "BTN_ASSIGN_TIMBRE", "22": "BTN_ASSIGN_TIMBRE_EG", "23": "BTN_ASSIGN_AMP_EG", "24": "BTN_ASSIGN_PITCH",
        "25": "BTN_BYPASS", "26": "ENC_A", "27": "ENC_B", "28": "LCD_BL",
        "1": "ENC_SW", "2": "NC", "3": "NC", "4": "NC", "5": "NC", "6": "NC", "7": "POT_CS", "8": "LCD_RST"}
fp.add("Interface_Expansion:MCP23017_SP", "U", "MCP23017 (address 0x21)", 205.74, 330.2, exp2)
buttons = btn1 + btn1b + ["BTN_ASSIGN_TIMBRE", "BTN_ASSIGN_TIMBRE_EG", "BTN_ASSIGN_AMP_EG", "BTN_ASSIGN_PITCH", "BTN_BYPASS"]
for i, b in enumerate(buttons):
    x = 304.8 + (i % 4) * 38.1
    y = 223.52 + (i // 4) * 15.24
    fp.add("Switch:SW_Push", "SW", b[4:].replace("_", " ").title(), x, y, {"1": b, "2": "GND"})
fp.add("Device:RotaryEncoder_Switch", "SW", "Rotary encoder with push (browse / volume)", 330.2, 335.28,
       {"A": "ENC_A", "B": "ENC_B", "C": "GND", "S1": "ENC_SW", "S2": "GND"})
# Screen and microSD (both breakout boards).
fp.add("Connector_Generic:Conn_01x08", "J", "2.0in ST7789 IPS screen module", 81.28, 330.2,
       {"1": "GND", "2": "+3V3", "3": "SPI1_SCK", "4": "SPI1_MOSI", "5": "LCD_RST", "6": "LCD_DC", "7": "LCD_CS", "8": "LCD_BL"})
fp.add("Connector_Generic:Conn_01x06", "J", "microSD breakout (3.3V)", 81.28, 373.38,
       {"1": "+3V3", "2": "GND", "3": "SD_SCK", "4": "SD_MOSI", "5": "SD_MISO", "6": "SD_CS"})
r_pull(fp, "10k", 106.68, 355.6, "+3V3", "SD_CS")
decouple_row(fp, 152.4, 381, [("100nF", "+3V3", False), ("100nF", "+3V3", False), ("100nF", "+3V3", False)])
fp.text(25.4, 22.86,
        "FRONT PANEL: lights, knobs, buttons, screen, card slot\n"
        "LEDs: one data line from the Pico runs through the 32x8 grid panel first, then on through the 22 indicator LEDs\n"
        "(11 bus lights, 7 key-on lights, 4 Assign lights). Use 5mm through-hole WS2812 LEDs (e.g. WS2812D-F5) for these;\n"
        "their pin order differs from the WS2812B drawn here, so check the LED's datasheet when wiring.\n"
        "Feed the grid's power with thick wires straight from the USB-C connector, not through the protoboard.", size=1.5)
fp.text(25.4, 200.66,
        "KNOBS: 4 potentiometers read by an MCP3204. BUTTONS and the ENCODER: two MCP23017 I2C expanders\n"
        "with their built-in pull-ups turned on in firmware; every button just shorts its pin to ground.\n"
        "Expander 0x21 also drives the screen backlight and reset, and the volume chip's select line.", size=1.5)

if __name__ == "__main__":
    probs = P.check()
    for p in probs:
        print("PROBLEM:", p)
    P.root_notes = ("How to read this schematic\n"
                    "Each box is a page. Wires end in name tags (labels): any two tags with the same name are connected,\n"
                    "even on different pages. The little arrows/bars marked +5V, +5VA, +3V3 and GND are power connections.\n"
                    "Pages: Power > Controller (Pico 2) > Sound chip (YM2612) > Audio out > Front panel.")
    P.write(OUT)
    print("wrote", OUT, "problems:", len(probs))
