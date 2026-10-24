"""Tiny KiCad 7 schematic writer used to make the first draft of the YM2612 player schematic.

Every pin connection is made with a short wire stub plus a net label (or a power
symbol), so the drawing reads like a wiring list. Once the schematic is edited in
KiCad, the KiCad files become the source of truth and this script is no longer needed.
"""
import math
import os
import re
import uuid as uuidlib

KICAD_SYMBOLS = os.environ.get("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")
PROJECT = os.environ.get("YM_PROJECT", "ym2612_player")
TITLE = "YM2612 player"
DATE = "2026-10-24"
REV = "A0.1"
COMPANY = "YM2612"
POWER_NETS = {"GND": "power:GND", "GNDA": "power:GNDA", "+5V": "power:+5V", "+3V3": "power:+3V3",
              "+5V_YM": "ym2612:+5V_YM", "+4V5A": "ym2612:+4V5A"}
STUB = 2.54

_uuid_counter = [0]


def new_uuid():
    # Deterministic UUIDs so regenerating gives a stable diff.
    _uuid_counter[0] += 1
    return str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, f"ym2612-player/{_uuid_counter[0]}"))


# ---------------------------------------------------------------- s-expressions

def tokenize(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "()":
            yield c
            i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while s[j] != '"':
                if s[j] == "\\":
                    j += 1
                buf.append(s[j])
                j += 1
            yield ("str", "".join(buf))
            i = j + 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in "()":
                j += 1
            yield s[i:j]
            i = j


def parse(s):
    stack = [[]]
    for t in tokenize(s):
        if t == "(":
            stack.append([])
        elif t == ")":
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(t[1] if isinstance(t, tuple) else t)
    return stack[0][0]


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def fmt(v):
    v = round(v, 4)
    if v == int(v):
        return str(int(v))
    return ("%.4f" % v).rstrip("0").rstrip(".")


# ---------------------------------------------------------------- symbol library

class LibSymbol:
    def __init__(self, lib_id, text):
        self.lib_id = lib_id
        self.name = lib_id.split(":", 1)[1]
        self.text = text
        tree = parse(text)
        self.pins = []  # dict(number, name, type, x, y, angle, unit, hidden)
        self.props = {}
        for item in tree[2:]:
            if not isinstance(item, list):
                continue
            if item[0] == "property":
                at = next(x for x in item if isinstance(x, list) and x[0] == "at")
                self.props[item[1]] = (float(at[1]), float(at[2]), float(at[3]))
            if item[0] == "symbol":
                m = re.match(r".*_(\d+)_(\d+)$", item[1])
                unit = int(m.group(1))
                for p in item[2:]:
                    if isinstance(p, list) and p[0] == "pin":
                        at = next(x for x in p if isinstance(x, list) and x[0] == "at")
                        name = next(x for x in p if isinstance(x, list) and x[0] == "name")[1]
                        num = next(x for x in p if isinstance(x, list) and x[0] == "number")[1]
                        self.pins.append(dict(number=num, name=name, type=p[1], x=float(at[1]), y=float(at[2]),
                                              angle=float(at[3]), unit=unit, hidden="hide" in p))
        self.units = sorted({p["unit"] for p in self.pins if p["unit"] > 0}) or [1]

    def embedded(self):
        return self.text.replace(f'(symbol "{self.name}"', f'(symbol "{self.lib_id}"', 1)


_lib_cache = {}


def _extract(text, name):
    start = text.find(f'\n  (symbol "{name}"')
    if start < 0:
        raise KeyError(name)
    start += 1
    depth = 0
    i = start
    in_str = False
    while True:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1


def load_symbol(lib_id, local_libs):
    if lib_id in _lib_cache:
        return _lib_cache[lib_id]
    lib, name = lib_id.split(":", 1)
    path = local_libs.get(lib) or os.path.join(KICAD_SYMBOLS, lib + ".kicad_sym")
    text = open(path).read()
    blk = _extract(text, name)
    m = re.match(r'\s*\(symbol "[^"]+" \(extends "([^"]+)"\)', blk)
    if m:
        # Flatten a derived symbol: parent's drawing and pins, child's fields.
        parent = _extract(text, m.group(1))
        child_props = {pm.group(1): pm.group(0) for pm in re.finditer(r'\(property "([^"]+)" "(?:[^"\\]|\\.)*"', blk)}
        flat = parent.replace(f'"{m.group(1)}', f'"{name}')
        for key, prop in child_props.items():
            flat = re.sub(r'\(property "' + re.escape(key) + r'" "(?:[^"\\]|\\.)*"', lambda _: prop, flat, count=1)
        blk = flat
    sym = LibSymbol(lib_id, blk)
    _lib_cache[lib_id] = sym
    return sym


# ---------------------------------------------------------------- geometry

def rot_point(px, py, rot):
    """Library point (y up) -> schematic offset (y down) for a symbol rotated by rot (CCW on screen)."""
    x, y = px, -py
    t = math.radians(rot)
    return (x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t))


