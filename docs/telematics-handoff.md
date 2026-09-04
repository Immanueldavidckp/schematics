# MEWP Telematics Tracker — Full Design Handoff for Claude Code

Owner: Immanueldavid · Target: India · Budget: ~₹2,000/unit ex-works at ≥500 pcs
Life requirement: 5 years continuous field operation on rental MEWPs (boom lifts,
scissor lifts) · Fab/assembly: JLCPCB (prototypes), Indian EMS later.

This document + the `kicad-telematics` skill are the complete instructions.
Claude Code must not deviate from the BOM or pin map without flagging it.

---

## 1. Product definition

A CAN-connected GPS/LTE tracker powered from machine batteries (9–100 V DC),
with internal backup battery, 2 digital inputs, 2 digital outputs, ignition
input with voltage measurement, 6-axis IMU (tilt/impact/motion-wake), and
local flash buffering of ≥2 days of telemetry for network outages.

Variant for this build: **Variant A (mainstream)** — integrated-GNSS modem,
one CAN channel, 100 V-capable power front end.

## 2. Five-year & scaling design rules (non-negotiable)

1. No electrolytic or tantalum capacitors. Ceramic X7R/X7S only, voltage
   derated ≥2:1 (100 V rail parts rated 100 V minimum with TVS clamping).
2. Backup battery is field-replaceable: 1S Li-ion on a JST-PH-2+NTC (3-pin
   JST-XH) connector, never soldered. Battery is a 2–3 year service item.
3. MCU can hard power-cycle the modem: high-side P-FET switch on modem VBAT
   driven by MCU GPIO. A hung modem must never brick a deployed unit.
4. Independent watchdog (IWDG) always on; brown-out detector enabled.
5. OTA path: modem DFOTA for its own firmware + custom MCU bootloader in
   external flash for application FOTA.
6. Temperature: all semiconductors ≥105 °C rated where available (AT32 is
   −40…+105 °C). Conformal coat production boards.
7. Scaling/second-source: CAN transceiver pad-compatible alternates
   (SIT1051 ↔ TJA1051T/3 ↔ TCAN1042), IMU footprint fixed to QMI8658
   (LGA-14), dual SIM footprint — nano-SIM holder AND MFF2 eSIM pads in
   parallel with 0 Ω selects, for future soldered-eSIM scaling.
8. Test points on every rail, SWD, both UARTs, CAN, and a 4-pad bed-of-nails
   friendly layout for a production test jig.
9. LTE Cat-1 only (no 2G-dependent logic) — safe on Indian networks past 2031.

## 3. BOM — main components (verified in stock on JLCPCB, Aug 2026)

| Ref | Part | JLCPCB # | Qty | ~$@250+ | Function |
|---|---|---|---|---|---|
| U1 | Quectel EC200UCNAA-N05-SGNSA | C2916205 | 1 | 9.91 | LTE Cat-1 bis + GNSS + BT |
| U2 | Artery AT32F403ACGT7 | C55058656 | 1 | 1.69 | MCU, M4 240 MHz, 2×CAN, LQFP-48 |
| U3 | QST QMI8658B | C5380158 | 1 | 0.80 | 6-axis IMU, I2C |
| U4 | SIT1051AT/3 | C5382551 | 1 | 0.30 | CAN-FD transceiver, 3.3 V VIO |
| U5 | TI LM5164DDAR | C477928 | 1 | 1.97 | 6–100 V → 5 V/1 A sync buck |
| U6 | TI BQ25606RGER | C374063 | 1 | 1.62 | 1S charger + power path (SYS rail) |
| U7 | W25Q64JV (SPI NOR 8 MB) | verify: W25Q64JVSSIQ | 1 | 0.35 | ≥6 days telemetry buffer |
| U8 | TXB0104 level shifter (or equiv 4-ch) | select in stock | 1 | 0.30 | MCU 3.3 V ↔ modem 1.8 V UART |
| U9 | 3.3 V LDO 500 mA (XC6220/ME6217 class) | select in stock | 1 | 0.15 | 3V3 rail from SYS |
| D1 | S3M reverse-blocking diode | Basic part | 1 | 0.05 | Reverse polarity (P-FET upgrade path) |
| D2 | SMBJ100A TVS | C151249 | 1 | 0.10 | Input transient clamp |
| Q1,Q2 | 100 V logic-level NMOS SOT-23 (select: VDS≥100 V, ID≥1 A, VGS(th)≤2.5 V, JLC Basic) | select | 2 | 0.15 | DO1/DO2 low-side drivers |
| Q3 | P-FET high-side switch (−30 V, e.g. AO3401 class) | select | 1 | 0.05 | Modem VBAT power-cycle |
| OK1,OK2 | EL357N(D) high-CTR opto | C359074-family, pick (D) bin | 2 | 0.06 | Isolated DI1/DI2 |
| X1 | Nano/micro-SIM push-push holder | select in stock | 1 | 0.15 | + parallel MFF2 eSIM pads |
| J1 | Micro-Fit 3.0 style 12-pin (43045-compatible) | select in stock | 1 | 0.50 | Machine harness |
| ANT | LTE FPC antenna w/ U.FL + GNSS ceramic active-capable patch w/ U.FL | select | 2 | 0.80 | Internal; SMA drill option for steel installs |
| BT1 | 1S Li-ion 103450 ~1800 mAh w/ NTC + JST lead | Indian sourcing | 1 | 1.70 | Replaceable backup |
| — | Passives/crystals (8 MHz, 32.768 kHz), ESD arrays, LEDs, fuse ≥125 V (0453 class) | Basic parts | ~70 | 1.50 | — |

