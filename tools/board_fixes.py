#!/usr/bin/env python3
"""Board-only fixes from the 2026-09-29 verification review, each DRC-gated:

  dnp      mark the DNP parts (X2, R70, C48-C51) DNP on the board so the
           pick-and-place export leaves them out (the BOM already did)
  swap     C61 (1 uF, the charger's VBUS cap) sat 49 mm from U6 while C80
           (100 nF, same nets) sat 11 mm from it: swap their places
  epvias   more vias in the buck's exposed pad (VIN_B) to its L3 thermal
           island: 3 -> up to 8
  rfvias   GND stitching vias along both 50 ohm antenna lines (none before)

Every step: apply, refill, DRC; kept only if DRC errors and unconnected
items do not rise, else the board is restored. Run:
  PYTHONPATH=tools python3 tools/board_fixes.py [dnp swap epvias rfvias]
"""
import json
import math
import os
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
V = pcbnew.VECTOR2I


def nm(v):
    return int(round(v * 1e6))


def drc():
    netclasses.ensure()
    out = PCB + ".fix.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all", "-o", out, PCB],
                   capture_output=True)
    d = json.load(open(out))
    errs = [v for v in d["violations"] if v["severity"] == "error"]
    return errs, len(d["unconnected_items"])


def save(b):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b, True)


def fp(b, ref):
    return [f for f in b.GetFootprints() if f.GetReference() == ref][0]


# ---------------------------------------------------------------------------
def step_dnp(b):
    n = 0
    for ref in ("X2", "R70", "C48", "C49", "C50", "C51"):
        f = fp(b, ref)
        f.SetAttributes(f.GetAttributes() | pcbnew.FP_DNP)
        n += 1
    return f"{n} footprints marked DNP"


def step_swap(b):
    a, c = fp(b, "C61"), fp(b, "C80")
    pa = {p.GetNumber(): V(p.GetPosition()) for p in a.Pads()}
    pc = {p.GetNumber(): V(p.GetPosition()) for p in c.Pads()}
    sa = (V(a.GetPosition()), a.GetOrientation(), a.IsFlipped())
    sc = (V(c.GetPosition()), c.GetOrientation(), c.IsFlipped())

    def put(f, pos, rot, flipped, want):
        if f.IsFlipped() != flipped:
            f.Flip(f.GetPosition(), True)
        f.SetOrientation(rot)
        f.SetPosition(pos)
        got = {p.GetNumber(): p.GetPosition() for p in f.Pads()}
        if any(math.hypot(got[k].x - want[k].x, got[k].y - want[k].y) > 2000 for k in want):
            f.SetOrientation(rot + pcbnew.EDA_ANGLE(180, pcbnew.DEGREES_T))
            f.SetPosition(pos)
            got = {p.GetNumber(): p.GetPosition() for p in f.Pads()}
        if any(math.hypot(got[k].x - want[k].x, got[k].y - want[k].y) > 2000 for k in want):
            raise SystemExit(f"{f.GetReference()}: pads do not land on the old pads")
    put(a, *sc, pc)
    put(c, *sa, pa)
    return "C61 <-> C80 swapped in place (pads on the same copper)"


def step_epvias(b):
    u5 = fp(b, "U5")
    ep = [p for p in u5.Pads() if p.GetNumber() == "9"][0]
    net = ep.GetNet()
    c, s = ep.GetPosition(), ep.GetSize()
    existing = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == ep.GetNetname()]
    added = 0
    # the three fitted vias sit in a row at the pad's centre line; two more
    # rows above and below, staggered, clear of the boot capacitor C76 on
    # the far side (HV clearance 0.6 mm)
    for dx, dy in ((-0.85, -0.8), (0.0, -0.8), (-0.425, 0.8), (0.425, 0.8)):
        if True:
            x, y = c.x + nm(dx), c.y + nm(dy)
            if abs(nm(dx)) + nm(0.25) > s.x / 2 or abs(nm(dy)) + nm(0.25) > s.y / 2:
                continue
            if any(math.hypot(x - e.x, y - e.y) < nm(0.6) for e in existing):
                continue
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(V(x, y))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(nm(0.45))
            v.SetDrill(nm(0.2))
            v.SetNet(net)
            b.Add(v)
            existing.append(V(x, y))
            added += 1
    return f"{added} vias added in the U5 exposed pad ({len(existing)} total)"


