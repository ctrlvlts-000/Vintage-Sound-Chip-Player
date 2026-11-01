# YM2612 Rev B: independent review and simulation

Reviewed Oct 31, 2026, on `main` after PRs #9 and #10, without reading the earlier reviews first. Owner: Joey.
Live copy: <https://claude.ai/artifact/5c8hcbA7Uy351p8DA4PDeR>

**Verdict:** nothing in the Rev B circuit or board has to change before ordering. The board matches the schematic
pad for pad, the pinouts check out against the datasheets, and the simulated noise floor is about 109 dB below full
output, well past the -70 dB target. There are three medium findings to check on the first boards and a few small ones.

## Before ordering

No design change is required. These checks still stand:

- [ ] Run ERC and DRC in the KiCad 10 copy and make the PCBWay files from it (this review used KiCad 7).
- [ ] Encoder: the BOM part (Bourns PEC11R-4215F) has a 15 mm shaft, but the footprint and the 3D model assume about
      20 mm. Confirm the shaft length for the case, and check its mounting-lug spacing against the 11.2 mm EC11 footprint.
- [ ] Pico Plus 2: plug a real board and the two sockets into a 1:1 printout of the footprint to confirm the hole rows.
- [ ] Order note for PCBWay: C5 (47 µF on the analog supply input) should be a standard aluminium electrolytic, not a
      low-ESR polymer substitute (see L5).

## Worth fixing or checking (medium)

None of these stops the board working. Each is cheap to check on the first boards and has a one-part fix.

| # | Finding | Why it matters | What to do |
| --- | --- | --- | --- |
| M1 | The 4.5V regulator (U1, LP5907) has about 17 µF of ceramic plus a 47 µF electrolytic (C7) on its output. TI's guidance is 1 to 10 µF. | Too much output capacitance can make this kind of regulator ring or oscillate. The electrolytic's resistance probably keeps it stable, but it is outside what TI tested. | On the first board, look at +4V5A with a scope (or listen for a whine). If it rings, leave C7 off. |
| M2 | The regulator turns 5V USB into 4.5V, leaving about 0.45 V of headroom. | If the USB port sags below about 4.6 V (weak ports, hubs, long cables), the regulator stops filtering and USB noise reaches the audio. | Measure the 5V across C3 with the LCD on, from your PC's port. If it is below 4.7 V, use a better port or a powered hub, or swap U1 to the pin-compatible LP5907MFX-4.3. |
| M3 | The line outs clip if the YM2612 puts out more than about 2 V peak-to-peak at MOL/MOR. There is no reliable published figure for that level. | Clipping would add harsh distortion on loud songs. | Play a loud VGM and look at HOT_L. If it flattens at the top, change R24/R34 from 100k to 68k and C18/C24 from 470 pF to 680 pF (keeps the 3.39 kHz corner). |

## Low risk and cosmetic

| # | Finding | What to do |
| --- | --- | --- |
| L1 | The chip's audio traces (YM_MOL, YM_MOR) cross the data lines on the other copper layer near the top of the socket. They cross at right angles and never run alongside, so the coupling is tiny. | Nothing now. If faint clicks in time with register writes show up in M4, look here first. |
| L2 | About 140 µF sits directly on USB 5V, plus 220 µF behind a 10 Ω resistor. USB asks for 10 µF at plug-in. Most PCs cope. | If the PC's port resets or the Pico fails to start when plugged in, use a powered hub. |
| L3 | Power-on thump on the balanced outs: about 1 V on each leg for a few ms in simulation, settled within about 1 s. | Switch the player on before the monitors, or mute the interface input at power-up. Headphones are protected by the amp's enable pin. |
| L4 | The silkscreen text "BAL L     BAL R" sits entirely under J2, so the R label is under the wrong jack. | Cosmetic, inside the case. Label the case from the jacks: J2 (left, seen from the front) is L, J3 is R. |
| L5 | If PCBWay substitutes a low-ESR polymer cap for C5, the filter in front of the regulator peaks by 2.2 dB at 5.2 kHz. With a normal electrolytic there is no peak. | Order note above. Even the peak is harmless after the regulator. |
| L6 | The ground pours have 35 small islands, several joined to the main plane by a single via. All are connected. | Nothing. |
| L7 | No ESD protection on the audio jacks, and the balanced-out caps are 16 V parts. | Never plug the line outs into an input with 48 V phantom power switched on. |

## Firmware notes

The board relies on the firmware for these. None needs a hardware change.

- **Headphone enable (GP12):** keep it low for at least 1 s after power-up; the headphone amp's input settles at
  about 1 s in simulation, and TI says to enable only after the source has settled. Set it low before stopping audio.
