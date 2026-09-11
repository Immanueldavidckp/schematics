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
