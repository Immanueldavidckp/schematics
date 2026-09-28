#!/usr/bin/env python3
"""Give the GND_L2 plane back to GND in a window: remove every other net's
unlocked track segments on GND_L2 there, then refill.

FreeRouting used GND_L2 as a signal layer; under U2 the plane fell apart and
the MCU's GND pins were left as sealed islands with no plane to reach. After
this rip the nets that lost their L2 segments are re-routed by the finisher
on F.Cu / B.Cu / PWR_L3 (LV_L3=1), and the GND islands stitch down to the
restored plane. Vias are kept (they are through-hole and still carry the
other layers).

Run:  python3 tools/l2_reclaim.py x0 y0 x1 y1
"""
import os
import re
import sys

import pcbnew

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import netclasses                                   # noqa: E402
from pcbgen import _split_forms                     # noqa: E402

PCB = os.path.join(os.path.dirname(TOOLS), "telematics-tracker.kicad_pcb")
x0, y0, x1, y1 = map(float, sys.argv[1:5])
KEEP = {"GND"} | set(netclasses.HV) | set(netclasses.MV) | set(netclasses.RF)

txt = open(PCB, encoding="utf-8").read()
head_end = txt.index("\n") + 1
tail_start = txt.rstrip().rfind(")")
kept, nets, n = [], {}, 0
for fo in _split_forms(txt[head_end:tail_start]):
    drop = False
    if re.match(r"\(\s*segment\b", fo) and '(layer "GND_L2")' in fo and "(locked yes)" not in fo:
        net = re.search(r'\(net "([^"]*)"\)', fo)
        net = net.group(1) if net else ""
        if net not in KEEP:
            a = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", fo)
            b = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", fo)
            if a and b:
                ax, ay, bx, by = map(float, (a.group(1), a.group(2), b.group(1), b.group(2)))
                k = max(1, int(max(abs(bx - ax), abs(by - ay)) / 0.1))
                drop = any(x0 <= ax + (bx - ax) * i / k <= x1 and y0 <= ay + (by - ay) * i / k <= y1
                           for i in range(k + 1))
                if drop:
                    nets[net] = nets.get(net, 0) + 1
    if drop:
        n += 1
    else:
        kept.append(fo)
open(PCB, "w", encoding="utf-8").write(txt[:head_end] + "".join(kept) + txt[tail_start:])

b = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b, True)
print(f"L2_RECLAIM removed {n} GND_L2 segments of {len(nets)} nets in "
      f"x {x0}..{x1} y {y0}..{y1}: {dict(sorted(nets.items(), key=lambda kv: -kv[1]))}")
