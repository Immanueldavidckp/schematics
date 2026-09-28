#!/usr/bin/env python3
"""Apply hand-specified copper (tracks and vias) to the board, DRC-gated.

For connections no router can make because of a deliberate rule (the RF
corridor is a no-go for the LV finisher) or a geometry only a person would
pick. Each ROUTE is a named list of items; a route is kept only when the
board's DRC error count does not rise and its unconnected count falls,
otherwise the board is restored exactly.

  ("via", net, x, y, diameter, drill)
  ("trk", net, layer, x1, y1, x2, y2, width)

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


def apply(items):
    b = pcbnew.LoadBoard(PCB)
    for it in items:
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
