"""Draws real wires between the pins of each schematic page, so the drawing reads like a circuit, not a wiring list.

Used by kigen.py. Power nets keep their power symbols (GND, +5V and so on). Every other net on a page is joined by
wires that a maze router lays out on KiCad's 1.27 mm grid, around part bodies, text and labels. Wires of different nets
may cross at right angles but never touch: no shared corner, end, or overlapping run, so KiCad can't join them by
accident. A net that also appears on another page gets one global label. Where no clean path exists, that pin gets a
short stub and a net label instead (KiCad joins labels by name), so the drawing is always electrically right; the
netlist check in build.sh confirms it.
"""
import heapq
import math
import re

GRID = 1.27
BEND, CROSS, NEAR_TEXT = 6.0, 10.0, 4.0


def g(v):
    return int(round(v / GRID))


def body_box(sym, unit):
    """The symbol's drawing plus its pins' inner ends, as a box in library coords (y up)."""
    xs, ys = [], []
    for m in re.finditer(r'\(symbol "[^"]+_(\d+)_(\d+)"(.*?)(?=\n    \(symbol "|\Z)', sym.text, re.S):
        if int(m.group(1)) not in (0, unit):
            continue
        blk = m.group(3)
        for kw in ("xy", "start", "end", "mid", "center"):
            for x, y in re.findall(r'\(' + kw + r' ([-\d.]+) ([-\d.]+)\)', blk):
                xs.append(float(x))
                ys.append(float(y))
        for cx, cy, r in re.findall(r'\(circle \(center ([-\d.]+) ([-\d.]+)\) \(radius ([-\d.]+)\)', blk):
            xs += [float(cx) - float(r), float(cx) + float(r)]
            ys += [float(cy) - float(r), float(cy) + float(r)]
    for p in sym.pins:
        if p["unit"] in (0, unit) and not p["hidden"]:
            a = math.radians(p["angle"])
            xs.append(p["x"] + math.cos(a) * p["length"])
            ys.append(p["y"] + math.sin(a) * p["length"])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


class Router:
    def __init__(self):
        self.blocked = set()        # grid nodes nothing may use
        self.soft = {}              # node -> extra cost (near text)
        self.owner = {}             # node -> net
        self.kind = {}              # node -> "h" / "v" (a straight pass, crossable) or "x" (fixed: pin, bend, end)
        self.edges = {}             # frozenset(a, b) -> net
        self.wires = {}             # net -> set of edges
        self.pins = {}              # node -> net, for pin ends

    # ------------------------------------------------------------ obstacles
    def block_box(self, x0, y0, x1, y1, soft=0.0):
        for i in range(g(min(x0, x1)), g(max(x0, x1)) + 1):
            for j in range(g(min(y0, y1)), g(max(y0, y1)) + 1):
                if soft:
                    self.soft[(i, j)] = max(self.soft.get((i, j), 0), soft)
                else:
                    self.blocked.add((i, j))

    def claim(self, node, net, kind="x"):
        self.owner[node] = net
        self.kind[node] = kind

    def add_edge(self, a, b, net):
        self.edges[frozenset((a, b))] = net
        self.wires.setdefault(net, set()).add(frozenset((a, b)))

    # ------------------------------------------------------------ routing
    def route(self, net, src, out_dir, tree, limit):
        """Cheapest path from pin node `src` (leaving in `out_dir`) to any node of this net's `tree`."""
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        targets = list(tree)
        tx = [t[0] for t in targets]
        ty = [t[1] for t in targets]
        box = (min(tx + [src[0]]) - 40, min(ty + [src[1]]) - 40, max(tx + [src[0]]) + 40, max(ty + [src[1]]) + 40)

        def h(n):
            return min(abs(n[0] - x) + abs(n[1] - y) for x, y in targets[:40])

        start = (src, out_dir)
        dist = {start: 0}
        prev = {}
        heap = [(h(src), 0, src, out_dir)]
        while heap:
            f, d, n, dr = heapq.heappop(heap)
            if dist.get((n, dr), 1e18) < d:
                continue
            if d > limit:
                return None
            crossing = n in self.owner and self.owner[n] != net
            for k, (dx, dy) in enumerate(dirs):
                if n == src and (dx, dy) != out_dir:
                    continue
                if crossing and (dx, dy) != dr:
                    continue          # straight through a crossing, no turning on it
                if (dx, dy) == (-dr[0], -dr[1]) and n != src:
                    continue
                m = (n[0] + dx, n[1] + dy)
                if not (box[0] <= m[0] <= box[2] and box[1] <= m[1] <= box[3]):
                    continue
                if m in self.blocked or frozenset((n, m)) in self.edges:
                    continue
                cost = 1 + self.soft.get(m, 0) + (BEND if (dx, dy) != dr else 0)
                if m in self.owner and self.owner[m] != net:
                    want = "v" if dx == 0 else "h"
                    if self.kind[m] == "x" or self.kind[m] == want:
                        continue      # can only cross a straight run of another net, at right angles
                    cost += CROSS
                if m in self.pins and self.pins[m] != net:
                    continue
                nd = d + cost
                key = (m, (dx, dy))
                if nd < dist.get(key, 1e18):
                    dist[key] = nd
                    prev[key] = (n, dr)
                    if m in tree:
                        # reached the net: rebuild the path
                        path = [m]
                        cur = (n, dr)
                        while cur != start:
                            path.append(cur[0])
                            cur = prev[cur]
                        path.append(src)
                        return path[::-1]
                    heapq.heappush(heap, (nd + h(m), nd, m, (dx, dy)))
        return None

    def commit(self, net, path):
        for i, n in enumerate(path):
            if n in self.owner and self.owner[n] != net:
                continue      # a crossing: the other net keeps it
            if 0 < i < len(path) - 1:
                a, b = path[i - 1], path[i + 1]
                straight = a[0] == b[0] or a[1] == b[1]
                kind = ("v" if a[0] == b[0] else "h") if straight else "x"
                if n in self.owner and self.owner[n] == net:
                    kind = "x"
                self.claim(n, net, kind)
            else:
                self.claim(n, net, "x")
        for a, b in zip(path, path[1:]):
            self.add_edge(a, b, net)

    # ------------------------------------------------------------ output
    def segments(self, net, pin_nodes):
        """Straight wire runs for a net, broken at bends, branch points and pins, plus its junction dots."""
        adj = {}
        for e in self.wires.get(net, ()):
            a, b = tuple(e)
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        stops = set()
        juncs = []
        for n, nb in adj.items():
            deg = len(nb) + (1 if n in pin_nodes else 0)
            straight = len(nb) == 2 and (nb[0][0] == nb[1][0] or nb[0][1] == nb[1][1])
            if len(nb) != 2 or not straight or n in pin_nodes:
                stops.add(n)
            if deg >= 3:
                juncs.append(n)
        segs, seen = [], set()
        for s in stops:
            for nxt in adj[s]:
                if frozenset((s, nxt)) in seen:
                    continue
                run = [s, nxt]
                seen.add(frozenset((s, nxt)))
                while run[-1] not in stops:
                    cur = run[-1]
                    nn = [x for x in adj[cur] if x != run[-2]][0]
                    seen.add(frozenset((cur, nn)))
                    run.append(nn)
                segs.append((run[0], run[-1]))
        return segs, juncs
