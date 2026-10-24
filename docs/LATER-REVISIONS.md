# YM2612 Player: Later Revisions

Status: Ideas parked for after Rev A · Oct 24, 2026 · Owner: Joey

These features were designed during the first pass of the [design doc](DESIGN.md) and
are **not part of Rev A**. They are kept here so Rev B and later can pick them up.
Section numbers in this file are its own.

## 1. What's parked

- **Register light grid**, bus blinkenlights, and key-on lights (§2)
- **Synth controls:** Rev A has full parameter editing through menus and a data knob (see DESIGN.md §2.4). Later: 4 dedicated Korg DS-8 style knobs (Timbre, Timbre EG, Amp EG, Pitch), each assignable to any channel, plus Bypass and mute/solo (§3)
- **Fuller transport:** pause, next/previous, seek, loop, A-B repeat (§4)
- **Fuller hardware:** Pico Plus 2 with PSRAM, LED power budget, USB-C (§5)
- **Lit chip window and enclosure styling** (§6)
- **More MIDI:** a 3.5 mm TRS or 5-pin DIN MIDI in jack, MIDI CC control of the knobs, MIDI out
- Later still: a real SN76489 for Genesis PSG parts, USB drag-and-drop, other chips

## 2. The lights

**Proposal:** three groups of lights, all driven by the microcontroller from the
shadow registers, never wired to the chip's own pins (that keeps the chip safe and
makes the lights readable instead of a blur).

### 2.1 Register grid (the centerpiece)

A **32 × 8 addressable LED panel** (a common, cheap WS2812 matrix) laid out as a
map of the chip, so each light *means* something:

```
            CH1         CH2         CH3         CH4         CH5         CH6       GLOBAL
         op1 2 3 4   op1 2 3 4   op1 2 3 4   op1 2 3 4   op1 2 3 4   op1 2 3 4   ........
DT/MUL    ■ ■ ■ ■     ■ ■ ■ ■     ...                                            LFO
TL        ■ ■ ■ ■                                                                 DAC on
KS/AR     ■ ■ ■ ■                                                                 DAC level
AM/DR     ■ ■ ■ ■                                                                 CH3 mode
SR        ■ ■ ■ ■                                                                 key-on 1-6
SL/RR     ■ ■ ■ ■                                                                 ...
SSG-EG    ■ ■ ■ ■
CHANNEL   freq · block · FB/ALG · pan/LFO sens (one cell each)
```

- **Brightness** = the register's current value.
- **Flash** = the register was just written; it fades over about 100 ms.
- **Color** = who set it: warm white when the value is the song's own, amber when a knob is bending it.
- The **selected channel** (§3.1) is outlined, so you can see which columns the knobs affect.

### 2.2 Bus blinkenlights

11 LEDs in a row: D7–D0, A1, A0, /WR. They mirror the last write, held for a few
milliseconds so they flicker like a 70s front panel instead of staying dimly lit.

### 2.3 Key-on lights

7 LEDs: one per channel that lights on each note, plus one for the DAC.

**Power note:** 256 RGB LEDs at full white could draw several amps. Firmware caps
total LED brightness to stay inside a 5V 3A USB-C budget, and the LEDs get their own
supply path and ground return so they don't hum into the audio.

## 3. The controls

**Decision (Joey, Oct 23):** synth controls only, no direct register editing. The
knobs change the chip's registers behind the scenes, but you work with musical ideas
like "Timbre" and "Pitch", never raw register numbers.

### 3.1 Four knobs you point at channels

The controls borrow from two easy-to-use 4-operator FM synths of the late 80s:

- **Korg DS-8 / 707:** Korg hid FM's operators and algorithms behind analog-style terms.
  Each sound has a **timbre** (brightness) side and an **amplitude** (volume) side, each
  with its own envelope. The performance sliders are **relative to the stored sound**, not
  absolute, and an oscillator select button picks what the sliders act on.
- **Yamaha TQ5 "Easy Edit":** a handful of musical parameters, each moved about ±10 steps
  from the original sound.

On the YM2612 this maps cleanly: the firmware knows each channel's algorithm, so it knows
which operators are **modulators** (they shape timbre) and which are **carriers** (they
make the sound you hear). There are just **4 knobs**, each with a fixed job and a small
**Assign** button with a light:

| Knob | Inspired by | Under the hood | Sound |
| --- | --- | --- | --- |
| **Timbre** | DS-8 Timbre slider, TQ5 Brilliance | TL offset on *modulator* operators only | Dull to bright/harsh |
| **Timbre EG** | DS-8 timbre envelope | Attack and release rates of the *modulators*, together | How fast the brightness opens up and fades away |
| **Amp EG** | DS-8 envelope sliders, TQ5 Attack/Release | Attack and release rates of the *carriers*, together | Left: snappy, short tails. Right: soft swell, long tails |
| **Pitch** | DS-8 joystick bend (up to 12 semitones) | Frequency/block offset in semitones (±12) | Pitch down/up |

Each knob has **21 positions: −10 to +10**, with 0 at the center detent meaning "the song
as written", like the TQ5's ±10 Easy Edit and the DS-8's relative sliders. Pitch uses
±12 semitones instead. Decay and sustain always stay as the song wrote them.

Left out on purpose: feedback ("buzz"), the TQ5's **Wave** choice (the YM2612 only makes
sine waves), **vibrato and tremolo** (dropped by Joey), and built-in effects (the YM2612
has none).

