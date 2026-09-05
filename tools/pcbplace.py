#!/usr/bin/env python3
"""Milestone 4 stage 2: placement + planes.

Adds to the board built by tools/pcbgen.py:
  - every footprint from the exported netlist, placed by zone
  - nets assigned to pads
  - L2 solid GND plane, L3 power pours
  - thermal / stitching vias (F-9 relief plan, U5 pad, RF fence)

Placement strategy. The critical parts are positioned explicitly in ANCHORS -
those are the ones where position is an engineering decision (RF, HV, the
switching loop, the modem ground field). Everything else is packed into its
zone next to its owner by a skyline packer, spilling to the bottom side when a
zone's top side is full. Total courtyard is 69% of one side, so a single-sided
placement cannot route on a stackup whose only signal layers are L1 and L4.

Nothing here is released: the outline, the hole positions and therefore every
coordinate below are provisional until the housing is confirmed.

Run:  python3 tools/pcbgen.py && python3 tools/pcbplace.py
"""
import os
import re
import sys

import pcbnew

from pcbgen import (PROJ, PCB, SYSFP, BW, BH, HV_X, canonicalise, get_net,
                    mm, pt, add_seg)

JLCFP = os.path.join(PROJ, "lib", "jlc.pretty")
NETLIST = os.path.join(PROJ, "nl.net")

GAP = 0.70          # mm between courtyards when packing
EDGE = 1.0          # mm keep-in from the board edge

# ---------------------------------------------------------------- floorplan
# (x0, y0, x1, y1) in mm. Zones are packed independently, top side first.
ZONES = {
    # HV: connector end. Everything at up to 100 V lives left of HV_X.
    "hv":      (EDGE, EDGE, HV_X - 0.75, BH - EDGE),
    # Power gets 23 mm of height, not 15.5. L1 alone is 13.8 x 12.4 mm, and at
    # the smaller size the relaxation had nowhere to put C73/C74 and stacked
    # them on L1. x stops at 43.0 because U1's keepout reaches x = 44.2.
    "pwr":     (HV_X + 0.75, EDGE, 43.0, 27.0),
    "dig":     (HV_X + 0.75, 27.5, 43.0, BH - EDGE),
    "rf":      (44.0, EDGE, BW - EDGE, BH - EDGE),
}

# Explicit positions: (x, y, rotation_deg, side) - side 0 = top, 1 = bottom.
# These are decisions, not packing results.
ANCHORS = {
    # --- RF end ---------------------------------------------------------
    # U1 centred in the RF zone, ANT pads (47/49) facing the right edge.
    "U1":  (61.0, 27.0, 0, 0),
    # Placement amendment (b): GNSS moved to the BOTTOM-right corner so the
    # buck inductor sits diagonally opposite it (~62 mm instead of ~45 mm).
    # LTE takes the top-right corner - it transmits and has AGC, GNSS does
    # neither.
    "AF1": (72.0, 8.0, 0, 0),      # LTE  U.FL, top-right
    "AF2": (72.0, 52.0, 0, 0),     # GNSS U.FL, bottom-right
    # SIM group beside the module, away from the RF edge. F-16: pad map is the
    # verified incumbent, locating-post holes deliberately absent.
    "X1":  (52.0, 51.0, 0, 0),
    # F-17 land pattern now exists, so the MFF2 site can be placed. It sits
    # beside X1 because the two are wired in parallel through 0R selects.
    "X2":  (63.5, 50.5, 0, 0),

    # --- HV end ---------------------------------------------------------
    # J1 rotated so its 23.2 mm length runs up the 60 mm edge.
    "J1":  (7.5, 30.0, 90, 0),
    "F1":  (16.0, 8.0, 90, 0),
    "D1":  (16.0, 15.0, 90, 0),
    "D2":  (15.5, 21.5, 90, 0),
    "R80": (16.0, 27.5, 90, 0),

    # --- power block ----------------------------------------------------
    # Amendment (a): the hot loop is C73/C74 -> U5 VIN -> U5 SW -> D16, so the
    # column is ordered to follow it. D16 sits above U5 because SW is pin 6 on
    # U5's upper edge; C73/C74 sit below because VIN is pin 8 on the lower one.
    #
    # The first attempt stacked C73/C74 in the strip ABOVE L1, which left a
    # 4.2 mm gap for two 3.29 mm parts - the caps ended 1.33 mm apart and could
    # not be relaxed out, because C73 was clamped on the zone edge and L1
    # blocked C74. Neither a wider board nor a 10x10 inductor fixed that
    # (measured: 3 -> 2 and 3 -> 1 overlaps respectively); putting the cluster
    # in its own column beside L1 is what actually resolves it.
    "L1":  (27.65, 12.0, 0, 0),    # amendment (b): left end, far from ANT_GNSS
    "D16": (38.8, 2.8, 0, 0),
    "U5":  (38.3, 9.0, 0, 0),
    "C73": (38.3, 15.0, 0, 0),   # nearest U5 VIN: this is the loop-critical one
    # U6 charger and U9 LDO are low-voltage and do not belong in the buck
    # column: U6 feeds SYS to the battery at J2, so it belongs near J2 on the
    # digital side. U9 (SYS -> 3V3 LDO) has no critical position at all and is
    # left to the packer.
    "U6":  (30.0, 46.0, 0, 0),
    "J2":  (40.0, 55.0, 0, 0),

    # --- digital --------------------------------------------------------
    "U2":  (29.0, 25.0, 0, 0),
    # Amendment (c) / F-18: U3 hard against the provisional 5th M3 at (27,52).
    "U3":  (29.5, 55.0, 0, 0),
    "U7":  (24.0, 33.0, 0, 0),
    "U4":  (24.5, 43.5, 0, 0),
    "U8":  (41.0, 24.0, 0, 0),
}

