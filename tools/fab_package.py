#!/usr/bin/env python3
"""One-file manufacturing package: everything a PCB fab, an assembler and an
enclosure maker need, in one zip.

Run AFTER tools/release.py has passed its gate (it refuses otherwise):

    PYTHONPATH=tools python3 tools/release.py
    python3 tools/bom_audit.py
    python3 tools/fab_package.py

Writes out/package/<name>/ and out/<name>.zip, where <name> is
telematics-tracker-mfg-<date>-<git short hash>. Layout:

  README.txt                  what to send to whom, the full order spec
  1_PCB_fabrication/          gerbers.zip (+ unzipped), fabrication-drawing.pdf,
                              IPC-D-356 test netlist, ODB++ archive
  2_PCB_assembly/             BOM (JLCPCB + with manufacturer part numbers),
                              pick-and-place, assembly drawings, 3D renders
  3_documentation/            schematic PDF, assembled-board STEP, BOM audit,
                              design verification report (OK / NOT OK per item)
  4_enclosure/                STL / STEP / Blender source + renders, notes
"""
import csv
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

import pcbnew

if not hasattr(pcbnew.SwigPyIterator, "next"):
    pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")
SCH = os.path.join(PROJ, "telematics-tracker.kicad_sch")
OUT = os.path.join(PROJ, "out")


