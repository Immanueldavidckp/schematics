#!/usr/bin/env python3
"""Open sealed pockets by ripping and rerouting ONE wall net at a time.

The last unconnected items on a routed board are pockets: a GND pour island,
or the pad of a signal, walled in by other nets' tracks so that neither a
stub nor a via fits (tools/pcbroute_lv.py reports them with "DEBUG pocket
walls" / "DEBUG pad seal" lines). The finisher's own rip-retry rips up to
three nets at once, never re-routes a ripped rail, and has one chance per
run. This tool is the patient version of a human moving a track aside:

  for each pocket, for each of its wall nets (most walls first):
    1. remove that net's unlocked copper - the whole net for a signal, only
       the copper within RIP_R of the pocket for a rail;
    2. route the starved target first (tools/pcbroute_lv.py --net TARGET,
       restricted to the island for GND);
    3. re-route the ripped net (--net WALL);
    4. DRC: keep the result only if the error count did not rise and the
       board's unconnected count FELL; otherwise restore the board exactly.

No rule is relaxed; only the order in which the same rules are met changes.

Run:  python3 tools/pocket_open.py            (the project's board, in place)
Env:  POCKET_RIP_R (mm, default 2.0), POCKET_CANDS (walls tried, default 3),
      POCKET_DEADLINE_S (default 10800)
"""
import ast
import itertools
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
from pcbgen import _split_forms                     # noqa: E402

PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")
WORK = os.path.join(PROJ, ".pocket")
RIP_R = float(os.environ.get("POCKET_RIP_R", "2.0"))
CANDS = int(os.environ.get("POCKET_CANDS", "3"))
DEADLINE = float(os.environ.get("POCKET_DEADLINE_S", "10800"))
NEVER_RIP = set(netclasses.HV) | set(netclasses.MV) | set(netclasses.RF) | \
    set(netclasses.BULK) | {"GND", "netless", "edge/nogo", ""}
RAILS = set(netclasses.PWR) | set(netclasses.BULK)

os.makedirs(WORK, exist_ok=True)
T0 = time.time()


def log(msg):
    print(f"[pocket {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def drc(tag):
    netclasses.ensure()
    rpt = os.path.join(WORK, f"{tag}.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "-o", rpt, PCB],
                   capture_output=True)
    txt = open(rpt).read()
    kinds = re.findall(r"^\[([a-z_]+)\]", txt, re.M)
    unc = sum(1 for k in kinds if k == "unconnected_items")
    return len(kinds) - unc, unc, txt


def child(net, extra_env=None, timeout=1200):
    env = dict(os.environ, PYTHONPATH=TOOLS, LV_DEBUG="1", PYTHONUNBUFFERED="1")
    env.pop("LV_ISLAND_AT", None)
    if extra_env:
        env.update(extra_env)
    try:
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "pcbroute_lv.py"),
                            "--net", net], capture_output=True, text=True,
                           timeout=timeout, env=env, cwd=PROJ)
        return r.stdout
    except subprocess.TimeoutExpired:
        return "CHILD_FAIL timeout"


def rip(net, box=None):
    """Remove the net's unlocked segments/vias; with box=(x0,y0,x1,y1) only
    those that come within RIP_R of it. Returns how many were removed."""
    txt = open(PCB, encoding="utf-8").read()
    head_end = txt.index("\n") + 1
    tail_start = txt.rstrip().rfind(")")
    body = txt[head_end:tail_start]
    kept, n = [], 0
    if box:
        bx0, by0, bx1, by1 = (box[0] - RIP_R, box[1] - RIP_R,
                              box[2] + RIP_R, box[3] + RIP_R)
    for fo in _split_forms(body):
        m = re.match(r"\(\s*(segment|via|arc)\b", fo)
        drop = False
        if m and "(locked yes)" not in fo and f'(net "{net}")' in fo:
            if box is None:
                drop = True
            else:
                if m.group(1) == "via":
                    at = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", fo)
                    pts = [(float(at.group(1)), float(at.group(2)))] if at else []
                else:
                    a = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", fo)
                    b = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", fo)
                    pts = []
                    if a and b:
                        ax, ay = float(a.group(1)), float(a.group(2))
                        ex, ey = float(b.group(1)), float(b.group(2))
                        k = max(1, int(max(abs(ex - ax), abs(ey - ay)) / 0.1))
                        pts = [(ax + (ex - ax) * i / k, ay + (ey - ay) * i / k)
                               for i in range(k + 1)]
                drop = any(bx0 <= x <= bx1 and by0 <= y <= by1 for x, y in pts)
        if drop:
            n += 1
        else:
            kept.append(fo)
    open(PCB, "w", encoding="utf-8").write(txt[:head_end] + "".join(kept) + txt[tail_start:])
    return n