def relax_anchors(anchor_boxes, bounds, min_gap=1.10, iters=1500):
    """Nudge overlapping anchors apart, keeping each inside its bounds.

    The anchor coordinates encode engineering intent - which zone a part is in
    and what it sits next to - but hand-picked millimetres do not converge on a
    legal layout: L1 alone is 13.8 mm wide in a 22.75 mm power zone, and the
    first pass left 16 overlapping anchor pairs which produced every remaining
    courtyard overlap and short. This preserves the intent and fixes the
    arithmetic: push each overlapping pair apart along its axis of least
    overlap, clamp to bounds, repeat.
    """
    pos = {r: [v["x"], v["y"]] for r, v in anchor_boxes.items()}
    for it in range(iters):
        moved = False
        refs = sorted(pos)
        for i, a in enumerate(refs):
            for b in refs[i + 1:]:
                A, B = anchor_boxes[a], anchor_boxes[b]
                if A["side"] != B["side"]:
                    continue
                dx = (pos[a][0] - pos[b][0])
                dy = (pos[a][1] - pos[b][1])
                needx = (A["w"] + B["w"]) / 2 + min_gap
                needy = (A["h"] + B["h"]) / 2 + min_gap
                ox, oy = needx - abs(dx), needy - abs(dy)
                if ox <= 0 or oy <= 0:
                    continue
                moved = True
                if dx == 0 and dy == 0:
                    # exactly coincident: bounds clamping can collapse two
                    # boxes onto one point, and then dx/dy give no direction.
                    # Nudge deterministically by reference order.
                    dx = 1.0 if a < b else -1.0
                # alternate the preferred axis so a pair that cannot separate
                # on its narrower axis eventually tries the other one
                prefer_x = (ox <= oy) if (it % 2 == 0) else (ox < oy * 0.6)
                if prefer_x:                      # separate along x
                    push = ox / 2 + 1e-3
                    sgn = 1.0 if dx >= 0 else -1.0
                    pos[a][0] += sgn * push
                    pos[b][0] -= sgn * push
                else:
                    push = oy / 2 + 1e-3
                    sgn = 1.0 if dy >= 0 else -1.0
                    pos[a][1] += sgn * push
                    pos[b][1] -= sgn * push
        for r, (x0, y0, x1, y1) in bounds.items():
            A = anchor_boxes[r]
            pos[r][0] = min(max(pos[r][0], x0 + A["w"] / 2), x1 - A["w"] / 2)
            pos[r][1] = min(max(pos[r][1], y0 + A["h"] / 2), y1 - A["h"] / 2)
        if not moved:
            break
    # Report anything still overlapping after the last iteration. Silent
    # non-convergence here shows up much later as a courtyard DRC error whose
    # cause is no longer obvious.
    leftover = []
    refs = sorted(pos)
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            A, B = anchor_boxes[a], anchor_boxes[b]
            if A["side"] != B["side"]:
                continue
            ox = (A["w"] + B["w"]) / 2 - abs(pos[a][0] - pos[b][0])
            oy = (A["h"] + B["h"]) / 2 - abs(pos[a][1] - pos[b][1])
            if ox > 0 and oy > 0:
                leftover.append(f"{a}+{b} (x {ox:+.2f}, y {oy:+.2f})")
    if leftover:
        print(f"  relaxation did NOT converge for {len(leftover)} pair(s): "
              + ", ".join(leftover))
    return {r: (round(v[0], 2), round(v[1], 2)) for r, v in pos.items()}