def run(cmd, timeout=1800):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=PROJ)
    if r.returncode:
        sys.exit(f"failed: {' '.join(cmd)}\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
    return r


def gate_ok():
    """The release gate's own report must be fresh and clean."""
    rpt = os.path.join(PROJ, ".release-tmp", "release-drc.rpt")
    if not os.path.exists(rpt) or os.path.getmtime(rpt) < os.path.getmtime(PCB):
        return "run tools/release.py first (its DRC report is missing or older than the board)"
    t = open(rpt).read()
    if not re.search(r"Found 0 (?:DRC )?violations", t) or not re.search(r"Found 0 unconnected", t):
        return "the release DRC report is not clean"
    for f in ("gerbers.zip", "bom.csv", "positions.csv", "bom-mpn.csv"):
        if not os.path.exists(os.path.join(OUT, f)):
            return f"out/{f} missing"
    audit = os.path.join(PROJ, "docs", "bom-audit.md")
    if not os.path.exists(audit) or "**0 line(s) to fix**" not in open(audit).read():
        return "BOM audit is not clean (python3 tools/bom_audit.py)"
    return None


# ---------------------------------------------------------------------------
def board_facts():
    b = pcbnew.LoadBoard(PCB)
    # the outline's own geometry (line / arc end points), not the bounding
    # box - that includes the 0.1 mm line width
    pts = [(p.x / 1e6, p.y / 1e6) for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts
           for p in (d.GetStart(), d.GetEnd())]
    w = round(max(x for x, _ in pts) - min(x for x, _ in pts), 3)
    h = round(max(y for _, y in pts) - min(y for _, y in pts), 3)
    holes = []
    fps = {"F": 0, "B": 0}
    tht = []
    for f in b.GetFootprints():
        ref = f.GetReference()
        if ref.startswith("H"):
            p = f.GetPosition()
            d = max(pd.GetDrillSize().x for pd in f.Pads()) / 1e6
            holes.append((ref, p.x / 1e6, p.y / 1e6, d))
            continue
        attrs = f.GetAttributes()
        if attrs & pcbnew.FP_EXCLUDE_FROM_POS_FILES:
            continue
        fps["B" if f.IsFlipped() else "F"] += 1
        # through-hole = has a plated drilled pad. Not the footprint's THT
        # attribute: the imported U.FL / modem / IMU / SIM footprints carry it
        # although they are surface-mount.
        if any(pd.GetDrillSize().x > 0 and pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
               for pd in f.Pads()):
            tht.append(ref)
    return dict(w=w, h=h, holes=sorted(holes), sides=fps, tht=sorted(tht))


def drill_table(drl):
    """[(diameter, hits, 'PTH' | 'NPTH')] from the Excellon file; plating from
    the aperture-function comment KiCad writes before each tool."""
    t = open(drl).read()
    tools, plating, func = {}, {}, "PTH"
    for line in t.splitlines():
        m = re.search(r"TA\.AperFunction,(NonPlated|Plated)", line)
        if m:
            func = "NPTH" if m.group(1) == "NonPlated" else "PTH"
        m = re.match(r"^T(\d+)C([\d.]+)", line)
        if m:
            tools[m.group(1)], plating[m.group(1)] = float(m.group(2)), func
    hits, cur = {}, None
    for line in t.splitlines():
        m = re.match(r"^T(\d+)$", line)
        if m:
            cur = m.group(1)
            continue
        if cur and line[:1] in "XY":
            hits[cur] = hits.get(cur, 0) + 1
    return sorted(((tools[k], hits.get(k, 0), plating[k]) for k in tools), key=lambda r: (r[2], r[0]))


def stackup(job):
    j = json.load(open(job))
    return j["GeneralSpecs"], j.get("MaterialStackup", [])


# ---------------------------------------------------------------------------
def fab_drawing(path, facts, drills, specs, stack, rev, date):
    """A4 landscape SVG -> PDF: outline with dimensions and holes, tables, notes."""
    S = 1.45                                   # board drawing scale
    ox, oy = 18.0, 34.0                        # board origin on the sheet (mm)
    W, H = facts["w"], facts["h"]
    el = []

    def text(x, y, s, size=3.0, anchor="start", weight="normal"):
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        el.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
                  f'font-weight="{weight}" font-family="DejaVu Sans, Liberation Sans, sans-serif">{s}</text>')

    def line(x1, y1, x2, y2, w=0.25, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        el.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="black" '
                  f'stroke-width="{w}"{d}/>')

    # outline, R2 corners
    r = 2.0 * S
    el.append(f'<rect x="{ox}" y="{oy}" width="{W * S:.2f}" height="{H * S:.2f}" rx="{r:.2f}" ry="{r:.2f}" '
              f'fill="#eef5ee" stroke="black" stroke-width="0.5"/>')
    for ref, x, y, d in facts["holes"]:
        cx, cy = ox + x * S, oy + y * S
        el.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{d / 2 * S:.2f}" fill="white" stroke="black" stroke-width="0.35"/>')
        line(cx - 3, cy, cx + 3, cy, 0.15)
        line(cx, cy - 3, cx, cy + 3, 0.15)
        text(cx + 3.2, cy - 2.2, ref, 2.4)
    # dimensions
    yd = oy + H * S + 8
    line(ox, oy + H * S + 2, ox, yd + 2, 0.2)
    line(ox + W * S, oy + H * S + 2, ox + W * S, yd + 2, 0.2)
    line(ox, yd, ox + W * S, yd, 0.25)
    text(ox + W * S / 2, yd - 1.2, f"{W:.2f} mm", 3.2, "middle", "bold")
    xd = ox + W * S + 8
    line(ox + W * S + 2, oy, xd + 2, oy, 0.2)
    line(ox + W * S + 2, oy + H * S, xd + 2, oy + H * S, 0.2)
    line(xd, oy, xd, oy + H * S, 0.25)
    el.append(f'<text x="{xd + 1.5:.2f}" y="{oy + H * S / 2:.2f}" font-size="3.2" font-weight="bold" '
              f'font-family="DejaVu Sans, sans-serif" transform="rotate(90 {xd + 1.5:.2f} {oy + H * S / 2:.2f})" '
              f'text-anchor="middle">{H:.2f} mm</text>')
    text(ox, oy - 3, "Board outline (Edge_Cuts), top view, corner radius 2.0 mm, 0.1 mm outline line. "
                     "Origin: top-left corner, X right, Y down.", 2.6)
    # hole table
    ty = yd + 8
    text(ox, ty, "Mounting holes (plated, GND)", 3.0, weight="bold")
    for i, (ref, x, y, d) in enumerate(facts["holes"]):
        text(ox, ty + 4.5 + i * 3.8, f"{ref}:  X {x:6.2f}   Y {y:6.2f}  (from bottom-left: {x:.2f}, {H - y:.2f})   "
                                     f"drill {d:.2f} mm", 2.6)
    # right column: stackup, drills, specs
    rx = 180.0
    yy = 16.0
    text(rx, yy, "Stackup (1.6 mm, JLC04161H-7628 or equivalent)", 3.0, weight="bold")
    yy += 4.5
    for s in stack:
        if s.get("Type") in ("Legend", "SolderPaste"):
            continue
        th = s.get("Thickness")
        extra = f"  {s.get('Material', '')} er {s.get('DielectricConstant', '')}" if s.get("Type") == "Dielectric" else ""
        text(rx, yy, f"{s.get('Name', s.get('Type')):22s} {s.get('Type'):12s} {th if th else '':>7} mm{extra}", 2.5)
        yy += 3.4
    yy += 3
    text(rx, yy, "Drill table (PTH = plated, NPTH = non-plated)", 3.0, weight="bold")
    yy += 4.5
    for d, n, pl in drills:
        text(rx, yy, f"drill {d:5.2f} mm   x {n}   {pl}", 2.5)
        yy += 3.4
    yy += 3
    text(rx, yy, "Fabrication requirements", 3.0, weight="bold")
    yy += 4.5
    notes = [
        "4 layers: F.Cu (top) / GND_L2 (in 1) / PWR_L3 (in 2) / B.Cu (bottom)",
        "FR-4, Tg >= 150 preferred; 1.6 mm +/-10 %; 1 oz outer, 0.5 oz inner",
        "Finish ENIG; mask both sides (green); silkscreen white, both sides",
        "Min track / space 0.127 / 0.127 mm; min via 0.45 / 0.20 mm",
        "Min hole 0.20 mm; vias tented (U2 pin 47: via in pad)",
        "Impedance: 50 ohm CPWG on L1, W 0.40, gap 0.30, ref. L2",
        "  (needs L1-L2 dielectric 0.2104 mm, er 4.4 - confirm stackup)",
        "IPC-6012 Class 2; 100 % electrical test (IPC-D-356 supplied)",
        "Panelisation by the fab is fine; keep 5 mm rails for assembly",
    ]
    for n in notes:
        text(rx, yy, n, 2.5)
        yy += 3.4
    # title block
    el.append('<rect x="10" y="190" width="277" height="12" fill="none" stroke="black" stroke-width="0.4"/>')
    text(14, 197.5, "MEWP telematics tracker - PCB fabrication drawing", 3.6, weight="bold")
    text(150, 197.5, f"{W:.0f} x {H:.0f} x 1.6 mm, 4 layers, ENIG", 3.0)
    text(283, 197.5, f"rev {rev}  {date}", 3.0, "end")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 297 210">'
           '<rect width="297" height="210" fill="white"/>' + "".join(el) + "</svg>")
    sp = path[:-4] + ".svg"
    open(sp, "w").write(svg)
    run(["rsvg-convert", "-f", "pdf", "-o", path, sp])
    os.unlink(sp)


