# DRC violations — placement pass (Milestone 4 stage 2)

Generated from `drc-placement.rpt`. **This is not a routed board and
this is not a clean DRC.** The list below is the honest accounting of
what the placement pass leaves open, split into what is expected at
this stage and what is a genuine defect still to fix.

**Total: 896 violations.**

| count | type | status |
|---|---|---|
| 443 | `unconnected_items` | EXPECTED — nothing is routed yet. Clears with routing. |
| 169 | `silk_over_copper` | EXPECTED/WAIVABLE — footprint silk touching its own pads; inherent to the vendor footprints. Normally waived or trimmed at release. |
| 71 | `solder_mask_bridge` | TO FIX — mask slivers between close pads. Some are intra-footprint and waivable; the rest need spacing. |
| 58 | `clearance` | **DEFECT** — packed parts too close. Needs placement iteration. |
| 58 | `silk_overlap` | TO FIX — remaining reference-designator collisions on ICs/connectors that kept silk refs. |
| 51 | `shorting_items` | **DEFECT** — pads/vias of different nets touching. Needs placement iteration. |
| 22 | `courtyards_overlap` | **DEFECT** — overlapping courtyards. Needs placement iteration. |
| 6 | `hole_clearance` | **DEFECT** — hole too near copper. |
| 5 | `pth_inside_courtyard` | TO REVIEW — mounting-hole pads inside a part courtyard. |
| 4 | `npth_inside_courtyard` | TO REVIEW — as above, unplated. |
| 3 | `isolated_copper` | TO FIX — orphaned zone islands; resolves once routing gives the pours something to connect to. |
| 2 | `annular_width` | TO FIX — 2 vias still below the 0.1 mm annular minimum. |
| 2 | `padstack` | TO REVIEW — padstack definition warning. |
| 1 | `hole_to_hole` | TO FIX — two holes too close. |
| 1 | `silk_edge_clearance` | TO FIX — silk over the board edge. |

## Genuine defects, by location

### `shorting_items` (51)

- Items shorting two nets (nets /modem_rf/ANT_GNSS_C and /modem_rf/USB_DM_TP)
- Items shorting two nets (nets 3V3 and MODEM_RX)
- Items shorting two nets (nets 3V3 and MODEM_RI)
- Items shorting two nets (nets GND and )
- Items shorting two nets (nets GND and DO2_GATE)
- Items shorting two nets (nets GND and /modem_rf/VBAT_MODEM)
- Items shorting two nets (nets GND and MODEM_PWRKEY)
- Items shorting two nets (nets /mcu/VBAT_MCU and SPI1_MOSI)
- Items shorting two nets (nets /modem_rf/USIM_VDD and GND)
- Items shorting two nets (nets 3V3 and /io/CANL_T)
- Items shorting two nets (nets /mcu/I2C1_SCL and /io/CANH_T)
- Items shorting two nets (nets MODEM_PWR_EN and /modem_rf/PWRKEY_MOD)
- Items shorting two nets (nets /modem_rf/Q14_B and GND)
- Items shorting two nets (nets /modem_rf/Q13_B and GND)
- Items shorting two nets (nets /modem_rf/Q13_B and /modem_rf/RESETN_MOD)
- Items shorting two nets (nets /mcu/BOOT1 and GND)
- Items shorting two nets (nets /mcu/BOOT0 and FLASH_CS)
- Items shorting two nets (nets GND and SPI1_MISO)
- Items shorting two nets (nets /modem_rf/Q3_G and GND)
- Items shorting two nets (nets /io/CANL and DI1)
- Items shorting two nets (nets /power/SW_CHG and SYS)
- Items shorting two nets (nets 5V0 and /power/U5_VCC)
- Items shorting two nets (nets /io/DI2_LED and GND)
- Items shorting two nets (nets VIN and DI2)
- Items shorting two nets (nets /io/DI2_LED and GND)
- Items shorting two nets (nets /power/VIN_F and VIN)
- Items shorting two nets (nets /mcu/3V3A and GND)
- Items shorting two nets (nets GND and /power/VIN_B)
- Items shorting two nets (nets GND and 5V0)
- Items shorting two nets (nets /power/U5_VB and /modem_rf/VDD_EXT_1V8)
- Items shorting two nets (nets /power/VIN_P and /mcu/DBG_RX)
- Items shorting two nets (nets /power/VIN_P and SPI1_MOSI)
- Items shorting two nets (nets /power/VIN_P and VBAT_SENSE)
- Items shorting two nets (nets /power/VIN_P and FLASH_CS)
- Items shorting two nets (nets /power/VIN_P and ADC_SPARE)
- Items shorting two nets (nets /power/VIN_P and /mcu/BOOT1)
- Items shorting two nets (nets /power/VIN_P and MODEM_PWR_EN)
- Items shorting two nets (nets /power/VIN_P and /mcu/NET_STATUS_LED)
- Items shorting two nets (nets /power/SW_BUCK and /modem_rf/MTXD_1V8)
- Items shorting two nets (nets /power/SW_BUCK and /modem_rf/MRI_1V8)
- …and 11 more (see `drc-placement.rpt`)

### `courtyards_overlap` (22)

- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap
- Courtyards overlap

### `clearance` (58)

- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1639 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1639 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1145 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1900 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0287 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0050 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1250 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0062 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1155 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1550 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0450 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0422 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1159 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0546 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0546 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1690 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.1900 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0450 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0950 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0950 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0000 mm)
- Clearance violation (netclass 'Default' clearance 0.2000 mm; actual 0.0500 mm)
- …and 18 more (see `drc-placement.rpt`)

### `annular_width` (2)

- Annular width (board setup constraints min annular width 0.1000 mm; actual 0.0000 mm)
- Annular width (board setup constraints min annular width 0.1000 mm; actual 0.0000 mm)

### `hole_to_hole` (1)

- Drilled hole too close to other hole (rule 'JLCPCB hole to hole' min 0.4995 mm; actual 0.0000 mm)

### `hole_clearance` (6)

- Hole clearance violation (board setup constraints hole clearance 0.2500 mm; actual 0.0268 mm)
- Hole clearance violation (board setup constraints hole clearance 0.2500 mm; actual 0.0000 mm)
- Hole clearance violation (board setup constraints hole clearance 0.2500 mm; actual 0.0000 mm)
- Hole clearance violation (board setup constraints hole clearance 0.2500 mm; actual 0.0000 mm)
- Hole clearance violation (board setup constraints hole clearance 0.2500 mm; actual 0.0000 mm)
- Hole clearance violation (board setup constraints hole clearance 0.2500 mm; actual 0.0000 mm)

