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

### 1.1 Environmental rating (approved 2026-09-04, governed by U1)

**Rated operating ambient: −20 °C to +70 °C.**
**The housing must be mounted shaded, or be light-coloured.**
**85 °C is a survival limit, not an operating limit.**

This is governed by the **U1 EC200U temperature range**, *Quectel EC200U Series
Hardware Design V1.2*, §5.3 Table 42, p.75 — the most restrictive active part:

| EC200U range | Limits | Meaning (datasheet footnotes 9/10) |
|---|---|---|
| Operating | −35…+75 °C | module **meets 3GPP specifications** |
| Extended | −40…+85 °C | functions maintained, no unrecoverable malfunction, but *"one or more specifications, such as Pout, may exceed the specified tolerances of 3GPP"* |
| Storage | −40…+90 °C | — |

So the +70 °C rating keeps 5 °C of margin to the top of the **3GPP-compliant**
window, and 85 °C lands exactly on the **extended** limit — where the modem
still works but is out of spec. Hence the wording: survival, not operating.
The −20 °C floor is a product choice for the India target (the module itself
goes to −35 °C), taken to leave margin rather than to chase it.

The 5 °C top margin is thin *on purpose* and is why the housing rule exists:
internal rise above ambient (modem transmit bursts, buck losses, charger) plus
solar gain on a dark enclosure on an exposed boom lift can easily exceed it.
Shading or a light/reflective housing is a **specification requirement, not a
recommendation** — it must appear on the installation sheet.

**Open item — BT1 vs the +70 °C ceiling.** Typical 1S Li-ion cells are rated
−20…+60 °C on *discharge* and 0…+45 °C on *charge*, both narrower at the top
than +70 °C. Charging is already protected: the BQ25606 TS pin runs the JEITA
network (R88/R89 + the in-pack NTC), so charge is inhibited outside the cell's
window automatically. Discharge above 60 °C and calendar life at sustained high
temperature are **not** protected by hardware, and are the reason BT1 is
specified as a 2–3 year field-replaceable service item (rule 2). Flag for the
user: confirm this is acceptable, or narrow the product rating to +60 °C.

## 2. Five-year & scaling design rules (non-negotiable)

1. No electrolytic or tantalum capacitors. Ceramic X7R/X7S only, voltage
   derated ≥2:1 (100 V rail parts rated 100 V minimum with TVS clamping).
2. **Field-replaceable / service items — three parts, all temperature-limited:**
   the backup battery (1S Li-ion on a JST-PH-2+NTC 3-pin JST-XH connector,
   never soldered, 2–3 year interval) **and both antennas** (lid-mounted on
   U.FL pigtails, F-23). These are the parts whose life is set by temperature
   rather than by design margin, and all three are reachable without
   unsoldering anything.
3. MCU can hard power-cycle the modem: high-side P-FET switch on modem VBAT
   driven by MCU GPIO. A hung modem must never brick a deployed unit.
4. Independent watchdog (IWDG) always on; brown-out detector enabled.
5. OTA path: modem DFOTA for its own firmware + custom MCU bootloader in
   external flash for application FOTA.
6. Temperature: all semiconductors ≥105 °C rated where available (AT32 is
   −40…+105 °C). **Conformal coating is MANDATORY on every board, including
   prototypes — it is a safety-critical process requirement, not a finish
   preference. Creepage at U5 depends on it (see F-20 below).**
7. Scaling/second-source: CAN transceiver pad-compatible alternates
   (SIT1051 ↔ TJA1051T/3 ↔ TCAN1042), IMU footprint fixed to QMI8658
   (LGA-14), dual SIM footprint — nano-SIM holder AND MFF2 eSIM pads in
   parallel with 0 Ω selects, for future soldered-eSIM scaling.
8. Test points on every rail, SWD, both UARTs, CAN, and a 4-pad bed-of-nails
   friendly layout for a production test jig. PLUS the modem USB pair and
   VBUS (TP15/16/17): USB is the EC200U's only firmware-recovery path, so
   losing it bricks field units - approved addition, 2026-09-06.
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

### 6.1 F-20 — conformal coating is creepage-critical (confirmed 2026-09-05)

**U5's exposed pad (EG11752 pin 9) is VIN_B, at up to 100 V, and the SOIC-8
package places its own signal pins 0.55 mm away.** Measured from the footprint:
EP 3.30 × 2.40 mm centred, signal pads at y = ±2.72 with 1.94 mm height, so
their inner edges sit at ±1.75 against an EP edge at ±1.20. No layout can widen
this — it is the package.

