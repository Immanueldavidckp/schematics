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
| FW-6 | **MODEM_PWR_EN (PB10) is active-high = POWER CUT** | Default state (pin low/floating/reset) = modem powered. Power-cycle sequence: try graceful `AT+QPOWD` → wait for STATUS to show off → if hung: PWRKEY held low ≥ 3 s (HW design §3.7.2.1) → if still hung: PB10 HIGH ≥ 1 s (Q3 opens, VBAT_MODEM collapses into 4×47 µF) → PB10 LOW → VBAT stable ≥ 30 ms (§3.7.1 note 1; 2 s if VBAT was off for long) → PWRKEY pulse per EC200U timing (≥ 2 s low… see HW design Fig 13: STATUS asserts ~4–5 s after PWRKEY). RESET_N only when `AT+QPOWD` and PWRKEY both fail (§3.7.3 note 2). Never leave PB10 high in sleep — that is the brick-prevention path. | modem_rf, handoff §2 rule 3 |
| FW-7 | **PWRKEY / RESET_N are through NPN inverters** | PA8/PB3 HIGH = pin pulled LOW at the modem. RESET_N is last-resort only per Quectel. | modem_rf |
| FW-8 | **TXB0104 OE follows VDD_EXT (10 k / 100 k divider = 1.64 V, fixed 2026-09-30)** | UART pins are Hi-Z until the modem's 1.8 V rail is up — do not interpret bus idle as modem-ready; use STATUS (FW-5). **Leave the MCU's internal pull-up/pull-down OFF on PA9/PA10/PA11/PA12** (MODEM_TX/RX/RI/DTR): the TXB0104's weak output drivers (≈4 kΩ) are overridden by pull resistors below 50 kΩ, and the AT32's internal pull is ≈40 kΩ. Configure them as plain push-pull (TX, DTR) and floating inputs (RX, RI). The original 47 k / 10 k divider left OE at 0.32 V, i.e. the modem UART would have been permanently disabled. | modem_rf, TI TXB0104 §"pull-up/down" |
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
| FW-13 | **Guaranteed VIN floor is 12 V; 10.5 V is a bench figure (BV-5)** | At VIN = 10.5 V and full load the buck input VIN_B is only ≈ 9.2 V after D1 (≈ 0.7 V) and R80 (1 R × 0.64 A), under the EG11752's 10 V minimum; at 12 V it is ≈ 10.7 V. Until BV-5 measures the real dropout, treat VIN_SENSE < 12 V as "on battery" (make the threshold a config value). The design intent is battery ride-through, not a fault. | U5 condition (a); review 2026-09-30 |
| FW-14 | **IGN_SENSE / VIN_SENSE cannot wake the MCU by EXTI — poll them by ADC from the RTC wake** | Both are 3×100 k : 9.1 k dividers (÷ 34): 12 V → 0.35 V, 24 V → 0.71 V, 100 V → 2.9 V, far below the AT32's digital VIH, so PA0/PA1 never see a logic edge. Wake from Deepsleep on the RTC alarm (1–5 s), sample the ADC, then decide; or run the ADC analog watchdog on a periodic conversion. IMU INT1 (PB5) is the motion wake and RI (PA11) the SMS/URC wake (both true digital edges). | handoff §5; review 2026-09-30 |
| FW-15 | Battery sense divider 1 M:1 M from SYS — ~2 µA standing drain, high impedance: use long ADC sample time (handoff: slow sample time, 12-bit). | handoff §4 |
| FW-18 | **CAN transceiver is in STANDBY until firmware drives PA15 LOW** | SIT1051 STB (pin 8) high = standby; PA15 is JTDI with an internal pull-up after reset. Sequence: disable JTAG (FW-1) → PA15 push-pull LOW → CAN1 init. Keep it high in sleep to save the transceiver's supply current. | io sheet; review 2026-09-30 |
| FW-19 | **IWDG keeps counting in Deepsleep (LSI)** | The sleep interval must be shorter than the IWDG timeout, or the watchdog kicked immediately before sleeping with a timeout sized for the longest sleep. There is no hardware "freeze in sleep" for the IWDG. | FW-3 consequence |
| FW-20 | **Battery floor and ceiling** | BQ25606 SYS regulation minimum is 3.5 V (SYSMIN) and the charge voltage is 4.208 V (VSET floating), so VBAT_SENSE reads 3.5–4.26 V in normal use. Shut the modem down gracefully (FW-6) at ≈ 3.6 V and stop logging at ≈ 3.5 V; the modem's own VBAT minimum (3.4 V) and the 3V3 LDO dropout leave no margin below that. | BQ25606 §7.3; review 2026-09-30 |
| FW-21 | **Lock the modem to LTE if the fitted variant has 2G fallback** (`AT+QCFG="nwscanmode",3` — check the EC200U AT manual for the exact value) | The VBAT_MODEM bulk (4×47 µF X7R, F-13) is sized for LTE Cat 1 transmit bursts, not for GSM 2 A/577 µs bursts. | review 2026-09-30 |
| FW-22 | **Read the Artery AT32F403A errata sheet before finalising the CAN and low-power drivers**; it has entries on both. | review 2026-09-30 |

