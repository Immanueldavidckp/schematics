#!/usr/bin/env python3
"""Parallel rip-and-reroute: one worker per stuck net, then a gated merge.

tools/pocket_open.py works through the stuck nets one at a time, and a single
net can take 20-40 minutes of attempts (outer-layer route, PWR_L3 route, wall
combinations). The attempts for different nets are independent, so:

  1. MAP: for each net with unconnected items, copy the board (with its rules
     and tools) into its own directory and run pocket_open.py there with
     POCKET_ONLY_NET=<net>, up to WORKERS at a time;
  2. every worker that ends with FEWER unconnected items than the base
     yields a patch: the track/via records it removed and added (by uuid);
  3. REDUCE: apply the patches to the real board one at a time, best gain
     first, each followed by a zone refill and a DRC; a patch is kept only when
     the error count does not rise and the unconnected count falls, otherwise
     the board is restored exactly. Two patches that fight over the same space
     simply fail the second gate.

Run:  python3 tools/pocket_par.py            (the project's board, in place)
Env:  PAR_WORKERS (default 8), POCKET_DEADLINE_S per worker (default 2400)
"""
import concurrent.futures as cf
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
WORK = os.path.join(PROJ, ".pocket-par")
WORKERS = int(os.environ.get("PAR_WORKERS", "8"))
PER_NET_S = os.environ.get("POCKET_DEADLINE_S", "2400")
SKIP = {"GND", ""} | set(netclasses.HV) | set(netclasses.MV) | set(netclasses.RF)


def log(msg):
    print(f"[par {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def drc(path, tag):
    netclasses.ensure()
    rpt = os.path.join(WORK, f"{tag}.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "-o", rpt, path],
                   capture_output=True)
    txt = open(rpt).read()
    kinds = re.findall(r"^\[([a-z_]+)\]", txt, re.M)
    unc = sum(1 for k in kinds if k == "unconnected_items")
    return len(kinds) - unc, unc, txt


def stuck_nets(rpt):
    nets = []
    for blk in re.split(r"\n(?=\[)", rpt):
        if not blk.startswith("[unconnected"):
            continue
        m = re.search(r"\[([^\]]+)\](?: of \S+)? on", blk)
        if m and m.group(1) not in SKIP and m.group(1) not in nets:
            nets.append(m.group(1))
    return nets


def forms(path):
    txt = open(path, encoding="utf-8").read()
    head_end = txt.index("\n") + 1
    tail_start = txt.rstrip().rfind(")")
    out = {}
    for fo in _split_forms(txt[head_end:tail_start]):
        if re.match(r"\(\s*(segment|via|arc)\b", fo):
            u = re.search(r'\(uuid "([^"]+)"\)', fo)
            if u:
                out[u.group(1)] = fo
    return txt, head_end, tail_start, out


def worker(net, base):
    d = os.path.join(WORK, re.sub(r"[^A-Za-z0-9_]+", "_", net).strip("_") or "net")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    shutil.copytree(TOOLS, os.path.join(d, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(base, os.path.join(d, "telematics-tracker.kicad_pcb"))
    for ext in (".kicad_pro", ".kicad_dru"):
        shutil.copyfile(os.path.join(PROJ, "telematics-tracker" + ext),
                        os.path.join(d, "telematics-tracker" + ext))
    env = dict(os.environ, PYTHONPATH=os.path.join(d, "tools"), PYTHONUNBUFFERED="1",
               POCKET_DEADLINE_S=PER_NET_S)
    if net == "__GND__":
        env["POCKET_GND_ONLY"] = "1"          # the sealed-island phase, alone
    else:
        env["POCKET_ONLY_NET"] = net
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(d, "tools", "pocket_open.py")],
                       capture_output=True, text=True, env=env, cwd=d,
                       timeout=int(PER_NET_S) + 3600)
    m = re.search(r"POCKET_RESULT unconnected=(\d+) errors=(\d+)", r.stdout)
    kept = [l for l in r.stdout.splitlines() if "KEPT" in l or "routed" in l]
    return net, d, (int(m.group(1)) if m else None), (int(m.group(2)) if m else None), \
        kept, time.time() - t0


def apply_patch(base_forms, result_path):
    """Apply result-vs-base track/via differences to the real board file."""
    _t, _h, _s, res = forms(result_path)
    removed = set(base_forms) - set(res)
    added = [res[u] for u in res if u not in base_forms]
    txt, head_end, tail_start, cur = forms(PCB)
    body = txt[head_end:tail_start]
    kept = []
    for fo in _split_forms(body):
        u = re.search(r'\(uuid "([^"]+)"\)', fo)
        if u and u.group(1) in removed and re.match(r"\(\s*(segment|via|arc)\b", fo):
            continue
        kept.append(fo)
    new = txt[:head_end] + "".join(kept) + "".join("\t" + a.strip() + "\n" for a in added) + txt[tail_start:]
    open(PCB, "w", encoding="utf-8").write(new)
    import pcbnew
    if not hasattr(pcbnew.SwigPyIterator, "next"):
        pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b, True)
    return len(removed), len(added)


def main():
    os.makedirs(WORK, exist_ok=True)
    base = os.path.join(WORK, "base.kicad_pcb")
    shutil.copyfile(PCB, base)
    e0, u0, rpt = drc(PCB, "start")
    log(f"start: errors {e0}, unconnected {u0}")
    if e0:
        sys.exit("PAR_BASELINE_NOT_CLEAN")
    nets = stuck_nets(rpt)
    if re.search(r"^\[unconnected[^\n]*\n(?:[^\[][^\n]*\n)*?[^\n]*\[GND\]", rpt, re.M):
        nets.insert(0, "__GND__")             # sealed GND islands get a worker too
    log(f"{len(nets)} stuck net(s), {WORKERS} workers: {nets}")
    results = []
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(worker, n, base) for n in nets]
        for f in cf.as_completed(futs):
            try:
                net, d, u, e, kept, dt = f.result()
            except Exception as exc:                  # a worker crash costs only its net
                log(f"worker failed: {exc!r}")
                continue
            gain = (u0 - u) if u is not None else 0
            log(f"  {net}: {u0} -> {u} ({dt / 60:.0f} min){' ' + '; '.join(k[19:80] for k in kept) if kept else ''}")
            if u is not None and e == 0 and gain > 0:
                results.append((gain, net, d))
    results.sort(key=lambda t: -t[0])
    log(f"{len(results)} worker(s) improved their copy; merging best first")
    _t, _h, _s, base_forms = forms(base)
    u_cur = u0
    for gain, net, d in results:
        backup = os.path.join(WORK, "before-merge.kicad_pcb")
        shutil.copyfile(PCB, backup)
        nrem, nadd = apply_patch(base_forms, os.path.join(d, "telematics-tracker.kicad_pcb"))
        e, u, _ = drc(PCB, "merge")
        if e <= e0 and u < u_cur:
            log(f"  MERGED {net} (-{nrem} +{nadd} items): unconnected {u_cur} -> {u}")
            u_cur = u
        else:
            shutil.copyfile(backup, PCB)
            log(f"  {net}: patch rejected on the merged board (errors {e}, unconnected {u} vs {u_cur})")
    e, u, _ = drc(PCB, "end")
    log(f"PAR_RESULT unconnected={u} errors={e}")
    print(f"PAR_RESULT unconnected={u} errors={e}")


if __name__ == "__main__":
    main()
