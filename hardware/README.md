# Chip Shrine hardware

The schematic for the YM2612 player proof of concept, drawn in KiCad. It follows
[docs/DESIGN.md](../docs/DESIGN.md).

**Just want to look?** Open [chip_shrine/chip_shrine.pdf](chip_shrine/chip_shrine.pdf). GitHub shows it in the browser.

## Opening it in KiCad

1. Install KiCad 8 or newer from <https://www.kicad.org/download/>. It's free.
2. Download this repository: on GitHub, click the green **Code** button, then **Download ZIP**, and unzip it.
   (If the change is still a pull request, switch to its branch first with the branch menu at the top left.)
3. In KiCad, choose **File > Open Project** and pick `hardware/chip_shrine/chip_shrine.kicad_pro`.
4. Double-click **chip_shrine.kicad_sch** in the project window to open the Schematic Editor.
5. The first page is a map with one box per page. Double-click a box to go into that page. To go back up, press
   **Alt + Backspace**, or use the page list on the left.

The files were saved in KiCad 7 format. Newer KiCad opens them fine and offers to upgrade them the first time you save.

**Reading the drawing:** wires end in name tags (labels). Any two tags with the same name are connected, even on
different pages. The `+5V`, `+5VA`, `+3V3` and `GND` symbols are power connections. A small blue X on a pin means
"not connected on purpose".

## Pages

| Page | What's on it |
| --- | --- |
| Power | USB-C 5V in, fuse, quiet `+5VA` rail for the chip and audio, diode into the Pico |
| Controller | Pico 2 sized board (Pimoroni Pico Plus 2 for its 8 MB PSRAM) and the pin plan |
| Sound chip | YM2612 in a socket, 7.67 MHz oscillator, level shifters with 100 ohm protection resistors |
| Audio out | Filter, digital volume chip, NJM4556A headphone driver, one 3.5 mm jack (headphones or line out) |
| Front panel | 32x8 LED grid connector, 22 indicator LEDs, 4 knobs, 19 buttons, encoder, screen, microSD |

## Decisions in this draft

- **Audio:** one headphone-capable 3.5 mm jack that also works as line out (Joey, Oct 23).
- **Lights:** the proposed 32x8 WS2812 panel plus 22 WS2812 indicator LEDs, all on one data line.
- **Buttons:** read through two MCP23017 I2C expanders, because every Pico pin is already used.
- **Knobs:** read by an MCP3204 ADC (the Pico only has 3 analog inputs).
- **Volume:** MCP4251 digital pot, set from the encoder, as in the design doc.
- **Modules on protoboard:** the screen, microSD and LED panel are breakout boards on headers. Footprints get
  picked when the PCB starts.

## Things to check on the breadboard (milestone M1)

- The YM2612's output level. Two 4.7k load resistors (R24, R28) are drawn but marked "do not fit". Fit them if the
  sound is weak or distorted.
- Bus timing against the busy flag, as planned in the design doc.
- Through-hole WS2812 LEDs (WS2812D-F5) have a different pin order from the WS2812B symbol. Wire by the LED's datasheet.

## Parts list (from the schematic)

| Qty | Part |
| --- | --- |
| 1 | Pimoroni Pico Plus 2 (or Raspberry Pi Pico 2) |
| 1 | YM2612 + 24-pin socket (buy a spare chip) |
| 1 | 7.670454 MHz oscillator can, 5V |
| 1 each | 74LVC245A, 74HCT541, 74HCT125, MCP4251-503, NJM4556A, MCP3204, (2) MCP23017, all DIP with sockets |
| 23 | WS2812 LEDs (22 indicators; a 32x8 WS2812 panel separately) |
| 4 | 10k linear pots with center detent |
| 19 + 1 | Push buttons + rotary encoder with push switch |
| 1 each | 2.0" ST7789 IPS screen module, microSD breakout (3.3V), USB-C power breakout or receptacle, 3.5 mm stereo jack |
| 1 each | 3A PTC fuse, 1N5817 diode, ferrite bead |
| 35 | 100nF capacitors |
| 13 / 10 / 4 / 3 / 2 / 1 | Resistors: 100, 10k, 4.7k (+2 optional), 33, 5.1k, 330 ohm |
| assorted | Capacitors: 1000uF, 220uF x3, 100uF, 47uF x2, 10uF x2, 1uF film x2, 2.2nF x2 |

## Regenerating

`tools/` holds the script that wrote this first draft (`python3 tools/design.py chip_shrine`). Once anyone edits the
schematic in KiCad, the KiCad files are the real source and the script should not be rerun.
