---
name: kicad-telematics
description: >
  Design workflow for the MEWP telematics tracker PCB in KiCad. Use this skill
  whenever working on the telematics hardware project: creating or editing the
  KiCad schematic/PCB, importing JLCPCB/LCSC parts, generating fabrication
  outputs, or verifying the design against the telematics spec. Triggers:
  "telematics", "tracker PCB", "KiCad", "JLCPCB", "footprint import",
  "gerbers", any C-number like C2916205.
---

# KiCad Telematics Tracker Skill

## Golden rules
1. NEVER invent a footprint or symbol. Every component comes from
   `easyeda2kicad` using its verified LCSC/JLCPCB C-number, or from KiCad's
   official libraries for generic passives.
2. NEVER change a C-number without flagging it to the user. The BOM in
   `telematics-handoff.md` is the single source of truth.
3. All work happens in the project repo: `telematics-tracker/`.
4. After every schematic milestone run ERC; after every layout milestone run
   DRC. Zero errors before moving on. Warnings must be individually justified
   in `design-log.md`.
5. Keep a running `design-log.md`: every decision, every deviation, every
   ERC/DRC exception.

## Environment setup (run once)
```bash
# KiCad 9 (Ubuntu; use the installer on Windows/Mac)
sudo add-apt-repository ppa:kicad/kicad-9.0-releases -y
sudo apt update && sudo apt install -y kicad

# Footprint/symbol importer for LCSC C-numbers
pip install easyeda2kicad

# KiCad MCP server so Claude Code can drive KiCad directly
git clone https://github.com/lamaalrajih/kicad-mcp.git ~/kicad-mcp
cd ~/kicad-mcp && pip install -r requirements.txt
claude mcp add kicad -- python ~/kicad-mcp/main.py
```
If the MCP server repo layout differs, follow its README; the goal is a
working `kicad` MCP entry in `claude mcp list`. If MCP tooling fails, fall
back to editing `.kicad_sch` / `.kicad_pcb` S-expression files directly and
opening KiCad for visual verification — the file format is documented and
diff-able.

## Importing every footprint (run before schematic capture)
```bash
mkdir -p telematics-tracker/lib
cd telematics-tracker
for id in C2916205 C55058656 C5380158 C5382551 C477928 C374063 C16581 \
          C5126709 C151249 C359074 C73013 C2685734; do
  easyeda2kicad --full --lcsc_id=$id --output lib/jlc
done
```
This creates `lib/jlc.kicad_sym`, `lib/jlc.pretty/`, `lib/jlc.3dshapes/`.
Register them as project-local libraries. For every imported footprint,
open it and VERIFY pad 1 marking, courtyard, and pin count against the
manufacturer datasheet before use — importer output is good but not
guaranteed. Log each verification in `design-log.md`.

Generic passives (0603/0805 R/C, SOT-23, SOD-123) use KiCad built-in
libraries; assign JLCPCB Basic-part C-numbers in the `LCSC` field of each
symbol so the assembly BOM exports correctly.

## Schematic structure (hierarchical sheets)
1. `power.kicad_sch`     — input protection, buck, charger, battery, rails
2. `mcu.kicad_sch`       — AT32F403ACGT7, crystals, SWD, boot, resets
3. `modem_rf.kicad_sch`  — EC200U, SIM, antennas, USB test pads
4. `io.kicad_sch`        — CAN, DI/DO, ignition + VIN sensing
5. `storage.kicad_sch`   — SPI NOR flash

Every net named, every sheet with hierarchical pins. Follow the pin map and
block circuits in `telematics-handoff.md` §5–§6 exactly.

## PCB rules
- 4 layers: L1 signal/RF, L2 solid GND, L3 power, L4 signal. ~60 × 80 mm.
- RF: 50 Ω CPWG from EC200U ANT pads to U.FL, stitching vias, no plane
  splits under RF. GNSS and LTE U.FL at opposite board corners.
- HV zone (VIN up to 100 V) physically separated; ≥ 1.5 mm clearance
  HV-to-LV, marked keepout. Divider resistors: two in series (0805).
- Modem VBAT: bulk caps (2×100 µF ceramic) within 5 mm of VBAT pins;
  trace ≥ 2 mm wide.
- Thermal: LM5164 exposed pad stitched to L2/L3 with ≥ 9 vias.
- Mounting: 4× M3 holes, GND-tied. Test points on every rail, UART, SWD.
- JLCPCB capabilities: min 0.15 mm track/space is safe; via 0.3/0.45 mm.

## Fabrication outputs
```
gerbers (JLCPCB preset) + drill  → out/gerbers.zip
BOM: Comment,Designator,Footprint,LCSC  → out/bom.csv
CPL: Designator,Mid X,Mid Y,Layer,Rotation → out/positions.csv
```
Check rotations of the modem, MCU and QFN parts against JLCPCB's rotation
conventions before release.

## Definition of done
- ERC = 0 errors, DRC = 0 errors, exceptions logged
- All footprints datasheet-verified
- BOM C-numbers re-checked in stock at jlcpcb.com/parts on release day
- 3D render reviewed (antenna keepouts, connector orientation, housing fit
  vs. 58 × 78 mm usable area, battery pocket)
- `design-log.md` complete