def walls_of(out):
    """Merge every pad-seal / pocket-wall Counter the child printed."""
    w = {}
    for l in out.splitlines():
        m = re.search(r"DEBUG (?:pad seal \(\w+\)|pocket walls): (\{.*\})", l)
        if m:
            try:
                for k, v in ast.literal_eval(m.group(1)).items():
                    w[k] = w.get(k, 0) + v
            except (ValueError, SyntaxError):
                pass
    return w


def island_pockets(out):
    """[(x0, y0, x1, y1, walls)] for each sealed GND island in a --net GND run."""
    res, cur = [], None
    for l in out.splitlines():
        m = re.search(r"DEBUG island stub \(layer \d+\) at \(([-\d.]+),([-\d.]+)\) "
                      r"size ([\d.]+)x([\d.]+): no path", l)
        if m:
            x, y, w, h = map(float, m.groups())
            cur = [x, y, x + w, y + h, {}]
            res.append(cur)
            continue
        if cur is not None:
            # same-layer flood walls and, weighted double, the nets that block
            # a through via inside the island on the other layers
            m = re.search(r"DEBUG (pocket|via) walls: (\{.*\})", l)
            if m:
                try:
                    w = ast.literal_eval(m.group(2))
                    k = 2 if m.group(1) == "via" else 1
                    for n, c in w.items():
                        cur[4][n] = cur[4].get(n, 0) + k * c
                except (ValueError, SyntaxError):
                    pass
    return res


def signal_targets(rpt):
    """Nets (not GND, not protected) that still have unconnected items."""
    nets = []
    for blk in re.split(r"\n(?=\[)", rpt):
        if not blk.startswith("[unconnected"):
            continue
        for n in re.findall(r"\[([^\]]+)\](?: of \S+)? on", blk):
            if n != "GND" and n not in NEVER_RIP and n not in nets:
                nets.append(n)
            break
    return nets


def settle(tag):
    """A new route often closes its own gap and cuts a GND pour in two
    (measured: MODEM_RX fixed, GND 9 -> 10, net zero). Stitch the new GND
    island (tools/stitch_gnd.py gates itself) and measure again."""
    subprocess.run([sys.executable, os.path.join(TOOLS, "stitch_gnd.py")],
                   capture_output=True, text=True, timeout=1500,
                   env=dict(os.environ, PYTHONPATH=TOOLS), cwd=PROJ)
    return drc(tag)[:2]


def improved(e, u, tag):
    """Gate: fewer unconnected, no new errors - after a GND settle when the
    route alone was a near miss."""
    if e <= E0 and u < U_CUR:
        return True, u
    if e <= E0 and u <= U_CUR + 1:
        e2, u2 = settle(tag + "-settle")
        if e2 <= E0 and u2 < U_CUR:
            return True, u2
    return False, u


def attempt(target, walls, box, island_at):
    """One rip / route / reroute / gate cycle for a SET of wall nets.
    Returns True when kept."""
    global E0, U_CUR
    backup = os.path.join(WORK, "before-attempt.kicad_pcb")
    shutil.copyfile(PCB, backup)
    label = f"{target} x {'+'.join(walls)}"
    n = 0
    for wall in walls:
        n += rip(wall, box if wall in RAILS else None)
    if n == 0:
        return False
    env = {"LV_ISLAND_AT": f"{island_at[0]:.2f},{island_at[1]:.2f}"} if island_at else None
    out1 = child(target, env)
    progressed = ("CHILD_OK" in out1 or "CHILD_PARTIAL" in out1)
    if island_at:
        # a stub out of the island, or a via placed straight inside it
        progressed = progressed and ("cells to" in out1 or
                                     re.search(r"island taps: [1-9]\d* vias", out1) is not None)
    if not progressed:
        shutil.copyfile(backup, PCB)
        log(f"  {label}: target still blocked after ripping {n} items")
        return False
    tails = []
    for wall in walls:
        out2 = child(wall)
        t = [l for l in out2.splitlines() if l.startswith("CHILD_")]
        tails.append(f"{wall}: {t[-1][:40] if t else '?'}")
    e, u, _ = drc("attempt")
    ok, u = improved(e, u, "attempt")
    if ok:
        log(f"  KEPT {label} (rip of {n}): unconnected {U_CUR} -> {u}, errors {e}")
        U_CUR = u
        return True
    shutil.copyfile(backup, PCB)
    log(f"  {label}: rejected (errors {e}, unconnected {u} vs {U_CUR}; {'; '.join(tails)})")
    return False


