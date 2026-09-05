#!/usr/bin/env python3
"""Hand-route the HV nets with a grid maze router, then lock them.

Autorouters are not trusted with the 100 V front end: FreeRouting v2.4.1 was
measured violating the HV netclass clearance 30 times and undercutting the
board's minimum track width. So these nets are routed here, under explicit
control, and locked as Specctra `(type fix)` before any autorouter sees the
board.

Why a maze router and not straight lines: the first attempt drew L-shapes
between HV pads and ploughed through D2, U5 and J1 - 13 shorts. A real router
has to see obstacles.

Clearances applied per cell, from the agreed policy:
  HV copper -> non-HV, non-GND copper   1.50 mm   (handoff section 7)
  HV copper -> other HV / GND copper    0.60 mm   (HV netclass, IPC-2221 100 V)
  HV copper -> board edge               1.00 mm   (.kicad_dru rule)

Run:  PYTHONPATH=tools python3 tools/pcbroute_hv.py
"""
import heapq
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbgen import PCB, mm, pt, canonicalise                # noqa: E402
from netclasses import HV as HV_NETS                        # noqa: E402

to_mm = pcbnew.ToMM

RES = 0.15            # mm per cell
HV_W = 0.50           # HV netclass track width
CLR_LV = 1.50         # to non-HV, non-GND
CLR_HV = 0.60         # to other HV, and to GND copper
CLR_EDGE = 1.00       # to the board edge
VIA_D, VIA_DRILL = 0.80, 0.40      # HV netclass via
VIA_COST = 14         # in cell units, discourages layer hopping
LAYERS = None         # filled in main()

# Components whose own pad-to-pad spacing is exempt from the 1.5 mm HV-to-LV
# separation, matching the rules already in telematics-tracker.kicad_dru. These
# parts ARE the HV->LV transition and their pin spacing is the package, so
# applying 1.5 mm around their LV pads walls off their own HV pads.
#   R30-R35  sense dividers, 32.35 V across each (<= 40 V policy)
#   R40      DNP spare divider, 91.7 V - IPC-2221 + coating basis
#   Q1, Q2   DO FETs, LV gate against HV drain
#   U5       F-20: exposed pad is VIN_B, own pins 0.55 mm away
#   OK1, OK2 the isolation barrier itself
#   X1       vendor footprint internal spacing
# Obstacles belonging to these get the HV-grade 0.60 mm instead of 1.50 mm.
# D16 needs no entry: its other terminal is GND, already excepted by the rule.
EXEMPT_FOOTPRINTS = {"R30", "R31", "R32", "R33", "R34", "R35",
                     "Q1", "Q2", "U5", "OK1", "OK2", "X1", "L1"}


