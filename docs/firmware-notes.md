# Firmware notes — MEWP telematics tracker

Hardware decisions that firmware must honour. Started at milestone 3; updated
every milestone. Source of truth for each row is design-log.md.

## Pin/peripheral configuration

| # | Item | Detail | Origin |
|---|---|---|---|
| FW-1 | **JTAG must be disabled (SWD retained) at early boot** | PA15 (CAN_STB), PB3 (MODEM_RESET), PB4 (MODEM_STATUS) reuse JTDI/JTDO/NJTRST. Until the JTAG-disable remap runs, these pins are not GPIO. | handoff §5 |
| FW-2 | **CAN1 uses the PB8/PB9 remap** | Configure the AFIO remap before enabling CAN1. | handoff §5 |
| FW-3 | **IWDG always on** | Independent watchdog enabled at boot (option bytes if supported); kick in the main loop only. Brown-out detector enabled. | handoff §2 rule 4 |
| FW-4 | **BOOT1 (PB2) is strapped low, BOOT0 low via 10 k** | Bootloader entry needs the BOOT0 solder jumper (JP1) — no firmware path can enter system bootloader accidentally. | mcu sheet |

## Modem control

| # | Item | Detail | Origin |
|---|---|---|---|
| FW-5 | **MODEM_STATUS is INVERTED at the MCU** | Quectel Fig 28 NPN stage: PB4 LOW = modem running, HIGH = modem off. | modem_rf, design-log |
| FW-6 | **MODEM_PWR_EN (PB10) is active-high = POWER CUT** | Default state (pin low/floating/reset) = modem powered. Power-cycle sequence: try graceful `AT+QPOWD` → wait for STATUS to show off → if hung: PB10 HIGH ≥ 1 s (Q3 opens, VBAT_MODEM collapses into 2×100 µF) → PB10 LOW → wait VBAT settle → PWRKEY pulse per EC200U timing (≥ 2 s low… see HW design Fig 13: STATUS asserts ~4–5 s after PWRKEY). Never leave PB10 high in sleep — that is the brick-prevention path. | modem_rf, handoff §2 rule 3 |
| FW-7 | **PWRKEY / RESET_N are through NPN inverters** | PA8/PB3 HIGH = pin pulled LOW at the modem. RESET_N is last-resort only per Quectel. | modem_rf |
| FW-8 | **TXB0104 OE is hardware-gated by VDD_EXT** | UART pins are Hi-Z until the modem's 1.8 V rail is up — do not interpret bus idle as modem-ready; use STATUS (FW-5). | modem_rf |
| FW-9 | **Modem DFOTA** is the modem's own update path; MCU app FOTA uses the external flash (U7) staging area + custom bootloader. | handoff §2 rule 5 |

## Storage

| # | Item | Detail | Origin |
|---|---|---|---|
| FW-10 | **Flash write-throttle above 80 °C** | U7 (GD25Q64ESIGR) is the 85 °C I-grade (F-2 acceptance condition): above 80 °C internal MCU temperature, throttle ring-buffer flush rate and defer non-critical writes to protect P/E endurance and retention. | design-log F-2 |
| FW-11 | Ring buffer with wear levelling; ≈150 B/10 s → 1.3 MB/day → 8 MB ≈ 6 days. WP#/HOLD# are tied high in hardware — software write protection only. | handoff §6 |

## Power-state behaviour

| # | Item | Detail | Origin |
|---|---|---|---|
| FW-12 | **DO1/DO2 and CAN are inactive during battery-backup operation** | Both depend on 5V0, which exists only with machine power. Firmware must not report DO commands as executed when VIN is absent (check VIN_SENSE first). | F-10 consequence; handoff §4 |
| FW-13 | **Guaranteed VIN floor is 10.5 V** | Below ~10.5 V the buck may drop out; the design intent is battery ride-through. Treat VIN_SENSE < 10.5 V as "on battery". | U5 condition (a) |
| FW-14 | IGN_SENSE (PA0) is also the EXTI wake source; IMU INT1 (PB5) is the motion wake. RI (PA11) wakes on SMS/URC. | handoff §5 |
| FW-15 | Battery sense divider 1 M:1 M from SYS — ~2 µA standing drain, high impedance: use long ADC sample time (handoff: slow sample time, 12-bit). | handoff §4 |

## IMU

| # | Item | Detail | Origin |
|---|---|---|---|
| FW-16 | QMI8658B on I2C1 at address **0x6A** (SA0 tied high). CS tied high = I2C mode. RESV pin handling is hardware; nothing to do in firmware. INT1 → PB5. | mcu sheet, QST datasheet |
| FW-17 | **SIM card-detect polarity:** holder CD switch is SHORTED to GND with no card, OPEN with card inserted → USIM_DET floats high (module pull) = card present. Configure `AT+QSIMDET` level accordingly. | JXTCONN drawing, M3 |

## Bench/bring-up items (hardware validation, firmware assists)

| # | Item | Detail | Origin |
|---|---|---|---|
| BV-1 | **EG11752 R_IS (F-12)** | R82 is fitted 0 R; no R_IS formula exists in the V1.0 datasheet. Bench/FAE item: characterise the current limit before layout freeze. | power sheet, F-12 |
| BV-2 | **EG11752 minimum on-time** | At 100 V→5 V, Ton ≈ 455 ns @110 kHz; datasheet gives no min-on-time spec. Bench test: 100 V in, 0.7–1 A out, and light-load at 100 V (frequency-foldback behaviour). #1 bench item. | TASK A risk list |
| BV-3 | EG11752 EN is pulled up to VCC through 100 k per fig 6-2 — verify EN pin voltage stays within its 7 V abs max across VCC range on first power-up. | power sheet note |
| BV-4 | U5 qualification: 3 units, 1000 h burn-in at 100 V/85 °C + thermal cycling −40↔+85 °C (U5 condition (c), milestone-6 plan). | U5 approval |
