# Hand-routing worksheet - board of record

94 open connections on 44 nets, generated from the
DRC report of the board on branch `worktree-route-finish`.

Coordinates are KiCad board coordinates in mm (X to the right, Y downwards - the
numbers in the editor's status bar). F = top copper (F.Cu), B = bottom copper (B.Cu).
Tick a line when its ratsnest line has disappeared.

Order: (1) programming / debug / modem UART first, so the board can be flashed and
talked to even if something else is left; (2) power, ground, crystal; (3) the rest.

## 1. Programming, debug, modem control (do these first)

- [ ] **/mcu/BOOT1** (1 connection)
    - U2.20 at (33.4700, 21.3300) F  <->  R2.1 at (34.0625, 48.9950) F
- [ ] **/mcu/SWCLK** (1 connection)
    - U2.37 at (25.2500, 19.3300) F  <->  TP2.1 at (49.3510, 26.1400) B
- [ ] **/mcu/SWDIO** (1 connection)
    - U2.34 at (27.6100, 17.9700) F  <->  TP1.1 at (47.0010, 29.8300) B
- [ ] **/modem_rf/USB_VBUS** (1 connection)
    - TP17.1 at (45.7975, 4.7962) B  <->  track at (53.1500, 13.8500) B,
- [ ] **MODEM_PWRKEY** (1 connection)
    - U2.29 at (30.1100, 17.9700) F  <->  R55.1 at (76.8125, 51.9950) F
- [ ] **MODEM_RX** (1 connection)
    - U2.31 at (29.1100, 17.9700) F  <->  track at (43.8106, 48.4696) F,

## 2. Power, ground, crystal

- [ ] **/mcu/OSC32_IN** (1 connection)
    - track at (21.7500, 22.4500) B,  <->  U2.3 at (27.6100, 26.1900) F
- [ ] **/mcu/SYS_LED_A** (1 connection)
    - D20.2 at (33.5625, 32.2750) F  <->  R4.2 at (39.5625, 28.4950) B
- [ ] **/mcu/VBAT_MCU** (1 connection)
    - U2.1 at (26.6100, 26.1900) F  <->  track at (21.5000, 32.2750) F,
- [ ] **/modem_rf/VBAT_MODEM** (1 connection)
    - TP24.1 at (51.7975, 4.7962) B  <->  C43.1 at (48.7500, 2.2750) F
- [ ] **/power/U6_BTST** (1 connection)
    - U6.21 at (30.5200, 43.9500) F  <->  C64.1 at (36.2900, 44.1850) B
- [ ] **/power/U6_ICHG** (1 connection)
    - U6.10 at (30.5200, 48.0500) F  <->  R85.1 at (39.0400, 41.0625) B
- [ ] **/mcu/OSC_IN** (2 connections)
    - U2.5 at (28.6100, 26.1900) F  <->  Y1.1 at (29.8600, 19.3500) B
    - Y1.1 at (29.8600, 19.3500) B  <->  C1.1 at (24.7400, 18.6050) B
- [ ] **/mcu/OSC_OUT** (2 connections)
    - U2.6 at (29.1100, 26.1900) F  <->  C2.1 at (33.0100, 20.1250) B
    - C2.1 at (33.0100, 20.1250) B  <->  Y1.3 at (27.6600, 17.6500) B
- [ ] **/modem_rf/VDD_EXT_1V8** (2 connections)
    - C44.1 at (52.2500, 2.2750) F  <->  track at (45.4500, 24.2000) F,
    - C45.1 at (62.2500, 2.2750) F  <->  C44.1 at (52.2500, 2.2750) F
- [ ] **/power/SW_CHG** (2 connections)
    - track at (31.5200, 43.9500) F,  <->  L3.1 at (32.7300, 49.8000) B
    - C64.2 at (36.2900, 42.6350) B  <->  track at (31.5200, 43.9500) F,
- [ ] **/power/U5_VCC** (2 connections)
    - C75.1 at (21.5000, 23.2750) F  <->  U5.1 at (36.4000, 11.7200) F
    - U5.1 at (36.4000, 11.7200) F  <->  R81.1 at (23.3875, 1.9950) B
- [ ] **3V3** (5 connections)
    - via at (26.4347, 51.4220) F  <->  track at (27.7400, 54.2500) F,
    - R7.1 at (30.3875, 52.4950) B  <->  track at (29.5000, 54.7187) F,
    - track at (47.5300, 11.4900) B,  <->  via at (44.7500, 9.6500) F
    - via at (50.8901, 49.1135) F  <->  track at (37.5625, 49.9950) F,
    - track at (68.0028, 49.3499) PWR_L3,  <->  U8.14 at (52.9900, 48.9500) B
- [ ] **5V0** (6 connections)
    - via at (30.6327, 36.2513) F  <->  track at (26.3500, 43.5500) F,
    - track at (29.3500, 7.2500) F,  <->  C79.1 at (35.5450, 24.5250) F
    - track at (31.6950, 35.8000) F,  <->  C80.1 at (36.2100, 40.0350) B
    - track at (34.8186, 33.0961) B,  <->  track at (31.6950, 35.8000) F,
    - C79.1 at (35.5450, 24.5250) F  <->  track at (32.7425, 31.0200) B,
    - C80.1 at (36.2100, 40.0350) B  <->  R49.1 at (39.8875, 42.9950) B
- [ ] **SYS** (6 connections)
    - R38.1 at (23.3875, 28.4950) B  <->  U9.3 at (30.2950, 6.8875) B
    - track at (30.9100, 40.0050) B,  <->  R38.1 at (23.3875, 28.4950) B
    - U9.1 at (32.1950, 6.8875) B  <->  U9.3 at (30.2950, 6.8875) B
    - U6.16 at (32.3100, 45.7500) F  <->  track at (32.5475, 41.2962) F,
    - U6.15 at (32.3100, 46.2500) F  <->  L3.2 at (30.3900, 49.8000) B
    - track at (50.2925, 8.9500) F,  <->  U9.1 at (32.1950, 6.8875) B
- [ ] **GND** (29 connections)
    - zone F_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  U2.35 at (27.1100, 17.9700) F
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - Y1.4 at (29.8600, 17.6500) B  <->  U2.35 at (27.1100, 17.9700) F
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - U6.9 at (30.0200, 48.0500) F  <->  zone F_GND at (0.6500, 0.6500)
    - U2.8 at (30.1100, 26.1900) F  <->  zone F_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - U6.18 at (32.3100, 44.7500) F  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone L2_GND_solid at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone B_GND at (0.6500, 0.6500)  <->  zone B_GND at (0.6500, 0.6500)
    - zone L2_GND_solid at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone L2_GND_solid at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  D14.2 at (55.2500, 4.5450) F
    - zone L2_GND_solid at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone F_GND at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)
    - zone L2_GND_solid at (0.6500, 0.6500)  <->  zone F_GND at (0.6500, 0.6500)