def main():
    board = pcbnew.LoadBoard(PCB)
    global LAYERS
    LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]

    bb = board.GetBoardEdgesBoundingBox()
    x0, y0 = to_mm(bb.GetLeft()), to_mm(bb.GetTop())
    x1, y1 = to_mm(bb.GetRight()), to_mm(bb.GetBottom())
    NX = int((x1 - x0) / RES) + 1
    NY = int((y1 - y0) / RES) + 1
    print(f"grid {NX} x {NY} cells at {RES} mm, {len(LAYERS)} layers")

    def cell(x, y):
        return (int(round((x - x0) / RES)), int(round((y - y0) / RES)))

    def pos(ix, iy):
        return (x0 + ix * RES, y0 + iy * RES)

    # ---- collect copper obstacles ------------------------------------
    # (netname, layer-list, x, y, half-width-x, half-width-y)
    obst = []
    for f in board.GetFootprints():
        for p in f.Pads():
            b = p.GetBoundingBox()
            lays = [l for l in p.GetLayerSet().CuStack()]
            obst.append((p.GetNetname(), lays,
                         to_mm(b.GetCenter().x), to_mm(b.GetCenter().y),
                         to_mm(b.GetWidth()) / 2, to_mm(b.GetHeight()) / 2,
                         f.GetReference()))
    def add_tracks():
        out = []
        for t in board.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA):
                out.append((t.GetNetname(), LAYERS,
                            to_mm(t.GetPosition().x), to_mm(t.GetPosition().y),
                            to_mm(t.GetWidth()) / 2, to_mm(t.GetWidth()) / 2,
                            ""))
            else:
                a = t.GetStart(); b2 = t.GetEnd()
                w = to_mm(t.GetWidth()) / 2
                # sample the segment so a coarse box does not over-block
                ax, ay = to_mm(a.x), to_mm(a.y)
                bx, by = to_mm(b2.x), to_mm(b2.y)
                n = max(1, int(math.hypot(bx - ax, by - ay) / RES))
                for i in range(n + 1):
                    tt = i / n
                    out.append((t.GetNetname(), [t.GetLayer()],
                                ax + (bx - ax) * tt, ay + (by - ay) * tt,
                                w, w, ""))
        return out
    obst += add_tracks()
    print(f"copper obstacles: {len(obst)}")

    placed = []          # tracks/vias we add, as extra obstacles for later nets

    # Courtyard boxes of the exempt footprints. The .kicad_dru exemptions are
    # all of the form insideCourtyard(X) && insideCourtyard(X) - they relax the
    # spacing INSIDE one package, not around it. Relaxing globally let a
    # DO2_OUT track pass 0.542 mm from Q1's gate pad out in the open, which DRC
    # correctly called against the 1.5 mm rule.
    exempt_court = {}
    for f in board.GetFootprints():
        if f.GetReference() in EXEMPT_FOOTPRINTS:
            c = f.GetCourtyard(pcbnew.F_Cu)
            if c.OutlineCount() == 0:
                c = f.GetCourtyard(pcbnew.B_Cu)
            bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox()
            exempt_court[f.GetReference()] = (
                to_mm(bb.GetLeft()), to_mm(bb.GetTop()),
                to_mm(bb.GetRight()), to_mm(bb.GetBottom()))

    def build_blocked(netname):
        """bytearray per layer: 1 = this net's track centre may not sit here."""
        grids = [bytearray(NX * NY) for _ in LAYERS]
        # Sized for the LARGEST item we place, not the track: a via is 0.80 mm
        # across, so a cell legal for a 0.50 mm track is illegal for a via
        # dropped at the same cell. Most of the 128 clearance violations were
        # on vias for exactly this reason.
        half = max(HV_W, VIA_D) / 2
        for onet, lays, ox, oy, hw, hh, oref in obst + placed:
            if onet == netname:
                continue
            if onet in HV_NETS or onet == "GND":
                clr = CLR_HV
            elif onet == "" or onet is None:
                clr = CLR_HV          # netless pad: treat as HV-grade
            elif oref in EXEMPT_FOOTPRINTS:
                clr = CLR_HV          # transition device, see EXEMPT_FOOTPRINTS
            else:
                clr = CLR_LV
            # Quantise the halo OUTWARD. cell() rounds to nearest, so a cell
            # centre could sit up to RES/2 = 0.075 mm inside the forbidden
            # region - which is exactly the size of the 0.545..0.594 mm
            # shortfalls DRC reported against the 0.600 mm HV clearance.
            def box(clr_):
                rx, ry = hw + clr_ + half, hh + clr_ + half
                return (int(math.floor((ox - rx - x0) / RES)),
                        int(math.floor((oy - ry - y0) / RES)),
                        int(math.ceil((ox + rx - x0) / RES)),
                        int(math.ceil((oy + ry - y0) / RES)))

            # An exempt package relaxes to CLR_HV only INSIDE its own
            # courtyard; beyond it the full CLR_LV separation still applies.
            court = exempt_court.get(oref) if clr == CLR_HV and \
                oref in exempt_court and onet not in HV_NETS and onet != "GND" \
                else None
            regions = [box(clr)]
            if court is not None:
                cx0, cy0, cx1, cy1 = court
                regions.append((box(CLR_LV), (cx0, cy0, cx1, cy1)))
            for li, lay in enumerate(LAYERS):
                if lay not in lays:
                    continue
                g = grids[li]
                i0, j0, i1, j1 = regions[0]
                for j in range(max(0, j0), min(NY - 1, j1) + 1):
                    row = j * NX
                    for i in range(max(0, i0), min(NX - 1, i1) + 1):
                        g[row + i] = 1
                if court is None:
                    continue
                (li0, lj0, li1, lj1), (cx0, cy0, cx1, cy1) = regions[1]
                for j in range(max(0, lj0), min(NY - 1, lj1) + 1):
                    row = j * NX
                    py = y0 + j * RES
                    for i in range(max(0, li0), min(NX - 1, li1) + 1):
                        px = x0 + i * RES
                        if cx0 <= px <= cx1 and cy0 <= py <= cy1:
                            continue          # inside the package: relaxed
                        g[row + i] = 1
        # board edge
        e = int((CLR_EDGE + half) / RES) + 1
        for g in grids:
            for j in range(NY):
                row = j * NX
                for i in range(NX):
                    if i < e or i >= NX - e or j < e or j >= NY - e:
                        g[row + i] = 1
        return grids

    def astar(grids, starts, goals):
        """8-connected A* across both layers. starts/goals are (li,ix,iy)."""
        goalset = set(goals)
        if not goalset:
            return None
        gx = sum(g[1] for g in goals) / len(goals)
        gy = sum(g[2] for g in goals) / len(goals)

        def h(li, ix, iy):
            return math.hypot(ix - gx, iy - gy)

        openh = []
        best = {}
        for s in starts:
            best[s] = 0.0
            heapq.heappush(openh, (h(*s), 0.0, s, None))
        came = {}
        NB = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
              (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
        while openh:
            _, g, cur, parent = heapq.heappop(openh)
            if cur in came:
                continue
            came[cur] = parent
            if cur in goalset:
                path = [cur]
                while came[path[-1]] is not None:
                    path.append(came[path[-1]])
                return path[::-1]
            li, ix, iy = cur
            for dx, dy, w in NB:
                nx_, ny_ = ix + dx, iy + dy
                if not (0 <= nx_ < NX and 0 <= ny_ < NY):
                    continue
                if grids[li][ny_ * NX + nx_]:
                    continue
                nxt = (li, nx_, ny_)
                ng = g + w
                if ng < best.get(nxt, 1e18):
                    best[nxt] = ng
                    heapq.heappush(openh, (ng + h(*nxt), ng, nxt, cur))
            # layer change
            for lj in range(len(LAYERS)):
                if lj == li or grids[lj][iy * NX + ix]:
                    continue
                nxt = (lj, ix, iy)
                ng = g + VIA_COST
                if ng < best.get(nxt, 1e18):
                    best[nxt] = ng
                    heapq.heappush(openh, (ng + h(*nxt), ng, nxt, cur))
        return None

    def pad_cells(p):
        """cells covered by a pad, per layer it exists on"""
        b = p.GetBoundingBox()
        cx, cy = to_mm(b.GetCenter().x), to_mm(b.GetCenter().y)
        hw, hh = to_mm(b.GetWidth()) / 2, to_mm(b.GetHeight()) / 2
        lays = [l for l in p.GetLayerSet().CuStack()]
        out = []
        for li, lay in enumerate(LAYERS):
            if lay not in lays:
                continue
            i0, j0 = cell(cx - hw * 0.9, cy - hh * 0.9)
            i1, j1 = cell(cx + hw * 0.9, cy + hh * 0.9)
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    if 0 <= i < NX and 0 <= j < NY:
                        out.append((li, i, j))
        return out or [(0,) + cell(cx, cy)]

    # ---- route each HV net -------------------------------------------
    results = {}
    for netname in HV_NETS:
        net = board.FindNet(netname)
        if net is None:
            continue
        pads = []
        for f in board.GetFootprints():
            for p in f.Pads():
                if p.GetNetname() == netname:
                    pads.append((f"{f.GetReference()}.{p.GetNumber()}", p))
        if len(pads) < 2:
            continue
        grids = build_blocked(netname)
        connected = list(pad_cells(pads[0][1]))
        made, failed = 0, []
        for name, p in pads[1:]:
            goals = pad_cells(p)
            path = astar(grids, connected, goals)
            if path is None:
                failed.append(name)
                continue
            # emit
            prev = None
            for (li, ix, iy) in path:
                if prev is not None:
                    if prev[0] != li:
                        v = pcbnew.PCB_VIA(board)
                        v.SetPosition(pt(*pos(ix, iy)))
                        v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL))
                        v.SetNet(net); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                        v.SetLocked(True); board.Add(v)
                        placed.append((netname, LAYERS, *pos(ix, iy),
                                       VIA_D / 2, VIA_D / 2, ""))
                    else:
                        t = pcbnew.PCB_TRACK(board)
                        t.SetStart(pt(*pos(*prev[1:])))
                        t.SetEnd(pt(*pos(ix, iy)))
                        t.SetWidth(mm(HV_W)); t.SetLayer(LAYERS[li])
                        t.SetNet(net); t.SetLocked(True); board.Add(t)
                        placed.append((netname, [LAYERS[li]],
                                       *pos(ix, iy), HV_W / 2, HV_W / 2, ""))
                prev = (li, ix, iy)
            connected += path
            made += 1
            grids = build_blocked(netname)     # refresh with own copper
        results[netname] = (made, len(pads) - 1, failed)
        flag = "" if not failed else f"  FAILED: {', '.join(failed)}"
        print(f"  {netname:24} {made}/{len(pads)-1} connections{flag}")

    tot = sum(r[0] for r in results.values())
    need = sum(r[1] for r in results.values())
    print(f"\nHV routed: {tot}/{need} connections")
    board.BuildListOfNets()
    try:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    except Exception as e:
        print(f"  zone refill: {e}")
    pcbnew.SaveBoard(PCB, board)
    canonicalise(PCB)
    print("saved and canonicalised (all HV copper LOCKED)")


if __name__ == "__main__":
    main()
