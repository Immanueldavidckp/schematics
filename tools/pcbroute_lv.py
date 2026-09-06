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
    "Default":    (0.20, 0.15, 0.50, 0.30),
    "PWR":        (0.50, 0.20, 0.80, 0.40),
    "MODEM_BULK": (2.00, 0.20, 0.80, 0.40),
    "GND":        (0.50, 0.15, 0.50, 0.30),
}
CLS_CLR = {"HV": 0.60, "MV": 0.60, "RF": 0.30, "GND": 0.15,
           "PWR": 0.20, "MODEM_BULK": 0.20, "Default": 0.15}


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


def main():
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
                         to_mm(b2.GetWidth()) / 2, to_mm(b2.GetHeight()) / 2))
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            obst.append((t.GetNetname(), LAYERS,
                         to_mm(t.GetPosition().x), to_mm(t.GetPosition().y),
                         to_mm(t.GetWidth()) / 2, to_mm(t.GetWidth()) / 2))
        else:
            a, b2 = t.GetStart(), t.GetEnd()
            w = to_mm(t.GetWidth()) / 2
            ax, ay, bx, by = to_mm(a.x), to_mm(a.y), to_mm(b2.x), to_mm(b2.y)
            n = max(1, int(math.hypot(bx - ax, by - ay) / RES))
            for i in range(n + 1):
                tt = i / n
                obst.append((t.GetNetname(), [t.GetLayer()],
                             ax + (bx - ax) * tt, ay + (by - ay) * tt, w, w))
    print(f"obstacles: {len(obst)}")
    placed = []

    def build(netname, my_clr, half):
        grids = [bytearray(NX * NY) for _ in LAYERS]

        def block(g, ox, oy, rx, ry):
            i0 = int(math.floor((ox - rx - x0) / RES))
            j0 = int(math.floor((oy - ry - y0) / RES))
            i1 = int(math.ceil((ox + rx - x0) / RES))
            j1 = int(math.ceil((oy + ry - y0) / RES))
            for j in range(max(0, j0), min(NY - 1, j1) + 1):
                row = j * NX
                for i in range(max(0, i0), min(NX - 1, i1) + 1):
                    g[row + i] = 1

        for onet, lays, ox, oy, hw, hh in obst + placed:
            if onet == netname:
                continue
            oc = net_class(onet) if onet else "HV"
            clr = max(my_clr, CLS_CLR.get(oc, 0.15))
            # the 1.5 mm HV-to-LV rule: HV copper in the left strip of
            # HV_ZONE (x < 20; the buck arm is the BUCK_HV rescope at 0.60)
            if oc == "HV" and ox < 20.0:
                clr = 1.50
            for li, lay in enumerate(LAYERS):
                if lay not in lays:
                    continue
                block(grids[li], ox, oy, hw + clr + half, hh + clr + half)
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

    # ---- clusters via KiCad connectivity (zone-fill aware) ---------------
    def clusters(netname):
        conn = board.GetConnectivity()
        pads = [p for f in board.GetFootprints() for p in f.Pads()
                if p.GetNetname() == netname]
        seen, out = set(), []
        for p in pads:
            pid = p.m_Uuid.AsString()
            if pid in seen:
                continue
            items = conn.GetConnectedItems(p)
            group, extra = [], []
            ids = set()
            for it in items:
                ids.add(it.m_Uuid.AsString())
                if it.Type() == pcbnew.PCB_PAD_T and \
                        it.GetNetname() == netname:
                    group.append(pcbnew.Cast_to_PAD(it)
                                 if hasattr(pcbnew, "Cast_to_PAD") else it)
                elif it.Type() in (pcbnew.PCB_TRACE_T, pcbnew.PCB_VIA_T):
                    extra.append(it)
            if pid not in ids:
                group.append(p)
                ids.add(pid)
            seen |= ids
            out.append((group or [p], extra))
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
                               vd / 2, vd / 2))
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
                                   x0 + fx * RES, y0 + fy * RES, w / 2, w / 2))
        stats["vias"] += nv
        return nv, tl

    # ---- pour taps ---------------------------------------------------------
    pours = defaultdict(list)      # net -> [(x0,y0,x1,y1)] usable via windows
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        lays = list(z.GetLayerSet().CuStack())
        if pcbnew.F_Cu in lays and pcbnew.B_Cu in lays:
            pass
        zb = z.GetBoundingBox()
        # inner layers only: a through via reaches them anywhere inside
        if any(l not in (pcbnew.F_Cu, pcbnew.B_Cu) for l in lays):
            pours[z.GetNetname()].append(
                (to_mm(zb.GetLeft()) + 1.0, to_mm(zb.GetTop()) + 1.0,
                 to_mm(zb.GetRight()) - 1.0, to_mm(zb.GetBottom()) - 1.0))

    def tap_pour(netname, group, vg, vd, vdr, w):
        """via + stub from one pad of the cluster into the net's inner pour."""
        wins = pours.get(netname)
        if not wins:
            return None
        net = board.FindNet(netname)
        for p in group:
            bb2 = p.GetBoundingBox()
            px, py = to_mm(bb2.GetCenter().x), to_mm(bb2.GetCenter().y)
            if not any(wx0 <= px <= wx1 and wy0 <= py <= wy1
                       for wx0, wy0, wx1, wy1 in wins):
                continue
            li = 0 if pcbnew.F_Cu in p.GetLayerSet().CuStack() else 1
            ci, cj = cell(px, py)
            for r in range(2, 26):          # 0.2 .. 2.5 mm ring search
                found = None
                for di in range(-r, r + 1):
                    for dj in (-r, r):
                        for ii, jj in ((ci + di, cj + dj), (ci + dj, cj + di)):
                            if 0 <= ii < NX and 0 <= jj < NY and \
                                    not vg[0][jj * NX + ii] and \
                                    not vg[1][jj * NX + ii]:
                                vx, vy = pos(ii, jj)
                                if any(wx0 <= vx <= wx1 and wy0 <= vy <= wy1
                                       for wx0, wy0, wx1, wy1 in wins):
                                    found = (ii, jj)
                                    break
                        if found:
                            break
                    if found:
                        break
                if found:
                    ii, jj = found
                    vx, vy = pos(ii, jj)
                    stub_w = min(w, 2 * min(to_mm(bb2.GetWidth()),
                                            to_mm(bb2.GetHeight())) / 2)
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(pt(px, py)); t.SetEnd(pt(vx, vy))
                    t.SetWidth(mm(max(0.20, stub_w)))
                    t.SetLayer(LAYERS[li]); t.SetNet(net)
                    board.Add(t)
                    v = pcbnew.PCB_VIA(board)
                    v.SetPosition(pt(vx, vy))
                    v.SetWidth(mm(vd)); v.SetDrill(mm(vdr))
                    v.SetNet(net); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                    board.Add(v)
                    stats["vias"] += 1
                    placed.append((netname, LAYERS, vx, vy, vd / 2, vd / 2))
                    placed.append((netname, [LAYERS[li]], px, py,
                                   max(0.20, stub_w) / 2, max(0.20, stub_w) / 2))
                    placed.append((netname, [LAYERS[li]], vx, vy,
                                   max(0.20, stub_w) / 2, max(0.20, stub_w) / 2))
                    return (vx, vy)
        return None

    # GND: the L2 plane is full-board
    pours["GND"] = [(x0 + 2.0, y0 + 2.0, x1 - 2.0, y1 - 2.0)]

    # ---- the work list -----------------------------------------------------
    def refill():
        board.BuildListOfNets()
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    def refresh_connectivity():
        board.BuildConnectivity()

    refill()
    refresh_connectivity()

    all_nets = sorted({p.GetNetname() for f in board.GetFootprints()
                       for p in f.Pads()
                       if p.GetNetname() and p.GetNetname() not in PROTECTED})
    todo = []
    for n in all_nets:
        cl = clusters(n)
        if len(cl) > 1:
            todo.append(n)
    print(f"nets needing work: {len(todo)}")

    shutil.copyfile(PCB, LAST_GOOD)
    baseline = drc_errors(PCB)
    print(f"baseline DRC errors (non-ratsnest): {baseline}")

    metrics = {}
    failed = {}
    done_ct = 0
    total_ct = len(todo)

    # Nets that caused a DRC regression in a previous invocation. The gate
    # rolls the FILE back and re-execs this script; the skip file is what
    # stops a pathological net from looping forever.
    SKIP_FILE = os.path.join(PROJ, ".lv-route-skip")
    skip = set()
    if os.path.exists(SKIP_FILE):
        skip = {l.strip() for l in open(SKIP_FILE) if l.strip()}
        print(f"skipping {len(skip)} net(s) from a previous DRC regression: "
              f"{', '.join(sorted(skip))}")

    def route_net(netname):
        """Route one net to a single cluster. Partial copper that meets the
        grid rules is legal and is KEPT on failure - only the connection is
        reported missing. Returns (ok, cause, vias, length, manhattan)."""
        cls = net_class(netname)
        w, my_clr, vd, vdr = GEO[cls]
        net = board.FindNet(netname)
        nv_net, tl_net, man_net = 0, 0.0, 0.0
        for _round in range(12):
            refresh_connectivity()
            cl = clusters(netname)
            if len(cl) <= 1:
                return True, "", nv_net, tl_net, man_net
            tg = build(netname, my_clr, w / 2)
            vg = build(netname, my_clr, vd / 2)
            tapped = False
            for group, _extra in cl[1:]:
                if tap_pour(netname, group, vg, vd, vdr, w):
                    nv_net += 1
                    tapped = True
                    break
            if tapped:
                continue
            bestpair, bestd = None, 1e18
            for i in range(len(cl)):
                for j in range(i + 1, len(cl)):
                    for pa in cl[i][0]:
                        for pb in cl[j][0]:
                            d = (pa.GetPosition() - pb.GetPosition()).EuclideanNorm()
                            if d < bestd:
                                bestd, bestpair = d, (i, j, pa, pb)
            if bestpair is None:
                return False, "no pad pair", nv_net, tl_net, man_net
            i, j, pa, pb = bestpair
            starts = []
            for p in cl[i][0]:
                starts += pad_cells(p)
            for it in cl[i][1]:
                if isinstance(it, pcbnew.PCB_VIA):
                    c = cell(to_mm(it.GetPosition().x), to_mm(it.GetPosition().y))
                    starts += [(0, *c), (1, *c)]
            goals = []
            for p in cl[j][0]:
                goals += pad_cells(p)
            path = astar(tg, vg, starts, goals)
            if path is None:
                cause = (f"no path "
                         f"{pa.GetParentFootprint().GetReference()}.{pa.GetNumber()}"
                         f" -> "
                         f"{pb.GetParentFootprint().GetReference()}.{pb.GetNumber()}")
                return False, cause, nv_net, tl_net, man_net
            nv, tl = emit_path(path, net, w, vd, vdr)
            nv_net += nv
            tl_net += tl
            man_net += (abs(to_mm(pa.GetPosition().x - pb.GetPosition().x))
                        + abs(to_mm(pa.GetPosition().y - pb.GetPosition().y)))
        return False, "cluster count did not converge in 12 rounds", \
            nv_net, tl_net, man_net

    # MODEM_BULK and PWR first (widest copper needs room), then by name.
    order = [n for n in sorted(
                todo, key=lambda n: (net_class(n) != "MODEM_BULK",
                                     net_class(n) != "PWR", n))
             if n not in skip]
    queue = list(order)
    for attempt in range(1, 4):
        print(f"--- pass {attempt}: {len(queue)} net(s)")
        next_queue = []
        for netname in queue:
            ok, cause, nv, tl, man = route_net(netname)
            if not ok:
                failed[netname] = cause
                next_queue.append(netname)
                print(f"  FAIL {netname:28} {cause}")
                continue
            failed.pop(netname, None)
            refill()
            pcbnew.SaveBoard(PCB, board)
            errs = drc_errors(PCB)
            if errs > baseline:
                # gate 1: the routed net broke a rule DRC can see but the
                # grids could not (should not happen; belt-and-braces).
                print(f"  DRC REGRESSION on {netname}: {errs} > {baseline}. "
                      f"Rolling the file back and re-execing with the net "
                      f"skipped.")
                shutil.copyfile(LAST_GOOD, PCB)
                with open(SKIP_FILE, "a") as fh:
                    fh.write(netname + "\n")
                os.execv(sys.executable, [sys.executable,
                                          os.path.abspath(__file__)])
            shutil.copyfile(PCB, LAST_GOOD)
            done_ct += 1
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
                git_progress(f"LV routing progress: {done_ct}/{total_ct} nets "
                             f"({pct:.0f}%)")
                print(f"== progress commit at {done_ct}/{total_ct} ({pct:.0f}%)")
        queue = next_queue
        if not queue:
            break

    refill()
    pcbnew.SaveBoard(PCB, board)
    canonicalise(PCB)
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
        if skip:
            fh.write("\nSKIPPED (previous DRC regression):\n")
            for n in sorted(skip):
                fh.write(f"  {n}\n")
    print(f"\nROUTED {done_ct}/{total_ct} nets  vias {tot_v}  "
          f"via-flags {len(flagged_v)}  ratio-flags {len(flagged_r)}")
    if failed:
        print("UNROUTED (with cause):")
        for n, c in failed.items():
            print(f"  {n}: {c}")
    print("metrics written to docs/lv-route-metrics.txt")
    print("LV_ROUTE_DONE")


if __name__ == "__main__":
    main()
