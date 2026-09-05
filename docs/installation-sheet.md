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

## 6. Commissioning check

1. Apply machine power. The status LED indicates network activity.
2. Confirm the unit reports in within 5 minutes of first power-up.
3. Cycle the ignition input and confirm the state change is reported.
4. Record the mounting location and orientation.

---

*Open items before release: final housing model and dimensions; confirmed DO
load types; whether the product ceiling stays at +70 °C or is narrowed to
+60 °C to match typical Li-ion discharge ratings (see handoff §1.1).*
