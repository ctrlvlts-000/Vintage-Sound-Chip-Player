# Chip Shrine: YM2612 Player — Rev A Design

Status: Draft v1.0 · Oct 24, 2026 · Owner: Joey

> A small box with a real Sega Genesis sound chip, the Yamaha YM2612. Put VGM files
> onto it over USB-C like a thumb drive, pick a song with the buttons, and hear the
> real chip play it through headphones or balanced outputs into your studio.

**Rev A is the simplest, lowest-cost version that plays music.** It does VGM import and
playback and nothing else. The lights, synth knobs, fuller transport, and lit window
designed earlier are parked in [LATER-REVISIONS.md](LATER-REVISIONS.md) for Rev B and on.

Joey is drawing the schematic and PCB in a KiCad project called **YM2612 player**. This
doc is the reference for what goes on that board. Items marked **Proposal** are
recommendations waiting for Joey's OK; items marked **Open** still need a call.

---

## 1. What Rev A does

**Features (the whole list)**

1. **VGM import over USB-C:** plug the player into a computer and it shows up as a USB drive. Drag `.vgm` and `.vgz` files onto it. No memory card.
2. **Playback** on a real YM2612.
3. **Audio outputs:** a 3.5 mm headphone jack, plus **two balanced 1/4" TRS line outs** (L and R) for an audio interface. Target: **noise floor at or below −70 dB** (§5.5).
4. **A small green-screen display:** a cheap 1.9" 320 × 170 color LCD drawn like a tiny vintage green terminal. It always shows the VGM file that's playing, plus the name of whatever you're editing (§2.1).
5. **A late-80s digital synth front panel:** one data knob and 7 buttons (Play, Stop, ◀, ▶, Edit, Exit, Write) driving simple menus for every function (§2.2–2.4).
6. **Full sound editing:** every YM2612 sound parameter, plus Korg DS-8 style quick controls, reachable from the menus (§2.4).
7. **USB MIDI in** over the same USB-C cable, with two modes: **VGM mode** plays song files, **MIDI mode** plays the YM2612 like a synth from Ableton or any DAW (§2.5). Costs no extra parts.

**Not in Rev A**

- Lights, the 4-knob panel, lit chip window (see [LATER-REVISIONS.md](LATER-REVISIONS.md)).
- Seek, loop, A-B repeat.
- Volume control (see Open questions, §8).
- Genesis PSG parts: only the YM2612 plays (decided Oct 23).
- DIN or TRS MIDI jacks (USB MIDI only), MIDI out, MIDI control of knobs.
- Other chips, battery, wireless.

## 2. Front panel, screen, and menus

The panel works like a late-80s / early-90s digital synth (think Korg M1, Roland D-50, Yamaha
DX7): **one data knob, a few buttons, and a small screen with simple menus**. Nothing is
buried more than one level deep, and the screen always says what you're editing.

### 2.1 The screen: a tiny green terminal

**Decision (Joey, Oct 24):** a
**1.9" 320 × 170 IPS color TFT** with an ST7789 controller, SPI, about $5. It's a wide strip
(about 43 × 23 mm active area), close to the shape of a vintage synth's LCD. Because it's a
color screen, the firmware draws the green terminal itself on a black background:

- A chunky **VT220-style bitmap font** (8 lines × 40 characters, or 5 lines × 26 in the large font).
- **Phosphor green** text, with **amber** and **plain white** styles in the System menu.
- **Scanlines:** every other pixel row drawn slightly dimmer, like a CRT.
- **Phosphor glow:** a faint halo around lit characters and a short fade when text changes.
- **Inverse-video** highlight for the selected item and a **blinking block cursor**.
- A **boot screen** that types out `CHIP SHRINE  YM2612 OK` like an old computer.

The one trade-off against OLED: an LCD's black is lit from behind, so in a dark room the
background is very dark grey rather than true black. The firmware keeps the backlight at a
moderate level to help.

Alternatives, if this one doesn't suit: a **2.0" 320 × 240** ST7789 (same wiring, taller and
less synth-like), or a **20 × 4 character LCD** with a yellow-green backlight (the authentic
DX7/M1 look, but dark text on green, with no terminal effects).

**Home screen (VGM mode)** — the playing file is always on the top line:

```
┌──────────────────────────────────────────┐
│ GHZ.VGM                      VGM  ▶ 01:24 │  file name, mode, play state, time
│ Green Hill Zone                    03/27 │  title from the GD3 tag, track number
│ Sonic the Hedgehog                       │  game
│ CH1▮▮▮ CH2▮▮ CH3▮▮▮▮ CH4▮ CH5▮▮ CH6/DAC▮▮ │  channel activity
└──────────────────────────────────────────┘
```

**Edit page** — the file stays on top, the parameter name is spelled out:

```
┌──────────────────────────────────────────┐
│ GHZ.VGM                      VGM  ▶ 01:24 │
│ OPERATOR   CH2                           │  page, channel
│      OP1   OP2   OP3   OP4               │
│ ATTACK RATE  31  [18]   31    28         │  cursor on OP2; knob changes it
└──────────────────────────────────────────┘
```

### 2.2 Controls

| Control | On the home screen | In the menus |
| --- | --- | --- |
| **Data knob** | Scroll the track list | Change the value under the cursor, or pick a menu item |
| **◀ / ▶** | Previous / next track | Move the cursor between parameters (and across OP1–OP4) |
| **Play** | Play / pause | Play / pause (you hear edits live) |
| **Stop** | Stop | Stop |
| **Edit** | Open the main menu | Enter the selected menu item |
| **Exit** | — | Back up one level; cancels a prompt |
| **Write** | — | Save (instrument, or your edits to a song), with an "are you sure" prompt |

That's **7 buttons and 1 knob**. The data knob is turn-only. The knob speeds up when spun
fast, so long ranges like operator level (0–127) are quick to cover.

### 2.3 Menu map

Press **Edit** on the home screen to get the main menu. Pick a page with the knob, Edit to
enter it, Exit to come back.

```
MAIN MENU
 1 QUICK EDIT    Channel, Timbre, Timbre EG, Amp EG, Pitch      (Korg DS-8 style)
 2 OPERATOR      10 settings × OP1–OP4, shown side by side
 3 CHANNEL       Algorithm, Feedback, Pan, LFO depth (AM / PM)
 4 LFO           On/off, Speed (all channels)
 5 MODE          VGM player  /  MIDI synth
 6 INSTRUMENT    Load, Init, Rename  (Write saves)
 7 SYSTEM        MIDI channel, Screen style, Scanlines, Brightness, Loop count, Firmware info
```

Every page shows the **channel** being edited (CH1–CH6 or ALL). On the Quick Edit page,
"Channel" is the first item, and every other page follows it.

### 2.4 What can be edited

| Page | Parameter | Range |
| --- | --- | --- |
| Quick Edit | Channel | All, 1–6 (each remembers its own edits) |
| | Timbre | −10 … +10 (modulator levels: dull to bright) |
| | Timbre EG | −10 … +10 (modulator attack + release) |
| | Amp EG | −10 … +10 (carrier attack + release: snappy to swelling) |
| | Pitch | −12 … +12 semitones |
| Operator (×4) | Attack rate, Decay rate, Sustain rate | 0–31 |
| | Release rate, Sustain level | 0–15 |
| | Level | 0–127 |
| | Multiple (harmonic) | 0–15 |
| | Detune | −3 … +3 |
| | Key scaling | 0–3 |
| | Amplitude mod | off, on |
| | SSG-EG shape | off, 8 shapes |
| Channel | Algorithm | 1–8 (the screen draws the operator wiring) |
| | Feedback | 0–7 |
| | Pan | L, C, R |
| | LFO amplitude depth, pitch depth | 0–3, 0–7 |
| LFO | On/off, Speed | off/on, 0–7 |

That covers every sound setting the YM2612 has.

**What an edit means in each mode**

- **VGM mode:** an edited parameter is **held at your value** on that channel, ignoring what the
  song writes to it; untouched parameters keep following the song. Quick Edit values are offsets
  that bend the song's own values instead. **Write** saves your edits next to the song
  (`GHZ.EDT`), so they come back next time it plays. Holding **Exit** for 2 seconds clears all edits.
- **MIDI mode:** edits change the instrument you're playing. **Write** saves it to the drive as a
  `.tfi` file, after you name it with the knob and ◀ / ▶.

### 2.5 MIDI mode

1. Connect the player to a computer. It's a class-compliant USB MIDI device, so it needs no
   drivers on Windows or macOS and shows up in Ableton Live's MIDI preferences as **Chip Shrine**,
   alongside the USB drive. Turn on **Track** for it, then set a MIDI track's *MIDI To* to
   Chip Shrine, channel 1 (the channel is changeable in System).