def outward(angle, rot):
    """Visual direction pointing away from the body, as (dx, dy) in schematic coords and an angle."""
    a = (angle + rot + 180) % 360
    return (round(math.cos(math.radians(a))), -round(math.sin(math.radians(a)))), a


# ---------------------------------------------------------------- schematic

class Part:
    def __init__(self, sheet, lib_id, ref, value, x, y, nets, rot=0, unit=1, fields=None, dnp=False, stagger=False):
        # stagger: alternate short and long wire stubs so power symbols on neighbouring pins don't overlap.
        self.stagger = stagger
        self.sheet, self.lib_id, self.ref, self.value = sheet, lib_id, ref, value
        self.x, self.y, self.nets, self.rot, self.unit = x, y, nets, rot, unit
        self.fields = fields or {}
        self.dnp = dnp
        self.uuid = new_uuid()


class Sheet:
    def __init__(self, project, filename, title, paper="A3"):
        self.project, self.filename, self.title, self.paper = project, filename, title, paper
        self.parts, self.texts = [], []
        self.uuid = new_uuid()      # uuid of the sheet file
        self.sym_uuid = new_uuid()  # uuid of the sheet symbol on the root sheet
        project.sheets.append(self)

    def add(self, lib_id, prefix, value, x, y, nets, rot=0, unit=1, ref=None, **kw):
        if ref is None:
            ref = self.project.next_ref(prefix)
        p = Part(self, lib_id, ref, value, x, y, nets, rot, unit, **kw)
        self.parts.append(p)
        return p

    def text(self, x, y, s, size=1.8):
        self.texts.append((x, y, s, size))


