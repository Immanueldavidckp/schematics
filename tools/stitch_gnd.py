#!/usr/bin/env python3
"""GND stitching pass: connect every GND cluster to the GND_L2 plane.

Why this exists. On every routed board most of the DRC "unconnected items"
were not failed routes but GND clusters with no path to the plane: pieces of
the F.Cu / B.Cu GND pour that survive island removal because they touch a GND
pad or track, and SMD GND pads the pour cannot reach. FreeRouting and the LV
finisher treat GND as one more net to route and leave them (T2 board, cycle 1:
38 of 78 unconnected entries were zone-zone, 36 involved a GND pad). A through
via anywhere inside such a cluster connects it to the solid GND_L2 plane.

What it does, in order:
  1. islands: for each F_GND / B_GND fill outline that contains no GND via
     and no GND through-hole pad, place one via at the most inset legal point.
  2. pads: for each SMD GND pad whose cluster still has no via, place a via
     beside it and a 0.25 mm track from the pad centre to the via.
  3. gate: refill zones, save, run kicad-cli DRC. Any via/track of ours that
     appears at a violation position is removed and the gate re-run. The
     unconnected count must not rise for any non-GND net (a via can cut a
     narrow PWR_L3 finger); if it does, the vias sitting in L3 pours are
     removed and the gate re-run.

Legality of a via is checked geometrically on all four layers against every
other-net pad, track, via and zone fill with the larger of the two netclass
clearances, plus the hole-to-hole rule, the board edge and rule areas that
forbid vias. PWR_L3 pours adapt to a via, so they are not obstacles as such,
but a via must not split one: the via's clearance disk is subtracted from the
pour and the spot is refused if the pour falls into more pieces.

Stage 0 first tightens every pour's clearance from KiCad's 0.5 mm default to
0.20 mm (GND) / 0.25 mm (power) and refills: that alone reconnects many GND
pads the pours could not reach.

Run:  python3 tools/stitch_gnd.py [board.kicad_pcb]
      (default: the project's telematics-tracker.kicad_pcb; the .kicad_pro
      and .kicad_dru must sit beside the board for the DRC gate)
Env:  STITCH_DRY=1  plan only, do not write.
"""
import math
import os
import re
import subprocess
import sys

import pcbnew

if not hasattr(pcbnew.SwigPyIterator, "next"):
    pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netclasses import CLASSES, DEFAULT_CLEARANCE   # noqa: E402

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, "telematics-tracker.kicad_pcb")
PCB = os.path.abspath(PCB)

VIA_D, VIA_DRILL = 0.60, 0.30          # GND class via
TRACK_W = 0.25                          # pad-to-via link (board floor 0.20)
MARGIN = 0.02                           # on top of every clearance
HOLE_TO_HOLE = 0.50                     # .kicad_dru "JLCPCB hole to hole"
EDGE = 0.50 + 0.02                      # board setup copper-edge clearance
POUR_CLR = {"GND": 0.20, "other": 0.25}  # zone clearance (KiCad's default 0.5 starved the pours)
POUR_GAP = 0.30                         # thermal relief gap (pads connect solid anyway)
VIA_SMALL = 0.50                        # fallback via (annulus 0.10 = board floor)
GRID = 0.20                             # candidate grid inside islands
RING = (0.0, 0.10, 0.20, 0.35, 0.50, 0.70, 0.90)   # extra pad-via distances tried
ANGLES = 16
CLS_CLR = {name: clr for name, _p, clr, _t, _vd, _vdr in CLASSES}
CLS_CLR["Default"] = DEFAULT_CLEARANCE
GND_CLR = CLS_CLR["GND"]


def mm(v):
    return int(round(v * 1e6))


def to_mm(v):
    return v / 1e6


