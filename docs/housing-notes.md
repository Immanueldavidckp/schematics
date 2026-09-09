# Enclosure design notes (Blender parametric model)

Model: `tools/housing.py` (Blender 5.2.1 LTS, headless).
Outputs: `docs/housing/base.stl`, `docs/housing/lid.stl`,
`docs/housing/housing.blend`, renders `docs/housing/housing-{iso,front,top}.png`.
Rebuild with `blender -b -P tools/housing.py`.

Status: **concept for milestone-5 review** — form, features and clearances are
driven by measured board facts; it is not yet a tooling-ready part (no draft
angles, no rib/wall FEA, gasket cross-section unselected).

## Dimensions

| Item | Value |
|---|---|
| Board | 82 × 62 × 1.6 mm |
| Cavity | 85 × 65 mm (1.5 mm margin/side), walls 2.5 mm, floor 2.5 mm |
| Standoff (floor → board bottom) | 5.0 mm |
| Clearance above board | 22 mm (see J1 below) |
| Base outside | 90 × 70 × 31.1 mm (+ flanges, + corner posts) |
| Lid | 2.5 mm plate + 3.5 mm skirt pocket |

## Feature → requirement map

- **Five M3 bosses** at H1 (3.5, 3.5), H2 (78.5, 3.5), H3 (3.5, 58.5),
  H4 (78.5, 58.5) and **H5 (23.5, 55)** — H5's boss satisfies **F-18**
  (support under the buck/relay-driver quadrant). Bosses OD 8, bored 4.0 for
  M3 heat-set inserts.
- **J1 harness entry**: J1 is the XUNPU MX3.0-12PZZ **vertical** (top-entry)
  Micro-Fit at (7.5, 30), rot 90 — the mating plug stacks ~17 mm above the
  board plus wire bend, which sets the 22 mm internal height. The harness
  exits through an **M16 cable gland** in the −X wall (Ø16.5 hole, OD 24
  external seat boss, hole centre 9.4 mm above board top) — a sealed gland,
  not an open aperture, keeps the perimeter gasket meaningful outdoors on a
  MEWP. *The earlier idea of a rectangular wall cutout was wrong for a
  vertical header and has been dropped.*
- **Antenna scheme — internal first, external optional** (per handoff §BOM
  ANT row): both antennas are INTERNAL and lid-mounted on U.FL pigtails — the
  LTE FPC and the GNSS ceramic patch (active-capable). The Ø6.5 **SMA
  bulkhead** in the +X wall is the handoff's *"SMA drill option for steel
  installs"*: a U.FL→SMA pigtail replaces the internal antenna feed when the
  tracker is mounted on/behind steel. A second SMA boss with a 1 mm pilot
  dimple (sealed until drilled) sits 14 mm further along the wall so LTE and
  GNSS can both go external on the worst installs.
- **F-23 — mechanical LTE FPC antenna retention in the lid** (adhesive alone
  rejected): two clamp bosses (Ø6, pilot 2.2 for M2.5 self-tap clamp plate)
  at (55, 31) and (75, 31) plus two strap ribs at x 48–50 and 78–80 forming a
  strap/clamp channel across the FPC bay over the RF corridor half of the lid.
- **Gasket groove** 2 × 1.5 mm around the lid skirt midline (IP intent;
  cross-section/material TBD at milestone 5).
- **Lid fixing**: four external corner posts (Ø9) with 12 mm-deep 2.5 mm
  pilots for M3 self-tappers; matching countersinkable Ø3.4 holes in lid ears.
  Posts are outside the gasket line, so lid screws do not penetrate the seal.
- **Chassis mounting**: two 14 mm flanges (±Y ends, 4 mm thick) with four
  6 × 11 mm slots for M5 chassis bolts — slotted for MEWP rail tolerance.
- **SIM service**: lid-off access; X1 push-push faces up, nothing overhangs it
  in the lid (clamp bosses are at y 31; X1 bay is clear).
- **Colour/thermal**: material set light grey per the product spec
  (light-coloured housing, −20…+70 °C operating). Target material for
  production: ASA (UV-stable) in light grey, not ABS.

## Known open items (for milestone 5)

1. Gasket cross-section + groove fill ratio once a cord/molded seal is chosen.
2. Gland make/IP rating (M16, cable OD range must cover the 12-way loom).
3. FPC clamp plate is referenced but not modelled (flat strip, 2 screws).
4. No draft angles / radii — model is machining/print-oriented, not molding.
5. Venting membrane (pressure equalisation, −20…+70 °C swings) not yet placed.