class Project:
    def __init__(self, local_libs):
        self.local_libs = local_libs
        self.sheets = []
        self.counters = {}
        self.root_uuid = new_uuid()

    def next_ref(self, prefix):
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        return f"{prefix}{self.counters[prefix]}"

    def sym(self, lib_id):
        return load_symbol(lib_id, self.local_libs)

    # ------------------------------------------------------------ checks
    def net_map(self):
        nets = {}
        for sh in self.sheets:
            for p in sh.parts:
                for num, net in p.nets.items():
                    if net == "NC":
                        continue
                    nets.setdefault(net, []).append((sh, p, num))
        return nets

    def check(self):
        problems = []
        for sh in self.sheets:
            for p in sh.parts:
                sym = self.sym(p.lib_id)
                unit_pins = [pin for pin in sym.pins if pin["unit"] in (0, p.unit)]
                nums = {pin["number"] for pin in unit_pins}
                for num in p.nets:
                    if num not in nums:
                        problems.append(f"{p.ref}: no pin {num} in {p.lib_id} unit {p.unit}")
                for pin in unit_pins:
                    if pin["type"] == "no_connect" or pin["hidden"]:
                        continue
                    if pin["number"] not in p.nets:
                        problems.append(f"{p.ref}: pin {pin['number']} ({pin['name']}) left unassigned")
        for net, users in self.net_map().items():
            if len(users) < 2 and net not in POWER_NETS:
                problems.append(f"net {net} has only one connection ({users[0][1].ref}.{users[0][2]})")
        return problems

    # ------------------------------------------------------------ writing
    def write(self, outdir):
        nets = self.net_map()
        global_nets = {n for n, users in nets.items() if len({u[0].filename for u in users}) > 1}
        for sh in self.sheets:
            with open(os.path.join(outdir, sh.filename), "w") as f:
                f.write(self._sheet_text(sh, global_nets))
        with open(os.path.join(outdir, PROJECT + ".kicad_sch"), "w") as f:
            f.write(self._root_text())

    def _path(self, sh):
        return f"/{self.root_uuid}/{sh.sym_uuid}"

    def _sheet_text(self, sh, global_nets):
        out = []
        used = []
        for p in sh.parts:
            if p.lib_id not in used:
                used.append(p.lib_id)
        body = []
        pwr_count = [0]

        def power_symbol(net, x, y, direction_angle):
            lib_id = POWER_NETS[net]
            if lib_id not in used:
                used.append(lib_id)
            # GND art hangs below its pin; supply art sits above it.
            if net == "GND":
                rot = {270: 0, 90: 180, 180: 270, 0: 90}[direction_angle]
            else:
                rot = {90: 0, 270: 180, 180: 90, 0: 270}[direction_angle]
            pwr_count[0] += 1
            ref = f"#PWR{len(self.sheets) * 0 + self.sheets.index(sh) + 1:01d}{pwr_count[0]:03d}"
            vx, vy = rot_point(0, -3.81 if net == "GND" else 3.556, rot)
            u = new_uuid()
            body.append(
                f'  (symbol (lib_id {q(lib_id)}) (at {fmt(x)} {fmt(y)} {rot}) (unit 1)\n'
                f'    (in_bom yes) (on_board yes) (dnp no)\n'
                f'    (uuid {u})\n'
                f'    (property "Reference" {q(ref)} (at {fmt(x)} {fmt(y)} 0)\n'
                f'      (effects (font (size 1.27 1.27)) hide)\n    )\n'
                f'    (property "Value" {q(net)} (at {fmt(x + vx)} {fmt(y + vy)} 0)\n'
                f'      (effects (font (size 1.27 1.27)))\n    )\n'
                f'    (property "Footprint" "" (at {fmt(x)} {fmt(y)} 0)\n'
                f'      (effects (font (size 1.27 1.27)) hide)\n    )\n'
                f'    (property "Datasheet" "" (at {fmt(x)} {fmt(y)} 0)\n'
                f'      (effects (font (size 1.27 1.27)) hide)\n    )\n'
                f'    (pin "1" (uuid {new_uuid()}))\n'
                f'    (instances\n      (project {q(PROJECT)}\n'
                f'        (path {q(self._path(sh))}\n          (reference {q(ref)}) (unit 1)\n        )\n      )\n    )\n'
                f'  )\n')

        for p in sh.parts:
            sym = self.sym(p.lib_id)
            # Symbol instance.
            props = []
            two_pin_sideways = p.rot in (90, 270) and len(sym.pins) == 2
            for k, (name, val) in enumerate((("Reference", p.ref), ("Value", p.value))):
                if two_pin_sideways:
                    # Sideways resistors/caps: reference above, value below, both readable left to right.
                    props.append((name, val, p.x, p.y + (-2.54 if k == 0 else 2.54), p.rot % 180, False))
                    continue
                lx, ly, la = sym.props.get(name, (0, 0, 0))
                ox, oy = rot_point(lx, ly, p.rot)
                ang = la  # field angles are relative to the symbol's own rotation
                props.append((name, val, p.x + ox, p.y + oy, ang, False))
            props.append(("Footprint", p.fields.get("Footprint", ""), p.x, p.y, 0, True))
            props.append(("Datasheet", p.fields.get("Datasheet", ""), p.x, p.y, 0, True))
            for k, v in p.fields.items():
                if k not in ("Footprint", "Datasheet"):
                    props.append((k, v, p.x, p.y, 0, True))
            s = (f'  (symbol (lib_id {q(p.lib_id)}) (at {fmt(p.x)} {fmt(p.y)} {p.rot}) (unit {p.unit})\n'
                 f'    (in_bom yes) (on_board yes) (dnp {"yes" if p.dnp else "no"})\n'
                 f'    (uuid {p.uuid})\n')
            for name, val, x, y, ang, hide in props:
                s += (f'    (property {q(name)} {q(val)} (at {fmt(x)} {fmt(y)} {fmt(ang)})\n'
                      f'      (effects (font (size 1.27 1.27)){" hide" if hide else ""})\n    )\n')
            for pin in sym.pins:
                if pin["unit"] in (0, p.unit):
                    s += f'    (pin {q(pin["number"])} (uuid {new_uuid()}))\n'
            s += (f'    (instances\n      (project {q(PROJECT)}\n'
                  f'        (path {q(self._path(sh))}\n          (reference {q(p.ref)}) (unit {p.unit})\n        )\n      )\n    )\n'
                  f'  )\n')
            body.append(s)

            # Connections.
            done = set()
            k = 0
            for pin in sorted(sym.pins, key=lambda q: (q["angle"], q["x"], q["y"])):
                if pin["unit"] not in (0, p.unit) or pin["number"] not in p.nets:
                    continue
                net = p.nets[pin["number"]]
                ox, oy = rot_point(pin["x"], pin["y"], p.rot)
                px, py = round(p.x + ox, 3), round(p.y + oy, 3)
                if (px, py) in done:
                    continue  # stacked pins share one label
                done.add((px, py))
                if net == "NC":
                    body.append(f'  (no_connect (at {fmt(px)} {fmt(py)}) (uuid {new_uuid()}))\n')
                    continue
                (dx, dy), a = outward(pin["angle"], p.rot)
                stub = STUB * (3 if p.stagger and k % 2 else 1)
                k += 1
                ex, ey = px + dx * stub, py + dy * stub
                body.append(f'  (wire (pts (xy {fmt(px)} {fmt(py)}) (xy {fmt(ex)} {fmt(ey)}))\n'
                            f'    (stroke (width 0) (type default))\n    (uuid {new_uuid()})\n  )\n')
                if net in POWER_NETS:
                    power_symbol(net, ex, ey, int(a))
                    continue
                justify = "left" if a in (0, 90) else "right"
                if net in global_nets:
                    body.append(
                        f'  (global_label {q(net)} (shape passive) (at {fmt(ex)} {fmt(ey)} {int(a)}) (fields_autoplaced)\n'
                        f'    (effects (font (size 1.27 1.27)) (justify {justify}))\n'
                        f'    (uuid {new_uuid()})\n'
                        f'    (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {fmt(ex)} {fmt(ey)} 0)\n'
                        f'      (effects (font (size 1.27 1.27)) hide)\n    )\n  )\n')
                else:
                    body.append(
                        f'  (label {q(net)} (at {fmt(ex)} {fmt(ey)} {int(a)}) (fields_autoplaced)\n'
                        f'    (effects (font (size 1.27 1.27)) (justify {justify} bottom))\n'
                        f'    (uuid {new_uuid()})\n  )\n')

        for x, y, s, size in sh.texts:
            body.append(f'  (text {q(s)} (at {fmt(x)} {fmt(y)} 0)\n'
                        f'    (effects (font (size {size} {size})) (justify left top))\n'
                        f'    (uuid {new_uuid()})\n  )\n')

        out.append(f'(kicad_sch (version 20230121) (generator eeschema)\n\n  (uuid {sh.uuid})\n\n'
                   f'  (paper {q(sh.paper)})\n\n'
                   f'  (title_block\n    (title {q(sh.title)})\n    (date {q(DATE)})\n    (rev {q(REV)})\n'
                   f'    (company {q(COMPANY)})\n    (comment 1 "YM2612 player Rev A, draft for review")\n  )\n\n'
                   f'  (lib_symbols\n')
        for lib_id in used:
            out.append("    " + self.sym(lib_id).embedded().replace("\n", "\n  ") + "\n")
        out.append("  )\n\n")
        out.extend(body)
        out.append(")\n")
        return "".join(out)

    def _root_text(self):
        s = (f'(kicad_sch (version 20230121) (generator eeschema)\n\n  (uuid {self.root_uuid})\n\n'
             f'  (paper "A4")\n\n'
             f'  (title_block\n    (title {q(TITLE + " Rev A")})\n    (date {q(DATE)})\n    (rev {q(REV)})\n'
             f'    (company {q(COMPANY)})\n    (comment 1 "Top sheet: double-click a box to open that page")\n  )\n\n'
             f'  (lib_symbols\n  )\n\n')
        x0, y0, w, h = 30.48, 40.64, 50.8, 20.32
        for i, sh in enumerate(self.sheets):
            x = x0 + (i % 3) * (w + 15.24)
            y = y0 + (i // 3) * (h + 25.4)
            s += (f'  (sheet (at {fmt(x)} {fmt(y)}) (size {fmt(w)} {fmt(h)}) (fields_autoplaced)\n'
                  f'    (stroke (width 0.1524) (type solid))\n'
                  f'    (fill (color 0 0 0 0.0000))\n'
                  f'    (uuid {sh.sym_uuid})\n'
                  f'    (property "Sheetname" {q(sh.title)} (at {fmt(x)} {fmt(y - 0.7116)} 0)\n'
                  f'      (effects (font (size 1.27 1.27)) (justify left bottom))\n    )\n'
                  f'    (property "Sheetfile" {q(sh.filename)} (at {fmt(x)} {fmt(y + h + 0.5846)} 0)\n'
                  f'      (effects (font (size 1.27 1.27)) (justify left top))\n    )\n'
                  f'    (instances\n      (project {q(PROJECT)}\n'
                  f'        (path {q("/" + self.root_uuid)} (page {q(str(i + 2))}))\n      )\n    )\n'
                  f'  )\n')
        s += self._root_notes()
        s += ('  (sheet_instances\n    (path "/" (page "1"))\n  )\n)\n')
        return s

    root_notes = ""

    def _root_notes(self):
        if not self.root_notes:
            return ""
        return (f'  (text {q(self.root_notes)} (at 30.48 140 0)\n'
                f'    (effects (font (size 1.8 1.8)) (justify left top))\n'
                f'    (uuid {new_uuid()})\n  )\n')