## IMU

| # | Item | Detail | Origin |
|---|---|---|---|
| FW-16 | QMI8658B on I2C1 at address **0x6A** (SA0 tied high). CS tied high = I2C mode. RESV pin handling is hardware; nothing to do in firmware. INT1 → PB5. | mcu sheet, QST datasheet |
| FW-17 | **SIM card-detect polarity:** holder CD switch is SHORTED to GND with no card, OPEN with card inserted → USIM_DET is pulled to VDD_EXT by R91 (51 k, added 2026-09-30 — the pin has no internal pull-up, Quectel Fig 18) = card present. Enable detection with `AT+QSIMDET=1,1` (high level = inserted; confirm the argument order in the EC200U AT manual). | JXTCONN drawing, M3; review 2026-09-30 |

## Bench/bring-up items (hardware validation, firmware assists)

| # | Item | Detail | Origin |
|---|---|---|---|
| BV-1 | **EG11752 current limit (F-12 closed 2026-09-30)** | R82 is now 0.1 R: the IC compares (IS − VS) with 0.2 V, so the peak limit is 2.0 A (normal peak ≈ 1.2 A, L1 Isat 2.7 A). 0 R had disabled the limit and the short-circuit protection. Bench: short 5V0 through 0.1 R at 100 V in and confirm the converter folds back without damage; record the actual trip current. | power sheet, review 2026-09-30 |
| BV-5 | **Input dropout** | Measure the VIN at which 5V0 leaves regulation at 1 A load (expected between 10.5 and 12 V, see FW-13) and set the firmware "on battery" threshold from it. | review 2026-09-30 |
| BV-6 | **Reverse polarity, all pins** | Apply −24 V VIN with the DO1/DO2 loads connected to the same supply and confirm nothing conducts (D7/D8 now return to VIN_P behind D1, closing the body-diode path that bypassed D1). | review 2026-09-30 |
| BV-7 | **DI margin at the input floor** | At 10.5 V on DI1/DI2 confirm PB12/PB13 read low with margin (opto CTR at 0.26 mA LED current against the 220 k pull-up), −20 °C and +70 °C. | review 2026-09-30 |
| BV-2 | **EG11752 minimum on-time** | At 100 V→5 V, Ton ≈ 455 ns @110 kHz; datasheet gives no min-on-time spec. Bench test: 100 V in, 0.7–1 A out, and light-load at 100 V (frequency-foldback behaviour). #1 bench item. | TASK A risk list |
| BV-3 | EG11752 EN is pulled up to VCC through 100 k per fig 6-2 — verify EN pin voltage stays within its 7 V abs max across VCC range on first power-up. | power sheet note |
| BV-4 | U5 qualification: 3 units, 1000 h burn-in at 100 V/85 °C + thermal cycling −40↔+85 °C (U5 condition (c), milestone-6 plan). | U5 approval |
