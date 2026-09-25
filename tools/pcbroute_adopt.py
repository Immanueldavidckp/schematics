#!/usr/bin/env python3
"""Adopt the autorouted scratch board as the real board, after cleaning it.

Steps:
  1. DRC the scratch. Rip the EXACT copper fragments named by every ERROR
     violation (segments whose start point, or vias whose centre, sits at a
     reported violation position) - never locked, never protected copper.
     Repeat until the report is clean or nothing rippable remains.
  2. Only then fall back to the old behaviour for what is still violating:
     rip the whole net's UNLOCKED copper. The protected RF/HV/MV nets are
     always ripped in full - the autorouter must own nothing there.
     (Measured before this change: a single 0.15 mm foul on a 3V3 stub cost
     the entire 3V3, 5V0, SYS and VBAT_MODEM nets on every cycle - 50 to 70
     connections thrown away per adopt.)
  3. Write the result over the real board file, refill zones, canonicalise.
  4. DRC the adopted board and repeat the fragment-first / net-second rip
     there; the non-ratsnest error count must reach 0 because the adopted
     board becomes the LV finisher's baseline.

All ripping is TEXTUAL on the .kicad_pcb s-expression: board.Remove()
crashes pcbnew at scale (SKILL.md) and text surgery is deterministic.

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
ITEM = re.compile(r"@\(([\d.]+) mm, ([\d.]+) mm\): (Track|Via) \[([^\]]*)\]")


def drc(path, out):
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "-o", out, path], capture_output=True)
    return open(out).read()


def violations(text):
    """[(type, [(x, y, kind, net), ...], [net names])] for non-ratsnest errors."""
    out = []
    for block in re.split(r"\n(?=\[)", text):
        m = re.match(r"\[([a-z_]+)\]", block)
        if not m or m.group(1) == "unconnected_items":
            continue
        items = [(float(x), float(y), k, n) for x, y, k, n in ITEM.findall(block)]
        nets = [n for n in re.findall(r"\[([^\]\[]*)\]", block)[1:]
                if n and n != "<no net>"]
        out.append((m.group(1), items, nets))
    return out


def _forms(path):
    txt = open(path, encoding="utf-8").read()
    head = txt[:txt.index("\n") + 1]
    body = txt[txt.index("\n") + 1:txt.rstrip().rfind(")")]
    tail = txt[txt.rstrip().rfind(")"):]
    return head, _split_forms(body), tail


def rip_fragments(path, viols):
    """Remove the unlocked, unprotected segment/via forms that sit exactly at
    a reported violation position. Returns the number of forms removed."""
    targets = [(x, y, n) for _t, items, _n in viols for x, y, _k, n in items
               if n not in PROTECTED]
    if not targets:
        return 0
    head, forms, tail = _forms(path)
    kept, ripped = [], 0
    for f in forms:
        tag = re.match(r"\(\s*([A-Za-z_0-9]+)", f).group(1)
        drop = False
        if tag in ("segment", "via") and "(locked yes)" not in f:
            mnet = re.search(r'\(net "([^"]*)"\)', f)
            pts = re.findall(r"\((?:start|end|at) ([-\d.]+) ([-\d.]+)\)", f)
            if mnet and pts:
                for tx, ty, tn in targets:
                    if tn == mnet.group(1) and any(
                            abs(float(px) - tx) < 0.01 and abs(float(py) - ty) < 0.01
                            for px, py in pts):
                        drop = True
                        break
        if drop:
            ripped += 1
        else:
            kept.append(f)
    open(path, "w", encoding="utf-8").write(head + "".join(kept) + tail)
    return ripped


def rip_nets(path, nets):
    """Remove every unlocked segment/via of the named nets."""
    head, forms, tail = _forms(path)
    kept, ripped = [], 0
    for f in forms:
        tag = re.match(r"\(\s*([A-Za-z_0-9]+)", f).group(1)
        if tag in ("segment", "via") and "(locked yes)" not in f:
            m = re.search(r'\(net "([^"]*)"\)', f)
            if m and m.group(1) in nets:
                ripped += 1
                continue
        kept.append(f)
    open(path, "w", encoding="utf-8").write(head + "".join(kept) + tail)
    return ripped


def refill(path):
    import pcbnew
    board = pcbnew.LoadBoard(path)
    board.BuildListOfNets()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board, True)


def clean(path, rpt, label, max_frag=6, max_net=3, canon=False):
    """Fragment-first, net-second cleaning loop. Returns remaining error count."""
    errs = None
    for it in range(max_frag):
        viols = violations(drc(path, rpt))
        errs = len(viols)
        kinds = {}
        for t, _i, _n in viols:
            kinds[t] = kinds.get(t, 0) + 1
        print(f"{label} DRC (frag iter {it}): errors={errs} {kinds}")
        if not errs:
            return 0
        n = rip_fragments(path, viols)
        print(f"  ripped {n} violating fragment(s)")
        if not n:
            break
        if canon:
            refill(path)
            canonicalise(path)
    for it in range(max_net):
        viols = violations(drc(path, rpt))
        errs = len(viols)
        if not errs:
            return 0
        nets = {n for _t, _i, ns in viols for n in ns} - PROTECTED
        present = set(re.findall(r'\(net "([^"]*)"\)', open(path, encoding="utf-8").read()))
        nets &= present
        n = rip_nets(path, nets)
        print(f"{label} DRC (net iter {it}): errors={errs}; ripping whole nets "
              f"{sorted(nets)} - {n} forms")
        if not n:
            print("  violations remain on LOCKED or protected copper - placement problem")
            break
        if canon:
            refill(path)
            canonicalise(path)
    return len(violations(drc(path, rpt)))


def main():
    rpt = os.path.join(PROJ, "adopt-drc.rpt")
    # 1+2: clean the scratch (fragments first), then always rip protected nets
    clean(SCRATCH, rpt, "scratch", canon=False)
    n = rip_nets(SCRATCH, PROTECTED)
    print(f"protected nets: {n} unlocked form(s) ripped")
    # 3: adopt
    head, forms, tail = _forms(SCRATCH)
    open(PCB, "w", encoding="utf-8").write(head + "".join(forms) + tail)
    refill(PCB)
    canonicalise(PCB)
    # 4: the adopted board must be error-free
    errs = clean(PCB, rpt, "adopted", canon=True)
    os.unlink(rpt)
    if errs:
        print("ADOPT_BASELINE_NOT_CLEAN")
        sys.exit(2)
    print("ADOPT_OK")


if __name__ == "__main__":
    main()
