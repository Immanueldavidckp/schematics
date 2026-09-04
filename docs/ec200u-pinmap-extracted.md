# EC200U pin map — C2916206 symbol vs Quectel Table 7

**Sources.** Symbol: LCSC **C2916206** (EC200UCNLA-N05-SGNSA) imported via
easyeda2kicad 1.0.1 into `lib/jlc.kicad_sym`. Datasheet: *Quectel EC200U Series
Hardware Design V1.2*, chapter 3.3 **Table 7 (Pin Description)**, pages 22–33 of
the PDF; page numbers below are PDF pages.

**Method.** Table 7 was machine-parsed; each symbol pin name was compared to the
parsed datasheet name for the same pin number, through a documented alias map
(TXD→MAIN_TXD, RXD→MAIN_RXD, RI\*→MAIN_RI, DTR\*→MAIN_DTR, DCD\*→MAIN_DCD,
RTS→MAIN_RTS, CTS→MAIN_CTS, USIM_PRESENCE→USIM_DET, NETLIGHT→NET_STATUS).

**Result: 103/144 VERIFIED, 41/144 NEEDS-HUMAN.**
(Was 68/76. The 35 GND rows were promoted to VERIFIED on 2026-09-04 when the
Table 7 GND row was finally read from the PDF — see F-9b below.)

**F-9b — the GND row, read verbatim from the primary source.** Chapter 3.3
Table 7 "Pin Description", Power Supply sub-block, p.21, repeated verbatim in
chapter 3.6.1 Table 9 "VBAT and GND Pins", p.36:

```
GND               8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112
```

Expanded, that is **43 GND pads** — and it matches the previously-inferred set
exactly, pin for pin. Pin 10 `USIM_GND` is a separate (U)SIM ground.
Table 7 note 3, p.20: *"Please keep all RESERVED and unused pins unconnected,
and all GND pins are connected to the ground."*

*Root cause of the "row not machine-parsed" rows:* the ranges are written with
**U+2013 EN DASH** (`50–54`, `85–112`), not `~` and not ASCII `-`. The original
parser dropped them. This was previously attributed to "the comma-list row
format", which was wrong.

**Correction to the earlier geometric argument.** The earlier claim that the
central LGA grid is "overwhelmingly the ground/thermal field" is **false** and
must not be relied on. The F-9b reverse check (every inner-field / ANT-fence
pad cross-checked against the GND set) found **40 of the 64 inner-field and
fence pads carry definite non-ground functions**, 24 of them VERIFIED directly
against Table 7 — SPK/MIC (73–77), KEYIN/KEYOUT (78–84), LCD and SPILCD
(119–125), SDIO2 (129–134), WLAN/BT (135–139), ADC0 (45), RFCTL (143/144).
What the geometry *does* show, correctly stated:
- pads **85–112** occupy an exclusive, regular full-span lattice with zero
  signal intrusion — a genuine thermal/ground via field;
- pad **76** sits between SPK_N/MIC_P and MIC_N in both numbering and position
  — a local audio ground, not part of that lattice;
- pads **46/48/50/51** alternate with ANT_GNSS(47)/ANT_MAIN(49) — an RF ground
  fence. But 33/34/45/143/144 also fall within two pitches of an antenna pad
  and are signals, so "near the antenna" alone proves nothing.

Other geometric cross-checks that do hold: VBAT_RF(57,58)+VBAT_BB(59,60)
contiguous; 80 perimeter + 64 inner pads = Quectel's 80 LCC + 64 LGA.

**RELEASE GATE: the 43 GND pads are released and connected. The remaining 41
NEEDS-HUMAN pins stay no-connect** — which is also what Table 7 note 3 requires
for unused and RESERVED pins — **and must be reviewed against the PDF before any
of them is ever wired.**

