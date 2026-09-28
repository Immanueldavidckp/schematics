# Hand-routing worksheet - T3 board (100 x 68 mm, relief round 7)

> **2026-09-29: done - nothing left to route by hand.** Every connection below was closed by the
> tools and the hand routes in `tools/manual_routes.py`; see design-log.md, 2026-09-29.


41 open connections on 25 nets, generated from the
DRC report of the board on branch `relief6-stretch` (commit "Relief round 7: T3 board ... unconnected=41 errors=0").

Coordinates are KiCad board coordinates in mm (X to the right, Y downwards - the
numbers in the editor's status bar). F = top copper (F.Cu), B = bottom copper (B.Cu).
Tick a line when its ratsnest line has disappeared.

Order: (1) programming / debug / modem UART first, so the board can be flashed and
talked to even if something else is left; (2) power, ground, crystal; (3) the rest.

## 1. Programming, debug, modem control (do these first)

- [ ] **/modem_rf/USB_DM_M** (1 connection)
    - U1.70 at (72.0500, 14.9500) F  <->  D15.3 at (88.4550, 54.3360) F
- [ ] **/modem_rf/USB_DM_TP** (1 connection)
    - TP16.1 at (80.7975, 46.2962) B  <->  D15.4 at (88.4550, 52.0360) F
- [ ] **/modem_rf/USB_DP_M** (1 connection)
    - U1.69 at (73.3500, 14.9500) F  <->  D15.1 at (86.5550, 54.3360) F
- [ ] **/modem_rf/USB_DP_TP** (1 connection)
    - TP15.1 at (77.7975, 46.2962) B  <->  D15.6 at (86.5550, 52.0360) F
- [ ] **MODEM_PWRKEY** (1 connection)
    - U2.29 at (36.1400, 24.3800) F  <->  R55.1 at (87.8125, 60.4950) F
- [ ] **MODEM_TX** (1 connection)
    - U8.13 at (70.9600, 48.3000) B  <->  track at (67.8535, 24.9900) B,

## 2. Power, ground, crystal

- [ ] **/mcu/3V3A** (1 connection)
    - track at (29.4825, 32.9182) PWR_L3,  <->  U2.9 at (36.6400, 32.6000) F
- [ ] **/modem_rf/VDD_EXT_1V8** (2 connections)
    - track at (59.0134, 25.2551) GND_L2,  <->  track at (61.3199, 23.7716) F,
    - C44.1 at (69.7500, 2.2750) F  <->  C45.1 at (73.2500, 2.2750) F
- [ ] **3V3** (2 connections)
    - track at (41.5000, 28.2750) F,  <->  U2.24 at (39.5000, 25.7400) F
    - track at (61.3500, 15.5500) F,  <->  track at (64.2700, 18.9800) B,
- [ ] **5V0** (3 connections)
    - track at (38.0625, 42.4950) F,  <->  track at (33.8925, 43.3239) PWR_L3,
    - R44.1 at (41.4425, 35.2300) B  <->  track at (39.6168, 39.6890) F,
    - track at (48.0480, 42.6592) GND_L2,  <->  track at (39.6153, 41.1925) F,
- [ ] **GND** (12 connections)
    - zone L2_GND_solid at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone L2_GND_solid at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)

## 3. Remaining signals

- [ ] **/io/CANH** (1 connection)
    - track at (23.4176, 33.6550) PWR_L3,
- [ ] **/io/CANL** (1 connection)
    - track at (23.5500, 34.0450) F,
- [ ] **/io/IGN_SENSE** (1 connection)
    - R35.2 at (2.2000, 33.8375) F  <->  track at (25.0000, 30.2750) F,
- [ ] **/io/VIN_SENSE** (1 connection)
    - via at (20.4688, 27.4789) F  <->  R32.2 at (2.2000, 20.1875) F
- [ ] **/mcu/NET_STATUS_LED** (1 connection)
    - track at (30.2871, 21.7594) GND_L2,  <->  track at (21.4284, 31.3432) GND_L2,
- [ ] **/modem_rf/GNSS_BIAS** (1 connection)
    - L4.2 at (98.7850, 38.0000) F  <->  C83.1 at (94.1500, 45.5700) F
- [ ] **/modem_rf/NETLED_K** (1 connection)
    - D13.1 at (79.2375, 45.7750) F  <->  Q12.3 at (90.4125, 57.2450) F
- [ ] **/modem_rf/Q14_C** (1 connection)
    - Q14.3 at (69.4125, 5.2450) F  <->  R51.2 at (82.1375, 4.4950) F
- [ ] **/modem_rf/SIM_CLK** (1 connection)
    - D14.3 at (88.2500, 49.3950) F  <->  track at (83.1750, 47.6500) F,
- [ ] **/modem_rf/SIM_DATA** (1 connection)
    - track at (82.3552, 52.4502) F,  <->  D14.1 at (88.2500, 50.6950) F
- [ ] **/modem_rf/USIM_CLK_M** (1 connection)
    - U1.16 at (63.4500, 39.0000) F  <->  R67.1 at (82.8125, 65.4950) F
- [ ] **/modem_rf/USIM_VDD** (1 connection)
    - D14.5 at (86.4500, 50.0450) F  <->  track at (88.7500, 50.1500) B,
- [ ] **/modem_rf/USIM_VDD_SIM** (1 connection)
    - X1.C1 at (71.1300, 45.6270) F  <->  R69.2 at (80.6375, 65.9950) F
- [ ] **/modem_rf/Q13_B** (2 connections)
    - R51.1 at (80.3125, 4.4950) F  <->  Q13.1 at (63.0375, 4.2950) F
    - R52.2 at (86.1375, 4.9950) F  <->  R51.1 at (80.3125, 4.4950) F
