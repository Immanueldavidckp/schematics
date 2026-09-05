#!/usr/bin/env python3
"""Milestone 4 stage 3: hand-route the critical nets.

Option 1, agreed sequence:
  1. RF CPWG (W 0.40 / G 0.30) with a via fence
  2. HV front end
  3. VBAT_MODEM (>= 2 mm)
  4. U5 switching hot loop
Thermal vias under U1 and U5's exposed pad are already placed by pcbplace.py.
Everything else is left for FreeRouting.

These nets are hand-routed because their geometry IS the design: the RF runs
are impedance-controlled, the HV nets carry up to 100 V, VBAT_MODEM carries the
modem's 2 A transmit burst, and the buck loop's enclosed area sets its EMI.
An autorouter has no model for any of that.

Run after tools/pcbplace.py (tools/build.py does this in order).
"""
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbgen import PROJ, PCB, mm, pt, canonicalise         # noqa: E402

# pcbgen.mm is FromMM (mm -> nm, for WRITING geometry). Reading a position back
# needs the inverse. Conflating the two overflows VECTOR2I.
to_mm = pcbnew.ToMM

# 50 ohm CPWG on JLC7628 L1-L2 (design log): W = 0.40, G = 0.30
RF_W = 0.40
RF_GAP = 0.30
FENCE_STANDOFF = 2 * RF_W      # Quectel V1.2 4.3: vias >= 2 x W from the trace
FENCE_PITCH = 2.0
FENCE_VIA_D, FENCE_VIA_DRILL = 0.50, 0.30

VBAT_W = 2.0                   # handoff section 4
HV_W = 0.75                    # VIN chain: 1 A at up to 100 V
LOOP_W = 1.0                   # buck hot loop


def fp(board, ref):
    for f in board.GetFootprints():
        if f.GetReference() == ref:
            return f
    return None


def pad(board, ref, num):
    f = fp(board, ref)
    if f is None:
        return None
    for p in f.Pads():
        if p.GetNumber() == num:
            return p
    return None


def xy(p):
    return (to_mm(p.GetPosition().x), to_mm(p.GetPosition().y))


def track(board, a, b, width, net, layer=None):
    if a == b:
        return None
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pt(*a))
    t.SetEnd(pt(*b))
    t.SetWidth(mm(width))
    t.SetLayer(layer if layer is not None else pcbnew.F_Cu)
    if net is not None:
        t.SetNet(net)
    board.Add(t)
    return t


def route(board, pts, width, net, layer=None):
    """Polyline with 135-degree corners.

    Quectel V1.2 section 4.3: "all the right-angle traces should be changed to
    curved ones. The recommended trace angle is 135 degrees." Every corner is
    therefore mitred rather than square.
    """
    out = []
    cur = pts[0]
    for i in range(1, len(pts)):
        nxt = pts[i]
        if i < len(pts) - 1:
            after = pts[i + 1]
            m1 = _mitre(cur, nxt, 0.6)
            m2 = _mitre(after, nxt, 0.6)
            out.append(track(board, cur, m1, width, net, layer))
            out.append(track(board, m1, m2, width, net, layer))
            cur = m2
        else:
            out.append(track(board, cur, nxt, width, net, layer))
    return [t for t in out if t]


def _mitre(frm, corner, d):
    dx, dy = corner[0] - frm[0], corner[1] - frm[1]
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return corner
    d = min(d, L * 0.45)
    return (corner[0] - dx / L * d, corner[1] - dy / L * d)


def via(board, p, net, dia=FENCE_VIA_D, drill=FENCE_VIA_DRILL):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(*p))
    v.SetWidth(mm(dia))
    v.SetDrill(mm(drill))
    v.SetNet(net)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)
    return v


def _clear(board, vx, vy, gnd, keep=0.45):
    """True if a via at (vx, vy) would not foul another net's pad or via.

    The first fence pass placed vias blindly and produced 23 shorts, 33 mask
    bridges and 10 hole-clearance errors.
    """
    v = pcbnew.VECTOR2I(mm(vx), mm(vy))
    r = mm(FENCE_VIA_D / 2 + keep)
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == "GND":
                continue
            bb = p.GetBoundingBox()
            bb.Inflate(r)
            if bb.Contains(v):
                return False
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            d = (t.GetPosition() - v).EuclideanNorm()
            if d < mm(0.9):
                return False
    return True


