#!/usr/bin/env python3
"""Build the whole project in the one order that actually works.

Order matters and the failure modes are silent, so this exists instead of a
README list of commands:

  1. sheets.py            regenerate the five schematic sheets + root
  2. export netlist       pcbplace reads nl.net, not the .kicad_sch
  3. pcbgen.py            board outline, mounting holes, HV silk boundary
  4. pcbplace.py          footprints, nets, HV keepout, planes, stitching vias
  5. netclasses.py        MUST come after 3 and 4: pcbnew.SaveBoard() rewrites
                          the project and wipes net_settings, so any netclass
                          applied earlier is gone by now
  6. refill zones         MUST come after 5: the zones were filled while only
                          the Default class existed, so the fill used 0.2 mm
                          where HV needs 0.6 mm. kicad-cli loads the project
                          properly and refills with the real clearances
  7. canonicalise         step 6 rewrote the board, so re-stabilise it
  8. ERC + DRC + renders  the review deliverables

Run:  python3 tools/build.py
"""
import os
import subprocess
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCH = os.path.join(PROJ, "telematics-tracker.kicad_sch")
PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")
TOOLS = os.path.join(PROJ, "tools")


def run(desc, cmd, quiet=True):
    print(f"\n=== {desc}")
    env = dict(os.environ, PYTHONPATH=TOOLS)
    r = subprocess.run(cmd, cwd=PROJ, env=env, capture_output=True, text=True)
    out = [l for l in r.stdout.splitlines()
           if l.strip() and "property.h" not in l and "PROPERTY_ENUM" not in l]
    if quiet:
        out = out[-14:]
    for l in out:
        print("   " + l)
    if r.returncode != 0:
        print(f"   FAILED (exit {r.returncode})")
        err = [l for l in r.stderr.splitlines()
               if "property.h" not in l and "PROPERTY_ENUM" not in l]
        for l in err[-12:]:
            print("   ! " + l)
        sys.exit(r.returncode)
    return r.stdout


def main():
    py = sys.executable
    run("1/8 schematic sheets", [py, "tools/sheets.py"])
    run("2/8 netlist", ["kicad-cli", "sch", "export", "netlist", "--format",
                        "kicadsexpr", "--output", "nl.net", SCH])
    run("3/8 board skeleton", [py, "tools/pcbgen.py"])
    run("4/8 placement + planes + vias", [py, "tools/pcbplace.py"])
    run("5/8 net classes", [py, "tools/netclasses.py"])
    run("6/8 refill zones with real netclass clearances",
        ["kicad-cli", "pcb", "drc", "--refill-zones", "--save-board",
         "--output", os.devnull, PCB])
    print("\n=== 7/8 canonicalise")
    sys.path.insert(0, TOOLS)
    import pcbgen
    pcbgen.canonicalise(PCB)

    run("8/8 ERC", ["kicad-cli", "sch", "erc", "--output", "erc-full.rpt", SCH])
    run("8/8 DRC", ["kicad-cli", "pcb", "drc", "--output", "drc-placement.rpt",
                    "--severity-error", "--severity-warning", "--units", "mm",
                    PCB])
    print("\nbuild complete")


if __name__ == "__main__":
    main()
