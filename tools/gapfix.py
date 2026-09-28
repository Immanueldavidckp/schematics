#!/usr/bin/env python3
"""Close unconnected edges directly, gap by gap, from the DRC report.

Every unconnected entry the DRC report gives with two copper items (track,
via or pad - not a zone-to-zone island) names the two exact points that must
be joined. For each one, tools/pcbroute_lv.py is run in gap mode
(LV_GAP="x1,y1,L1;x2,y2,L2") on the outer layers, and if that fails with
PWR_L3 allowed. A result is kept only when the DRC error count does not
rise and the unconnected count falls - after a GND stitch when the new
copper split a pour (net zero on its own). Otherwise the board is restored.

Run:  python3 tools/gapfix.py          (the project's board, in place)
"""
import os
import re
import shutil
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import netclasses                                   # noqa: E402

PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")
WORK = os.path.join(PROJ, ".gapfix")
os.makedirs(WORK, exist_ok=True)
ITEM = re.compile(r"@\(([\d.]+) mm, ([\d.]+) mm\): (Track|Via|Pad \S+) \[([^\]]*)\](?: of \S+)? on ([A-Za-z0-9_.]+)")
SKIP = {"GND", ""} | set(netclasses.HV) | set(netclasses.MV) | set(netclasses.RF)


def log(msg):
    print(f"[gap {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def drc(tag):
    netclasses.ensure()
    rpt = os.path.join(WORK, f"{tag}.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "-o", rpt, PCB],
                   capture_output=True)
    txt = open(rpt).read()
    kinds = re.findall(r"^\[([a-z_]+)\]", txt, re.M)
    unc = sum(1 for k in kinds if k == "unconnected_items")
    return len(kinds) - unc, unc, txt


def gaps(rpt):
    out = []
    for blk in re.split(r"\n(?=\[)", rpt):
        if not blk.startswith("[unconnected"):
            continue
        items = ITEM.findall(blk)
        if len(items) < 2:
            continue
        (x1, y1, _k1, n1, l1), (x2, y2, _k2, n2, l2) = items[:2]
        if n1 != n2 or n1 in SKIP:
            continue
        out.append((n1, f"{x1},{y1},{l1};{x2},{y2},{l2}"))
    return out


def child(net, spec, l3):
    env = dict(os.environ, PYTHONPATH=TOOLS, PYTHONUNBUFFERED="1", LV_GAP=spec)
    env.pop("LV_ISLAND_AT", None)
    if l3:
        env["LV_L3"] = "1"
    else:
        env.pop("LV_L3", None)
    try:
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "pcbroute_lv.py"), "--net", net],
                           capture_output=True, text=True, timeout=1500, env=env, cwd=PROJ)
        t = [l for l in r.stdout.splitlines() if l.startswith("CHILD_")]
        return t[-1] if t else f"child rc={r.returncode}"
    except subprocess.TimeoutExpired:
        return "CHILD_FAIL timeout"


def settle():
    subprocess.run([sys.executable, os.path.join(TOOLS, "stitch_gnd.py")],
                   capture_output=True, text=True, timeout=1500,
                   env=dict(os.environ, PYTHONPATH=TOOLS), cwd=PROJ)


def main():
    e0, u, rpt = drc("start")
    log(f"start: errors {e0}, unconnected {u}")
    if e0:
        sys.exit("GAP_BASELINE_NOT_CLEAN")
    todo = gaps(rpt)
    log(f"{len(todo)} two-point gap(s): {[n for n, _ in todo]}")
    done = set()
    for net, spec in todo:
        for l3 in (False, True):
            backup = os.path.join(WORK, "before.kicad_pcb")
            shutil.copyfile(PCB, backup)
            res = child(net, spec, l3)
            if not res.startswith("CHILD_OK"):
                shutil.copyfile(backup, PCB)
                continue
            e, u2, _ = drc("try")
            if e <= e0 and u2 >= u and u2 <= u + 1:
                settle()
                e, u2, _ = drc("try-settle")
            if e <= e0 and u2 < u:
                log(f"  KEPT {net} {'on PWR_L3' if l3 else 'outer layers'}: {res[:40]} -> unconnected {u} -> {u2}")
                u = u2
                done.add(net)
                break
            shutil.copyfile(backup, PCB)
        if net not in done:
            log(f"  {net}: not closed ({spec})")
    e, u, _ = drc("end")
    log(f"GAP_RESULT unconnected={u} errors={e}")
    print(f"GAP_RESULT unconnected={u} errors={e}")


if __name__ == "__main__":
    main()