Where the table says "select in stock", Claude Code chooses a JLCPCB
**Basic** part meeting the stated criteria and logs the C-number chosen.
Re-verify every C-number's stock on jlcpcb.com/parts on order day.

Cheap fallback swaps if budget pressure demands: U3→SC7A20TR C5126709,
U5→XL7015E1 C73013 (caps system at 80 V!), U6→TP4056 C16581 + discrete
power-path. Do not apply without user approval.

## 4. Power architecture

```
J1.VIN (9–100 V) ──F1 fuse──D1 S3M──┬── SMBJ100A → GND
                                    ├── C: 2×2.2 µF/100 V X7R 1210 + 100 nF
                                    └── U5 LM5164 ──► 5V0 @1 A
                                          (datasheet 5 V/1 A typical app:
                                           L 150–220 µH shielded ≥1.5 A sat,
                                           Cout ≥47 µF eff., RON for ~300 kHz,
                                           FB: 100 k / 31.6 k → 5.0 V)
5V0 ──► U6 BQ25606 (IN) ──► SYS (3.5–4.4 V, power-path with BT1)
              │  ICHG ≈ 0.7 A (RICHG per datasheet formula)
              │  TS ← battery NTC (JEITA)
              └─ BT1 1S Li-ion (JST, replaceable)
SYS ──► Q3 P-FET (MODEM_PWR_EN, default ON via pulldown on gate driver) ──► VBAT_MODEM
        VBAT_MODEM decoupling: 2×100 µF ceramic + 1 µF + 100 nF + TVS, ≤5 mm from U1
SYS ──► U9 LDO ──► 3V3 (MCU, IMU, flash, CAN VIO, level shifter B-side)
5V0 ──► SIT1051 VCC (CAN alive only when machine power present — accepted)
U1 VDD_EXT (1.8 V out) ──► level shifter A-side reference
```

Sensing dividers (all into MCU ADC, 12-bit, slow sample time):
- VIN sense: 300 k (3×100 k 0805 in series) : 9.1 k + 100 nF + BAV99 clamp → PA1
- IGN sense: identical divider on J1.IGN → PA0 (also EXTI wake)
- Battery sense: 1 M : 1 M + 100 nF → PB0 (≈2 µA standing drain)

## 5. The connection — full MCU pin map (AT32F403ACGT7, LQFP-48)

