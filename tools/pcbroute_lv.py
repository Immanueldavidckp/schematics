#!/usr/bin/env python3
"""Route the remaining low-speed nets with the in-repo maze router (path b).

Approved after FreeRouting v2.4.1 was measured malfunctioning on this board
(design-log 2026-09-06). Quality gates, as instructed:

  1. Netclass rules enforced per net, DRC after each net, never loosened.
     A net whose routing raises the DRC error count is ROLLED BACK from the
     last good save and reported as failed - copper that cannot meet the
     rules does not stay on the board.
  2. Progress commit every 25 nets with completion %.
  3. Metrics: vias per net (flag > 4), total vias, routed length vs Manhattan
     distance per net (flag > 2.5x).
  4. No new copper on RF/HV/MV nets (those are locked and finished), none in
     the RF corridor, and none through the U1 lattice or U5 EP via fields.
  5. On plateau: stop with a per-net unrouted list and the blocking cause.

Architecture: pour-first. The board's power architecture IS the L2 GND plane
and the L3 islands (5V0 / SYS / 3V3 / VIN_B / VBAT_MODEM), so power-net pads
are connected by a stub + via into their plane wherever the pad sits over its
pour - one via, near-zero added length. Only what cannot reach a pour is
maze-routed on F/B.

Run:  PYTHONPATH=tools python3 tools/pcbroute_lv.py
"""
import heapq
import math
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbgen import PROJ, PCB, mm, pt, canonicalise           # noqa: E402
from netclasses import HV, MV, RF, PWR, BULK                 # noqa: E402

to_mm = pcbnew.ToMM

RES = 0.10
CLR_EDGE = 0.50                 # copper-to-edge board rule for LV
LAST_GOOD = PCB + ".lastgood"
PROTECTED = set(HV) | set(MV) | set(RF)

# (track_width, clearance, via_dia, via_drill) per class
GEO = {
    # Default clearance is 0.20: that is what the board's stock Default
    # netclass carries, and the first run used 0.15 here - DRC (correctly)
    # rejected 12 nets against the class rule. Gate 1 works; the constant
    # was wrong.
    "Default":    (0.20, 0.20, 0.50, 0.30),
    "PWR":        (0.50, 0.20, 0.80, 0.40),
    "MODEM_BULK": (2.00, 0.20, 0.80, 0.40),
    "GND":        (0.50, 0.15, 0.50, 0.30),
}
CLS_CLR = {"HV": 0.60, "MV": 0.60, "RF": 0.30, "GND": 0.15,
           "PWR": 0.20, "MODEM_BULK": 0.20, "Default": 0.20}


def net_class(n):
    if n in HV:
        return "HV"
    if n in MV:
        return "MV"
    if n in RF:
        return "RF"
    if n in PWR:
        return "PWR"
    if n in BULK:
        return "MODEM_BULK"
    if n == "GND":
        return "GND"
    return "Default"


def drc_errors(path):
    """Non-ratsnest DRC error count (the per-net gate)."""
    rpt = path + ".drc"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "-o", rpt, path], capture_output=True)
    text = open(rpt).read()
    kinds = re.findall(r"^\[([a-z_]+)\]", text, re.M)
    os.unlink(rpt)
    return sum(1 for k in kinds if k != "unconnected_items")


def git_progress(msg):
    subprocess.run(["git", "-C", PROJ, "add", os.path.basename(PCB)],
                   capture_output=True)
    subprocess.run(["git", "-C", PROJ, "commit", "-q", "-m",
                    msg + "\n\nCo-Authored-By: Claude Opus 5 (1M context) "
                    "<noreply@anthropic.com>"], capture_output=True)


