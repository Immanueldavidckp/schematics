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

GAP = 0.60          # mm between courtyards when packing
EDGE = 1.0          # mm keep-in from the board edge

# ---------------------------------------------------------------- floorplan
# (x0, y0, x1, y1) in mm. Zones are packed independently, top side first.
ZONES = {
    # HV: connector end. Everything at up to 100 V lives left of HV_X.
    "hv":      (EDGE, EDGE, HV_X - 0.75, BH - EDGE),
    # digital centre
    "dig":     (HV_X + 0.75, 17.0, 45.0, BH - EDGE),
    # power block, top of the digital end, adjacent to the HV boundary so the
    # VIN_B feed stays short
    "pwr":     (HV_X + 0.75, EDGE, 45.0, 16.5),
    # modem / RF end
    "rf":      (45.5, EDGE, BW - EDGE, BH - EDGE),
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
    # Amendment (a): the U5 / D16 / C73-C74 hot loop packed tight, and
    # amendment (b): L1 at the left end, furthest from the RF edge.
    "L1":  (27.5, 8.5, 0, 0),
    "U5":  (35.5, 4.5, 0, 0),
    "D16": (35.5, 9.5, 0, 0),
    "C73": (31.0, 3.0, 0, 0),
    "C74": (31.0, 5.5, 0, 0),
    "U6":  (41.0, 5.0, 0, 0),
    "U9":  (41.0, 12.0, 0, 0),
    # J2 must sit ON an edge: it is a wire-to-board JST for the replaceable
    # battery pack, and its lead has to leave the board. The first pass put it
    # mid-board next to U2, which the 3D render caught.
    "J2":  (40.0, 55.0, 0, 0),

    # --- digital --------------------------------------------------------
    "U2":  (29.0, 25.0, 0, 0),
    # Amendment (c) / F-18: U3 hard against the provisional 5th M3 at (27,52).
    "U3":  (31.5, 51.5, 0, 0),
    "U7":  (24.0, 33.0, 0, 0),
    "U4":  (24.5, 43.5, 0, 0),
    "U8":  (41.0, 24.0, 0, 0),
}

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

# Refs that belong in a different zone than their sheet implies. The io sheet
# is a mix: the CAN transceiver side and the DO gate drive are low voltage and
# belong in the digital zone, while the DI/DO/divider front ends are HV.
ZONE_OVERRIDE = {
    "U4": "dig", "L2": "hv", "D3": "hv",
    "TP25": "hv", "TP26": "hv", "TP23": "hv",
    "TP27": "dig", "TP28": "dig", "TP24": "rf",
}

POWER_POURS = [
    # (net, layer, x0, y0, x1, y1) on L3
    ("5V0", "In2.Cu", HV_X + 0.75, EDGE, 45.0, 17.0),
    ("SYS", "In2.Cu", HV_X + 0.75, 17.0, 45.0, 34.0),
    ("3V3", "In2.Cu", HV_X + 0.75, 34.0, 45.0, BH - EDGE),
]


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


_sizecache = {}


def size_of(fp, fpid=None):
    if fpid is not None and fpid in _sizecache:
        return _sizecache[fpid]
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if bb.GetWidth() == 0:
        bb = fp.GetBoundingBox(False, False)
    wh = (pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))
    if fpid is not None:
        _sizecache[fpid] = wh
    return wh


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


def stitch_vias(board):
    gnd = get_net(board, "GND")
    u1 = None
    for f in board.GetFootprints():
        if f.GetReference() == "U1":
            u1 = f
            break
    if u1 is None:
        print("U1 not placed - no stitching vias")
        return
    made = 0

    def via(pos, dia, drill):
        nonlocal made
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pos)
        v.SetWidth(mm(dia))
        v.SetDrill(mm(drill))
        v.SetNet(gnd)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        board.Add(v)
        made += 1

    # 0.50/0.30 gives exactly the 0.100 mm minimum annular ring; 0.45 gave
    # 0.075 and failed board setup. The fence pads are 0.8 mm tall, so 0.50 is
    # also the largest via that keeps copper either side of the barrel.
    for group, dia, drill in ((LATTICE, 0.60, 0.30),
                              (FENCE, 0.50, 0.30),
                              (PERIM, 0.50, 0.30)):
        for num in group:
            p = u1.FindPadByNumber(num)
            if p is None:
                continue
            via(p.GetPosition(), dia, drill)
    print(f"F-9 stitching vias placed: {made} "
          f"({len(LATTICE)} lattice, {len(FENCE)} RF fence, "
          f"{len(PERIM)} perimeter/audio)")


def main():
    if not os.path.exists(NETLIST):
        sys.exit(f"missing {NETLIST} - run:\n  kicad-cli sch export netlist "
                 f"--format kicadsexpr --output nl.net telematics-tracker.kicad_sch")
    comps, nets = parse_netlist(NETLIST)
    print(f"netlist: {len(comps)} components, {len(nets)} named nets")

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
        if re.match(r"^(R|C|L|TP|JP)\d+$", ref):
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

    order = sorted(comps, key=lambda r: (r not in ANCHORS, r))
    for ref in order:
        c = comps[ref]
        if ref in ANCHORS:
            x, y, rot, side = ANCHORS[ref]
            fp = add(ref, c, x, y, rot, side)
            if fp is not None:
                # Measure AFTER add() has applied the rotation, so the
                # courtyard bbox already reflects it. Do not swap w/h again -
                # that double-swap mis-registered every 90-degree anchor's
                # keepout (J1 blocked a 23x10 box where the part is 10x23, so
                # the packer dropped D7 straight on top of it).
                w, h = size_of(fp)
                for z in zones.values():
                    z.block(x, y, w, h)
            continue
        probe = load_fp(c["fp"])
        if probe is None:
            unplaced.append(ref)
            continue
        w, h = size_of(probe, c["fp"])
        zname = ZONE_OVERRIDE.get(ref) or SHEET_ZONE.get(c["sheet"], "dig")
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
        add(ref, c, spot[0], spot[1], 0, side)

    # --- bind pads to nets ----------------------------------------------
    bound = 0
    byref = {f.GetReference(): f for f in board.GetFootprints()}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            f = byref.get(ref)
            if f is None:
                continue
            p = f.FindPadByNumber(pin)
            if p is not None:
                p.SetNet(netobj[name])
                bound += 1
    print(f"pads bound to nets: {bound}")

    planes(board)
    stitch_vias(board)

    board.BuildListOfNets()
    try:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        print("zones filled")
    except Exception as e:
        print(f"zone fill skipped ({e}) - fill in the GUI or via kicad-cli")
    pcbnew.SaveBoard(PCB, board)
    canonicalise(PCB)

    top = sum(1 for v in placed.values() if v[3] == 0)
    bot = len(placed) - top
    print(f"\nplaced {len(placed)}: {top} top, {bot} bottom")
    if unplaced:
        print(f"UNPLACED ({len(unplaced)}): {sorted(unplaced)}")
    print("outline, hole positions and all coordinates are PROVISIONAL")


if __name__ == "__main__":
    main()
