# Hand-routing worksheet - T1 board (100 x 68 mm, relief round 6)

40 open connections on 23 nets, generated from the
DRC report of the board on branch `relief6-stretch` (commit "relief round 6 T1 finisher after stitch: unconnected=40 errors=0").

Coordinates are KiCad board coordinates in mm (X to the right, Y downwards - the
numbers in the editor's status bar). F = top copper (F.Cu), B = bottom copper (B.Cu).
Tick a line when its ratsnest line has disappeared.

Order: (1) programming / debug / modem UART first, so the board can be flashed and
talked to even if something else is left; (2) power, ground, crystal; (3) the rest.

## 1. Programming, debug, modem control (do these first)

- [ ] **/modem_rf/USB_DM_TP** (1 connection)
    - track at (76.8860, 62.0105) F,  <->  D15.4 at (71.4550, 4.0360) F
- [ ] **/modem_rf/USB_DP_TP** (1 connection)
    - D15.6 at (69.5550, 4.0360) F  <->  TP15.1 at (73.7975, 4.7962) F
- [ ] **/modem_rf/USB_VBUS** (1 connection)
    - track at (70.7500, 14.9500) F,  <->  D15.5 at (70.5050, 4.0360) F
- [ ] **MODEM_PWRKEY** (1 connection)
    - R55.1 at (90.8125, 49.9950) F  <->  track at (36.1400, 25.4417) F,

## 2. Power, ground, crystal

- [ ] **3V3** (1 connection)
    - track at (29.5625, 41.4950) F,  <->  track at (25.5625, 39.4950) F,
- [ ] **5V0** (2 connections)
    - R49.1 at (38.0625, 42.4950) F  <->  track at (32.8940, 44.9405) GND_L2,
    - track at (41.4425, 35.2300) B,  <->  C23.1 at (40.4650, 40.0400) F
- [ ] **GND** (14 connections)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone L2_GND_solid at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone L2_GND_solid at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)

## 3. Remaining signals

- [ ] **/io/CANL** (1 connection)
    - track at (23.5500, 34.0450) F,
- [ ] **/io/IGN_SENSE** (1 connection)
    - track at (25.0000, 30.2750) F,  <->  R35.2 at (2.2000, 33.8375) F
- [ ] **/io/VIN_SENSE** (1 connection)
    - track at (20.4688, 27.4789) F,  <->  R32.2 at (2.2000, 20.1875) F
- [ ] **/mcu/I2C1_SCL** (1 connection)
    - track at (43.8875, 43.4950) F,  <->  via at (33.9202, 27.8866) F
- [ ] **/modem_rf/GNSS_BIAS** (1 connection)
    - L4.2 at (98.7850, 38.0000) F  <->  C83.1 at (94.1500, 45.5700) F
- [ ] **/modem_rf/NETLED_A** (1 connection)
    - D13.2 at (64.3125, 4.2750) F  <->  R65.2 at (89.1375, 57.4950) F
- [ ] **/modem_rf/Q10_B** (1 connection)
    - Q10.1 at (80.5375, 4.2950) F  <->  R57.2 at (88.6375, 52.4950) F
- [ ] **/modem_rf/SIM_CLK** (1 connection)
    - track at (63.7792, 45.6270) F,  <->  D14.3 at (67.7500, 3.8950) F
- [ ] **/modem_rf/SIM_RST** (1 connection)
    - R68.2 at (97.1375, 59.4950) F  <->  track at (83.7184, 48.3002) PWR_L3,
- [ ] **/modem_rf/STATUS_MOD** (1 connection)
    - U1.61 at (83.7500, 14.9500) F  <->  R59.1 at (94.8125, 54.4950) F
- [ ] **/modem_rf/U8_OE** (1 connection)
    - track at (78.5206, 54.7031) F,  <->  R63.2 at (96.6375, 56.9950) F
- [ ] **/modem_rf/USIM_RST_M** (1 connection)
    - U1.17 at (63.4500, 40.3000) F  <->  R68.1 at (95.3125, 59.4950) F
- [ ] **MODEM_RESET** (1 connection)
    - U2.39 at (31.2800, 26.7400) F  <->  R57.1 at (86.8125, 52.4950) F
- [ ] **/io/CANH** (2 connections)
    - track at (19.8500, 28.0500) F,
    - track at (45.8871, 18.4824) GND_L2,  <->  track at (56.5775, 30.8294) GND_L2,
- [ ] **/modem_rf/Q11_B** (2 connections)
    - Q11.1 at (85.0375, 4.7950) F  <->  R60.1 at (86.8125, 54.9950) F
    - R60.1 at (86.8125, 54.9950) F  <->  R59.2 at (96.6375, 54.4950) F
- [ ] **/modem_rf/USIM_VDD** (2 connections)
    - D14.5 at (65.9500, 4.5450) F  <->  track at (63.4500, 36.4000) F,
    - C47.1 at (83.7500, 2.2750) F  <->  D14.5 at (65.9500, 4.5450) F
