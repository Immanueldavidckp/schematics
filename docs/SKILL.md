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

## Silent-failure guards (mandatory — these fail without any error)

Both of these were hit on this project. Neither produces a warning; both leave
a board that looks correct and is not. **Check them, do not assume them.**

**G1. A footprint's courtyard may be SMALLER than its pad extent.**
Never use `GetCourtyard()` alone as a keepout, and never use a footprint's
courtyard as the basis for spacing or clearance reasoning. U2's LQFP-48
courtyard measures 7.1 x 7.1 mm — the body — while its pads reach 9.0 mm, so
packing to the courtyard put 0603s directly on its leads. Also note the
courtyard box is **not necessarily centred on the footprint origin**: J1's
derived Molex courtyard is centred 7.50 mm in x and 1.92 mm in y away from its
origin, because the origin sits on pin 1.
- *Required:* keepout = `max(courtyard, pad bounding box)` per axis, positioned
  by the **box centre**, not the footprint origin. See `keepout_abs()` in
  `tools/pcbplace.py`.

**G2. `pcbnew.SaveBoard()` wipes `net_settings` out of the .kicad_pro.**
Every net class and net-class pattern is destroyed each time a Python
generator saves the board. RF/HV/VBAT_MODEM rules then stop applying while DRC
continues to report a low violation count, so the design silently loses its
impedance, HV-clearance and current-carrying constraints. Compounding it,
KiCad **discards any hand-written net class** that lacks `bus_width`,
`priority` or `tuning_profile`, or that is written with the wrong
`meta.version` — again with no warning.
- *Required:* apply net classes **after** every board-writing step, then
  **verify they survive a KiCad round trip** and fail loudly if they do not.
  See `tools/netclasses.py`, and use `tools/build.py` rather than running the
  stages by hand.

Two related pcbnew traps, for anyone editing the generators:
- `board.Remove()` hands ownership back to Python and double-frees on the next
  GC — the interpreter segfaults with exit 139 and no traceback. Rebuild from
  a template instead of deleting.
- `pcbnew.FootprintLoad()` returns **one C++ object per library id**. Caching
  and reusing it collapses every component sharing that footprint onto a single
  instance, because `board.Add()` is a no-op after the first call. This
  produced 45 footprints instead of 219 and left 349 pads unbound to nets.

## Safety-critical process requirements

**P1. Conformal coating is MANDATORY on every board, including prototypes.**
Not a finish preference — **creepage at U5 depends on it.** The EG11752's
exposed pad is VIN_B at up to 100 V and the SOIC-8 package places its own
signal pins 0.55 mm away. IPC-2221 needs 0.60 mm for external *uncoated*
conductors at 100 V; coated (B4) needs about 0.25 mm. The board therefore only
meets creepage **once coated**, and the 0.3 mm DRC exception scoped to
`HV_ZONE` is written against the coated figure.
- Prototypes must be coated **before** the 100 V / 85 C burn-in.
- The **U5 area is a coating inspection point** and is marked as such on the
  assembly drawing (F.Fab).
- An uncoated board relies on the package's own certified spacing alone and
  must not be energised at line voltage.

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
PYTHONPATH=tools python3 tools/release.py
gerbers (JLCPCB preset) + drill  → out/gerbers.zip
BOM: Comment,Designator,Footprint,LCSC  → out/bom.csv
CPL: Designator,Mid X,Mid Y,Layer,Rotation → out/positions.csv
```
`tools/release.py` REFUSES to export while DRC shows any violation OR any
unconnected item, ERC shows an error, or checkpins fails - "0 violations"
alone is not a complete board. `--force` exports into `out/NOT-FOR-FAB/`
for checking the mechanics only.
Check rotations of the modem, MCU and QFN parts against JLCPCB's rotation
conventions before release.

## Definition of done
- ERC = 0 errors, DRC = 0 errors, exceptions logged
- All footprints datasheet-verified
- BOM C-numbers re-checked in stock at jlcpcb.com/parts on release day
- 3D render reviewed (antenna keepouts, connector orientation, housing fit
  vs. 58 × 78 mm usable area, battery pocket)
- `design-log.md` complete

## HV scoping (approved policy, 2026-09-06)

- The 1.5 mm HV-to-LV separation is defence-in-depth for EXTERNALLY-WIRED
  nets. It is scoped: full force in HV_ZONE outside BUCK_HV; 0.60 mm
  electrical minimum (IPC-2221, coated per F-20) inside BUCK_HV and across
  the MV class (interior <= 70 V chain nodes, voltages logged in
  netclasses.py). Never silently re-widen the scope — and never narrow it
  without the same approval trail this one has (design-log 2026-09-06).
- Netclass membership is load-bearing: SW_BUCK sat in Default and the error
  was invisible until a router treated it as LV. When adding a net, ask what
  voltage it SWINGS to, not what rail it nominally belongs to.

## Router guards (pcbroute_hv.py)

- Halos must be quantised OUTWARD (floor/ceil), never round-to-nearest:
  round() admits RES/2 encroachment, which at RES 0.15 is exactly the
  0.545..0.594 mm shortfall band DRC reported against 0.600 mm.
- Track cells and via sites need SEPARATE blocked grids: a 0.80 mm via is
  illegal where a 0.50 mm track is legal, and one merged grid blocks the
  single-cell escape lanes between fine-pitch pins.
- DRU courtyard exemptions are insideCourtyard(X) && insideCourtyard(X) —
  INSIDE one package. A router exemption keyed only on the footprint
  reference relaxes copper in open field and DRC will (correctly) fail it.
