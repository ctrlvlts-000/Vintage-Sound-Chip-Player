#!/usr/bin/env python3
"""Builds simple stand-in 3D models for the parts KiCad's library has no model for, attaches them to a copy of
the board, and exports a STEP of the whole board for the enclosure design.

    python3 make_3d.py <board.kicad_pcb> <out.step>

Needs KiCad 7+ (pcbnew python, kicad-cli, kicad-packages3d) and cadquery. Every stand-in is a box/cylinder sized
from datasheets or typical parts, so check the marked heights against the real parts before printing.
Model coordinates follow KiCad: origin at the footprint origin, +X right, +Y towards the board's rear (up on
screen), +Z up from the board's top face.
"""
import os
import subprocess
import sys

import cadquery as cq
import pcbnew

board_path, out_step = sys.argv[1], os.path.abspath(sys.argv[2])
shapes = os.path.join(os.path.dirname(os.path.abspath(board_path)), "ym2612.3dshapes")
os.makedirs(shapes, exist_ok=True)


def box(x0, x1, y0, y1, z0, z1):
    """Box from footprint coordinates (y down, as in the footprint editor)."""
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, -y1, z0))


def cyl(x, y, d, z0, z1):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, -y, z0))


def save(name, *parts):
    a = cq.Assembly()
    for i, (shape, color) in enumerate(parts):
        a.add(shape, name=f"{name}_{i}", color=cq.Color(*color))
    path = os.path.join(shapes, name + ".step")
    a.save(path)  # STEP is picked from the extension
    return path


BLACK, GREY, METAL, GREEN, BLUE, RED = ((0.1, 0.1, 0.1), (0.4, 0.4, 0.4), (0.75, 0.75, 0.78),
                                               (0.1, 0.45, 0.2), (0.15, 0.3, 0.8), (0.75, 0.1, 0.1))

# 12 mm tactile switch (Omron B3F-4055 class) with a snap-on round cap. Body 12 x 12 x 3.5, plunger to 7.3 mm,
# cap 12 mm round reaching about 12 mm above the board (approximate: depends on the cap bought).
CAP_TOP = 12.0
button = save("SW_PUSH_12mm_with_cap",
              (box(0.25, 12.25, -3.5, 8.5, 0, 3.5), BLACK),
              (cyl(6.25, 2.5, 6.5, 3.5, 7.3), GREY),
              (cyl(6.25, 2.5, 12.0, 7.3, CAP_TOP), RED))

# Alps EC11E vertical encoder, 20 mm shaft (H20). Body 12 x 11.6 x 6.5, M7 bushing to 11.5 mm, 6 mm shaft to 20 mm.
# No knob: the knob is chosen with the case.
encoder = save("EC11E_Vertical_H20mm",
               (box(1.5, 13.5, -3.3, 8.3, 0, 6.5), METAL),
               (cyl(7.5, 2.5, 7.0, 6.5, 11.5), METAL),
               (cyl(7.5, 2.5, 6.0, 11.5, 20.0), METAL))

# Neutrik NMJ6HCD2 1/4" jack. Body outline from the footprint's fab layer (20.6 x 18.2), body height ~17 mm
# (approximate), chrome nose 11.4 mm across, 3 mm long, centred ~8.5 mm above the board.
JACK_H, NOSE_Z = 17.0, 8.5
nose = cq.Workplane("YZ").circle(11.4 / 2).extrude(3.0).translate((16.7, -8.115, NOSE_Z))
jack = save("Neutrik_NMJ6HCD2_Horizontal",
            (box(-3.91, 16.7, -0.985, 17.215, 0, JACK_H), BLACK),
            (box(-6.83, -3.91, 3.765, 12.465, 0, 10.0), BLACK),
            (nose, METAL))

