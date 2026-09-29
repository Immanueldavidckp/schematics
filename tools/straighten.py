#!/usr/bin/env python3
"""Straighten the grid router's staircase tracks, DRC-gated.

The LV finisher routes on a 0.1 mm grid, so a track at any angle that is not
a multiple of 45 degrees comes out as a staircase of tiny 45/90-degree steps
(2026-09-29: 88 such runs, 1394 steps, on 44 nets). Electrically harmless,
but untidy. This replaces every run of track between fixed points with the
fewest straight segments that keep all clearances ("string pulling"):

  run      segments of one net, layer and width joined end to end at plain
           bends; it ends at an anchor - a pad, a via, a branch, a width
           change, a locked segment
  pulled   from each vertex the farthest later vertex whose straight segment
           clears all foreign copper on the layer (tracks, pads, vias), all
           holes, the board edge and track keep-outs, by the class clearance
           + MARGIN; the anchors never move, so connectivity is kept
  skipped  RF nets (impedance-controlled shapes) and locked tracks. HV
           nets are held to the .kicad_dru creepage rules (1.5 mm to
           signals, 1.0 mm to the edge) as well as their class; a segment that carries a
           connection mid-run (a T-junction, a via or pad on its side, other
           than at the run's own ends) keeps both its end points

Runs are processed in a fixed order against the updated geometry, so two
straightened runs never collide with each other. Then the whole board must
pass DRC with no more errors and no more unconnected items than before;
runs named in a new violation are excluded and everything is re-planned
from the original (repeat until clean). Deletion is by uuid in the file
text, like the other tools.

Run:  PYTHONPATH=tools python3 tools/straighten.py [--dry-run]
"""
import collections
import json
import math
import os
import re
import shutil
import subprocess
import sys

import pcbnew

if not hasattr(pcbnew.SwigPyIterator, "next"):
    pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__

TOOLS = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import netclasses                                   # noqa: E402

PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")
MARGIN = 0.002           # mm over every rule (the grid router left tracks at exactly
                         # the rule; the DRC gate below has the final word)
EDGE = 0.5 + 0.02        # min_copper_edge_clearance + margin
HOLE = 0.2 + 0.02        # min_hole_clearance + margin
SKIP = set(netclasses.RF)      # impedance-controlled geometry stays as drawn
HV_TO_SIGNAL = 1.5             # .kicad_dru "HV to signal 1.5mm" (applied board-wide here)
HV_EDGE = 1.0 + 0.02           # .kicad_dru "HV to board edge"
V = pcbnew.VECTOR2I
FORM_RE = re.compile(r"\t\((segment|via|arc)\n(?:\t\t.*\n)*?\t\)\n")


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


AREAS = {}                     # rule-area outlines by name, filled by Board()


def in_area(name, x, y):
    z = AREAS.get(name)
    return bool(z) and z.Outline().Contains(V(nm(x), nm(y)))