2. Notes play the YM2612 with **6-note polyphony** (one note per FM channel; when a 7th note
   arrives, the oldest note is stolen).
3. Switch modes in **MODE**. On the home screen in MIDI mode, the knob picks the instrument.

**Where the instruments come from** :

- **Built-in presets:** a small bank of classic Genesis-style sounds stored with the firmware.
- **Borrowed from songs:** the player scans the VGM files on the drive and lists every
  distinct instrument it finds, named by song and channel, for example *Green Hill Zone · ch 2*.
- **Instrument files:** `.tfi` files (a common 42-byte YM2612 instrument format) dragged onto the drive show up too.

**What MIDI controls in Rev A:**

| MIDI message | Effect |
| --- | --- |
| Note on / off | Plays and releases notes |
| Velocity | Note loudness (carrier operator levels) |
| Pitch bend | ±2 semitones |
| Sustain pedal (CC 64) | Holds notes |
| Program change | Picks the instrument |
| All notes off (CC 123) | Silences the chip |

```
┌──────────────────────────────────────────┐
│ MIDI SYNTH                    CH1   ♪ 3/6 │  mode, MIDI channel, notes sounding
│ 014/120  Green Hill Zone · ch2           │  instrument number and name
│ ALG 4  FB 5                               │  quick look at the patch
│ V1▮ V2▮ V3▮ V4  V5  V6                    │  which of the 6 voices are playing
└──────────────────────────────────────────┘
```

### 2.6 Adding songs

Plug the player into a computer with USB-C, drag `.vgm` / `.vgz` files onto the **CHIPSHRINE**
drive, then eject it. The player rescans its files after you eject. Playback is paused while
the computer has the drive mounted; MIDI works either way.

## 3. The chip: YM2612 at a glance

| Fact | What Rev A does about it |
| --- | --- |
| 6 FM channels with 4 operators each; channel 6 can play 8-bit samples (DAC) | Firmware plays all of it, including drum and voice samples |
| Two register banks, selected with address lines A0 and A1 | 2 GPIO lines |
| 24-pin DIP, 5V, NMOS | DIP socket; 3.3V → 5V buffers between the Pico and the chip |
| Clock about 7.67 MHz (NTSC Genesis) | Generated by the Pico, no oscillator part needed (§5.3) |
| Registers are write-only; the status byte can be read | Rev A never reads it. /RD is tied high, so the bus is one-way |
| Needs a short wait after each write | Fixed minimum gap, measured on a logic analyzer in M1 |
| Analog outputs MOL / MOR | Low-noise filter stage, then headphone and balanced drivers (§5.5) |

## 4. How it works

### 4.1 Audio pipeline

```mermaid
flowchart LR
    PC[Computer<br/>drag and drop]

    subgraph PICO["Pimoroni Pico Plus 2 (RP2350)"]
        USB[USB drive<br/>over USB-C]
        FLASH[(16 MB flash<br/>VGM / VGZ files)]
        PARSE[VGM parser]
        PCM[(Sample data<br/>in PSRAM)]
        SCHED[Write scheduler<br/>44.1 kHz timeline]
        DRV[YM2612 driver<br/>PIO bus writes]
        CLKGEN[Clock output<br/>7.67 MHz]
        UI[Display, buttons,<br/>data knob]
        SYN[Edit engine<br/>all sound settings]
    end

    BUF[74HCT buffers<br/>3.3V to 5V]
    YM{{YM2612}}
    FILT[Filter + buffer<br/>OPA2350]
    AMP[NJM4556A<br/>headphone driver]
    JACK((3.5 mm<br/>headphones))
    BAL[Balanced driver<br/>OPA2350]
    TRS((2x 1/4 in TRS<br/>balanced L / R))
    LCD[1.9 in 320x170<br/>green-terminal LCD]
    BTN[Data knob +<br/>7 buttons]
    MIDI[USB MIDI<br/>keyboard / DAW]

    PC --> USB --> FLASH --> PARSE
    PARSE -- "sample data" --> PCM
    PARSE -- "timed writes" --> SCHED
    PCM -- "DAC bytes" --> SCHED
    SCHED --> SYN --> DRV --> BUF --> YM
    UI -- "edits" --> SYN
    CLKGEN --> BUF
    YM -- "analog L/R" --> FILT
    FILT --> AMP --> JACK
    FILT --> BAL --> TRS
    BTN --> UI
    UI --> LCD
    UI -- "start, stop" --> SCHED
    MIDI -- "notes (MIDI mode)" --> SYN
```