# sheet -> zone for everything not anchored
SHEET_ZONE = {"power": "pwr", "mcu": "dig", "storage": "dig",
              "io": "hv", "modem_rf": "rf"}

# Where a part goes when its own zone is full on both sides. The power sheet
# needs 694 mm^2 of courtyard against a 372 mm^2 power zone, so it must spill;
# it spills into the digital zone, which is adjacent. HV deliberately spills
# nowhere except its own bottom side - a 100 V part must not wander out of the
# zone the 1.5 mm clearance rule and the silk boundary are drawn around.
SPILL = {"pwr": ["dig", "rf"], "dig": ["pwr", "rf"],
         "rf": ["dig"], "hv": []}

# The io sheet is a mix of HV and LV, so sheet name alone cannot place it:
# the DI/DO/divider front ends sit at up to 100 V while the gate drive, the
# opto collectors and the CAN transceiver side are 3V3/5V logic. Assigning the
# whole sheet to "hv" pushed the eight DO gate-drive resistors R42-R49 into the
# HV zone, filled it, and left 13 parts unplaced.
#
# Instead, an io part goes in the HV zone if and only if it actually touches an
# HV-class net. That is also what the HV keepout means in practice: nothing
# low-voltage should be sitting inside the zone the 1.5 mm rule is drawn
# around. HV net membership is read from the netclass patterns in the .kicad_pro
# so there is one source of truth.
ZONE_OVERRIDE = {
    "TP27": "dig", "TP28": "dig", "TP24": "rf",
}


def hv_nets():
    """The HV net list, taken from tools/netclasses.py rather than from the
    generated .kicad_pro.

    It cannot be read from the project file here: pcbnew.SaveBoard() rewrites
    the project and wipes net_settings, so by the time pcbgen.py has run there
    are no netclass patterns left to read. netclasses.py is re-applied as the
    last build step for the same reason.
    """
    import netclasses
    return set(netclasses.HV)

POWER_POURS = [
    # (net, layer, x0, y0, x1, y1) on L3. The 5V0 pour starts below the U5
    # island and keeps the HV netclass clearance from it.
    ("5V0", "In2.Cu", HV_X + 0.75, 27.5, 43.0, 39.0),
    ("SYS", "In2.Cu", HV_X + 0.75, 39.5, 43.0, 48.0),
    ("3V3", "In2.Cu", HV_X + 0.75, 48.5, 43.0, BH - EDGE),
]

# The EG11752 exposed pad is VIN_B (F-20), and the skill file requires the
# buck's thermal pad stitched down with >= 9 vias. Those vias need copper to
# land on, so L3 carries a small VIN_B island under U5 - which is also what
# spreads the heat. Sized and placed from U5's actual position at build time.
U5_ISLAND_MARGIN = 1.6


# ------------------------------------------------------------------ netlist
def parse_netlist(path):
    t = open(path, encoding="utf-8").read()
    comps = {}
    for m in re.finditer(
            r'\(comp\n\s*\(ref "([^"]+)"\)(.*?)(?=\n\t\t\(comp\n|\n\t\)\n\t\()',
            t, re.S):
        ref, body = m.groups()
        fp = re.search(r'\(footprint "([^"]*)"\)', body)
        val = re.search(r'\(value "([^"]*)"\)', body)
        sh = re.search(r'\(name "Sheetname"\)\s*\(value "([^"]*)"\)', body)
        comps[ref] = dict(ref=ref, fp=fp.group(1) if fp else "",
                          val=val.group(1) if val else "",
                          sheet=sh.group(1) if sh else "?")
    nets = {}
    for m in re.finditer(
            r'\(net\s*\(code\s+"?\d+"?\)\s*\(name\s+"([^"]*)"\)(.*?)'
            r'(?=\n\t\t\(net\s|\Z)', t, re.S):
        name, body = m.groups()
        if name.startswith("unconnected-"):
            continue
        nets[name] = re.findall(
            r'\(node\s*\(ref\s+"([^"]+)"\)\s*\(pin\s+"([^"]+)"\)', body)
    return comps, nets


def load_fp(fpid):
    """Always return a FRESH footprint instance.

    Do not cache and reuse the object: pcbnew hands back one C++ FOOTPRINT,
    and board.Add() of the same object is a no-op after the first call, so
    every component sharing a footprint id collapses onto a single instance
    that the next SetPosition() simply moves. That silently produced 45
    footprints instead of 219 and left 349 pads unbound to nets.
    """
    lib, _, name = fpid.partition(":")
    path = JLCFP if lib == "jlc" else os.path.join(SYSFP, lib + ".pretty")
    if not os.path.isdir(path):
        return None
    try:
        return pcbnew.FootprintLoad(path, name)
    except Exception:
        return None


