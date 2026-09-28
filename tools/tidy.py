#!/usr/bin/env python3
"""Tidy the finished board: router leftovers out, DRC-gated.

  track_dangling  a stub segment with a free end
  via_dangling    a via that connects on one layer only
  hole_to_hole    two vias of one net drilled on top of each other (a
                  board-setup warning here, but overlapping drills are a
                  fab problem): one of the pair goes

Items are removed by uuid in the file text (like pocket_open / manual_routes
do; pcbnew's Remove() is not safe for many items in one session), zones are
refilled, and the batch is kept only when DRC shows no more errors and no
more unconnected items than before; otherwise it is undone and its items
are tried one at a time. Removing a stub can leave the segment behind it
dangling, so this repeats until nothing is left or nothing changes.
Locked items and HV / RF nets are never touched.

Run:  PYTHONPATH=tools python3 tools/tidy.py [--dry-run]
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pcbnew

TOOLS = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import netclasses                                   # noqa: E402

PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")
FORM_RE = re.compile(r"\t\((segment|via|arc)\n(?:\t\t.*\n)*?\t\)\n")
KEEP_NETS = set(netclasses.HV) | set(netclasses.RF)


def report():
    netclasses.ensure()
    out = PCB + ".tidy.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all",
                    "-o", out, PCB], capture_output=True)
    with open(out) as f:
        d = json.load(f)
    errors = sum(1 for v in d["violations"] if v["severity"] == "error")
    return d, errors, len(d["unconnected_items"])


def net_of(item):
    m = re.search(r"\[(.*?)\]", item["description"])
    return m.group(1) if m else ""


def targets(d, locked):
    single, pairs = [], []
    for v in d["violations"]:
        it = v["items"]
        if v["type"] in ("track_dangling", "via_dangling"):
            if it[0]["uuid"] not in locked and net_of(it[0]) not in KEEP_NETS:
                single.append((it[0]["uuid"], f"{v['type']} {it[0]['description']} @({it[0]['pos']['x']:.3f},{it[0]['pos']['y']:.3f})"))
        elif v["type"] == "hole_to_hole" and len(it) == 2 and \
                all(i["description"].startswith("Via") for i in it) and net_of(it[0]) == net_of(it[1]):
            pair = [i["uuid"] for i in it if i["uuid"] not in locked]
            if pair:
                pairs.append((pair, f"hole_to_hole {it[0]['description']} @({it[0]['pos']['x']:.3f},{it[0]['pos']['y']:.3f})"))
    return single, pairs


def locked_uuids():
    txt = open(PCB, encoding="utf-8").read()
    out = set()
    for m in FORM_RE.finditer(txt):
        if "(locked yes)" in m.group(0):
            u = re.search(r'\(uuid "([^"]+)"\)', m.group(0))
            if u:
                out.add(u.group(1))
    return out


def drop(uuids):
    txt = open(PCB, encoding="utf-8").read()
    n = 0

    def keep(m):
        nonlocal n
        u = re.search(r'\(uuid "([^"]+)"\)', m.group(0))
        if u and u.group(1) in uuids:
            n += 1
            return ""
        return m.group(0)
    txt = FORM_RE.sub(keep, txt)
    with open(PCB, "w", encoding="utf-8") as f:
        f.write(txt)
    subprocess.run([sys.executable, "-c",
                    "import pcbnew,sys; b=pcbnew.LoadBoard(sys.argv[1]); "
                    "pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(sys.argv[1], b, True)", PCB],
                   capture_output=True)
    return n


def attempt(uuids, e0, u0):
    backup = PCB + ".tidy-backup"
    shutil.copyfile(PCB, backup)
    n = drop(set(uuids))
    d, e, u = report()
    if n and e <= e0 and u <= u0:
        os.unlink(backup)
        return True, d, e, u
    shutil.copyfile(backup, PCB)
    os.unlink(backup)
    return False, None, e, u


def main():
    dry = "--dry-run" in sys.argv
    d, e0, u0 = report()
    print(f"before: errors {e0}, unconnected {u0}")
    removed = 0
    for rnd in range(1, 8):
        locked = locked_uuids()
        single, pairs = targets(d, locked)
        if not single and not pairs:
            break
        print(f"round {rnd}: {len(single)} dangling item(s), {len(pairs)} overlapping via pair(s)")
        for _, s in single:
            print("   ", s)
        for _, s in pairs:
            print("   ", s)
        if dry:
            return
        batch = [u for u, _ in single] + [p[0] for p, _ in pairs]
        ok, d2, e, u = attempt(batch, e0, u0)
        if ok:
            print(f"   batch of {len(batch)} kept: errors {e}, unconnected {u}")
            removed += len(batch)
            d = d2
            continue
        print(f"   batch rejected (errors {e}, unconnected {u}); one at a time")
        progress = False
        for uuid, s in single:
            ok, d2, e, u = attempt([uuid], e0, u0)
            print(f"   {'kept' if ok else 'rejected'}: {s}")
            if ok:
                removed += 1
                progress = True
                d = d2
        for pair, s in pairs:
            for uuid in pair:
                ok, d2, e, u = attempt([uuid], e0, u0)
                if ok:
                    print(f"   kept: {s} (one via removed)")
                    removed += 1
                    progress = True
                    d = d2
                    break
            else:
                print(f"   rejected: {s}")
        if not progress:
            break
        d, e0, u0 = report()
    d, e, u = report()
    left = sum(1 for v in d["violations"] if v["type"] in ("track_dangling", "via_dangling", "hole_to_hole"))
    print(f"TIDY_RESULT removed={removed} errors={e} unconnected={u} leftovers={left}")


if __name__ == "__main__":
    main()