In plain words: the Pico reads a VGM file from its own flash memory, where you copied it over USB. The file is a list of "write
this value to this chip setting, then wait this long". One of the Pico's two cores
plays those writes to the YM2612 at the right moments. The other core runs the display
and buttons. The YM2612 makes the sound, and the op-amps clean it up and drive
the headphone jack and the balanced outputs.

### 4.2 Firmware modules

| Module | Job |
| --- | --- |
| **Storage** | A FAT filesystem in the board's flash (about 14 MB free after the firmware), read with FatFs. Builds the track list. |
| **USB** | TinyUSB composite device: a mass-storage drive called CHIPSHRINE plus a USB MIDI device called Chip Shrine. While the computer has the drive mounted, VGM playback is off; after eject, the player rescans the files. MIDI works either way. |
| **MIDI mode** | Voice allocator for 6 notes, note/velocity/pitch-bend/sustain handling, and an instrument library (presets, `.tfi` files, and instruments extracted from VGM files by watching which register sets each song writes). Writes go through the same YM2612 driver. |
| **VGM parser** | Reads the header (clock, length, loop point) and GD3 tags (title, game). Turns commands into timed writes: YM2612 port 0/1 writes, waits, PCM data blocks, DAC writes, and DAC stream commands. Skips PSG writes. VGZ files are unzipped while loading, which matters more now since storage is limited. |
| **Sample data** | Loads the song's PCM samples into the board's 8 MB PSRAM, so even sample-heavy tracks fit. |
| **Scheduler** | Runs on core 1. Releases each write at its exact sample time (1/44,100 s). Stops at the end, or after the loop has played twice. |
| **YM2612 driver** | PIO program: put A1/A0 and D0–D7 on the pins, pulse /WR, wait the minimum gap. Also pulses /IC (reset) at power-up and on Stop to silence the chip. |
| **Edit engine** | Keeps every sound parameter per channel. In VGM mode it holds edited parameters at your value (and applies Quick Edit as offsets) on every write; in MIDI mode it edits the current instrument. Saves instruments as `.tfi` and song edits as `.edt`. Clamps settings that would be silent or painful. |
| **UI** | Runs on core 0. Runs the menus: debounces the 7 buttons, reads the data knob (with acceleration), and draws the green-terminal screen over SPI with DMA (font, scanlines, glow, cursor). Never delays a chip write. |

## 5. Hardware

### 5.1 Block diagram

```
Pico USB-C ── VBUS 5V ──────┬─ ferrite + caps ── YM2612, 74HCT buffers
                           ├─ ferrite + LC filter ── low-noise LDO 4.5V ── op-amps (analog rail)
                           ├─ Pico's own 3.3V regulator ── Pico
                           └─ ferrite + 3.3V regulator ── display (its own, to keep display noise off the audio)

Pico GPIO ── 2× 74HCT541 ── YM2612 (DIP socket) ── OPA2350 filter ─┬─ NJM4556A ── 3.5 mm headphones
                                                                   └─ OPA2350 inverter ── 2× 1/4" TRS balanced
     ├── SPI ── 1.9" LCD
     └── 7 buttons + data knob to GND
```

### 5.2 Parts (Proposal)

| Part | Choice | Rough cost |
| --- | --- | --- |
| Microcontroller | **Pimoroni Pico Plus 2** (RP2350, 16 MB flash, 8 MB PSRAM, USB-C), Pico-sized, soldered by its castellated edges or on headers | $12–15 |
| Sound chip | YM2612, pulled from a Model 1 Genesis or bought tested | $5–15 |
| Chip socket | 24-pin DIP, turned-pin | $0.50 |
| Level shifting | 2× 74HCT541 (one-way 3.3V → 5V buffers, powered from 5V) | $1 |
| Filter / buffer | OPA2350 low-noise, rail-to-rail dual op-amp rated for 2.7–5.5V (L and R) | $2 |
| Headphone driver | NJM4556A dual op-amp, AC-coupled output | $1 |
| Balanced driver | OPA2350 dual op-amp making the inverted (cold) leg for L and R | $2 |
| Analog supply | Low-noise LDO (about 4.5V, for example TPS7A20) plus LC filter | $1 |
| Audio jacks | 3.5 mm stereo headphone jack + 2× 1/4" TRS panel jacks | $3–4 |
| Display | 1.9" 320×170 IPS TFT, ST7789 controller, SPI, on a breakout module with header pins | $4–8 |
| Display supply | Small 3.3V LDO plus ferrite, just for the display and its backlight | $0.50 |
| Buttons | 7× 6 mm tactile switches (or 12 mm with caps for a synth feel) | $0.70–3 |
| Data knob | Rotary encoder, no push switch needed (EC11 type), with a knob cap | $1 |
| Power and file loading | The Pico board's own USB-C port (no extra connector) | $0 |
| Passives | Decoupling, ferrites, op-amp resistors and caps, output caps | $2 |
| PCB | 2-layer, about 100 × 70 mm | about $1 each in a batch of 5 |