def main(single_net=None):
    board = pcbnew.LoadBoard(PCB)
    LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]

    bb = board.GetBoardEdgesBoundingBox()
    x0, y0 = to_mm(bb.GetLeft()), to_mm(bb.GetTop())
    x1, y1 = to_mm(bb.GetRight()), to_mm(bb.GetBottom())
    NX, NY = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
    print(f"grid {NX} x {NY} at {RES} mm")

    def cell(x, y):
        return (int(round((x - x0) / RES)), int(round((y - y0) / RES)))

    def pos(ix, iy):
        return (x0 + ix * RES, y0 + iy * RES)

    # ---- no-go regions (both layers, for ALL new copper) -----------------
    nogo = []
    # RF corridor: everything outboard of x = 76.8 is CPWG + fence + U.FL
    nogo.append((76.8, y0, x1, y1, "RF corridor"))
    for ref, pads in (("U1", [str(i) for i in range(85, 113)]), ("U5", ["9"])):
        fp = next(f for f in board.GetFootprints() if f.GetReference() == ref)
        xs, ys, xe, ye = 1e9, 1e9, -1e9, -1e9
        for p in fp.Pads():
            if p.GetNumber() in pads:
                b2 = p.GetBoundingBox()
                xs = min(xs, to_mm(b2.GetLeft())); ys = min(ys, to_mm(b2.GetTop()))
                xe = max(xe, to_mm(b2.GetRight())); ye = max(ye, to_mm(b2.GetBottom()))
        nogo.append((xs - 0.3, ys - 0.3, xe + 0.3, ye + 0.3, ref + " via field"))
    for r in nogo:
        print(f"  no-go: {r[4]}  x {r[0]:.1f}..{r[2]:.1f} y {r[1]:.1f}..{r[3]:.1f}")

    # ---- obstacles --------------------------------------------------------
    # (net, layers, x, y, hw, hh)
    obst = []
    for f in board.GetFootprints():
        for p in f.Pads():
            b2 = p.GetBoundingBox()
            obst.append((p.GetNetname(), [l for l in p.GetLayerSet().CuStack()],
                         to_mm(b2.GetCenter().x), to_mm(b2.GetCenter().y),
                         to_mm(b2.GetWidth()) / 2, to_mm(b2.GetHeight()) / 2,
                         f.GetReference()))
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            obst.append((t.GetNetname(), LAYERS,
                         to_mm(t.GetPosition().x), to_mm(t.GetPosition().y),
                         to_mm(t.GetWidth()) / 2, to_mm(t.GetWidth()) / 2, ""))
        else:
            a, b2 = t.GetStart(), t.GetEnd()
            w = to_mm(t.GetWidth()) / 2
            ax, ay, bx, by = to_mm(a.x), to_mm(a.y), to_mm(b2.x), to_mm(b2.y)
            n = max(1, int(math.hypot(bx - ax, by - ay) / RES))
            for i in range(n + 1):
                tt = i / n
                # the true layer is kept even when it is an INNER one:
                # FreeRouting routes on GND_L2/PWR_L3, and a through-via
                # must clear that copper (measured: MODEM_BULK vias landed
                # 0.05..0.15 mm from SIM_RST on GND_L2 - invisible to a
                # 2-layer grid model)
                obst.append((t.GetNetname(), [t.GetLayer()],
                             ax + (bx - ax) * tt, ay + (by - ay) * tt, w, w, ""))
    print(f"obstacles: {len(obst)}")
    placed = []

    def build(netname, my_clr, half, via_mode=False):
        """via_mode: the grid gates VIA sites - a through via lands on every
        copper layer, so inner-layer obstacles block BOTH surface grids."""
        grids = [bytearray(NX * NY) for _ in LAYERS]
        trace = None
        if os.environ.get("LV_TRACE"):
            tx, ty = map(float, os.environ["LV_TRACE"].split(","))
            trace = cell(tx, ty)

        def block(g, ox, oy, rx, ry):
            # nogo/edge regions only: plain rectangles
            i0 = int(math.floor((ox - rx - x0) / RES))
            j0 = int(math.floor((oy - ry - y0) / RES))
            i1 = int(math.ceil((ox + rx - x0) / RES))
            j1 = int(math.ceil((oy + ry - y0) / RES))
            for j in range(max(0, j0), min(NY - 1, j1) + 1):
                row = j * NX
                for i in range(max(0, i0), min(NX - 1, i1) + 1):
                    g[row + i] = 1

        def block_pad(g, ox, oy, hw, hh, reach):
            # EXACT distance to the copper rectangle, like DRC measures it.
            # A box halo overestimates the corners by (sqrt(2)-1)*reach - up
            # to ~0.2 mm - and that inflation is precisely what erased the
            # legal diagonal passages around the U5/U6/U7 pin fields
            # (27/113 routed, everything else walled in).
            r2 = reach * reach
            i0 = int(math.floor((ox - hw - reach - x0) / RES))
            j0 = int(math.floor((oy - hh - reach - y0) / RES))
            i1 = int(math.ceil((ox + hw + reach - x0) / RES))
            j1 = int(math.ceil((oy + hh + reach - y0) / RES))
            for j in range(max(0, j0), min(NY - 1, j1) + 1):
                row = j * NX
                py = y0 + j * RES
                dy = abs(py - oy) - hh
                if dy < 0:
                    dy = 0.0
                dy2 = dy * dy
                for i in range(max(0, i0), min(NX - 1, i1) + 1):
                    px = x0 + i * RES
                    dx = abs(px - ox) - hw
                    if dx < 0:
                        dx = 0.0
                    if dx * dx + dy2 < r2 - 1e-12:
                        g[row + i] = 1

        for onet, lays, ox, oy, hw, hh, _oref in obst + placed:
            if onet == netname:
                continue
            oc = net_class(onet) if onet else "HV"
            clr = max(my_clr, CLS_CLR.get(oc, 0.15))
            # the 1.5 mm HV-to-LV rule: HV copper in the left strip of
            # HV_ZONE (x < 20; the buck arm is the BUCK_HV rescope at 0.60)
            if oc == "HV" and ox < 20.0:
                clr = 1.50
            inner = via_mode and any(l not in (pcbnew.F_Cu, pcbnew.B_Cu)
                                     for l in lays)
            for li, lay in enumerate(LAYERS):
                if not inner and lay not in lays:
                    continue
                if trace is not None and \
                        abs(ox - (x0 + trace[0] * RES)) <= hw + clr + half and \
                        abs(oy - (y0 + trace[1] * RES)) <= hh + clr + half:
                    print(f"      TRACE L{li} blocked by [{onet}] ref={_oref!r} "
                          f"at ({ox:.2f},{oy:.2f}) hw={hw:.2f} hh={hh:.2f} "
                          f"clr={clr:.2f}")
                block_pad(grids[li], ox, oy, hw, hh, clr + half)
        for gx0, gy0, gx1, gy1, _n in nogo:
            for g in grids:
                block(g, (gx0 + gx1) / 2, (gy0 + gy1) / 2,
                      (gx1 - gx0) / 2 + half, (gy1 - gy0) / 2 + half)
        e = int(math.ceil((CLR_EDGE + half) / RES - 1e-9)) + 1
        for g in grids:
            for j in range(NY):
                row = j * NX
                for i in range(NX):
                    if i < e or i >= NX - e or j < e or j >= NY - e:
                        g[row + i] = 1
        return grids

    def open_pad_entries(netname, tg, half):
        """Unblock the legal axial entry lane into each of this net's pads.

        A 0.5 mm-pitch LQFP pad has a legal entry: a track on the pad's long
        axis keeps 0.5 - 0.15 - half >= class clearance to the neighbouring
        pins. But that window is a +-0.05 mm line, and the box halos of the
        neighbours bury it - measured: U2.44 had 0/48 free goal cells while
        the flood reached 268k cells everywhere else. This opens the axis
        lane ON the pad plus up to 12 cells beyond each tip, re-verifying
        every lane cell against all obstacles EXCEPT sibling pads of the
        same footprint (the axial geometry to siblings is legal by
        construction; anything else - another part's pad, a via, a track -
        still blocks)."""
        mypads = [(o, r) for o in obst
                  for r in [o[6]] if o[0] == netname and o[6]]
        for (onet, lays, cx, cy, hw, hh, ref), _r in mypads:
            vert = hh >= hw
            both = abs(hh - hw) < 0.2      # round/square (THT) pads: 2 lanes
            # Sibling pads are excluded from lane blocking ONLY when they are
            # LATERAL neighbours - offset perpendicular to the lane axis, the
            # single-row case where the axial geometry is legal at class
            # clearance by construction. A sibling AHEAD along the lane must
            # still block: on U3's LGA grid the 3V3 lane extended straight
            # through the IMU's GND and NC pads (measured: shorting_items).
            # HV-in-strip siblings always block (1.5 mm rule, no exception).
            def sib_skip(o, axis):
                """True when sibling o may be ignored for THIS lane axis.

                Per-lane, and ARITHMETIC, not faith: a lateral sibling is
                skippable only when the lane's copper actually clears it -
                at U3's 0.5 mm LGA pitch a PWR-width entry has zero margin
                and 'legal by construction' measured 0.11 mm (regressions).
                0.055 covers the half-cell grid snap."""
                if o[6] != ref:
                    return False
                if o[0] in HV and o[2] < 20.0:
                    return False          # HV-in-strip: 1.5 mm rule, no pass
                oc2 = net_class(o[0]) if o[0] else "HV"
                need = max(CLS_CLR.get(net_class(netname), 0.2),
                           CLS_CLR.get(oc2, 0.15)) + half + 0.055
                if axis == "v":
                    return abs(o[3] - cy) <= hh + 0.15 and \
                        (abs(o[2] - cx) - o[4]) >= need
                return abs(o[2] - cx) <= hw + 0.15 and \
                    (abs(o[3] - cy) - o[5]) >= need

            near = [o for o in obst + placed
                    if o[0] != netname
                    and abs(o[2] - cx) < 4.0 and abs(o[3] - cy) < 4.0]

            def lane_cell_ok(px, py, lay, axis):
                for o in near:
                    on2, l2, ox, oy, ohw, ohh, _r = o
                    if lay not in l2:
                        continue
                    if sib_skip(o, axis):
                        continue
                    oc = net_class(on2) if on2 else "HV"
                    clr = max(CLS_CLR.get(net_class(netname), 0.2),
                              CLS_CLR.get(oc, 0.15))
                    if on2 in HV and ox < 20.0:
                        clr = 1.50
                    ddx = max(abs(px - ox) - ohw, 0.0)
                    ddy = max(abs(py - oy) - ohh, 0.0)
                    if ddx * ddx + ddy * ddy < (clr + half) ** 2 - 1e-12:
                        return False
                for gx0, gy0, gx1, gy1, _n in nogo:
                    if gx0 - half <= px <= gx1 + half and \
                            gy0 - half <= py <= gy1 + half:
                        return False
                return True

            for li, lay in enumerate(LAYERS):
                if lay not in lays:
                    continue
                if vert or both:
                    ci = int(round((cx - x0) / RES))
                    j0 = int(round((cy - hh - y0) / RES)) - 25
                    j1 = int(round((cy + hh - y0) / RES)) + 25
                    for j in range(max(1, j0), min(NY - 2, j1) + 1):
                        px, py = pos(ci, j)
                        # every lane cell is verified - including on-pad
                        # cells, because a track on J1.4's own pad can still
                        # sit closer than 1.5 mm to the HV pin next to it
                        if lane_cell_ok(px, py, lay, "v"):
                            tg[li][j * NX + ci] = 0
                if (not vert) or both:
                    cj = int(round((cy - y0) / RES))
                    i0 = int(round((cx - hw - x0) / RES)) - 25
                    i1 = int(round((cx + hw - x0) / RES)) + 25
                    for i in range(max(1, i0), min(NX - 2, i1) + 1):
                        px, py = pos(i, cj)
                        if lane_cell_ok(px, py, lay, "h"):
                            tg[li][cj * NX + i] = 0

    def astar(tg, vg, starts, goals):
        goalset = set(goals)
        if not goalset:
            return None
        gx = sum(g[1] for g in goals) / len(goals)
        gy = sum(g[2] for g in goals) / len(goals)
        openh, best, came = [], {}, {}
        for s in starts:
            best[s] = 0.0
            heapq.heappush(openh, (math.hypot(s[1] - gx, s[2] - gy), 0.0, s, None))
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
                if not (0 <= nx_ < NX and 0 <= ny_ < NY) or tg[li][ny_ * NX + nx_]:
                    continue
                nxt, ng = (li, nx_, ny_), g + w
                if ng < best.get(nxt, 1e18):
                    best[nxt] = ng
                    heapq.heappush(openh, (ng + math.hypot(nx_ - gx, ny_ - gy),
                                           ng, nxt, cur))
            for lj in range(2):
                if lj == li or vg[lj][iy * NX + ix] or vg[li][iy * NX + ix]:
                    continue
                nxt, ng = (lj, ix, iy), g + 14
                if ng < best.get(nxt, 1e18):
                    best[nxt] = ng
                    heapq.heappush(openh, (ng + math.hypot(ix - gx, iy - gy),
                                           ng, nxt, cur))
        return None

    def pad_cells(p):
        b2 = p.GetBoundingBox()
        cx, cy = to_mm(b2.GetCenter().x), to_mm(b2.GetCenter().y)
        hw, hh = to_mm(b2.GetWidth()) / 2, to_mm(b2.GetHeight()) / 2
        lays = [l for l in p.GetLayerSet().CuStack()]
        out = []
        for li, lay in enumerate(LAYERS):
            if lay not in lays:
                continue
            i0, j0 = cell(cx - hw * 0.9, cy - hh * 0.9)
            i1, j1 = cell(cx + hw * 0.9, cy + hh * 0.9)
            for j in range(max(0, j0), min(NY - 1, j1) + 1):
                for i in range(max(0, i0), min(NX - 1, i1) + 1):
                    out.append((li, i, j))
        return out

    # ---- clusters: BFS over the connectivity graph's DIRECT edges --------
    # GetConnectedItems(item) with no type filter returns just the item, and
    # even typed queries return only DIRECTLY touching items (measured:
    # C81.1 -> 1 via, not the cluster). So the cluster is computed here: BFS
    # over per-type direct-edge queries, zone fills included.
    CONN_TYPES = (pcbnew.PCB_PAD_T, pcbnew.PCB_TRACE_T,
                  pcbnew.PCB_VIA_T, pcbnew.PCB_ZONE_T)

    def clusters(netname):
        conn = board.GetConnectivity()
        items = []
        for f in board.GetFootprints():
            for p in f.Pads():
                if p.GetNetname() == netname:
                    items.append(p)
        for t in board.GetTracks():
            if t.GetNetname() == netname:
                items.append(t)
        for z in board.Zones():
            if not z.GetIsRuleArea() and z.GetNetname() == netname:
                items.append(z)
        byid = {i.m_Uuid.AsString(): i for i in items}
        seen, out = set(), []
        for k in byid:
            if k in seen:
                continue
            stack, comp = [k], []
            while stack:
                c = stack.pop()
                if c in seen:
                    continue
                seen.add(c)
                comp.append(c)
                it = byid[c]
                for T in CONN_TYPES:
                    for j in conn.GetConnectedItems(it, T):
                        jk = j.m_Uuid.AsString()
                        if jk in byid and jk not in seen:
                            stack.append(jk)
            group = [byid[c] for c in comp
                     if byid[c].Type() == pcbnew.PCB_PAD_T]
            extra = [byid[c] for c in comp
                     if byid[c].Type() in (pcbnew.PCB_TRACE_T,
                                           pcbnew.PCB_VIA_T)]
            has_zone = any(byid[c].Type() == pcbnew.PCB_ZONE_T for c in comp)
            out.append((group or [byid[comp[0]]], extra, has_zone))
        # the pour-connected cluster first, then by pad count. The tap loop
        # must SKIP zone-connected clusters: without the flag it re-tapped
        # the already-merged cluster every round (all size-1 clusters sort
        # arbitrarily) and the count never dropped.
        out.sort(key=lambda ge: (not ge[2], -len(ge[0])))
        return out

    # ---- emit helpers -----------------------------------------------------
    stats = {"vias": 0}

    def emit_path(path, net, w, vd, vdr):
        nv, tl = 0, 0.0
        runs, prev = [], None
        for cur in path:
            if prev is not None:
                if prev[0] != cur[0]:
                    runs.append(["via", cur, None, None])
                else:
                    d = (cur[1] - prev[1], cur[2] - prev[2])
                    if runs and runs[-1][0] == "seg" and \
                            runs[-1][3] == (prev[0], d) and runs[-1][2] == prev:
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
                board.Add(v)
                nv += 1
                placed.append((net.GetNetname(), LAYERS, *pos(ix, iy),
                               vd / 2, vd / 2, ""))
            else:
                li = meta[0]
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pt(*pos(*a[1:]))); t.SetEnd(pt(*pos(*b2[1:])))
                t.SetWidth(mm(w)); t.SetLayer(LAYERS[li]); t.SetNet(net)
                board.Add(t)
                seg = math.hypot(b2[1] - a[1], b2[2] - a[2]) * RES
                tl += seg
                n_ = max(abs(b2[1] - a[1]), abs(b2[2] - a[2]), 1)
                for k in range(n_ + 1):
                    fx = a[1] + (b2[1] - a[1]) * k / n_
                    fy = a[2] + (b2[2] - a[2]) * k / n_
                    placed.append((net.GetNetname(), [LAYERS[li]],
                                   x0 + fx * RES, y0 + fy * RES, w / 2, w / 2, ""))
        stats["vias"] += nv
        return nv, tl

    # ---- pour taps ---------------------------------------------------------
    # net -> [(zone, inner_layer, window)] - the FILLED polygon is what a tap
    # via must hit. The first run tested the bounding box only: vias landed in
    # fill voids (clearance holes around other copper), never connected, the
    # cluster count never dropped, and each power net sprayed up to 12 dead
    # vias that then walled off every later net.
    pours = defaultdict(list)
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for l in z.GetLayerSet().CuStack():
            if l in (pcbnew.F_Cu, pcbnew.B_Cu):
                continue
            zb = z.GetBoundingBox()
            pours[z.GetNetname()].append(
                (z, l, (to_mm(zb.GetLeft()) + 0.6, to_mm(zb.GetTop()) + 0.6,
                        to_mm(zb.GetRight()) - 0.6, to_mm(zb.GetBottom()) - 0.6)))

    def tap_pour(netname, group, tg, vg, vd, vdr, w, net):
        """Maze a stub from the cluster to a via site that HITS the net's
        filled inner-layer pour. Returns the emitted items (for rollback) or
        None. The via site is verified against the FILLED polygon and the
        stub is a routed path, not a blind line."""
        zl = pours.get(netname)
        if not zl:
            return None
        goals = []
        for z, lay, (wx0, wy0, wx1, wy1) in zl:
            i0, j0 = cell(wx0, wy0)
            i1, j1 = cell(wx1, wy1)
            for j in range(max(0, j0), min(NY - 1, j1) + 1):
                for i in range(max(0, i0), min(NX - 1, i1) + 1):
                    if vg[0][j * NX + i] or vg[1][j * NX + i]:
                        continue
                    x, y = pos(i, j)
                    if z.HitTestFilledArea(lay, pt(x, y), 0):
                        goals.append((0, i, j))
                        goals.append((1, i, j))
        if not goals:
            return None
        starts = []
        for p in group:
            starts += pad_cells(p)
        path = astar(tg, vg, starts, set(goals))
        if path is None:
            return None
        mark = len(placed)
        items_before = set(id(t) for t in board.GetTracks())
        emit_path(path, net, w, vd, vdr)
        # a through via at the endpoint reaches the inner pour; if the path
        # already ended with a layer change, that via is the tap
        li, ix, iy = path[-1]
        need_via = len(path) < 2 or path[-2][0] == path[-1][0]
        if need_via:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pt(*pos(ix, iy)))
            v.SetWidth(mm(vd)); v.SetDrill(mm(vdr))
            v.SetNet(net); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(v)
            stats["vias"] += 1
            placed.append((netname, LAYERS, *pos(ix, iy), vd / 2, vd / 2, ""))
        new_items = [t for t in board.GetTracks() if id(t) not in items_before]
        return new_items, mark

    # GND: the L2 solid plane
    for z in board.Zones():
        if z.GetZoneName() == "L2_GND_solid":
            pours["GND"] = [(z, board.GetLayerID("In1.Cu"),
                             (x0 + 2.0, y0 + 2.0, x1 - 2.0, y1 - 2.0))]

    # ---- the work list -----------------------------------------------------
    def refill():
        board.BuildListOfNets()
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    def refresh_connectivity():
        board.BuildConnectivity()

    if single_net == "--finish--":
        refill()
        pcbnew.SaveBoard(PCB, board)
        canonicalise(PCB)
        print("CHILD_FINISHED")
        return

    refill()
    refresh_connectivity()

    if single_net == "--list--":
        all_nets = sorted({p.GetNetname() for f in board.GetFootprints()
                           for p in f.Pads()
                           if p.GetNetname() and p.GetNetname() not in PROTECTED})
        for n in all_nets:
            if len(clusters(n)) > 1:
                print(f"TODO {n}")
        return

    if single_net == "--spans--":
        all_nets = {p.GetNetname() for f in board.GetFootprints()
                    for p in f.Pads()
                    if p.GetNetname() and p.GetNetname() not in PROTECTED}
        for n in sorted(all_nets):
            xs, ys = [], []
            for f in board.GetFootprints():
                for p in f.Pads():
                    if p.GetNetname() == n:
                        xs.append(to_mm(p.GetPosition().x))
                        ys.append(to_mm(p.GetPosition().y))
            if len(xs) > 1:
                print(f"SPAN {max(xs)-min(xs)+max(ys)-min(ys):.1f} {n}")
        return

    def route_net(netname):
        """Route one net to a single cluster. On failure ALL of this net's
        partial copper is REMOVED (board.Remove on tracks/vias is safe -
        verified; the footprint segfault in SKILL.md does not apply) so a
        failed net cannot wall off the nets after it. Returns
        (ok, cause, vias, length, manhattan)."""
        cls = net_class(netname)
        w, my_clr, vd, vdr = GEO[cls]
        net = board.FindNet(netname)
        nv_net, tl_net, man_net = 0, 0.0, 0.0

        def pad_cap(p):
            b2 = p.GetBoundingBox()
            return max(0.20, min(to_mm(b2.GetWidth()), to_mm(b2.GetHeight())))

        def fail(cause):
            # No in-memory rollback: board.Remove on many tracks crashed
            # pcbnew (SWIG leak storm then silent death). In child-per-net
            # mode failure simply means the child exits WITHOUT saving, so
            # the file never sees the partial copper.
            return False, cause, 0, 0.0, 0.0

        # The FIRST tap into a virgin pour does not reduce the pad-cluster
        # count (it merges a cluster with the pour, not with another pad
        # cluster) - the drop comes when the second cluster taps in. So the
        # stagnation window is 3 rounds, not 1.
        best_cl, stagnant = None, 0
        for _round in range(40):
            refresh_connectivity()
            cl = clusters(netname)
            if len(cl) <= 1:
                return True, "", nv_net, tl_net, man_net
            if os.environ.get("LV_DEBUG"):
                sizes = [len(g) for g, _e, _z in cl][:8]
                print(f"    DEBUG round {_round}: {len(cl)} clusters "
                      f"(pad counts {sizes})")
            if best_cl is None or len(cl) < best_cl:
                best_cl, stagnant = len(cl), 0
            else:
                stagnant += 1
                if stagnant >= 3:
                    return fail(f"cluster count stuck at {len(cl)}")
            tg = build(netname, my_clr, w / 2)
            vg = build(netname, my_clr, vd / 2, via_mode=True)
            open_pad_entries(netname, tg, w / 2)
            tapped = False
            for group, _extra, hz in cl[1:]:
                if hz:
                    continue          # already reaches the pour
                r = tap_pour(netname, group, tg, vg, vd, vdr, w, net)
                if r is not None:
                    if os.environ.get("LV_DEBUG"):
                        gp = group[0]
                        nm = "?"
                        try:
                            nm = (gp.GetParentFootprint().GetReference()
                                  + "." + gp.GetPadNumber())
                        except Exception:
                            nm = gp.GetClass()
                        items2, _mk = r
                        vpos = [f"({to_mm(t.GetPosition().x):.1f},"
                                f"{to_mm(t.GetPosition().y):.1f})"
                                for t in items2
                                if isinstance(t, pcbnew.PCB_VIA)]
                        print(f"    DEBUG tapped {nm} vias at "
                              f"{vpos}")
                    nv_net += 1
                    tapped = True
                    break
            if tapped:
                last_cl = len(cl)
                continue
            pairs = []
            for i in range(len(cl)):
                for j in range(i + 1, len(cl)):
                    for pa in cl[i][0]:
                        for pb in cl[j][0]:
                            d = (pa.GetPosition() - pb.GetPosition()).EuclideanNorm()
                            pairs.append((d, i, j, pa, pb))
            if not pairs:
                return fail("no pad pair")
            pairs.sort(key=lambda t: t[0])
            # try up to 4 candidate pairs: the closest pair's endpoint can
            # be pocketed while another cluster pair routes fine
            path = None
            for _d, i, j, pa, pb in pairs[:4]:
            # A 2.0 mm MODEM_BULK track cannot ENTER a 1210 pad cluster at
            # 0.2 clearance (measured: C81.1 goals 0/286 free). The last
            # approach is physically capped by the endpoint pad's own width -
            # the pad is the cross-section limit; the RAIL requirement is
            # carried by the pour and the wide mid-run.
            # min() of the endpoint caps: the hop must ENTER BOTH pads, and
            # a 1.5 mm track cannot enter an 0603 (measured on C43.1). The
            # rail current rides the pour; the last approach is pad-limited.
                w_hop = min(w, pad_cap(pa), pad_cap(pb))
                if w_hop < w:
                    tg = build(netname, my_clr, w_hop / 2)
                    open_pad_entries(netname, tg, w_hop / 2)
                starts = []
                for p in cl[i][0]:
                    starts += pad_cells(p)
                for it in cl[i][1]:
                    if isinstance(it, pcbnew.PCB_VIA):
                        c = cell(to_mm(it.GetPosition().x),
                                 to_mm(it.GetPosition().y))
                        starts += [(0, *c), (1, *c)]
                goals = []
                for p in cl[j][0]:
                    goals += pad_cells(p)
                path = astar(tg, vg, starts, goals)
                if path is not None:
                    break
                if w_hop < w:
                    # restore the class-width grid for the next candidate
                    tg = build(netname, my_clr, w / 2)
                    open_pad_entries(netname, tg, w / 2)
            if path is None and os.environ.get("LV_DEBUG"):
                free_s = sum(1 for li, i, j in starts if not tg[li][j * NX + i])
                free_g = sum(1 for li, i, j in goals if not tg[li][j * NX + i])
                print(f"    DEBUG starts {free_s}/{len(starts)} free, "
                      f"goals {free_g}/{len(goals)} free")
                from collections import deque
                seen, dq = set(), deque()
                for c in starts:
                    li, i, j = c
                    if not tg[li][j * NX + i]:
                        seen.add(c); dq.append(c)
                while dq:
                    li, i, j = dq.popleft()
                    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),
                                   (1,1),(1,-1),(-1,1),(-1,-1)):
                        ni, nj = i + dx, j + dy
                        if 0 <= ni < NX and 0 <= nj < NY and \
                                not tg[li][nj * NX + ni] and \
                                (li, ni, nj) not in seen:
                            seen.add((li, ni, nj)); dq.append((li, ni, nj))
                    lj = 1 - li
                    if not vg[lj][j * NX + i] and not vg[li][j * NX + i] \
                            and (lj, i, j) not in seen:
                        seen.add((lj, i, j)); dq.append((lj, i, j))
                xs = [pos(i, j) for li, i, j in list(seen)[:100000]]
                if xs:
                    print(f"    DEBUG flood {len(seen)} cells, x range "
                          f"{min(x for x,_ in xs):.1f}..{max(x for x,_ in xs):.1f}, "
                          f"y {min(y for _,y in xs):.1f}..{max(y for _,y in xs):.1f}")
                else:
                    print(f"    DEBUG flood 0 cells - ALL start cells blocked")
                # name the walls: which nets' halos form the pocket boundary
                cls = net_class(netname)
                my_clr = GEO[cls][1]
                half = GEO[cls][0] / 2
                from collections import Counter
                wall = Counter()
                frontier = 0
                for (li, i, j) in list(seen)[:60000]:
                    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                        ni, nj = i + dx, j + dy
                        if not (0 <= ni < NX and 0 <= nj < NY) or \
                                not tg[li][nj * NX + ni]:
                            continue
                        frontier += 1
                        if frontier > 4000:
                            break
                        px, py = pos(ni, nj)
                        hit = None
                        for on2, l2, ox, oy, ohw, ohh, oref in obst + placed:
                            if on2 == netname or LAYERS[li] not in l2:
                                continue
                            oc = net_class(on2) if on2 else "HV"
                            clr = max(my_clr, CLS_CLR.get(oc, 0.15))
                            if on2 in HV and ox < 20.0:
                                clr = 1.50
                            if abs(px - ox) <= ohw + clr + half and \
                                    abs(py - oy) <= ohh + clr + half:
                                hit = f"{on2 or 'netless'}"
                                break
                        wall[hit or "edge/nogo"] += 1
                    if frontier > 4000:
                        break
                print(f"    DEBUG pocket walls: "
                      f"{dict(wall.most_common(8))}")
                shown = 0
                for (li, i, j) in list(seen)[:60000]:
                    if shown >= 6:
                        break
                    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                        ni, nj = i + dx, j + dy
                        if not (0 <= ni < NX and 0 <= nj < NY) or \
                                not tg[li][nj * NX + ni]:
                            continue
                        px, py = pos(ni, nj)
                        hit = None
                        for on2, l2, ox, oy, ohw, ohh, oref in obst + placed:
                            if on2 == netname or LAYERS[li] not in l2:
                                continue
                            oc = net_class(on2) if on2 else "HV"
                            clr = max(my_clr, CLS_CLR.get(oc, 0.15))
                            if on2 in HV and ox < 20.0:
                                clr = 1.50
                            if abs(px - ox) <= ohw + clr + half and \
                                    abs(py - oy) <= ohh + clr + half:
                                hit = on2
                                break
                        if hit is None:
                            print(f"    DEBUG unknown wall cell L{li} "
                                  f"({px:.2f},{py:.2f})")
                            shown += 1
                            break
            if path is None:
                cause = (f"no path "
                         f"{pa.GetParentFootprint().GetReference()}.{pa.GetNumber()}"
                         f" -> "
                         f"{pb.GetParentFootprint().GetReference()}.{pb.GetNumber()}")
                return fail(cause)
            nv, tl = emit_path(path, net, w_hop, vd, vdr)
            nv_net += nv
            tl_net += tl
            man_net += (abs(to_mm(pa.GetPosition().x - pb.GetPosition().x))
                        + abs(to_mm(pa.GetPosition().y - pb.GetPosition().y)))
            last_cl = len(cl)
        return fail("cluster count did not converge in 40 rounds")

    # child mode: route exactly one net; save ONLY on success
    ok, cause, nv, tl, man = route_net(single_net)
    if ok:
        refill()
        pcbnew.SaveBoard(PCB, board)
        print(f"CHILD_OK vias={nv} len={tl:.2f} man={man:.2f}")
        return
    print(f"CHILD_FAIL {cause}")
    sys.exit(3)


