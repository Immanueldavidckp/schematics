#!/usr/bin/env python3
"""Delete floating copper: track/via groups of a net that touch no pad and no
pour of that net.

Rip-and-reroute passes leave fragments behind (a ripped net rerouted
elsewhere, a partial route that the gate kept because the board improved).
Such a fragment connects nothing, but DRC counts it as one more cluster of its
net, so a net whose two real halves are one gap apart can show two
unconnected items with the fragment in the middle (DO1_GATE on E2). Removing
it can never break a connection. Locked items and the HV / MV / RF nets are
left alone. DRC-gated: kept only when errors do not rise and unconnected does
not rise.

Run:  python3 tools/prune_orphans.py [board]
"""
import os
import re
import shutil
import subprocess
import sys

import pcbnew

if not hasattr(pcbnew.SwigPyIterator, "next"):
    pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import netclasses                                   # noqa: E402
from pcbgen import _split_forms                     # noqa: E402

PCB = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(os.path.dirname(TOOLS), "telematics-tracker.kicad_pcb")
KEEP = set(netclasses.HV) | set(netclasses.MV) | set(netclasses.RF)


def drc():
    netclasses.ensure()
    rpt = PCB + ".prune.rpt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "-o", rpt, PCB], capture_output=True)
    kinds = re.findall(r"^\[([a-z_]+)\]", open(rpt).read(), re.M)
    unc = sum(1 for k in kinds if k == "unconnected_items")
    return len(kinds) - unc, unc


def orphan_uuids(board):
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    types = (pcbnew.PCB_PAD_T, pcbnew.PCB_TRACE_T, pcbnew.PCB_VIA_T, pcbnew.PCB_ZONE_T)
    tracks = {}
    for t in board.GetTracks():
        if t.GetNetname() in KEEP or t.IsLocked() or not t.GetNetname():
            continue
        tracks[t.m_Uuid.AsString()] = t
    seen, out = set(), []
    for k, t0 in tracks.items():
        if k in seen:
            continue
        comp, stack, anchored = [], [t0], False
        while stack:
            it = stack.pop()
            ik = it.m_Uuid.AsString()
            if ik in seen:
                continue
            seen.add(ik)
            if it.Type() in (pcbnew.PCB_PAD_T, pcbnew.PCB_ZONE_T):
                anchored = True
                continue
            comp.append(ik)
            for T in types:
                for j in conn.GetConnectedItems(it, T):
                    if j.GetNetname() == t0.GetNetname() and j.m_Uuid.AsString() not in seen:
                        stack.append(j)
        if not anchored:
            out.append((t0.GetNetname(), comp))
    return out


def main():
    e0, u0 = drc()
    print(f"before: errors {e0}, unconnected {u0}")
    b = pcbnew.LoadBoard(PCB)
    orphans = orphan_uuids(b)
    drop = {u for _n, comp in orphans for u in comp}
    del b
    if not drop:
        print("PRUNE_RESULT no floating copper")
        return
    backup = PCB + ".prune-backup"
    shutil.copyfile(PCB, backup)
    txt = open(PCB, encoding="utf-8").read()
    head_end = txt.index("\n") + 1
    tail_start = txt.rstrip().rfind(")")
    kept = []
    for fo in _split_forms(txt[head_end:tail_start]):
        m = re.search(r'\(uuid "([^"]+)"\)', fo)
        if m and m.group(1) in drop and re.match(r"\(\s*(segment|via|arc)\b", fo):
            continue
        kept.append(fo)
    open(PCB, "w", encoding="utf-8").write(txt[:head_end] + "".join(kept) + txt[tail_start:])
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b, True)
    e, u = drc()
    nets = sorted({n for n, _c in orphans})
    if e <= e0 and u <= u0:
        print(f"PRUNE_RESULT removed {len(drop)} floating items on {nets}: unconnected {u0} -> {u}, errors {e}")
    else:
        shutil.copyfile(backup, PCB)
        print(f"PRUNE_RESULT rejected (errors {e0} -> {e}, unconnected {u0} -> {u}); board restored")
    os.unlink(backup)


if __name__ == "__main__":
    main()
