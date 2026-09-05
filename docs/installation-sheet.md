# MEWP Telematics Tracker — Installation Sheet

Draft, revision A · created 2026-09-04 · applies to Variant A (LTE Cat-1 bis +
GNSS, single CAN, 9–100 V front end)

> This sheet is the field-facing document. It exists so the environmental and
> wiring limits that the hardware relies on are actually stated to the person
> mounting the unit. Keep it in sync with `telematics-handoff.md`.

---

## 1. Mounting location — environmental limits

**Rated operating ambient: −20 °C to +70 °C.**

**The unit must be mounted in shade, or the housing must be light-coloured.**

**85 °C is a survival limit, not an operating limit.** Above +70 °C ambient the
modem is outside its 3GPP-compliant range: it keeps working, but transmit power
and other RF specifications drift out of tolerance, so data may be delivered
late or not at all until it cools. Nothing is damaged, and normal operation
resumes by itself once the temperature falls back into range.

Why this matters in practice: a dark enclosure in direct sun on an exposed
boom lift can run 20–30 °C above air temperature from solar gain alone, before
the unit's own heat (modem transmit bursts, buck converter, battery charging)
is added. A 40 °C day in direct sun on a black box is already over the limit.

**Do:**
- mount inside the chassis, under a cover, or on a shaded face
- prefer a north-facing or downward-facing surface (northern hemisphere)
- keep the housing light-coloured if any sun exposure is unavoidable
- allow air movement around the housing where possible

**Do not:**
- mount on a dark horizontal surface in full sun
- mount against a hot surface — engine bay, hydraulic tank, exhaust run
- wrap or box the unit in insulating material
- paint the housing a dark colour

## 2. Battery (BT1)

The internal backup cell is a **field-replaceable service item on a 2–3 year
interval** — it is on a connector, never soldered.

High temperature is the main thing that shortens its life. Charging is
protected automatically: the charger reads the in-pack thermistor and stops
charging when the cell is outside its safe window, so a hot unit simply will
not charge until it cools. Sustained operation near the top of the ambient
range will still age the cell faster and may shorten the replacement interval.

Replace with the specified 1S Li-ion pack **with NTC and JST lead** only. A
pack without the thermistor will not charge.

## 2a. Conformal coating (do not remove)

Every board is conformal coated, and the coating is part of the unit's
electrical safety, not a cosmetic finish — the 100 V section relies on it for
creepage. Do not scrape, solvent-clean or rework the coating in the field. If a
board is opened and the coating is damaged, the unit must be returned rather
than re-fitted.

## 3. Supply wiring

- Guaranteed input range: **10.5 V to 100 V DC**. Below 10.5 V the unit runs
  from its backup battery — this is expected behaviour during cranking dips,
  not a fault.
- Observe polarity. The unit is reverse-polarity protected but will not
  operate reversed.
- Fuse the supply feed at the machine end in addition to the unit's internal
  fuse.
- **CAN and both digital outputs are inactive while running on backup
  battery** (they are powered from the 5 V rail, which requires machine
  power). Ignition sensing, GNSS, LTE and logging continue.

## 4. Digital inputs / outputs

- Digital inputs DI1/DI2: valid input range **9–100 V**, optically isolated.
- Digital outputs DO1/DO2: low-side switches, rated for **relay coils and
  buzzers up to 0.5 A at 12/24 V**. Inductive loads are fine — flyback
  clamping is built in. Do not drive a load returning to a different supply.

## 5. Antennas

- Two internal antennas: LTE (FPC, on the lid) and GNSS (patch, on the lid).
- Keep the lid free of metal fixings over the antenna areas.
- For steel-cabinet installations use the external-antenna drill option and
  fit both bulkhead antennas outside the cabinet — a closed steel enclosure
  will prevent both GNSS fix and LTE registration.

## 5a. Antenna metal clearance and separation — HOUSING REQUIREMENTS

These are requirements on the **housing and the installation**, not on the PCB.
Both antennas mount in the lid and reach the board only through a U.FL
pigtail, so there is no board copper underneath either of them.

From *Quectel EC200U Series Hardware Design V1.2*, §4.4.1 Table 39
"Antenna Requirements":

| requirement | value |
|---|---|
| **Isolation, GNSS to LTE antenna** | **> 40 dB** |
| GNSS frequency range | 1559–1609 MHz |
| GNSS polarisation | RHCP or linear |
| GNSS VSWR | ≤ 2 (typ.) |
| GNSS efficiency | > 30 % |
| Passive GNSS antenna gain | > 0 dBi |
| Active GNSS antenna: noise factor | < 1.5 dB |
| Active GNSS antenna: gain | > 0 dBi |
| **Active GNSS antenna: internal LNA gain** | **< 17 dB** |
| LTE cable loss | < 1 dB below 1 GHz, < 1.5 dB 1–2.3 GHz, < 2 dB above 2.3 GHz |

**The > 40 dB isolation figure is the one that constrains the lid.** Both
antennas sit in the same lid of a ~120 × 80 mm housing, and 40 dB of isolation
between two antennas that close is not automatic — it drives how far apart and
in what orientation they are mounted. Confirm by measurement on the first
build; it is not something the PCB layout can fix afterwards.

