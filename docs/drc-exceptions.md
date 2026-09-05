# DRC exceptions — Milestone 4 floorplan pass

Generated from `drc-placement.rpt` by `tools/build.py`.
**Routing has not started.**

**485 items** (33 violations
+ 452 unconnected). First placement pass was 896.

**Zero courtyard overlaps, zero shorting items, zero solder-mask bridges,
zero annular-width, padstack, hole-to-hole or dangling-via errors.**

| count | type | classification |
|---|---|---|
| 452 | `unconnected_items` | **EXPECTED** — nothing is routed. Clears with routing. |
| 20 | `clearance` | see breakdown below |
| 8 | `silk_over_copper` | **WAIVED** — vendor footprint silk graphics touching their own pads. All reference designators are on F.Fab, so nothing here affects assembly or the CPL. |
| 3 | `isolated_copper` | **EXPECTED** — the three L3 pours have no vias landing in them yet. Clears with routing. |
| 2 | `silk_overlap` | **WAIVED** — residual footprint silk graphic overlaps. |

## Clearance breakdown

| count | rule | classification |
|---|---|---|
| 18 | `HV to signal 1.5mm` | **WAIVED** — these components *are* the HV-to-LV transition. See below. |
| 1 | `netclass 'Default'` | **WAIVED** — X1 internal pad spacing, vendor footprint. |
| 1 | `netclass 'HV'` | **OPEN** — review individually. |

### Why the HV-to-signal items are waived

The 1.5 mm figure is a **zone separation** requirement (handoff §7),
enforced inside the `HV_ZONE` rule area. The parts below straddle the
boundary by design, so they necessarily have an HV pad near an LV pad.

**Within one component (5):** `R40`, `R35`, `R32`, `Q2`, `Q1` — sense-divider resistors and
the DO low-side FETs. A divider's tap is by definition low voltage while
its top end is at line voltage. Mitigation is already in the design: the
VIN and IGN dividers are 3×100k in series so no single resistor carries
the full 100 V (R40 is the DNP spare and is a single resistor).

**Between adjacent boundary components (13):** `R34+R40`, `Q2+R31`, `Q1+R30`, `F1+Q1`, `R40+TP9`, `R32+R33`, `R17+R32`, `R19+R35`, `D8+OK1`, `D7+OK2`.
Opto isolators with their series chains, DO FETs with their gate
resistors, divider chains. The isolation barrier is the opto's own
certified creepage, not board spacing.

**These are waivers, not fixes.** They depend on the conformal-coating
requirement (SKILL.md P1) and on the silkscreen HV boundary remaining on
the board as the installer-visible marking.
