# Routing endgame report — milestone-5 decision package

Date: 2026-09-11. Board at the latest `main` commit.
**State: 136 unconnected edges over 69 nets, 0 DRC rule errors.
No rule was loosened at any point.**

## 1. Convergence history (all states committed, all reversible)

| state | unconnected | note |
|---|---|---|
| hybrid v9 fixed point | 155 | stale-ses replay + DSN gaps (both fixed) |
| v12 with fixes | 110 | island taps: +40 edges in one pass |
| pocket restart | — | 50 signal nets routed clean from a cleared pocket, incl. every historic hard net (crystal, SWD, CAN, DI, MCU escapes) |
| pour landing + fingers + scrubber | 134 | best committed count |
| mop-up v3 (full toolkit) | 136 | churn-neutral: the floor |

## 2. What was tried (and is now permanent tooling)

- FreeRouting 1.9.0 with a corrected model (edge/HV/MV keepouts, fresh-ses
  guard): converged — 24 passes = 8 passes, byte-identical.
- **6 copper layers: tested, ineffective** (143 vs 148 on identical
  conditions). The blocker is pad-entry/pocket density on the SURFACE
  layers, which more inner layers cannot relieve. Not recommended.
- Maze router upgrades, all live in `tools/pcbroute_lv.py`: corner-cut A*,
  exact per-cell sibling lanes, 12-pair search, island taps, seal-targeted
  rip-retry negotiation, window restart, foul scrubber in the batch gate.
- Placement micro-relief round 1: six test points moved out of the pocket
  (validated: SWD/debug nets route now); 3V3 L3 reach fingers added.

## 3. What remains and why

The 136 edges concentrate in the pocket **x ≈ 19–42** between the VIN_B HV
belt (1.5 mm halos, immovable) and U2/U7/U4/U6:

- **3V3 (19), GND (17), 5V0 (9), SYS (5+3)**: decoupling caps and power pins
  whose pads are sealed by legally-routed neighbours; the L3 under them
  belongs to other rails, so tap-down is impossible and lateral entry has no
  legal lane at 0.20 mm clearance.
- **~40 signal nets at 1–3 edges** (SIM level shifter, U6 charger satellites,
  DI/DO chains, CAN pair): same mechanism, measured per net by flood
  diagnostics (`DEBUG pad seal` / `pocket walls` in the LV logs).

This is placement density, not router weakness: the pocket-restart experiment
routed 50 of these nets cleanly the moment the pocket was cleared — the
geometry admits a solution only when the right nets get the lanes, and there
are ~10% more lane-demands than lanes.

## 4. Options (decision requested)

**A. Placement relief round 2 — recommended.** Spread the pocket by ~1–2 mm:
the C10/C11/C12/C21/C24 decoupling column, the U6 charger satellites
(R85–R89, L3), the SIM level shifter (U8) cluster, and re-park TP4. Then
regenerate and let the now-hardened pipeline route from scratch (it routed
the hard 50 first-try on a clean pocket). Estimated: a few hours of layout
work + up to a day of pipeline time. Risk: moderate — the board has spare
area east and south of the pocket.

**B. 6-layer respin — not recommended.** Measured gain ≈ 3%; cost is real
(stackup, impedance re-work, fab price). Evidence in
`docs/routing-plateau-report.md` §4.

**C. Ship milestone 4 with the exception list as-is — not viable.** 136 open
edges are real electrical absences (unconnected decoupling, split rails),
not cosmetic exceptions.

## 5. Assets

- `docs/renders/endgame-top.png` — current top view.
- `docs/lv-route-metrics.txt` — per-net metrics + unrouted causes.
- Memory/process learnings in the design log; all tooling committed.


---

# Addendum 2026-09-15 — pipeline repaired; the floor is now measured honestly

**State: 109 unconnected edges, 0 DRC rule errors** (from 174 at the start of
the day). No rule loosened.

## What was actually broken (and is fixed)

1. `zones_intersect` on the 3V3 L3 fingers (priority never set) named net 3V3
   and aborted every adopt with `ADOPT_BASELINE_NOT_CLEAN`.
2. The autoroute scratch had **no `.kicad_dru`** and a stale `.kicad_pro`.
   Adopt's DRC of it saw a phantom X1 pad-to-pad clearance naming GND, and
   ripped the whole GND net **every cycle** (v12 logs: identical rip set);
   its zone refill also ran without the rules (468 hidden violations).

With both fixed, FreeRouting adopts with an **empty rip set** and every gain
sticks. The earlier "FR converged at 24 passes = 8 passes" finding was
measured through the broken adopt and should be disregarded.

## Convergence today

| step | unconnected |
|---|---|
| start (v13 board) | 174 |
| LV finisher: GND pour taps, 47 vias | 131 |
| FR 8 passes -> adopt (clean) | 120 |
| LV finisher: GND +13 vias | 114 |
| FR 20 passes -> adopt (clean) | 111 |
| LV finisher (40 min): GND +2 vias, CANL fragment | **109** |

Both engines are at their floor on this placement: FR 20 passes bought 3
edges; the LV finisher fails 67/68 remaining nets with `no path` and the
A/B on the pre-fix board fails identically, so this is geometry, not tooling.

## Where the remaining edges are

72 % of pad edges are in the pocket x 19-42. **U2 alone accounts for 26
edge-halves**, and they are its WEST column (x 25.25: BOOT0, I2C1_SCL/SDA,
SWCLK, CAN_STB, CAN1_RX/TX, GND) and NORTH row (y 17.97: DI1, DI2, DO1/DO2
gates, MODEM_TX/RX/RI/DTR). Every west-column net must escape SOUTH to
U4 (24, 44), JP1 (22, 49) or U3 (29, 55) - and **U7 (SPI flash) sits at
(23.4, 34.2), squarely in that corridor**, ringed by C10/C11/C24/C28 and
R21/R25/R43/R46. Meanwhile U2's SPI pins are on its EAST side (x 33.47), so
SPI1_MISO/MOSI must cross the whole pocket to reach U7 - two of the 67
failures are exactly those nets.

## Recommendation: placement relief round 3 = move U7 east of U2

Front-side x 43-52, y 12-24 is **empty** (only back-side test points TP3,
TP6, TP27 under it). Place U7 at about (46, 18) front, its four passives with
it. Effects: SPI1_* shrink from ~17 mm cross-pocket to ~10 mm direct; the
U2 west corridor gains ~5 mm of width for the 12 south-bound nets; nothing
in the RF corridor (x >= 76.8) or the HV strip is touched. Then regenerate
and run the repaired pipeline (FR -> adopt -> LV, ~1.5 h per cycle now).
Secondary candidates if U7 alone is not enough: C6/C28/C25 decoupling column
at x 28.3 (rotate to the east side of U2), and TP4 at (22, 20.6).

This is a placement change and is held for the same approval as round 2.