# ---------------------------------------------------------------------------
def readme(path, facts, drills, rev, date, bom_lines, bom_parts, placements, zipname):
    tht = ", ".join(facts["tht"]) or "none"
    txt = f"""MEWP TELEMATICS TRACKER - MANUFACTURING PACKAGE
================================================
Revision {rev} (git branch relief6-stretch), generated {date}.
Board {facts['w']:.1f} x {facts['h']:.1f} mm, 4 layers, 1.6 mm, ENIG.
Checks passed before this package was made: DRC 0 errors / 0 unconnected,
ERC 0 errors, MCU pin map 47/47, 0 duplicate items, 0 overlapping holes,
BOM verified line by line against LCSC/JLCPCB (0 open), part heights
checked against the enclosure.

WHAT TO SEND TO WHOM
--------------------
1. PCB fabricator (bare boards)
     1_PCB_fabrication/gerbers.zip          <- the board itself (all layers + drill)
     1_PCB_fabrication/fabrication-drawing.pdf
     1_PCB_fabrication/telematics-tracker.ipc   (electrical test netlist, IPC-D-356)
     1_PCB_fabrication/telematics-tracker-odb.zip (the same board as ODB++, if they prefer)
2. Assembler (PCBA)
     JLCPCB:            gerbers.zip, then 2_PCB_assembly/bom-jlcpcb.csv and pick-and-place.csv
     local assembler:   2_PCB_assembly/bom-with-manufacturer-part-numbers.csv (manufacturer +
                        MPN on every line), pick-and-place.csv, assembly-top.pdf, assembly-bottom.pdf
3. Enclosure maker / 3D printing
     4_enclosure/  (see housing-notes.md; STL for printing, STEP for the lids, Blender source)

PCB FABRICATION SPECIFICATION
-----------------------------
Layer count ........ 4
Layer order ........ 1 F.Cu (top)       telematics-tracker-F_Cu.gtl
                     2 GND_L2 (inner 1) telematics-tracker-GND_L2.g1
                     3 PWR_L3 (inner 2) telematics-tracker-PWR_L3.g2
                     4 B.Cu (bottom)    telematics-tracker-B_Cu.gbl
Outline ............ telematics-tracker-Edge_Cuts.gm1: {facts['w']:.1f} x {facts['h']:.1f} mm, R2.0 corners
Thickness .......... 1.6 mm +/-10 %
Stackup ............ JLC04161H-7628 or equivalent:
                     L1-L2 7628 prepreg 0.2104 mm (er 4.4) / core 1.065 mm (er 4.6) /
                     L3-L4 7628 prepreg 0.2104 mm. The GNSS antenna feed depends on it.
Copper ............. 1 oz outer, 0.5 oz inner (finished)
Material ........... FR-4, Tg >= 150 preferred (sealed box, 70 C ambient)
Surface finish ..... ENIG (flat pads for the LGA-144 modem and the 0.5 mm-pitch MCU)
Solder mask ........ both sides (green, or any colour)
Silkscreen ......... both sides, white
Min track/space .... 0.127 / 0.127 mm (5 mil)
Min via ............ 0.45 mm pad, 0.20 mm drill; smallest hole 0.20 mm
Drill sizes ........ plated: {', '.join(f'{d:.2f} mm x{n}' for d, n, pl in drills if pl == 'PTH')}
                     NON-plated: {', '.join(f'{d:.2f} mm x{n}' for d, n, pl in drills if pl == 'NPTH') or 'none'}
                     (connector / SIM-holder locating pegs; marked NPTH in the drill file)
Vias ............... tented both sides. One via is in a pad (U2 pin 47, ground): plugged /
                     epoxy filled and capped if offered, otherwise acceptable as is.
Impedance control .. YES: 50 ohm coplanar waveguide on layer 1 (GNSS antenna feed):
                     track 0.40 mm, gap 0.30 mm to layer-1 ground, reference plane layer 2.
                     Valid for the stackup above - if your standard stackup differs, send it
                     to us before building so the track can be re-sized.
Quality / test ..... IPC-6012 Class 2, 100 % electrical test (telematics-tracker.ipc)
Panelisation ....... fab's choice; keep 5 mm rails and fiducials if the boards are assembled

IMPORTANT: a local fab must be able to do 0.127 mm track/space and 0.20 mm drills on
4 layers. If they cannot, do not let them "adjust" the files - tell us.

ASSEMBLY
--------
Placement .......... double-sided SMT: {facts['sides']['F']} parts on top, {facts['sides']['B']} on the bottom
                     ({placements} placements in pick-and-place.csv); through-hole: {tht}
BOM ................ {bom_lines} lines, {bom_parts} parts; DNP parts are excluded from BOM and placement
Rotation ........... check U1 (EC200U), U2 (LQFP-48) and U6 (QFN-24) in the placement preview
Test points ........ TPx are bare pads (not purchased parts)
CONFORMAL COATING .. MANDATORY on every board, prototypes included (safety: 100 V creepage
                     at U5). Coat both sides after assembly and before any 100 V test.
                     Keep coating OFF: J1, J2, AF1, AF2 (U.FL), X1 (SIM holder), test points.

ENCLOSURE (IP65)
----------------
Two variants (4_enclosure/internal-antennas, external-antennas): base 112 x 76 x 31.1 mm,
ASA light grey, O-ring cord seal, 6 lid screws outside the seal, M16 IP68 cable gland,
M12 ePTFE vent. Drawn to IP67 intent so IP65 has margin; jet-test a prototype.
Concept status: good for 3D-printed prototypes and quotes; a moulded version needs a CAD
redraw with draft angles (housing-notes.md, open items).

FILE INDEX
----------
"""
    for root, _, files in sorted(os.walk(os.path.dirname(path))):
        for f in sorted(files):
            rel = os.path.relpath(os.path.join(root, f), os.path.dirname(path))
            if rel != "README.txt":
                txt += f"  {rel}\n"
    txt += f"\n(This file and everything listed is in {zipname}.)\n"
    open(path, "w").write(txt)