def pair(a, b, pts=()):
    """Class clearance, plus the .kicad_dru HV-to-signal 1.5 mm where that rule
    applies: an HV item inside HV_ZONE and outside BUCK_HV, against anything
    that is not HV, MV or GND. `pts` are the new piece's end points; with none
    given the rule is assumed to apply (conservative)."""
    c = max(clr(a), clr(b))
    hv, lvish = set(netclasses.HV), set(netclasses.HV) | set(netclasses.MV) | {"GND"}
    if (a in hv and b not in lvish) or (b in hv and a not in lvish):
        if not pts or any(in_area("HV_ZONE", x, y) and not in_area("BUCK_HV", x, y) for x, y in pts):
            c = max(c, HV_TO_SIGNAL)
    return c + MARGIN


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_seg(a, b, c, d):
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1, d2, d3, d4 = cross(c, d, a), cross(c, d, b), cross(a, b, c), cross(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 and d2 and d3 and d4:
        return 0.0
    return min(seg_dist(*a, *c, *d), seg_dist(*b, *c, *d), seg_dist(*c, *a, *b), seg_dist(*d, *a, *b))


class Grid:
    """Obstacles bucketed in 1 mm cells for fast neighbourhood queries."""

    def __init__(self):
        self.cells = collections.defaultdict(set)
        self.items = {}

    def _keys(self, x0, y0, x1, y1):
        for i in range(int(math.floor(x0)), int(math.floor(x1)) + 1):
            for j in range(int(math.floor(y0)), int(math.floor(y1)) + 1):
                yield (i, j)

    def add(self, key, item, bbox):
        self.items[key] = (item, bbox)
        for k in self._keys(*bbox):
            self.cells[k].add(key)

    def remove(self, key):
        item, bbox = self.items.pop(key)
        for k in self._keys(*bbox):
            self.cells[k].discard(key)

    def near(self, x0, y0, x1, y1):
        seen = set()
        for k in self._keys(x0, y0, x1, y1):
            for key in self.cells.get(k, ()):
                if key not in seen:
                    seen.add(key)
                    yield self.items[key][0]


class Board:
    def __init__(self, path):
        self.b = b = pcbnew.LoadBoard(path)
        self.cu = [l for l in (b.GetLayerID("F.Cu"), b.GetLayerID("GND_L2"), b.GetLayerID("PWR_L3"),
                               b.GetLayerID("B.Cu"))]
        self.grid = {l: Grid() for l in self.cu}
        self.segs = {}                     # uuid -> dict
        self.vias = []
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                v = dict(kind="via", net=t.GetNetname(), x=p.x / 1e6, y=p.y / 1e6,
                         r=t.GetWidth(pcbnew.F_Cu) / 2e6, dr=t.GetDrill() / 2e6)
                self.vias.append(v)
                for l in self.cu:
                    self.grid[l].add(("via", len(self.vias) - 1), v,
                                     (v["x"] - v["r"], v["y"] - v["r"], v["x"] + v["r"], v["y"] + v["r"]))
            elif t.GetClass() == "PCB_TRACK":
                s, e = t.GetStart(), t.GetEnd()
                u = t.m_Uuid.AsString()
                d = dict(kind="trk", uuid=u, net=t.GetNetname(), layer=t.GetLayer(),
                         a=(s.x / 1e6, s.y / 1e6), b=(e.x / 1e6, e.y / 1e6),
                         ai=(s.x, s.y), bi=(e.x, e.y), w=t.GetWidth() / 1e6, locked=t.IsLocked())
                self.segs[u] = d
                self._add_seg(("trk", u), d)
        self.pads = []
        self.holes = []
        for f in b.GetFootprints():
            for p in f.Pads():
                pos = p.GetPosition()
                if p.GetDrillSize().x > 0:
                    self.holes.append((pos.x / 1e6, pos.y / 1e6, max(p.GetDrillSize().x, p.GetDrillSize().y) / 2e6,
                                       p.GetNetname()))
                bb = p.GetBoundingBox()
                pd = dict(kind="pad", net=p.GetNetname(), pad=p,
                          bbox=(bb.GetLeft() / 1e6, bb.GetTop() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6))
                self.pads.append(pd)
                for l in self.cu:
                    if p.IsOnLayer(l):
                        self.grid[l].add(("pad", len(self.pads) - 1), pd, pd["bbox"])
        self.edge = []
        for d in b.GetDrawings():
            if d.GetLayer() != pcbnew.Edge_Cuts:
                continue
            if d.GetShapeStr() == "Arc":
                pts = [d.GetStart(), d.GetArcMid(), d.GetEnd()]
                pts = [(p.x / 1e6, p.y / 1e6) for p in pts]
                self.edge += list(zip(pts, pts[1:]))
            else:
                self.edge.append(((d.GetStart().x / 1e6, d.GetStart().y / 1e6),
                                  (d.GetEnd().x / 1e6, d.GetEnd().y / 1e6)))
        self.keepouts = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowTracks()]
        AREAS.clear()
        AREAS.update({z.GetZoneName(): z for z in b.Zones() if z.GetIsRuleArea()})

    def _add_seg(self, key, d):
        (ax, ay), (bx, by) = d["a"], d["b"]
        h = d["w"] / 2
        self.grid[d["layer"]].add(key, d, (min(ax, bx) - h, min(ay, by) - h, max(ax, bx) + h, max(ay, by) + h))

    # ---- clearance test for a new straight piece -----------------------------
    def clear(self, p, q, w, net, layer):
        hw = w / 2
        reach = hw + 1.0 + HV_TO_SIGNAL + MARGIN
        x0, y0 = min(p[0], q[0]) - reach, min(p[1], q[1]) - reach
        x1, y1 = max(p[0], q[0]) + reach, max(p[1], q[1]) + reach
        seg_shape = None
        for it in self.grid[layer].near(x0, y0, x1, y1):
            if it["net"] == net:
                continue
            if it["kind"] == "trk":
                if seg_seg(p, q, it["a"], it["b"]) < hw + it["w"] / 2 + pair(net, it["net"], (p, q)):
                    return False
            elif it["kind"] == "via":
                if seg_dist(it["x"], it["y"], *p, *q) < it["r"] + hw + pair(net, it["net"], (p, q)):
                    return False
            else:
                if seg_shape is None:
                    seg_shape = pcbnew.SHAPE_SEGMENT(V(nm(p[0]), nm(p[1])), V(nm(q[0]), nm(q[1])), nm(w))
                if it["pad"].GetEffectiveShape(layer).Collide(seg_shape, nm(pair(net, it["net"], (p, q)))):
                    return False
        for hx, hy, hr, hnet in self.holes:
            if hnet != net and abs(hx - (p[0] + q[0]) / 2) < 60 and seg_dist(hx, hy, *p, *q) < hr + hw + HOLE:
                return False
        edge = HV_EDGE if net in netclasses.HV else EDGE
        for a, c in self.edge:
            if seg_seg(p, q, a, c) < hw + edge:
                return False
        for z in self.keepouts:
            if z.IsOnLayer(layer):
                n = max(2, int(math.hypot(q[0] - p[0], q[1] - p[1]) / 0.05))
                for k in range(n + 1):
                    x = p[0] + (q[0] - p[0]) * k / n
                    y = p[1] + (q[1] - p[1]) * k / n
                    if z.Outline().Contains(V(nm(x), nm(y))):
                        return False
        return True

    # ---- runs ---------------------------------------------------------------------
    def runs(self):
        """[(net, layer, width, [points in nm], [uuids])] for every straightenable run."""
        by_end = collections.defaultdict(list)
        for u, d in self.segs.items():
            by_end[(d["net"], d["layer"], d["ai"])].append(u)
            by_end[(d["net"], d["layer"], d["bi"])].append(u)
        via_at = {(v["net"], nm(v["x"]), nm(v["y"])) for v in self.vias}
        pad_hit = collections.defaultdict(list)
        for pd in self.pads:
            pad_hit[pd["net"]].append(pd)

        def on_pad(net, layer, pt):
            for pd in pad_hit.get(net, ()):
                x0, y0, x1, y1 = pd["bbox"]
                if x0 - 0.01 <= pt[0] / 1e6 <= x1 + 0.01 and y0 - 0.01 <= pt[1] / 1e6 <= y1 + 0.01 and \
                        pd["pad"].IsOnLayer(layer) and pd["pad"].HitTest(V(*pt)):
                    return True
            return False

        def anchor(net, layer, pt):
            us = by_end[(net, layer, pt)]
            if len(us) != 2 or (net, pt[0], pt[1]) in via_at or on_pad(net, layer, pt):
                return True
            a, c = (self.segs[u] for u in us)
            return a["w"] != c["w"] or a["locked"] or c["locked"]

        def attachments(d, run_set, ends):
            """Same-net copper touching segment d that is not part of the run and
            does not sit on one of the run's end anchors: straightening could
            pull the track away from it, so d must stay where it is."""
            (ax, ay), (bx, by) = d["a"], d["b"]
            at_end = lambda x, y: any(abs(x - e[0] / 1e6) < 1e-4 and abs(y - e[1] / 1e6) < 1e-4 for e in ends)
            for it in self.grid[d["layer"]].near(min(ax, bx) - 0.5, min(ay, by) - 0.5,
                                                 max(ax, bx) + 0.5, max(ay, by) + 0.5):
                if it["net"] != d["net"]:
                    continue
                if it["kind"] == "trk":
                    if it["uuid"] in run_set:
                        continue
                    for e in (it["a"], it["b"]):
                        if not at_end(*e) and seg_dist(*e, ax, ay, bx, by) <= d["w"] / 2 + it["w"] / 2:
                            return True
                elif it["kind"] == "via":
                    if not at_end(it["x"], it["y"]) and \
                            seg_dist(it["x"], it["y"], ax, ay, bx, by) <= it["r"] + d["w"] / 2:
                        return True
                else:
                    pad = it["pad"]
                    if not pad.IsOnLayer(d["layer"]) or any(pad.HitTest(V(*e)) for e in ends):
                        continue
                    shape = pcbnew.SHAPE_SEGMENT(V(*d["ai"]), V(*d["bi"]), nm(d["w"]))
                    if pad.GetEffectiveShape(d["layer"]).Collide(shape, 0):
                        return True
            return False

        done, out = set(), []
        for u, d in sorted(self.segs.items(), key=lambda kv: (kv[1]["net"], kv[1]["layer"], kv[1]["ai"])):
            if u in done or d["net"] in SKIP or d["locked"]:
                continue
            net, layer = d["net"], d["layer"]
            if not (anchor(net, layer, d["ai"]) or anchor(net, layer, d["bi"])):
                continue                       # start runs only at an anchor end
            start = d["ai"] if anchor(net, layer, d["ai"]) else d["bi"]
            pts, uu, cur, pt = [start], [], u, start
            while True:
                s = self.segs[cur]
                done.add(cur)
                uu.append(cur)
                pt = s["bi"] if s["ai"] == pt else s["ai"]
                pts.append(pt)
                if anchor(net, layer, pt):
                    break
                nxt = [x for x in by_end[(net, layer, pt)] if x != cur]
                if not nxt or nxt[0] in done:
                    break
                cur = nxt[0]
            if len(uu) < 3 or any(self.segs[x]["locked"] for x in uu):
                continue
            # a segment with copper attached mid-run keeps both its end points
            run_set, ends = set(uu), (pts[0], pts[-1])
            keep = {0, len(pts) - 1}
            for k, x in enumerate(uu):
                if attachments(self.segs[x], run_set, ends):
                    keep |= {k, k + 1}
            out.append((net, layer, d["w"], pts, uu, keep))
        return out

    def pull(self, net, layer, w, pts, keep):
        """Farthest-visible string pulling over the run's own vertices, never
        skipping a vertex in `keep` (end anchors, attached segments)."""
        mm = [(x / 1e6, y / 1e6) for x, y in pts]
        stops = sorted(keep)
        res = [0]
        for s0, s1 in zip(stops, stops[1:]):
            i = s0
            while i < s1:
                j = s1
                while j > i + 1 and not self.clear(mm[i], mm[j], w, net, layer):
                    j -= 1
                res.append(j)
                i = j
        return [pts[k] for k in res]

    def commit(self, net, layer, w, old_uuids, new_pts):
        for u in old_uuids:
            self.grid[layer].remove(("trk", u))
        for k, (a, c) in enumerate(zip(new_pts, new_pts[1:])):
            d = dict(kind="trk", uuid=f"new-{old_uuids[0]}-{k}", net=net, layer=layer,
                     a=(a[0] / 1e6, a[1] / 1e6), b=(c[0] / 1e6, c[1] / 1e6), ai=a, bi=c, w=w, locked=False)
            self._add_seg(("trk", d["uuid"]), d)