| condition | IPC-2221 requirement at 100 V | actual |
|---|---|---|
| external, **uncoated** (B1) | 0.60 mm | 0.55 mm — **FAILS** |
| external, **coated** (B4) | ≈0.25 mm | 0.55 mm — passes, >2:1 margin |

**The board only meets creepage once coated.** Therefore:
1. Conformal coating is **mandatory in production and on prototypes**.
2. **Prototypes must be coated before the 100 V / 85 °C burn-in.**
3. The **U5 area is a coating inspection point**, marked on the assembly
   drawing (F.Fab) as `COATING INSPECTION - CREEPAGE CRITICAL (F-20)`.
4. An uncoated board relies on the package's certified spacing alone and
   **must not be energised at line voltage.**
5. The 0.3 mm DRC exception in `telematics-tracker.kicad_dru` is scoped to the
   `HV_ZONE` rule area and is written against the **coated** figure. If the
   coating requirement is ever dropped, that exception becomes invalid and U5
   must be reconsidered.

### 6.2 F-23 — antennas in the 85 °C survival tier (ACCEPTED 2026-09-05)

Both selected antennas are rated **−45 to +85 °C for OPERATING *and* STORAGE**
— the two ranges are identical, verified verbatim in both datasheets:

| | operating | storage |
|---|---|---|
| LTE C496569 (工作温度 / 存储温度) | −45…+85 °C | −45…+85 °C |
| GNSS C784386 | −45…+85 °C | −45…+85 °C |

Against the product spec (§1.1):

| | product | antennas | margin |
|---|---|---|---|
| operating max | +70 °C | +85 °C | **+15 °C — OK** |
| survival max | +85 °C | +85 °C | **ZERO** |

**The 85 °C survival limit sits exactly on the antennas' rated maximum**, and
neither vendor publishes an excursion rating, a derating curve or any
life-versus-temperature data. A sealed IP65 ABS lid in Indian sun can exceed
85 °C internally, and the antennas are mounted *in the lid* — the hottest part
of the enclosure.

This makes the antennas the weakest thermal link in the design and reinforces
two existing requirements rather than adding a new one: the housing **must** be
shaded or light-coloured (§1.1), and antenna retention **must** be mechanical
(below). **Bench soak at 85 °C is required before release.**

**ACCEPTED.** The antennas join the **85 °C survival tier already set by U1**,
whose extended range tops out at the same +85 °C — so the tier is defined
consistently by three parts, not by the antennas alone. Two consequences,
both now binding:

1. **Both antennas are field-replaceable service items** alongside BT1
   (rule 2).
2. **85 °C soak is part of prototype qualification, with GNSS C/N0 measured
   before and after.** C/N0 is the right metric because it is what an ageing
   patch or a degraded LNA actually loses; a pass/fail "does it still get a
   fix" would miss gradual degradation.

### 6.3 Antenna retention — mechanical, not adhesive

**Antennas must be mechanically retained in the lid. Adhesive alone is not
acceptable.** Quectel Antenna Design Guide V3.3 §3.1 note 3:

> "As effectiveness of the adhesive (usually 3M adhesive is used) will be
> weakened under high ambient temperature, heat staking or other mounting
> methods should be used to fix the FPC antenna."

At +70 °C rated ambient — and with the lid the hottest surface — a 3M-backed
FPC will creep and eventually detach. Acceptable methods: heat staking, a
moulded clamp or rib, a screwed retainer, or a captive pocket in the lid.
Note also that **C496569's own datasheet gives its mount as 压扣 (crimp)**, not
adhesive; any 3M backing on that part is unverified.

**This is a housing selection criterion**, not just an assembly instruction: the
chosen enclosure must provide the retention features, so it cannot be a plain
smooth-lidded box.

## 7. PCB & housing

4-layer, ~60 × 80 mm, rules per skill file §PCB. HV zone (VIN, dividers,
DI series resistors, DO drains) grouped at connector end with 1.5 mm
clearance and silkscreen boundary. Both U.FL at antenna end, ≥15 mm apart,
GND keepout under FPC antenna region per antenna datasheet. Battery pocket
marked; 4× M3 mounting holes. Housing: off-the-shelf IP65 ABS ≈120×80×40 mm
(Indian supplier, e.g. Hylec/Sunbox class) + PG7 cable gland; lid carries
FPC LTE antenna and GNSS patch **mechanically retained — heat stake, clamp or
captive pocket, NOT adhesive alone (see §6.3)**; alternate drill template for
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
