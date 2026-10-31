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
DATE = "2026-10-31"
REV = "B0.1"
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
                        ln = next((float(x[1]) for x in p if isinstance(x, list) and x[0] == "length"), 0.0)
                        self.pins.append(dict(number=num, name=name, type=p[1], x=float(at[1]), y=float(at[2]),
                                              angle=float(at[3]), unit=unit, hidden="hide" in p, length=ln))
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
    def __init__(self, sheet, lib_id, ref, value, x, y, nets, rot=0, unit=1, fields=None, dnp=False, stagger=False,
                 labelled=False):
        # stagger: unused since the wiring pass (kept so older calls still work).
        # labelled: connect this part's pins with net labels instead of wires (test points, far-off connectors).
        self.stagger = stagger
        self.labelled = labelled
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
        pins = []
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
                if name == "Value" and getattr(p, "value_at", None):
                    ox, oy = p.value_at      # moved clear of pins on this page (offset from the part, y down)
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

            # Pins, for the wiring pass below.
            for pin in sym.pins:
                if pin["unit"] not in (0, p.unit) or pin["number"] not in p.nets:
                    continue
                ox, oy = rot_point(pin["x"], pin["y"], p.rot)
                (dx, dy), a = outward(pin["angle"], p.rot)
                pins.append((round(p.x + ox, 3), round(p.y + oy, 3), dx, dy, int(a), p.nets[pin["number"]], p))

        body.extend(self._wiring(sh, global_nets, pins, power_symbol))

        for x, y, s, size in sh.texts:
            body.append(f'  (text {q(s)} (at {fmt(x)} {fmt(y)} 0)\n'
                        f'    (effects (font (size {size} {size})) (justify left top))\n'
                        f'    (uuid {new_uuid()})\n  )\n')

        out.append(f'(kicad_sch (version 20230121) (generator eeschema)\n\n  (uuid {sh.uuid})\n\n'
                   f'  (paper {q(sh.paper)})\n\n'
                   f'  (title_block\n    (title {q(sh.title)})\n    (date {q(DATE)})\n    (rev {q(REV)})\n'
                   f'    (company {q(COMPANY)})\n    (comment 1 "YM2612 player Rev B, draft for review")\n  )\n\n'
                   f'  (lib_symbols\n')
        for lib_id in used:
            out.append("    " + self.sym(lib_id).embedded().replace("\n", "\n  ") + "\n")
        out.append("  )\n\n")
        out.extend(body)
        out.append(")\n")
        return "".join(out)

    def _wiring(self, sh, global_nets, pins, power_symbol):
        """Wires between the pins of each net on this page (see wires.py), power symbols, labels, no-connect marks."""
        from wires import Router, body_box, g, GRID, NEAR_TEXT as NEAR
        out = []
        r = Router()

        def wire(a, b):
            out.append(f'  (wire (pts (xy {fmt(a[0])} {fmt(a[1])}) (xy {fmt(b[0])} {fmt(b[1])}))\n'
                       f'    (stroke (width 0) (type default))\n    (uuid {new_uuid()})\n  )\n')

        def label(net, x, y, a):
            justify = "left" if a in (0, 90) else "right"
            if net in global_nets:
                out.append(
                    f'  (global_label {q(net)} (shape passive) (at {fmt(x)} {fmt(y)} {a}) (fields_autoplaced)\n'
                    f'    (effects (font (size 1.27 1.27)) (justify {justify}))\n'
                    f'    (uuid {new_uuid()})\n'
                    f'    (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {fmt(x)} {fmt(y)} 0)\n'
                    f'      (effects (font (size 1.27 1.27)) hide)\n    )\n  )\n')
            else:
                out.append(
                    f'  (label {q(net)} (at {fmt(x)} {fmt(y)} {a}) (fields_autoplaced)\n'
                    f'    (effects (font (size 1.27 1.27)) (justify {justify} bottom))\n'
                    f'    (uuid {new_uuid()})\n  )\n')

        def node(x, y):
            return (g(x), g(y))

        def xy(n):
            return (n[0] * GRID, n[1] * GRID)

        # Obstacles: part bodies (with their pin lines) and the page's notes.
        for p in sh.parts:
            bb = body_box(self.sym(p.lib_id), p.unit)
            if bb is None:
                continue
            corners = [rot_point(x, y, p.rot) for x in (bb[0], bb[2]) for y in (bb[1], bb[3])]
            xs = [p.x + c[0] for c in corners]
            ys = [p.y + c[1] for c in corners]
            r.block_box(min(xs), min(ys), max(xs), max(ys))
            r.block_box(min(xs) - 2.54, min(ys) - 2.54, max(xs) + 2.54, max(ys) + 2.54, soft=NEAR)
        for x, y, s, size in sh.texts:
            lines = s.split("\n")
            r.block_box(x - 1.27, y - 1.27, x + max(len(l) for l in lines) * size * 0.95 + 1.27,
                        y + len(lines) * size * 1.65 + 1.27)
        # Pin ends belong to their nets; nothing else may touch them.
        for x, y, dx, dy, a, net, p in pins:
            n = node(x, y)
            r.blocked.discard(n)
            r.claim(n, net)
            r.pins[n] = net
        done = set()
        signal = {}
        tagged = []
        power = {}
        pin_ref = {}
        for x, y, dx, dy, a, net, p in pins:
            n = node(x, y)
            if n in done:
                continue      # stacked pins share one connection
            done.add(n)
            if net == "NC":
                out.append(f'  (no_connect (at {fmt(x)} {fmt(y)}) (uuid {new_uuid()}))\n')
                continue
            if net in POWER_NETS:
                power.setdefault((net, dx, dy, a, p.ref), []).append((n, x, y))
                continue
            if p.labelled:
                tagged.append((net, n, (dx, dy)))
                continue
            signal.setdefault(net, []).append((n, (dx, dy), a))
            pin_ref[n] = p.ref

        # Power pins: a short stub and a power symbol. Neighbouring pins of one part on the same rail (side by side,
        # facing the same way) share one symbol, joined by a wire across their stub ends.
        sym_ends = []
        for (net, dx, dy, a, _), plist in power.items():
            along = 1 if dx else 0          # pins of a run are spread along the other axis
            plist.sort(key=lambda t: t[0][along])
            runs = [[plist[0]]]
            for t in plist[1:]:
                last = runs[-1][-1][0]
                if t[0][1 - along] == last[1 - along] and t[0][along] - last[along] <= 4:
                    runs[-1].append(t)
                else:
                    runs.append([t])
            for run in runs:
                k = 1
                while k < 4:      # stubs long enough to clear the neighbours' power symbols
                    stubs = [[(n[0] + dx * i, n[1] + dy * i) for i in range(1, 2 * k + 1)] for n, _, _ in run]
                    if not any(m in r.blocked or (m in r.owner and r.owner[m] != net) for st in stubs for m in st):
                        break
                    k += 1
                # a neighbouring power symbol (another rail) on the same side: step this one further out, so the
                # two names don't overlap
                end = stubs[0][-1]
                if any(e[1 - along] == end[1 - along] and abs(e[along] - end[along]) <= 4 for e in sym_ends):
                    stubs = [[(n[0] + dx * i, n[1] + dy * i) for i in range(1, 2 * k + 5)] for n, _, _ in run]
                for (n, x, y), st in zip(run, stubs):
                    prevn = n
                    for m in st:
                        r.claim(m, net)
                        r.add_edge(prevn, m, net)
                        prevn = m
                    wire((x, y), xy(st[-1]))
                ends = [st[-1] for st in stubs]
                if len(ends) > 1:
                    for e0, e1 in zip(ends, ends[1:]):
                        wire(xy(e0), xy(e1))      # split at every stub, so KiCad joins each one
                    lo, hi = ends[0][along], ends[-1][along]
                    for v in range(lo, hi + 1):
                        m = (v, ends[0][1]) if along == 0 else (ends[0][0], v)
                        r.claim(m, net)
                    for e in ends[1:-1]:
                        ex, ey = xy(e)
                        out.append(f'  (junction (at {fmt(ex)} {fmt(ey)}) (diameter 0) (color 0 0 0 0)\n'
                                   f'    (uuid {new_uuid()})\n  )\n')
                # one symbol: at the bottom of an upright run for GND (the top for a supply), else mid-run
                if along == 1:
                    sym_end = ends[-1] if net == "GND" else ends[0]
                else:
                    sym_end = ends[len(ends) // 2]
                ex, ey = xy(sym_end)
                # keep the symbol's art clear of wires
                r.block_box(ex + dx * 1.27 - 1.9 * abs(dy) - 0.6 * abs(dx), ey + dy * 1.27 - 1.9 * abs(dx) - 0.6 * abs(dy),
                            ex + dx * 3.81 + 1.9 * abs(dy) + 0.6 * abs(dx), ey + dy * 3.81 + 1.9 * abs(dx) + 0.6 * abs(dy))
                power_symbol(net, ex, ey, a)
                sym_ends.append(sym_end)

        ANGLE = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}

        def label_box(net, end, d):
            w = len(net) * 1.27 + (3.0 if net in global_nets else 1.0)
            ex, ey = xy(end)
            # one grid row either side would collide with the next pin's label at 2.54 mm pitch, so keep to its own row
            return (ex + d[0] * 0.6 - 0.6 * abs(d[1]), ey + d[1] * 0.6 - 0.6 * abs(d[0]),
                    ex + d[0] * w + 0.6 * abs(d[1]), ey + d[1] * w + 0.6 * abs(d[0]))

        def fits(net, n, d, k):
            stub = [(n[0] + d[0] * i, n[1] + d[1] * i) for i in range(1, k + 1)]
            if any(m in r.blocked or m in r.owner for m in stub):
                return None
            if any(frozenset((x, y)) in r.edges for x, y in zip([n] + stub, stub)):
                return None
            x0, y0, x1, y1 = label_box(net, stub[-1], d)
            for i in range(g(min(x0, x1)), g(max(x0, x1)) + 1):
                for j in range(g(min(y0, y1)), g(max(y0, y1)) + 1):
                    if (i, j) in r.blocked or (i, j) in r.owner:
                        return None
            return stub

        def stub_label(net, n, d, must=True):
            stub = None
            for k in (2, 3, 4, 6, 8):
                stub = fits(net, n, d, k)
                if stub:
                    break
            if not stub:
                if not must:
                    return None
                stub = [(n[0] + d[0] * i, n[1] + d[1] * i) for i in (1, 2)]
            prevn = n
            for m in stub:
                r.claim(m, net)
                r.add_edge(prevn, m, net)
                prevn = m
            label(net, *xy(stub[-1]), ANGLE[d])
            r.block_box(*label_box(net, stub[-1], d))
            return stub

        def label_nearby(net, t):
            """A free spot for the label within a few cm of the net, joined to it by its own wire."""
            cx = sum(n[0] for n in t) / len(t)
            cy = sum(n[1] for n in t) / len(t)
            spots = sorted(((i, j) for i in range(int(cx) - 40, int(cx) + 41, 2) for j in range(int(cy) - 40, int(cy) + 41, 2)),
                           key=lambda m: abs(m[0] - cx) + abs(m[1] - cy))
            for m in spots:
                if m in r.blocked or m in r.owner:
                    continue
                for d in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    if not fits(net, (m[0] - d[0], m[1] - d[1]), d, 1):
                        continue
                    path = r.route(net, m, (-d[0], -d[1]), t, limit=200)
                    if path:
                        r.commit(net, path)
                        t |= set(path)
                        label(net, *xy(m), ANGLE[d])
                        r.block_box(*label_box(net, m, d))
                        return True
            return False

        # Wires a page draws by hand (sh.paths: net -> list of corner points), laid down before anything is routed.
        fixed = {}
        for net, pts in getattr(sh, "paths", {}).items():
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                a, b = node(x0, y0), node(x1, y1)
                step = ((b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1]))
                path = [a]
                while path[-1] != b:
                    path.append((path[-1][0] + step[0], path[-1][1] + step[1]))
                r.commit(net, path)
                fixed.setdefault(net, set()).update(path)
        tree = {}
        labelled_nets = set()
        for net, n, d in tagged:
            stub_label(net, n, d)
            labelled_nets.add(net)
        # Global nets get their label first, at the pin with the most room in front of it, so wires leave it space.
        pre = {}
        for net, ps in sorted(signal.items()):
            if net not in global_nets or net in labelled_nets:
                continue
            def room(item):
                n, d, a = item
                free = 0
                for i in range(1, 25):
                    m = (n[0] + d[0] * i, n[1] + d[1] * i)
                    if m in r.blocked or m in r.owner:
                        break
                    free += 1
                return free
            want = getattr(sh, "label_at", {}).get(net)      # a page can name the part whose pin gets the label
            best = max([p for p in ps if pin_ref[p[0]] == want] or ps, key=room)
            stub = stub_label(net, best[0], best[1], must=False)
            if stub:
                pre[net] = (best[0], stub)
                labelled_nets.add(net)
        # Then wire each net, shortest first.
        def span(net):
            ns = [p[0] for p in signal[net]]
            return max(x for x, _ in ns) - min(x for x, _ in ns) + max(y for _, y in ns) - min(y for _, y in ns)
        self.fallbacks = getattr(self, "fallbacks", 0)
        for net in sorted(signal, key=span):
            ps = signal[net]
            t = {pre[net][0], *pre[net][1]} if net in pre else {ps[0][0]}
            t |= fixed.get(net, set())
            todo = [p for p in ps if p[0] not in t]
            failed = []
            while todo:
                todo.sort(key=lambda p: min(abs(p[0][0] - x) + abs(p[0][1] - y) for x, y in t))
                n, d, a = todo.pop(0)
                path = r.route(net, n, d, t, limit=400)
                if path is None:
                    failed.append((n, d, a))
                    continue
                r.commit(net, path)
                t |= set(path)
            tree[net] = t
            if failed:
                labelled_nets.add(net)
                self.fallbacks += len(failed)
                for n, d, a in failed:
                    print("  no wire path for a", net, "pin on", sh.title)
                    stub_label(net, n, d)
        # One label per net that has to be named here: global nets (they leave this page) and nets that fell back to
        # labels. It goes on a pin with room in front of it, or else off the side of one of the net's straight wires.
        for net in sorted(tree):
            if net not in global_nets and net not in labelled_nets:
                continue
            ps = signal[net]
            cands = [(p[0], p[1]) for p in ps if p[0] in tree[net]]
            for n in sorted(tree[net]):
                k = r.kind.get(n)
                if r.owner.get(n) == net and k in ("h", "v"):
                    cands += [(n, (0, -1)), (n, (0, 1))] if k == "h" else [(n, (1, 0)), (n, (-1, 0))]
            if net in pre:
                continue
            for n, d in cands:
                if stub_label(net, n, d, must=False):
                    break
            else:
                if not label_nearby(net, tree[net]):
                    print("  no clean spot for the", net, "label on", sh.title)
                    stub_label(net, ps[0][0], ps[0][1])
            labelled_nets.add(net)
        for net in sorted(set(tree) | {n for n in r.wires if n not in POWER_NETS}):
            pin_nodes = {p[0] for p in signal.get(net, [])} | {n for nt, n, d in tagged if nt == net}
            segs, juncs = r.segments(net, pin_nodes)
            for a, b in segs:
                wire(xy(a), xy(b))
            if net not in labelled_nets and net not in global_nets and segs:
                # Name the net on its longest flat run, so the PCB keeps the same net names.
                def length(s):
                    return abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1])
                flat = [s for s in segs if s[0][1] == s[1][1]] or segs
                a, b = max(flat, key=length)
                if a[1] == b[1]:
                    a = min(a, b)
                    label(net, a[0] * GRID, a[1] * GRID, 0)
                else:
                    a = max(a, b, key=lambda n: n[1])
                    label(net, a[0] * GRID, a[1] * GRID, 90)
            for j in juncs:
                jx, jy = xy(j)
                out.append(f'  (junction (at {fmt(jx)} {fmt(jy)}) (diameter 0) (color 0 0 0 0)\n    (uuid {new_uuid()})\n  )\n')
        return out

    def _root_text(self):
        s = (f'(kicad_sch (version 20230121) (generator eeschema)\n\n  (uuid {self.root_uuid})\n\n'
             f'  (paper "A4")\n\n'
             f'  (title_block\n    (title {q(TITLE + " Rev B")})\n    (date {q(DATE)})\n    (rev {q(REV)})\n'
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
