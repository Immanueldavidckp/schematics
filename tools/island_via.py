#!/usr/bin/env python3
"""Find a through via for each orphan GND pour island, nudging tracks.

An orphan island is a piece of GND pour (with a GND pad in it) that no via,
track or pad joins to the rest of the ground. The fix is one via inside it
that lands in connected GND pour on another layer - but under the pads of
this board the inner layers carry signal tracks, so every spot is blocked
somewhere. This searches a fine grid of via spots inside each island and,
where only unlocked signal tracks are in the way, bends each one around the
via with a 45-degree jog (the same move as the Q14_B jog in manual_routes).
Every new piece is checked against all foreign copper with KiCad's own
shapes and the class clearances; pads, vias and holes are never moved.

Writes candidate routes, best first (fewest and smallest nudges), as JSON
for manual_routes.py (MANUAL_JSON=...), which applies them DRC-gated.

Run:  python3 tools/island_via.py [out.json]
"""
import json
import math
import os
import sys

import pcbnew

if not hasattr(pcbnew.SwigPyIterator, "next"):
    pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__

TOOLS = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import netclasses                                   # noqa: E402

PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")
VIA_D, VIA_DR = 0.45, 0.20
STEP = 0.025                  # via-spot grid, mm
MARGIN = 0.004                # on top of every rule clearance, mm
EDGE = 0.5                    # via centre to board edge, mm
HOLE_GAP = 0.45               # via drill edge to any other drill edge (pad rule, the larger)
KEEP = int(os.environ.get("ISLAND_KEEP", "6"))   # candidates written per island
NO_NUDGE = set(netclasses.HV) | set(netclasses.MV) | set(netclasses.RF) | set(netclasses.BULK)
V = pcbnew.VECTOR2I


def nm(v):
    return int(round(v * 1e6))


def clr(net):
    if net in netclasses.HV or net in netclasses.MV:
        return 0.6
    if net in netclasses.RF:
        return 0.3
    if net in netclasses.BULK:
        return 0.2
    if net in netclasses.PWR:
        return 0.15
    return netclasses.DEFAULT_CLEARANCE