- **Chip reset:** start the 7.67 MHz clock on GP21 before releasing /IC (GP11). The YM2612 needs its clock during reset.
- **LCD speed:** PCF8574 backpacks are rated for 100 kHz I2C. DESIGN.md says 400 kHz; use 100 kHz.
- **System clock:** 153.33 MHz is slightly above the RP2350's 150 MHz rating. A common, mild overclock.

## Simulation results (ngspice 42)

| What | Result |
| --- | --- |
| Model 1 style filter, balanced out, relative to 100 Hz | 1 kHz -0.35 dB, 2 kHz -1.3 dB, 3.39 kHz -3.0 dB, 5 kHz -5.0 dB, 10 kHz -9.9 dB, 20 kHz -15.5 dB |
| Bass | Flat to well below 20 Hz (-3 dB under 5 Hz) |
| Gain, chip pin to balanced output (hot minus cold) | 4.26 times (+12.6 dB) |
| Noise, balanced out, 20 Hz to 20 kHz | 10.5 µV rms (resistors and op-amps) |
| Largest clean balanced output | about 3.1 V rms (+12 dBu) |
| Noise floor vs full output | **-109 dB** (target -70 dB) |
| Noise into the headphone amp | 2.5 µV rms, about -110 dB below its full level |
| Clipping point | line out stays clean up to about 1.0 V peak at MOL/MOR |
| USB 5V ripple to regulator input (ferrite + 10 µH + caps) | 1 kHz -0.04 dB, 10 kHz -3 dB, 20 kHz -8.5 dB, 100 kHz -32 dB |
| YM2612 A.VCC filter (10 Ω + 220 µF) | 100 Hz -4.8 dB, 1 kHz -22 dB, 10 kHz -30 dB |
| Power-on, balanced out | about 1 V per leg in the first ms; under 2 mV after 1.5 s |
| Power-on, headphone amp input | settles by about 1 s |

The filter ahead of the regulator only works above the audio band; the regulator does the audio-band cleaning, which
is why its headroom (M2) matters. The real noise floor will be set by digital interference and grounding, not these
thermal numbers; M4's measurement against a real Model 1 is the true test. Compared afterwards with the Rev A
simulations: they found the same clipping point (about 1.05 V peak at the chip pin).

## Checked and correct

- **Board matches schematic:** every pad is on the same net as in the schematic; no missing or extra connections, 0 unconnected pads.
- **DRC (KiCad 7):** 0 real violations (the report's 145 entries are all "library not configured" notes from the cloud machine).
- **Pinouts:** Pico Plus 2 (40 pins), YM2612 (24), TPA6132A2 (pin by pin against [TI's datasheet](https://ti.com/lit/pdf/SLOS597)), OPA2350 SOIC-8, LP5907 SOT-23-5, 74HCT541.
- **Chip interface:** 74HCT541 buffers turn 3.3V into 5V, always enabled, spare inputs grounded. Pull-downs on /IC, A0, A1 and a pull-up on /WR keep the chip in reset while the Pico boots. No 5V signal reaches a Pico pin.
- **LCD:** standard BSS138 I2C level shifter; connector order GND, VCC, SDA, SCL matches the HiLetgo backpack.
- **Headphone amp:** -6 dB gain, single-ended inputs wired as TI shows, charge-pump and supply caps at TI's values, enable pulled low by default.
- **Output caps:** all electrolytics face the right way (+ toward the 2.25 V op-amp side).
- **Layout:** audio on the left away from USB and the bus; chip audio traces short (24 mm); clock trace clear of the audio; 0 Ω ground-lift links on both balanced jacks.
- **Fab files:** Gerbers, BOM and placement file come from the same commit as the board; do-not-fit parts are left out.
- **Power budget:** roughly 300 mA from USB (LCD backlight is the biggest load), under a USB 2 port's 500 mA.

## How this was done, and its limits

KiCad 7.0.11 exported the netlist ([netlist.txt](netlist.txt)) and ran DRC; a script compared every board pad with
the schematic. KiCad 7's command line has no ERC, so ERC rests on the KiCad 10 run.

Simulation files are in [sim/](sim). Run any `.sp` file with `ngspice -b <file>` from inside `sim/`:
`ac2.sp` (frequency response), `noise.sp`, `clip.sp`, `supply.sp` / `supply_lowesr.sp` / `s3.sp` (USB ripple and
A.VCC filter), `thump.sp` / `thump2.sp` (power-on). `audio.cir` is the left channel as drawn; `opamp.inc` is the op-amp model.

Limits: the op-amps are a behavioural model (38 MHz, rail-to-rail, 5 nV/√Hz); the YM2612 is a signal source with an
assumed 1k output resistance; the headphone amp is an ideal -6 dB stage; the regulator has no model, so M1 can only be
settled on the bench. Headphone load 32 Ω, interface input 10k per leg.