| Pin | Port | Net | Goes to |
|---|---|---|---|
| 10 | PA0 | IGN_SENSE | Ignition divider (ADC + EXTI wake) |
| 11 | PA1 | VIN_SENSE | Main supply divider (ADC) |
| 12 | PA2 | DBG_TX | Debug UART (USART2) → test pads |
| 13 | PA3 | DBG_RX | Debug UART |
| 14 | PA4 | FLASH_CS | U7 W25Q64 pin 1 |
| 15 | PA5 | SPI1_SCK | U7 pin 6 |
| 16 | PA6 | SPI1_MISO | U7 pin 2 (DO) |
| 17 | PA7 | SPI1_MOSI | U7 pin 5 (DI) — W25Q64: WP & HOLD tied 3V3 |
| 18 | PB0 | VBAT_SENSE | Battery divider (ADC) |
| 19 | PB1 | ADC_SPARE | Spare divider footprint (DNP) |
| 21 | PB10 | MODEM_PWR_EN | Q3 gate driver (modem power-cycle) |
| 22 | PB11 | NET_STATUS_LED | Status LED (via NPN) |
| 25 | PB12 | DI1 | OK1 collector (47 k pull-up to 3V3) |
| 26 | PB13 | DI2 | OK2 collector (47 k pull-up to 3V3) |
| 27 | PB14 | DO1_GATE | Q1 gate (100 R series, 10 k pulldown) |
| 28 | PB15 | DO2_GATE | Q2 gate (100 R series, 10 k pulldown) |
| 29 | PA8 | MODEM_PWRKEY | NPN open-drain → U1 PWRKEY |
| 30 | PA9 | MODEM_TX | USART1_TX → U8 → U1 MAIN_RXD (1.8 V domain) |
| 31 | PA10 | MODEM_RX | USART1_RX ← U8 ← U1 MAIN_TXD |
| 32 | PA11 | MODEM_RI | via U8 ch3 (wake on SMS/URC) |
| 33 | PA12 | MODEM_DTR | via U8 ch4 (modem sleep control) |
| 34 | PA13 | SWDIO | SWD header/test pads |
| 37 | PA14 | SWCLK | SWD |
| 38 | PA15 | CAN_STB | U4 pin 8 (standby; JTAG JTDI — disable JTAG, keep SWD) |
| 39 | PB3 | MODEM_RESET | NPN open-drain → U1 RESET_N (JTDO — SWD-only) |
| 40 | PB4 | MODEM_STATUS | ← U1 STATUS via divider (NJTRST — SWD-only) |
| 41 | PB5 | IMU_INT1 | U3 INT1 (motion wake, EXTI) |
| 42 | PB6 | I2C1_SCL | U3 SCL (2.2 k pull-ups to 3V3) |
| 43 | PB7 | I2C1_SDA | U3 SDA |
| 45 | PB8 | CAN1_RX (remap) | U4 pin 4 RXD |
| 46 | PB9 | CAN1_TX (remap) | U4 pin 1 TXD |
| 2 | PC13 | SYS_LED | Heartbeat LED |
| 3/4 | PC14/15 | OSC32 | 32.768 kHz crystal + 2×6.8 pF |
| 5/6 | PD0/1 | OSC_HSE | 8 MHz crystal + 2×18 pF |
| 7 | NRST | RESET | 100 nF + SWD |
| 44 | BOOT0 | BOOT0 | 10 k to GND + jumper pad |
| 1 | VBAT | 3V3 | via 0 Ω (RTC keeps time from SYS-fed 3V3) |
| 8/9 | VSSA/VDDA | AGND/3V3A | ferrite + 1 µF/100 nF |

Firmware note: JTAG must be disabled (SWD retained) before PA15/PB3/PB4 are
used as GPIO. CAN1 uses the PB8/PB9 remap.

## 6. Block circuit details

**Modem (U1, EC200U-CN LCC-144).** Follow Quectel EC200U hardware design
guide reference schematic exactly: VBAT_MODEM at all VBAT pins; PWRKEY and
RESET_N each through NPN (MMBT3904) with 4.7 k base, 47 k base pulldown;
USIM_VDD/DATA/CLK/RST/GND to SIM holder X1 with 33 R series on DATA/CLK/RST,
100 nF on USIM_VDD, ESD array (SMF05C class) at the holder; MFF2 eSIM pads
wired in parallel with 0 Ω selects. USB_DP/DM/VBUS to 4 test pads (FOTA and
Quectel tools) with ESD protection. ANT_MAIN and ANT_GNSS: 50 Ω CPWG, π
matching footprint (DNP 0 Ω center) at each, to two U.FL. NETLIGHT → NPN →
LED. VDD_EXT (1.8 V) powers U8 A-side, 1 µF + 100 nF decoupling.

