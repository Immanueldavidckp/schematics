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

Clearances applied per cell, from the agreed policy (and its two approved
rescopes - BUCK_HV area and the MV class, see telematics-tracker.kicad_dru):
  HV copper -> LV copper                1.50 mm   (handoff section 7)
     ... except inside BUCK_HV or an exempt courtyard:  0.60 mm
  HV copper -> HV / MV / GND copper     0.60 mm   (netclass, IPC-2221 100 V)
  MV copper -> anything                 0.60 mm   (MV netclass)
  HV/MV copper -> board edge            1.00 mm   (.kicad_dru rule)

Run:  PYTHONPATH=tools python3 tools/pcbroute_hv.py
"""
import heapq
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbgen import PCB, mm, pt, canonicalise                # noqa: E402
from netclasses import HV as HV_NETS, MV as MV_NETS         # noqa: E402
from pcbplace import BUCK_X, BUCK_Y                          # noqa: E402
from pcbgen import HV_X                                      # noqa: E402

to_mm = pcbnew.ToMM

RES = 0.10            # mm per cell. 0.15 left the single-cell escape lane
                      # out of U5.6 (between pins 5 and 7) too coarse to enter
HV_W = 0.50           # HV netclass track width
MV_W = 0.30           # MV runs (class minimum 0.20; 0.30 for a little margin)
CLR_LV = 1.50         # HV to LV, outside BUCK_HV / exempt courtyards
CLR_HV = 0.60         # electrical minimum: HV/MV to anything
CLR_EDGE = 1.00       # to the board edge
VIA_D, VIA_DRILL = 0.80, 0.40      # HV netclass via
MV_VIA_D, MV_VIA_DRILL = 0.50, 0.30
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


# ---- route nets, most-constrained first ----------------------------
# Order is not cosmetic. Routed greedily in declaration order, VIN_P (an
# open-field net: D2, C71, C72, R80) routed FIRST and its locked copper
# walled C73.1 into a 626-cell pocket - flood-fill measured - making
# VIN_B 0/4 even though every endpoint was reachable on the empty board.
# So: the buck cluster (tightest area on the board) routes first, then the
# chain nets, and the long-haul VIN/VIN_P/VIN_F nets last - they have the
# whole left strip to work around whatever is already down.
ORDER = ["/power/U5_IS", "/power/SW_BUCK", "/power/U5_VB", "/power/VIN_B",
         # VIN_P is all short local hops around R80/D2/C70-C72 now that
         # the caps are anchored beside their source node - route it
         # before the DI/DO copper can wall the area
         "/power/VIN_P", "/power/VIN_F",
         # DO nets span the whole strip (J1 -> clamps at the top -> FETs
         # at the bottom): they need the north-south freeway before the
         # DI/divider copper eats it. Routed second-to-last they failed;
         # the same hop routed cleanly on a board that already carried
         # the freeway copper.
         "/io/DO1_OUT", "/io/DO2_OUT",
         "/io/DI1_IN", "/io/DI1_M1", "/io/DI1_M2", "/io/DI1_LED",
         "/io/DI2_IN", "/io/DI2_M1", "/io/DI2_M2", "/io/DI2_LED",
         "/io/VIN_D0", "/io/VIN_D1", "/io/IGN", "/io/IGN_D0",
         "/io/IGN_D1",
         "/io/J1_SPARE1", "/io/J1_SPARE2",
         "VIN"]


def route_attempt(order):
    """One full routing pass in the given net order, on a FRESH board loaded
    from disk. Returns (board, results). The board is not saved here - the
    caller keeps the best attempt. Fresh-load instead of undo because
    board.Remove() segfaults (see SKILL.md)."""
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

    def build_blocked(netname, half, hv_rules):
        """bytearray per layer: 1 = this net's track centre may not sit here.

        half     - half-width of the copper being placed
        hv_rules - True when routing an HV-class net: LV obstacles then get
                   the 1.5 mm halo outside BUCK_HV / exempt courtyards. MV
                   nets route at the electrical 0.60 mm to everything.

        Called TWICE per net: once with the track half-width and once with the
        via radius. Sizing one grid for the larger of the two blocked the
        axial escape lane out of U5's SOIC pins: at 1.27 mm pitch a 0.50 mm
        track exits along the pad axis with 0.72 mm to the neighbouring pins
        (legal, > 0.60), but a 0.80 mm via in the same cell would not be - and
        banning both made SW_BUCK unroutable at 0/4.
        """
        grids = [bytearray(NX * NY) for _ in LAYERS]
        buck = (HV_X, 0.5, BUCK_X, BUCK_Y)      # the approved rescope area
        for onet, lays, ox, oy, hw, hh, oref in obst + placed:
            if onet == netname:
                continue

            def box(clr_):
                rx, ry = hw + clr_ + half, hh + clr_ + half
                return (int(math.floor((ox - rx - x0) / RES)),
                        int(math.floor((oy - ry - y0) / RES)),
                        int(math.ceil((ox + rx - x0) / RES)),
                        int(math.ceil((oy + ry - y0) / RES)))

            is_lv = (onet not in HV_NETS and onet not in MV_NETS
                     and onet != "GND" and onet != "" and onet is not None)
            # Every pair has the electrical 0.60 mm floor (HV/MV netclass).
            hard = box(CLR_HV)
            # The 1.5 mm ring applies only HV -> LV, and is relaxed to the
            # electrical floor inside BUCK_HV and inside the obstacle's own
            # courtyard when the .kicad_dru exempts that package.
            soft = box(CLR_LV) if (hv_rules and is_lv) else None
            relaxed = [buck]
            if soft is not None and oref in exempt_court:
                relaxed.append(exempt_court[oref])
            for li, lay in enumerate(LAYERS):
                if lay not in lays:
                    continue
                g = grids[li]
                i0, j0, i1, j1 = hard
                for j in range(max(0, j0), min(NY - 1, j1) + 1):
                    row = j * NX
                    for i in range(max(0, i0), min(NX - 1, i1) + 1):
                        g[row + i] = 1
                if soft is None:
                    continue
                i0, j0, i1, j1 = soft
                for j in range(max(0, j0), min(NY - 1, j1) + 1):
                    row = j * NX
                    py = y0 + j * RES
                    for i in range(max(0, i0), min(NX - 1, i1) + 1):
                        px = x0 + i * RES
                        if any(rx0 <= px <= rx1 and ry0 <= py <= ry1
                               for rx0, ry0, rx1, ry1 in relaxed):
                            continue      # inside a rescoped region
                        g[row + i] = 1
        # board edge. ceil with an epsilon, NOT int(): (1.0 + 0.4) / 0.1
        # is 13.999999999999998 in floats, int() truncates to 13, and the
        # margin loses a whole cell - measured as a via 0.95 mm from the
        # edge against the 1.0 mm rule.
        e = int(math.ceil((CLR_EDGE + half) / RES - 1e-9)) + 1
        for g in grids:
            for j in range(NY):
                row = j * NX
                for i in range(NX):
                    if i < e or i >= NX - e or j < e or j >= NY - e:
                        g[row + i] = 1
        return grids

    def astar(tgrids, vgrids, starts, goals):
        """8-connected A* across both layers. starts/goals are (li,ix,iy).

        Lateral moves consult the track grid; a layer change needs the via
        grid free on BOTH layers, because a through via lands on both.
        """
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
                if tgrids[li][ny_ * NX + nx_]:
                    continue
                nxt = (li, nx_, ny_)
                ng = g + w
                if ng < best.get(nxt, 1e18):
                    best[nxt] = ng
                    heapq.heappush(openh, (ng + h(*nxt), ng, nxt, cur))
            # layer change
            for lj in range(len(LAYERS)):
                if lj == li or vgrids[lj][iy * NX + ix] \
                        or vgrids[li][iy * NX + ix]:
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

    results = {}
    for netname in order:
        hv_rules = netname in HV_NETS
        w = HV_W if hv_rules else MV_W
        vd, vdr = (VIA_D, VIA_DRILL) if hv_rules else (MV_VIA_D, MV_VIA_DRILL)
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
        tgrids = build_blocked(netname, w / 2, hv_rules)     # track cells
        vgrids = build_blocked(netname, vd / 2, hv_rules)    # via sites
        if os.environ.get("HV_DEBUG") == netname:
            for nm_, p_ in pads:
                cs_ = pad_cells(p_)
                fr_ = sum(1 for li_, i_, j_ in cs_ if not tgrids[li_][j_ * NX + i_])
                print(f"    DEBUG {nm_}: {fr_}/{len(cs_)} free")
            print(f"    DEBUG grid sums t={sum(tgrids[0])},{sum(tgrids[1])} "
                  f"v={sum(vgrids[0])},{sum(vgrids[1])} NX={NX} NY={NY}")
        connected = list(pad_cells(pads[0][1]))
        made, failed = 0, []
        for name, p in pads[1:]:
            goals = pad_cells(p)
            path = astar(tgrids, vgrids, connected, goals)
            if path is None:
                if os.environ.get("HV_DEBUG") == netname:
                    from collections import deque
                    seen = set(); dq = deque()
                    for c in connected:
                        li_, i_, j_ = c
                        if not tgrids[li_][j_ * NX + i_]:
                            seen.add(c); dq.append(c)
                    while dq:
                        li_, i_, j_ = dq.popleft()
                        for dx_, dy_ in ((1,0),(-1,0),(0,1),(0,-1),
                                         (1,1),(1,-1),(-1,1),(-1,-1)):
                            ni_, nj_ = i_ + dx_, j_ + dy_
                            if 0 <= ni_ < NX and 0 <= nj_ < NY and \
                                    not tgrids[li_][nj_ * NX + ni_] and \
                                    (li_, ni_, nj_) not in seen:
                                seen.add((li_, ni_, nj_)); dq.append((li_, ni_, nj_))
                        lj_ = 1 - li_
                        if not vgrids[lj_][j_ * NX + i_] and \
                                not vgrids[li_][j_ * NX + i_] and \
                                (lj_, i_, j_) not in seen:
                            seen.add((lj_, i_, j_)); dq.append((lj_, i_, j_))
                    hit = any(c in seen for c in goals)
                    print(f"    DEBUG astar=None for {name}: flood {len(seen)} "
                          f"cells, goal reachable={hit}")
                failed.append(name)
                continue
            # emit - COALESCED. One PCB_TRACK per cell step produced ~3500
            # collinear 0.10 mm stubs, and FreeRouting v2.4.1's search tree
            # NPE-crashloops on that geometry (measured: two 90-minute runs
            # died in the fanout stage throwing SearchTreeObject.shapeLayer
            # NullPointerExceptions). Consecutive steps in the same direction
            # on the same layer merge into one segment; electrically identical.
            runs = []
            prev = None
            for cur in path:
                if prev is not None:
                    if prev[0] != cur[0]:
                        runs.append(["via", cur, None, None])
                    else:
                        d = (cur[1] - prev[1], cur[2] - prev[2])
                        if runs and runs[-1][0] == "seg" \
                                and runs[-1][3] == (prev[0], d) \
                                and runs[-1][2] == prev:
                            runs[-1][2] = cur
                        else:
                            runs.append(["seg", prev, cur, (prev[0], d)])
                prev = cur
            for kind, a, b2, meta in runs:
                if kind == "via":
                    li, ix, iy = a
                    v = pcbnew.PCB_VIA(board)
                    v.SetPosition(pt(*pos(ix, iy)))
                    v.SetWidth(mm(vd)); v.SetDrill(mm(vdr))
                    v.SetNet(net); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                    v.SetLocked(True); board.Add(v)
                    placed.append((netname, LAYERS, *pos(ix, iy),
                                   vd / 2, vd / 2, ""))
                else:
                    li = meta[0]
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(pt(*pos(*a[1:])))
                    t.SetEnd(pt(*pos(*b2[1:])))
                    t.SetWidth(mm(w)); t.SetLayer(LAYERS[li])
                    t.SetNet(net); t.SetLocked(True); board.Add(t)
                    # obstacle samples along the merged run
                    n_ = max(abs(b2[1] - a[1]), abs(b2[2] - a[2]), 1)
                    for k in range(n_ + 1):
                        fx = a[1] + (b2[1] - a[1]) * k / n_
                        fy = a[2] + (b2[2] - a[2]) * k / n_
                        placed.append((netname, [LAYERS[li]],
                                       x0 + fx * RES, y0 + fy * RES,
                                       w / 2, w / 2, ""))
            connected += path
            connected += goals        # the whole pad is now copper, not just
                                      # the cell the path happened to enter on
            made += 1
            tgrids = build_blocked(netname, w / 2, hv_rules)   # own copper
            vgrids = build_blocked(netname, vd / 2, hv_rules)
        results[netname] = (made, len(pads) - 1, failed)
        flag = "" if not failed else f"  FAILED: {', '.join(failed)}"
        cls = "HV" if hv_rules else "MV"
        print(f"  {cls} {netname:24} {made}/{len(pads)-1} connections{flag}")

    return board, results


def main():
    """Route with failed-first retry.

    A single greedy pass oscillates: DO2 routed second-to-last failed; moved
    early it routed and DI2_IN failed instead. Each loser routes fine when
    given priority, so the fix is systematic: re-run the whole pass with the
    previous attempt's failed nets promoted to the front (after the buck
    trio, whose order is geometrically forced), until a pass completes or
    the failure set stops shrinking. Every pass obeys the same clearances -
    retrying changes ORDER, never a rule.
    """
    assert set(ORDER) == set(HV_NETS) | set(MV_NETS), \
        "ORDER must cover exactly the HV + MV nets"
    FORCED = ORDER[:3]                     # SW_BUCK, U5_VB, VIN_B
    order = list(ORDER)
    best = None                            # (fails, tot, board, results)
    for attempt in range(1, 5):
        print(f"--- attempt {attempt}: {', '.join(n.split('/')[-1] for n in order[:6])} ...")
        board, results = route_attempt(order)
        tot = sum(r[0] for r in results.values())
        need = sum(r[1] for r in results.values())
        failed_nets = [n for n in order if results.get(n, (0, 0, []))[2]]
        print(f"  attempt {attempt}: {tot}/{need} connections, "
              f"{len(failed_nets)} net(s) incomplete")
        if best is None or len(failed_nets) < best[0]:
            best = (len(failed_nets), tot, board, results)
        if not failed_nets:
            break
        promoted = [n for n in failed_nets if n not in FORCED]
        order = FORCED + promoted + [n for n in order
                                     if n not in FORCED and n not in promoted]
    fails, tot, board, results = best
    need = sum(r[1] for r in results.values())
    print(f"\nHV routed: {tot}/{need} connections "
          f"({fails} net(s) incomplete)")
    for n, (made, total, failed) in results.items():
        if failed:
            print(f"  UNROUTED {n}: {', '.join(failed)}")
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