# ---------------------------------------------------------------------------
def main():
    why = gate_ok()
    if why:
        sys.exit(f"PACKAGE REFUSED: {why}")
    rev = run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    dirty = run(["git", "status", "--porcelain", "--", "telematics-tracker.kicad_pcb",
                 "telematics-tracker.kicad_sch", "tools"]).stdout.strip()
    if dirty:
        rev += "+"
    date = datetime.date.today().isoformat()
    name = f"telematics-tracker-mfg-{date}-{rev.rstrip('+')}"
    pkg = os.path.join(OUT, "package", name)
    if os.path.exists(pkg):
        shutil.rmtree(pkg)
    d1, d2, d3, d4 = (os.path.join(pkg, s) for s in
                      ("1_PCB_fabrication", "2_PCB_assembly", "3_documentation", "4_enclosure"))
    for d in (d1, d2, d3, d4):
        os.makedirs(d)

    # 1 - fabrication
    shutil.copy(os.path.join(OUT, "gerbers.zip"), d1)
    shutil.copytree(os.path.join(OUT, "gerbers"), os.path.join(d1, "gerbers"))
    run(["kicad-cli", "pcb", "export", "ipcd356", "-o", os.path.join(d1, "telematics-tracker.ipc"), PCB])
    run(["kicad-cli", "pcb", "export", "odb", "-o", os.path.join(d1, "telematics-tracker-odb.zip"), PCB])
    facts = board_facts()
    drills = drill_table(os.path.join(OUT, "gerbers", "telematics-tracker.drl"))
    specs, stack = stackup(os.path.join(OUT, "gerbers", "telematics-tracker-job.gbrjob"))
    fab_drawing(os.path.join(d1, "fabrication-drawing.pdf"), facts, drills, specs, stack, rev, date)

    # 2 - assembly
    shutil.copy(os.path.join(OUT, "bom.csv"), os.path.join(d2, "bom-jlcpcb.csv"))
    shutil.copy(os.path.join(OUT, "bom-mpn.csv"), os.path.join(d2, "bom-with-manufacturer-part-numbers.csv"))
    shutil.copy(os.path.join(OUT, "positions.csv"), os.path.join(d2, "pick-and-place.csv"))
    for side, layers, mirror in (("top", "F.Fab,Edge.Cuts", []), ("bottom", "B.Fab,Edge.Cuts", ["--mirror"])):
        run(["kicad-cli", "pcb", "export", "pdf", "--mode-single", "--layers", layers, "--ibt",
             "--sp", "--cdnp", *mirror, "-o", os.path.join(d2, f"assembly-{side}.pdf"), PCB])
        run(["kicad-cli", "pcb", "render", "--side", side, "--width", "2400", "--height", "1700",
             "--quality", "high", "--background", "opaque", "-o", os.path.join(d2, f"board-{side}.png"), PCB])
    rows = list(csv.DictReader(open(os.path.join(OUT, "bom-mpn.csv"), newline="", encoding="utf-8")))
    bom_lines, bom_parts = len(rows), sum(int(r["Qty"] or 0) for r in rows)
    placements = sum(1 for _ in open(os.path.join(OUT, "positions.csv"))) - 1

    # 3 - documentation
    run(["kicad-cli", "sch", "export", "pdf", "-o", os.path.join(d3, "schematic.pdf"), SCH])
    run(["kicad-cli", "pcb", "export", "step", "--subst-models", "--no-dnp", "-f",
         "-o", os.path.join(d3, "assembled-board.step"), PCB], timeout=2400)
    shutil.copy(os.path.join(PROJ, "docs", "bom-audit.md"), d3)
    shutil.copy(os.path.join(PROJ, "docs", "verification-report.pdf"), d3)

    # 4 - enclosure
    shutil.copy(os.path.join(PROJ, "docs", "housing-notes.md"), d4)
    from PIL import Image
    for variant, label in (("internal", "internal-antennas"), ("external", "external-antennas")):
        src, dst = os.path.join(PROJ, "docs", "housing", variant), os.path.join(d4, label)
        os.makedirs(dst)
        for f in sorted(os.listdir(src)):
            if f.endswith((".stl", ".step", ".blend")):
                shutil.copy(os.path.join(src, f), dst)
            elif f.endswith(".png"):
                Image.open(os.path.join(src, f)).convert("RGB").save(
                    os.path.join(dst, f[:-4] + ".jpg"), quality=88)

    zipname = f"{name}.zip"
    readme(os.path.join(pkg, "README.txt"), facts, drills, rev, date, bom_lines, bom_parts,
           placements, zipname)
    zpath = os.path.join(OUT, zipname)
    for old in os.listdir(OUT):
        if old.startswith("telematics-tracker-mfg-") and old.endswith(".zip"):
            os.unlink(os.path.join(OUT, old))
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, _, files in os.walk(pkg):
            for f in sorted(files):
                full = os.path.join(root, f)
                z.write(full, os.path.join(name, os.path.relpath(full, pkg)))
    n = sum(len(fs) for _, _, fs in os.walk(pkg))
    print(f"PACKAGE_OK {zpath} ({os.path.getsize(zpath) / 1e6:.1f} MB, {n} files)")


if __name__ == "__main__":
    main()
