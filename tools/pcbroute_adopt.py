#!/usr/bin/env python3
"""Adopt the autorouted scratch board as the real board, after cleaning it.

Steps:
  1. DRC the scratch. Every net named in an ERROR violation (anything but
     unconnected_items) is marked for rip, and the protected RF/HV/MV nets
     are always marked - the autorouter must own nothing there.
  2. Rip those nets' UNLOCKED copper TEXTUALLY (top-level segment/via forms).
     board.Remove() crashes pcbnew at scale (SKILL.md); text surgery on the
     s-expression file is deterministic and cannot crash the library.
  3. Write the result over the real board file, refill zones, canonicalise.
  4. DRC the adopted board - the non-ratsnest error count must be 0, because
     it becomes the LV finisher's baseline.

Run:  PYTHONPATH=tools python3 tools/pcbroute_adopt.py
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbgen import PROJ, PCB, canonicalise, _split_forms   # noqa: E402
from netclasses import HV, MV, RF                          # noqa: E402

SCRATCH = os.path.join(PROJ, "autoroute-scratch.kicad_pcb")
PROTECTED = set(HV) | set(MV) | set(RF)


def drc(path, out):
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "-o", out, path], capture_output=True)
    return open(out).read()


def main():
    rpt = os.path.join(PROJ, "adopt-drc.rpt")
    text = drc(SCRATCH, rpt)

    ripnets = set(PROTECTED)
    block = []
    for line in text.splitlines():
        if line.startswith("["):
            block = [line]
        elif line.startswith(("    @", "    ;", "    Rule", "    Local")):
            block.append(line)
        if block and not block[0].startswith("[unconnected_items]"):
            for m in re.finditer(r"\[([^]\[]+)\]", line):
                nm = m.group(1)
                if nm and not nm.islower() or "/" in nm:
                    ripnets.add(nm)
    # the regexy net harvest can catch violation-type tags; they are all
    # lowercase_with_underscores and cannot collide with net names on this
    # board except literal rails - filter against the board's net table below.

    txt = open(SCRATCH, encoding="utf-8").read()
    body = txt[txt.index("\n") + 1:txt.rstrip().rfind(")")]
    forms = _split_forms(body)
    netno = {}
    for f in forms:
        m = re.match(r'\(\s*net (\d+) "([^"]*)"', f)
        if m:
            netno[int(m.group(1))] = m.group(2)
    ripnets &= (set(netno.values()) | PROTECTED)

    kept, ripped = [], 0
    for f in forms:
        tag = re.match(r"\(\s*([A-Za-z_0-9]+)", f).group(1)
        if tag in ("segment", "via") and "(locked yes)" not in f:
            m = re.search(r"\(net (\d+)\)", f)
            if m and netno.get(int(m.group(1)), "") in ripnets:
                ripped += 1
                continue
        kept.append(f)
    print(f"ripping nets ({len(ripnets)} incl. protected): "
          f"{sorted(n for n in ripnets if n not in PROTECTED)}")
    print(f"forms ripped: {ripped}")

    head = txt[:txt.index("\n") + 1]
    tail = txt[txt.rstrip().rfind(")"):]
    open(PCB, "w", encoding="utf-8").write(head + "".join(kept) + tail)

    import pcbnew
    board = pcbnew.LoadBoard(PCB)
    board.BuildListOfNets()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    canonicalise(PCB)

    text2 = drc(PCB, rpt)
    kinds = {}
    for k in re.findall(r"^\[([a-z_]+)\]", text2, re.M):
        kinds[k] = kinds.get(k, 0) + 1
    os.unlink(rpt)
    print(f"adopted board DRC: {kinds}")
    errs = sum(v for k, v in kinds.items() if k != "unconnected_items")
    if errs:
        print("ADOPT_BASELINE_NOT_CLEAN")
        sys.exit(2)
    print("ADOPT_OK")


if __name__ == "__main__":
    main()