def pt(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


class Board:
    def __init__(self, path):
        self.path = path
        self.b = pcbnew.LoadBoard(path)
        b = self.b
        self.gnd = b.GetNetcodeFromNetname("GND")
        self.F, self.B = pcbnew.F_Cu, pcbnew.B_Cu
        self.L2, self.L3 = b.GetLayerID("GND_L2"), b.GetLayerID("PWR_L3")
        self.layers = [self.F, self.L2, self.L3, self.B]
        self.added = []                 # (item, kind) we placed
        self.via_d = VIA_D
        self.refresh()

    def refresh(self):
        b = self.b
        self.tracks = list(b.GetTracks())
        self.pads = list(b.GetPads())
        self.zones = list(b.Zones())
        self.gnd_vias = [t for t in self.tracks if t.GetClass() == "PCB_VIA" and t.GetNetCode() == self.gnd]
        self.gnd_pth = [p for p in self.pads if p.GetNetCode() == self.gnd and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
        self.gnd_smd = [p for p in self.pads if p.GetNetCode() == self.gnd and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
        self.fills = {}
        for z in self.zones:
            if z.GetIsRuleArea() or z.GetNetCode() == 0:
                continue
            for l in z.GetLayerSet().Seq():
                self.fills.setdefault(l, []).append((z, z.GetFilledPolysList(l)))
        bb = b.GetBoardEdgesBoundingBox()
        self.edge = (to_mm(bb.GetX()), to_mm(bb.GetY()), to_mm(bb.GetRight()), to_mm(bb.GetBottom()))
        self.rule_novia = [z for z in self.zones if z.GetIsRuleArea() and z.GetDoNotAllowVias()]

    # ---- clearances -------------------------------------------------------
    def clr_of(self, item):
        try:
            c = to_mm(item.GetEffectiveNetClass().GetClearance())
            if c > 0:
                return c
        except Exception:
            pass
        try:
            return CLS_CLR.get(item.GetNetClassName(), DEFAULT_CLEARANCE)
        except Exception:
            return DEFAULT_CLEARANCE

    def need(self, item):
        return max(GND_CLR, self.clr_of(item)) + MARGIN

    # ---- geometry checks ----------------------------------------------------
    def in_board(self, x, y):
        x0, y0, x1, y1 = self.edge
        return x0 + EDGE + self.via_d / 2 <= x <= x1 - EDGE - self.via_d / 2 and y0 + EDGE + self.via_d / 2 <= y <= y1 - EDGE - self.via_d / 2

    def l3_pour_ok(self, x, y, circ):
        """PWR_L3 pours adapt to a via, but a via can cut a narrow finger.
        Subtract the via's clearance disk (plus the fill's minimum thickness,
        which erodes slivers) from each pour it touches and refuse the spot
        if that splits the pour into more pieces than it had."""
        p = pt(x, y)
        for z, polys in self.fills.get(self.L3, []):
            if z.GetNetCode() == self.gnd:
                continue
            clr = max(self.need(z), to_mm(z.GetLocalClearance()))
            if not polys.Collide(circ, mm(clr)):
                continue
            r = self.via_d / 2 + clr + to_mm(z.GetMinThickness()) + MARGIN
            disk = pcbnew.SHAPE_POLY_SET()
            disk.NewOutline()
            for k in range(24):
                a = 2 * math.pi * k / 24
                disk.Append(mm(x + r * math.cos(a)), mm(y + r * math.sin(a)))
            cut = pcbnew.SHAPE_POLY_SET(polys)
            cut.BooleanSubtract(disk)
            cut.Simplify()
            if cut.OutlineCount() > polys.OutlineCount():
                return False
        return True

    def via_why(self, x, y):
        """None when a GND through via at (x, y) violates nothing fixed on any
        layer, else a short reason (for the rejection histogram)."""
        if not self.in_board(x, y):
            return "edge"
        p = pt(x, y)
        for z in self.rule_novia:
            if z.Outline().Contains(p):
                return "rule-area"
        circ = pcbnew.SHAPE_CIRCLE(p, mm(self.via_d / 2))
        for pad in self.pads:
            if pad.GetNetCode() == self.gnd and pad.GetNetCode() != 0:
                continue
            if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                d = math.hypot(to_mm(pad.GetPosition().x) - x, to_mm(pad.GetPosition().y) - y)
                if d < HOLE_TO_HOLE + VIA_DRILL / 2 + to_mm(max(pad.GetDrillSize().x, pad.GetDrillSize().y)) / 2 + MARGIN:
                    return "hole-hole pad"
            for l in self.layers:
                if pad.IsOnLayer(l) and pad.GetEffectiveShape(l).Collide(circ, mm(self.need(pad))):
                    return "pad"
        for t in self.tracks:
            if t.GetNetCode() == self.gnd:
                continue
            if t.GetClass() == "PCB_VIA":
                d = math.hypot(to_mm(t.GetPosition().x) - x, to_mm(t.GetPosition().y) - y)
                if d < HOLE_TO_HOLE + VIA_DRILL / 2 + to_mm(t.GetDrillValue()) / 2 + MARGIN:
                    return "hole-hole via"
                if t.GetEffectiveShape(self.F).Collide(circ, mm(self.need(t))):
                    return "via"
            else:
                if t.GetEffectiveShape(t.GetLayer()).Collide(circ, mm(self.need(t))):
                    return "track " + self.b.GetLayerName(t.GetLayer())
        for l in (self.F, self.B, self.L2):
            for z, polys in self.fills.get(l, []):
                if z.GetNetCode() != self.gnd and polys.Collide(circ, mm(self.need(z))):
                    return "fill " + self.b.GetLayerName(l)
        if not self.l3_pour_ok(x, y, circ):
            return "L3 pour split"
        # our own vias: hole-to-hole
        for it, kind in self.added:
            if kind == "via":
                d = math.hypot(to_mm(it.GetPosition().x) - x, to_mm(it.GetPosition().y) - y)
                if d < HOLE_TO_HOLE + VIA_DRILL + MARGIN:
                    return "hole-hole own"
        return None

    def via_ok(self, x, y, why=None):
        r = self.via_why(x, y)
        if r is not None and why is not None:
            why[r] = why.get(r, 0) + 1
        return r is None

    def track_ok(self, a, b, layer):
        seg = pcbnew.SHAPE_SEGMENT(pt(*a), pt(*b), mm(TRACK_W))
        for pad in self.pads:
            if pad.GetNetCode() == self.gnd and pad.GetNetCode() != 0:
                continue
            if pad.IsOnLayer(layer) and pad.GetEffectiveShape(layer).Collide(seg, mm(self.need(pad))):
                return False
        for t in self.tracks:
            if t.GetNetCode() == self.gnd:
                continue
            if t.GetClass() == "PCB_VIA" or t.GetLayer() == layer:
                if t.GetEffectiveShape(layer).Collide(seg, mm(self.need(t))):
                    return False
        for z, polys in self.fills.get(layer, []):
            if z.GetNetCode() != self.gnd and polys.Collide(seg, mm(self.need(z))):
                return False
        return True

    # ---- placement ------------------------------------------------------------
    def add_via(self, x, y):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(pt(x, y))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(self.F, self.B)
        v.SetWidth(mm(self.via_d))
        v.SetDrill(mm(VIA_DRILL))
        v.SetNetCode(self.gnd)
        self.b.Add(v)
        self.added.append((v, "via"))
        return v

    def add_track(self, a, b, layer):
        t = pcbnew.PCB_TRACK(self.b)
        t.SetStart(pt(*a))
        t.SetEnd(pt(*b))
        t.SetWidth(mm(TRACK_W))
        t.SetLayer(layer)
        t.SetNetCode(self.gnd)
        self.b.Add(t)
        self.added.append((t, "track"))
        return t

    # ---- stage 0: pour settings ----------------------------------------------
    def tighten_pours(self):
        """KiCad gives a new zone 0.5 mm clearance and the generator never
        overrode it, so the pours stopped 0.5 mm short of every track and could
        not reach GND pads in the pocket (T2 cycle 1: 78 -> 58 unconnected from
        this alone). DRC still enforces the netclass clearances on the fill."""
        changed = 0
        for z in self.zones:
            if z.GetIsRuleArea() or z.GetNetCode() == 0:
                continue
            want = POUR_CLR["GND"] if z.GetNetCode() == self.gnd else POUR_CLR["other"]
            if to_mm(z.GetLocalClearance()) > want + 1e-6:
                z.SetLocalClearance(mm(want))
                changed += 1
            if to_mm(z.GetThermalReliefGap()) > POUR_GAP + 1e-6:
                z.SetThermalReliefGap(mm(POUR_GAP))
        if changed:
            pcbnew.ZONE_FILLER(self.b).Fill(self.b.Zones())
            self.refresh()
        print(f"pours: {changed} zone(s) tightened to {POUR_CLR} mm clearance")
        return changed

    # ---- stage 1: islands ------------------------------------------------------
    def islands_without_via(self):
        out = []
        for l, name in ((self.F, "F.Cu"), (self.B, "B.Cu")):
            for z, polys in self.fills.get(l, []):
                if z.GetNetCode() != self.gnd:
                    continue
                for i in range(polys.OutlineCount()):
                    o = polys.Outline(i)
                    if any(o.PointInside(v.GetPosition()) for v in self.gnd_vias):
                        continue
                    if any(o.PointInside(p.GetPosition()) for p in self.gnd_pth):
                        continue
                    if any(o.PointInside(v.GetPosition()) for v, k in self.added if k == "via"):
                        continue
                    out.append((name, polys, i))
        return out

    def stitch_islands(self):
        done = skipped = 0
        for name, polys, i in self.islands_without_via():
            o = polys.Outline(i)
            holes = [polys.Hole(i, j) for j in range(polys.HoleCount(i))]
            bb = o.BBox()
            x0, y0 = to_mm(bb.GetX()), to_mm(bb.GetY())
            x1, y1 = to_mm(bb.GetRight()), to_mm(bb.GetBottom())
            best = None
            why = {}
            y = y0
            while y <= y1:
                x = x0
                while x <= x1:
                    p = pt(x, y)
                    if o.PointInside(p) and not any(h.PointInside(p) for h in holes):
                        inset = to_mm(o.Distance(p, True))   # outline only: inside points are 0 otherwise
                        for h in holes:
                            inset = min(inset, to_mm(h.Distance(p, True)))
                        if inset >= self.via_d / 2 + MARGIN and (best is None or inset > best[0]):
                            if self.via_ok(x, y, why):
                                best = (inset, x, y)
                    x += GRID
                y += GRID
            if best is None:
                skipped += 1
                print(f"  island {name} at ({x0:.1f},{y0:.1f}) {x1 - x0:.1f}x{y1 - y0:.1f} mm: no legal via spot {why}")
                continue
            self.add_via(best[1], best[2])
            done += 1
            print(f"  island {name} at ({x0:.1f},{y0:.1f}) {x1 - x0:.1f}x{y1 - y0:.1f} mm: via at ({best[1]:.2f},{best[2]:.2f}) inset {best[0]:.2f}")
        print(f"islands: {done} vias placed, {skipped} islands without a legal spot")
        return done

    # ---- stage 2: pads ----------------------------------------------------------
    def pad_has_via(self, pad):
        try:
            conn = self.b.GetConnectivity()
            items = conn.GetConnectedItems(pad, [pcbnew.PCB_VIA_T])
            if len(items) > 0:
                return True
        except Exception:
            pass
        # geometric fallback: a GND via touching the pad copper
        for v in self.gnd_vias + [it for it, k in self.added if k == "via"]:
            if pad.GetEffectiveShape(pad.GetLayer()).Collide(v.GetEffectiveShape(pad.GetLayer()), 0):
                return True
        return False

    def pad_in_stitched_island(self, pad):
        l = pad.GetLayer()
        for z, polys in self.fills.get(l, []):
            if z.GetNetCode() != self.gnd:
                continue
            for i in range(polys.OutlineCount()):
                o = polys.Outline(i)
                if o.PointInside(pad.GetPosition()):
                    if any(o.PointInside(v.GetPosition()) for v in self.gnd_vias):
                        return True
                    if any(o.PointInside(p.GetPosition()) for p in self.gnd_pth):
                        return True
                    if any(o.PointInside(v.GetPosition()) for v, k in self.added if k == "via"):
                        return True
        return False

    def stitch_pads(self):
        self.b.BuildConnectivity()
        done = skipped = 0
        for pad in self.gnd_smd:
            if pad.GetLayer() not in (self.F, self.B):
                continue
            if self.pad_has_via(pad) or self.pad_in_stitched_island(pad):
                continue
            cx, cy = to_mm(pad.GetPosition().x), to_mm(pad.GetPosition().y)
            bb = pad.GetBoundingBox()
            half = max(to_mm(bb.GetWidth()), to_mm(bb.GetHeight())) / 2
            base = half + VIA_D / 2 + 0.05
            placed = False
            why = {}
            w, h = to_mm(bb.GetWidth()), to_mm(bb.GetHeight())
            ax = (1, 0) if w >= h else (0, 1)      # pad long axis for in-pad offsets
            inpad = [(cx, cy)] + [(cx + ax[0] * d, cy + ax[1] * d) for d in (0.12, -0.12, 0.2, -0.2)]
            for via_d in (VIA_D, VIA_SMALL):
                self.via_d = via_d
                # adjacent via with a short link first, via-in-pad as fallback
                for extra in RING:
                    r = base + extra
                    for k in range(ANGLES):
                        a = 2 * math.pi * k / ANGLES
                        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
                        if not self.via_ok(x, y, why):
                            continue
                        if not self.track_ok((cx, cy), (x, y), pad.GetLayer()):
                            why["track"] = why.get("track", 0) + 1
                            continue
                        self.add_via(x, y)
                        self.add_track((cx, cy), (x, y), pad.GetLayer())
                        placed = True
                        break
                    if placed:
                        break
                if not placed:
                    for x, y in inpad:
                        if self.via_ok(x, y, why):
                            self.add_via(x, y)
                            placed = True
                            break
                if placed:
                    break
            self.via_d = VIA_D
            label = f"{pad.GetParentAsString()}.{pad.GetNumber()}"
            if placed:
                done += 1
                print(f"  pad {label} ({cx:.1f},{cy:.1f}) {self.b.GetLayerName(pad.GetLayer())}: via at ({x:.2f},{y:.2f})")
            else:
                skipped += 1
                print(f"  pad {label} ({cx:.1f},{cy:.1f}) {self.b.GetLayerName(pad.GetLayer())}: no legal via spot {why}")
        print(f"pads: {done} vias placed, {skipped} pads without a legal spot")
        return done

    # ---- stage 3: gate -------------------------------------------------------------
    def fill_and_save(self):
        pcbnew.ZONE_FILLER(self.b).Fill(self.b.Zones())
        pcbnew.SaveBoard(self.path, self.b)

    def drc(self, tag):
        rpt = self.path + f".stitch-{tag}.rpt"
        subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "-o", rpt, self.path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        txt = open(rpt).read()
        errs, unconn = [], {}
        for blk in re.split(r"\n(?=\[)", txt):
            if not blk.startswith("["):
                continue
            if blk.startswith("[unconnected"):
                nets = re.findall(r"\[([^\]]*)\] (?:of \S+ )?on", blk)
                net = nets[0] if nets else "?"
                unconn[net] = unconn.get(net, 0) + 1
            else:
                pos = [(float(x), float(y)) for x, y in re.findall(r"@\(([\d.]+) mm, ([\d.]+) mm\)", blk)]
                errs.append((blk.split("\n")[0][:70], pos))
        return errs, unconn

    def remove_at(self, positions, radius=0.35):
        removed = 0
        keep = []
        for it, kind in self.added:
            x, y = to_mm(it.GetPosition().x), to_mm(it.GetPosition().y)
            if kind == "track":
                xs = (to_mm(it.GetStart().x), to_mm(it.GetEnd().x))
                ys = (to_mm(it.GetStart().y), to_mm(it.GetEnd().y))
                hit = any(min(math.hypot(px - xx, py - yy) for xx, yy in zip(xs, ys)) < radius for px, py in positions)
            else:
                hit = any(math.hypot(px - x, py - y) < radius for px, py in positions)
            if hit:
                self.b.Remove(it)
                removed += 1
            else:
                keep.append((it, kind))
        self.added = keep
        return removed

    def gate(self, base_unconn):
        for attempt in range(4):
            self.fill_and_save()
            errs, unconn = self.drc(f"gate{attempt}")
            total = sum(unconn.values())
            worse = {n: c for n, c in unconn.items() if n != "GND" and c > base_unconn.get(n, 0)}
            print(f"gate {attempt}: errors={len(errs)} unconnected={total} (GND {unconn.get('GND', 0)})"
                  + (f" worse non-GND nets: {worse}" if worse else ""))
            if not errs and not worse:
                return total, unconn
            positions = [p for _e, ps in errs for p in ps]
            for e, _ps in errs[:8]:
                print("   ", e)
            n = self.remove_at(positions)
            if worse:
                # drop vias that sit inside a PWR_L3 pour of another net
                dropped = 0
                keep = []
                for it, kind in self.added:
                    if kind == "via":
                        p = it.GetPosition()
                        inpour = any(z.GetNetCode() != self.gnd and polys.Contains(p)
                                     for z, polys in self.fills.get(self.L3, []))
                        if inpour:
                            self.b.Remove(it)
                            dropped += 1
                            continue
                    keep.append((it, kind))
                self.added = keep
                n += dropped
            # orphan tracks (their via was removed) go too
            vias = {(it.GetPosition().x, it.GetPosition().y) for it, k in self.added if k == "via"}
            keep = []
            for it, kind in self.added:
                if kind == "track" and (it.GetEnd().x, it.GetEnd().y) not in vias:
                    self.b.Remove(it)
                    n += 1
                else:
                    keep.append((it, kind))
            self.added = keep
            print(f"   removed {n} of our items, retrying")
            if n == 0:
                break
        return None, None


def main():
    bd = Board(PCB)
    print(f"board {PCB}")
    print(f"GND: {len(bd.gnd_vias)} vias, {len(bd.gnd_pth)} PTH pads, {len(bd.gnd_smd)} SMD pads")
    errs0, unconn0 = bd.drc("before")
    total0 = sum(unconn0.values())
    print(f"before: errors={len(errs0)} unconnected={total0} (GND {unconn0.get('GND', 0)})")
    if errs0:
        sys.exit("STITCH_BASELINE_NOT_CLEAN")
    if bd.tighten_pours():
        bd.fill_and_save()
        errs1, unconn1 = bd.drc("pours")
        print(f"after pours: errors={len(errs1)} unconnected={sum(unconn1.values())} (GND {unconn1.get('GND', 0)})")
        if errs1:
            sys.exit("STITCH_POURS_NOT_CLEAN")
    n_isl = bd.stitch_islands()
    n_pad = bd.stitch_pads()
    if os.environ.get("STITCH_DRY"):
        print(f"dry run: would add {n_isl + n_pad} vias")
        return
    total, unconn = bd.gate(unconn0)
    if total is None:
        sys.exit("STITCH_GATE_FAILED")
    nv = sum(1 for _i, k in bd.added if k == "via")
    nt = sum(1 for _i, k in bd.added if k == "track")
    print(f"STITCH_OK vias={nv} tracks={nt} unconnected {total0} -> {total} (GND {unconn0.get('GND', 0)} -> {unconn.get('GND', 0)})")


if __name__ == "__main__":
    main()
