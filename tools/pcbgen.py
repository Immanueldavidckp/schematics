#!/usr/bin/env python3
"""Build telematics-tracker.kicad_pcb deterministically, the same way
tools/sheets.py builds the schematic sheets.

Stage 1 (this file, milestone 4): board outline, mounting holes, stackup.
Placement, zones, thermal vias and routing follow in later stages so each is
separately reviewable and each regeneration stays reproducible.

The outline is PROVISIONAL 80 x 60 mm. The final outline and the M3 hole
positions come from the purchased housing (handoff section 9) - do not treat
these numbers as released.

Run:  python3 tools/pcbgen.py
"""
import os
import sys
import uuid as _uuid

import pcbnew

# same namespace as tools/schgen.py, so the two generators cannot collide
NS = _uuid.UUID("11111111-2222-3333-4444-555555555555")


def det_uuid(*parts):
    return str(_uuid.uuid5(NS, "|".join(str(p) for p in parts)))

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")
TEMPLATE = os.path.join(PROJ, "tools", "pcb-template.kicad_pcb")
SYSFP = "/usr/share/kicad/footprints"

# ---- provisional outline -------------------------------------------------
# CHECK 1: the outline grew in Y from 60.0 to 62.0 mm. Placement could not
# absorb U1's inboard/downward shift:
#   AF1 must clear H2's 6.29 mm M3 pad (reaches y=6.65) -> U1 y >= 28.15
#   X1 (15.09 mm tall) must fit below U1 above the keep-in -> U1 y <= 27.51
# infeasible by 0.64 mm at BH=60. BH=62 opens the window to 28.15..29.51.
# STILL PROVISIONAL - the final outline comes from the purchased housing.
# X also grew, 80.0 -> 82.0. Moving U1 inboard for the RF corridor took 2 mm
# off the power zone, which left the buck cluster single-file in a 5.35 mm
# strip and pushed C73's VIN_B pad to 0.215 mm from U5's LV pins (check 3
# needs 1.5 mm between components). Growing X by 2 mm and putting U1 back at
# x=61 keeps the 3.73 mm corridor AND restores the power zone to 22.25 mm.
BW, BH = 82.0, 62.0          # mm, board width x height
CORNER = 2.0                 # mm, corner radius (housing-friendly, avoids a
                             # sharp point at the M3 bosses)
HOLE_INSET = 3.5             # mm, M3 hole centre from each edge

# F-18: fifth M3 in the digital zone, for the IMU anchor and to stiffen the
# panel under the 31 x 28 mm LCC module. Provisional exactly like the outline
# - it needs a matching boss in the purchased housing.
FIFTH_HOLE = (23.5, 55.0)

# The HV boundary from the placement study: everything left of x = 20 mm is
# the HV zone (handoff section 7). Marked on silk, not copper.
HV_X = 20.0

MOUNT_FP = ("MountingHole", "MountingHole_3.2mm_M3_ISO7380_Pad")


def _split_forms(body):
    """Split an S-expression body into its top-level child forms."""
    out, depth, start, instr, esc = [], 0, None, False, False
    for i, ch in enumerate(body):
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                out.append(body[start:i + 1])
    return out


def canonicalise(path):
    """Make the saved board byte-stable across regenerations.

    Two things in pcbnew defeat plain regeneration:
      1. KIIDs are random and there is no Python setter for them.
      2. Footprints and drawings are written from an unordered container, so
         even identical input can emit blocks in a different order.
    Both are fixed here, after saving: child forms are sorted by a stable key
    and every UUID is then restamped by position. Without this, regenerating
    produces a churn-only diff and MIGRATION.md's "regenerate, then git diff
    must be empty" check can no longer prove the design has not changed.
    """
    import re
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"\((kicad_pcb)\s", txt)
    if not m:
        sys.exit("unexpected board file shape")
    body = txt[txt.index("\n") + 1:txt.rstrip().rfind(")")]
    forms = _split_forms(body)

    # header forms keep their given order; nets must precede any reference
    HEAD = ("version", "generator", "generator_version", "general", "paper",
            "title_block", "layers", "setup", "net")
    head, rest = [], []
    for f in forms:
        tag = re.match(r"\(\s*([A-Za-z_0-9]+)", f).group(1)
        (head if tag in HEAD else rest).append((tag, f))

    def key(item):
        tag, f = item
        ref = re.search(r'\(property "Reference" "([^"]*)"', f)
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", f)
        start = re.search(r"\(start ([-\d.]+) ([-\d.]+)", f)
        # zones carry neither a Reference nor an (at ...) - they are polygons -
        # so without these two they all sorted as equal and swapped places
        # between runs, breaking byte-identical regeneration.
        zname = re.search(r'\(name "([^"]*)"', f)
        znet = re.search(r'\(net_name "([^"]*)"', f)
        firstxy = re.search(r"\(xy ([-\d.]+) ([-\d.]+)", f)
        c = at or start or firstxy
        xy = (float(c.group(1)), float(c.group(2))) if c else (0.0, 0.0)
        lay = re.search(r'\(layer "([^"]+)"', f)
        return (tag,
                ref.group(1) if ref else "",
                zname.group(1) if zname else "",
                znet.group(1) if znet else "",
                lay.group(1) if lay else "",
                xy[0], xy[1], len(f))

    rest.sort(key=key)
    ordered = [f for _, f in head] + [f for _, f in rest]

    n = [0]

    def sub(_m):
        n[0] += 1
        return f'(uuid "{det_uuid("pcb", n[0])}")'

    out = "(kicad_pcb\n" + "\n".join("\t" + f.replace("\n", "\n") for f in ordered) \
          + "\n)\n"
    out = re.sub(r'\(uuid "[0-9a-fA-F-]{36}"\)', sub, out)
    open(path, "w", encoding="utf-8").write(out)
    print(f"canonicalised: {len(ordered)} top-level forms, "
          f"{n[0]} uuids restamped")


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def add_seg(board, layer, a, b, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pt(*a))
    s.SetEnd(pt(*b))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    board.Add(s)
    return s


