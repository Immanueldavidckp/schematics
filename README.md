# MEWP Telematics Tracker — hardware

CAN-connected GPS/LTE tracker for rental MEWPs (boom/scissor lifts).
Powered from machine batteries with internal Li-ion backup, 2 isolated digital
inputs, 2 low-side outputs, ignition sense, 6-axis IMU, and ≥6 days of local
telemetry buffering.

**Status: milestone 3 complete.** Schematics are drawn and ERC-clean.
Layout has not started and is gated on the open flags below.

| | |
|---|---|
| Target | India · ~₹2,000/unit ex-works at ≥500 pcs · 5-year field life |
| Fab/assembly | JLCPCB (prototypes), Indian EMS later |
| EDA | KiCad 10 |
| Input range | 10.5–100 V DC (80 V packs reach ~96–100 V while charging) |

## Design

| Ref | Part | Function |
|---|---|---|
| U1 | Quectel EC200U-CN | LTE Cat-1 bis + GNSS |
| U2 | Artery AT32F403ACGT7 | MCU, M4 240 MHz, LQFP-48 |
| U3 | QST QMI8658B | 6-axis IMU |
| U4 | SIT1051AT/3 | CAN-FD transceiver |
| U5 | EG Micro EG11752 | 200 V abs-max buck → 5V0 |
| U6 | TI BQ25606 | 1S charger + power path |
| U7 | GD25Q64ESIGR | 8 MB SPI NOR telemetry buffer |
| U8 | TI TXB0104 | 1.8 V ↔ 3.3 V level shift |
| U9 | ME6211C33M5G | 3V3 LDO |

## Layout

```
telematics-tracker.kicad_pro/.kicad_sch/.kicad_pcb   project + root sheet
mcu / storage / io / modem_rf / power .kicad_sch     hierarchical sheets
lib/jlc.kicad_sym, lib/jlc.pretty, lib/jlc.3dshapes  LCSC parts (easyeda2kicad)
tools/schgen.py                                      KiCad S-expression emitter
tools/sheets.py                                      the schematics, as code
tools/checkpins.py                                   netlist-vs-spec guard
docs/                                                see below
erc-*.rpt                                            ERC evidence
```

Sheets are **generated**, not hand-drawn: edit `tools/sheets.py` and run
`python tools/sheets.py`, which rewrites all five sheets plus the root.
Symbol definitions are embedded in each sheet, so they parse without library
resolution. UUIDs are deterministic, so regeneration is diffable.

## Verification

Every change is gated on three checks:

```bash
python tools/sheets.py                                    # regenerate
kicad-cli sch erc  --output erc-full.rpt telematics-tracker.kicad_sch
kicad-cli sch export netlist --format kicadsexpr --output nl.net telematics-tracker.kicad_sch
python tools/checkpins.py nl.net                          # exits non-zero on any mismatch
```

Current: **ERC 0 errors** (14 warnings, each justified in the design log) ·
**48/48** handoff §5 pin-map rows verified against the netlist with far-end
checks · **8/8** DO default-OFF structural assertions.

The netlist guard exists because ERC does not catch everything. It has caught
four real faults that ERC reported only as warnings or not at all: a shorted-out
gate resistor, CANL tied to GND by overlapping stubs, VBAT merged into 3V3, and
a root-sheet wrap-around that shorted three rails.

## Documentation

| File | Contents |
|---|---|
| [design-log.md](design-log.md) | Every decision, deviation and flag, with evidence. Start here. |
| [docs/telematics-handoff.md](docs/telematics-handoff.md) | The governing spec (BOM, pin map, design rules) |
| [docs/f9-review.md](docs/f9-review.md) | EC200U pin-map review table — **sign-off gate** |
| [docs/ec200u-pinmap-extracted.md](docs/ec200u-pinmap-extracted.md) | All 144 pins, VERIFIED / NEEDS-HUMAN |
| [docs/section5-checklist.txt](docs/section5-checklist.txt) | Generated pin-map verification output |
| [docs/firmware-notes.md](docs/firmware-notes.md) | Hardware facts firmware must honour (FW-1…17, BV-1…4) |
| [docs/placement-study.svg](docs/placement-study.svg) | Milestone-4 placement study (provisional outline) |
| [docs/SKILL.md](docs/SKILL.md) | KiCad workflow rules for this project |

## Open flags (blocking layout)

- **F-9** — EC200U symbol came from an EasyEDA entry built around the MobileTek
  L610; its pin numbering contradicts Quectel Table 7 (VBAT_BB 90/91 vs 59/60).
  Only VERIFIED pins are wired; **76 pins are deliberately no-connect**, incl.
  35 probable GND pins. Human sign-off on `docs/f9-review.md` is required before
  layout.
- **F-15** — R80 10 Ω has no load-line solution at the 10.5 V floor at full
  load. Recommend 1 Ω anti-surge (C55348540).
- **F-13** modem bulk caps are X5R 6.3 V on a 4.35 V rail (violates the
  2:1 / X7R rule) · **F-14** six missing test points · **F-12** EG11752 R_IS and
  min-on-time bench items · **F-16** SIM holder locating posts · **F-17** MFF2
  land pattern · **F-5** provisional passive C-numbers.

Nothing here has been fabricated. Re-verify every LCSC C-number on order day.