## 3. Remaining signals

- [ ] **/io/CANH** (1 connection)
    - track at (23.5500, 35.9450) F,
- [ ] **/io/CANH_T** (1 connection)
    - L2.4 at (38.5100, 44.4500) F  <->  track at (25.5625, 38.4950) F,
- [ ] **/io/CANL** (1 connection)
    - track at (24.6962, 31.1655) GND_L2,
- [ ] **/io/DO1_B** (1 connection)
    - Q5.1 at (28.0475, 29.2900) B  <->  R42.2 at (39.5625, 36.9950) B
- [ ] **/io/DO1_DRV** (1 connection)
    - track at (35.7530, 30.1595) B,  <->  R23.1 at (29.5625, 49.9950) F
- [ ] **/io/DO2_DRV** (1 connection)
    - R24.1 at (33.5625, 51.4950) F  <->  track at (40.8765, 44.0568) B,
- [ ] **/io/VIN_SENSE** (1 connection)
    - track at (20.7464, 29.7375) F,  <->  R32.2 at (2.2000, 20.1875) F
- [ ] **/modem_rf/NETLED_A** (1 connection)
    - R65.2 at (45.3125, 1.9950) B  <->  D13.2 at (51.8125, 4.2750) F
- [ ] **/modem_rf/Q10_B** (1 connection)
    - Q10.1 at (66.0375, 4.2950) F  <->  track at (72.3282, 51.4576) F,
- [ ] **/modem_rf/SIM_CLK** (1 connection)
    - D14.3 at (55.2500, 3.8950) F  <->  R67.2 at (53.3125, 1.9950) B
- [ ] **/modem_rf/SIM_RST** (1 connection)
    - D14.4 at (53.4500, 3.8950) F  <->  R68.2 at (57.3125, 1.9950) B
- [ ] **/modem_rf/USIM_CLK_M** (1 connection)
    - U1.16 at (45.4500, 39.0000) F  <->  R67.1 at (55.1375, 1.9950) B
- [ ] **/modem_rf/USIM_DATA_M** (1 connection)
    - U1.15 at (45.4500, 37.7000) F  <->  R66.1 at (51.1375, 1.9950) B
- [ ] **/modem_rf/USIM_RST_M** (1 connection)
    - U1.17 at (45.4500, 40.3000) F  <->  R68.1 at (59.1375, 1.9950) B
- [ ] **/modem_rf/USIM_VDD** (1 connection)
    - track at (55.8859, 4.4033) GND_L2,  <->  D14.5 at (53.4500, 4.5450) F
- [ ] **/modem_rf/USIM_VDD_SIM** (1 connection)
    - X1.C1 at (53.9800, 45.6270) F  <->  R69.2 at (61.3125, 1.9950) B
- [ ] **CAN_STB** (1 connection)
    - U4.8 at (22.3200, 40.8200) F  <->  U2.38 at (25.2500, 19.8300) F
- [ ] **DO2_GATE** (1 connection)
    - U2.28 at (30.6100, 17.9700) F  <->  track at (21.2867, 32.5066) B,
- [ ] **MODEM_DTR** (1 connection)
    - U2.33 at (28.1100, 17.9700) F  <->  U8.10 at (52.9900, 46.3500) B
- [ ] **MODEM_RI** (1 connection)
    - U2.32 at (28.6100, 17.9700) F  <->  U8.11 at (52.9900, 47.0000) B
- [ ] **/io/IGN_SENSE** (2 connections)
    - C28.1 at (28.5000, 30.2750) F  <->  R35.2 at (2.2000, 33.8375) F
    - D11.3 at (37.2675, 41.7000) F  <->  C28.1 at (28.5000, 30.2750) F
- [ ] **DI1** (2 connections)
    - track at (39.0000, 28.6271) F,  <->  U2.25 at (32.1100, 17.9700) F
    - R21.2 at (39.8875, 49.4950) F  <->  OK1.4 at (22.5700, 43.4500) B
- [ ] **DO1_GATE** (2 connections)
    - R43.1 at (23.3925, 31.0100) B  <->  R42.1 at (41.3875, 36.9950) B
    - U2.27 at (31.1100, 17.9700) F  <->  R43.1 at (23.3925, 31.0100) B
