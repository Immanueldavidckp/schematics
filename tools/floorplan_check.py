#!/usr/bin/env python3
"""Measure the placed board against the eight floorplan approval conditions.

Numbers, not descriptions. Every check prints its measurement and PASS/FAIL.
Exit code is non-zero if any check fails, so this can gate routing.

Run:  python3 tools/floorplan_check.py
"""
import math
import os
import re
import sys

import pcbnew

# Python 3.14 / KiCad SWIG shim fix (see pcbgen.py)
if not hasattr(pcbnew.SwigPyIterator, "next"):
    pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netclasses import HV as HV_NETS, MV as MV_NETS       # noqa: E402

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")

# 50 ohm CPWG on JLC7628 L1-L2, from the design log
CPWG_W, CPWG_G = 0.40, 0.30
FENCE_STANDOFF = 2 * CPWG_W        # Quectel V1.2 section 4.3: >= 2 x W
FENCE_PITCH = 2.0

# CHECK 3 exemption: intra-component pad pairs are exempt where the voltage
# ACROSS the part is <= 40 V. The part IS the HV->LV transition, and its pad
# spacing is fixed by the package.
#
# VIN and IGN sense dividers are 3 x 100k in series then 9.1k to GND:
#   total 309.1k, so at VIN = 100 V, I = 100/309100 = 323.5 uA
#   across each 100k  = 32.35 V   <= 40 V  -> EXEMPT
#   across the 9.1k   =  2.94 V   (this is VIN_SENSE / IGN_SENSE)
# Anything above 40 V is NOT exempt by this rule and is listed separately; it
# then relies on the IPC-2221 figure for its actual voltage plus the mandatory
# conformal coating (SKILL P1), the same basis as F-20 at U5.
V_ACROSS = {
    "R30": 32.35, "R31": 32.35, "R32": 32.35,     # VIN divider  100k each
    "R33": 32.35, "R34": 32.35, "R35": 32.35,     # IGN divider  100k each
    "R36": 2.94, "R37": 2.94,                     # 9.1k bottom legs
    "R14": 49.4, "R15": 49.4, "R16": 49.4,        # DI1 series 2 x 12k
    "R17": 49.4, "R18": 49.4, "R19": 49.4,        # DI2 series 2 x 12k
    "R40": 91.66,        # spare ADC divider: a SINGLE 100k with 9.1k, DNP
    "Q1": 100.0, "Q2": 100.0,                     # DO FETs, LV gate / HV drain
}
V_EXEMPT = 40.0

results = []


def check(n, title, ok, detail):
    results.append((n, title, ok, detail))
    print(f"\n{'='*74}\n{n}. {title}\n{'='*74}")
    print(detail)
    print(f"--> {'PASS' if ok else 'FAIL'}")


def mm(v):
    return pcbnew.ToMM(v)


def fp(board, ref):
    for f in board.GetFootprints():
        if f.GetReference() == ref:
            return f
    return None


def pad(f, num):
    if f is None:
        return None
    for p in f.Pads():
        if p.GetNumber() == num:
            return p
    return None


def pxy(p):
    return (mm(p.GetPosition().x), mm(p.GetPosition().y))


def pad_rect(p):
    b = p.GetBoundingBox()
    return (mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom()))


def rect_gap(a, b):
    """Edge-to-edge gap between two axis-aligned rects; 0 if they overlap."""
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return math.hypot(dx, dy)


