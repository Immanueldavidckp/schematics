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

Run:  python3 tools/manual_routes.py [route-name ...]   (default: all)
"""
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
}


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


def drop_segments(dels):
    """Delete ("del", ...) tracks by editing the file text, like the other
    tools do: removing more than one item through pcbnew's Remove() in one
    session corrupts the board object (it segfaults in Zones())."""
    txt = open(PCB, encoding="utf-8").read()
    for _, net, layer, x1, y1, x2, y2 in dels:
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
    dels = [it for it in items if it[0] == "del"]
    if dels:
        drop_segments(dels)
    b = pcbnew.LoadBoard(PCB)
    for it in items:
        net = b.FindNet(it[1])
        if net is None:
            sys.exit(f"no net {it[1]}")
        if it[0] == "del":
            continue
        elif it[0] == "via":
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
    for name in names:
        backup = PCB + ".manual-backup"
        shutil.copyfile(PCB, backup)
        apply(ROUTES[name])
        e, u, txt = drc(name)
        if e <= e0 and u0 <= u <= u0 + 1:
            # the new copper may have split a GND pour: stitch, measure again
            subprocess.run([sys.executable, os.path.join(TOOLS, "stitch_gnd.py")],
                           capture_output=True, text=True, timeout=1500,
                           env=dict(os.environ, PYTHONPATH=TOOLS), cwd=PROJ)
            e, u, txt = drc(name + "-settle")
        if e <= e0 and u < u0:
            print(f"KEPT {name}: unconnected {u0} -> {u}, errors {e}")
            u0 = u
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