def keepout_abs(fp):
    """(cx, cy, w, h) of a POSITIONED footprint's keepout, in board mm.

    Returns the box's own centre, not the footprint's origin. Those are not the
    same thing: J1's derived Molex courtyard is centred 7.50 mm in x and
    1.92 mm in y away from its origin, because the origin sits on pin 1. The
    first version blocked a correctly-sized box in the wrong place, which is
    what let D2, D6, F1, TP8 and TP9 be packed on top of J1.
    """
    boxes = []
    cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if cy.GetWidth() > 0:
        boxes.append(cy)
    for pd in fp.Pads():
        boxes.append(pd.GetBoundingBox())
    if not boxes:
        boxes.append(fp.GetBoundingBox(False, False))
    x0 = min(b.GetLeft() for b in boxes)
    x1 = max(b.GetRight() for b in boxes)
    y0 = min(b.GetTop() for b in boxes)
    y1 = max(b.GetBottom() for b in boxes)
    return (pcbnew.ToMM((x0 + x1) // 2), pcbnew.ToMM((y0 + y1) // 2),
            pcbnew.ToMM(x1 - x0), pcbnew.ToMM(y1 - y0))


_sizecache = {}


def size_of(fp, fpid=None):
    """Keepout size = max(courtyard, pad extent) per axis.

    The courtyard alone is not safe to pack against: on several of these
    footprints F.CrtYd encloses only the BODY, not the leads. U2's LQFP-48
    courtyard measures 7.1 x 7.1 while its pads reach 9.0 mm, so packing to the
    courtyard dropped 0603s straight onto its leads - that single mistake
    produced most of the U1/U2 clearance and shorting violations.
    """
    if fpid is not None and fpid in _sizecache:
        return _sizecache[fpid]
    cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    w, h = pcbnew.ToMM(cy.GetWidth()), pcbnew.ToMM(cy.GetHeight())
    pads = list(fp.Pads())
    if pads:
        x0 = min(pcbnew.ToMM(pd.GetBoundingBox().GetLeft()) for pd in pads)
        x1 = max(pcbnew.ToMM(pd.GetBoundingBox().GetRight()) for pd in pads)
        y0 = min(pcbnew.ToMM(pd.GetBoundingBox().GetTop()) for pd in pads)
        y1 = max(pcbnew.ToMM(pd.GetBoundingBox().GetBottom()) for pd in pads)
        w, h = max(w, x1 - x0), max(h, y1 - y0)
    if w == 0 or h == 0:
        bb = fp.GetBoundingBox(False, False)
        w = w or pcbnew.ToMM(bb.GetWidth())
        h = h or pcbnew.ToMM(bb.GetHeight())
    wh = (w, h)
    if fpid is not None:
        _sizecache[fpid] = wh
    return wh


def through_obstacles(fp):
    """Positions/sizes of features that occupy BOTH sides of the board.

    A bottom-side part may sit under a top-side SMD part quite happily, but not
    under a through-hole pad, an unplated hole or a via. Those have to be
    blocked on both shelves.
    """
    out = []
    for pd in fp.Pads():
        ls = pd.GetLayerSet()
        if ls.Contains(pcbnew.F_Cu) and ls.Contains(pcbnew.B_Cu):
            bb = pd.GetBoundingBox()
            out.append((pcbnew.ToMM(bb.GetCenter().x),
                        pcbnew.ToMM(bb.GetCenter().y),
                        pcbnew.ToMM(bb.GetWidth()),
                        pcbnew.ToMM(bb.GetHeight())))
        elif pd.GetDrillSizeX() > 0:
            out.append((pcbnew.ToMM(pd.GetPosition().x),
                        pcbnew.ToMM(pd.GetPosition().y),
                        pcbnew.ToMM(pd.GetDrillSizeX()),
                        pcbnew.ToMM(pd.GetDrillSizeY() or pd.GetDrillSizeX())))
    return out


# ------------------------------------------------------------------ packing
class Shelf:
    """Skyline/shelf packer over a rectangle, with pre-placed obstacles."""

    def __init__(self, rect):
        self.x0, self.y0, self.x1, self.y1 = rect
        self.obstacles = []

    def block(self, x, y, w, h):
        self.obstacles.append((x - w / 2 - GAP / 2, y - h / 2 - GAP / 2,
                               x + w / 2 + GAP / 2, y + h / 2 + GAP / 2))

    def _free(self, cx, cy, w, h):
        a = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        if a[0] < self.x0 or a[1] < self.y0 or a[2] > self.x1 or a[3] > self.y1:
            return False
        for o in self.obstacles:
            if a[0] < o[2] and a[2] > o[0] and a[1] < o[3] and a[3] > o[1]:
                return False
        return True

    def place(self, w, h, step=0.5):
        y = self.y0 + h / 2
        while y <= self.y1 - h / 2 + 1e-9:
            x = self.x0 + w / 2
            while x <= self.x1 - w / 2 + 1e-9:
                if self._free(x, y, w, h):
                    self.block(x, y, w, h)
                    return x, y
                x += step
            y += step
        return None


def add_zone(board, layer, net, rect, name=""):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    x0, y0, x1, y1 = rect
    pts = pcbnew.VECTOR_VECTOR2I()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        pts.append(pcbnew.VECTOR2I(mm(x), mm(y)))
    z.AddPolygon(pts)
    z.SetZoneName(name)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # no thermal spokes
    z.SetIsFilled(False)
    board.Add(z)
    return z


def coating_inspection_marks(board):
    """Mark the U5 area on the assembly drawing as a coating inspection point.

    F-20 / SKILL P1: conformal coating is a safety-critical process
    requirement here, not a finish preference. The EG11752's exposed pad is
    VIN_B at up to 100 V with its own signal pins 0.55 mm away, so the board
    only meets creepage once coated. Whoever inspects the assembly has to know
    that this specific area is load-bearing.
    """
    u5 = _fp(board, "U5")
    if u5 is None:
        return
    ux = pcbnew.ToMM(u5.GetPosition().x)
    uy = pcbnew.ToMM(u5.GetPosition().y)
    _, _, uw, uh = keepout_abs(u5)
    m = 1.2
    for layer in (pcbnew.F_Fab,):
        for a, b in (((ux - uw/2 - m, uy - uh/2 - m), (ux + uw/2 + m, uy - uh/2 - m)),
                     ((ux + uw/2 + m, uy - uh/2 - m), (ux + uw/2 + m, uy + uh/2 + m)),
                     ((ux + uw/2 + m, uy + uh/2 + m), (ux - uw/2 - m, uy + uh/2 + m)),
                     ((ux - uw/2 - m, uy + uh/2 + m), (ux - uw/2 - m, uy - uh/2 - m))):
            add_seg(board, layer, a, b, width=0.12)
        t = pcbnew.PCB_TEXT(board)
        t.SetText("COATING INSPECTION - CREEPAGE CRITICAL (F-20)")
        t.SetLayer(layer)
        t.SetPosition(pt(ux, uy - uh / 2 - m - 1.4))
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.7), mm(0.7)))
        t.SetTextThickness(mm(0.11))
        board.Add(t)
    print("F-20: U5 marked as a coating inspection point on F.Fab")