def pair(a, b):
    return max(clr(a), clr(b)) + MARGIN


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_seg(a, b, c, d):
    """Distance between segments ab and cd (mm tuples)."""
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1, d2 = cross(c, d, a), cross(c, d, b)
    d3, d4 = cross(a, b, c), cross(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 and d2 and d3 and d4:
        return 0.0
    return min(seg_dist(*a, *c, *d), seg_dist(*b, *c, *d),
               seg_dist(*c, *a, *b), seg_dist(*d, *a, *b))


class Board:
    def __init__(self, path):
        self.b = b = pcbnew.LoadBoard(path)
        self.layers = {n: b.GetLayerID(n) for n in ("F.Cu", "GND_L2", "PWR_L3", "B.Cu")}
        self.name = {v: k for k, v in self.layers.items()}
        self.tracks, self.vias, self.pads, self.holes = [], [], [], []
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                self.vias.append(dict(net=t.GetNetname(), x=p.x / 1e6, y=p.y / 1e6,
                                      r=t.GetWidth() / 2e6, dr=t.GetDrill() / 2e6))
            elif t.GetClass() == "PCB_TRACK":
                s, e = t.GetStart(), t.GetEnd()
                self.tracks.append(dict(net=t.GetNetname(), layer=t.GetLayer(),
                                        a=(s.x / 1e6, s.y / 1e6), b=(e.x / 1e6, e.y / 1e6),
                                        w=t.GetWidth() / 1e6, locked=t.IsLocked()))
        for f in b.GetFootprints():
            for p in f.Pads():
                pos = p.GetPosition()
                if p.GetDrillSize().x > 0:
                    self.holes.append((pos.x / 1e6, pos.y / 1e6, max(p.GetDrillSize().x, p.GetDrillSize().y) / 2e6))
                lays = [l for l in self.layers.values() if p.IsOnLayer(l)]
                if not lays:
                    continue
                self.pads.append(dict(net=p.GetNetname(), ref=f"{f.GetReference()}.{p.GetNumber()}",
                                      x=pos.x / 1e6, y=pos.y / 1e6, pad=p, layers=lays,
                                      bb=p.GetBoundingBox()))
        self.edge = []
        for d in b.GetDrawings():
            if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
                self.edge.append(((d.GetStart().x / 1e6, d.GetStart().y / 1e6), (d.GetEnd().x / 1e6, d.GetEnd().y / 1e6)))
        bb = b.GetBoardEdgesBoundingBox()
        self.bbox = (bb.GetLeft() / 1e6, bb.GetTop() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6)
        self.keepouts = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
        self.gnd_zones = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND"]

    # ---- ground connectivity -------------------------------------------------
    def islands(self):
        """[(layer, zone, idx, polys, area, pads)] and the set of orphan keys."""
        isl = []
        for z in self.gnd_zones:
            for lay in self.layers.values():
                if not z.IsOnLayer(lay):
                    continue
                ps = z.GetFilledPolysList(lay)
                for i in range(ps.OutlineCount()):
                    isl.append((lay, z, i, ps, abs(ps.Outline(i).Area()) / 1e12))
        parent = list(range(len(isl) + len(self.vias) + len(self.pads) + len(self.tracks)))

        def find(k):
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        def union(a, c):
            ra, rc = find(a), find(c)
            if ra != rc:
                parent[ra] = rc
        nI, nV, nP = len(isl), len(self.vias), len(self.pads)
        gv = [k for k, v in enumerate(self.vias) if v["net"] == "GND"]
        gp = [k for k, p in enumerate(self.pads) if p["net"] == "GND"]
        gt = [k for k, t in enumerate(self.tracks) if t["net"] == "GND"]
        for k, (lay, z, i, ps, _) in enumerate(isl):
            for v in gv:
                if ps.Contains(V(nm(self.vias[v]["x"]), nm(self.vias[v]["y"])), i):
                    union(k, nI + v)
            for p in gp:
                pd = self.pads[p]
                if lay in pd["layers"] and ps.Contains(V(nm(pd["x"]), nm(pd["y"])), i):
                    union(k, nI + nV + p)
            for t in gt:
                tr = self.tracks[t]
                if tr["layer"] == lay and (ps.Contains(V(nm(tr["a"][0]), nm(tr["a"][1])), i)
                                           or ps.Contains(V(nm(tr["b"][0]), nm(tr["b"][1])), i)):
                    union(k, nI + nV + nP + t)
        for t in gt:
            tr = self.tracks[t]
            for end in (tr["a"], tr["b"]):
                for v in gv:
                    if math.hypot(end[0] - self.vias[v]["x"], end[1] - self.vias[v]["y"]) <= self.vias[v]["r"]:
                        union(nI + nV + nP + t, nI + v)
                for p in gp:
                    pd = self.pads[p]
                    if tr["layer"] in pd["layers"] and pd["pad"].GetEffectiveShape(tr["layer"]).Collide(
                            pcbnew.SHAPE_CIRCLE(V(nm(end[0]), nm(end[1])), 1000), 0):
                        union(nI + nV + nP + t, nI + nV + p)
                for u in gt:
                    tu = self.tracks[u]
                    if u != t and tu["layer"] == tr["layer"] and seg_dist(*end, *tu["a"], *tu["b"]) <= tu["w"] / 2:
                        union(nI + nV + nP + t, nI + nV + nP + u)
        for v in gv:
            for p in gp:
                pd = self.pads[p]
                vv = self.vias[v]
                if any(pd["pad"].GetEffectiveShape(l).Collide(pcbnew.SHAPE_CIRCLE(V(nm(vv["x"]), nm(vv["y"])), nm(vv["r"])), 0)
                       for l in pd["layers"]):
                    union(nI + v, nI + nV + p)
        big = max(range(nI), key=lambda k: isl[k][4])
        main = find(big)
        out, orphans = [], []
        for k, (lay, z, i, ps, area) in enumerate(isl):
            pads = [self.pads[p]["ref"] for p in gp if find(nI + nV + p) == find(k)
                    and lay in self.pads[p]["layers"] and ps.Contains(V(nm(self.pads[p]["x"]), nm(self.pads[p]["y"])), i)]
            rec = dict(layer=lay, zone=z, idx=i, polys=ps, area=area, pads=pads, main=find(k) == main)
            out.append(rec)
            if not rec["main"]:
                orphans.append(rec)
        return out, orphans

    # ---- via spot test -------------------------------------------------------
    def near(self, x, y, r):
        tr = [t for t in self.tracks if min(t["a"][0], t["b"][0]) - r <= x <= max(t["a"][0], t["b"][0]) + r
              and min(t["a"][1], t["b"][1]) - r <= y <= max(t["a"][1], t["b"][1]) + r]
        vi = [v for v in self.vias if abs(v["x"] - x) <= r and abs(v["y"] - y) <= r]
        pa = [p for p in self.pads if p["bb"].GetLeft() / 1e6 - r <= x <= p["bb"].GetRight() / 1e6 + r
              and p["bb"].GetTop() / 1e6 - r <= y <= p["bb"].GetBottom() / 1e6 + r]
        return tr, vi, pa

    def spot(self, x, y, main_fill):
        """None if the via at (x, y) cannot be made, else (nudges, cost)."""
        R = VIA_D / 2
        if not (self.bbox[0] + EDGE <= x <= self.bbox[2] - EDGE and self.bbox[1] + EDGE <= y <= self.bbox[3] - EDGE):
            return None
        if any(seg_dist(x, y, *a, *c) < EDGE for a, c in self.edge):
            return None
        for hx, hy, hr in self.holes:
            if math.hypot(x - hx, y - hy) < VIA_DR / 2 + HOLE_GAP + hr:
                return None
        for z in self.keepouts:
            if z.Outline().Contains(V(nm(x), nm(y))):
                return None
        tr, vi, pa = self.near(x, y, 2.0)
        for v in vi:
            if v["net"] == "GND":
                continue
            if math.hypot(x - v["x"], y - v["y"]) < R + v["r"] + pair("GND", v["net"]):
                return None
        circ = pcbnew.SHAPE_CIRCLE(V(nm(x), nm(y)), nm(R))
        for p in pa:
            if p["net"] == "GND":
                continue
            c = nm(pair("GND", p["net"]))
            if any(p["pad"].GetEffectiveShape(l).Collide(circ, c) for l in p["layers"]):
                return None
        # at least one other layer must have connected GND pour under the via
        if not main_fill(x, y):
            return None
        nudges, cost = [], 0.0
        new_by_layer = {}
        for t in tr:
            if t["net"] == "GND":
                continue
            need = R + pair("GND", t["net"]) + t["w"] / 2
            if seg_dist(x, y, *t["a"], *t["b"]) >= need:
                continue
            if t["locked"] or t["net"] in NO_NUDGE:
                return None
            pieces = self.detour(t, x, y, need, tr, vi, pa, new_by_layer.get(t["layer"], []))
            if pieces is None:
                return None
            new_by_layer.setdefault(t["layer"], []).extend((pp, t) for pp in pieces)
            nudges.append((t, pieces))
            cost += 1.0 + sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in pieces) - math.hypot(
                t["b"][0] - t["a"][0], t["b"][1] - t["a"][1])
        return nudges, cost

    def detour(self, t, x, y, need, tr, vi, pa, others):
        (ax, ay), (bx, by) = t["a"], t["b"]
        L = math.hypot(bx - ax, by - ay)
        if L < 1e-6:
            return None
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = -uy, ux
        t0 = (x - ax) * ux + (y - ay) * uy
        s = (x - ax) * nx + (y - ay) * ny
        if not (0 < t0 < L):
            return None
        need += 0.002
        # the via sits at offset s from the track line (along n); move the
        # line to offset d, `need` from the via on the side the track is on
        # already. Flat over t0 +- need, 45-degree jogs of |d| either side:
        # every jog point is >= need from the via along the track alone.
        for d in ([s - need] if s > 1e-6 else [s + need] if s < -1e-6 else [need, -need]):
            dd = abs(d)
            t1, t2 = t0 - need, t0 + need
            a0, b0 = t1 - dd, t2 + dd
            if a0 < 0 or b0 > L:
                continue

            def at(tt, o):
                return (ax + ux * tt + nx * o, ay + uy * tt + ny * o)
            pts = [(ax, ay), at(a0, 0), at(t1, d), at(t2, d), at(b0, 0), (bx, by)]
            pieces = [(pts[k], pts[k + 1]) for k in range(len(pts) - 1)
                      if math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) > 1e-4]
            if self.pieces_ok(t, pieces, x, y, tr, vi, pa, others):
                return pieces
        return None

    def pieces_ok(self, t, pieces, x, y, tr, vi, pa, others):
        hw, net, lay = t["w"] / 2, t["net"], t["layer"]
        for p, q in pieces:
            if seg_dist(x, y, *p, *q) < VIA_D / 2 + pair(net, "GND") + hw:
                return False
            for u in tr:
                if u is t or u["layer"] != lay or u["net"] == net:
                    continue
                if seg_seg(p, q, u["a"], u["b"]) < hw + u["w"] / 2 + pair(net, u["net"]):
                    return False
            for (op, oq), ot in others:
                if ot["net"] != net and seg_seg(p, q, op, oq) < hw + ot["w"] / 2 + pair(net, ot["net"]):
                    return False
            for v in vi:
                if v["net"] != net and seg_dist(v["x"], v["y"], *p, *q) < v["r"] + hw + pair(net, v["net"]):
                    return False
            seg = pcbnew.SHAPE_SEGMENT(V(nm(p[0]), nm(p[1])), V(nm(q[0]), nm(q[1])), nm(2 * hw))
            for pd in pa:
                if pd["net"] != net and lay in pd["layers"] and \
                        pd["pad"].GetEffectiveShape(lay).Collide(seg, nm(pair(net, pd["net"]))):
                    return False
            for hx, hy, hr in self.holes:
                if seg_dist(hx, hy, *p, *q) < hr + hw + 0.2 + MARGIN:
                    return False
        return True


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, ".island_via.json")
    B = Board(PCB)
    allisl, orphans = B.islands()
    mains = [r for r in allisl if r["main"]]
    print(f"{len(allisl)} GND pour islands, {len(orphans)} orphan(s)")
    routes = {}
    for o in orphans:
        lay = o["layer"]
        ch = o["polys"].Outline(o["idx"])
        bb = ch.BBox()
        x0, y0, x1, y1 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6
        tag = (o["pads"][0] if o["pads"] else f"{x0:.1f}_{y0:.1f}").replace(".", "_")
        print(f"island {B.name[lay]} ({x0:.2f},{y0:.2f})-({x1:.2f},{y1:.2f}) {o['area']:.2f} mm2 pads {o['pads']}")

        def main_fill(x, y):
            p = V(nm(x), nm(y))
            for r in mains:
                if r["layer"] != lay and r["polys"].Contains(p, r["idx"]):
                    # the via's ring must sit inside that pour, not on its rim
                    ok = all(r["polys"].Contains(V(nm(x + 0.2 * math.cos(a)), nm(y + 0.2 * math.sin(a))), r["idx"])
                             for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2))
                    if ok:
                        return True
            return False
        cands = []
        ny, nx = int((y1 - y0) / STEP) + 1, int((x1 - x0) / STEP) + 1
        for j in range(ny):
            for i in range(nx):
                x, y = round(x0 + i * STEP, 4), round(y0 + j * STEP, 4)
                if not o["polys"].Contains(V(nm(x), nm(y)), o["idx"]):
                    continue
                r = B.spot(x, y, main_fill)
                if r is not None:
                    cands.append((r[1], x, y, r[0]))
        cands.sort(key=lambda c: c[0])
        print(f"   {len(cands)} via spot(s); best: " +
              ", ".join(f"({c[1]:.3f},{c[2]:.3f}) nudges={len(c[3])}" for c in cands[:3]))
        # keep spread-out alternatives, not neighbours of one spot
        picked = []
        for c in cands:
            if all(math.hypot(c[1] - p[1], c[2] - p[2]) > 0.3 for p in picked):
                picked.append(c)
            if len(picked) >= KEEP:
                break
        for k, (cost, x, y, nudges) in enumerate(picked):
            items = []
            for t, pieces in nudges:
                lname = B.name[t["layer"]]
                items.append(["del", t["net"], lname, round(t["a"][0], 6), round(t["a"][1], 6),
                              round(t["b"][0], 6), round(t["b"][1], 6)])
                for p, q in pieces:
                    items.append(["trk", t["net"], lname, round(p[0], 4), round(p[1], 4),
                                  round(q[0], 4), round(q[1], 4), round(t["w"], 4)])
            items.append(["via", "GND", x, y, VIA_D, VIA_DR])
            routes[f"isl_{tag}_{k}"] = items
            print(f"   isl_{tag}_{k}: via ({x:.3f},{y:.3f}) nudges "
                  f"{[(t['net'], B.name[t['layer']]) for t, _ in nudges]}")
    with open(out, "w") as f:
        json.dump(routes, f, indent=1)
    print(f"ISLAND_VIA wrote {len(routes)} candidate route(s) for {len(orphans)} island(s) -> {out}")


if __name__ == "__main__":
    main()
