# Enclosure design notes (Blender parametric model, two variants)

Model: `tools/housing.py` (Blender 5.2 LTS, headless). One script, two
builds:

```bash
blender -b -P tools/housing.py -- internal    # both antennas inside the lid
blender -b -P tools/housing.py -- external    # SMA bulkheads, steel-cabinet build
freecadcmd tools/housing_step.py              # closure check + STEP (lids)
```

Outputs per variant in `docs/housing/<variant>/`: `base.stl`, `lid.stl`,
`lid.step`, `housing.blend`, renders `housing-closed.png`,
`housing-sma-wall.png`, `housing-exploded.png`, `housing-lid-inside.png`,
`housing-base-inside.png`. Renders include reference parts (board, gland and
its locknut, vent, antennas / SMA jacks) that are **not** in the STLs.

Status: **concept for milestone-5 review** — form, features and clearances
are driven by the final board (checked against the board's 3D model, see
"Fit check") and the antenna clearance rules in `docs/installation-sheet.md`
§5a. It is good for 3D-printed prototypes and for quoting; it is not yet a
tooling-ready part (no draft angles, no rib/wall FEA, seal cord and
vent/gland makes not yet selected).

**Sealing target.** The product needs **IP65** (dust-tight, water jets). The
design is drawn to **IP67 intent** (1 m immersion), one step better, because
every opening is a sealed fitting or a compressed gasket: IP65 is met with
margin once the gasket, gland and vent below are fitted, and a prototype
should be jet-tested (IEC 60529 §14.2.5: 6.3 mm nozzle, 12.5 l/min, 3 min at
2.5-3 m) before the design is frozen.

## Why two variants

The handoff's antenna scheme is *internal first, external optional*: both
antennas live in the lid on their 120 mm U.FL pigtails, and the SMA bulkhead
is the "drill option for steel installs". Modelling both as distinct builds
makes the difference explicit:

| | **internal** | **external** |
|---|---|---|
| LTE | FPC BW4GFNX39-15B1 (39.6 × 14.5) in a lid bay | external antenna on SMA #2 |
| GNSS | active patch BWGNSCNX25-25B1Y4L120 (25 × 25 × 6.5) in a lid pocket | u-blox ANN-MB-00 (SMA male, 5 m) on SMA #1 |
| +X wall | solid; two Ø12 SMA seats with **1 mm sealed pilot dimples** only | two Ø6.5 SMA bulkhead holes, each with a Ø9 × 0.4 O-ring recess |
| Lid interior | 8.0 mm deep (patch 6.5 + tabs) | 3.5 mm skirt only |
| Lid height | 10.5 mm | 6.0 mm |
| Base | identical: 112 × 76 × 31.1 mm body (127 × 104 mm over posts and flanges) | identical |

The base is the same mould in both cases; the SMA positions are the same
casting features, drilled through or left sealed. Only the lid differs.

## Common: sealing

Every path through the wall is a sealed fitting or a compressed seal — there
is no open aperture.

- **Perimeter seal**: Ø2.0 silicone O-ring cord in a **2.4 × 1.6 mm groove**
  in the lid rim (82 % groove fill), compressed by a **1.0 × 0.8 mm tongue**
  on the base wall top. Both sit on the wall midline. Target ≈20 % cord
  compression; confirm once the cord hardness is chosen.
- **Six lid screws, all outside the seal line**: four corner posts plus two
  long-side midpoint posts (the long sides are 112 mm — corners alone leave
  the gasket under-compressed mid-span). Ø9 posts, 12 mm × Ø2.5 pilots for
  M3 self-tappers; Ø3.4 countersunk holes in the lid ears. Screws never
  penetrate the seal.
- **Harness**: J1 is the *vertical* (top-entry) Micro-Fit at (7.5, 30); the
  plug mates from above inside the cavity and the loom leaves through an
  **M16 × 1.5 IP68 cable gland** in the −X wall (Ø16.5 hole, Ø22 external
  seat boss, centre 9.4 mm above the board top). The cavity is **5.5 mm wider
  on this side** (1.5 mm elsewhere) so the gland's inner locknut (AF19,
  5 mm) sits entirely between the wall and the board edge — with 1.5 mm it
  reached 1.6 mm below the board surface over R30-R35 (fixed 2026-09-29; the
  script asserts the clearance).
- **Pressure equalisation**: **M12 × 1.5 ePTFE vent plug** in the −Y wall at
  x 20 (Ø12.2 hole, Ø18 seat boss, 11 mm above the board). Its locknut
  clears F1 (3.05 mm tall), whose body starts 3.1 mm from the board edge. A
  sealed box cycling −20…+70 °C otherwise breathes through the gasket every
  day and pulls moisture in.
- **SMA bulkheads (external variant)**: the Ø12 seat face carries a Ø9 × 0.4
  recess so the jack's O-ring is captive under the flange, not just squashed
  against a flat face.

## Common: mechanics

- **Five M3 bosses** at the board's plated holes H1 (3.5, 3.5), H2 (96.5,
  3.5), H3 (3.5, 64.5), H4 (96.5, 64.5) and **H5 (25.63, 60.58)** — H5's boss
  satisfies **F-18**. Bosses OD 8, bored 4.0 for M3 heat-set inserts. Board
  sits 5.0 mm above the 2.5 mm floor; 22 mm clear above the board (set by the
  mated vertical Micro-Fit plus wire bend).