On the board the two U.FL launches are **38.3 mm apart** (handoff §7 asks for
≥ 15 mm), so the board side is not the limiting factor.

### Selected antennas and their clearance figures

**LTE — Bat Wireless BW4GFNX39-15B1, LCSC C496569** (5,536 stock, $0.383 @250)
39.6 × 14.5 mm FPC · **700–2700 MHz continuous** · RG1.13 coax, **120 mm**,
IPEX-1 · 2.8 dBi typ · VSWR < 2.1 · −45…+85 °C.

**GNSS — Bat Wireless BWGNSCNX25-25B1Y4L120, LCSC C784386** (942 stock,
~$1.53 @250) 25 × 25 × 6.5 mm patch · IPEX-1, RG1.13, **120 mm** · RHCP ·
1575 ±5 / 1561 ±5 MHz · **ACTIVE, internal LNA 21.5 dB, 1.8–3.6 V, 4.3 mA** ·
−45…+85 °C.

**External active GNSS (steel-cabinet option) — u-blox ANN-MB-00**
LNA 28 ±3 dB · 3.0–5.0 V, 15 mA · SMA male · RG174, 5.0 m · magnetic base
+ 2 × M4 · −40…+85 °C. Not LCSC-stocked; order from Digi-Key/Mouser/Farnell.

### Clearance requirements — MANDATORY

**Neither antenna datasheet publishes a numeric clearance figure.** Both were
searched in full, in English and Chinese (净空 / 间距 / 距离 / 金属); the only
mounting line in the LTE sheet is `安装方式 / Mount way: 压扣`. The figures
below therefore come from **Quectel**, which does specify them:

| requirement | value | source |
|---|---|---|
| **LTE FPC to the main PCB** | **> 5 mm** | Antenna Design Guide V3.3 §3.1 note 2 p.14 |
| **GNSS patch to any tall metal component** | **≥ 10 mm** | GNSS Antenna Application Note V1.0 §4.2.3 |
| **GNSS patch to the enclosure wall** | **≥ 3 mm**, enclosure non-metal near the antenna | GNSS Antenna Application Note V1.0 §4.2.3 |
| GNSS to LTE antenna isolation | > 40 dB | HW Design V1.2 §4.4.1 Table 39 |

Verbatim, Antenna Design Guide V3.3 §3.1 note 2:
> "Keep the distance between antenna and the main PCB more than 5 mm (for a
> particular distance, refer to the evaluation result of the antenna supplier)."

Verbatim, GNSS Antenna Application Note V1.0 §4.2.3:
> "Maintain at least 10 mm distance between the patch antenna and other tall
> metal components to prevent adverse impacts on antenna performance."
> "Device enclosure should be made of non-metal materials, particularly in the
> vicinity of the antenna area. The minimum distance between antenna and
> enclosure is 3 mm."

### Antennas are service items

Both antennas are rated **−45 to +85 °C for operating AND storage** (the two
ranges are identical in both datasheets). Against this product:

| | product | antennas |
|---|---|---|
| operating max | +70 °C | +85 °C — 15 °C margin |
| **survival max** | **+85 °C** | **+85 °C — ZERO margin** |

Neither vendor publishes an excursion rating or a derating curve. **The
antennas are among the first things that will age in a hot install**, and they
sit in the lid, which is the hottest part of the enclosure.

**Both antennas are field-replaceable service items**, like the battery. They
are on U.FL pigtails and can be swapped without unsoldering anything. If GNSS
fix quality degrades over time in a hot installation, the antenna is the first
thing to replace — not the board. This is also the strongest practical reason
to obey the shading rule in §1.

### Antenna retention MUST be mechanical

Quectel Antenna Design Guide V3.3 §3.1 note 3:
> "As effectiveness of the adhesive (usually 3M adhesive is used) will be
> weakened under high ambient temperature, heat staking or other mounting
> methods should be used to fix the FPC antenna."

This unit is rated to **+70 °C ambient** and the lid is the hottest part of the
enclosure. **Adhesive alone is not an acceptable retention method for either
antenna.** Use heat staking, a moulded clamp or rib, a screwed retainer, or a
captive pocket in the lid. C496569's own datasheet gives its mount as
**压扣 (crimp)**, not adhesive; any 3M backing on that part is **UNVERIFIED**.

If an antenna detaches in service it will hang on its coax, detune, and
eventually break the U.FL — an intermittent-GNSS fault that is very hard to
diagnose in the field. Retention is worth getting right.

## 6. Commissioning check

1. Apply machine power. The status LED indicates network activity.
2. Confirm the unit reports in within 5 minutes of first power-up.
3. Cycle the ignition input and confirm the state change is reported.
4. Record the mounting location and orientation.

---

*Open items before release: final housing model and dimensions; confirmed DO
load types; whether the product ceiling stays at +70 °C or is narrowed to
+60 °C to match typical Li-ion discharge ratings (see handoff §1.1).*