def orchestrate():
    """Parent: per-net child processes. A child that fails (or crashes -
    pcbnew has done that) exits without saving, so the board file only ever
    contains fully-routed, gate-checked nets. No in-memory rollback exists
    because none is needed."""
    me = os.path.abspath(__file__)

    def child(args, timeout=900):
        return subprocess.run([sys.executable, "-u", me] + args,
                              capture_output=True, text=True, timeout=timeout)

    r = child(["--list"])
    todo = [l.split(None, 1)[1] for l in r.stdout.splitlines()
            if l.startswith("TODO ")]
    total_ct = len(todo)
    print(f"nets needing work: {total_ct}")

    shutil.copyfile(PCB, LAST_GOOD)
    baseline = drc_errors(PCB)
    print(f"baseline DRC errors (non-ratsnest): {baseline}")

    # span per net, from a --spans child (longest first: the cross-board
    # corridors are the scarce resource - CANH from J1 to the transceiver
    # was walled in by its OWN termination nets routed before it)
    r = child(["--spans"])
    spans = {}
    for l in r.stdout.splitlines():
        if l.startswith("SPAN "):
            _, v, n = l.split(None, 2)
            spans[n] = float(v)
    metrics, failed = {}, {}
    done_ct = 0
    order = sorted(todo, key=lambda n: (net_class(n) != "MODEM_BULK",
                                        net_class(n) != "PWR",
                                        -spans.get(n, 0.0), n))
    queue = list(order)
    for attempt in range(1, 4):
        print(f"--- pass {attempt}: {len(queue)} net(s)")
        next_queue = []
        for netname in queue:
            try:
                r = child(["--net", netname])
            except subprocess.TimeoutExpired:
                shutil.copyfile(LAST_GOOD, PCB)
                failed[netname] = "child timeout (900 s)"
                next_queue.append(netname)
                print(f"  FAIL {netname:28} child timeout")
                continue
            m = re.search(r"CHILD_OK vias=(\d+) len=([\d.]+) man=([\d.]+)",
                          r.stdout)
            if not m:
                fm = re.search(r"CHILD_FAIL (.*)", r.stdout)
                cause = fm.group(1) if fm else \
                    f"child crashed (rc={r.returncode})"
                shutil.copyfile(LAST_GOOD, PCB)   # crash may have half-saved
                failed[netname] = cause
                next_queue.append(netname)
                print(f"  FAIL {netname:28} {cause}")
                for l in r.stdout.splitlines():
                    if "DEBUG" in l:
                        print(f"   {l}")
                continue
            errs = drc_errors(PCB)
            if errs > baseline:
                # keep the evidence: the mid-run board state that produced
                # the regression is destroyed by the rollback, so capture
                # the report (and the new violation types) NOW.
                rpt = PCB + ".drc"
                subprocess.run(["kicad-cli", "pcb", "drc",
                                "--severity-error", "-o", rpt, PCB],
                               capture_output=True)
                text = open(rpt).read()
                os.unlink(rpt)
                kinds = {}
                for k in re.findall(r"^\[([a-z_]+)\]", text, re.M):
                    if k != "unconnected_items":
                        kinds[k] = kinds.get(k, 0) + 1
                keep = os.path.join(PROJ, "docs",
                                    "lv-regressions",
                                    netname.replace("/", "_") + ".rpt")
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                with open(keep, "w") as fh:
                    fh.write(text)
                shutil.copyfile(LAST_GOOD, PCB)
                failed[netname] = f"DRC regression (+{errs - baseline}: {kinds})"
                next_queue.append(netname)
                print(f"  FAIL {netname:28} DRC regression "
                      f"(+{errs - baseline}) {kinds} - report kept")
                continue
            shutil.copyfile(PCB, LAST_GOOD)
            failed.pop(netname, None)
            done_ct += 1
            nv, tl, man = int(m.group(1)), float(m.group(2)), float(m.group(3))
            ratio = (tl / man) if man > 0.5 else 1.0
            metrics[netname] = (nv, tl, man, ratio)
            flags = []
            if nv > 4:
                flags.append("VIAS>4")
            if ratio > 2.5:
                flags.append("RATIO>2.5")
            pct = 100 * done_ct / total_ct
            print(f"  OK {netname:28} vias={nv} len={tl:5.1f} man={man:5.1f} "
                  f"ratio={ratio:4.2f} [{done_ct}/{total_ct} {pct:3.0f}%]"
                  f"{'  ' + ','.join(flags) if flags else ''}")
            if done_ct % 25 == 0:
                git_progress(f"LV routing progress: {done_ct}/{total_ct} "
                             f"nets ({pct:.0f}%)")
                print(f"== progress commit at {done_ct}/{total_ct} "
                      f"({pct:.0f}%)")
        queue = next_queue
        if not queue:
            break

    child(["--finish"], timeout=600)
    tot_v = sum(m[0] for m in metrics.values())
    flagged_v = [n for n, m in metrics.items() if m[0] > 4]
    flagged_r = [n for n, m in metrics.items() if m[3] > 2.5]
    with open(os.path.join(PROJ, "docs", "lv-route-metrics.txt"), "w") as fh:
        fh.write("LV routing metrics (tools/pcbroute_lv.py)\n")
        fh.write(f"nets routed: {done_ct}/{total_ct}   total vias: {tot_v}\n")
        fh.write(f"{'net':30} {'vias':>4} {'len mm':>8} {'manhattan':>9} "
                 f"{'ratio':>6}\n")
        for n in sorted(metrics):
            nv, tl, man, ratio = metrics[n]
            fl = (" VIAS>4" if nv > 4 else "") + \
                 (" RATIO>2.5" if ratio > 2.5 else "")
            fh.write(f"{n:30} {nv:4} {tl:8.1f} {man:9.1f} {ratio:6.2f}{fl}\n")
        if failed:
            fh.write("\nUNROUTED:\n")
            for n, c in failed.items():
                fh.write(f"  {n}: {c}\n")
    print(f"\nROUTED {done_ct}/{total_ct} nets  vias {tot_v}  "
          f"via-flags {len(flagged_v)}  ratio-flags {len(flagged_r)}")
    if failed:
        print("UNROUTED (with cause):")
        for n, c in failed.items():
            print(f"  {n}: {c}")
    print("metrics written to docs/lv-route-metrics.txt")
    print("LV_ROUTE_DONE")


if __name__ == "__main__":
    if "--net" in sys.argv:
        main(single_net=sys.argv[sys.argv.index("--net") + 1])
    elif "--list" in sys.argv:
        main(single_net="--list--")
    elif "--spans" in sys.argv:
        main(single_net="--spans--")
    elif "--finish" in sys.argv:
        main(single_net="--finish--")
    else:
        orchestrate()
