#!/usr/bin/env python3
"""Fabrication release for JLCPCB: gate, then gerbers + drill, BOM, CPL.

THE GATE IS THE POINT. A board can pass every DRC *rule* and still be
missing copper: KiCad reports missing connections separately ("unconnected
items"), and a fab house will happily build a board with 94 of them. This
script refuses to emit anything for fabrication unless ALL of:

  DRC violations == 0  AND  DRC unconnected items == 0
  ERC errors == 0
  tools/checkpins.py exits 0 (netlist matches the handoff pin map)

Outputs (docs/SKILL.md "Fabrication outputs"):
  out/gerbers/*.g*, *.drl       KiCad JLCPCB-style plot: Protel extensions,
                                 X2 off, soldermask subtracted from silk,
                                 Excellon mm, absolute origin
  out/gerbers.zip               what you upload to JLCPCB
  out/bom.csv                   Comment,Designator,Footprint,LCSC
  out/positions.csv             Designator,Mid X,Mid Y,Layer,Rotation

--force writes to a directory whose name says NOT-FOR-FAB, for checking the
export mechanics on an unfinished board. It never writes to out/.

Run:  PYTHONPATH=tools python3 tools/release.py [--force] [--out DIR]
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbgen import PROJ, PCB                                 # noqa: E402

SCH = os.path.join(PROJ, "telematics-tracker.kicad_sch")
NET = os.path.join(PROJ, "nl.net")
# untranslated layer names of THIS board (In1/In2 are renamed GND_L2/PWR_L3)
GERBER_LAYERS = ("F.Cu,GND_L2,PWR_L3,B.Cu,F.Paste,B.Paste,F.Silkscreen,"
                 "B.Silkscreen,F.Mask,B.Mask,Edge.Cuts")


def run(cmd, timeout=900):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       cwd=PROJ)
    return r


def gate(tmp):
    """Return a list of blocking reasons (empty = release allowed)."""
    why = []
    rpt = os.path.join(tmp, "release-drc.rpt")
    run(["kicad-cli", "pcb", "drc", "--severity-error", "-o", rpt, PCB])
    text = open(rpt).read() if os.path.exists(rpt) else ""
    m_v = re.search(r"Found (\d+) (?:DRC )?violations", text)
    m_u = re.search(r"Found (\d+) unconnected", text)
    viol = int(m_v.group(1)) if m_v else -1
    unc = int(m_u.group(1)) if m_u else -1
    print(f"DRC: violations={viol} unconnected={unc}")
    if viol != 0:
        why.append(f"DRC reports {viol} rule violation(s)")
    if unc != 0:
        why.append(f"DRC reports {unc} unconnected item(s) - copper is MISSING")

    erc = os.path.join(tmp, "release-erc.rpt")
    run(["kicad-cli", "sch", "erc", "--severity-error", "-o", erc, SCH])
    etext = open(erc).read() if os.path.exists(erc) else ""
    # the ERC report has no "Found N" line: with --severity-error every
    # "[type]: ..." entry is an error
    eerr = len(re.findall(r"^\[[a-z_]+\]", etext, re.M)) if etext else -1
    print(f"ERC: errors={eerr}")
    if eerr != 0:
        why.append(f"ERC reports {eerr} error(s)")

    run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr",
         "--output", NET, SCH])
    r = run([sys.executable, os.path.join(PROJ, "tools", "checkpins.py"), NET])
    print(f"checkpins: rc={r.returncode}")
    if r.returncode != 0:
        why.append("checkpins.py failed - netlist does not match the pin map")
    return why


def export(outdir):
    gdir = os.path.join(outdir, "gerbers")
    os.makedirs(gdir, exist_ok=True)
    r = run(["kicad-cli", "pcb", "export", "gerbers", "-o", gdir + "/",
             "--layers", GERBER_LAYERS, "--no-x2", "--subtract-soldermask",
             "--check-zones", PCB])
    if r.returncode:
        sys.exit(f"gerber export failed:\n{r.stdout}\n{r.stderr}")
    r = run(["kicad-cli", "pcb", "export", "drill", "-o", gdir + "/",
             "--format", "excellon", "--excellon-units", "mm",
             "--drill-origin", "absolute", "--generate-map",
             "--map-format", "gerberx2", PCB])
    if r.returncode:
        sys.exit(f"drill export failed:\n{r.stdout}\n{r.stderr}")
    files = sorted(os.listdir(gdir))
    zpath = os.path.join(outdir, "gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(gdir, f), f)
    print(f"gerbers: {len(files)} files -> {zpath}")

    # BOM in JLCPCB's column order; grouped so one line per part number
    bom = os.path.join(outdir, "bom.csv")
    r = run(["kicad-cli", "sch", "export", "bom", "-o", bom,
             "--fields", "Value,Reference,Footprint,LCSC",
             "--labels", "Comment,Designator,Footprint,LCSC",
             "--group-by", "Value,Footprint,LCSC", "--exclude-dnp", SCH])
    if r.returncode:
        sys.exit(f"BOM export failed:\n{r.stdout}\n{r.stderr}")
    rows = list(csv.DictReader(open(bom, newline="", encoding="utf-8")))
    # test points and solder jumpers are bare copper, not purchased parts
    keep = [row for row in rows
            if not all(re.match(r"(TP|JP)\d+$", d.strip())
                       for d in row["Designator"].split(","))]
    if len(keep) != len(rows):
        with open(bom, "w", newline="", encoding="utf-8") as fo:
            wr = csv.DictWriter(fo, fieldnames=list(rows[0].keys()),
                                quoting=csv.QUOTE_ALL)
            wr.writeheader()
            wr.writerows(keep)
        rows = keep
    missing = [row["Designator"] for row in rows if not row.get("LCSC")]
    print(f"BOM: {len(rows)} lines -> {bom}"
          + (f"  ({len(missing)} line(s) WITHOUT an LCSC number: "
             f"{', '.join(missing)[:200]})" if missing else ""))

    # CPL: KiCad csv -> JLCPCB columns
    kpos = os.path.join(outdir, "positions-kicad.csv")
    r = run(["kicad-cli", "pcb", "export", "pos", "-o", kpos, "--format", "csv",
             "--units", "mm", "--side", "both", "--exclude-dnp", PCB])
    if r.returncode:
        sys.exit(f"position export failed:\n{r.stdout}\n{r.stderr}")
    cpl = os.path.join(outdir, "positions.csv")
    n = 0
    with open(kpos, newline="", encoding="utf-8") as fi, \
            open(cpl, "w", newline="", encoding="utf-8") as fo:
        rd = csv.DictReader(fi)
        wr = csv.writer(fo)
        wr.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in rd:
            side = "Top" if row["Side"].lower().startswith("top") else "Bottom"
            wr.writerow([row["Ref"], f'{float(row["PosX"]):.4f}mm',
                         f'{float(row["PosY"]):.4f}mm', side,
                         f'{float(row["Rot"]):.1f}'])
            n += 1
    os.unlink(kpos)
    print(f"CPL: {n} placements -> {cpl}")
    print("REMINDER: check U1/U2/QFN rotations against JLCPCB's conventions, "
          "re-check every LCSC number is in stock, and order WITH conformal "
          "coating (mandatory - creepage at U5, see docs/SKILL.md P1).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="export despite a failed gate, into a NOT-FOR-FAB dir")
    ap.add_argument("--out", default=None,
                    help="output directory (default out/, or the NOT-FOR-FAB "
                         "dir with --force)")
    a = ap.parse_args()
    tmp = os.path.join(PROJ, ".release-tmp")
    os.makedirs(tmp, exist_ok=True)
    why = gate(tmp)
    if why and not a.force:
        print("\nRELEASE BLOCKED - do NOT order this board:")
        for w in why:
            print(f"  - {w}")
        sys.exit(2)
    if why:
        outdir = a.out or os.path.join(PROJ, "out", "NOT-FOR-FAB")
        print("\nWARNING: gate failed, --force given. Writing to a NOT-FOR-FAB "
              "directory; these files must not be sent to a fab:")
        for w in why:
            print(f"  - {w}")
    else:
        outdir = a.out or os.path.join(PROJ, "out")
        print("\nGATE PASSED - board is complete and rule-clean.")
    os.makedirs(outdir, exist_ok=True)
    export(outdir)
    print("RELEASE_OK" if not why else "RELEASE_FORCED_NOT_FOR_FAB")


if __name__ == "__main__":
    main()