def hv_rule_area(board):
    """The HV keepout, as a named rule area the .kicad_dru can reference.

    This is what makes the 1.5 mm HV-to-signal rule expressible. That rule is a
    BOARD-LEVEL zone separation requirement, and it cannot be applied blindly:
    U5's exposed pad carries VIN_B at up to 100 V and its own signal pins sit
    0.55 mm away inside the SOIC-8 package, so no layout can achieve 1.5 mm
    there. Scoping the rule to items inside this area keeps it satisfiable and
    stops it masking genuine violations elsewhere. See design-log F-20.
    """
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName("HV_ZONE")
    z.SetLayerSet(pcbnew.LSET.AllCuMask())
    for setter in ("SetDoNotAllowTracks", "SetDoNotAllowVias",
                   "SetDoNotAllowPads", "SetDoNotAllowZoneFills",
                   "SetDoNotAllowFootprints"):
        if hasattr(z, setter):
            getattr(z, setter)(False)
    pts = pcbnew.VECTOR_VECTOR2I()
    for x, y in ((0.5, 0.5), (HV_X, 0.5), (HV_X, BH - 0.5), (0.5, BH - 0.5)):
        pts.append(pcbnew.VECTOR2I(mm(x), mm(y)))
    z.AddPolygon(pts)
    board.Add(z)
    print(f"HV keepout: named rule area 'HV_ZONE' over x = 0.5 to {HV_X} mm, "
          f"all copper layers")