def step_rfvias(b):
    gnd = b.FindNet("GND")
    rf = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetLayer() == pcbnew.F_Cu
          and t.GetNetname().split("/")[-1].startswith("ANT_")]
    vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    pads = [p for f in b.GetFootprints() for p in f.Pads()]
    added = []
    for t in rf:
        a, c = t.GetStart(), t.GetEnd()
        L = math.hypot(c.x - a.x, c.y - a.y)
        if L < nm(1.2):
            continue
        ux, uy = (c.x - a.x) / L, (c.y - a.y) / L
        nx, ny = -uy, ux
        n = int(L / nm(1.5))
        for k in range(1, n + 1):
            px, py = a.x + ux * L * k / (n + 1), a.y + uy * L * k / (n + 1)
            for side in (1, -1):
                x, y = int(px + side * nx * nm(0.9)), int(py + side * ny * nm(0.9))
                if any(math.hypot(x - v.GetPosition().x, y - v.GetPosition().y) < nm(0.75) for v in vias):
                    continue
                if any(p.GetBoundingBox().Inflate(nm(0.4)).Contains(V(x, y)) for p in pads):
                    continue
                if any(math.hypot(x - q.x, y - q.y) < nm(0.75) for q in added):
                    continue
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(V(x, y))
                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetWidth(nm(0.45))
                v.SetDrill(nm(0.2))
                v.SetNet(gnd)
                b.Add(v)
                vias.append(v)
                added.append(V(x, y))
    return f"{len(added)} GND stitching vias added along the RF lines"


STEPS = {"dnp": step_dnp, "swap": step_swap, "epvias": step_epvias, "rfvias": step_rfvias}


def main():
    names = sys.argv[1:] or list(STEPS)
    e0, u0 = drc()
    print(f"before: errors {len(e0)}, unconnected {u0}")
    for name in names:
        backup = PCB + ".fix-backup"
        shutil.copyfile(PCB, backup)
        b = pcbnew.LoadBoard(PCB)
        msg = STEPS[name](b)
        save(b)
        e, u = drc()
        if len(e) <= len(e0) and u <= u0:
            print(f"KEPT {name}: {msg}; errors {len(e)}, unconnected {u}")
            os.unlink(backup)
        else:
            # for the via steps, drop only the offending vias and retry once
            bad = {i["uuid"] for v in e for i in v["items"]}
            if name in ("epvias", "rfvias") and bad:
                b = pcbnew.LoadBoard(PCB)
                n = 0
                for t in list(b.GetTracks()):
                    if t.GetClass() == "PCB_VIA" and t.m_Uuid.AsString() in bad:
                        b.Remove(t)
                        n += 1
                save(b)
                e, u = drc()
                if len(e) <= len(e0) and u <= u0:
                    print(f"KEPT {name} after removing {n} via(s): {msg}; errors {len(e)}, unconnected {u}")
                    os.unlink(backup)
                    continue
            shutil.copyfile(backup, PCB)
            os.unlink(backup)
            print(f"REJECTED {name}: {msg}; errors {len(e0)} -> {len(e)}, unconnected {u0} -> {u}")
            for v in e[:5]:
                print("   ", v["description"][:140], [i["description"][:50] for i in v["items"]])
    e, u = drc()
    print(f"BOARD_FIXES_RESULT errors={len(e)} unconnected={u}")


if __name__ == "__main__":
    main()
