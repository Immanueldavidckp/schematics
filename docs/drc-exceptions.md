# DRC exceptions — Milestone 4 floorplan pass

Generated from `drc-placement.rpt` by `tools/build.py`.
**Routing has not started.** Every item below is either expected at this
stage or a justified exception; the ones that are neither are called out
as OPEN.

**518 violations total** (down from 896 on the first placement pass).

| count | type | classification |
|---|---|---|
| 450 | `unconnected_items` | **EXPECTED** — nothing is routed. Clears with routing. |
| 30 | `silk_over_copper` | **WAIVED** — vendor footprint silk graphics touching their own pads. Inherent to the imported footprints; trimmed or waived at release. |
| 24 | `clearance` | see the breakdown below |
| 8 | `silk_overlap` | **WAIVED** — residual silk graphic overlaps. All reference designators were moved to F.Fab, so nothing here affects assembly or the CPL. |
| 3 | `courtyards_overlap` | **OPEN** — 3 remaining, all in the buck cluster. See below. |
| 3 | `isolated_copper` | **EXPECTED** — the three L3 pours have no vias landing in them yet. Clears with routing. |

## Clearance breakdown

| count | rule | classification |
|---|---|---|
| 17 | `HV to signal 1.5mm` | **WAIVED — the HV/LV transition boundary itself.** See below. |
| 5 | `U5 package internal HV spacing` | **WAIVED — F-20.** EG11752's exposed pad is VIN_B at up to 100 V and the SOIC-8 puts its own signal pins 0.55 mm away. Not fixable by layout. Conditional on conformal coating (handoff rule 6): the coated B4 requirement at 100 V is ~0.25 mm. |
| 1 | `netclass 'Default'` | **OPEN** — 1 item (X1 internal pad spacing, vendor footprint). |
| 1 | `netclass 'HV'` | **OPEN** — 1 item. |

### Why the 1.5 mm HV-to-signal hits are waived

The 1.5 mm figure is a **zone separation** requirement (handoff §7). The
parts below *are* the high-voltage-to-low-voltage transition, so they
necessarily have an HV pad and an LV pad close together:

**Within a single component (5):** `R35`, `R40`, `R32`, `Q2`, `Q1` — divider resistors and the DO low-side FETs. A divider's tap is by
definition low voltage while its top end is at line voltage, and the
FETs have an LV gate against an HV drain. The mitigation is already in
the design: the sense dividers are 3x100k in series so no single
resistor carries the full 100 V (R40 is the DNP spare and is single).

**Between adjacent boundary components (12):** `R34+R40`, `Q2+R31`, `Q1+R30`, `R32+R33`, `R19+R35`, `R17+R32`, `F1+Q1`, `D8+OK1`, `D7+OK2`.
These are the opto isolators with their series chains, the DO FETs with
their gate resistors, and the divider chains. The isolation barrier is
the opto's own certified creepage, not board spacing.

**These are waivers, not fixes.** They should be reviewed against the
conformal-coating requirement before release, and the silkscreen HV
boundary must remain on the board as the installer-visible marking.

## OPEN items to resolve before routing

- `courtyards_overlap` — @(35.7300 mm, 4.6900 mm): Footprint U5 / @(27.6500 mm, 11.3900 mm): Footprint L1
- `courtyards_overlap` — @(27.6500 mm, 11.3900 mm): Footprint L1 / @(29.7900 mm, 3.9800 mm): Footprint C74
- `courtyards_overlap` — @(29.7900 mm, 3.9800 mm): Footprint C74 / @(29.7700 mm, 2.6500 mm): Footprint C73

All three are the **buck cluster**: L1 is a 12.3 x 12.3 mm shielded
inductor and U5 / D16 / C73 / C74 have to sit tight around it to keep the
switching loop small (placement amendment (a)). The power zone is
22.25 x 26 mm and the anchors alone need ~380 mm2 with gaps. This is a
genuine density limit, not a packing bug: it needs either a physically
smaller inductor, or a larger board, or accepting the overlap where the
courtyards touch but the copper does not. **Decision needed.**
