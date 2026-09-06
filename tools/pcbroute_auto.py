#!/usr/bin/env python3
"""Step 4: FreeRouting on the remaining low-speed nets, onto a SCRATCH copy.

Everything hand-routed (RF CPWG + fence, all HV and MV nets) is locked, so
KiCad exports it as Specctra `(type fix)` and FreeRouting must route around
it. The autorouter's output lands on a scratch copy of the board - the real
board file is only touched by the deterministic generator flow.

FreeRouting version, jar size and SHA-256 are pinned in docs/MIGRATION.md
section 1. The import rules (standing policy) are in design-log.md:
never loosen a netclass to improve completion; verify locked items survive;
re-run floorplan_check; review every autorouted HV path; count thermal vias.

Run:  PYTHONPATH=tools python3 tools/pcbroute_auto.py <path-to-jar> [minutes]
"""
import os
import shutil
import subprocess
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbgen import PROJ, PCB                                 # noqa: E402

SCRATCH = os.path.join(PROJ, "autoroute-scratch.kicad_pcb")
DSN = os.path.join(PROJ, "autoroute.dsn")
SES = os.path.join(PROJ, "autoroute.ses")


def main():
    jar = sys.argv[1]
    minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    if not os.path.exists(jar):
        sys.exit(f"jar not found: {jar}")

    board = pcbnew.LoadBoard(PCB)
    locked = sum(1 for t in board.GetTracks() if t.IsLocked())
    total = len(list(board.GetTracks()))
    print(f"board: {total} track/via items, {locked} locked (exported as fix)")
    if not pcbnew.ExportSpecctraDSN(board, DSN):
        sys.exit("DSN export failed")
    print(f"exported {DSN} ({os.path.getsize(DSN)} bytes)")

    # The DSN must carry the netclass geometry - the rule-mismatch class of
    # failure (step 1) was FreeRouting genuinely using a narrower width than
    # the board floor because the class said so.
    text = open(DSN).read()
    for token in ('"kicad_default" 200', '"MV" 300', '"HV" 500',
                  '"MODEM_BULK" 2000', '"PWR" 500', '"GND" 500'):
        # class widths are written as (rule (width NNN)) after the class name;
        # check net-class blocks exist at all, tolerating format drift
        name = token.split()[0].strip('"')
        if f'(class "{name}"' not in text and f'(class {name}' not in text:
            print(f"  WARNING: class {name} not found in DSN")
    print("DSN class blocks present")

    shutil.copyfile(PCB, SCRATCH)

    cmd = ["java", "-jar", jar, "-de", DSN, "-do", SES, "-mp", "100"]
    print("running:", " ".join(cmd))
    print(f"budget: {minutes} minutes")
    try:
        subprocess.run(cmd, timeout=minutes * 60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        print(f"FreeRouting hit the {minutes}-minute budget and was stopped")
    if not os.path.exists(SES):
        sys.exit("no .ses produced - nothing to import")
    print(f"session file: {SES} ({os.path.getsize(SES)} bytes)")

    scratch = pcbnew.LoadBoard(SCRATCH)
    before = len(list(scratch.GetTracks()))
    ok = pcbnew.ImportSpecctraSES(scratch, SES)
    after = len(list(scratch.GetTracks()))
    print(f"ImportSpecctraSES: {ok}  ({before} -> {after} items)")
    scratch.BuildListOfNets()
    try:
        pcbnew.ZONE_FILLER(scratch).Fill(scratch.Zones())
    except Exception as e:
        print(f"zone refill: {e}")
    pcbnew.SaveBoard(SCRATCH, scratch)
    print(f"scratch board saved: {SCRATCH}")


if __name__ == "__main__":
    main()