**Rough total: $35–45 per board** before the enclosure, mostly depending on the YM2612's price.

### 5.3 Cost savers in this design

- **No crystal oscillator for the chip.** The RP2350 runs at 153.33 MHz (12 MHz × 115 ÷ 9),
  and its clock-output pin divides that by 20 to give **7.667 MHz**, within 0.05% of
  a real Genesis (less than 1 cent of pitch). The clock goes through a spare 74HCT541
  channel to reach 5V levels. **Proposal:** add an unpopulated footprint for an oscillator
  can as a fallback.
- **No busy-flag reads,** so the buffers only go one way and /RD is tied high.
- **No memory card, USB connector, regulator, or power switch.** The Pico board's USB-C port loads files and powers everything.
- **No volume control** (see §8).

### 5.4 Pin map (Proposal)

Consecutive pins keep the PIO program simple. The Pico Plus 2 uses the standard Pico header for GP0–GP28. Check each pin against its pinout in KiCad.

| Pico GPIO | Signal | Goes to |
| --- | --- | --- |
| GP0–GP7 | D0–D7 | 74HCT541 #1 → YM2612 data bus |
| GP8 | A0 | 74HCT541 #2 → YM2612 |
| GP9 | A1 | 74HCT541 #2 → YM2612 |
| GP10 | /WR | 74HCT541 #2 → YM2612 |
| GP11 | /IC (reset) | 74HCT541 #2 → YM2612 |
| GP21 | Clock out (GPOUT0) | 74HCT541 #2 → YM2612 φM |
| GP12 | Display D/C | LCD |
| GP13 | Display CS | LCD |
| GP14 | Display SCK (SPI1) | LCD |
| GP15 | Display MOSI (SPI1) | LCD |
| — | Display reset tied to the Pico's RUN pin; backlight always on through a resistor | LCD |
| GP16 | Button Play | to GND, internal pull-up |
| GP17 | Button Stop | to GND, internal pull-up |
| GP18 | Button ◀ | to GND, internal pull-up |
| GP19 | Button ▶ | to GND, internal pull-up |
| GP20 | Button Edit | to GND, internal pull-up |
| GP22 | Button Exit | to GND, internal pull-up |
| GP26 | Button Write | to GND, internal pull-up |
| GP27 | Data knob A | encoder, internal pull-up |
| GP28 | Data knob B | encoder, internal pull-up |
| — | /CS tied low, /RD tied high | YM2612 |

### 5.5 Audio output and the −70 dB target

**Signal path**

- MOL and MOR each go through a load resistor into an **OPA2350** stage that buffers and
  low-pass filters them, based on a known-good Genesis Model 1 output stage.
- From there, each channel splits two ways:
  - **Headphones:** an NJM4556A drives the 3.5 mm jack through about 220 µF output capacitors.
  - **Balanced line out:** the filter output is the *hot* leg, and a second OPA2350 makes an
    inverted *cold* leg. Both go through 100 Ω resistors and DC-blocking capacitors to a 1/4"
    TRS jack (tip = hot, ring = cold, sleeve = ground). A 5V board can only swing about 3 V
    per leg, but balanced doubles that between hot and cold, so the line out reaches about
    2 V RMS.

**Why balanced:** in the studio, the player is on USB to the PC and its audio goes into an
audio interface on the same PC. That creates a ground loop, the usual cause of hum and USB
whine. A balanced input on the interface rejects noise that appears equally on hot and cold,
so the loop stops mattering.

**Target:** idle noise floor **at or below −70 dB relative to full-scale output**, 20 Hz–20 kHz,
measured on the balanced outs into an audio interface with the player on USB to the same PC.
That level of hiss is easy for these op-amps. The work is keeping digital noise out:

- **Analog rail:** USB 5V → ferrite → LC filter → low-noise LDO (about 4.5V) for the op-amps
  only. The 2.25V mid-rail reference gets its own RC filter and a large capacitor.