def fence(board, pts, gnd, edge_x=None):
    """GND vias either side of an RF run.

    Standoff is measured from the trace CENTRELINE: half the trace, plus the
    coplanar gap, plus Quectel's 2 x W, plus the via radius.
    """
    off = RF_W / 2 + RF_GAP + FENCE_STANDOFF + FENCE_VIA_D / 2
    made = 0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg < FENCE_PITCH:
            continue
        ux, uy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
        nx, ny = -uy, ux
        n = int(seg // FENCE_PITCH)
        for k in range(1, n + 1):
            t = k * FENCE_PITCH
            cx, cy = a[0] + ux * t, a[1] + uy * t
            for sgn in (+1, -1):
                vx, vy = cx + nx * off * sgn, cy + ny * off * sgn
                if edge_x is not None and vx > edge_x:
                    continue          # would fall off the board edge
                if vx < 1.0 or vy < 1.0:
                    continue
                if not _clear(board, vx, vy, gnd):
                    continue          # would sit on another net's copper
                via(board, (vx, vy), gnd)
                made += 1
    return made


def main():
    board = pcbnew.LoadBoard(PCB)
    gnd = board.FindNet("GND")
    edge_x = to_mm(board.GetBoardEdgesBoundingBox().GetRight()) - 0.8
    n_tracks = n_vias = 0

    # ---- 1. RF ---------------------------------------------------------
    # Out of the ANT pad into the corridor, along it, then in to the target.
    # Corridor x is set so the trace clears U1's keepout edge and still leaves
    # room for the fence on both sides.
    CORR = 79.8   # corridor centreline: (77.80 + 81.75) / 2
    rf_runs = [
        ("ANT_MAIN_M",  [("U1", "49"), ("R71", "1")]),
        ("ANT_MAIN_C",  [("R71", "2"), ("AF1", "3")]),
        ("ANT_GNSS_M",  [("U1", "47"), ("R72", "1")]),
        ("ANT_GNSS_C",  [("R72", "2"), ("C84", "1")]),
        # one run C84 -> AF2; L4.1 sits ON it (L4 is horizontal so pad 2 is
        # clear of the line). Routing "through" L4 shorted its pad 2.
        ("ANT_GNSS_F",  [("C84", "2"), ("AF2", "3")]),
    ]
    for name, hops in rf_runs:
        (r0, p0), (r1, p1) = hops
        pa, pb = pad(board, r0, p0), pad(board, r1, p1)
        if pa is None or pb is None:
            print(f"  RF {name}: missing pad"); continue
        a, b = xy(pa), xy(pb)
        net = pa.GetNet()
        if abs(a[0] - b[0]) < 0.05 or abs(a[1] - b[1]) < 0.05:
            pts = [a, b]                       # already straight
        elif r1.startswith("AF"):
            # Approach the U.FL signal pad along a line just OUTBOARD of its
            # own centre. The connector's GND pads reach x = body+1.10, and at
            # the pad-3 centre the gap was 0.23 mm against the RF netclass's
            # 0.30 mm - so shift out by 0.15 mm, still well inside pad 3.
            appr = 3.0 if b[1] > a[1] else -3.0
            ax = b[0] + 0.28   # +0.22 still left 0.298 vs the 0.30 RF clearance
            pts = [a, (CORR, a[1]), (CORR, b[1] - appr), (ax, b[1] - appr), b]
        else:
            # Turn INBOARD of the corridor before running to the target pad.
            # Jogging at the source y ran the trace along the far pad of the
            # same part (R71/R72 pads are ~1.0 mm apart in y).
            pts = [a, (78.6, a[1]), (78.6, b[1]), b]
        route(board, pts, RF_W, net)
        n_tracks += len(pts) - 1
        n_vias += fence(board, pts, gnd, edge_x)
    print(f"RF: {len(rf_runs)} runs at W={RF_W} G={RF_GAP}, fence standoff "
          f"{FENCE_STANDOFF:.2f} mm, pitch {FENCE_PITCH} mm")

    # ---- 2. HV front end -> LEFT TO FREEROUTING, deliberately -----------
    # The first attempt drew naive L-shapes between the HV pads and ploughed
    # straight through D2, U5 and J1 - 13 shorts. That is not routing, it is
    # drawing lines.
    #
    # The distinction that matters: for the RF runs the PATH is the design
    # (impedance, fence geometry, length), so it must be placed by hand. For
    # the HV chain the constraints are WIDTH and CLEARANCE, and both are
    # already expressed in the HV netclass (0.50 mm track, 0.60 mm clearance)
    # plus the 1.5 mm HV-to-signal rule in the .kicad_dru. FreeRouting reads
    # those from the DSN and will honour them while actually avoiding
    # obstacles, which the hand pass did not.
    print("HV front end: left to FreeRouting under the HV netclass "
          "(0.50 mm / 0.60 mm) + the 1.5 mm HV-to-signal rule")

    # ---- 3 & 4. VBAT_MODEM and the U5 hot loop -> FreeRouting ----------
    # Both were hand-routed first and both caused shorts, because drawing a
    # straight line between two pads is not routing. More importantly, neither
    # actually needs hand-placed copper:
    #
    #   VBAT_MODEM - the requirement is WIDTH (>= 2 mm), and that is the
    #     MODEM_BULK netclass track width, which FreeRouting honours. The caps
    #     are already anchored 1.95 mm / 0.00 mm from U1 pads 57-60 (check 4),
    #     so the loop is short regardless of how the copper is drawn.
    #   U5 hot loop - the enclosed AREA is set by PLACEMENT, and it already
    #     measures 44.85 mm2 (check 6). Which order the copper is drawn in does
    #     not change that.
    #
    # Hand-routing is reserved for the RF runs, where the path itself is the
    # design: impedance, fence geometry and length.
    print("VBAT_MODEM + U5 hot loop: left to FreeRouting under their "
          "netclasses (MODEM_BULK 2.00 mm, PWR 0.50 mm)")

    # Lock everything placed by hand. This is part of the reproducible flow,
    # not a one-off: the lock is what makes KiCad export these as Specctra
    # (type fix) rather than (type route), which is what stops FreeRouting
    # ripping up the RF CPWG, its fence and the U1/U5 stitching vias. Locking
    # outside the generator would also break byte-identical regeneration.
    nlock = 0
    for t in board.GetTracks():
        t.SetLocked(True)
        nlock += 1
    print(f"locked {nlock} hand-routed items (exported as Specctra 'type fix')")

    board.BuildListOfNets()
    try:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    except Exception as e:
        print(f"  zone refill skipped: {e}")
    pcbnew.SaveBoard(PCB, board)
    # Same reason as pcbgen/pcbplace: pcbnew mints random KIIDs and writes
    # tracks from an unordered container, so without this the board is not
    # byte-stable and "rebuild, then git diff must be empty" stops working.
    canonicalise(PCB)
    print(f"\ntracks added: {n_tracks}   fence/tie vias added: {n_vias}")


if __name__ == "__main__":
    main()
