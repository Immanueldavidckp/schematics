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


def inject_keepouts(dsn_path, board):
    """Teach FreeRouting the rules a DSN cannot express, as keepouts.

    Measured on cycle-2's session (docs/design-log.md, hybrid fixed point):
    every cycle FR produced copper that adopt HAD to rip - 17 board-edge
    violations (board setup edge clearance 0.5, which a DSN boundary does not
    carry) and 1 via inside the 1.5 mm HV halo (a scoped DRU rule FR cannot
    know). The ripped nets then requeued to the LV finisher, which had already
    failed them: a fixed point at 155 unconnected.

    This injects (keepout ...) polygons - a strictly TIGHTER model, never a
    looser one:
      - four 0.5 mm strips along the board edges, both copper layers;
      - a halo rect around every locked HV segment/via: 1.5 mm outside
        BUCK_HV, 0.6 mm inside it (the approved BUCK_HV carve-out);
      - a 0.6 mm halo around locked MV copper (MV class clearance).
    Coordinates: DSN units are 0.1 um, Y negated.
    """
    from netclasses import HV, MV

    def rect(layer, x0, y0, x1, y1):
        c = [int(round(v * 10000)) for v in (x0, -y1, x1, -y0)]
        return (f'    (keepout "" (polygon {layer} 0  {c[0]} {c[1]}  '
                f'{c[2]} {c[1]}  {c[2]} {c[3]}  {c[0]} {c[3]}  '
                f'{c[0]} {c[1]}))\n')

    bb = board.GetBoardEdgesBoundingBox()
    bx0, by0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
    bx1, by1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
    EDGE = 0.5          # board setup constraints edge clearance
    out = []
    for lay in ("F.Cu", "B.Cu"):
        out.append(rect(lay, bx0, by0, bx1, by0 + EDGE))
        out.append(rect(lay, bx0, by1 - EDGE, bx1, by1))
        out.append(rect(lay, bx0, by0, bx0 + EDGE, by1))
        out.append(rect(lay, bx1 - EDGE, by0, bx1, by1))

    buck = None
    for z in board.Zones():
        if z.GetZoneName() == "BUCK_HV":
            b2 = z.GetBoundingBox()
            buck = (b2.GetLeft() / 1e6, b2.GetTop() / 1e6,
                    b2.GetRight() / 1e6, b2.GetBottom() / 1e6)

    def hv_margin(x0, y0, x1, y1):
        if buck and x0 >= buck[0] and y0 >= buck[1] and \
                x1 <= buck[2] and y1 <= buck[3]:
            return 0.6
        return 1.5

    hv, mv = set(HV), set(MV)
    lname = {board.GetLayerID("F.Cu"): "F.Cu", board.GetLayerID("B.Cu"): "B.Cu"}
    n_hv = n_mv = 0
    for t in board.GetTracks():
        if not t.IsLocked():
            continue
        net = t.GetNetname()
        if net in hv:
            is_hv = True
        elif net in mv:
            is_hv = False
        else:
            continue
        if t.GetClass() == "PCB_VIA":
            x, y = t.GetPosition().x / 1e6, t.GetPosition().y / 1e6
            r = t.GetWidth(pcbnew.F_Cu) / 2e6
            m = (hv_margin(x - r, y - r, x + r, y + r) if is_hv else 0.6) + r
            for lay in ("F.Cu", "B.Cu"):
                out.append(rect(lay, x - m, y - m, x + m, y + m))
        else:
            lay = lname.get(t.GetLayer())
            if lay is None:
                continue
            s, e = t.GetStart(), t.GetEnd()
            x0, x1 = sorted((s.x / 1e6, e.x / 1e6))
            y0, y1 = sorted((s.y / 1e6, e.y / 1e6))
            hw = t.GetWidth() / 2e6
            m = (hv_margin(x0 - hw, y0 - hw, x1 + hw, y1 + hw)
                 if is_hv else 0.6) + hw
            out.append(rect(lay, x0 - m, y0 - m, x1 + m, y1 + m))
        n_hv += is_hv
        n_mv += not is_hv

    txt = open(dsn_path).read()
    i = txt.index("(keepout")            # existing keepout block in structure
    txt = txt[:i] + "".join(out) + "    " + txt[i:]
    open(dsn_path, "w").write(txt)
    print(f"injected keepouts: 8 edge strips, {n_hv} HV halos, "
          f"{n_mv} MV halos")


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

    inject_keepouts(DSN, board)

    shutil.copyfile(PCB, SCRATCH)
    # The scratch is DRC'd by pcbroute_adopt.py, and a board DRC'd without
    # its project's .kicad_dru / .kicad_pro reports PHANTOM violations
    # (measured: X1's own pads C5 [GND] vs CD [USIM_DET] at 0.19 mm, which
    # the DRU exempts). A phantom that names GND makes adopt rip the whole
    # GND net - every cycle. Keep the scratch project in lockstep.
    stem = SCRATCH[:-len(".kicad_pcb")]
    for ext in (".kicad_dru", ".kicad_pro"):
        shutil.copyfile(PCB[:-len(".kicad_pcb")] + ext, stem + ext)

    # -mp 8: v2.4.1 has no wall-clock option and only writes the .ses when
    # it finishes, so a kill at the time budget yields NOTHING - measured:
    # -mp 100 ran the full 90 minutes and was stopped empty-handed, while the
    # earlier (harder, pre-shrink) board completed 8 passes in ~40 minutes.
    # Fewer optimisation passes is a schedule choice, not a rule change.
    passes = os.environ.get("FR_PASSES", "8")
    # A stale .ses from the previous cycle MUST NOT satisfy the existence
    # check below: when FR hits the budget and is killed it writes nothing,
    # and importing the old session replays the old cycle verbatim (measured:
    # cycles 1 and 2 both "103935 bytes" - the hybrid fixed point).
    if os.path.exists(SES):
        os.replace(SES, SES + ".prev")
    cmd = ["java", "-jar", jar, "-de", DSN, "-do", SES, "-mp", passes]
    cmd += os.environ.get("FR_EXTRA", "").split()   # e.g. 2.x: -mt 8 --gui.enabled=false
    print("running:", " ".join(cmd))
    print(f"budget: {minutes} minutes")
    log = open(os.path.join(PROJ, "autoroute.log"), "w")
    try:
        subprocess.run(cmd, timeout=minutes * 60, stdout=log, stderr=log)
    except subprocess.TimeoutExpired:
        print(f"FreeRouting hit the {minutes}-minute budget and was stopped")
    log.close()
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