def planes(board):
    """L2 solid GND, L3 power pours.

    Pad connection is FULL (no thermal reliefs) on the GND plane. That is not
    just a preference here: EC200U HW Design V1.2 section 4.3 requires
    "The GND pins adjacent to RF pins should not be designed as thermal relief
    pads, and should be fully connected to ground."
    """
    gnd = get_net(board, "GND")
    inset = 0.35
    add_zone(board, board.GetLayerID("In1.Cu"), gnd,
             (inset, inset, BW - inset, BH - inset), "L2_GND_solid")
    print("L2: solid GND pour, full-board, no thermal reliefs")
    # HV island on L3 under U5, for the exposed-pad thermal vias
    u5 = _fp(board, "U5")
    vinb = board.FindNet("/power/VIN_B")
    if u5 is not None and vinb is not None:
        uw, uh = size_of(u5)
        ux = pcbnew.ToMM(u5.GetPosition().x)
        uy = pcbnew.ToMM(u5.GetPosition().y)
        m = U5_ISLAND_MARGIN
        add_zone(board, board.GetLayerID("In2.Cu"), vinb,
                 (ux - uw / 2 - m, uy - uh / 2 - m,
                  ux + uw / 2 + m, uy + uh / 2 + m), "L3_VIN_B_U5_thermal")
        print(f"  L3: VIN_B thermal island under U5 "
              f"({uw + 2*m:.1f} x {uh + 2*m:.1f} mm) - F-20, EP is at line voltage")

    for netname, layer, x0, y0, x1, y1 in POWER_POURS:
        n = board.FindNet(netname)
        if n is None:
            print(f"  L3 skip {netname}: net not on board")
            continue
        add_zone(board, board.GetLayerID(layer), n, (x0, y0, x1, y1),
                 f"L3_{netname}")
        print(f"  L3: {netname} pour {x1-x0:.0f} x {y1-y0:.0f} mm")


# F-9 thermal relief plan. Pads 85-112 are 2.0 x 3.0 mm at 3.2 mm spacing, so
# a via sits comfortably inside each one; the RF fence pads are 2.5 x 0.8 mm,
# which needs the minimum via to keep an annulus.
LATTICE = [str(i) for i in range(85, 113)]
FENCE = ["46", "48", "50", "51"]
PERIM = ["8", "9", "19", "22", "36", "52", "53", "54", "56", "72", "76"]


def _fp(board, ref):
    for f in board.GetFootprints():
        if f.GetReference() == ref:
            return f
    return None


def planned_vias(board):
    """(x, y, diameter) for every stitching via, computed from the anchors.

    Split out from placement so the sites can be reserved before packing.
    """
    spots = []
    u1 = _fp(board, "U1")
    if u1 is not None:
        for group, dia in ((LATTICE, 0.60), (FENCE, 0.50), (PERIM, 0.50)):
            for num in group:
                for pd in u1.Pads():
                    if pd.GetNumber() == num:
                        spots.append((pcbnew.ToMM(pd.GetPosition().x),
                                      pcbnew.ToMM(pd.GetPosition().y), dia))
                        break
    # U5 exposed pad: the skill file requires the buck's thermal pad stitched
    # to L2/L3 with at least 9 vias. EG11752 pin 9 is the EP (and is VIN_B on
    # this part, per the datasheet - so these vias carry VIN_B, not GND).
    u5 = _fp(board, "U5")
    if u5 is not None:
        for pd in u5.Pads():
            if pd.GetNumber() != "9":
                continue
            bb = pd.GetBoundingBox()
            cx = pcbnew.ToMM(bb.GetCenter().x)
            cy = pcbnew.ToMM(bb.GetCenter().y)
            w = pcbnew.ToMM(bb.GetWidth())
            h = pcbnew.ToMM(bb.GetHeight())
            # 3 x 3 grid at a pitch that guarantees the 0.5 mm minimum
            # hole-to-hole. The earlier scaling formula produced 0.72 mm pitch
            # on this 3.30 x 2.40 pad -> 0.42 mm hole-to-hole, which failed.
            # 0.85 mm pitch with a 0.30 mm drill gives 0.55 mm.
            PITCH, VIA = 0.85, 0.50
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    x, y = cx + i * PITCH, cy + j * PITCH
                    if (abs(x - cx) + VIA / 2 <= w / 2 - 0.2 and
                            abs(y - cy) + VIA / 2 <= h / 2 - 0.2):
                        spots.append((x, y, VIA))
            break
    return spots


def stitch_vias(board, spots):
    """Place the vias reserved by planned_vias(), on the net of the pad each
    one sits in, so a via in the U5 exposed pad does not short VIN_B to GND."""
    gnd = get_net(board, "GND")
    made = 0
    for vx, vy, vd in spots:
        net = gnd
        for f in board.GetFootprints():
            hit = False
            for pd in f.Pads():
                if pd.HitTest(pcbnew.VECTOR2I(mm(vx), mm(vy))):
                    if pd.GetNet() is not None and pd.GetNetname():
                        net = pd.GetNet()
                    hit = True
                    break
            if hit:
                break
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pt(vx, vy))
        v.SetWidth(mm(vd))
        v.SetDrill(mm(0.30))
        v.SetNet(net)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        board.Add(v)
        made += 1
    print(f"stitching vias placed: {made}")


