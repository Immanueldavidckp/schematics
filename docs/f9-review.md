# F-9 review table — all 76 NEEDS-HUMAN pins, three sources consolidated

**Purpose:** the human sign-off gate for the EC200U pin map (milestone-3 hard
gate). Nothing is connected on the strength of this table — the schematic keeps
all 76 pins NC until the user signs off.

**Sources.** (1) *Quectel EC200U Series Hardware Design V1.2* Table 7 (machine-
parsed; page refs are PDF pages; "(unparsed)" = the comma-list row format
defeated the parser and the row must be read by eye). (2) The C2916206 symbol
pin names. (3) The footprint pad geometry, classified as: **central LGA grid**
(the inner 64-pad field — on this module family, overwhelmingly the ground/
thermal field), **ANT GND fence** (pads 46/48/50/51 flanking the two antenna
pads on the RF edge), or **edge LCC** (the 80-pin perimeter).

**Ordering:** the 35 priority-1 GND rows first, then RESERVED rows 81/82/117,
then the remainder.

**Verdicts:** 61 AGREE
(incl. naming variants and 2-source GND rows), **14 CONFLICT** — every
conflict is listed with both readings and a proposed action; none is wired.

| Pin | Table 7 (V1.2) | C2916206 symbol | Footprint position | Verdict | Proposed action |
|---|---|---|---|---|---|
| 51 | (unparsed) (not machine-parsed) | GND | ANT GND fence (edge, RF end) | AGREE (2-source: symbol GND + RF fence position; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 52 | (unparsed) (not machine-parsed) | GND | edge LCC | AGREE-WEAK (symbol GND; edge pad; Table 7 row unparsed) | CONNECT TO GND after sign-off; double-check row in PDF |
| 53 | (unparsed) (not machine-parsed) | GND | edge LCC | AGREE-WEAK (symbol GND; edge pad; Table 7 row unparsed) | CONNECT TO GND after sign-off; double-check row in PDF |
| 54 | (unparsed) (not machine-parsed) | GND | edge LCC | AGREE-WEAK (symbol GND; edge pad; Table 7 row unparsed) | CONNECT TO GND after sign-off; double-check row in PDF |
| 56 | (unparsed) (not machine-parsed) | GND | edge LCC | AGREE-WEAK (symbol GND; edge pad; Table 7 row unparsed) | CONNECT TO GND after sign-off; double-check row in PDF |
| 72 | (unparsed) (not machine-parsed) | GND | edge LCC | AGREE-WEAK (symbol GND; edge pad; Table 7 row unparsed) | CONNECT TO GND after sign-off; double-check row in PDF |
| 76 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 85 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 86 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 87 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 88 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 89 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 90 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 91 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 92 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 93 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 94 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 95 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 96 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 97 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 98 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 99 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 100 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 101 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 102 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 103 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 104 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 105 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 106 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 107 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 108 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 109 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 110 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 111 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 112 | (unparsed) (not machine-parsed) | GND | central LGA grid | AGREE (2-source: symbol GND + thermal grid; Table 7 row unparsed) | CONNECT TO GND after sign-off |
| 81 | RESERVED (p.32) | KEYIN4 | central LGA grid | **CONFLICT** (Table 7 RESERVED vs symbol KEYIN4) | keep NC (both readings imply NC); confirm in PDF |
| 82 | RESERVED (p.32) | KEYIN5 | central LGA grid | **CONFLICT** (Table 7 RESERVED vs symbol KEYIN5) | keep NC (both readings imply NC); confirm in PDF |
| 117 | RESERVED (p.32) | CLK26M_OUT | central LGA grid | **CONFLICT** (Table 7 RESERVED vs symbol CLK26M_OUT) | keep NC (both readings imply NC); confirm in PDF |
| 4 | (unparsed) (not machine-parsed) | ~{W_DISABLE} | edge LCC | INSUFFICIENT (only symbol name available) | keep NC; read the PDF row |
| 24 | PCM_DIN (p.27) | PCM_IN | edge LCC | AGREE (naming variant: PCM_DIN vs PCM_IN) | keep NC (unused function) |
| 25 | PCM_DOUT (p.27) | PCM_OUT | edge LCC | AGREE (naming variant: PCM_DOUT vs PCM_OUT) | keep NC (unused function) |
| 28 | SDIO1_DATA3 (p.29) | SDC2_DATA_3 | edge LCC | **CONFLICT** (Table 7 SDIO1_DATA3 vs symbol SDC2_DATA_3) | keep NC; resolve in PDF before any future use |
| 29 | SDIO1_DATA2 (p.29) | SDC2_DATA_2 | edge LCC | **CONFLICT** (Table 7 SDIO1_DATA2 vs symbol SDC2_DATA_2) | keep NC; resolve in PDF before any future use |
| 30 | SDIO1_DATA1 (p.29) | SDC2_DATA_1 | edge LCC | **CONFLICT** (Table 7 SDIO1_DATA1 vs symbol SDC2_DATA_1) | keep NC; resolve in PDF before any future use |
| 31 | SDIO1_DATA0 (p.29) | SDC2_DATA_0 | edge LCC | **CONFLICT** (Table 7 SDIO1_DATA0 vs symbol SDC2_DATA_0) | keep NC; resolve in PDF before any future use |
| 32 | SDIO1_CLK (p.30) | SDC2_CLK | edge LCC | AGREE (naming variant: SDIO1_CLK vs SDC2_CLK) | keep NC (unused function) |
| 33 | SDIO1_CMD (p.30) | SDC2_CMD | edge LCC | AGREE (naming variant: SDIO1_CMD vs SDC2_CMD) | keep NC (unused function) |
| 34 | SDIO1_VDD (p.30) | VDD_SDIO | edge LCC | AGREE (naming variant: SDIO1_VDD vs VDD_SDIO) | keep NC (unused function) |
| 35 | SCAN (p.30) | WIFI_ANT | edge LCC | **CONFLICT** (Table 7 SCAN vs symbol WIFI_ANT) | keep NC; resolve in PDF before any future use |
| 37 | SPI_CS (p.28) | SPI_CS_N | edge LCC | AGREE (naming variant: SPI_CS vs SPI_CS_N) | keep NC (unused function) |
| 38 | SPI_DOUT (p.28) | SPI_MOSI | edge LCC | AGREE (naming variant: SPI_DOUT vs SPI_MOSI) | keep NC (unused function) |
| 39 | SPI_DIN (p.28) | SPI_MISO | edge LCC | AGREE (naming variant: SPI_DIN vs SPI_MISO) | keep NC (unused function) |
| 64 | MAIN_CTS (p.26) | RTS | edge LCC | **CONFLICT** (RTS/CTS swapped between sources) | keep NC (flow control unused); relabel symbol before any future use |
| 65 | MAIN_RTS (p.26) | CTS | edge LCC | **CONFLICT** (RTS/CTS swapped between sources) | keep NC (flow control unused); relabel symbol before any future use |
| 73 | LOUDSPK_P (p.27) | SPK_P | central LGA grid | AGREE (naming variant: LOUDSPK_P vs SPK_P) | keep NC (unused function) |
| 74 | LOUDSPK_N (p.27) | SPK_N | central LGA grid | AGREE (naming variant: LOUDSPK_N vs SPK_N) | keep NC (unused function) |
| 118 | CLK (p.30) | NC | central LGA grid | **CONFLICT** (Table 7 CLK vs symbol NC) | keep NC; resolve in PDF before any future use |
| 121 | LCD_SEL (p.28) | SPILCD_SEL | central LGA grid | AGREE (naming variant: LCD_SEL vs SPILCD_SEL) | keep NC (unused function) |
| 122 | LCD_CS (p.28) | SPILCD_CS | central LGA grid | AGREE (naming variant: LCD_CS vs SPILCD_CS) | keep NC (unused function) |
| 123 | LCD_CLK (p.28) | SPILCD_CLK | central LGA grid | AGREE (naming variant: LCD_CLK vs SPILCD_CLK) | keep NC (unused function) |
| 124 | LCD_SDC (p.28) | SPILCD_SDC | central LGA grid | AGREE (naming variant: LCD_SDC vs SPILCD_SDC) | keep NC (unused function) |
| 125 | LCD_SI/O (p.28) | SPILCD_SI/O | central LGA grid | AGREE (naming variant: LCD_SI/O vs SPILCD_SI/O) | keep NC (unused function) |
| 127 | EN (p.30) | PM_EN_WLAN | central LGA grid | **CONFLICT** (Table 7 EN vs symbol PM_EN_WLAN) | keep NC; resolve in PDF before any future use |
| 128 | USIM2_VDD (p.25) | NC | central LGA grid | **CONFLICT** (Table 7 USIM2_VDD vs symbol NC) | keep NC; resolve in PDF before any future use |
| 129 | SDIO2_DATA3 (p.30) | SD1_DATA3 | central LGA grid | AGREE (naming variant: SDIO2_DATA3 vs SD1_DATA3) | keep NC (unused function) |
| 130 | SDIO2_DATA2 (p.30) | SD1_DATA2 | central LGA grid | AGREE (naming variant: SDIO2_DATA2 vs SD1_DATA2) | keep NC (unused function) |
| 131 | SDIO2_DATA1 (p.30) | SD1_DATA1 | central LGA grid | AGREE (naming variant: SDIO2_DATA1 vs SD1_DATA1) | keep NC (unused function) |
| 132 | SDIO2_DATA0 (p.30) | SD1_DATA0 | central LGA grid | AGREE (naming variant: SDIO2_DATA0 vs SD1_DATA0) | keep NC (unused function) |
| 133 | SDIO2_CLK (p.30) | SD1_CLK | central LGA grid | AGREE (naming variant: SDIO2_CLK vs SD1_CLK) | keep NC (unused function) |
| 134 | SDIO2_CMD (p.30) | SD1_CMD | central LGA grid | AGREE (naming variant: SDIO2_CMD vs SD1_CMD) | keep NC (unused function) |
| 135 | WLAN_WAKE (p.30) | WAKE_WLAN | central LGA grid | AGREE (naming variant: WLAN_WAKE vs WAKE_WLAN) | keep NC (unused function) |
| 137 | AUX_RXD (p.26) | UART3_RXD | central LGA grid | AGREE (naming variant: AUX_RXD vs UART3_RXD) | keep NC (unused function) |
| 138 | AUX_TXD (p.27) | UART3_TXD | central LGA grid | AGREE (naming variant: AUX_TXD vs UART3_TXD) | keep NC (unused function) |
| 140 | ISINK (p.29) | NC | central LGA grid | **CONFLICT** (Table 7 ISINK vs symbol NC) | keep NC; resolve in PDF before any future use |
| 143 | GRFC1 (p.32) | RFCTL_1 | edge LCC | AGREE (naming variant: GRFC1 vs RFCTL_1) | keep NC (unused function) |
| 144 | GRFC2 (p.32) | RFCTL_2 | edge LCC | AGREE (naming variant: GRFC2 vs RFCTL_2) | keep NC (unused function) |
