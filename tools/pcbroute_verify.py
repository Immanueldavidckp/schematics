#!/usr/bin/env python3
"""Verify a FreeRouting import against the standing import rules.

Compares the SCRATCH board (autoroute result) against the real board and
produces the step-4 report: completion %, violations by type, per-net
unrouted list, plus the standing-policy checks:

  rule 2: every locked item survives byte-identical (position, width, layer,
          net) - the autorouter must not have touched the hand-routed copper;
          and no autorouter copper on any RF/HV/MV net.
  rule 5: thermal via counts under U1 paddle and U5 EP.

Run:  PYTHONPATH=tools python3 tools/pcbroute_verify.py
"""
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbgen import PROJ, PCB                                 # noqa: E402
from netclasses import HV, MV, RF                            # noqa: E402

SCRATCH = os.path.join(PROJ, "autoroute-scratch.kicad_pcb")
to_mm = pcbnew.ToMM


def sig(t):
    if isinstance(t, pcbnew.PCB_VIA):
        return ("via", t.GetNetname(), t.GetPosition().x, t.GetPosition().y,
                t.GetWidth(), t.GetDrillValue())
    return ("trk", t.GetNetname(), t.GetStart().x, t.GetStart().y,
            t.GetEnd().x, t.GetEnd().y, t.GetWidth(), t.GetLayer())


def main():
    base = pcbnew.LoadBoard(PCB)
    scr = pcbnew.LoadBoard(SCRATCH)

    # ---- rule 2: locked copper survives, byte-identical -----------------
    base_locked = {sig(t) for t in base.GetTracks() if t.IsLocked()}
    scr_all = [t for t in scr.GetTracks()]
    scr_sigs = {sig(t) for t in scr_all}
    missing = base_locked - scr_sigs
    print(f"locked items on the real board: {len(base_locked)}")
    print(f"  present identically on scratch: {len(base_locked) - len(missing)}")
    if missing:
        print(f"  MISSING/ALTERED: {len(missing)}")
        for m in sorted(missing)[:10]:
            print(f"    {m[0]} {m[1]}")

    # ---- rule 2b/4: no autorouter copper on protected nets --------------
    protected = set(HV) | set(MV) | set(RF)
    new_items = [t for t in scr_all if sig(t) not in base_locked
                 and not t.IsLocked()]
    bad = [t for t in new_items if t.GetNetname() in protected]
    print(f"autorouter items added: {len(new_items)}")
    if bad:
        print(f"  ON PROTECTED NETS (must be zero): {len(bad)}")
        for t in bad[:10]:
            print(f"    {t.GetNetname()} at "
                  f"({to_mm(t.GetPosition().x):.2f},{to_mm(t.GetPosition().y):.2f})")
    else:
        print("  none on RF/HV/MV nets")

    # ---- completion + violations (DRC on scratch) ------------------------
    rpt = os.path.join(PROJ, "autoroute-scratch-drc.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--severity-warning", "-o", rpt, SCRATCH],
                   capture_output=True)
    text = open(rpt).read()
    kinds = Counter(re.findall(r"^\[([a-z_]+)\]", text, re.M))
    print("\nDRC on scratch:")
    for k, n in kinds.most_common():
        print(f"  {n:5} {k}")

    # per-net unrouted list
    unrouted = defaultdict(int)
    for m in re.finditer(r"\[unconnected_items\].*?\n(.*?)\n(.*?)\n", text):
        nets = re.findall(r"\[([^]\s]+)\]", m.group(0) + m.group(1) + m.group(2))
        for n in set(nets):
            unrouted[n] += 1
    conn = scr.GetConnectivity()
    total_ratsnest = kinds.get("unconnected_items", 0)
    base_unconn = None
    print(f"\nunconnected items: {total_ratsnest}")
    if unrouted:
        print("per-net unrouted (from DRC report):")
        for n, c in sorted(unrouted.items(), key=lambda kv: -kv[1]):
            print(f"  {c:3}  {n}")

    # ---- rule 5: thermal vias under U1 paddle / U5 EP --------------------
    for ref in ("U1", "U5"):
        fp = next(f for f in scr.GetFootprints() if f.GetReference() == ref)
        bb = fp.GetBoundingBox()
        n = 0
        for t in scr.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA) and bb.Contains(t.GetPosition()) \
                    and t.GetNetname() in ("GND", "/power/VIN_B"):
                n += 1
        print(f"thermal/stitch vias inside {ref} outline: {n}")


if __name__ == "__main__":
    main()
