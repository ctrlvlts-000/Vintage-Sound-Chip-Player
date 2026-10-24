# YM2612 player hardware (Rev A)

The Rev A board, drawn in KiCad. It follows [docs/DESIGN.md](../docs/DESIGN.md). The goal is a
**PCBWay turnkey prototype**: PCBWay makes the board, buys the parts and solders them on. Joey supplies
the YM2612 and plugs it into the socket.

**Status:** schematic draft, ready for review. No PCB layout yet.

**Just want to look?** Open [ym2612_player/ym2612_player.pdf](ym2612_player/ym2612_player.pdf). GitHub shows it in the browser.
The parts list is [ym2612_player/bom.csv](ym2612_player/bom.csv).

## Opening it in KiCad

1. Install KiCad (any version from 7 up) from <https://www.kicad.org/download/>.
2. Download this repository: on GitHub click the green **Code** button, then **Download ZIP**, and unzip it.
   (While this is still a pull request, pick its branch in the branch menu at the top left first.)
3. In KiCad choose **File > Open Project** and pick `hardware/ym2612_player/ym2612_player.kicad_pro`.
4. Double-click **ym2612_player.kicad_sch**. The first page has one box per page; double-click a box to go in,
   **Alt + Backspace** to come back out.

The files are saved in KiCad 7 format. Newer KiCad opens them and offers to upgrade them the first time you save.
If you'd rather keep working in your own **YM2612 player** project, copy these files into it, or ask Claude to do it
through folder access.

**Reading the drawing:** wires end in name tags (labels). Any two tags with the same name are connected, even on
different pages. `+5V`, `+5V_YM`, `+4V5A`, `+3V3`, `GND` and `GNDA` are power connections. A blue X means "not
connected on purpose". A part crossed out in red is "do not fit": it has a footprint but PCBWay leaves it off.

## Pages

| Page | What's on it |
| --- | --- |
| Power | 5V from the Pico's USB-C, a ferrite-filtered 5V for the chip, and a quiet 4.5V LDO rail for the audio |
| Controller | Pimoroni Pico Plus 2 soldered flat, boot-time pull resistors, spare-pin header, test points |
| Sound chip | YM2612 socket, two 74HCT541 buffers (3.3V to 5V) with 100 ohm resistors, clock options, window LEDs |
| Audio out | Model 1 style filter, balanced 1/4" outs, headphone amp with the dual slide volume |
| Front panel | 7 buttons (12 mm), data knob, I2C level shifter, LCD connector |

## Choices made in this draft

- **Pico Plus 2 soldered flat** by its castellated edges (Digi-Key part PIM724, so PCBWay can buy it). Lowest
  height, nothing to wiggle loose. If you'd rather have it removable, it can sit on two 20-pin sockets instead.
- **YM2612 socket:** Mill-Max turned-pin, 24-pin, 600 mil wide. PCBWay solders the socket only.
- **Clock:** the Pico makes the 7.67 MHz clock (as the design doc proposes). There's an unfitted footprint for a
  7.670454 MHz oscillator can, so switching to exact Genesis pitch is a two-part change with no new board.
- **Buttons:** 12 mm Omron B3F-4055 switches with snap-on round caps (your choice, Oct 24).
- **Analog rail:** LP5907 4.5V low-noise regulator after a ferrite and an LC filter.
- **Grounds:** digital `GND` and analog `GNDA` are joined at one point (NT1), to be placed beside the YM2612.
- **Audio filter:** 2.2k load, then a 3.39 kHz first-order low-pass (Model 1 style). See DESIGN.md 5.5.
- **Balanced outs:** hot and cold legs from OPA2350s, 100 ohm + 10 µF each, Neutrik NMJ6HCD2 jacks, with a 0 ohm
  ground-lift footprint on each sleeve.

## Still to do before ordering

1. **PCB layout:** board size and the position of every jack, button, the knob and the LCD come from your enclosure.
2. **Slide pot footprint:** the Bourns PTA2044 dual-gang slide pot has no KiCad footprint. It needs drawing from
   Bourns's drawing (or downloading from the Digi-Key / SnapEDA page) before layout.
3. **Pico Plus 2 footprint check:** `ym2612.pretty/Pimoroni_PicoPlus2_SMD` uses the standard Pico pad positions.
   Check it against a real board or Pimoroni's drawing before ordering.
4. **Window LEDs:** pick an exact warm-white 3 mm LED for PCBWay (any will do electrically).
5. **Placement file (CPL / centroid)** and Gerbers come out of the finished layout.

## Regenerating

`tools/build.sh` rebuilds the schematic from `tools/design.py`, checks every connection against the netlist, and
re-exports the PDF and BOM (needs KiCad installed). Once anyone edits the schematic in KiCad, the KiCad files become
the real source and the script should not be rerun.