# Pimoroni Pico Plus 2 on two 1x20 female sockets (8.5 mm), sitting on its own male headers (2.5 mm spacer):
# module underside at 11 mm, 1 mm board, USB-C 3.2 mm high on top at the pin 1 end.
SOCK, SPACER, PCB = 8.5, 2.5, 1.0
z_pcb = SOCK + SPACER
pico = save("Pimoroni_PicoPlus2_on_sockets",
            (box(-8.89 - 1.27, -8.89 + 1.27, -25.4, 25.4, 0, SOCK), BLACK),
            (box(8.89 - 1.27, 8.89 + 1.27, -25.4, 25.4, 0, SOCK), BLACK),
            (box(-8.89 - 1.27, -8.89 + 1.27, -25.4, 25.4, SOCK, z_pcb), BLACK),
            (box(8.89 - 1.27, 8.89 + 1.27, -25.4, 25.4, SOCK, z_pcb), BLACK),
            (box(-10.5, 10.5, -25.5, 25.5, z_pcb, z_pcb + PCB), BLACK),
            (box(-6.0, 6.0, -6.0, 6.0, z_pcb + PCB, z_pcb + PCB + 1.0), GREY),          # RP2350 + flash
            (box(-4.47, 4.47, -26.8, -19.5, z_pcb + PCB, z_pcb + PCB + 3.2), METAL))    # USB-C

# HiLetgo 2004A 20x4 LCD on four 15 mm M3 standoffs, attached at the rear-left standoff (H5). Module board
# 98 x 60 x 1.6, metal bezel 97 x 40 x 9 on top, PCF8574 I2C backpack (41.5 x 19) hanging 9 mm below it under
# the pin row at the rear-left. The text reads from the front of the case.
STANDOFF, LCD_PCB = 15.0, 1.6
top = STANDOFF + LCD_PCB
x0, y0 = -2.5, -2.5                      # module corner relative to H5 (holes 93 x 55 on a 98 x 60 board)
lcd = save("LCD_2004A_I2C_on_15mm_standoffs",
           (box(x0, x0 + 98, y0, y0 + 60, STANDOFF, top), GREEN),
           (box(x0 + 0.5, x0 + 97.5, y0 + 10, y0 + 50, top, top + 9.0), BLUE),
           (box(x0 + 8.0, x0 + 49.5, y0 + 0.5, y0 + 19.5, STANDOFF - 9.0, STANDOFF), GREY))
standoff = save("Standoff_M3_hex_15mm", (cyl(0, 0, 5.5, 0, STANDOFF), METAL))

# YM2612 (DIP-24) seated in its turned-pin socket.
chip = "${KICAD7_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-24_W15.24mm.step"


def model(path, z=0.0):
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = path
    m.m_Offset = pcbnew.VECTOR3D(0, 0, z)
    m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)
    m.m_Rotation = pcbnew.VECTOR3D(0, 0, 0)
    return m


board = pcbnew.LoadBoard(board_path)
for fp in board.GetFootprints():
    ref, models = fp.GetReference(), fp.Models()
    fpid = fp.GetFPID().GetUniStringLibItemName()
    if ref in ("J1", "X1"):          # not fitted
        models.clear()
    elif fpid == "SW_PUSH-12mm":
        models.clear(); models.push_back(model(button))
    elif fpid.startswith("RotaryEncoder_Alps_EC11E"):
        models.clear(); models.push_back(model(encoder))
    elif fpid.startswith("Jack_6.35mm_Neutrik_NMJ6HCD2"):
        models.clear(); models.push_back(model(jack))
    elif fpid.startswith("WQFN-16-1EP_3x3mm"):   # the 1.68 mm pad variant has no model; same package outline
        models.clear(); models.push_back(model("${KICAD7_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/WQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm.step"))
    elif ref == "U2":
        models.clear(); models.push_back(model(pico))
    elif ref == "U5":
        models.push_back(model(chip, 3.5))
    elif ref in ("H5", "H6", "H7", "H8"):
        models.clear(); models.push_back(model(standoff))
        if ref == "H5":
            models.push_back(model(lcd))
tmp = os.path.join(os.path.dirname(os.path.abspath(board_path)), "_3d_export.kicad_pcb")
board.Save(tmp)
env = dict(os.environ, KICAD6_3DMODEL_DIR="/usr/share/kicad/3dmodels", KICAD7_3DMODEL_DIR="/usr/share/kicad/3dmodels")
subprocess.run(["kicad-cli", "pcb", "export", "step", "--subst-models", "--force", "-o", out_step, tmp],
               env=env, check=True)
os.remove(tmp)