- **Grounds:** a solid analog ground area under the audio section, joined to digital ground at
  one point. USB, the bus, and the clock never cross the analog area.
- **The chip:** the YM2612's own supply gets its own ferrite and decoupling, and its outputs
  leave on short traces straight into the analog section.
- **Spare footprints:** room for an extra filter stage and a ground-lift resistor, in case
  measurements in M4 call for them.

While music plays, the YM2612's own 9-bit DAC adds its well-known grit. That's the chip's
character, not noise from the board, and it isn't part of the −70 dB figure.

### 5.6 Protecting the chip

- Series resistors (about 100 Ω) on every buffer output into the YM2612.
- The YM2612 is socketed and only gets 5V through a ferrite and decoupling right at its pins.
- Keep a spare YM2612 on hand. Buy from a seller with returns, since pulled and fake chips are common.

## 6. KiCad notes for Joey's "YM2612 player" project

- Symbols you may need to make: YM2612 (DIP-24) and the display module's header (check the exact module's pin order; ST7789 breakouts differ).
  The Pico Plus 2 uses the standard Pico footprint (Raspberry Pi's official KiCad footprint works).
- Put the YM2612, buffers, and op-amps on the 5V side of the board, and the display connector on the 3.3V side. Keep the display cable and its backlight current away from the audio corner.
- Keep the 7.67 MHz clock trace short, and away from the audio traces.
- Place the headphone jack, both 1/4" TRS jacks, and the Pico board's USB-C port on board edges so the case can expose them.
- Keep the analog section (op-amps, LDO, jacks) in one corner, away from the Pico, bus, and clock.
- Add test points for D0–D7, A0, A1, /WR, and the clock for the logic analyzer in M1.

## 7. Milestones

| # | Milestone | Done when |
| --- | --- | --- |
| M0 | **Parts in hand** | Tested-good YM2612 (plus a spare), Pico Plus 2, buffers, op-amps, display |
| M1 | **First sound** | Breadboard: the Pico clocks the YM2612 and plays a hard-coded FM note; write gap measured |
| M2 | **Play a VGM** | Files dragged on over USB-C appear on the drive, and a Genesis VGM plays start to finish, samples included |
| M3 | **Screen + panel** | Green-terminal home screen with file name and time; data knob, ◀ ▶, Play, Stop working |
| M3a | **Menus + editing** | Every menu page works; edits are heard live on a playing song and in MIDI mode; Write saves `.edt` and `.tfi` files |
| M3b | **MIDI mode** | A USB keyboard or DAW plays 6-note chords on the YM2612 using built-in and borrowed instruments |
| M4 | **Quiet audio** | Idle noise floor at or below −70 dB on the balanced outs into an interface on the same PC; no hum or whine on headphones |
| M5 | **Schematic + PCB** | Joey's KiCad project matches this doc; boards ordered |
| M6 | **Rev A built** | Assembled board loads files over USB-C and plays them in a simple case |

## 8. Open questions

- [ ] **Headphone volume:** the balanced outs stay at a fixed line level, but the headphone jack may be
  loud. Add a small dual volume wheel on the headphone output only (about $0.50)?
- [x] **Display:** 1.9" 320×170 ST7789 IPS LCD with the green terminal drawn in software (Joey, Oct 24).
- [ ] **Buttons:** small 6 mm tactile switches, or larger synth-style buttons with caps?
- [ ] **Clock:** Pico-generated clock (proposed), or an oscillator can for exact Genesis pitch?
- [x] **File loading:** over USB-C into the board's flash, no microSD (Joey, Oct 24).
- [ ] **VGZ:** proposed as required in Rev A, since zipped files stretch the 16 MB of storage.

## 9. Glossary

- **VGM / VGZ:** "Video Game Music", a recording of every chip write a game made, with timing. VGZ is the zipped version.
- **GD3 tag:** the part of a VGM file that holds the track title, game, and composer.
- **Register:** a tiny memory slot in the chip; writing a number to it changes pitch, volume, or tone.
- **PIO:** programmable I/O blocks on the RP2350 that toggle pins with exact timing.
- **DAC:** the YM2612's sample-playback mode on channel 6, used for drums and voices.
- **PSG:** the Genesis's second, simpler sound chip. Rev A doesn't play its parts.
- **Level shifting:** converting the Pico's 3.3V signals to the 5V the YM2612 expects.
