#!/usr/bin/env python3
"""Remove exact duplicate track segments and vias from the board file.

FreeRouting session imports plus repeated adopt / finisher passes left
stacked copies of the same segment (one 5V0 segment on B.Cu appeared six
times). A duplicate has the same net, layer, width and endpoints (either
direction) as a segment already kept, or the same net, position, size and
drill as a via already kept; removing it cannot change connectivity or
clearances. Locked items are kept in preference to unlocked copies.

Run:  python3 tools/dedupe_tracks.py [board.kicad_pcb]
"""
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
from pcbgen import _split_forms                     # noqa: E402

PCB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(TOOLS), "telematics-tracker.kicad_pcb")


def key(fo):
    m = re.match(r"\(\s*(segment|via)\b", fo)
    if not m:
        return None
    net = re.search(r'\(net "([^"]*)"\)', fo)
    net = net.group(1) if net else ""
    if m.group(1) == "segment":
        a = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", fo)
        b = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", fo)
        w = re.search(r"\(width ([-\d.]+)\)", fo)
        lay = re.search(r'\(layer "([^"]+)"\)', fo)
        if not (a and b and w and lay):
            return None
        p1 = (round(float(a.group(1)), 4), round(float(a.group(2)), 4))
        p2 = (round(float(b.group(1)), 4), round(float(b.group(2)), 4))
        return ("seg", net, lay.group(1), round(float(w.group(1)), 4), min(p1, p2), max(p1, p2))
    at = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", fo)
    size = re.search(r"\(size ([-\d.]+)\)", fo)
    drill = re.search(r"\(drill ([-\d.]+)\)", fo)
    if not (at and size and drill):
        return None
    return ("via", net, round(float(at.group(1)), 4), round(float(at.group(2)), 4),
            round(float(size.group(1)), 4), round(float(drill.group(1)), 4))


def main():
    txt = open(PCB, encoding="utf-8").read()
    head_end = txt.index("\n") + 1
    tail_start = txt.rstrip().rfind(")")
    forms = _split_forms(txt[head_end:tail_start])
    # locked copies win: index keys of locked forms first
    locked = {}
    for i, fo in enumerate(forms):
        k = key(fo)
        if k is not None and "(locked yes)" in fo and k not in locked:
            locked[k] = i
    seen, kept, n_seg, n_via = set(), [], 0, 0
    for i, fo in enumerate(forms):
        k = key(fo)
        if k is None:
            kept.append(fo)
            continue
        if k in seen or (k in locked and locked[k] != i):
            if k[0] == "seg":
                n_seg += 1
            else:
                n_via += 1
            continue
        seen.add(k)
        kept.append(fo)
    open(PCB, "w", encoding="utf-8").write(txt[:head_end] + "".join(kept) + txt[tail_start:])
    print(f"DEDUPE removed {n_seg} duplicate segments and {n_via} duplicate vias")


if __name__ == "__main__":
    main()