def add_arc(board, layer, centre, start, end, width=0.1):
    """Arc through explicit start/mid/end, built from centre + endpoints."""
    import math
    cx, cy = centre
    a0 = math.atan2(start[1] - cy, start[0] - cx)
    a1 = math.atan2(end[1] - cy, end[0] - cx)
    r = math.hypot(start[0] - cx, start[1] - cy)
    # take the short way round
    d = (a1 - a0) % (2 * math.pi)
    if d > math.pi:
        d -= 2 * math.pi
    am = a0 + d / 2
    mid = (cx + r * math.cos(am), cy + r * math.sin(am))
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetStart(pt(*start))
    s.SetEnd(pt(*end))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    try:
        s.SetArcGeometry(pt(*start), pt(*mid), pt(*end))
    except AttributeError:
        s.SetCenter(pt(cx, cy))
    board.Add(s)
    return s


def outline(board):
    """Rounded rectangle on Edge.Cuts, 0 -> BW, 0 -> BH."""
    r = CORNER
    L = pcbnew.Edge_Cuts
    add_seg(board, L, (r, 0), (BW - r, 0))
    add_seg(board, L, (BW, r), (BW, BH - r))
    add_seg(board, L, (BW - r, BH), (r, BH))
    add_seg(board, L, (0, BH - r), (0, r))
    add_arc(board, L, (BW - r, r), (BW - r, 0), (BW, r))
    add_arc(board, L, (BW - r, BH - r), (BW, BH - r), (BW - r, BH))
    add_arc(board, L, (r, BH - r), (r, BH), (0, BH - r))
    add_arc(board, L, (r, r), (0, r), (r, 0))
    print(f"outline: rounded rect {BW} x {BH} mm, corner r = {r} mm")


def get_net(board, name):
    n = board.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
    return n


def mounting_holes(board):
    """4 corner M3 + the provisional 5th (F-18). All GND-tied per handoff."""
    gnd = get_net(board, "GND")
    pos = [(HOLE_INSET, HOLE_INSET),
           (BW - HOLE_INSET, HOLE_INSET),
           (HOLE_INSET, BH - HOLE_INSET),
           (BW - HOLE_INSET, BH - HOLE_INSET),
           FIFTH_HOLE]
    lib, name = MOUNT_FP
    for i, (x, y) in enumerate(pos, start=1):
        fp = pcbnew.FootprintLoad(os.path.join(SYSFP, lib + ".pretty"), name)
        if fp is None:
            sys.exit(f"could not load {lib}:{name}")
        fp.SetPosition(pt(x, y))
        fp.SetReference(f"H{i}")
        fp.Reference().SetVisible(False)
        for pad in fp.Pads():
            pad.SetNet(gnd)
        board.Add(fp)
        tag = " (F-18, provisional)" if i == 5 else ""
        print(f"  H{i} M3 at ({x}, {y}) GND-tied{tag}")


def hv_boundary(board):
    """Silk boundary for the HV zone (handoff section 7). Not copper."""
    add_seg(board, pcbnew.F_SilkS, (HV_X, 1.0), (HV_X, BH - 1.0), width=0.15)
    # Runs up the boundary line itself, clear of the H1/H3 pads at the corners.
    t = pcbnew.PCB_TEXT(board)
    t.SetText("HV ZONE  <= 100 V")
    t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(pt(HV_X - 1.2, BH / 2))
    t.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
    t.SetTextThickness(mm(0.15))
    t.SetTextAngleDegrees(90)
    board.Add(t)
    print(f"HV boundary on F.Silkscreen at x = {HV_X} mm")


def main():
    # Always build from the pristine template (layers + setup only) rather
    # than mutating the previous output. Two reasons: regeneration stays
    # deterministic and diffable, exactly like tools/sheets.py; and pcbnew's
    # board.Remove() hands ownership back to Python, which double-frees and
    # segfaults the interpreter on the next GC. Never delete, always rebuild.
    board = pcbnew.LoadBoard(TEMPLATE)

    outline(board)
    mounting_holes(board)
    hv_boundary(board)

    board.BuildListOfNets()
    nfp = len(list(board.GetFootprints()))
    ndr = len(list(board.GetDrawings()))
    pcbnew.SaveBoard(PCB, board)
    canonicalise(PCB)
    print(f"\nwrote {os.path.basename(PCB)}: {nfp} footprints, "
          f"{ndr} drawing items")
    print("NOTE outline and all hole positions are PROVISIONAL "
          "(final geometry comes from the purchased housing)")


if __name__ == "__main__":
    main()
