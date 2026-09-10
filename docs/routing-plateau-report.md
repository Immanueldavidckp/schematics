# Routing plateau report (path-b gate 5)

Date: 2026-09-10. Board at commit `9c6e512`.
**State: 108 unconnected edges, 0 DRC rule errors. No rule was loosened at
any point.**

## 1. Where the number came from

| stage | unconnected | rule errors |
|---|---|---|
| pre-hybrid (HV/MV/RF locked, LV virgin) | ~450 | 0 |
| hybrid v9 (FreeRouting 1.9.0 + adopt + LV finisher) | 155 | 0 |
| v11: DSN keepout injection + stale-ses guard | 150 | 0 |
| v12: island-tap pass (pour islands bonded to plane stack) | 110 | 0 |
| F-24 tap-via defect fix (C48/C50 ANT stubs) | **108** | **0** |

v12 cycles 1 and 2 both ended at 110 → plateau confirmed → stopped per the
approved gate.

## 2. Root causes already found and FIXED during convergence

1. **Stale-session replay** — a budget-killed FreeRouting writes no `.ses`,
   and the pipeline re-imported the previous cycle's file. Cycles were
   literal replays. Fixed (session moved aside before each run).
2. **DSN model gaps** — FreeRouting cannot see the 0.5 mm board-edge rule or
   the scoped 1.5 mm HV rule; its best copper was legally ripped every cycle.
   Fixed by injecting keepouts (edge strips + HV/MV halos) into the DSN —
   a strictly tighter model.
3. **Split pour islands invisible to the LV router** — KiCad connectivity
   treats a zone as one item; 104 of 150 edges were island splits. Fixed with
   the island-tap pass (bond via inside each anchor-less island).
4. **F-24 generator defect** — C48/C50 pi-shunt tap vias 1.59/1.02 mm off
   their runs. Fixed in generator + board.
5. **LV wall-clock deadline** — the chain's outer `timeout` failed to fire
   (one LV phase ran 15 h). LV now self-caps (`LV_DEADLINE_S`).

## 3. The remaining 108 edges, per net, with cause

Causes are from per-net `LV_DEBUG` flood diagnostics run in isolated
worktrees (each failing child logs its free start/goal cells and the nets
whose copper forms the pocket walls).

### a. Pour-connectivity residue — 57 edges on 2 nets

| net | edges | cause |
|---|---|---|
| 3V3 | 29 | L3 island tracks/pads on the far side of the congested pocket; islands DO hold vias (no orphans left) but the surface stubs from FB1.1, U7.7/8, R7.1, TP6.1 etc. cannot reach any tap site — walls: GND, CAN_SPLIT, MODEM_PWRKEY routed copper at 0.2 mm |
| GND | 28 | 21 small kept fill islands with **no legal via spot** (every free cell misses the L2 plane or another GND fill underneath) plus the C1.2→U2.35 crystal-pocket edge |

### b. The congested pocket — ~40 edges on 40 signal nets

One geographic cluster: **x ≈ 19–42, y ≈ 6–49**, bounded left by the VIN_B
HV belt (1.5 mm halos, immovable), right by U2's LQFP pin field, containing
the crystal cluster (Y1/C1/C2 → OSC_IN/OSC_OUT 4 edges), U7, U4 (CAN), the
DI opto rows and the gate-driver resistors. Typical diagnostics:

- `CAN_STB`, `CAN1_RX`: starts 15/45 free — U2.38/U2.45 pin escapes walled
- `/power/U6_TS`: goals 0/36 free — R88.2 completely enclosed
- `DI1/DI2`: path exists on neither surface layer; walls are GND/5V0/3V3
  routed copper, not HV halos
- `/io/CANH`, `/io/CANL`: goals 392/392 free (J1 pads open) but the flood
  never escapes the pocket

These are honest 2-signal-layer congestion failures: L2 is the solid GND
plane, L3 is power islands, so every signal must resolve on F/B.

## 4. Fallbacks already executed (per the approved sequence)

- **FreeRouting 1.9.x pinned (SHA-256)** — is the production autorouter in
  the hybrid. Converged: a 24-pass 160-min run returns byte-identical results
  to the 8-pass run (163,586 bytes both).
- **6-layer test** — full copy converted to 6 copper layers, FR re-run:
  **143 vs 148** unconnected (4-layer, same conditions). Extra layers do NOT
  unlock the pocket (the walls are pad-entry lanes and pin escapes, which
  exist on the surface layers regardless of layer count).
  **6-layer escalation is NOT recommended — the evidence says it buys ~3%.**

## 5. Recommendation for milestone 5

Small placement relief inside the pocket, then re-run the pipeline
(regeneration is deterministic; HV/RF re-route automatically):

1. Widen the channel between the VIN_B belt and U2 by shifting the
   divider column (R32/R35/R36/R37, x≈2.2 col is fine — it is the
   TP1/TP2/TP4/TP5 test-point row at y 13–30 that plugs the exits).
2. Give the crystal cluster (Y1/C1/C2) its own escape: rotate Y1 90° or move
   C1/C2 0.5 mm outward so OSC_IN/OSC_OUT resolve on B.Cu directly.
3. Re-park TP3/TP6/TP27 (NRST/3V3/MODEM_TX test points) outside x 19–42.
4. Merge the 21 unreachable GND slivers by nudging the F/B GND pour
   clearance-driven gaps: most sit between DI-row pads — a 0.2 mm pour
   min-width increase (fill option, not a clearance rule) removes them as
   kept islands.

Estimated effect: items 1–3 free the pin-escape walls that block ~40 signal
edges; item 4 removes ~21 GND edges without copper changes. Residual risk
stays on 3V3's long pour reach (its L3 island geometry may want one more
finger toward FB1).

## 6. Quality metrics at the plateau

From `docs/lv-route-metrics.txt` (last full LV pass): 19 + 4 + 2 nets routed
across v12 cycles, total vias placed by LV ≈ 63 plus 45 island-tap bonding
vias; flagged nets: 4 with >4 vias (3V3, 5V0, MODEM_PWRKEY, U5_FB), 3 with
length ratio >2.5 (VBAT_MODEM 3.11, U5_FB 2.96, MODEM_RX 4.05) — all
power/bulk nets where the pour carries the current and track length is not
electrical.

Locked copper (RF corridor, HV strip, MV chains) is untouched throughout —
verified by pcbroute_verify.py identity checks each adoption.
