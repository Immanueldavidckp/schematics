#!/usr/bin/env python3
"""Apply hand-specified copper (tracks and vias) to the board, DRC-gated.

For connections no router can make because of a deliberate rule (the RF
corridor is a no-go for the LV finisher) or a geometry only a person would
pick. Each ROUTE is a named list of items; a route is kept only when the
board's DRC error count does not rise and its unconnected count falls,
otherwise the board is restored exactly.

  ("via", net, x, y, diameter, drill)
  ("trk", net, layer, x1, y1, x2, y2, width)
  ("del", net, layer, x1, y1, x2, y2)      remove that track (to re-lay it)
  ("delvia", net, x, y)                    remove that via
  ("padnet", ref, pad, net)                put a footprint pad on another net
                                           (after the same change in the schematic)
  ("rotate", ref, degrees)                 set a footprint's orientation
  ("value", ref, text)                     set a footprint's Value field
  ("move", ref, x, y)                      set a footprint's position

MANUAL_ACCEPT_EQUAL=1 keeps a route that leaves the unconnected count where it
was (for re-routes and pin swaps, where nothing new gets connected).

Run:  python3 tools/manual_routes.py [route-name ...]   (default: all)

MANUAL_JSON=file adds routes from a JSON file (island_via.py writes one);
routes named <group>_<k> are alternatives: once one of a group is kept the
rest are skipped. MANUAL_NO_SETTLE=1 skips the GND stitch after a near miss.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pcbnew

if not hasattr(pcbnew.SwigPyIterator, "next"):
    pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__

TOOLS = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import netclasses                                   # noqa: E402

PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")

ROUTES = {
    # GNSS antenna bias: L4 sits ON the GNSS CPWG line with its bias pad (2)
    # on the OUTBOARD side, between the line and the board edge; the bias
    # network (C83 / C85 / R90) is inboard. The finisher never routes in the
    # RF corridor, and the line's bend at y 45 closes the outboard channel, so
    # the link crosses UNDER the line on B.Cu (L2 is the CPWG reference, so a
    # B.Cu track below it does not touch the RF geometry). Via A sits 0.58 mm
    # from the line's copper (RF clearance 0.30) and ~1 mm from the edge.
    "gnss_bias": [
        ("trk", "/modem_rf/GNSS_BIAS", "F.Cu", 98.785, 38.000, 98.800, 39.000, 0.20),
        ("via", "/modem_rf/GNSS_BIAS", 98.800, 39.000, 0.45, 0.20),
        ("trk", "/modem_rf/GNSS_BIAS", "B.Cu", 98.800, 39.000, 95.800, 42.000, 0.20),
        ("trk", "/modem_rf/GNSS_BIAS", "B.Cu", 95.800, 42.000, 94.150, 43.650, 0.20),
        ("trk", "/modem_rf/GNSS_BIAS", "B.Cu", 94.150, 43.650, 94.150, 44.600, 0.20),
        ("via", "/modem_rf/GNSS_BIAS", 94.150, 44.600, 0.45, 0.20),
        ("trk", "/modem_rf/GNSS_BIAS", "F.Cu", 94.150, 44.600, 94.150, 45.570, 0.20),
    ],
    # SIM_DATA from the SIM ESD array D14 pad 1 to the eSIM holder X2 pad 3.
    # D14 sits directly above the USB ESD array D15 and pad 1 is walled east
    # by USB_DP_M and north by D14.2 (GND); the only way out is the 0.6 mm
    # channel between the two SOT arrays (D14 bottom edge 50.895, D15 top
    # 51.500, USB_VBUS via top 51.425), then down beside the eSIM holder and
    # west between its NC pad (bottom 52.15) and X2.4 (top 52.95). Every
    # clearance >= 0.15 mm (rule 0.127). The finisher's 0.1 mm grid has no
    # cell in the 0.05 mm window at y 51.12, which is why it never found it.
    "sim_data": [
        ("trk", "/modem_rf/SIM_DATA", "F.Cu", 88.250, 50.695, 88.250, 51.120, 0.15),
        ("trk", "/modem_rf/SIM_DATA", "F.Cu", 88.250, 51.120, 85.200, 51.120, 0.15),
        ("trk", "/modem_rf/SIM_DATA", "F.Cu", 85.200, 51.120, 85.200, 52.500, 0.15),
        ("trk", "/modem_rf/SIM_DATA", "F.Cu", 85.200, 52.500, 83.250, 52.500, 0.15),
        ("trk", "/modem_rf/SIM_DATA", "F.Cu", 83.250, 52.500, 83.175, 52.746, 0.15),
    ],
    # USIM_VDD to the SIM ESD array D14 pad 5, the only pad of the net left
    # out. The nearest USIM_VDD copper is the through via at (74.495, 49.400)
    # 12 mm west, and PWR_L3 between them is empty. A via next to the pad is
    # boxed in: the SIM_RST B.Cu track runs under the pad at x 86.05 (USB_VBUS
    # at 86.55 stops it moving east) and the Q14_B track crosses GND_L2 at
    # x 85.388, 0.66 mm apart - too narrow for a 0.45 via with 0.127 each side.
    # So Q14_B jogs 0.23 mm west on L2 for 1.4 mm (nothing else is on L2
    # there), the via sits at x 85.60 (0.14 to Q14_B, 0.15 to SIM_RST), and
    # L3 runs at y 50.045 (0.65 mm from the USB_DP_TP via) into the far via.
    "usim_vdd": [
        ("del", "/modem_rf/Q14_B", "GND_L2", 85.3878, 58.4545, 85.3878, 16.3427),
        ("trk", "/modem_rf/Q14_B", "GND_L2", 85.3878, 58.4545, 85.3878, 50.7500, 0.15),
        ("trk", "/modem_rf/Q14_B", "GND_L2", 85.3878, 50.7500, 85.1600, 50.5222, 0.15),
        ("trk", "/modem_rf/Q14_B", "GND_L2", 85.1600, 50.5222, 85.1600, 49.5678, 0.15),
        ("trk", "/modem_rf/Q14_B", "GND_L2", 85.1600, 49.5678, 85.3878, 49.3400, 0.15),
        ("trk", "/modem_rf/Q14_B", "GND_L2", 85.3878, 49.3400, 85.3878, 16.3427, 0.15),
        ("trk", "/modem_rf/USIM_VDD", "F.Cu", 86.450, 50.045, 85.600, 50.045, 0.15),
        ("via", "/modem_rf/USIM_VDD", 85.600, 50.045, 0.45, 0.20),
        ("trk", "/modem_rf/USIM_VDD", "PWR_L3", 85.600, 50.045, 75.200, 50.045, 0.15),
        ("trk", "/modem_rf/USIM_VDD", "PWR_L3", 75.200, 50.045, 74.495, 49.400, 0.15),
    ],
    # DO1_GATE: the stub from the via at (22.489, 43.339) ends between the two
    # pads of R5 and the rest of the net ends 1.1 mm east at (23.623, 42.074),
    # on the far side of R5.2. The only channel is the 0.44 mm strip between
    # the NET_STATUS_LED track at y 41.778 and the top of R5, and that track's
    # 45-degree drop into R5.1 closed its west end. Re-lay the drop square
    # (west to x 22.05, 0.15 clear of the NSL_BASE bend, then down into R5.1)
    # and DO1_GATE runs up the gap between the R5 pads and along the strip
    # at y 42.074 (0.146 to NET_STATUS_LED and to R5.2).
    "do1_gate": [
        ("del", "/mcu/NET_STATUS_LED", "F.Cu", 22.7772, 41.7782, 21.5625, 42.9929),
        ("del", "/mcu/NET_STATUS_LED", "F.Cu", 21.5625, 42.9929, 21.5625, 42.9950),
        ("trk", "/mcu/NET_STATUS_LED", "F.Cu", 22.7772, 41.7782, 22.0500, 41.7782, 0.15),
        ("trk", "/mcu/NET_STATUS_LED", "F.Cu", 22.0500, 41.7782, 22.0500, 42.5500, 0.15),
        ("trk", "/mcu/NET_STATUS_LED", "F.Cu", 22.0500, 42.5500, 21.5625, 42.9950, 0.15),
        ("trk", "DO1_GATE", "F.Cu", 22.4888, 42.7642, 22.4888, 42.0736, 0.15),
        ("trk", "DO1_GATE", "F.Cu", 22.4888, 42.0736, 23.6232, 42.0736, 0.15),
    ],
    # U2.8 (the MCU's VSSA pin) sits in a 0.3 mm sliver of F.Cu pour between
    # its neighbours, with NRST running under the pin row at y 33.895, the
    # OSC_OUT via and the 3V3A track above: no via fits in the sliver. The
    # via goes just past the pin tip at (36.14, 33.64), where B.Cu is
    # connected GND pour, joined to the pin by a 0.34 mm stub. Three nudges
    # make room: NRST steps down to y 34.071 under the via (0.149 to the
    # R1 pad), CANH on L3 jogs 0.02 mm south, and BOOT0 on L2 jogs 0.43 mm
    # south-west into the pour. Every gap >= 0.131 mm (rule 0.127).
    "u2_8": [
        ("del", "/mcu/NRST", "F.Cu", 35.6400, 33.6137, 35.9213, 33.8950),
        ("del", "/mcu/NRST", "F.Cu", 35.9213, 33.8950, 40.5514, 33.8950),
        ("trk", "/mcu/NRST", "F.Cu", 35.6400, 33.6137, 35.6400, 33.9000, 0.15),
        ("trk", "/mcu/NRST", "F.Cu", 35.6400, 33.9000, 35.8110, 34.0710, 0.15),
        ("trk", "/mcu/NRST", "F.Cu", 35.8110, 34.0710, 36.5710, 34.0710, 0.15),
        ("trk", "/mcu/NRST", "F.Cu", 36.5710, 34.0710, 36.7470, 33.8950, 0.15),
        ("trk", "/mcu/NRST", "F.Cu", 36.7470, 33.8950, 40.5514, 33.8950, 0.15),
        ("del", "/io/CANH", "PWR_L3", 42.0869, 34.0539, 32.6942, 34.0539),
        ("trk", "/io/CANH", "PWR_L3", 42.0869, 34.0539, 36.5921, 34.0539, 0.15),
        ("trk", "/io/CANH", "PWR_L3", 36.5921, 34.0539, 36.5730, 34.0730, 0.15),
        ("trk", "/io/CANH", "PWR_L3", 36.5730, 34.0730, 35.7070, 34.0730, 0.15),
        ("trk", "/io/CANH", "PWR_L3", 35.7070, 34.0730, 35.6879, 34.0539, 0.15),
        ("trk", "/io/CANH", "PWR_L3", 35.6879, 34.0539, 32.6942, 34.0539, 0.15),
        ("del", "/mcu/BOOT0", "GND_L2", 34.3700, 31.8793, 36.9750, 34.4843),
        ("trk", "/mcu/BOOT0", "GND_L2", 34.3700, 31.8793, 35.5277, 33.0370, 0.15),
        ("trk", "/mcu/BOOT0", "GND_L2", 35.5277, 33.0370, 35.5277, 33.6400, 0.15),
        ("trk", "/mcu/BOOT0", "GND_L2", 35.5277, 33.6400, 36.1400, 34.2523, 0.15),
        ("trk", "/mcu/BOOT0", "GND_L2", 36.1400, 34.2523, 36.7430, 34.2523, 0.15),
        ("trk", "/mcu/BOOT0", "GND_L2", 36.7430, 34.2523, 36.9750, 34.4843, 0.15),
        ("trk", "GND", "F.Cu", 36.1400, 33.3000, 36.1400, 33.6400, 0.20),
        ("via", "GND", 36.1400, 33.6400, 0.45, 0.20),
    ],
    # U2.47 (MCU VSS) is walled at its outer end by CAN1_TX and the 0.6 mm
    # 3V3 via, and past its inner end by I2C1_SDA / I2C1_SCL on GND_L2 (0.53
    # apart) and the BOOT0 via. The one clean spot is in the pad itself:
    # 0.135 to U2.46 and U2.48, 0.19 to C4.1 on B.Cu, 0.47 to I2C1_SDA, and
    # B.Cu there is connected pour (C4.2). Via in pad on a GND pin: order the
    # board with plugged (filled and capped) vias, or accept a little solder
    # wicking on this one ground pin. The pads are 0.72 mm apart, 7 um short
    # of 0.45 + 0.127 + PWR's 0.15, so .kicad_dru lets a GND via keep 0.127
    # to U2's PWR pads; and U2.48's 0.5 mm track leaves the 0.28 mm pad with
    # its end cap proud of the pad, so its first 0.57 mm is re-laid at the
    # pad's own 0.28 mm (0.183 to the via); the 0.05 mm stub from the pad
    # centre to that track is dropped (its cap reached the pad's top edge,
    # and the track now starts inside the pad).
    # C42.2 and C43.2, the GND pads of the two VBAT_MODEM bulk caps on the top
    # edge, sit in F.Cu pockets sealed by 3V3, Q13_B, VDD_EXT_1V8 and the
    # caps' own VBAT pads, and every through via there lands in the 2 mm
    # VBAT_MODEM copper on B.Cu that feeds the caps. That B.Cu branch only
    # serves these two caps, so it is re-laid to leave room for a GND via
    # into the L2 plane under each: the 3.5 mm C42.1-C43.1 link becomes
    # 1.4 mm wide and 0.31 mm higher (above the 0.5 mm VBAT_MODEM floor,
    # 0.235 to the new via, 0.24 to VDD_EXT_1V8), the parallel upper path
    # to (71.65, 2.85) goes (the lower 2 mm path carries the feed), and the
    # link from C43.1's via dips under C43.2 at full 2 mm width, >= 0.2
    # from the GND, Q14_B and VDD_EXT_1V8 vias around it.
    "c42_c43": [
        ("del", "/modem_rf/VBAT_MODEM", "B.Cu", 63.15, 2.75, 66.65, 2.75),
        ("del", "/modem_rf/VBAT_MODEM", "B.Cu", 66.65, 2.75, 66.75, 2.85),
        ("del", "/modem_rf/VBAT_MODEM", "B.Cu", 66.75, 2.85, 68.15, 2.85),
        ("del", "/modem_rf/VBAT_MODEM", "B.Cu", 68.15, 2.85, 69.35, 4.05),
        ("del", "/modem_rf/VBAT_MODEM", "B.Cu", 66.75, 2.85, 71.65, 2.85),
        ("del", "/modem_rf/VBAT_MODEM", "B.Cu", 71.65, 2.85, 73.15, 4.35),
        ("trk", "/modem_rf/VBAT_MODEM", "B.Cu", 63.15, 2.44, 66.65, 2.44, 1.4),
        ("trk", "/modem_rf/VBAT_MODEM", "B.Cu", 66.65, 2.75, 67.25, 2.75, 2.0),
        ("trk", "/modem_rf/VBAT_MODEM", "B.Cu", 67.25, 2.75, 68.05, 3.55, 2.0),
        ("trk", "/modem_rf/VBAT_MODEM", "B.Cu", 68.05, 3.55, 68.85, 3.55, 2.0),
        ("trk", "/modem_rf/VBAT_MODEM", "B.Cu", 68.85, 3.55, 69.35, 4.05, 2.0),
        ("via", "GND", 63.90, 3.60, 0.45, 0.20),
        ("via", "GND", 68.70, 2.00, 0.45, 0.20),
    ],
    "u2_47": [
        ("del", "3V3", "F.Cu", 31.2800, 31.2880, 31.2800, 31.2400),
        ("del", "3V3", "F.Cu", 31.2800, 31.2880, 30.8740, 31.6940),
        ("trk", "3V3", "F.Cu", 31.2800, 31.2880, 30.8740, 31.6940, 0.28),
        ("via", "GND", 31.3000, 30.7400, 0.45, 0.20),
    ],
}


if os.environ.get("MANUAL_JSON"):
    with open(os.environ["MANUAL_JSON"]) as _f:
        ROUTES.update(json.load(_f))


def group(name):
    head, _, k = name.rpartition("_")
    return head if head and k.isdigit() else name


def drc(tag):
    netclasses.ensure()
    rpt = os.path.join(PROJ, f".manual-{tag}.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "-o", rpt, PCB],
                   capture_output=True)
    txt = open(rpt).read()
    kinds = re.findall(r"^\[([a-z_]+)\]", txt, re.M)
    unc = sum(1 for k in kinds if k == "unconnected_items")
    return len(kinds) - unc, unc, txt


def mm(v):
    return int(round(v * 1e6))


SEG_RE = re.compile(r"\t\(segment\n(?:\t\t.*\n)*?\t\)\n")
VIA_RE = re.compile(r"\t\(via\n(?:\t\t.*\n)*?\t\)\n")


def drop_segments(dels):
    """Delete ("del", ...) tracks and ("delvia", ...) vias by editing the file
    text, like the other tools do: removing more than one item through
    pcbnew's Remove() in one session corrupts the board object (it segfaults
    in Zones())."""
    txt = open(PCB, encoding="utf-8").read()
    for it in [d for d in dels if d[0] == "delvia"]:
        _, net, x, y = it
        hits = []
        for m in VIA_RE.finditer(txt):
            blk = m.group(0)
            at = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", blk)
            if f'(net "{net}")' in blk and at and abs(float(at.group(1)) - x) < 6e-4 and abs(float(at.group(2)) - y) < 6e-4:
                hits.append(m.span())
        if len(hits) != 1:
            sys.exit(f"delvia: {len(hits)} vias match {net} ({x}, {y})")
        a, z = hits[0]
        txt = txt[:a] + txt[z:]
    for _, net, layer, x1, y1, x2, y2 in [d for d in dels if d[0] == "del"]:
        std = re.search(rf'\(\d+ "([^"]+)" \w+ "{re.escape(layer)}"\)', txt)
        layers = {layer} | ({std.group(1)} if std else set())
        want = [(x1, y1), (x2, y2)]
        hits = []
        for m in SEG_RE.finditer(txt):
            blk = m.group(0)
            ly = re.search(r'\(layer "([^"]+)"\)', blk)
            if f'(net "{net}")' not in blk or not ly or ly.group(1) not in layers:
                continue
            s = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
            e = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
            pts = [(float(s.group(1)), float(s.group(2))), (float(e.group(1)), float(e.group(2)))]
            if all(any(abs(p[0] - w[0]) < 6e-4 and abs(p[1] - w[1]) < 6e-4 for w in want) for p in pts):
                hits.append(m.span())
        if len(hits) != 1:
            sys.exit(f"del: {len(hits)} segments match {net} {layer} {want}")
        a, z = hits[0]
        txt = txt[:a] + txt[z:]
    with open(PCB, "w", encoding="utf-8") as f:
        f.write(txt)


def apply(items):
    dels = [it for it in items if it[0] in ("del", "delvia")]
    if dels:
        drop_segments(dels)
    b = pcbnew.LoadBoard(PCB)
    for it in items:
        if it[0] in ("del", "delvia"):
            continue
        if it[0] == "padnet":
            _, ref, pad, netname = it
            f = [x for x in b.GetFootprints() if x.GetReference() == ref][0]
            p = [x for x in f.Pads() if x.GetNumber() == pad][0]
            n = b.FindNet(netname)
            if n is None:
                sys.exit(f"no net {netname}")
            p.SetNet(n)
            continue
        if it[0] == "rotate":
            _, ref, deg = it
            f = [x for x in b.GetFootprints() if x.GetReference() == ref][0]
            f.SetOrientationDegrees(deg)
            continue
        if it[0] == "value":
            _, ref, text = it
            f = [x for x in b.GetFootprints() if x.GetReference() == ref][0]
            f.SetValue(text)
            continue
        if it[0] == "move":
            _, ref, x, y = it
            f = [x for x in b.GetFootprints() if x.GetReference() == ref][0]
            f.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            continue
        net = b.FindNet(it[1])
        if net is None:
            sys.exit(f"no net {it[1]}")
        if it[0] == "via":
            _, _, x, y, d, dr = it
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(mm(d))
            v.SetDrill(mm(dr))
            v.SetNet(net)
            b.Add(v)
        else:
            _, _, layer, x1, y1, x2, y2, w = it
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
            t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
            t.SetWidth(mm(w))
            t.SetLayer(b.GetLayerID(layer))
            t.SetNet(net)
            b.Add(t)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b, True)


def main():
    names = sys.argv[1:] or list(ROUTES)
    e0, u0, _ = drc("before")
    print(f"before: errors {e0}, unconnected {u0}")
    done = set()
    for name in names:
        if group(name) in done:
            continue
        backup = PCB + ".manual-backup"
        shutil.copyfile(PCB, backup)
        apply(ROUTES[name])
        e, u, txt = drc(name)
        if e <= e0 and u0 <= u <= u0 + 1 and not os.environ.get("MANUAL_NO_SETTLE"):
            # the new copper may have split a GND pour: stitch, measure again
            subprocess.run([sys.executable, os.path.join(TOOLS, "stitch_gnd.py")],
                           capture_output=True, text=True, timeout=1500,
                           env=dict(os.environ, PYTHONPATH=TOOLS), cwd=PROJ)
            e, u, txt = drc(name + "-settle")
        ok = e <= e0 and (u < u0 or (u == u0 and os.environ.get("MANUAL_ACCEPT_EQUAL")))
        if ok:
            print(f"KEPT {name}: unconnected {u0} -> {u}, errors {e}")
            u0 = u
            done.add(group(name))
        else:
            shutil.copyfile(backup, PCB)
            new = [l for l in txt.splitlines() if l.startswith("[") and "unconnected" not in l][:6]
            print(f"REJECTED {name}: errors {e0} -> {e}, unconnected {u0} -> {u}")
            for l in new:
                print("   ", l)
        os.unlink(backup)
    print(f"MANUAL_RESULT unconnected={u0} errors={e0}")


if __name__ == "__main__":
    main()