**Pointing a knob at a channel:** tap the knob's **Assign** button, then tap a channel
button (1–6). Tap Assign twice to point it at **all channels**. Each knob remembers its
channel, so different knobs can work on different channels at once, for example
Timbre on the bass and Pitch on the lead. The register grid outlines each knob's
channel in that knob's color, so you can see what's pointed where.

### 3.2 How the knobs behave

- Every knob is centered on **"the song as written"**. Turning it bends the sound from there, and the song keeps playing its own changes underneath.
- Knobs are potentiometers with a **center detent**, so the "as written" position is easy to feel.
- When a knob is re-assigned, the old channel goes back to the song's own sound.
- **Bypass** button: hear the untouched song while held, to compare.
- Settings that would produce silence or a painful sound are clamped by the firmware, and the output stage has a limiter.
- Songs that use the chip's own vibrato or tremolo still play it as written.

### 3.3 Buttons and encoder

- **Encoder + screen:** browse folders and tracks; on the now-playing screen, turning it sets volume.
- **Transport:** previous, rewind, play/pause, stop, fast-forward, next.
- **Channel buttons 1–6 + DAC:** tap to mute, hold to solo, or pick a channel right after pressing a knob's Assign. Each sits under its channel's column on the grid.
- **Assign** (one per knob) and **Bypass** (§3.1–3.2).
- **Loop / A-B:** loop one section while you play with the knobs.

### 3.4 Full parameter editing

Now part of Rev A: late-80s style menus with one data knob reach every YM2612 sound
parameter (see [DESIGN.md §2.4](DESIGN.md)).

## 4. Seeking and fuller transport

Rev A only has start/stop and up/down. Rev B adds pause, next/previous, seek, loop, and A-B repeat.

### 4.1 How seeking works

The chip can't be read back, so to jump to 1:30:

1. Key off all channels and mute the DAC.
2. Run the file from the start **without writing to the chip**, updating only the shadow registers, up to 1:30.
3. Write the whole shadow table to the chip in one burst, then re-send the key-on state.
4. Resume playback.

This takes milliseconds for a typical file. Fast-forward, rewind, loop, and A-B repeat all reuse it.

## 5. Fuller hardware (Rev B)

```
USB-C 5V ─┬─ ferrite ─ 3.3V ── RP2350 board, screen, SD
          ├─ ferrite ─ LDO 5V (analog) ── YM2612 + output stage
          └─ separate path ── LED grid + bus LEDs (brightness-capped)

RP2350 ── PIO bus ── level shifters ── YM2612 (socketed) ── op-amp buffer/filter ── 3.5 mm
```

| Part | Proposal |
| --- | --- |
| Microcontroller | RP2350 board with PSRAM (for example Pimoroni Pico Plus 2). Two cores, PIO for exact bus timing, room for big sample banks. |
| Chip socket | 24-pin ZIF or turned-pin socket, centered under the window |
| Clock | 7.67 MHz crystal oscillator can |
| Level shifting | 74HCT-series buffers for 3.3V → 5V writes; a 5V-tolerant buffer or divider for reading the busy bit. Confirm thresholds against the datasheet. |
| Audio out | Op-amp buffer and low-pass filter on MOL/MOR, based on a known-good Genesis model 1 output stage; 3.5 mm line out plus a headphone amp; volume through a digitally controlled potentiometer set from the encoder |
| Screen | 2.0"–2.8" color IPS (SPI) |
| Lights | 32×8 WS2812 panel, 11 + 7 discrete LEDs |
| Controls | 4 center-detent potentiometers, 1 clickable encoder, about 21 buttons (4 with indicator LEDs) |
| Power | USB-C with 5.1 kΩ resistors on CC for 5V; needs a 3A-capable supply because of the LEDs |
| Storage | microSD slot, reachable from outside the case |
| Build | Protoboard or a carrier board for the RP2350 and chip; the PCB comes later |

**Protecting the chip:** series resistors on every bus line, no user-reachable pins,
reverse-polarity protection on the input. Keep a spare YM2612 on hand.

**Sourcing:** YM2612s are pulled from old consoles and are widely counterfeited. Buy
from a seller with returns, and test each one on the breadboard rig (M1) before it goes
in the box. A YM3438 (the later CMOS version) sounds cleaner and lacks the gritty DAC;
note which one you have.

## 6. Enclosure ideas

What the case needs to hold and expose:

- **Chip window:** the YM2612 visible under a clear window with warm edge lighting raking across the top so the markings glow.
- **Register grid:** 32×8 panel behind a diffuser, ideally with a printed light-blocking grid so each cell reads as its own square. Column and row labels printed or engraved on the panel (§2.1).
- **Bus and key-on LED rows** near the grid.
- **Screen**, **encoder**, **4 synth knobs, each with an Assign button**, **~18 buttons**, with the 7 channel buttons lined up under the grid's channel columns.
- **Rear or side:** USB-C, 3.5 mm line out, headphone jack + volume, microSD slot.
- **Inside:** standoffs for the RP2350 board and the chip/audio board; keep the audio board away from the LED panel's power wiring.
- **Style ideas from the notes:** beige or black finish, period font, the YM2612 pinout printed beside the window.

Exact dimensions get filled in once the screen, LED panel, knobs, and buttons are bought (M5).