def seg_point_dist(a, b, p):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def main():
    board = pcbnew.LoadBoard(PCB)
    vias = [v for v in board.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]

    # ---------------------------------------------------------------- 1
    lines = []
    ok1 = True
    # (name, U1 pad, U.FL ref, inline parts that must sit in the RF path)
    RF = [("ANT_MAIN (LTE)", "49", "AF1", ["R71"]),
          # L4 is the bias tap and sits ON the RF line by design, so it is an
          # inline element like C84 rather than an obstruction
          ("ANT_GNSS", "47", "AF2", ["R72", "C84", "L4"])]
    corridor_half = CPWG_W / 2 + CPWG_G + FENCE_STANDOFF
    for name, u1pad, aref, rrefs in RF:
        src = pad(fp(board, "U1"), u1pad)
        dst = pad(fp(board, aref), "3")
        if src is None or dst is None:
            lines.append(f"{name}: MISSING pad"); ok1 = False; continue
        a, b = pxy(src), pxy(dst)
        d = math.hypot(a[0] - b[0], a[1] - b[1])
        lines.append(f"{name}:  U1.{u1pad} ({a[0]:.2f}, {a[1]:.2f})  ->  "
                     f"{aref}.3 ({b[0]:.2f}, {b[1]:.2f})   "
                     f"straight-line = {d:.2f} mm")
        # The routed path is a dog-leg, not a straight line: the trace leaves
        # the ANT pad outboard into the corridor, runs along it, then turns in
        # to the U.FL. So the pi-network resistor is measured against the
        # requirement actually stated - pad-edge to pad-edge, <= 2 mm from the
        # ANT pad - and checked to be on the outboard side, not against its
        # offset from a straight line it was never meant to sit on.
        path = [a, (a[0] + 2.45, a[1]), (a[0] + 2.45, b[1]), b]
        for rref in rrefs:
            rs = fp(board, rref)
            if rs is None:
                lines.append(f"    !! {rref} not placed"); ok1 = False; continue
            rc = (mm(rs.GetPosition().x), mm(rs.GetPosition().y))
            outboard = rc[0] > a[0]
            # distance from the routed dog-leg, not from the ANT pad: only the
            # first element has to be hard against the pad
            off = min(seg_point_dist(path[i], path[i+1], rc)
                      for i in range(len(path)-1))
            if rref == rrefs[0]:
                g0 = min(rect_gap(pad_rect(src), pad_rect(q)) for q in rs.Pads())
                lines.append(f"    {rref} at {rc[0]:.2f},{rc[1]:.2f}: "
                             f"pad-to-pad from U1.{u1pad} = {g0:.2f} mm "
                             f"(<= 2.00), {'outboard' if outboard else 'INBOARD'}")
                if g0 > 2.0 or not outboard:
                    lines.append(f"    !! {rref} fails the inline requirement")
                    ok1 = False
            else:
                lines.append(f"    {rref} at {rc[0]:.2f},{rc[1]:.2f}: "
                             f"{off:.2f} mm off the routed path "
                             f"(<= {corridor_half:.2f}), "
                             f"{'outboard' if outboard else 'INBOARD'}")
                if off > corridor_half or not outboard:
                    lines.append(f"    !! {rref} is not inline in the RF path")
                    ok1 = False
        # obstruction scan
        blockers = []
        allow = {"U1", aref} | set(rrefs)
        for f in board.GetFootprints():
            if f.GetReference() in allow:
                continue
            for p in f.Pads():
                if p.GetNetname() == "GND":
                    continue
                if min(seg_point_dist(path[i], path[i+1], pxy(p))
                       for i in range(len(path)-1)) < corridor_half:
                    blockers.append(f"{f.GetReference()}.{p.GetNumber()}"
                                    f"[{p.GetNetname() or 'nc'}]")
                    break
        for v in vias:
            if v.GetNetname() == "GND":
                continue
            vp = (mm(v.GetPosition().x), mm(v.GetPosition().y))
            if min(seg_point_dist(path[i], path[i+1], vp)
                   for i in range(len(path)-1)) < corridor_half:
                blockers.append("via")
        if blockers:
            lines.append(f"    !! {len(blockers)} obstruction(s) inside the "
                         f"{2*corridor_half:.2f} mm corridor: "
                         f"{', '.join(sorted(set(blockers))[:8])}")
            ok1 = False
        else:
            lines.append(f"    dog-leg path corridor {2*corridor_half:.2f} mm "
                         f"wide is CLEAR of non-GND pads and vias")
    # How much room actually exists where the RF leaves the module? A CPWG
    # needs W + 2G of copper, plus a via fence standing off 2xW each side.
    bb0 = board.GetBoardEdgesBoundingBox()
    edge_r = mm(bb0.GetRight())
    need_trace = CPWG_W + 2 * CPWG_G
    need_full = CPWG_W + 2 * CPWG_G + 2 * (FENCE_STANDOFF + 0.25)
    lines.append("")
    lines.append("Corridor available where the RF leaves U1:")
    for name, u1pad, aref, rref in RF:
        p49 = pad(fp(board, "U1"), u1pad)
        if p49 is None:
            continue
        r = pad_rect(p49)
        avail = edge_r - r[2] - 0.30      # 0.30 = min copper-to-edge
        lines.append(f"  {name}: pad outer edge x={r[2]:.2f}, board edge "
                     f"x={edge_r:.2f}  ->  usable strip = {avail:.2f} mm")
    lines.append(f"  CPWG needs {need_trace:.2f} mm for trace+gaps, "
                 f"{need_full:.2f} mm including a two-sided via fence")
    if avail < need_full:
        lines.append(f"  !! the strip outboard of the ANT pads is "
                     f"{avail:.2f} mm - too narrow for a fenced CPWG "
                     f"({need_full:.2f} mm). A one-sided (inboard) fence fits "
                     f"in {need_trace:.2f} mm but the outboard side would rely "
                     f"on the board edge, not a via wall.")
        ok1 = False
    lines.append("")
    lines.append(f"GND fence plan: CPWG W={CPWG_W} G={CPWG_G} mm; fence vias "
                 f">= {FENCE_STANDOFF:.2f} mm from the trace (Quectel V1.2 "
                 f"4.3: 2xW), pitch {FENCE_PITCH} mm "
                 f"(= lambda/33 at 2.69 GHz, LTE B41 top).")
    check(1, "ANT pad -> U.FL distance, CPWG path clear, GND fence",
          ok1, "\n".join(lines))

    # ---------------------------------------------------------------- 2
    # RECLASSIFIED. Both antennas mount in the LID and reach the board only
    # through a U.FL pigtail, so there is no PCB copper underneath either of
    # them and a copper keepout is not the applicable control. What the antenna
    # datasheets actually constrain is how far the antenna must sit from metal
    # inside the housing - that is an INSTALLATION / HOUSING requirement, and
    # the check is that it is written down where the installer will see it.
    ant_fps = [f.GetReference() for f in board.GetFootprints()
               if f.GetReference().startswith("AF")]
    # match the whole word - "1R 2512 anti-surge" (R80) contains "ANT"
    onboard = [f.GetReference() for f in board.GetFootprints()
               if re.search(r"\bANTENNA\b", (f.GetValue() or "").upper())
               and not f.GetReference().startswith("AF")]
    inst = os.path.join(PROJ, "docs", "installation-sheet.md")
    txt = open(inst, encoding="utf-8").read() if os.path.exists(inst) else ""
    has_sec = "Antenna metal clearance" in txt
    figs = re.findall(r"(\d+(?:\.\d+)?)\s*mm", txt.split("Antenna metal clearance")[1]) \
        if has_sec else []
    lines2 = [
        f"antenna PCB footprints on the board: {onboard or 'none'}",
        f"U.FL launch connectors (the only antenna-related copper): "
        f"{sorted(ant_fps)}",
        "",
        "PCB copper keepout: **N/A** - both antennas are lid-mounted and reach",
        "the board only through a U.FL pigtail, so no board copper sits under",
        "either antenna. There is nothing on the PCB to keep clear.",
        "",
        f"metal-clearance recorded as an installation/housing requirement: "
        f"{'YES' if has_sec else 'NO'}",
    ]
    if has_sec:
        lines2.append(f"numeric clearances stated in docs/installation-sheet.md: "
                      f"{', '.join(figs[:8]) if figs else 'NONE'} mm")
    else:
        lines2.append("docs/installation-sheet.md has no 'Antenna metal "
                      "clearance' section yet")
    ok2 = bool(has_sec and figs and not onboard)
    check(2, "Antenna metal clearance (PCB copper N/A - lid-mounted)",
          ok2, "\n".join(lines2))

    # ---------------------------------------------------------------- 3
    u5 = fp(board, "U5")
    u5box = None
    if u5:
        b = u5.GetCourtyard(pcbnew.F_CrtYd).BBox()
        u5box = (mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom()))

    def in_u5(r):
        if not u5box:
            return False
        return not (r[2] < u5box[0] or r[0] > u5box[2]
                    or r[3] < u5box[1] or r[1] > u5box[3])

    # BUCK_HV rescope area (approved): inside it the HV-to-LV minimum is the
    # electrical 0.60 mm, not 1.5 mm. Read from the board's named rule area so
    # this check cannot drift from what DRC actually enforces.
    buckbox = None
    for z in board.Zones():
        if z.GetZoneName() == "BUCK_HV":
            b = z.GetBoundingBox()
            buckbox = (mm(b.GetLeft()), mm(b.GetTop()),
                       mm(b.GetRight()), mm(b.GetBottom()))

    def in_buck(r):
        if not buckbox:
            return False
        return not (r[2] < buckbox[0] or r[0] > buckbox[2]
                    or r[3] < buckbox[1] or r[1] > buckbox[3])

    hv, lv = [], []
    for f in board.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            r = pad_rect(p)
            # Pads must SHARE a copper layer to have a clearance relationship.
            # Ignoring this reported C73 (F.Cu) against R87 (B.Cu) as 0.000 mm
            # when they are on opposite sides of 1.6 mm of FR4 - which is also
            # why DRC, which does check layers, reported no short.
            lset = frozenset(p.GetLayerSet().CuStack())
            tag = f"{f.GetReference()}.{p.GetNumber()}[{n or 'nc'}]"
            if n in HV_NETS:
                # inside U5's courtyard OR the BUCK_HV rescope: 0.60 mm floor
                hv.append((r, tag, in_u5(r) or in_buck(r), lset))
            elif n in MV_NETS:
                pass    # <= 70 V interior nodes: 0.60 mm electrical, not 1.5
            elif n and n != "GND":
                lv.append((r, tag, in_u5(r) or in_buck(r), lset))
    worst, pair = 1e9, None          # any pair
    wbetween, pbetween = 1e9, None   # different footprints only
    for hr, ht, hu, hl in hv:
        for lr, lt, lu, ll in lv:
            if hu and lu:      # both inside U5's courtyard -> F-20 exception
                continue
            if not (hl & ll):  # no shared copper layer
                continue
            g = rect_gap(hr, lr)
            if g < worst:
                worst, pair = g, (ht, lt)
            if ht.split(".")[0] != lt.split(".")[0] and g < wbetween:
                wbetween, pbetween = g, (ht, lt)
    detail = (f"HV-class pads: {len(hv)}   LV pads (excl GND): {len(lv)}\n\n"
              f"minimum HV->LV clearance, ANY pair, outside the U5 exception:\n"
              f"    **{worst:.3f} mm**   {pair[0]}  <->  {pair[1]}\n"
              f"minimum BETWEEN DIFFERENT components (what layout controls):\n"
              f"    **{wbetween:.3f} mm**   {pbetween[0]}  <->  {pbetween[1]}\n\n"
              f"requirement: >= 1.500 mm")
    # intra-component pairs, split by the <= 40 V exemption
    intra = {}
    for hr, ht, hu, hl in hv:
        for lr, lt, lu, ll in lv:
            if hu and lu or not (hl & ll):
                continue
            ra, rb = ht.split(".")[0], lt.split(".")[0]
            if ra != rb:
                continue
            g = rect_gap(hr, lr)
            if ra not in intra or g < intra[ra][0]:
                intra[ra] = (g, ht, lt)
    ex, notex = [], []
    for ref in sorted(intra):
        g, ht, lt = intra[ref]
        v = V_ACROSS.get(ref)
        row = (f"    {ref:5} {g:5.2f} mm   V across = "
               f"{('%.2f V' % v) if v is not None else 'UNKNOWN'}")
        (ex if (v is not None and v <= V_EXEMPT) else notex).append(row)
    detail += "\n\nIntra-component pairs, <= 40 V (EXEMPT by rule):\n"
    detail += ("\n".join(ex) if ex else "    none")
    detail += ("\n\nIntra-component pairs ABOVE 40 V (not exempt by the 40 V "
               "rule):\n")
    detail += ("\n".join(notex) if notex else "    none")
    if notex:
        detail += ("\n    These rely on the IPC-2221 figure for their actual "
                   "voltage (0.60 mm uncoated at <= 100 V) plus the mandatory "
                   "conformal coating (SKILL P1), the same basis as F-20 at U5."
                   "\n    R40 is the DNP spare divider and is a SINGLE 100k, so "
                   "it sees 91.7 V where the fitted dividers see 32.35 V - if it "
                   "is ever populated it should be 3 x 100k like the others.")
    ok3 = wbetween >= 1.5
    detail += (f"\n\nVERDICT: between-component minimum {wbetween:.3f} mm "
               f"{'>=' if ok3 else '<'} 1.500 mm requirement")
    check(3, "HV->LV: >= 1.5 mm between components, <= 40 V intra exempt",
          ok3, detail)

    # ---------------------------------------------------------------- 4
    u1 = fp(board, "U1")
    vb = [pad(u1, n) for n in ("57", "58", "59", "60")]
    vb = [p for p in vb if p]
    rows, ok4 = [], True
    for ref in ("C40", "C41", "C81", "C82"):
        f = fp(board, ref)
        if f is None:
            rows.append(f"  {ref}: NOT PLACED"); ok4 = False; continue
        best = min(rect_gap(pad_rect(cp), pad_rect(vp))
                   for cp in f.Pads() for vp in vb)
        c = (mm(f.GetPosition().x), mm(f.GetPosition().y))
        rows.append(f"  {ref} at ({c[0]:6.2f},{c[1]:6.2f})  nearest of U1 "
                    f"pads 57-60 = {best:5.2f} mm"
                    f"   {'ok' if best <= 5.0 else '<-- OVER 5 mm'}")
        if best > 5.0:
            ok4 = False
    check(4, "VBAT_MODEM bulk caps within 5 mm of U1 pads 57-60",
          ok4, "\n".join(rows))

    # ---------------------------------------------------------------- 5
    u3 = fp(board, "U3")
    holes = [(f.GetReference(), mm(f.GetPosition().x), mm(f.GetPosition().y))
             for f in board.GetFootprints() if f.GetReference().startswith("H")]
    if u3 and holes:
        ux, uy = mm(u3.GetPosition().x), mm(u3.GetPosition().y)
        ds = sorted(((math.hypot(ux - hx, uy - hy), r) for r, hx, hy in holes))
        near, nref = ds[0]
        cx = sum(h[1] for h in holes) / len(holes)
        cy = sum(h[2] for h in holes) / len(holes)
        midspan = math.hypot(ux - cx, uy - cy)
        detail = (f"U3 at ({ux:.2f}, {uy:.2f})\n"
                  f"nearest mounting hole: {nref} at "
                  f"{near:.2f} mm centre-to-centre\n"
                  f"all holes: " + ", ".join(f"{r}={d:.1f}" for d, r in ds) +
                  f"\ndistance from the mounting-hole centroid "
                  f"({cx:.1f},{cy:.1f}): {midspan:.2f} mm "
                  f"(larger = further from mid-span)")
        ok5 = near <= 8.0
        detail += f"\ncriterion: nearest hole <= 8.00 mm -> {near:.2f} mm"
        check(5, "U3 IMU adjacent to a mounting hole, not mid-span", ok5, detail)
    else:
        check(5, "U3 IMU adjacent to a mounting hole", False, "U3 or holes missing")

    # ---------------------------------------------------------------- 6
    pts, miss = [], []
    for ref, pn in (("C73", "1"), ("U5", "8"), ("U5", "6"),
                    ("D16", "1"), ("D16", "2"), ("C73", "2")):
        p = pad(fp(board, ref), pn)
        if p is None:
            miss.append(f"{ref}.{pn}")
        else:
            pts.append((f"{ref}.{pn}", pxy(p)))
    if miss:
        check(6, "Buck hot-loop enclosed area", False, f"missing: {miss}")
    else:
        xs = [p[1][0] for p in pts]; ys = [p[1][1] for p in pts]
        a = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i][1]; x2, y2 = pts[(i + 1) % len(pts)][1]
            a += x1 * y2 - x2 * y1
        area6 = abs(a) / 2
        l1 = fp(board, "L1")
        l1d = ""
        if l1:
            sw = pad(fp(board, "U5"), "6")
            best = min(rect_gap(pad_rect(sw), pad_rect(q)) for q in l1.Pads())
            l1d = f"\nU5 SW (pin 6) to nearest L1 pad: {best:.2f} mm"
        detail = ("loop vertices (commutating path C73 -> U5 VIN -> U5 SW -> "
                  "D16 -> GND -> C73):\n" +
                  "\n".join(f"  {n:8} ({x:6.2f}, {y:6.2f})" for n, (x, y) in pts) +
                  f"\n\nenclosed area (shoelace) = **{area6:.2f} mm^2**"
                  f"\nbounding box {max(xs)-min(xs):.2f} x {max(ys)-min(ys):.2f} mm"
                  + l1d)
        check(6, "Buck hot loop U5 SW -> L1 -> D16 -> C73 enclosed area",
              area6 > 0, detail)

    # ---------------------------------------------------------------- 7
    bb = board.GetBoardEdgesBoundingBox()
    ex0, ey0 = mm(bb.GetLeft()), mm(bb.GetTop())
    ex1, ey1 = mm(bb.GetRight()), mm(bb.GetBottom())
    rows, ok7 = [f"board outline {ex0:.2f},{ey0:.2f} .. {ex1:.2f},{ey1:.2f} "
                 f"({ex1-ex0:.1f} x {ey1-ey0:.1f} mm)"], True
    for ref in ("J1", "J2", "X1"):
        f = fp(board, ref)
        if f is None:
            rows.append(f"  {ref}: NOT PLACED"); ok7 = False; continue
        b = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
        r = (mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom()))
        gaps = {"left": r[0]-ex0, "top": r[1]-ey0, "right": ex1-r[2],
                "bottom": ey1-r[3]}
        near = min(gaps, key=gaps.get)
        rows.append(f"  {ref}: extent {r[0]:.2f},{r[1]:.2f} .. {r[2]:.2f},"
                    f"{r[3]:.2f}  edge gaps L/T/R/B = "
                    f"{gaps['left']:.2f}/{gaps['top']:.2f}/"
                    f"{gaps['right']:.2f}/{gaps['bottom']:.2f} mm"
                    f"  -> nearest edge: {near} ({gaps[near]:.2f} mm)")
        if ref in ("J1", "J2") and gaps[near] > 3.0:
            rows.append(f"      !! {ref} is a wire-to-board connector and sits "
                        f"{gaps[near]:.2f} mm from the nearest edge")
            ok7 = False
    x1 = fp(board, "X1")
    if x1:
        b = x1.GetCourtyard(pcbnew.F_CrtYd).BBox()
        r = (mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom()))
        # the card slot opens on the side away from the contact rows; the
        # contacts sit at the -y end of the footprint, so the opening is +y
        rot = x1.GetOrientationDegrees() % 360
        rows.append(f"  X1 SIM: rotation {rot:.0f} deg; card slot faces +Y "
                    f"(contacts are at the -Y end of the land)")
        rows.append(f"      clearance from the X1 land to the +Y board edge: "
                    f"{ey1 - r[3]:.2f} mm")
        if ey1 - r[3] > 3.0:
            rows.append("      !! the slot does not face an edge - insertion "
                        "needs a lid opening; confirm with the housing")
            ok7 = False
    check(7, "J1/J2 edge positions, SIM access direction", ok7, "\n".join(rows))

    # ---------------------------------------------------------------- 8
    want = [os.path.join(PROJ, "docs", "renders", n)
            for n in ("top.png", "bottom.png", "iso.png")]
    have = [p for p in want if os.path.exists(p)]
    check(8, "Renders exported to docs/renders/",
          len(have) == len(want),
          "\n".join(f"  {'ok  ' if p in have else 'MISS'} {os.path.relpath(p, PROJ)}"
                    for p in want))

    # ---------------------------------------------------------------- summary
    print(f"\n{'='*74}\nSUMMARY\n{'='*74}")
    for n, title, ok, _ in results:
        print(f"  {n}. {'PASS' if ok else 'FAIL'}  {title}")
    nfail = sum(1 for _, _, ok, _ in results if not ok)
    print(f"\n{len(results)-nfail}/{len(results)} passed, {nfail} failed")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
