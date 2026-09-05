#!/usr/bin/env python3
"""Measure the closest LV approach for every HV net, and log it.

Step 2 of the routing plan requires the HV nets to be hand-routed at >= 1.5 mm
from LV copper AND for that separation to be measured, not asserted. Anything
under 1.50 mm must be inside an approved package exception in
telematics-tracker.kicad_dru - the table is what makes that checkable.

Layer-aware: two pads on opposite sides of 1.6 mm of FR4 are not close, and an
earlier hand measurement wrongly reported 0.000 mm for exactly that case.
Intra-component pairs are skipped - they are governed by the <= 40 V / package
exceptions, per the permanently split CHECK 3 metric.

Run:  PYTHONPATH=tools python3 tools/hv_measure.py
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netclasses import HV                                    # noqa: E402
from pcbgen import PCB                                       # noqa: E402

mm = pcbnew.ToMM
b = pcbnew.LoadBoard(PCB)

def gap(a, c):          # bbox edge-to-edge distance, 0 if overlapping
    dx = max(a[0] - c[2], c[0] - a[2], 0.0)
    dy = max(a[1] - c[3], c[1] - a[3], 0.0)
    return (dx*dx + dy*dy) ** 0.5

items = []
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox()
        items.append((p.GetNetname(), f.GetReference(), p.GetNumber(),
                      (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())),
                      frozenset(p.GetLayerSet().CuStack())))
for t in b.GetTracks():
    bb = t.GetBoundingBox()
    kind = "via" if isinstance(t, pcbnew.PCB_VIA) else "track"
    items.append((t.GetNetname(), "", kind,
                  (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())),
                  frozenset(t.GetLayerSet().CuStack())))

lv = [x for x in items if x[0] and x[0] not in HV and x[0] != "GND"]
print(f"{'HV net':24} {'closest LV':>10}   closest pair")
rows = []
for net in HV:
    hv = [x for x in items if x[0] == net]
    if not hv:
        continue
    best = (1e9, "", "")
    for n1, r1, p1, bb1, l1 in hv:
        for n2, r2, p2, bb2, l2 in lv:
            if not (l1 & l2):
                continue
            if r1 and r2 and r1 == r2:      # same package: intra-component
                continue
            d = gap(bb1, bb2)
            if d < best[0]:
                best = (d, f"{r1}.{p1}" if r1 else f"{net} {p1}",
                        f"{r2}.{p2}" if r2 else f"{n2} {p2}")
    rows.append((net,) + best)
for net, d, a, c in sorted(rows, key=lambda r: r[1]):
    print(f"{net:24} {d:9.3f}   {a} <-> {c}{'   << under 1.50' if d < 1.5 else ''}")