def report():
    netclasses.ensure()
    out = PCB + ".straighten.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all", "-o", out, PCB],
                   capture_output=True)
    d = json.load(open(out))
    errors = [v for v in d["violations"] if v["severity"] == "error"]
    warn = collections.Counter(v["type"] for v in d["violations"] if v["severity"] != "error")
    return errors, len(d["unconnected_items"]), warn


def plan(skip):
    B = Board(PCB)
    runs = B.runs()
    changes = []
    for net, layer, w, pts, uu, keep in runs:
        if uu[0] in skip:
            continue
        new = B.pull(net, layer, w, pts, keep)
        if len(new) < len(pts):
            B.commit(net, layer, w, uu, new)
            changes.append((net, layer, w, uu, new, len(pts) - 1))
    return B, runs, changes


def apply(changes):
    """Delete the old segments by uuid (file text), add the new ones, refill."""
    gone = {u for c in changes for u in c[3]}
    txt = open(PCB, encoding="utf-8").read()

    def keep(m):
        u = re.search(r'\(uuid "([^"]+)"\)', m.group(0))
        return "" if u and u.group(1) in gone else m.group(0)
    txt = FORM_RE.sub(keep, txt)
    with open(PCB, "w", encoding="utf-8") as f:
        f.write(txt)
    b = pcbnew.LoadBoard(PCB)
    owner = {}
    for idx, (net, layer, w, uu, new, _) in enumerate(changes):
        ni = b.FindNet(net)
        for a, c in zip(new, new[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(V(*a))
            t.SetEnd(V(*c))
            t.SetWidth(nm(w))
            t.SetLayer(layer)
            t.SetNet(ni)
            b.Add(t)
            owner[t.m_Uuid.AsString()] = uu[0]
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b, True)
    return owner


def main():
    dry = "--dry-run" in sys.argv
    e0, u0, w0 = report()
    print(f"before: errors {len(e0)}, unconnected {u0}, warnings {dict(w0)}")
    original = PCB + ".straighten-orig"
    shutil.copyfile(PCB, original)
    skip = set()
    for rnd in range(1, 8):
        shutil.copyfile(original, PCB)
        B, runs, changes = plan(skip)
        steps = sum(c[5] for c in changes)
        after = sum(len(c[4]) - 1 for c in changes)
        print(f"round {rnd}: {len(runs)} runs, {len(changes)} straightened: {steps} segments -> {after}")
        if dry or not changes:
            shutil.copyfile(original, PCB)
            os.unlink(original)
            print("STRAIGHTEN_RESULT dry run / nothing to do - board unchanged")
            return
        owner = apply(changes)
        errs, u, warn = report()
        blame = {owner[i["uuid"]] for v in errs for i in v["items"] if i["uuid"] in owner}
        print(f"   DRC: errors {len(errs)}, unconnected {u} (was {u0}); blamed runs {len(blame)}")
        if len(errs) <= len(e0) and u <= u0:
            os.unlink(original)
            print(f"STRAIGHTEN_RESULT runs={len(changes)} segments {steps} -> {after} "
                  f"errors={len(errs)} unconnected={u}")
            return
        if not blame:
            # connectivity loss (a pour split) names no track: halve the batch
            order = [c[3][0] for c in changes]
            blame = set(order[len(order) // 2:])
            print(f"   no track named - excluding the second half ({len(blame)} runs) and re-planning")
        skip |= blame
    shutil.copyfile(original, PCB)
    os.unlink(original)
    print("STRAIGHTEN_RESULT no clean result - board restored")


if __name__ == "__main__":
    main()