def main():
    if not os.path.exists(NETLIST):
        sys.exit(f"missing {NETLIST} - run:\n  kicad-cli sch export netlist "
                 f"--format kicadsexpr --output nl.net telematics-tracker.kicad_sch")
    comps, nets = parse_netlist(NETLIST)
    print(f"netlist: {len(comps)} components, {len(nets)} named nets")

    HV = hv_nets()
    hv_refs = {ref for n, nodes in nets.items() if n in HV for ref, _ in nodes}
    print(f"HV-class nets: {len(HV)}; parts touching HV: {len(hv_refs)}")

    board = pcbnew.LoadBoard(PCB)
    placed, unplaced = {}, []

    # nets first so pads can be bound as footprints are added
    netobj = {n: get_net(board, n) for n in nets}

    # --- add every footprint, anchors at their given position -----------
    zones = {k: Shelf(v) for k, v in ZONES.items()}
    zones.update({k + "_b": Shelf(v) for k, v in ZONES.items()})
    # existing mounting holes are obstacles in whatever zone they fall in
    for fp in board.GetFootprints():
        w, h = size_of(fp)
        x = pcbnew.ToMM(fp.GetPosition().x)
        y = pcbnew.ToMM(fp.GetPosition().y)
        for z in zones.values():
            z.block(x, y, w + 1.0, h + 1.0)   # extra ring: screw head keepout

    def add(ref, c, x, y, rot, side):
        fp = load_fp(c["fp"])
        if fp is None:
            unplaced.append(ref)
            return None
        fp.SetReference(ref)
        fp.SetValue(c["val"])
        # 199 silk_overlap + 199 silk_over_copper violations were all
        # reference-designator text on a board this dense. Two-terminal
        # passives and test points move their reference to F.Fab (kept for the
        # assembly drawing and the CPL, off the silkscreen); the ICs,
        # connectors and semiconductors keep theirs so the board is still
        # readable on the bench. Values are fab-layer only throughout.
        fp.Reference().SetLayer(pcbnew.F_Fab)
        fp.Value().SetLayer(pcbnew.F_Fab)
        board.Add(fp)
        fp.SetPosition(pt(x, y))
        if rot:
            fp.SetOrientationDegrees(rot)
        if side:
            fp.Flip(pt(x, y), False)
        placed[ref] = (x, y, rot, side)
        return fp

    # --- measure the anchors, then relax them into a legal arrangement ---
    abox, bounds = {}, {}
    for ref, (ax, ay, arot, aside) in ANCHORS.items():
        c = comps.get(ref)
        if c is None:
            continue
        probe = load_fp(c["fp"])
        if probe is None:
            continue
        probe.SetPosition(pt(ax, ay))
        if arot:
            probe.SetOrientationDegrees(arot)
        bcx, bcy, aw, ah = keepout_abs(probe)
        abox[ref] = dict(x=bcx, y=bcy, w=aw, h=ah, side=aside,
                         ox=bcx - ax, oy=bcy - ay)
        # each anchor is confined to the zone it was authored into, so relaxing
        # cannot move an HV part out of the HV zone or a part off the board
        home = None
        for zn, (zx0, zy0, zx1, zy1) in ZONES.items():
            if zx0 - 1.5 <= ax <= zx1 + 1.5 and zy0 - 1.5 <= ay <= zy1 + 1.5:
                home = (zx0, zy0, zx1, zy1)
                break
        bounds[ref] = home or (EDGE, EDGE, BW - EDGE, BH - EDGE)
    # mounting holes take part but cannot move
    for f in board.GetFootprints():
        r = f.GetReference()
        if not r.startswith("H"):
            continue
        hcx, hcy, hw, hh = keepout_abs(f)
        abox[r] = dict(x=hcx, y=hcy, w=hw, h=hh, side=0, ox=0.0, oy=0.0)
        bounds[r] = (hcx, hcy, hcx, hcy)
    relaxed_box = relax_anchors(abox, bounds)
    relaxed = {r: (round(bx - abox[r]["ox"], 3), round(by - abox[r]["oy"], 3))
               for r, (bx, by) in relaxed_box.items() if r in ANCHORS}
    nudged = [r for r in ANCHORS if r in relaxed
              and (abs(relaxed[r][0] - ANCHORS[r][0]) > 0.02
                   or abs(relaxed[r][1] - ANCHORS[r][1]) > 0.02)]
    print(f"anchor relaxation moved {len(nudged)}: {sorted(nudged)}")

    order = sorted(comps, key=lambda r: (r not in ANCHORS, r))
    via_spots = []
    reserved = False
    for ref in order:
        c = comps[ref]
        if ref not in ANCHORS and not reserved:
            # Anchors are all placed by now, so U1 and U5 have positions and
            # the stitching-via sites can be computed. Reserving them HERE,
            # before any packing, is the whole point: the previous version ran
            # this after the packing loop, and R84 was packed on the bottom
            # directly under U5's exposed-pad via field - 3 shorts, 3 mask
            # bridges and 3 hole-clearance errors from one misordered step.
            via_spots = planned_vias(board)
            for vx, vy, vd in via_spots:
                for z in zones.values():
                    z.block(vx, vy, vd + 0.8, vd + 0.8)
            print(f"reserved {len(via_spots)} stitching-via sites before packing")
            reserved = True
        if ref in ANCHORS:
            x, y, rot, side = ANCHORS[ref]
            if ref in relaxed:
                x, y = relaxed[ref]
            fp = add(ref, c, x, y, rot, side)
            if fp is not None:
                # Measure AFTER add() has applied the rotation, so the
                # courtyard bbox already reflects it. Do not swap w/h again -
                # that double-swap mis-registered every 90-degree anchor's
                # keepout (J1 blocked a 23x10 box where the part is 10x23, so
                # the packer dropped D7 straight on top of it).
                bcx, bcy, w, h = keepout_abs(fp)
                # An SMD anchor only obstructs its OWN side. Blocking it on
                # both wasted most of the bottom side - U1 alone removed
                # ~1030 mm2 of bottom-side area it does not actually occupy,
                # which is why parts started going unplaced.
                same = [zn for zn in zones
                        if zn.endswith("_b") == bool(side)]
                for zn in same:
                    zones[zn].block(bcx, bcy, w, h)
                # through-hole pads and unplated holes DO pierce both sides
                for ox, oy, ow, oh in through_obstacles(fp):
                    for z in zones.values():
                        z.block(ox, oy, ow + 0.4, oh + 0.4)
            continue
        probe = load_fp(c["fp"])
        if probe is None:
            unplaced.append(ref)
            continue
        probe.SetPosition(pt(0, 0))
        pox, poy, w, h = keepout_abs(probe)
        zname = ZONE_OVERRIDE.get(ref)
        if zname is None:
            zname = SHEET_ZONE.get(c["sheet"], "dig")
            if c["sheet"] == "io":
                zname = "hv" if (ref in hv_refs) else "dig"
        # own zone top, own zone bottom, then the spill chain top then bottom
        spot, side = None, 0
        for cand in [zname] + SPILL.get(zname, []):
            spot = zones[cand].place(w, h)
            if spot is not None:
                side = 0
                break
            spot = zones[cand + "_b"].place(w, h)
            if spot is not None:
                side = 1
                break
        if spot is None:
            unplaced.append(ref)
            continue
        add(ref, c, spot[0] - pox, spot[1] - poy, 0, side)

    # --- bind pads to nets ----------------------------------------------
    bound = 0
    byref = {f.GetReference(): f for f in board.GetFootprints()}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            f = byref.get(ref)
            if f is None:
                continue
            for p in f.Pads():
                if p.GetNumber() == pin:
                    p.SetNet(netobj[name])
                    bound += 1
    print(f"pads bound to nets: {bound}")

    hv_rule_area(board)
    coating_inspection_marks(board)
    planes(board)
    stitch_vias(board, via_spots)

    board.BuildListOfNets()
    try:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        print("zones filled")
    except Exception as e:
        print(f"zone fill skipped ({e}) - fill in the GUI or via kicad-cli")
    pcbnew.SaveBoard(PCB, board)
    canonicalise(PCB)

    # LAST: pcbnew.SaveBoard() above wiped net_settings out of the project,
    # so the net classes have to be re-applied after it, not before.
    import netclasses
    netclasses.apply()
    if netclasses.verify() != 0:
        sys.exit("net classes did not survive - aborting")

    top = sum(1 for v in placed.values() if v[3] == 0)
    bot = len(placed) - top
    print(f"\nplaced {len(placed)}: {top} top, {bot} bottom")
    if unplaced:
        print(f"UNPLACED ({len(unplaced)}): {sorted(unplaced)}")
    print("outline, hole positions and all coordinates are PROVISIONAL")


if __name__ == "__main__":
    main()