| Pin | Symbol name | Status | Reference / note |
|---|---|---|---|
| 1 | WAKEUP_IN | VERIFIED | Table 7 p.25 |
| 2 | AP_READY | VERIFIED | Table 7 p.25 |
| 3 | SLEEP_IND | VERIFIED | Table 7 p.25 |
| 4 | ~{W_DISABLE} | NEEDS-HUMAN | row not machine-parsed from Table 7 |
| 5 | NET_MODE | VERIFIED | Table 7 p.23 |
| 6 | NET_STATUS | VERIFIED | Table 7 p.23 |
| 7 | VDD_EXT | VERIFIED | Table 7 p.23 |
| 8 | GND | VERIFIED | Table 7 p.22 |
| 9 | GND | VERIFIED | Table 7 p.22 |
| 10 | USIM_GND | VERIFIED | Table 7 p.24 |
| 11 | DBG_RXD | VERIFIED | Table 7 p.26 |
| 12 | DBG_TXD | VERIFIED | Table 7 p.26 |
| 13 | USIM_PRESENCE (Table 7: USIM_DET) | VERIFIED | Table 7 p.25 |
| 14 | USIM_VDD | VERIFIED | Table 7 p.24 |
| 15 | USIM_DATA | VERIFIED | Table 7 p.24 |
| 16 | USIM_CLK | VERIFIED | Table 7 p.24 |
| 17 | USIM_RST | VERIFIED | Table 7 p.24 |
| 18 | NC | VERIFIED | Table 7 p.32 (RESERVED) |
| 19 | GND | VERIFIED | Table 7 p.22 |
| 20 | RESET_N | VERIFIED | Table 7 p.23 |
| 21 | PWRKEY | VERIFIED | Table 7 p.23 |
| 22 | GND | VERIFIED | Table 7 p.22 |
| 23 | SD_DET | VERIFIED | Table 7 p.29 |
| 24 | PCM_IN | NEEDS-HUMAN | Table 7 p.27 says 'PCM_DIN', symbol says 'PCM_IN' |
| 25 | PCM_OUT | NEEDS-HUMAN | Table 7 p.27 says 'PCM_DOUT', symbol says 'PCM_OUT' |
| 26 | PCM_SYNC | VERIFIED | Table 7 p.28 |
| 27 | PCM_CLK | VERIFIED | Table 7 p.28 |
| 28 | SDC2_DATA_3 | NEEDS-HUMAN | Table 7 p.29 says 'SDIO1_DATA3', symbol says 'SDC2_DATA_3' |
| 29 | SDC2_DATA_2 | NEEDS-HUMAN | Table 7 p.29 says 'SDIO1_DATA2', symbol says 'SDC2_DATA_2' |
| 30 | SDC2_DATA_1 | NEEDS-HUMAN | Table 7 p.29 says 'SDIO1_DATA1', symbol says 'SDC2_DATA_1' |
| 31 | SDC2_DATA_0 | NEEDS-HUMAN | Table 7 p.29 says 'SDIO1_DATA0', symbol says 'SDC2_DATA_0' |
| 32 | SDC2_CLK | NEEDS-HUMAN | Table 7 p.30 says 'SDIO1_CLK', symbol says 'SDC2_CLK' |
| 33 | SDC2_CMD | NEEDS-HUMAN | Table 7 p.30 says 'SDIO1_CMD', symbol says 'SDC2_CMD' |
| 34 | VDD_SDIO | NEEDS-HUMAN | Table 7 p.30 says 'SDIO1_VDD', symbol says 'VDD_SDIO' |
| 35 | WIFI_ANT | NEEDS-HUMAN | Table 7 p.30 says 'SCAN', symbol says 'WIFI_ANT' |
| 36 | GND | VERIFIED | Table 7 p.22 |
| 37 | SPI_CS_N | NEEDS-HUMAN | Table 7 p.28 says 'SPI_CS', symbol says 'SPI_CS_N' |
| 38 | SPI_MOSI | NEEDS-HUMAN | Table 7 p.28 says 'SPI_DOUT', symbol says 'SPI_MOSI' |
| 39 | SPI_MISO | NEEDS-HUMAN | Table 7 p.28 says 'SPI_DIN', symbol says 'SPI_MISO' |
| 40 | SPI_CLK | VERIFIED | Table 7 p.28 |
| 41 | I2C_SCL | VERIFIED | Table 7 p.27 |
| 42 | I2C_SDA | VERIFIED | Table 7 p.27 |
| 43 | ADC2 | VERIFIED | Table 7 p.27 |
| 44 | ADC1 | VERIFIED | Table 7 p.27 |
| 45 | ADC0 | VERIFIED | Table 7 p.27 |
| 46 | GND | VERIFIED | Table 7 p.22 |
| 47 | ANT_GNSS | VERIFIED | Table 7 p.31 |
| 48 | GND | VERIFIED | Table 7 p.22 |
| 49 | ANT_MAIN | VERIFIED | Table 7 p.31 |
| 50 | GND | VERIFIED | Table 7 p.22 |
| 51 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 52 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 53 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 54 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 55 | NC | VERIFIED | Table 7 p.32 (RESERVED) |
| 56 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 57 | VBAT_RF | VERIFIED | Table 7 p.22 |
| 58 | VBAT_RF | VERIFIED | Table 7 p.22 |
| 59 | VBAT_BB | VERIFIED | Table 7 p.22 |
| 60 | VBAT_BB | VERIFIED | Table 7 p.22 |
| 61 | STATUS | VERIFIED | Table 7 p.23 |
| 62 | RI* (Table 7: MAIN_RI) | VERIFIED | Table 7 p.26 |
| 63 | DCD* (Table 7: MAIN_DCD) | VERIFIED | Table 7 p.26 |
| 64 | RTS (Table 7: MAIN_RTS) | NEEDS-HUMAN | Table 7 p.26 says 'MAIN_CTS', symbol says 'RTS' |
| 65 | CTS (Table 7: MAIN_CTS) | NEEDS-HUMAN | Table 7 p.26 says 'MAIN_RTS', symbol says 'CTS' |
| 66 | DTR* (Table 7: MAIN_DTR) | VERIFIED | Table 7 p.26 |
| 67 | TXD (Table 7: MAIN_TXD) | VERIFIED | Table 7 p.26 |
| 68 | RXD (Table 7: MAIN_RXD) | VERIFIED | Table 7 p.26 |
| 69 | USB_DP | VERIFIED | Table 7 p.23 |
| 70 | USB_DM | VERIFIED | Table 7 p.24 |
| 71 | USB_VBUS | VERIFIED | Table 7 p.23 |
| 72 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 73 | SPK_P | NEEDS-HUMAN | Table 7 p.27 says 'LOUDSPK_P', symbol says 'SPK_P' |
| 74 | SPK_N | NEEDS-HUMAN | Table 7 p.27 says 'LOUDSPK_N', symbol says 'SPK_N' |
| 75 | MIC_P | VERIFIED | Table 7 p.27 |
| 76 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 77 | MIC_N | VERIFIED | Table 7 p.27 |
| 78 | KEYIN1 | VERIFIED | Table 7 p.29 |
| 79 | KEYIN2 | VERIFIED | Table 7 p.29 |
| 80 | KEYIN3 | VERIFIED | Table 7 p.29 |
| 81 | KEYIN4 | NEEDS-HUMAN | Table 7 p.32 says 'RESERVED', symbol says 'KEYIN4' -- RESOLVED F-9b: V1.2 RESERVED row p.30 is "18, 55, 81, 82, 116, 117", comment "Keep these pins open." Symbol uses QuecOpen-variant names (KEYOUT4/5 there). Correct action NC. |
| 82 | KEYIN5 | NEEDS-HUMAN | Table 7 p.32 says 'RESERVED', symbol says 'KEYIN5' -- RESOLVED F-9b: in the V1.2 RESERVED row p.30, "Keep these pins open." Correct action NC. |
| 83 | KEYOUT0 | VERIFIED | Table 7 p.29 |
| 84 | KEYOUT1 | VERIFIED | Table 7 p.29 |
| 85 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 86 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 87 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 88 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 89 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 90 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 91 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 92 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 93 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 94 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 95 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 96 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 97 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 98 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 99 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 100 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 101 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 102 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 103 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 104 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 105 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 106 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 107 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 108 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 109 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 110 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 111 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 112 | GND | VERIFIED | Table 7 p.21 GND row, repeated verbatim in Table 9 p.36: “8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112” (F-9b: en-dash ranges defeated the original parser) |
| 113 | KEYOUT2 | VERIFIED | Table 7 p.29 |
| 114 | KEYOUT3 | VERIFIED | Table 7 p.29 |
| 115 | USB_BOOT | VERIFIED | Table 7 p.29 |
| 116 | NC | VERIFIED | Table 7 p.32 (RESERVED) |
| 117 | CLK26M_OUT | NEEDS-HUMAN | Table 7 p.32 says 'RESERVED', symbol says 'CLK26M_OUT' -- RESOLVED F-9b: in the V1.2 RESERVED row p.30, "Keep these pins open." (CLK26M_AUX1 in QuecOpen, also reserved). Correct action NC. |
| 118 | NC | NEEDS-HUMAN | Table 7 p.30 says 'CLK', symbol says 'NC' -- RESOLVED F-9b: V1.2 reads WLAN_SLP_CLK, DO, WLAN sleep clock, "If unused, keep it open." Correct action NC. |
| 119 | LCD_FMARK | VERIFIED | Table 7 p.28 |
| 120 | LCD_RSTB | VERIFIED | Table 7 p.28 |
| 121 | SPILCD_SEL | NEEDS-HUMAN | Table 7 p.28 says 'LCD_SEL', symbol says 'SPILCD_SEL' |
| 122 | SPILCD_CS | NEEDS-HUMAN | Table 7 p.28 says 'LCD_CS', symbol says 'SPILCD_CS' |
| 123 | SPILCD_CLK | NEEDS-HUMAN | Table 7 p.28 says 'LCD_CLK', symbol says 'SPILCD_CLK' |
| 124 | SPILCD_SDC | NEEDS-HUMAN | Table 7 p.28 says 'LCD_SDC', symbol says 'SPILCD_SDC' |
| 125 | SPILCD_SI/O | NEEDS-HUMAN | Table 7 p.28 says 'LCD_SI/O', symbol says 'SPILCD_SI/O' |
| 126 | GPIO1 | VERIFIED | Table 7 p.32 |
| 127 | PM_EN_WLAN | NEEDS-HUMAN | Table 7 p.30 says 'EN', symbol says 'PM_EN_WLAN' |
| 128 | NC | NEEDS-HUMAN | Table 7 p.25 says 'USIM2_VDD', symbol says 'NC' -- RESOLVED F-9b: V1.2 confirms USIM2_VDD, PO, (U)SIM2 power supply; SIM2 unused in this design. Correct action NC. |
| 129 | SD1_DATA3 | NEEDS-HUMAN | Table 7 p.30 says 'SDIO2_DATA3', symbol says 'SD1_DATA3' |
| 130 | SD1_DATA2 | NEEDS-HUMAN | Table 7 p.30 says 'SDIO2_DATA2', symbol says 'SD1_DATA2' |
| 131 | SD1_DATA1 | NEEDS-HUMAN | Table 7 p.30 says 'SDIO2_DATA1', symbol says 'SD1_DATA1' |
| 132 | SD1_DATA0 | NEEDS-HUMAN | Table 7 p.30 says 'SDIO2_DATA0', symbol says 'SD1_DATA0' |
| 133 | SD1_CLK | NEEDS-HUMAN | Table 7 p.30 says 'SDIO2_CLK', symbol says 'SD1_CLK' |
| 134 | SD1_CMD | NEEDS-HUMAN | Table 7 p.30 says 'SDIO2_CMD', symbol says 'SD1_CMD' |
| 135 | WAKE_WLAN | NEEDS-HUMAN | Table 7 p.30 says 'WLAN_WAKE', symbol says 'WAKE_WLAN' |
| 136 | WLAN_EN | VERIFIED | Table 7 p.30 |
| 137 | UART3_RXD | NEEDS-HUMAN | Table 7 p.26 says 'AUX_RXD', symbol says 'UART3_RXD' |
| 138 | UART3_TXD | NEEDS-HUMAN | Table 7 p.27 says 'AUX_TXD', symbol says 'UART3_TXD' |
| 139 | BT_EN | VERIFIED | Table 7 p.32 |
| 140 | NC | NEEDS-HUMAN | Table 7 p.29 says 'ISINK', symbol says 'NC' -- RESOLVED F-9b: V1.2 confirms ISINK, PI, backlight current sink, Imax = 200 mA; unused. Correct action NC. |
| 141 | I2C2_SCL | VERIFIED | Table 7 p.27 |
| 142 | I2C2_SDA | VERIFIED | Table 7 p.27 |
| 143 | RFCTL_1 | NEEDS-HUMAN | Table 7 p.32 says 'GRFC1', symbol says 'RFCTL_1' |
| 144 | RFCTL_2 | NEEDS-HUMAN | Table 7 p.32 says 'GRFC2', symbol says 'RFCTL_2' |