**IMU (U3).** I2C address pin tied per datasheet; 100 nF + 1 µF; INT1 → PB5.
Mount away from board edge flex zones, axes marked on silk.

**CAN (U4).** TXD/RXD to MCU, VIO=3V3, VCC=5V0, STB → PA15. CANH/CANL:
split termination 2×60 Ω + 4.7 nF to GND via jumper-selectable solder
bridge (default OPEN — machine bus is already terminated), common-mode
choke (51 µH class) + PESD1CAN TVS at connector.

**Digital inputs.** J1.DIx → 24 k series (2×12 k 0805) → OK1/OK2 LED with
antiparallel BAV99; phototransistor emitter to GND, collector to PB12/13
with 47 k pull-up + 100 nF. Valid input 9–100 V.

**Digital outputs.** Q1/Q2 low-side to J1.DOx, SS3200 (200 V) flyback from
DOx to VIN, spec loads: relay coils/buzzers ≤0.5 A at 12/24 V.
NOTE (F-10, approved 2026-09-02): gates are driven from 5V0 through a
two-stage non-inverting NPN driver per channel (no in-stock 150 V SOT-23
NMOS guarantees enhancement at 3.3 V worst-case/cold). Provably OFF when
the MCU pin floats/resets/is unpowered: MCU-side base pulldown + second
stage clamps the gate; 10 k gate pulldown retained. Consequence: DO1/DO2
(like CAN) are inactive during battery-backup operation (5V0 absent).

**Storage (U7).** SPI1 @ 30 MHz+, 100 nF + 1 µF. Firmware: ring buffer with
wear leveling; at 150 B/10 s ≈ 1.3 MB/day → 8 MB ≈ 6 days.

## 7. PCB & housing

4-layer, ~60 × 80 mm, rules per skill file §PCB. HV zone (VIN, dividers,
DI series resistors, DO drains) grouped at connector end with 1.5 mm
clearance and silkscreen boundary. Both U.FL at antenna end, ≥15 mm apart,
GND keepout under FPC antenna region per antenna datasheet. Battery pocket
marked; 4× M3 mounting holes. Housing: off-the-shelf IP65 ABS ≈120×80×40 mm
(Indian supplier, e.g. Hylec/Sunbox class) + PG7 cable gland; lid carries
FPC LTE antenna and GNSS patch on adhesive; alternate drill template for
2× SMA bulkhead (steel-cabinet installs use external antennas).

## 8. Claude Code — setup and execution order

Step 0 — install the skill (user has NOT installed it yet):
```bash
mkdir -p ~/.claude/skills/kicad-telematics
cp SKILL.md ~/.claude/skills/kicad-telematics/SKILL.md
```
Then restart Claude Code; confirm the skill loads. Install KiCad 9,
easyeda2kicad, and the kicad-mcp server exactly as in the skill file.

Execution order (one milestone per session, commit to git each time):
1. Repo + libraries: create `telematics-tracker/` KiCad project, run the
   easyeda2kicad import loop, verify every footprint vs datasheet, log.
2. Schematic sheets in order: power → mcu → storage → io → modem_rf.
   ERC clean after each sheet.
3. Full-design ERC + design review against §5 pin map (list every net and
   check it off).
4. PCB: placement (connector end HV / antenna end RF / center digital),
   stackup, routing, pours, DRC clean.
5. Outputs: gerbers, bom.csv, positions.csv; re-verify stock of every
   C-number; produce 3D renders for user review.
6. STOP for user review before any order is placed.

Kickoff prompt to paste into Claude Code:
```
Read ~/.claude/skills/kicad-telematics/SKILL.md and telematics-handoff.md
in this folder. Set up the environment (KiCad 9, easyeda2kicad, kicad-mcp),
then execute milestone 1 (project + library import + footprint verification)
and show me the design-log before continuing.
```

## 9. Open items Claude Code must ask the user before milestone 4
- Confirm worst-case machine voltage while charging (if truly >90 V
  sustained, review margins; if ≤60 V, the XL7015 cost-down is available).
- Confirm housing model/dimensions actually purchased so PCB outline and
  mounting holes match.
- Confirm DO load types (relay coil voltage/current) to finalize Q1/Q2.
