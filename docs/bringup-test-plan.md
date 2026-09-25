# Bring-up and bench test plan — MEWP telematics tracker

For the first assembled boards from JLCPCB. Work through the sections in
order; do not skip the power-up sequence. Every rail has a test point, so
nothing needs to be probed on a component.

Equipment: bench supply 0–110 V / 1 A with current limit, a second 12 V
supply, multimeter, oscilloscope (≥ 50 MHz), SWD probe (J-Link / ST-Link /
AT-Link), USB–UART adapter (3.3 V logic), CAN adapter (PCAN / candleLight),
nano-SIM with data, 1S Li-ion cell, the two antennas, a 100 Ω resistor and a
1 kΩ resistor for load tests.

Safety: the input section carries up to 100 V. Boards must be **conformal
coated before any test above 60 V** (design rule P1, creepage at U5). Keep
one hand off the board when the HV supply is on.

## 0. Visual and continuity (no power)

- [ ] Compare the board against the assembly drawing: U1 (modem), U2 (MCU),
      U5 (buck), U6 (charger) orientation marks; polarised parts D7/D8, D16,
      C77/C78, C40/C41 orientation.
- [ ] Multimeter continuity: no short between GND (TP7) and any rail test
      point: TP23 VIN, TP19 5V0, TP13 SYS, TP6 3V3, TP24 VBAT_MODEM,
      TP17 USB_VBUS. Expect > 1 kΩ on all (charged caps may read low then
      rise).
- [ ] Solder-jumper JP1 (BOOT0) open, JP2 as documented in the schematic.

## 1. Power-up sequence

Start with the current limit at **50 mA**; raise it only as each step passes.

1. [ ] Apply **12 V** to VIN (J1 pins per the harness sheet). Current limit
       50 mA. Expect 5V0 at TP19: **5.0 ± 0.25 V**. Idle input current < 20 mA.
       If 5V0 is absent or the supply limits: stop, check U5/L1/D16.
2. [ ] SYS at TP13: 4.4–5.0 V with no battery (U6 power path from 5V0).
3. [ ] 3V3 at TP6: **3.30 ± 0.10 V**.
4. [ ] Scope 5V0 ripple at C77/C78: < 50 mVpp at idle.
5. [ ] Raise the current limit to 500 mA. Connect the 1S cell to J2 with the
       correct polarity. VBAT at the cell terminals rises slowly; charge
       current (measure in series) ≤ the value set by R85/R86 (see schematic).
       Remove VIN: the board must stay alive from the cell (SYS ≈ cell voltage).
6. [ ] VBAT_MODEM at TP24: present only when the MCU has enabled the modem
       switch (Q3). Before firmware it may be 0 V — that is correct.
7. [ ] HV proof (coated boards only): raise VIN in steps 24 V → 48 V → 80 V →
       **100 V**, 1 minute each; 5V0 must stay within tolerance, input current
       must fall as voltage rises (constant power), nothing warms up beyond
       ~50 °C on U5/L1. Any audible noise or 5V0 droop: stop.

## 2. MCU: flash and debug

- [ ] SWD probe on TP1 (SWDIO), TP2 (SWCLK), TP3 (NRST), TP7 (GND), TP6 (3.3 V
      reference). The probe must identify an **AT32F403A** (Artery; use
      AT-Link or an ST-Link with Artery's tool). Read the device ID.
- [ ] Flash a blink/UART-hello build. UART console on TP4 (DBG_TX from the
      MCU) / TP5 (DBG_RX), 115200 8N1, 3.3 V. Expect the hello string.
- [ ] Bootloader path: short JP1 (BOOT0 high), reset: the MCU must enumerate
      as the Artery serial bootloader on the debug UART. Reopen JP1.
- [ ] 8 MHz crystal running (scope on Y1, 10:1 probe, or read the MCU clock
      register); 32 kHz crystal running (RTC ticking).

## 3. Storage and peripherals

- [ ] SPI NOR U7: read JEDEC ID over SPI1 — expect GigaDevice **C8 40 17**
      (GD25Q64). Write/read-back a 4 kB test pattern.
- [ ] IMU U3 (QMI8658): WHO_AM_I over I2C1 — expect **0x05**. Read
      accelerometer; tilt the board, values follow.
- [ ] CAN U4: connect the CAN adapter, 500 kbit/s, termination per the
      harness. Send a frame from the board and receive one; check CAN_STB
      behaviour (transceiver standby when the MCU sleeps).
- [ ] DI1/DI2: apply 12 V and 0 V to each input; the MCU reads the state and
      the input LEDs follow. Then 24 V and 80 V (coated boards): no damage,
      same reading.
- [ ] DO1/DO2: command each output on with a 1 kΩ load to 12 V: the low-side
      switch sinks; measure < 0.5 V across the FET at 100 mA (100 Ω load).
      Off state: leakage < 10 µA. Verify the **default-OFF at power-up** rule
      (outputs must not pulse when the MCU resets).
- [ ] IGN_SENSE and VIN_SENSE: apply known VIN values (12, 24, 48, 96 V);
      the ADC readings agree within 3 % after the divider ratio.
- [ ] VBAT_SENSE: reading matches the cell voltage within 2 %.

## 4. Modem and RF

- [ ] Insert the nano-SIM in X1. Firmware enables Q3: VBAT_MODEM at TP24 rises
      to the charger's SYS voltage; modem current at PWRKEY pulse spikes to
      ~0.5 A briefly (supply current limit ≥ 1 A here).
- [ ] MODEM_TX/RX (TP27/TP28): AT console alive: `AT` → `OK`, `ATI` shows
      EC200U firmware, `AT+CPIN?` → READY.
- [ ] USB test pads TP15/TP16/TP17: connect a USB cable (D+/D−/VBUS/GND);
      the PC enumerates the Quectel USB interfaces. Needed for modem firmware
      updates only.
- [ ] LTE: attach the LTE antenna (internal FPC or external SMA per build).
      `AT+CSQ` ≥ 10 in a location with normal coverage; `AT+CREG?` registered;
      a data session brings up an IP (`AT+QIACT`).
- [ ] GNSS: attach the active patch (bias-T L4/R90/C83 populated); outdoors
      or at a window, a first fix within 60 s cold, `AT+QGPSLOC=2` returns a
      position; C/N0 of the best satellites ≥ 35 dB-Hz. Repeat with the
      modem transmitting at full power (a data transfer running): C/N0 must
      not drop by more than ~5 dB — this is the 40 dB isolation check.
- [ ] NETLIGHT LED follows registration state.

## 5. System and endurance

- [ ] Idle current at 12 V with the modem in PSM/sleep: record it (target in
      the firmware notes); at 100 V, current ≈ 12 V current × 12/100.
- [ ] Thermal: 30 min at 100 V input, modem transmitting, DO1/DO2 loaded:
      surface temperatures with an IR thermometer; U5 and L1 < 70 °C,
      U1 < 60 °C, nothing else warm.
- [ ] 85 °C soak (qualification, per F-23): 4 h in an oven, then repeat the
      GNSS C/N0 and LTE CSQ readings — record before/after.
- [ ] 6-day buffering test: disconnect LTE (remove antenna), let the board
      log for 24 h, restore LTE; the buffered telemetry uploads and the
      flash usage matches the expected rate.

## 6. Record

For each board: serial, date, every measured voltage, current at 12/24/48/
100 V, modem IMEI, GNSS time-to-first-fix and C/N0, CAN OK/fail, DI/DO
readings, thermal readings, and any deviation. Photos of both sides before
coating. File under docs/bringup/<serial>.md.