- **Chassis mounting**: two 14 mm flanges (±Y ends, 4 mm thick) with four
  6 × 11 mm slots for M5 chassis bolts.
- **SIM service**: lid-off access; X1 push-push at (70.9, 52.4) faces up.
  Nothing in either lid reaches down toward it.
- **Colour/thermal**: light grey per the product spec (−20…+70 °C operating,
  shade-or-light-coloured rule). Production material: ASA, UV-stable.

## Fit check against the final board (2026-09-29)

From the board's STEP export (every part's 3D box, FreeCAD) against the
model's cavity:

| check | worst part | margin |
|---|---|---|
| height under the 22 mm base rim | J1 header 9.91 mm (datasheet; its plug and wire bend are what the 22 mm is for), L1 8.21 mm | 12.1 mm over J1 |
| depth over the 5.0 mm standoff | C81/C82 2.58 mm (bottom side) | 2.4 mm |
| bottom parts on a boss (OD 8) | none within 0.3 mm | — |
| gland locknut vs board / parts | clear with the 5.5 mm gland-side gap | 0.5 mm to the board edge |
| vent locknut vs parts | clear (F1 body starts at y 3.06) | — |
| SMA jack (external) vs U1 | jack underside 2.9 mm, U1 2.41 mm | 0.5 mm |

Mesh quality: all four STLs are closed, manifold solids (FreeCAD mesh check);
the lids also export as valid STEP solids. The base STEP is not written: the
faceted base solid fails OCC's validity check (near-degenerate triangles at
the boss/bore seams, which slicers ignore), and a broken STEP is worse than
none — a tooling STEP is a CAD redraw anyway (open item 4).

## Internal variant: antenna mounting

Rules applied (installation-sheet §5a, all mandatory): LTE FPC > 5 mm from
the main PCB · GNSS patch ≥ 3 mm from the enclosure wall and ≥ 10 mm from tall
metal · > 40 dB isolation · **no metal fixings over the antenna areas** ·
**mechanical retention, adhesive alone rejected (F-23)**.

- **LTE FPC bay** centred (74, 11): 40.6 × 15.5 × 0.4 mm locating recess in the
  lid ceiling. Retention is a plastic clamp frame **heat-staked** onto four
  Ø1.6 × 2.0 mm posts at the bay corners, plus a strap channel between two
  ribs as a second retention path. No screws. The FPC sits 30 mm above the
  board (22 + 8), far beyond the 5 mm rule, and the LTE U.FL (97.3, 10.2) is
  within the 120 mm pigtail.
- **GNSS patch pocket** centred (86, 40): the 25 × 25 × 6.5 ceramic mounts
  ground-side to the lid ceiling so its radiating face looks up through the
  2.5 mm ASA plate. Four corner L-tabs (1.5 mm thick, 6 mm arms, 0.2 mm
  clearance, 6.7 mm tall) each with a 0.6 mm lip tucked under the ceramic —
  the patch snaps in and is held without metal or adhesive. Patch edge to the
  +X wall inner face is **exactly 3.0 mm** (the script asserts the rule).
  Nearest tall metal is J1 at x 7.5 — far away laterally and 22 mm below.
- **Isolation**: FPC centre to patch centre is ~31 mm, at opposite ends of
  the RF half of the lid. 40 dB is not automatic at this spacing — measure on
  the bench with the modem transmitting at full power.
- **Pigtail clip** between patch and FPC bay keeps the GNSS RG1.13 off the SIM
  bay below.
- Both antennas are field-replaceable service items (F-23): lid off, unclip
  the U.FL, unsnap the patch / lift the clamp frame.

## External variant

- Two **1/4-36 SMA bulkhead jacks** in the +X wall at y 30 (GNSS) and y 44
  (LTE), 14 mm apart so a spanner fits both nuts, centred 6 mm above the
  board top. Ø6.5 holes, Ø12 raised seats, O-ring recess as above.
- Plain lid, 3.5 mm skirt: lower profile, less material.
- Bias-T note: the external active GNSS antenna draws 15 mA at 3.0–5.0 V
  through the coax; L4/R90/C83 must be populated in this build too.

## Known open items (for milestone 5)

1. Seal cord material/hardness → confirm compression with the 1.6 groove and
   0.8 tongue; adjust groove depth if a Ø2.5 cord is preferred.
2. Gland and vent makes/IP ratings (M16 gland cable OD range must cover the
   12-way loom; its locknut must be ≤ AF19 × 5 mm or the gland-side gap grows;
   vent airflow vs. the 112 × 76 × 31 internal volume).
3. FPC clamp frame is referenced but not modelled (flat plastic frame, four
   stake holes).
4. No draft angles / radii — model is machining/print-oriented. For a moulded
   part, redraw in CAD (B-rep STEP) with draft, wall ribs and gate position.
5. Patch tab lips are 0.6 mm: verify snap-in force with the chosen ASA and
   the ceramic's chamfer before tooling.
6. External variant: decide whether the LTE SMA is always fitted or the
   second seat stays sealed (installer's choice per the handoff).
7. LEDs (D13 NET, D20 heartbeat, D21 status) are visible only with the lid
   off; add light pipes if field staff must read them closed.
