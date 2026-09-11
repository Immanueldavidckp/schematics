#!/usr/bin/env python3
"""Rip the exact copper items named by DRC clearance/shorting violations.

Segment-granular version of pcbroute_adopt's net rip: when a routing child
banks many good connections plus one fouling fragment, removing just that
fragment (never locked, never protected) keeps the gains. The caller re-runs
DRC afterwards and reverts if anything still fails - the gate stays absolute.

Usage: PYTHONPATH=tools python3 tools/scrub_fouls.py
Exit 0 with "SCRUBBED n=..." on success.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbgen                                                   # noqa: E402
import pcbnew                                                   # noqa: E402
from pcbgen import PCB, PROJ, canonicalise, _split_forms        # noqa: E402
from netclasses import HV, MV, RF                               # noqa: E402

PROTECTED = set(HV) | set(MV) | set(RF)

rpt = os.path.join(PROJ, ".scrub.json")
subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                "--format", "json", "-o", rpt, PCB], capture_output=True)
data = json.load(open(rpt))
os.unlink(rpt)

targets = []      # (x_mm, y_mm, netname) of violating Track items
for v in data.get("violations", []):
    if v.get("type") == "unconnected_items":
        continue
    for it in v.get("items", []):
        d = it.get("description", "")
        m = re.match(r"Track \[([^\]]*)\]", d)
        if not m or m.group(1) in PROTECTED:
            continue
        p = it.get("pos", {})
        targets.append((round(p.get("x", 0), 4), round(p.get("y", 0), 4),
                        m.group(1)))
if not targets:
    print("SCRUBBED n=0 (no rippable track violations)")
    sys.exit(0)

txt = open(PCB, encoding="utf-8").read()
b0 = txt.index("\n") + 1
b1 = txt.rstrip().rfind(")")
kept, n = [], 0
for fo in _split_forms(txt[b0:b1]):
    drop = False
    if fo.startswith("(segment") and "(locked yes)" not in fo:
        mnet = re.search(r'\(net "([^"]*)"\)', fo)
        ms = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", fo)
        me = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", fo)
        if mnet and ms and me:
            pts = [(float(ms.group(1)), float(ms.group(2))),
                   (float(me.group(1)), float(me.group(2)))]
            for tx, ty, tn in targets:
                if tn == mnet.group(1) and any(
                        abs(px - tx) < 0.01 and abs(py - ty) < 0.01
                        for px, py in pts):
                    drop = True
                    break
    if drop:
        n += 1
    else:
        kept.append(fo)
open(PCB, "w", encoding="utf-8").write(txt[:b0] + "".join(kept) + txt[b1:])

board = pcbnew.LoadBoard(PCB)
board.BuildListOfNets()
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
canonicalise(PCB)
print(f"SCRUBBED n={n} of {len(targets)} violation targets")