def combos(cands):
    """Single walls first, then pairs, then the top three together."""
    out = [[c] for c in cands]
    out += [list(c) for c in itertools.combinations(cands, 2)]
    if len(cands) >= 3:
        out.append(list(cands[:3]))
    return out


def main():
    global E0, U_CUR
    E0, U_CUR, rpt = drc("start")
    log(f"start: errors {E0}, unconnected {U_CUR}")
    if E0:
        sys.exit("POCKET_BASELINE_NOT_CLEAN")

    # POCKET_ONLY_NET=<net>: work on that one net and skip the GND phase
    # (tools/pocket_par.py runs one such worker per net on its own board copy)
    only = os.environ.get("POCKET_ONLY_NET")
    # ---- GND islands --------------------------------------------------------
    survey_backup = os.path.join(WORK, "before-survey.kicad_pcb")
    shutil.copyfile(PCB, survey_backup)
    out = "" if only else child("GND")
    if not only:
        e, u, rpt = drc("survey")
        if e <= E0 and u < U_CUR:
            log(f"survey run itself helped: unconnected {U_CUR} -> {u}")
            U_CUR = u
        else:
            shutil.copyfile(survey_backup, PCB)
    pockets = island_pockets(out)
    log(f"{len(pockets)} sealed GND island(s)")
    for x0, y0, x1, y1, walls in pockets:
        if time.time() - T0 > DEADLINE:
            break
        cands = [n for n, _c in sorted(walls.items(), key=lambda kv: -kv[1])
                 if n not in NEVER_RIP][:CANDS]
        log(f"island ({x0:.1f},{y0:.1f}) {x1 - x0:.1f}x{y1 - y0:.1f}: walls {cands}")
        centre = ((x0 + x1) / 2, (y0 + y1) / 2)
        for ws in combos(cands):
            if time.time() - T0 > DEADLINE:
                break
            if attempt("GND", ws, (x0, y0, x1, y1), centre):
                break

    # ---- signal nets --------------------------------------------------------
    e, u, rpt = drc("signals")
    # POCKET_GND_ONLY=1: the GND phase only (a pocket_par worker of its own)
    todo = [] if os.environ.get("POCKET_GND_ONLY") else ([only] if only else signal_targets(rpt))
    for net in todo:
        if time.time() - T0 > DEADLINE:
            break
        backup = os.path.join(WORK, "before-survey.kicad_pcb")
        shutil.copyfile(PCB, backup)
        out = child(net)
        e, u, _ = drc("sig-survey")
        ok, u = improved(e, u, "sig-survey")
        if ok:
            log(f"{net}: routed directly, unconnected {U_CUR} -> {u}")
            U_CUR = u
            continue
        shutil.copyfile(backup, PCB)
        # second chance on PWR_L3: in the HV strip and between the pours L3
        # is empty (the sense lines from the input dividers cross under the
        # connector there - VIN_SENSE: 1 via, 31 mm, measured 2026-09-28).
        # The connectivity gate below rejects a route that cuts a pour.
        if os.environ.get("POCKET_L3", "1") != "0":
            out3 = child(net, {"LV_L3": "1"}, timeout=1800)
            e, u, _ = drc("sig-survey-l3")
            ok, u = improved(e, u, "sig-survey-l3")
            if ok:
                log(f"{net}: routed on PWR_L3, unconnected {U_CUR} -> {u}")
                U_CUR = u
                continue
            shutil.copyfile(backup, PCB)
            out += "\n" + out3
        walls = walls_of(out)
        cands = [n for n, _c in sorted(walls.items(), key=lambda kv: -kv[1])
                 if n not in NEVER_RIP and n != net][:CANDS]
        pads = [(float(x), float(y)) for x, y in re.findall(
            r"@\(([\d.]+) mm, ([\d.]+) mm\): Pad \S+ \[" + re.escape(net) + r"\]", rpt)]
        box = None
        if pads:
            box = (min(p[0] for p in pads), min(p[1] for p in pads),
                   max(p[0] for p in pads), max(p[1] for p in pads))
        log(f"{net}: walls {cands}")
        for ws in combos(cands):
            if time.time() - T0 > DEADLINE:
                break
            if box is None and any(w in RAILS for w in ws):
                continue
            if attempt(net, ws, box, None):
                break

    e, u, _ = drc("end")
    log(f"POCKET_RESULT unconnected={u} errors={e}")
    print(f"POCKET_RESULT unconnected={u} errors={e}")


if __name__ == "__main__":
    main()
